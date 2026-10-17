import numpy as np
import pytest
from conftest import mock

from app.replay import check_assumptions, run_replay, simulate
from app.solver import effective_due, effective_priority, outage_windows
from app.timeutil import hm


@pytest.fixture
def demo(F, demo_constraints):
    schedule = mock("solve.json")["alternatives"][0]["schedule"]
    return (F, schedule, outage_windows(F, demo_constraints), effective_due(F, demo_constraints),
            effective_priority(F, demo_constraints))


def test_reference_mock_numbers(demo):
    r = run_replay(*demo, {"samples": 500, "seed": 7})
    jobs = {j["job"]: j for j in r["jobs"]}
    assert jobs["J4"]["on_time"] == 239 and jobs["J2"]["on_time"] == 0
    assert all(jobs[j]["on_time"] == 500 for j in ("J1", "J3", "J5", "J6", "J7"))
    assert r["failing_scenario"]["reason"] == "J4 misses 17:00 by 61 min"
    assert r["failing_scenario"]["bottleneck"]["machine"] == "M1"
    assert sum(x["bottleneck"] for x in r["failing_scenario"]["timeline"]) == 1
    assert {(j["job"], j["p90_finish"]) for j in mock("replay.json")["jobs"]} == \
           {(j["job"], j["p90_finish"]) for j in r["jobs"]}


def test_zero_noise_reproduces_plan_exactly(demo):
    F, schedule, outages, due, _ = demo
    sim, _ = simulate(schedule, due, hm(F["now"]), outages, n=10, spread=(1, 1), repair_extra_max=0)
    for a, s, e in sim:
        assert (s == hm(a["start"])).all() and (e == hm(a["end"])).all()
    r = run_replay(*demo, {"samples": 50, "duration_spread": [1, 1], "repair_delay_max_min": 0})
    assert r["failing_scenario"] is None


def test_future_operations_never_dispatch_early(demo):
    F, schedule, outages, due, _ = demo
    sim, _ = simulate(schedule, due, hm(F["now"]), outages, n=500, seed=3)
    for a, s, _ in sim:
        assert (s >= hm(a["start"])).all()


def test_running_work_never_finishes_before_now():
    schedule = [{"job": "J1", "op": 1, "machine": "M1", "start": "08:00", "end": "10:01"}]
    sim, _ = simulate(schedule, {"J1": hm("11:00")}, hm("10:00"), {}, n=500, seed=7)
    assert (sim[0][2] > hm("10:00")).all() and (sim[0][1] == hm("08:00")).all()


def test_same_seed_same_output(demo):
    assert run_replay(*demo, {"seed": 11})["jobs"] == run_replay(*demo, {"seed": 11})["jobs"]


def test_every_outage_window_is_honoured():
    schedule = [{"job": "J1", "op": 1, "machine": "M1", "start": "13:00", "end": "14:00"}]
    outages = {"M1": [(hm("10:00"), hm("12:00")), (hm("13:30"), hm("15:00"))]}
    sim, _ = simulate(schedule, {"J1": hm("18:00")}, hm("10:00"), outages, n=20, spread=(1, 1), repair_extra_max=0)
    assert (sim[0][1] == hm("15:00")).all()


@pytest.mark.parametrize("bad", [{"samples": 0}, {"seed": -1}, {"duration_spread": [1.2, 1.1]},
                                 {"repair_delay_max_min": -5}, {"spread": [1, 1]}])
def test_bad_assumptions_rejected(bad):
    with pytest.raises(ValueError):
        check_assumptions(bad)


def test_numpy_only_device(demo):
    assert run_replay(*demo, {"samples": 5})["device"] == "cpu-numpy"
    assert np.__version__


def test_sampled_running_work_restarts_after_a_future_outage(F):
    """Review finding (PR 25): a running operation must not keep working through a known outage."""
    from app.checker import check
    from app.solver import solve
    from app.validate import validate_constraints
    message = "M1 is down from 10:11 until 11:00."
    cs = validate_constraints(message, [{"type": "machine_down", "params": {"machine": "M1", "from": "10:11", "until": "11:00"},
                                         "source_span": message}], F)
    plan = solve(F, cs, reroute=True, overtime=False)
    assert check(F, cs, plan["schedule"])["valid"]
    sim, _ = simulate(plan["schedule"], effective_due(F, cs), hm(F["now"]), outage_windows(F, cs), n=500, seed=7,
                      repair_extra_max=0)
    for a, s, e in sim:
        if a["machine"] == "M1":
            assert not ((s < hm("11:00")) & (e > hm("10:11"))).any(), (a, int(((s < 660) & (e > 611)).sum()))
    row, s, e = next(x for x in sim if (x[0]["job"], x[0]["op"]) == ("J6", 1))
    restarted = s > hm("09:00")
    assert restarted.any() and (s[restarted] >= hm("11:00")).all()
    assert (e[~restarted] <= hm("10:11")).all()
    # Nominal times are unchanged: zero noise reproduces the plan exactly.
    sim, _ = simulate(plan["schedule"], effective_due(F, cs), hm(F["now"]), outage_windows(F, cs), n=5,
                      spread=(1, 1), repair_extra_max=0)
    for a, s, e in sim:
        assert (s == hm(a["start"])).all() and (e == hm(a["end"])).all()
