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


def test_running_outage_segments_are_stored_in_approval(client):
    message = ("M1 is down from 10:11 until 11:00. J6 would ideally ship by 12:30. J6 is critical.")
    client.state["proposals"] = [
        {"type": "machine_down", "params": {"machine": "M1", "from": "10:11", "until": "11:00"},
         "source_span": "M1 is down from 10:11 until 11:00"},
        {"type": "due_date", "params": {"job": "J6", "time": "12:30", "hard": False},
         "source_span": "J6 would ideally ship by 12:30"},
        {"type": "priority", "params": {"job": "J6", "level": 3}, "source_span": "J6 is critical"},
    ]
    response = solve(client, extract(client, message))
    assert response.status_code == 200, response.json()
    solved = response.json()
    alternative = solved["alternatives"][0]  # identical policies may be deduplicated
    response = client.post("/api/replay", json={
        "run_id": solved["run_id"], "alternative_id": alternative["id"],
        "assumptions": {"samples": 500, "seed": 7, "repair_delay_max_min": 0}})
    assert response.status_code == 200, response.json()
    replay = response.json()
    operation = next(row for row in replay["failing_scenario"]["timeline"]
                     if (row["job"], row["op"]) == ("J6", 1))
    assert operation["start"] == "09:00" and operation["segments"][1]["start"] == "11:00"
    response = approve(client, solved["run_id"], alternative_id=alternative["id"],
                       concessions=[c["id"] for c in alternative["concessions"]])
    assert response.status_code == 200, response.json()
    saved = response.json()["decision_record"]["replay"]
    assert saved["failing_scenario"] == replay["failing_scenario"]
    assert saved["assumptions"]["running_work"] == replay["assumptions"]["running_work"]
