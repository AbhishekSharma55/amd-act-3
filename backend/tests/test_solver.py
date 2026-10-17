from copy import deepcopy

import pytest
from conftest import mock

from app.approval import required_concessions
from app.checker import check
from app.solver import plan_alternatives, solve
from app.timeutil import hm
from helpers import constraint, tiny_fixture


def key(schedule):
    return sorted((a["job"], a["op"], a["machine"], a["start"], a["end"]) for a in schedule)


def test_demo_outcomes(F, demo_constraints):
    alternatives, infeasible = plan_alternatives(F, demo_constraints, {})
    assert [a["id"] for a in alternatives] == ["alt_reroute"]
    alt = alternatives[0]
    assert alt["merged_with"] == ["alt_reroute_overtime"]
    assert alt["kpis"]["late_jobs"] == [{"job": "J2", "minutes_late": 190, "customer": "Birla Valves"}]
    assert max(hm(a["end"]) for a in alt["schedule"] if a["job"] == "J7") <= hm("16:00")
    assert check(F, demo_constraints, alt["schedule"])["valid"]
    assert key(alt["schedule"]) == key(mock("solve.json")["alternatives"][0]["schedule"])
    keep = infeasible[0]
    assert (keep["id"], keep["solver_status"], keep["conflict"], keep["conflict_kind"]) == \
           ("alt_keep", "INFEASIBLE", ["c1", "c2"], "sufficient")
    assert {"type": "allow_reroute", "available": True} in keep["possible_concessions"]


def test_keep_machines_core_is_hard_due(F, demo_constraints):
    assert solve(F, demo_constraints, reroute=False, overtime=True)["hard_due_in_conflict"] == ["c2"]


def test_no_disruption_keeps_committed_plan(F):
    alternatives, infeasible = plan_alternatives(F, [], {})
    assert not infeasible
    assert key(alternatives[0]["schedule"]) == key(F["committed_schedule"])
    assert {a["change"] for a in alternatives[0]["schedule"]} <= {"none", "frozen"}


def test_every_alternative_passes_checker_under_overtime_and_priority(F, demo_constraints):
    cs = deepcopy(demo_constraints) + [constraint("c4", "priority", job="J2", level=3)]
    for c in cs:
        c["status"] = "ok"
    alternatives, _ = plan_alternatives(F, cs, {})
    assert alternatives
    for a in alternatives:
        assert check(F, cs, a["schedule"])["valid"]


def test_relax_hard_due_is_refused(F, demo_constraints):
    with pytest.raises(ValueError):
        plan_alternatives(F, demo_constraints, {"relax_hard_due": True})


def test_overtime_cutoff_enforced_by_solver_and_checker():
    f = tiny_fixture()
    cs = [constraint("ot", "overtime", allowed=True, until="18:30")]
    assert solve(f, cs, True, True)["status"] == "INFEASIBLE"
    assert not check(f, cs, f["committed_schedule"])["valid"]


def test_overtime_cutoff_boundary_is_valid():
    f = tiny_fixture((30,))
    cs = [constraint("ot", "overtime", allowed=True, until="18:30")]
    result = solve(f, cs, True, True)
    assert result["status"] == "OPTIMAL" and result["schedule"][0]["end"] == "18:30"
    assert check(f, cs, result["schedule"])["valid"]


def test_policy_cannot_enable_unaccepted_overtime():
    f = tiny_fixture()
    for cs in ([], [constraint("ot", "overtime", allowed=False)]):
        assert solve(f, cs, True, True)["status"] == "INFEASIBLE"


def test_overtime_uses_occupied_minutes_and_hourly_rate():
    f = tiny_fixture()
    cs = [constraint("ot", "overtime", allowed=True, until="20:00")]
    result = solve(f, cs, True, True)
    assert result["status"] == "OPTIMAL"
    assert (result["overtime_minutes"], result["overtime_cost"]) == (120, 90)
    assert result["objective"] == sum(hm(a["end"]) for a in result["schedule"]) + 90
    required = required_concessions(f, cs, result["schedule"])
    assert (required[0]["type"], required[0]["minutes"], required[0]["cost"]) == ("overtime", 120, 90)


def test_hard_date_updates_tardiness_as_well_as_bound():
    f = tiny_fixture((120, 120), now="08:00", due="12:00")
    f["jobs"][0].update(due="10:00", priority=3)
    cs = [constraint("d1", "due_date", job="J1", time="12:00", hard=True),
          constraint("d2", "due_date", job="J2", time="10:00", hard=False)]
    result = solve(f, cs, True, False)
    assert {a["job"]: a["end"] for a in result["schedule"]} == {"J1": "12:00", "J2": "10:00"}
    assert required_concessions(f, cs, result["schedule"]) == []


def test_multiple_outages_do_not_overwrite_each_other():
    f = tiny_fixture((60,), now="10:00", due="18:00")
    cs = [constraint("a", "machine_down", machine="M1", **{"from": "10:00", "until": "11:00"}),
          constraint("b", "machine_down", machine="M1", **{"from": "10:30", "until": "12:00"})]
    result = solve(f, cs, True, False)
    assert result["schedule"][0]["start"] == "12:00"
    assert check(f, cs, result["schedule"])["valid"]


def test_timeout_is_never_called_impossible(F, demo_constraints, monkeypatch):
    import app.solver as solver_mod
    monkeypatch.setattr(solver_mod, "solve", lambda *a, **k: {"status": "UNKNOWN", "time_ms": 10000})
    alternatives, infeasible = solver_mod.plan_alternatives(F, demo_constraints, {})
    assert not alternatives
    for x in infeasible:
        assert x["solver_status"] == "UNKNOWN" and x["conflict_kind"] is None
        assert "not a proof" in x["explanation"]


def test_all_machines_down_explains_without_hard_dates(F):
    cs = [constraint(f"c{i}", "machine_down", machine=m, **{"from": "10:00", "until": "18:00"})
          for i, m in enumerate(["M1", "M2", "M3"], 1)]
    alternatives, infeasible = plan_alternatives(F, cs, {})
    assert not alternatives and all(x["solver_status"] == "INFEASIBLE" for x in infeasible)
    assert "does not fit" in infeasible[0]["explanation"]
