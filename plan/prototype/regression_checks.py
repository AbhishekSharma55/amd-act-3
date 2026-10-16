"""Focused regressions for executable planning examples, not an app test suite.

Run: python3 plan/prototype/regression_checks.py (requires ortools and numpy).
Loading guide blocks tests the examples a teammate will actually copy.
"""
import ast
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
import types
import unittest

import numpy as np

import proto
import replay_proto

PLAN = Path(__file__).resolve().parents[1]
BLOCKS = re.findall(r"```python\n(.*?)```", (PLAN / "04_BACKEND_GUIDE.md").read_text(), re.S)
PACKAGE = "rehearsal_plan_examples"
package = types.ModuleType(PACKAGE)
package.__path__ = []
sys.modules[PACKAGE] = package


def example(name, marker):
    source = next(block for block in BLOCKS if marker in block)
    module = types.ModuleType(f"{PACKAGE}.{name}")
    module.__package__ = PACKAGE
    sys.modules[module.__name__] = module
    exec(compile(source, f"04_BACKEND_GUIDE.md:{name}", "exec"), module.__dict__)
    return module


timeutil = example("timeutil", "def hm(")
validate = example("validate", "def validate_for_solve(")
solver = example("solver", "def solve(")
checker = example("checker", "def check(")
replay = example("replay", "def replay(")
approval = example("approve", "def prepare_approval(")


def tiny_fixture(durations=(60, 60), now="18:00", due="20:00"):
    """One machine, one operation per job; explicit committed release times."""
    jobs, base = [], []
    start = proto.hm(now)
    for i, duration in enumerate(durations, 1):
        jid = f"J{i}"
        jobs.append({"id": jid, "customer": f"Customer {i}", "due": due, "priority": 1,
                     "ops": [{"op": 1, "eligible": {"M1": duration}}]})
        base.append({"job": jid, "op": 1, "machine": "M1", "start": proto.fmt(start), "end": proto.fmt(start + duration)})
        start += duration
    return {"now": now, "shift": {"start": "08:00", "end": "18:00", "overtime_until": "20:00", "overtime_cost_per_hour": 45},
            "machines": [{"id": "M1", "name": "Mill M1", "aliases": []}], "jobs": jobs, "committed_schedule": base}


def constraint(cid, kind, **params):
    return {"id": cid, "type": kind, "params": params, "status": "accepted"}


class PlanningRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = json.loads((PLAN / "mocks/factory.json").read_text())
        cls.constraints = json.loads((PLAN / "mocks/extract.json").read_text())["constraints"]

    def test_nominal_demo_and_independent_checker(self):
        result = solver.solve(self.factory, self.constraints, reroute=True, overtime=False)
        self.assertIn(result["status"], {"OPTIMAL", "FEASIBLE"})
        self.assertTrue(checker.check(self.factory, self.constraints, result["schedule"])["valid"])
        self.assertLessEqual(max(proto.hm(a["end"]) for a in result["schedule"] if a["job"] == "J7"), proto.hm("16:00"))
        keep = solver.solve(self.factory, self.constraints, reroute=False, overtime=True)
        self.assertEqual(keep["status"], "INFEASIBLE")
        self.assertEqual(keep["hard_due_in_conflict"], ["c2"])

    def test_accept_cannot_bypass_missing_fields(self):
        c = json.loads((PLAN / "mocks/extract_review.json").read_text())["constraints"][0]
        c["status"] = "accepted"
        with self.assertRaises(ValueError):
            solver.solve(self.factory, [c], True, True)
        self.assertFalse(checker.check(self.factory, [c], self.factory["committed_schedule"])["valid"])

    def test_accept_cannot_bypass_unknown_id_or_missing_repair(self):
        for updates in ({"machine": "Mill 4"}, {"until": None}):
            c = deepcopy(self.constraints[0])
            c["params"].update(updates)
            c["status"] = "accepted"
            with self.assertRaises(ValueError):
                validate.validate_for_solve(self.factory, [c])

    def test_clock_minutes_and_missing_times_are_rejected(self):
        for value in (None, "09:99", "24:00", "9:00", "-1:00", "after lunch"):
            self.assertFalse(validate.valid_time(value, self.factory))
            with self.assertRaises(ValueError):
                timeutil.hm(value)
            with self.assertRaises(ValueError):
                proto.hm(value)

    def test_contradictory_dates_cannot_be_accepted(self):
        cs = [constraint("d1", "due_date", job="J7", time="15:00", hard=True),
              constraint("d2", "due_date", job="J7", time="16:00", hard=True)]
        with self.assertRaises(ValueError):
            validate.validate_for_solve(self.factory, cs)

    def test_status_cannot_clear_a_blocking_review(self):
        c = deepcopy(self.constraints[0])
        c.update(status="accepted", blocking_issues=["Confirm the explicit outage start"])
        with self.assertRaises(ValueError):
            validate.validate_for_solve(self.factory, [c])

    def test_overtime_cutoff_enforced_by_solver_and_checker(self):
        f = tiny_fixture()
        cs = [constraint("ot", "overtime", allowed=True, until="18:30")]
        self.assertEqual(solver.solve(f, cs, True, True)["status"], "INFEASIBLE")
        self.assertFalse(checker.check(f, cs, f["committed_schedule"])["valid"])
        status, _ = proto.solve(f, proto.hm(f["now"]), {}, {}, True, True,
                                baseline=f["committed_schedule"], overtime_until="18:30")
        self.assertEqual(status, "INFEASIBLE")

    def test_overtime_cutoff_boundary_is_valid(self):
        f = tiny_fixture((30,))
        cs = [constraint("ot", "overtime", allowed=True, until="18:30")]
        result = solver.solve(f, cs, True, True)
        self.assertEqual(result["status"], "OPTIMAL")
        self.assertEqual(result["schedule"][0]["end"], "18:30")
        self.assertTrue(checker.check(f, cs, result["schedule"])["valid"])

    def test_policy_cannot_enable_unaccepted_overtime(self):
        f = tiny_fixture()
        for cs in ([], [constraint("ot", "overtime", allowed=False)]):
            self.assertEqual(solver.solve(f, cs, True, True)["status"], "INFEASIBLE")

    def test_overtime_uses_occupied_minutes_and_hourly_rate(self):
        f = tiny_fixture()
        cs = [constraint("ot", "overtime", allowed=True, until="20:00")]
        result = solver.solve(f, cs, True, True)
        self.assertEqual(result["status"], "OPTIMAL")
        self.assertEqual(result["overtime_minutes"], 120)
        self.assertEqual(result["overtime_cost"], 90)
        expected_score = sum(proto.hm(a["end"]) for a in result["schedule"]) + 90
        self.assertEqual(result["objective"], expected_score)
        required = approval.required_concessions(f, cs, result["schedule"])
        self.assertEqual(required[0]["type"], "overtime")
        self.assertEqual(required[0]["minutes"], 120)
        self.assertEqual(required[0]["cost"], 90)

    def test_hard_date_updates_tardiness_as_well_as_bound(self):
        f = tiny_fixture((120, 120), now="08:00", due="12:00")
        f["jobs"][0].update(due="10:00", priority=3)
        cs = [constraint("d1", "due_date", job="J1", time="12:00", hard=True),
              constraint("d2", "due_date", job="J2", time="10:00", hard=False)]
        result = solver.solve(f, cs, True, False)
        ends = {a["job"]: a["end"] for a in result["schedule"]}
        self.assertEqual(ends, {"J1": "12:00", "J2": "10:00"})
        self.assertEqual(approval.required_concessions(f, cs, result["schedule"]), [])
        # The older fixture-only prototype also uses new hard dates in its objective.
        f["jobs"][1]["due"] = "10:00"
        status, schedule = proto.solve(f, proto.hm("08:00"), {}, {"J1": proto.hm("12:00")}, True, False,
                                       baseline=f["committed_schedule"], w_move=1)
        self.assertEqual(status, "OPTIMAL")
        self.assertEqual({a["job"]: a["end"] for a in schedule}, ends)

    def test_multiple_outages_do_not_overwrite_each_other(self):
        f = tiny_fixture((60,), now="10:00", due="18:00")
        cs = [constraint("a", "machine_down", machine="M1", **{"from": "10:00", "until": "11:00"}),
              constraint("b", "machine_down", machine="M1", **{"from": "10:30", "until": "12:00"})]
        result = solver.solve(f, cs, True, False)
        self.assertEqual(result["schedule"][0]["start"], "12:00")
        self.assertTrue(checker.check(f, cs, result["schedule"])["valid"])

    def test_replay_preserves_future_release_and_zero_noise_identity(self):
        schedule = [{"job": "J1", "op": 1, "machine": "M1", "start": "12:00", "end": "13:00"}]
        for module in (replay, replay_proto):
            sim, _ = module.replay(schedule, {"J1": "14:00"}, proto.hm("10:00"), {}, n=20,
                                   spread=(1, 1), repair_extra_max=0)
            np.testing.assert_array_equal(sim[0][1], np.full(20, proto.hm("12:00")))
            np.testing.assert_array_equal(sim[0][2], np.full(20, proto.hm("13:00")))

    def test_running_work_never_finishes_before_now(self):
        schedule = [{"job": "J1", "op": 1, "machine": "M1", "start": "08:00", "end": "10:01"}]
        for module in (replay, replay_proto):
            sim, _ = module.replay(schedule, {"J1": "11:00"}, proto.hm("10:00"), {}, n=500, seed=7)
            self.assertTrue((sim[0][2] > proto.hm("10:00")).all())
            self.assertTrue((sim[0][1] == proto.hm("08:00")).all())

    def test_zero_noise_demo_and_repeatable_samples(self):
        schedule = json.loads((PLAN / "mocks/solve.json").read_text())["alternatives"][0]["schedule"]
        due = {j["id"]: j["due"] for j in self.factory["jobs"]}
        args = (schedule, due, proto.hm(self.factory["now"]), {"M2": ("10:00", "14:00")})
        sim, _ = replay.replay(*args, n=10, spread=(1, 1), repair_extra_max=0)
        for a, starts, ends in sim:
            self.assertTrue((starts == proto.hm(a["start"])).all())
            self.assertTrue((ends == proto.hm(a["end"])).all())
        _, late1 = replay.replay(*args, seed=7)
        _, late2 = replay.replay(*args, seed=7)
        for job in due:
            np.testing.assert_array_equal(late1[job], late2[job])

    def test_prototype_replay_matches_guide_example(self):
        source = next(block for block in BLOCKS if "def replay(" in block)
        guide_ast = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "replay")
        proto_ast = next(n for n in ast.parse((PLAN / "prototype/replay_proto.py").read_text()).body
                         if isinstance(n, ast.FunctionDef) and n.name == "replay")
        self.assertEqual(ast.dump(guide_ast), ast.dump(proto_ast))

    def approval_run(self):
        solved = json.loads((PLAN / "mocks/solve.json").read_text())
        alternative = deepcopy(solved["alternatives"][0])
        return {"run_id": solved["run_id"], "fixture": deepcopy(self.factory), "constraints": deepcopy(self.constraints),
                "alternatives": {alternative["id"]: alternative}, "replays": {alternative["id"]: {"samples": 500}}}

    def approval_body(self, run):
        return {"run_id": run["run_id"], "alternative_id": "alt_reroute", "approved_concessions": ["k1"], "approver": "Supervisor"}

    def test_approval_derives_missing_concessions_from_server_schedule(self):
        run = self.approval_run()
        run["alternatives"]["alt_reroute"]["concessions"] = []
        body = self.approval_body(run)
        body["approved_concessions"] = []
        with self.assertRaises(ValueError):
            approval.prepare_approval(run, body)

    def test_approval_rejects_client_schedule_constraints_and_replay(self):
        run = self.approval_run()
        for key, value in (("alternative", {"concessions": []}), ("constraints", []), ("replay_summary", {"samples": 100000})):
            body = {**self.approval_body(run), key: value}
            with self.assertRaises(ValueError):
                approval.prepare_approval(run, body)

    def test_approval_rechecks_stored_plan(self):
        run = self.approval_run()
        run["alternatives"]["alt_reroute"]["schedule"][0]["machine"] = "nonexistent"
        with self.assertRaises(ValueError):
            approval.prepare_approval(run, self.approval_body(run))

    def test_valid_approval_exports_canonical_inputs(self):
        run = self.approval_run()
        result = approval.prepare_approval(run, self.approval_body(run))
        self.assertEqual(result["concessions"][0]["job"], "J2")
        self.assertEqual(result["replay"], {"samples": 500})
        self.assertTrue(result["checker"]["valid"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
