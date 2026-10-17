from copy import deepcopy

from api_helpers import approve, extract, solve
from conftest import mock

from app import runstore


def test_solve_and_approve_demo(client):
    ex = extract(client)
    s = solve(client, ex)
    assert s.status_code == 200
    s = s.json()
    assert s["run_id"].startswith(ex["run_id"] + "_s") and s["status"] == "ok"
    alt = s["alternatives"][0]
    assert alt["checker"]["valid"] and [c["job"] for c in alt["concessions"]] == ["J2"]
    assert s["infeasible"][0]["solver_status"] == "INFEASIBLE"
    ok = approve(client, s["run_id"])
    assert ok.status_code == 200, ok.json()
    body = ok.json()
    assert body["dispatch_csv"] == mock("approve.json")["dispatch_csv"]
    rec = body["decision_record"]
    assert rec["approver"] == "Supervisor" and rec["checker"]["valid"] and rec["amd_trace"]["model"] == "test-model"
    assert rec["data_notice"] == "Synthetic demo data"
    assert approve(client, s["run_id"]).json() == body  # double click returns the same record
    assert approve(client, s["run_id"], approver="Someone else").status_code == 409
    log = client.get(f"/api/runs/{s['run_id']}").json()["log"]
    assert [x["step"] for x in log] == ["extract", "solve", "approve"]


def test_resolve_creates_fresh_runs(client):
    ex = extract(client)
    assert solve(client, ex).json()["run_id"] != solve(client, ex).json()["run_id"]


def test_review_item_blocks_solve_until_rejected(client):
    client.state["proposals"] = [
        {"type": "machine_down", "params": {"machine": "Mill 4", "from": None, "until": None},
         "source_span": "Mill 4 is down after lunch"},
        {"type": "due_date", "params": {"job": "J7", "time": "16:00", "hard": False}, "source_span": "J7 ships at 4"}]
    ex = extract(client, "Mill 4 is down after lunch. J7 ships at 4.")
    accepted = deepcopy(ex["constraints"])
    for c in accepted:
        c["status"] = "accepted"
    r = client.post("/api/solve", json={"run_id": ex["run_id"], "constraints": accepted})
    assert r.status_code == 422 and r.json()["error"]["code"] == "review_required"
    r = client.post("/api/solve", json={"run_id": ex["run_id"], "constraints": accepted[1:]})
    assert r.status_code == 200
    assert [c["id"] for c in r.json()["rejected"]] == ["c1"]
    # The rejected item is kept in the decision record but never constrains the plan.
    plan = r.json()["alternatives"][0]["id"]
    rec = approve(client, r.json()["run_id"], concessions=[], alternative_id=plan).json()["decision_record"]
    assert {c["id"]: c["status"] for c in rec["constraints"]} == {"c2": "accepted", "c1": "rejected"}


def test_client_cannot_forge_spans_or_plan_data(client):
    ex = extract(client)
    forged = deepcopy(ex["constraints"])
    forged[1]["source_span"] = "J7 can ship tomorrow"
    assert solve(client, {**ex, "constraints": forged}).status_code == 422
    s = solve(client, ex).json()
    assert approve(client, s["run_id"], schedule=[]).status_code in (400, 422)
    assert approve(client, s["run_id"], concessions=[]).status_code == 422
    assert approve(client, s["run_id"], approver="  ").status_code in (400, 422)


def test_solve_input_errors(client):
    ex = extract(client)
    for extra, status in [({"allow": {"relax_hard_due": True}}, 422), ({"time_limit_s": 0}, 400),
                          ({"allow": {"bogus": True}}, 400), ({"extra": 1}, 400)]:
        r = solve(client, ex, **extra)
        assert r.status_code == status, (extra, r.json())
    assert client.post("/api/solve", json={"run_id": "r_nope", "constraints": []}).status_code == 404


def test_expired_run_is_410(client, monkeypatch):
    ex = extract(client)
    monkeypatch.setattr(runstore.config, "RUN_TTL_S", -1)
    r = solve(client, ex)
    assert r.status_code == 410 and r.json()["error"]["code"] == "run_expired"
