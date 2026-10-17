from api_helpers import approve, extract, solve


def test_replay_is_stored_and_captured_in_approval(client):
    s = solve(client, extract(client)).json()
    r = client.post("/api/replay", json={"run_id": s["run_id"], "alternative_id": "alt_reroute",
                                         "assumptions": {"samples": 500, "seed": 7}})
    assert r.status_code == 200
    r = r.json()
    assert {j["job"]: j["on_time"] for j in r["jobs"]}["J4"] == 239
    assert r["failing_scenario"]["reason"] == "J4 misses 17:00 by 61 min"
    rec = approve(client, s["run_id"]).json()["decision_record"]
    assert rec["replay"]["samples"] == 500 and rec["replay"]["assumptions"]["seed"] == 7
    # An approved run is locked: its replay evidence cannot be replaced.
    again = client.post("/api/replay", json={"run_id": s["run_id"], "alternative_id": "alt_reroute"})
    assert again.status_code == 409
    details = client.get(f"/api/runs/{s['run_id']}").json()
    assert [x["step"] for x in details["log"]] == ["extract", "solve", "replay", "approve"]
    assert details["replays"]["alt_reroute"]["device"] == "cpu-numpy"


def test_replay_errors(client):
    s = solve(client, extract(client)).json()
    for body, status in [({"run_id": s["run_id"], "alternative_id": "alt_nope"}, 404),
                         ({"run_id": s["run_id"], "alternative_id": "alt_reroute", "assumptions": {"samples": 0}}, 400),
                         ({"run_id": s["run_id"], "alternative_id": "alt_reroute", "schedule": []}, 400),
                         ({"run_id": "r_nope", "alternative_id": "alt_reroute"}, 404)]:
        r = client.post("/api/replay", json=body)
        assert r.status_code == status, (body, r.json())
