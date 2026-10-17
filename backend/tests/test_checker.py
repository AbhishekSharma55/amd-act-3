"""Counterexamples and trust-boundary checks for the independent checker."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.app.checker import check
from backend.app import checker_report


ROOT = Path(__file__).resolve().parents[2]


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def constraint(kind, params, cid="test", **changes):
    item = {"id": cid, "type": kind, "params": params, "status": "accepted",
            "source_span": "Reviewed synthetic test input", "origin": "user",
            "blocking_issues": [], "issues": []}
    item.update(changes)
    return item


def operation(schedule, job, op):
    return next(row for row in schedule if (row["job"], row["op"]) == (job, op))


def small_fixture(start="09:55", end="10:05", now="10:00"):
    return {"now": now, "shift": {"start": "08:00", "end": "18:00", "overtime_until": "20:00"},
            "machines": [{"id": "M1"}, {"id": "M2"}],
            "jobs": [{"id": "A", "due": "18:00", "priority": 1,
                      "ops": [{"op": 1, "eligible": {"M1": 10, "M2": 15}}]}],
            "committed_schedule": [{"job": "A", "op": 1, "machine": "M1", "start": start, "end": end}]}


class CheckerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load("shared/fixture.json")
        self.constraints = load("shared/mocks/extract.json")["constraints"]
        self.recovery = load("shared/mocks/solve.json")["alternatives"][0]["schedule"]
        self.schedule = deepcopy(self.fixture["committed_schedule"])

    def assertViolation(self, result, *fragments):
        self.assertIs(result["valid"], False, result)
        self.assertTrue(result["violations"], result)
        for fragment in fragments:
            self.assertTrue(any(fragment in item for item in result["violations"]), (fragment, result))

    def test_committed_and_recovery_plans_pass(self):
        self.assertEqual(check(self.fixture, [], self.schedule), {"valid": True, "violations": []})
        self.assertEqual(check(self.fixture, self.constraints, self.recovery), {"valid": True, "violations": []})

    def test_inputs_are_not_mutated(self):
        values = self.fixture, self.constraints, self.recovery
        before = deepcopy(values)
        check(*values)
        self.assertEqual(values, before)

    def test_original_plan_fails_new_outages(self):
        self.assertViolation(check(self.fixture, self.constraints, self.schedule), "J1 op 2 starts in the past", "J1 op 2 overlaps outage", "J2 op 1 overlaps outage", "J7 op 2 overlaps outage")

    def test_machine_overlap_is_reported(self):
        operation(self.schedule, "J4", 2).update(start="10:10", end="11:40")
        self.assertViolation(check(self.fixture, [], self.schedule), "overlap on M1")

    def test_all_nested_machine_overlaps_are_reported(self):
        fixture = small_fixture(start="12:00", end="13:00")
        fixture["jobs"][0]["ops"][0]["eligible"] = {"M1": 60}
        for jid, start, end in (("B", "13:00", "13:10"), ("C", "13:10", "13:20")):
            fixture["jobs"].append({"id": jid, "due": "18:00", "priority": 1, "ops": [{"op": 1, "eligible": {"M1": 10}}]})
            fixture["committed_schedule"].append({"job": jid, "op": 1, "machine": "M1", "start": start, "end": end})
        schedule = deepcopy(fixture["committed_schedule"])
        schedule[1].update(start="12:10", end="12:20")
        schedule[2].update(start="12:30", end="12:40")
        result = check(fixture, [], schedule)
        overlaps = [item for item in result["violations"] if "overlap on M1" in item]
        self.assertEqual(len(overlaps), 2, result)
        self.assertTrue(any("A op 1 and C op 1" in item for item in overlaps), result)

    def test_precedence_is_reported(self):
        operation(self.schedule, "J7", 3).update(start="11:00", end="11:30")
        self.assertViolation(check(self.fixture, [], self.schedule), "J7 op 3 starts before op 2 ends")

    def test_precedence_uses_fixture_order_not_operation_number(self):
        fixture = small_fixture(start="10:00", end="10:10")
        fixture["jobs"][0]["ops"] = [{"op": 2, "eligible": {"M1": 10}}, {"op": 1, "eligible": {"M1": 10}}]
        fixture["committed_schedule"] = [{"job": "A", "op": 2, "machine": "M1", "start": "10:00", "end": "10:10"},
                                         {"job": "A", "op": 1, "machine": "M1", "start": "10:10", "end": "10:20"}]
        self.assertTrue(check(fixture, [], fixture["committed_schedule"])["valid"])
        schedule = deepcopy(fixture["committed_schedule"])
        schedule[1].update(start="10:00", end="10:10")
        self.assertViolation(check(fixture, [], schedule), "A op 1 starts before op 2 ends")

    def test_frozen_work_cannot_move(self):
        operation(self.schedule, "J3", 1).update(machine="M2", end="08:50")
        self.assertViolation(check(self.fixture, [], self.schedule), "J3 op 1 is frozen")

    def test_machine_eligibility_and_machine_specific_duration(self):
        operation(self.schedule, "J4", 1)["machine"] = "M1"
        self.assertViolation(check(self.fixture, [], self.schedule), "J4 op 1 is on ineligible machine M1")
        operation(self.recovery, "J1", 2)["end"] = "11:00"
        self.assertViolation(check(self.fixture, self.constraints, self.recovery), "J1 op 2 duration 50 != 70 minutes on M1")

    def test_hard_due_date_fails_and_soft_due_does_not(self):
        item = constraint("due_date", {"job": "J7", "time": "13:54", "hard": True})
        self.assertViolation(check(self.fixture, [item], self.schedule), "hard due date test missed: J7 ends 13:55, due 13:54")
        item["params"]["hard"] = False
        self.assertTrue(check(self.fixture, [item], self.schedule)["valid"])

    def test_shift_and_accepted_overtime_cutoff(self):
        row = operation(self.schedule, "J4", 2)
        row.update(start="17:01", end="18:31")
        self.assertViolation(check(self.fixture, [], self.schedule), "after allowed end 18:00")
        overtime = constraint("overtime", {"allowed": True, "until": "18:30"})
        self.assertViolation(check(self.fixture, [overtime], self.schedule), "ends 18:31 after allowed end 18:30")
        row.update(start="17:00", end="18:30")
        self.assertTrue(check(self.fixture, [overtime], self.schedule)["valid"])

    def test_overtime_defaults_to_fixture_limit_and_combines_cutoffs(self):
        operation(self.schedule, "J4", 2).update(start="17:01", end="18:31")
        self.assertTrue(check(self.fixture, [constraint("overtime", {"allowed": True})], self.schedule)["valid"])
        items = [constraint("overtime", {"allowed": True, "until": "19:00"}, "wide"),
                 constraint("overtime", {"allowed": True, "until": "18:30"}, "narrow")]
        self.assertViolation(check(self.fixture, items, self.schedule), "after allowed end 18:30")

    def test_overtime_false_and_true_are_contradictory_and_cannot_extend_shift(self):
        operation(self.schedule, "J4", 2).update(start="17:00", end="18:30")
        items = [constraint("overtime", {"allowed": False}, "no"), constraint("overtime", {"allowed": True}, "yes")]
        self.assertViolation(check(self.fixture, items, self.schedule), "contradicts no", "after allowed end 18:00")

    def test_overtime_cannot_exceed_fixture_or_precede_shift_end(self):
        for cutoff in ("20:01", "17:59", "", [], 1830):
            with self.subTest(cutoff=cutoff):
                self.assertFalse(check(self.fixture, [constraint("overtime", {"allowed": True, "until": cutoff})], self.schedule)["valid"])

    def test_endpoint_adjacency_is_valid_for_outage_and_machine_intervals(self):
        fixture = small_fixture(start="11:00", end="11:10")
        outage = constraint("machine_down", {"machine": "M1", "from": "10:00", "until": "11:00"})
        self.assertTrue(check(fixture, [outage], fixture["committed_schedule"])["valid"])
        outage["params"].update(**{"from": "11:10", "until": "12:00"})
        self.assertTrue(check(fixture, [outage], fixture["committed_schedule"])["valid"])
        # The committed 15-operation fixture also contains many touching machine intervals.
        self.assertTrue(check(self.fixture, [], self.schedule)["valid"])

    def test_restart_on_same_machine_waits_for_repair(self):
        fixture = small_fixture()
        outage = constraint("machine_down", {"machine": "M1", "from": "10:00", "until": "11:00"})
        row = deepcopy(fixture["committed_schedule"])
        row[0].update(start="11:00", end="11:10")
        self.assertTrue(check(fixture, [outage], row)["valid"])
        row[0].update(start="10:00", end="10:10")
        self.assertViolation(check(fixture, [outage], row), "overlaps outage")

    def test_restart_on_alternate_machine_is_full_duration_and_after_now(self):
        fixture = small_fixture()
        outage = constraint("machine_down", {"machine": "M1", "from": "10:00", "until": "11:00"})
        row = deepcopy(fixture["committed_schedule"])
        row[0].update(machine="M2", start="10:00", end="10:15")
        self.assertTrue(check(fixture, [outage], row)["valid"])
        row[0]["end"] = "10:05"
        self.assertViolation(check(fixture, [outage], row), "duration 5 != 15")
        row[0].update(start="09:59", end="10:14")
        self.assertViolation(check(fixture, [outage], row), "starts in the past")

    def test_running_work_with_outage_onset_at_or_before_its_start_requires_restart(self):
        fixture = small_fixture()
        for start in ("09:55", "09:00"):
            with self.subTest(start=start):
                outage = constraint("machine_down", {"machine": "M1", "from": start, "until": "11:00"})
                self.assertViolation(check(fixture, [outage], fixture["committed_schedule"]), "starts in the past", "overlaps outage")
                row = deepcopy(fixture["committed_schedule"])
                row[0].update(machine="M2", start="10:00", end="10:15")
                self.assertTrue(check(fixture, [outage], row)["valid"])

    def test_repair_already_completed_still_requires_full_restart_after_now(self):
        fixture = small_fixture()
        outage = constraint("machine_down", {"machine": "M1", "from": "09:56", "until": "09:59"})
        row = deepcopy(fixture["committed_schedule"])
        self.assertViolation(check(fixture, [outage], row), "starts in the past", "overlaps outage")
        row[0].update(start="10:00", end="10:10")
        self.assertTrue(check(fixture, [outage], row)["valid"])

    def test_completed_work_stays_frozen_even_when_outage_is_retroactive(self):
        for start, end in (("09:50", "10:00"), ("09:49", "09:59")):
            fixture = small_fixture(start=start, end=end)
            outage = constraint("machine_down", {"machine": "M1", "from": "09:55", "until": "11:00"})
            self.assertTrue(check(fixture, [outage], fixture["committed_schedule"])["valid"])
            row = deepcopy(fixture["committed_schedule"])
            row[0].update(machine="M2", start="10:00", end="10:15")
            self.assertViolation(check(fixture, [outage], row), "is frozen")

    def test_operation_starting_exactly_now_is_new_work(self):
        fixture = small_fixture(start="10:00", end="10:10")
        row = deepcopy(fixture["committed_schedule"])
        row[0].update(start="10:10", end="10:20")
        self.assertTrue(check(fixture, [], row)["valid"])
        row[0].update(start="09:59", end="10:09")
        self.assertViolation(check(fixture, [], row), "starts in the past")

    def test_new_work_cannot_start_before_shift(self):
        fixture = small_fixture(start="08:00", end="08:10", now="08:00")
        row = deepcopy(fixture["committed_schedule"])
        row[0].update(start="07:55", end="08:05")
        self.assertViolation(check(fixture, [], row), "starts before shift start", "starts in the past")

    def test_all_violations_are_returned_together(self):
        self.schedule.remove(operation(self.schedule, "J2", 2))
        self.schedule.append(deepcopy(operation(self.schedule, "J3", 1)))
        self.schedule.append({"job": "UNKNOWN", "op": 1})
        operation(self.schedule, "J4", 1).update(machine="M1", start="10:20", end="11:04")
        operation(self.schedule, "J4", 2).update(start="10:30", end="12:00")
        operation(self.schedule, "J5", 2).update(start="09:51", end="10:21")
        due = constraint("due_date", {"job": "J7", "time": "10:30", "hard": True})
        self.assertViolation(check(self.fixture, [due], self.schedule), "J2 op 2 is missing", "J3 op 1 is scheduled more than once", "not a fixture operation", "ineligible machine", "J5 op 2 is frozen", "precedence", "overlap on M1", "hard due date")

    def test_missing_duplicate_unknown_and_malformed_operations_are_rejected(self):
        mutations = [lambda rows: rows.pop(), lambda rows: rows.append(deepcopy(rows[0])),
                     lambda rows: rows[0].update(job="UNKNOWN"), lambda rows: rows[0].update(op=True),
                     lambda rows: rows[0].update(op=[]), lambda rows: rows[0].update(job=[]),
                     lambda rows: rows[0].update(machine=[]), lambda rows: rows.append(None),
                     lambda rows: rows[0].pop("start"), lambda rows: rows[0].update(start="09:99")]
        for mutate in mutations:
            rows = deepcopy(self.schedule)
            mutate(rows)
            with self.subTest(rows=rows):
                self.assertFalse(check(self.fixture, [], rows)["valid"])
        for rows in (None, {}, "schedule", True):
            self.assertFalse(check(self.fixture, [], rows)["valid"])

    def test_malformed_fixture_shapes_never_raise(self):
        mutations = [lambda f: f.update(now=None), lambda f: f.update(shift=[]),
                     lambda f: f["shift"].update(start="18:00"), lambda f: f.update(machines={}),
                     lambda f: f["machines"].append({"id": []}), lambda f: f["machines"].append(deepcopy(f["machines"][0])),
                     lambda f: f.update(jobs=True), lambda f: f["jobs"][0].update(id=[]),
                     lambda f: f["jobs"][0].update(ops={}), lambda f: f["jobs"][0]["ops"][0].update(op=True),
                     lambda f: f["jobs"][0]["ops"][0].update(eligible={"M3": True}),
                     lambda f: f["jobs"][0]["ops"][0].update(eligible=[]),
                     lambda f: f.update(committed_schedule=None), lambda f: f["committed_schedule"].clear()]
        for mutate in mutations:
            fixture = deepcopy(self.fixture)
            mutate(fixture)
            with self.subTest(fixture=fixture):
                self.assertFalse(check(fixture, self.constraints, self.schedule)["valid"])
        for fixture in (None, [], True, "fixture"):
            self.assertFalse(check(fixture, None, None)["valid"])

    def test_accepted_does_not_bypass_invalid_constraint_fields(self):
        invalid = [constraint("machine_down", {"machine": "UNKNOWN", "until": "14:00"}),
                   constraint("machine_down", {"machine": [], "until": "14:00"}),
                   constraint("machine_down", {"machine": "M2"}),
                   constraint("machine_down", {"machine": "M2", "from": None, "until": "14:00"}),
                   constraint("machine_down", {"machine": "M2", "from": "14:00", "until": "14:00"}),
                   constraint("machine_down", {"machine": "M2", "from": "09:99", "until": "14:00"}),
                   constraint("due_date", {"job": "UNKNOWN", "time": "16:00", "hard": True}),
                   constraint("due_date", {"job": "J7", "time": "16:00", "hard": 1}),
                   constraint("priority", {"job": "J7", "level": True}),
                   constraint("priority", {"job": "J7", "level": 4}),
                   constraint("overtime", {"allowed": "false"}),
                   constraint("unsupported", {"note": "Material shortage"}),
                   constraint([], {}), constraint("overtime", [], status="accepted"),
                   constraint("overtime", {"allowed": True}, blocking_issues=["Resolve the cutoff"]),
                   constraint("overtime", {"allowed": True}, blocking_issues={}),
                   constraint("overtime", {"allowed": True}, status="review"),
                   constraint("overtime", {"allowed": True}, status=[]),
                   constraint("overtime", {"allowed": True}, source_span=""),
                   constraint("overtime", {"allowed": True}, origin=[])]
        for item in invalid:
            with self.subTest(item=item):
                self.assertFalse(check(self.fixture, [item], self.schedule)["valid"])
        for field in ("id", "type", "params", "status", "blocking_issues", "issues", "source_span", "origin"):
            item = constraint("overtime", {"allowed": True})
            item.pop(field)
            with self.subTest(missing=field):
                self.assertFalse(check(self.fixture, [item], self.schedule)["valid"])

    def test_rejected_constraints_are_skipped_without_reading_their_invalid_fields(self):
        rejected = {"status": "rejected", "params": None, "type": [], "blocking_issues": ["unknown ID"]}
        self.assertTrue(check(self.fixture, [rejected], self.schedule)["valid"])

    def test_constraint_arrays_ids_and_contradictions(self):
        for items in (None, {}, True, [None], [[]]):
            self.assertFalse(check(self.fixture, items, self.schedule)["valid"])
        due = constraint("due_date", {"job": "J7", "time": "16:00", "hard": True})
        self.assertViolation(check(self.fixture, [due, deepcopy(due)], self.schedule), "duplicate ID")
        other = constraint("due_date", {"job": "J7", "time": "16:01", "hard": True}, "other")
        self.assertViolation(check(self.fixture, [due, other], self.schedule), "conflicting due_date")
        priorities = [constraint("priority", {"job": "J7", "level": 1}, "p1"), constraint("priority", {"job": "J7", "level": 3}, "p2")]
        self.assertViolation(check(self.fixture, priorities, self.schedule), "conflicting priority")
        other["params"] = deepcopy(due["params"])
        self.assertTrue(check(self.fixture, [due, other], self.schedule)["valid"])

    def test_multiple_outages_are_all_checked(self):
        items = [constraint("machine_down", {"machine": "M2", "from": "10:00", "until": "11:00"}, "early"),
                 constraint("machine_down", {"machine": "M2", "from": "12:00", "until": "14:00"}, "late")]
        self.assertViolation(check(self.fixture, items, self.schedule), "outage early", "outage late")


class CheckerReportTests(unittest.TestCase):
    def test_report_results_and_all_source_hashes_match_current_files(self):
        generated = checker_report.generate_report()
        self.assertTrue(generated["reports"]["committed"]["valid"])
        self.assertTrue(generated["reports"]["recovery"]["valid"])
        self.assertFalse(generated["reports"]["disrupted_committed"]["valid"])
        for source in generated["provenance"]["source_files"].values():
            self.assertEqual(source["sha256"], hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest())
        self.assertIs(generated["provenance"]["amd_request_made"], False)
        self.assertEqual(generated, checker_report.generate_report())

    def test_cli_freshness_detects_tampering_or_stale_records(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            path = Path(directory) / "reports.json"
            args = ["--output", str(path)]
            self.assertEqual(checker_report.main(args), 0)
            self.assertEqual(checker_report.main(["--check", *args]), 0)
            path.write_text(path.read_text(encoding="utf-8").replace('"valid": true', '"valid": false', 1), encoding="utf-8")
            self.assertEqual(checker_report.main(["--check", *args]), 1)

    def test_generator_refuses_unexpected_outcomes(self):
        for valid in (True, False):
            with patch.object(checker_report, "check", return_value={"valid": valid, "violations": []}):
                with self.assertRaisesRegex(ValueError, "Refusing to save unexpected"):
                    checker_report.generate_report()


if __name__ == "__main__":
    unittest.main()
