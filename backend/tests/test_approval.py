import asyncio
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import unittest

from fastapi import FastAPI
import httpx

from backend.app.approval import ApprovalError, required_concessions
from backend.app.approval_api import create_approval_router
from backend.app.approval_store import ApprovalStore


ROOT = Path(__file__).resolve().parents[2]
UNSET = object()


def load(name):
    return json.loads((ROOT / "shared" / "mocks" / f"{name}.json").read_text())


def snapshot():
    extract, solve = load("extract"), load("solve")
    return {"fixture": load("factory"), "message": extract["message"], "trace": extract["trace"],
            "constraints": extract["constraints"], "alternatives": {a["id"]: a for a in solve["alternatives"]},
            "data_notice": "Synthetic demo data; no live AMD call"}


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 17, 12, 30, tzinfo=timezone.utc)
        self.store = ApprovalStore(clock=lambda: self.now)
        self.run = snapshot()
        self.run_id = self.store.save_run(self.run)
        self.body = {"run_id": self.run_id, "alternative_id": "alt_reroute", "approved_concessions": ["k1"], "approver": "  Abhishek Sharma  "}

    def assertError(self, code, body=UNSET, store=None):
        with self.assertRaises(ApprovalError) as raised:
            (store or self.store).approve(self.body if body is UNSET else body)
        self.assertEqual(raised.exception.code, code)
        return raised.exception

    def test_success_has_current_identity_trace_replay_constraints_and_sorted_csv(self):
        rejected = {"id": "rejected_original", "status": "rejected", "type": "unsupported", "params": {"note": "not modeled"}}
        run = snapshot()
        run["constraints"].append(rejected)
        run_id = self.store.save_run(run)
        replay = {**load("replay"), "run_id": run_id}
        self.store.save_replay(run_id, "alt_reroute", replay)
        result = self.store.approve({**self.body, "run_id": run_id})
        record = result["decision_record"]
        self.assertEqual(record["approver"], "Abhishek Sharma")
        self.assertEqual(record["approved_at"], self.now.isoformat(timespec="seconds"))
        self.assertEqual(record["amd_trace"], run["trace"])
        self.assertEqual(record["replay"], replay)
        self.assertIn(rejected, record["constraints"])
        self.assertEqual(record["checker"], {"valid": True, "violations": []})
        self.assertEqual(record["fixture"], run["fixture"])
        rows = list(csv.DictReader(io.StringIO(result["dispatch_csv"])))
        self.assertEqual(len(rows), 15)
        self.assertEqual([(r["machine"], r["start"]) for r in rows], sorted((r["machine"], r["start"]) for r in rows))
        for machine in {row["machine"] for row in rows}:
            self.assertEqual([int(row["sequence"]) for row in rows if row["machine"] == machine], list(range(1, 1 + sum(row["machine"] == machine for row in rows))))
        self.assertEqual(next(row for row in rows if row["job"] == "J1" and row["op"] == "2")["changed"], "restarted_on_M1")
        self.assertEqual(result["dispatch_csv"], load("approve")["dispatch_csv"])

    def test_cached_concessions_checker_and_change_labels_cannot_bypass_rules(self):
        self.run["alternatives"]["alt_reroute"].update(concessions=[], checker={"valid": True, "violations": []})
        self.run["alternatives"]["alt_reroute"]["schedule"][2]["change"] = "none"
        run_id = self.store.save_run(self.run)
        self.assertError("concessions_required", {**self.body, "run_id": run_id, "approved_concessions": []})
        result = self.store.approve({**self.body, "run_id": run_id})
        self.assertIn("restarted_on_M1", result["dispatch_csv"])

    def test_client_plan_trace_replay_or_concession_replacements_are_rejected(self):
        for key in ("schedule", "constraints", "concessions", "replay", "amd_trace", "checker", "approved_at"):
            with self.subTest(field=key):
                self.assertError("invalid_approval", {**self.body, key: []})

    def test_missing_or_extra_concessions_fail(self):
        for ids in ([], ["k2"], ["k1", "k2"]):
            with self.subTest(ids=ids):
                self.assertError("concessions_required", {**self.body, "approved_concessions": ids})

    def test_invalid_requests_return_domain_errors(self):
        for body in (None, [], {}, True, {**self.body, "approver": " "}, {**self.body, "approver": 1},
                     {**self.body, "run_id": []}, {**self.body, "alternative_id": "../bad"},
                     {**self.body, "approved_concessions": None}, {**self.body, "approved_concessions": [True]},
                     {**self.body, "approved_concessions": ["k1", "k1"]}):
            with self.subTest(body=body):
                self.assertError("invalid_approval", body=body)

    def test_broken_stored_schedule_fails_even_with_cached_passing_checker(self):
        self.run["alternatives"]["alt_reroute"]["schedule"][2]["start"] = "09:20"
        run_id = self.store.save_run(self.run)
        self.assertError("schedule_invalid", {**self.body, "run_id": run_id})

    def test_accepted_overtime_cutoff_and_hard_due_are_not_relaxed_at_approval(self):
        for extra in ({"id": "earlier", "type": "due_date", "params": {"job": "J7", "time": "12:00", "hard": True}, "status": "accepted", "source_span": "12:00", "issues": [], "blocking_issues": [], "origin": "user"},):
            run = snapshot()
            run["constraints"] = [c for c in run["constraints"] if c["type"] != "due_date"] + [extra]
            run_id = self.store.save_run(run)
            self.assertError("schedule_invalid", {**self.body, "run_id": run_id})
        run = snapshot()
        run["alternatives"]["alt_reroute"]["relaxed_constraint_ids"] = ["c2"]
        run_id = self.store.save_run(run)
        self.assertError("unsupported_relaxation", {**self.body, "run_id": run_id})

    def test_updated_due_dates_override_fixture_dates(self):
        fixture = load("factory")
        due = {"id": "due", "type": "due_date", "params": {"job": "J4", "time": "12:30", "hard": False}, "status": "accepted", "source_span": "12:30", "issues": [], "blocking_issues": [], "origin": "user"}
        concessions = required_concessions(fixture, [due], fixture["committed_schedule"])
        self.assertEqual(concessions, [{"id": "k1", "type": "late_delivery", "job": "J4", "detail": "J4 (Delta Auto) ships 35 min late"}])
        due["params"]["hard"] = True
        with self.assertRaises(ApprovalError):
            required_concessions(fixture, [due], fixture["committed_schedule"])

    def test_occupied_overtime_counts_only_work_and_uses_hourly_cost(self):
        run = snapshot()
        row = next(row for row in run["alternatives"]["alt_reroute"]["schedule"] if (row["job"], row["op"]) == ("J4", 2))
        row.update(start="18:00", end="19:30")
        run["alternatives"]["alt_reroute"]["policy"]["overtime"] = True
        run_id = self.store.save_run(run)
        self.assertError("concessions_required", {**self.body, "run_id": run_id})
        body = {**self.body, "run_id": run_id, "approved_concessions": ["k1", "k2", "k3"]}
        result = self.store.approve(body)
        overtime = result["decision_record"]["concessions"][-1]
        self.assertEqual((overtime["minutes"], overtime["cost"]), (90, 67.5))
        run["constraints"][-1]["params"]["until"] = "19:00"
        run_id = self.store.save_run(run)
        self.assertError("schedule_invalid", {**body, "run_id": run_id})

    def test_policy_and_cost_are_checked_instead_of_cached_kpis(self):
        run = snapshot()
        run["alternatives"]["alt_reroute"]["policy"]["reroute"] = False
        run_id = self.store.save_run(run)
        self.assertError("policy_violation", {**self.body, "run_id": run_id})
        run = snapshot()
        row = next(row for row in run["alternatives"]["alt_reroute"]["schedule"] if (row["job"], row["op"]) == ("J4", 2))
        row.update(start="18:00", end="19:30")
        run_id = self.store.save_run(run)
        self.assertError("policy_violation", {**self.body, "run_id": run_id})
        run["alternatives"]["alt_reroute"]["policy"]["overtime"] = True
        run["fixture"]["shift"]["overtime_cost_per_hour"] = True
        run_id = self.store.save_run(run)
        self.assertError("invalid_stored_run", {**self.body, "run_id": run_id})

    def test_malformed_server_metadata_is_rejected_cleanly(self):
        for policy in (None, [], {"reroute": "true", "overtime": False}):
            run = snapshot()
            run["alternatives"]["alt_reroute"]["policy"] = policy
            run_id = self.store.save_run(run)
            self.assertError("invalid_stored_run", {**self.body, "run_id": run_id})
        for options in ({"run_id": ""}, {"ttl_seconds": True}, {"ttl_seconds": 0}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.store.save_run(snapshot(), **options)
        for field, value in (("message", []), ("trace", True), ("alternatives", [])):
            run = snapshot()
            run[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.store.save_run(run)

    def test_unknown_expired_and_cross_run_alternatives_are_clean_errors(self):
        self.assertEqual(self.assertError("run_not_found", {**self.body, "run_id": "missing"}).status, 404)
        self.assertError("alternative_not_found", {**self.body, "alternative_id": "missing"})
        self.now += timedelta(hours=1)
        self.assertEqual(self.assertError("run_expired").status, 410)

    def test_snapshot_and_returned_records_are_isolated_and_ids_cannot_be_reused(self):
        self.run["alternatives"]["alt_reroute"]["schedule"].clear()
        fetched = self.store.get_run(self.run_id)
        fetched["constraints"].clear()
        result = self.store.approve(self.body)
        result["decision_record"]["concessions"].clear()
        self.assertEqual(len(self.store.approve(self.body)["decision_record"]["concessions"]), 1)
        with self.assertRaises(ApprovalError):
            self.store.save_run(snapshot(), run_id=self.run_id)
        self.assertNotEqual(self.store.save_run(snapshot()), self.run_id)

    def test_idempotent_retries_and_concurrent_clicks_return_one_locked_record(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.store.approve(self.body), range(4)))
        self.assertTrue(all(result == results[0] for result in results))
        self.now += timedelta(seconds=10)
        self.assertEqual(self.store.approve(self.body), results[0])
        self.assertError("run_locked", {**self.body, "approver": "Someone else"})
        with self.assertRaises(ApprovalError):
            self.store.save_replay(self.run_id, "alt_reroute", {**load("replay"), "run_id": self.run_id})

    def test_replay_cannot_be_attached_to_a_different_plan(self):
        with self.assertRaises(ValueError):
            self.store.save_replay(self.run_id, "alt_reroute", load("replay"))
        self.assertIsNone(self.store.approve(self.body)["decision_record"]["replay"])

    def test_http_contract_uses_real_status_and_canonical_errors(self):
        app = FastAPI()
        app.include_router(create_approval_router(self.store))

        async def exercise():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://approval.test") as client:
                response = await client.post("/api/approve", json={**self.body, "approved_concessions": []})
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json()["error"]["code"], "concessions_required")
                self.assertFalse(response.json()["error"]["retryable"])
                self.assertEqual((await client.post("/api/approve", content="{not-json")).status_code, 400)
                self.assertEqual((await client.post("/api/approve", json=[])).status_code, 422)
                self.assertEqual((await client.post("/api/approve", json={**self.body, "run_id": "missing"})).status_code, 404)
                self.assertEqual((await client.post("/api/approve", json=self.body)).status_code, 200)
                self.assertEqual((await client.post("/api/approve", json=self.body)).status_code, 200)
                self.assertEqual((await client.post("/api/approve", json={**self.body, "approver": "Other"})).status_code, 409)
                self.assertEqual((await client.post("/api/solve", json={})).status_code, 404)

        asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
