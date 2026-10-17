from copy import deepcopy

from api_helpers import extract
from conftest import DEMO_MESSAGE


def test_demo_extraction_and_log(client):
    ex = extract(client)
    assert [c["status"] for c in ex["constraints"]] == ["ok", "ok", "ok"]
    assert ex["trace"]["model"] == "test-model"
    assert [x["step"] for x in client.get(f"/api/runs/{ex['run_id']}").json()["log"]] == ["extract"]


def test_revalidate_endpoint_reports_ready(client):
    client.state["proposals"] = [{"type": "machine_down", "params": {"machine": "Mill 4", "until": "15:00"},
                                  "source_span": "Mill 4 is down until 15:00"}]
    ex = extract(client, "Mill 4 is down until 15:00")
    assert ex["constraints"][0]["blocking_issues"]
    c = deepcopy(ex["constraints"][0])
    c["params"]["machine"] = "M1"
    r = client.post("/api/constraints/revalidate", json={"run_id": ex["run_id"], "constraints": [c]}).json()
    assert r["ready"] and r["constraints"][0]["origin"] == "user"


def test_revalidate_rejects_forged_source(client):
    ex = extract(client)
    forged = deepcopy(ex["constraints"])
    forged[1]["source_span"] = "J7 can ship tomorrow"
    r = client.post("/api/constraints/revalidate", json={"run_id": ex["run_id"], "constraints": forged})
    assert r.status_code == 422


def test_input_errors(client):
    for body, code in [({"message": ""}, "empty_message"), ({"message": "x" * 1001}, "message_too_long"),
                       ({"message": "hi", "extra": 1}, "bad_request"), ([1, 2], "bad_request")]:
        r = client.post("/api/extract", json=body)
        assert r.status_code == 400 and r.json()["error"]["code"] == code, (body, r.json())


def test_rate_limit(client, monkeypatch):
    import app.routes_extract as routes
    monkeypatch.setattr(routes.limiter, "per_minute", 2)
    routes.limiter._hits.clear()
    codes = [client.post("/api/extract", json={"message": DEMO_MESSAGE}).status_code for _ in range(3)]
    routes.limiter._hits.clear()
    assert codes == [200, 200, 429]


def test_unconfigured_amd_is_clear(client, monkeypatch):
    import app.routes_extract as routes
    from app.extract import extract_amd
    monkeypatch.setattr(routes, "extract_amd", extract_amd)
    monkeypatch.setattr(routes.config, "AMD_API_KEY", "")
    monkeypatch.setattr(routes.config, "ALLOW_RULE_FALLBACK", False)
    r = client.post("/api/extract", json={"message": DEMO_MESSAGE})
    assert r.status_code == 503 and r.json()["error"]["code"] == "amd_not_configured"


def test_fallback_is_labeled(client, monkeypatch):
    import app.routes_extract as routes
    from app.extract import extract_amd
    monkeypatch.setattr(routes, "extract_amd", extract_amd)
    monkeypatch.setattr(routes.config, "AMD_API_KEY", "")
    monkeypatch.setattr(routes.config, "ALLOW_RULE_FALLBACK", True)
    body = client.post("/api/extract", json={"message": DEMO_MESSAGE}).json()
    assert body["trace"]["fallback_used"] is True
    assert {c["origin"] for c in body["constraints"]} == {"rule_fallback"}
    assert [c["type"] for c in body["constraints"]] == ["machine_down", "due_date", "overtime"]


def test_unrelated_revalidation_keeps_an_undecided_review(client):
    """Review finding (PR 23): editing c1 must not silently confirm c2's assumed soft date."""
    client.state["proposals"] = [
        {"type": "machine_down", "params": {"machine": "Mill 4", "until": "14:00"}, "source_span": "Mill 4 is down until 14:00"},
        {"type": "due_date", "params": {"job": "J7", "time": "12:00"}, "source_span": "J7 must ship at 12:00"}]
    ex = extract(client, "Mill 4 is down until 14:00. J7 must ship at 12:00.")
    assert ex["constraints"][1]["status"] == "review"
    kept = deepcopy(ex["constraints"])
    kept[0]["params"]["machine"] = "M1"
    r = client.post("/api/constraints/revalidate", json={"run_id": ex["run_id"], "constraints": kept}).json()
    c2 = r["constraints"][1]
    assert c2["status"] == "review" and c2["origin"] == "amd_model" and not r["ready"]
    assert any("fixed" in issue for issue in c2["issues"])
    kept = deepcopy(r["constraints"])
    kept[1]["status"] = "accepted"  # an explicit decision clears it
    r = client.post("/api/constraints/revalidate", json={"run_id": ex["run_id"], "constraints": kept}).json()
    assert r["constraints"][1]["status"] == "accepted" and r["ready"]
    kept[1]["status"] = "review"
    kept[1]["params"] = {"job": "J7", "time": "12:00", "hard": True}  # so does a relevant edit
    r = client.post("/api/constraints/revalidate", json={"run_id": ex["run_id"], "constraints": kept}).json()
    assert r["constraints"][1]["status"] == "ok" and r["constraints"][1]["origin"] == "user"


def test_rejecting_one_side_clears_a_contradiction(client):
    client.state["proposals"] = [
        {"type": "due_date", "params": {"job": "J7", "time": "15:00", "hard": True}, "source_span": "J7 ships at 15:00"},
        {"type": "due_date", "params": {"job": "J7", "time": "16:30", "hard": True}, "source_span": "J7 ships at 16:30"}]
    ex = extract(client, "J7 ships at 15:00. Correction: J7 ships at 16:30.")
    assert all(c["blocking_issues"] for c in ex["constraints"])
    r = client.post("/api/constraints/revalidate", json={"run_id": ex["run_id"], "constraints": ex["constraints"][1:]}).json()
    assert r["constraints"][0]["status"] == "ok" and r["ready"]
