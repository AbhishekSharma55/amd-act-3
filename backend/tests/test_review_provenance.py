from copy import deepcopy

import pytest

from api_helpers import extract
from app.validate import review_constraints, validate_constraints, validate_for_solve


def missing_hard_draft(client):
    client.state["proposals"] = [
        {"type": "machine_down", "params": {"machine": "Mill 4", "until": "14:00"},
         "source_span": "Mill 4 is down until 14:00"},
        {"type": "due_date", "params": {"job": "J7", "time": "12:00"},
         "source_span": "J7 must ship at 12:00"},
    ]
    draft = extract(client, "Mill 4 is down until 14:00. J7 must ship at 12:00.")
    constraints = deepcopy(draft["constraints"])
    constraints[0]["params"]["machine"] = "M1"
    return draft, constraints


def revalidate(client, draft, constraints):
    response = client.post("/api/constraints/revalidate", json={
        "run_id": draft["run_id"], "constraints": constraints})
    assert response.status_code == 200, response.json()
    return response.json()


def test_unrelated_revalidation_cannot_accept_a_missing_hard_flag(client, F):
    draft, constraints = missing_hard_draft(client)
    original_warning = draft["constraints"][1]["issues"]
    for _ in range(3):
        # Client-supplied ok/empty issues are not an explicit acceptance decision.
        constraints[1].update(status="ok", issues=[], blocking_issues=[])
        result = revalidate(client, draft, constraints)
        constraints = result["constraints"]
        due = constraints[1]
        assert result["ready"] is False
        assert due["status"] == "review" and due["issues"] == original_warning
        assert due["origin"] == "amd_model" and due["params"]["hard"] is False
        with pytest.raises(ValueError, match="resolve or reject"):
            validate_for_solve(F, constraints)


@pytest.mark.parametrize("decision", ["accept_soft", "set_hard"])
def test_deadline_can_be_resolved_by_an_explicit_decision(client, F, decision):
    draft, constraints = missing_hard_draft(client)
    if decision == "accept_soft":
        constraints[1]["status"] = "accepted"
    else:
        constraints[1]["params"]["hard"] = True
    result = revalidate(client, draft, constraints)
    due = result["constraints"][1]
    assert result["ready"]
    assert due["status"] == ("accepted" if decision == "accept_soft" else "ok")
    assert due["params"]["hard"] is (decision == "set_hard")
    assert due["origin"] == ("amd_model" if decision == "accept_soft" else "user")
    validate_for_solve(F, result["constraints"])


def test_changing_due_time_does_not_resolve_missing_hard_flag(client):
    draft, constraints = missing_hard_draft(client)
    constraints[1]["params"]["time"] = "12:30"
    result = revalidate(client, draft, constraints)
    due = result["constraints"][1]
    assert not result["ready"] and due["status"] == "review"
    assert due["params"]["time"] == "12:30" and due["origin"] == "user"
    assert any("whether this date is fixed" in issue for issue in due["issues"])


def test_editing_machine_does_not_confirm_an_ambiguous_repair_time(F):
    message = "Mill 4 is down until 2."
    proposals = [{"type": "machine_down", "params": {"machine": "Mill 4", "until": "14:00"},
                  "source_span": message}]
    draft = {"message": message, "proposals": proposals,
             "constraints": validate_constraints(message, proposals, F)}
    constraints = deepcopy(draft["constraints"])
    constraints[0]["params"]["machine"] = "M1"
    checked, _, _ = review_constraints(draft, constraints, F)
    assert checked[0]["status"] == "review" and not checked[0]["blocking_issues"]
    assert any("please confirm" in issue for issue in checked[0]["issues"])
    constraints[0]["params"]["until"] = "15:00"
    checked, _, edits = review_constraints(draft, constraints, F)
    assert checked[0]["status"] == "ok" and checked[0]["origin"] == "user"
    assert edits[0]["after"]["until"] == "15:00"


def test_rejecting_conflicting_item_still_clears_cross_item_review(F):
    message = "J7 ships at 15:00. J7 ships at 16:00."
    proposals = [{"type": "due_date", "params": {"job": "J7", "time": time, "hard": True},
                  "source_span": f"J7 ships at {time}"} for time in ("15:00", "16:00")]
    draft = {"message": message, "proposals": proposals,
             "constraints": validate_constraints(message, proposals, F)}
    assert all(c["blocking_issues"] for c in draft["constraints"])
    checked, rejected, _ = review_constraints(draft, [draft["constraints"][1]], F)
    assert checked[0]["status"] == "ok" and not checked[0]["blocking_issues"]
    assert rejected[0]["id"] == "c1" and rejected[0]["status"] == "rejected"
