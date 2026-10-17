from conftest import DEMO_MESSAGE


def extract(client, message=DEMO_MESSAGE):
    r = client.post("/api/extract", json={"message": message})
    assert r.status_code == 200, r.json()
    return r.json()


def solve(client, ex, **extra):
    return client.post("/api/solve", json={"run_id": ex["run_id"], "constraints": ex["constraints"], **extra})


def approve(client, run_id, concessions=("k1",), approver="Supervisor", alternative_id="alt_reroute", **extra):
    return client.post("/api/approve", json={"run_id": run_id, "alternative_id": alternative_id,
                                             "approved_concessions": list(concessions), "approver": approver, **extra})
