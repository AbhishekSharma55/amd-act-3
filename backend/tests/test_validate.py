from copy import deepcopy

import pytest
from conftest import DEMO_MESSAGE, DEMO_PROPOSALS, mock

from app.timeutil import hm
from app.validate import (normalize_time, resolve_machine, review_constraints, span_ok, time_evidenced,
                          validate_constraints, validate_for_solve, valid_time)
from helpers import constraint


def by_type(cs):
    return {c["type"]: c for c in cs}


def test_demo_message_matches_contract(F):
    got = validate_constraints(DEMO_MESSAGE, DEMO_PROPOSALS, F)
    want = mock("extract.json")["constraints"]
    for g, w in zip(got, want):
        assert (g["id"], g["type"], g["params"], g["status"], g["blocking_issues"]) == \
               (w["id"], w["type"], w["params"], w["status"], w["blocking_issues"])
    assert "Outage interrupts J1 op 2 (in progress on M2); it will restart after repair" in got[0]["issues"]


def test_alias_resolves_to_machine_id(F):
    assert resolve_machine("Big Mill", F) == "M2"
    assert resolve_machine("vmc-1", F) == "M1"
    assert resolve_machine("Mill 4", F) is None


def test_unknown_machine_and_missing_times_block(F):
    msg = "Mill 4 is down after lunch. J7 ships at 4."
    cs = validate_constraints(msg, [
        {"type": "machine_down", "params": {"machine": "Mill 4", "from": None, "until": None},
         "source_span": "Mill 4 is down after lunch"},
        {"type": "due_date", "params": {"job": "J7", "time": "16:00", "hard": False}, "source_span": "J7 ships at 4"}], F)
    down, due = cs
    assert down["status"] == "review" and len(down["blocking_issues"]) == 3
    assert any("Unknown machine 'Mill 4'" in i for i in down["issues"])
    # "4" -> 16:00 is a complete but ambiguous interpretation: confirmable, not blocking
    assert due["status"] == "review" and due["blocking_issues"] == []


def test_span_not_in_message_blocks(F):
    cs = validate_constraints("M2 is down until 14:00", [
        {"type": "machine_down", "params": {"machine": "M2", "until": "14:00"}, "source_span": "M2 broke at 9"}], F)
    assert cs[0]["blocking_issues"] and "not in the message" in " ".join(cs[0]["issues"])


def test_span_check_ignores_case_whitespace_and_punctuation():
    assert span_ok("mill m2  is unavailable until 14:00", "Mill M2 is unavailable until 14:00.")
    assert not span_ok("", "anything")


def test_contradictory_due_dates_both_block(F):
    msg = "J7 ships at 15:00. Actually J7 ships at 16:00."
    cs = validate_constraints(msg, [
        {"type": "due_date", "params": {"job": "J7", "time": "15:00", "hard": True}, "source_span": "J7 ships at 15:00"},
        {"type": "due_date", "params": {"job": "J7", "time": "16:00", "hard": True}, "source_span": "J7 ships at 16:00"}], F)
    assert all(c["blocking_issues"] for c in cs)
    assert all("Two different due dates for J7" in c["issues"] for c in cs)


def test_unsupported_and_unknown_types_block(F):
    msg = "Steel bar shortage for J3."
    cs = validate_constraints(msg, [{"type": "material_shortage", "params": {"note": "steel"},
                                     "source_span": "Steel bar shortage for J3"}], F)
    assert cs[0]["type"] == "unsupported" and cs[0]["blocking_issues"]


def test_negation_overtime(F):
    cs = validate_constraints("No overtime today.", [
        {"type": "overtime", "params": {"allowed": False, "until": None}, "source_span": "No overtime today"}], F)
    assert cs[0]["status"] == "ok" and cs[0]["params"] == {"allowed": False, "until": None}


def test_outage_end_never_invented(F):
    cs = validate_constraints("Big mill stopped.", [
        {"type": "machine_down", "params": {"machine": "big mill", "from": None, "until": None},
         "source_span": "Big mill stopped"}], F)
    assert cs[0]["params"]["until"] is None
    assert "Provide an explicit repair end time" in cs[0]["blocking_issues"]


def test_time_parsing_and_evidence():
    assert normalize_time("2pm") == "14:00" and normalize_time("2:30 PM") == "14:30"
    assert normalize_time("14.00") == "14:00" and normalize_time(None) is None
    assert time_evidenced("14:00", "till 2pm") and time_evidenced("16:00", "at 4 p.m.")
    assert not time_evidenced("16:00", "J7 ships at 4") and not time_evidenced("16:00", "by 4:00")


