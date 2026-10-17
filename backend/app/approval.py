"""Pure approval rules and exports. Browser/cached plan fields are never authority."""

from __future__ import annotations

from copy import deepcopy
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import io
import re
from typing import Any

from .checker import check


class ApprovalError(Exception):
    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status

    def response(self) -> dict:
        return {"error": {"code": self.code, "message": self.message, "retryable": False}}


def validate_request(body: Any) -> dict:
    fields = {"run_id", "alternative_id", "approved_concessions", "approver"}
    if not isinstance(body, dict) or set(body) != fields:
        raise ApprovalError("invalid_approval", "Approval accepts only run_id, alternative_id, approved_concessions and approver; plan data comes from the server.")
    for field in ("run_id", "alternative_id"):
        if not isinstance(body[field], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", body[field]):
            raise ApprovalError("invalid_approval", f"{field} must be a valid stored identifier.")
    if not isinstance(body["approver"], str) or not 1 <= len(body["approver"].strip()) <= 120:
        raise ApprovalError("invalid_approval", "Enter an approver name (1–120 characters).")
    approved = body["approved_concessions"]
    if not isinstance(approved, list) or any(not isinstance(cid, str) or not cid for cid in approved):
        raise ApprovalError("invalid_approval", "approved_concessions must be a list of concession IDs.")
    if len(approved) != len(set(approved)):
        raise ApprovalError("invalid_approval", "Each concession ID may be approved only once.")
    return {**body, "approver": body["approver"].strip(), "approved_concessions": sorted(approved)}


def _minutes(value: str) -> int:
    return int(value[:2]) * 60 + int(value[3:])


def _derive_concessions(fixture: dict, constraints: list, schedule: list) -> list[dict]:
    due = {job["id"]: job["due"] for job in fixture["jobs"]}
    for constraint in constraints:
        if constraint.get("status") in ("ok", "accepted") and constraint["type"] == "due_date":
            due[constraint["params"]["job"]] = constraint["params"]["time"]
    concessions = []
    for job in sorted(fixture["jobs"], key=lambda item: item["id"]):
        finish = max(row["end"] for row in schedule if row["job"] == job["id"])
        late = _minutes(finish) - _minutes(due[job["id"]])
        if late > 0:
            customer = job.get("customer", job["id"])
            concessions.append({"id": f"k{len(concessions) + 1}", "type": "late_delivery", "job": job["id"],
                                "detail": f"{job['id']} ({customer}) ships {late} min late"})
    shift_end = _minutes(fixture["shift"]["end"])
    occupied = sum(max(0, _minutes(row["end"]) - max(_minutes(row["start"]), shift_end)) for row in schedule)
    if occupied:
        rate = fixture["shift"].get("overtime_cost_per_hour")
        try:
            if isinstance(rate, bool) or not isinstance(rate, (int, float)):
                raise ValueError
            hourly = Decimal(str(rate))
            if not hourly.is_finite() or hourly < 0:
                raise ValueError
            cost = (hourly * occupied / 60).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (ValueError, InvalidOperation):
            raise ApprovalError("invalid_stored_run", "The stored fixture needs a valid nonnegative overtime cost per hour.") from None
        concessions.append({"id": f"k{len(concessions) + 1}", "type": "overtime", "minutes": occupied, "cost": float(cost),
                            "detail": f"{occupied} machine-minutes overtime"})
    return concessions


def required_concessions(fixture: dict, constraints: list, schedule: list) -> list[dict]:
    """Shared by alternative cards and approval; derive only from a checked plan."""
    checked = check(fixture, constraints, schedule)
    if not checked["valid"]:
        raise ApprovalError("schedule_invalid", "Stored schedule failed re-check: " + "; ".join(checked["violations"]))
    return _derive_concessions(fixture, constraints, schedule)


def dispatch_rows(fixture: dict, constraints: list, schedule: list) -> list[dict]:
    """Recompute change annotations instead of trusting cached labels."""
    base = {(row["job"], row["op"]): row for row in fixture["committed_schedule"]}
    now = _minutes(fixture["now"])
    downs = [c["params"] for c in constraints if c.get("status") in ("ok", "accepted") and c["type"] == "machine_down"]
    rows, sequence = [], {}
    for operation in sorted(schedule, key=lambda row: (row["machine"], row["start"], row["end"], row["job"], row["op"])):
        original = base[operation["job"], operation["op"]]
        bs, be = _minutes(original["start"]), _minutes(original["end"])
        interrupted = bs < now < be and any(
            down["machine"] == original["machine"] and bs < _minutes(down["until"]) and be > _minutes(down.get("from", fixture["now"]))
            for down in downs)
        if bs < now and not interrupted:
            change = "frozen"
        elif interrupted:
            change = "restarted" if operation["machine"] == original["machine"] else f"restarted_on_{operation['machine']}"
        elif operation["machine"] != original["machine"]:
            change = f"moved_from_{original['machine']}"
        elif (operation["start"], operation["end"]) != (original["start"], original["end"]):
            change = "retimed"
        else:
            change = "none"
        machine = operation["machine"]
        sequence[machine] = sequence.get(machine, 0) + 1
        rows.append({"machine": machine, "sequence": sequence[machine], "job": operation["job"], "op": operation["op"],
                     "start": operation["start"], "end": operation["end"], "changed": change})
    return rows


def build_approval(run: dict, body: dict, approved_at: datetime) -> dict:
    """Use an immutable server snapshot; caller provides locking and idempotency."""
    body = validate_request(body)
    if body["run_id"] != run.get("run_id"):
        raise ApprovalError("invalid_approval", "Run ID does not match the stored snapshot.")
    alternatives = run.get("alternatives", {})
    alternative = alternatives.get(body["alternative_id"])
    if alternative is None:
        raise ApprovalError("alternative_not_found", "The selected alternative is not in this run. Choose a recovery plan again.", 404)
    fixture, constraints, schedule = run["fixture"], run["constraints"], alternative["schedule"]
    checked = check(fixture, constraints, schedule)
    if not checked["valid"]:
        raise ApprovalError("schedule_invalid", "Stored schedule failed re-check: " + "; ".join(checked["violations"]))
    policy = alternative.get("policy", {})
    if not isinstance(policy, dict) or any(type(policy.get(field)) is not bool for field in ("reroute", "overtime")):
        raise ApprovalError("invalid_stored_run", "The stored alternative needs explicit reroute and overtime policies.")
    if alternative.get("relaxed_constraints") or alternative.get("relaxed_constraint_ids") or policy.get("relax_hard_due"):
        raise ApprovalError("unsupported_relaxation", "Hard due-date relaxation is not supported by approval.")
    concessions = _derive_concessions(fixture, constraints, schedule)
    originals = {(row["job"], row["op"]): row for row in fixture["committed_schedule"]}
    if not policy["reroute"] and any(row["machine"] != originals[row["job"], row["op"]]["machine"] for row in schedule):
        raise ApprovalError("policy_violation", "The stored schedule moves work although its policy forbids re-routing.")
    if not policy["overtime"] and any(item["type"] == "overtime" for item in concessions):
        raise ApprovalError("policy_violation", "The stored schedule uses overtime although its policy forbids it.")
    if set(body["approved_concessions"]) != {item["id"] for item in concessions}:
        required = "; ".join(f"{item['id']}: {item['detail']}" for item in concessions) or "none"
        raise ApprovalError("concessions_required", f"Approve exactly the required tradeoffs from the stored plan: {required}.")
    if approved_at.tzinfo is None or approved_at.utcoffset() is None:
        raise ValueError("approved_at must include a timezone")
    rows = dispatch_rows(fixture, constraints, schedule)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=["machine", "sequence", "job", "op", "start", "end", "changed"], lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    decision = {
        "run_id": run["run_id"], "approved_at": approved_at.isoformat(timespec="seconds"), "approver": body["approver"],
        "message": run["message"], "constraints": deepcopy(constraints), "alternative_id": alternative["id"],
        "concessions": concessions, "checker": checked, "amd_trace": deepcopy(run.get("trace")),
        "replay": deepcopy(run.get("replays", {}).get(alternative["id"])),
        "data_notice": run.get("data_notice", "Synthetic demo data"),
        "fixture": deepcopy(fixture), "schedule": [{**{key: row[key] for key in ("machine", "job", "op", "start", "end")}, "change": row["changed"]} for row in rows],
        "policy": deepcopy(alternative.get("policy", {})),
    }
    return {"dispatch_csv": output.getvalue(), "decision_record": decision}
