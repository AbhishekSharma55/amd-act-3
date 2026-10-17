"""Check a running packaged app without calling AMD or needing third-party packages.

python scripts/container_smoke.py http://127.0.0.1:7860 --mode strict
python scripts/container_smoke.py http://127.0.0.1:7860 --mode fallback
"""
import argparse
import csv
import io
import json
import re
import time
import urllib.error
import urllib.request

MESSAGE = ("Mill M2 is unavailable until 14:00. Order J7 still needs to ship at 16:00. "
           "Overtime requires approval.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url")
    parser.add_argument("--mode", choices=("strict", "fallback"), required=True)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    checks = []

    def request(path, body=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(base + path, data=data,
                                     headers={} if data is None else {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read()

    def api(path, body=None, status=200):
        actual, raw = request(path, body)
        payload = json.loads(raw)
        assert actual == status, (path, actual, payload)
        return payload

    deadline = time.monotonic() + 45
    while True:
        try:
            health = api("/api/health")
            break
        except (urllib.error.URLError, TimeoutError):
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.5)
    assert health["ok"] and health["replay_device"] == "cpu-numpy"
    assert health["amd"]["configured"] is False, "Smoke tests require empty AMD configuration."
    assert health["fallback_enabled"] is (args.mode == "fallback"), health
    checks.append("health and explicit extraction mode")

    status, html = request("/")
    assert status == 200 and b'<div id="root">' in html
    assets = set(re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html.decode()))
    assert any(path.endswith(".js") for path in assets)
    for path in assets:
        status, content = request(path)
        assert status == 200 and content and not content.lstrip().startswith(b"<!doctype html>"), path
    checks.append("same-origin production frontend and compiled assets")

    factory = api("/api/factory")
    assert len(factory["committed_schedule"]) == sum(len(job["ops"]) for job in factory["jobs"])
    assert api("/api/does-not-exist", status=404)["error"]["code"] == "not_found"
    assert api("/api/extract", {"message": ""}, status=400)["error"]["code"] == "empty_message"
    checks.append("fixture and canonical API failures")

    if args.mode == "strict":
        error = api("/api/extract", {"message": MESSAGE}, status=503)["error"]
        assert error["code"] == "amd_not_configured" and error["retryable"] is False
        checks.append("missing AMD returns 503 without recorded substitution")
    else:
        draft = api("/api/extract", {"message": MESSAGE})
        assert draft["trace"]["fallback_used"] is True
        assert all(c["origin"] == "rule_fallback" for c in draft["constraints"])
        assert all(c["status"] == "ok" and not c["blocking_issues"] for c in draft["constraints"])
        checks.append("labeled rule extraction without an AMD call")

        solved = api("/api/solve", {"run_id": draft["run_id"], "constraints": draft["constraints"]})
        assert solved["run_id"] != draft["run_id"] and solved["alternatives"]
        assert all(a["checker"]["valid"] for a in solved["alternatives"])
        alternative = next((a for a in solved["alternatives"] if a["id"] == "alt_reroute"), solved["alternatives"][0])
        checks.append("actual CPU solving and independent checking")

        replay_body = {"run_id": solved["run_id"], "alternative_id": alternative["id"],
                       "assumptions": {"samples": 500, "seed": 7}}
        replay = api("/api/replay", replay_body)
        assert replay["samples"] == 500 and replay["device"] == "cpu-numpy"
        assert len(replay["jobs"]) == len(factory["jobs"])
        assert all(0 <= job["on_time"] <= job["of"] == 500 for job in replay["jobs"])
        checks.append("actual NumPy replay")

        approve_body = {"run_id": solved["run_id"], "alternative_id": alternative["id"],
                        "approved_concessions": [c["id"] for c in alternative["concessions"]],
                        "approver": "Container smoke test"}
        if approve_body["approved_concessions"]:
            error = api("/api/approve", {**approve_body, "approved_concessions": []}, status=422)["error"]
            assert error["code"] == "concessions_required"
        approved = api("/api/approve", approve_body)
        record = approved["decision_record"]
        assert record["checker"]["valid"] and record["run_id"] == solved["run_id"]
        assert record["amd_trace"]["fallback_used"] is True
        assert record["replay"]["samples"] == 500
        rows = list(csv.DictReader(io.StringIO(approved["dispatch_csv"])))
        assert len(rows) == len(factory["committed_schedule"])
        assert {(r["job"], int(r["op"])) for r in rows} == {(r["job"], r["op"]) for r in alternative["schedule"]}
        assert api("/api/approve", approve_body) == approved
        assert api("/api/replay", replay_body, status=409)["error"]["code"] == "run_locked"
        details = api(f"/api/runs/{solved['run_id']}")
        assert {"extract", "solve", "replay", "approve"} <= {entry["step"] for entry in details["log"]}
        checks.append("concession approval, idempotent export and locked evidence")

    print(json.dumps({"mode": args.mode, "passed": len(checks), "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