def test_clock_minutes_and_missing_times_are_rejected(F):
    for value in (None, "09:99", "24:00", "9:00", "-1:00", "after lunch"):
        assert not valid_time(value, F)
        with pytest.raises(ValueError):
            hm(value)


def test_accept_cannot_bypass_unknown_id_or_missing_repair(F, demo_constraints):
    for updates in ({"machine": "Mill 4"}, {"until": None}):
        c = deepcopy(demo_constraints[0])
        c["params"].update(updates)
        c["status"] = "accepted"
        with pytest.raises(ValueError):
            validate_for_solve(F, [c])


def test_status_cannot_clear_a_blocking_review(F, demo_constraints):
    c = deepcopy(demo_constraints[0])
    c.update(status="accepted", blocking_issues=["Confirm the explicit outage start"])
    with pytest.raises(ValueError):
        validate_for_solve(F, [c])


def test_contradictory_dates_cannot_be_accepted(F):
    cs = [constraint("d1", "due_date", job="J7", time="15:00", hard=True),
          constraint("d2", "due_date", job="J7", time="16:00", hard=True)]
    with pytest.raises(ValueError):
        validate_for_solve(F, cs)


def test_review_edit_is_revalidated_and_marked_user(F):
    msg = "Mill 4 is down until 15:00."
    draft = {"message": msg, "constraints": validate_constraints(msg, [
        {"type": "machine_down", "params": {"machine": "Mill 4", "from": None, "until": "15:00"},
         "source_span": "Mill 4 is down until 15:00"}], F)}
    assert draft["constraints"][0]["blocking_issues"]
    edited = deepcopy(draft["constraints"][0])
    edited["status"] = "accepted"
    out, rejected, edits = review_constraints(draft, [edited], F)
    assert out[0]["status"] == "review" and out[0]["blocking_issues"]  # Accept alone fixes nothing
    edited["params"]["machine"] = "M1"
    out, rejected, edits = review_constraints(draft, [edited], F)
    assert out[0]["status"] == "ok" and out[0]["origin"] == "user"
    assert edits == [{"id": "c1", "before": draft["constraints"][0]["params"], "after": edited["params"]}]


def test_planner_typed_times_need_no_reconfirmation(F):
    msg = "Mill 4 is down after lunch."
    draft = {"message": msg, "constraints": validate_constraints(msg, [
        {"type": "machine_down", "params": {"machine": "Mill 4", "from": None, "until": None},
         "source_span": "Mill 4 is down after lunch"}], F)}
    edited = deepcopy(draft["constraints"][0])
    edited["params"] = {"machine": "M1", "from": "13:00", "until": "15:00"}
    out, _, _ = review_constraints(draft, [edited], F)
    assert out[0]["status"] == "ok" and out[0]["origin"] == "user"
    edited["params"]["until"] = "12:00"  # still validated: end before start
    out, _, _ = review_constraints(draft, [edited], F)
    assert out[0]["blocking_issues"]


def test_review_rejects_changed_source_or_new_items(F):
    msg = "M2 is down until 14:00."
    draft = {"message": msg, "constraints": validate_constraints(msg, [
        {"type": "machine_down", "params": {"machine": "M2", "until": "14:00"}, "source_span": "M2 is down until 14:00"}], F)}
    forged = deepcopy(draft["constraints"][0]) | {"source_span": "M2 is down until 19:00"}
    with pytest.raises(ValueError):
        review_constraints(draft, [forged], F)
    with pytest.raises(ValueError):
        review_constraints(draft, [deepcopy(forged) | {"id": "c9"}], F)
    out, rejected, _ = review_constraints(draft, [], F)
    assert out == [] and rejected[0]["status"] == "rejected"


def test_job_by_customer_name(F):
    msg = "Gamma Aerospace's order must ship by 16:00."
    cs = validate_constraints(msg, [{"type": "due_date", "params": {"job": "Gamma Aerospace", "time": "16:00", "hard": True},
                                     "source_span": "Gamma Aerospace's order must ship by 16:00"}], F)
    assert cs[0]["params"]["job"] == "J7" and cs[0]["status"] == "ok"


def test_relative_time_is_kept_but_confirmed(F):
    msg = "Mill M2 will be down for 2 hours."
    cs = validate_constraints(msg, [{"type": "machine_down", "params": {"machine": "M2", "from": None, "until": "12:00"},
                                     "source_span": "Mill M2 will be down for 2 hours"}], F)
    assert cs[0]["params"]["until"] == "12:00"
    assert cs[0]["status"] == "review" and cs[0]["blocking_issues"] == []


def test_four_digit_and_hrs_times():
    assert normalize_time("1430") == "14:30" and normalize_time("14 hrs") == "14:00"
    assert time_evidenced("14:30", "down till 1430 hrs")
