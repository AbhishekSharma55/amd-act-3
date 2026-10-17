"""Independent, standard-library schedule validation; deliberately no solver imports.

The fixture and constraints are untrusted inputs here. A client-set ``accepted``
status never replaces structural validation. Source-span meaning/matching needs
the stored extraction message and remains the extraction layer's responsibility.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


_CLOCK = re.compile(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]\Z")


def _time(value: Any) -> int | None:
    if not isinstance(value, str) or not _CLOCK.fullmatch(value):
        return None
    return int(value[:2]) * 60 + int(value[3:])


def _clock(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


def _identifier(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _key(row: dict) -> tuple[str, int] | None:
    if _identifier(row.get("job")) and type(row.get("op")) is int and row["op"] > 0:
        return row["job"], row["op"]
    return None


def _name(key: tuple[str, int]) -> str:
    return f"{key[0]} op {key[1]}"


@dataclass(frozen=True)
class _Operation:
    key: tuple[str, int]
    machine: str
    start: int
    end: int


def _schedule(value: Any, label: str, expected: dict, machines: set[str], violations: list[str]) -> list[_Operation]:
    """Parse every row, retaining duplicates so they cannot hide other violations."""
    if not isinstance(value, list):
        violations.append(f"{label} must be an array of operation objects")
        return []
    seen: set[tuple[str, int]] = set()
    parsed: list[_Operation] = []
    for index, row in enumerate(value):
        prefix = f"{label}[{index}]"
        if not isinstance(row, dict):
            violations.append(f"{prefix} must be an operation object")
            continue
        key = _key(row)
        if key is None:
            violations.append(f"{prefix} needs a job ID and a positive integer op (booleans are invalid)")
            continue
        if key not in expected:
            violations.append(f"{prefix}: {_name(key)} is not a fixture operation")
            continue
        if key in seen:
            violations.append(f"{label}: {_name(key)} is scheduled more than once")
        seen.add(key)
        machine = row.get("machine")
        valid_machine = isinstance(machine, str) and machine in machines
        if not valid_machine:
            violations.append(f"{prefix}: {_name(key)} needs a known machine ID")
        start, end = _time(row.get("start")), _time(row.get("end"))
        if start is None or end is None:
            violations.append(f"{prefix}: {_name(key)} has invalid times; use HH:MM (00:00–23:59)")
        if not valid_machine or start is None or end is None:
            continue
        if start >= end:
            violations.append(f"{prefix}: {_name(key)} must start before it ends")
        if machine not in expected[key]:
            violations.append(f"{label}: {_name(key)} is on ineligible machine {machine}")
        elif end - start != expected[key][machine]:
            violations.append(f"{label}: {_name(key)} duration {end - start} != {expected[key][machine]} minutes on {machine}")
        parsed.append(_Operation(key, machine, start, end))
    for key in expected:
        if key not in seen:
            violations.append(f"{label}: {_name(key)} is missing")
    return parsed


def _fixture(value: Any, violations: list[str]) -> dict | None:
    if not isinstance(value, dict):
        violations.append("fixture must be an object")
        return None
    now = _time(value.get("now"))
    if now is None:
        violations.append("fixture.now must be a valid HH:MM time")
    shift = value.get("shift")
    if not isinstance(shift, dict):
        violations.append("fixture.shift must be an object")
        shift = {}
    shift_start = _time(shift.get("start"))
    shift_end = _time(shift.get("end"))
    maximum = _time(shift.get("overtime_until", shift.get("end")))
    if shift_start is None or shift_end is None or maximum is None:
        violations.append("fixture.shift start, end and overtime_until must be valid HH:MM times")
    elif not shift_start < shift_end <= maximum:
        violations.append("fixture.shift must satisfy start < end <= overtime_until")
    if now is not None and shift_start is not None and maximum is not None and not shift_start <= now <= maximum:
        violations.append("fixture.now must be inside the working day")

    machines: set[str] = set()
    machine_rows = value.get("machines")
    if not isinstance(machine_rows, list) or not machine_rows:
        violations.append("fixture.machines must be a non-empty array")
        machine_rows = []
    for index, machine in enumerate(machine_rows):
        if not isinstance(machine, dict) or not _identifier(machine.get("id")):
            violations.append(f"fixture.machines[{index}] needs a machine ID")
        elif machine["id"] in machines:
            violations.append(f"fixture has duplicate machine {machine['id']}")
        else:
            machines.add(machine["id"])

    expected: dict[tuple[str, int], dict[str, int]] = {}
    ordered: dict[str, list[tuple[str, int]]] = {}
    jobs = value.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        violations.append("fixture.jobs must be a non-empty array")
        jobs = []
    for index, job in enumerate(jobs):
        if not isinstance(job, dict) or not _identifier(job.get("id")):
            violations.append(f"fixture.jobs[{index}] needs a job ID")
            continue
        jid = job["id"]
        if jid in ordered:
            violations.append(f"fixture has duplicate job {jid}")
            continue
        ordered[jid] = []
        if _time(job.get("due")) is None:
            violations.append(f"fixture {jid}.due must be a valid HH:MM time")
        if type(job.get("priority")) is not int or job["priority"] not in (1, 2, 3):
            violations.append(f"fixture {jid}.priority must be an integer from 1 to 3")
        ops = job.get("ops")
        if not isinstance(ops, list) or not ops:
            violations.append(f"fixture {jid}.ops must be a non-empty array")
            continue
        for operation in ops:
            if not isinstance(operation, dict) or type(operation.get("op")) is not int or operation["op"] <= 0:
                violations.append(f"fixture {jid} needs positive integer operation numbers")
                continue
            key = jid, operation["op"]
            if key in expected:
                violations.append(f"fixture has duplicate {_name(key)}")
                continue
            eligible = operation.get("eligible")
            if not isinstance(eligible, dict) or not eligible:
                violations.append(f"fixture {_name(key)} needs eligible machines and durations")
                eligible = {}
            valid_eligible = {}
            for machine, duration in eligible.items():
                if not isinstance(machine, str) or machine not in machines:
                    violations.append(f"fixture {_name(key)} references an unknown eligible machine")
                elif type(duration) is not int or duration <= 0:
                    violations.append(f"fixture {_name(key)} duration on {machine} must be a positive integer")
                else:
                    valid_eligible[machine] = duration
            expected[key] = valid_eligible
            ordered[jid].append(key)

    baseline = _schedule(value.get("committed_schedule"), "fixture.committed_schedule", expected, machines, violations)
    base = {}
    for row in baseline:
        base.setdefault(row.key, row)
        if shift_start is not None and row.start < shift_start:
            violations.append(f"fixture.committed_schedule: {_name(row.key)} starts before the shift")
        if maximum is not None and row.end > maximum:
            violations.append(f"fixture.committed_schedule: {_name(row.key)} ends beyond the fixture limit")
    return {"now": now, "start": shift_start, "end": shift_end, "maximum": maximum,
            "machines": machines, "expected": expected, "ordered": ordered, "base": base}


def _constraints(value: Any, context: dict, violations: list[str]) -> list[dict]:
    if not isinstance(value, list):
        violations.append("constraints must be an array")
        return []
    seen: set[str] = set()
    accepted = []
    for index, item in enumerate(value):
        prefix = f"constraint[{index}]"
        before = len(violations)
        if not isinstance(item, dict):
            violations.append(f"{prefix} must be an object")
            continue
        if item.get("status") == "rejected":
            continue
        cid = item.get("id")
        if not _identifier(cid):
            violations.append(f"{prefix} needs a non-empty ID")
        else:
            prefix = f"constraint {cid}"
            if cid in seen:
                violations.append(f"{prefix} has a duplicate ID")
            seen.add(cid)
        if item.get("status") not in ("ok", "accepted"):
            violations.append(f"{prefix} has unresolved status; correct or reject it before checking")
        blocking = item.get("blocking_issues")
        if not isinstance(blocking, list) or any(not isinstance(issue, str) for issue in blocking):
            violations.append(f"{prefix}.blocking_issues must be an array of strings")
        elif blocking:
            violations.append(f"{prefix} has blocking issues; acceptance does not repair them")
        issues = item.get("issues")
        if not isinstance(issues, list) or any(not isinstance(issue, str) for issue in issues):
            violations.append(f"{prefix}.issues must be an array of strings")
        if not _identifier(item.get("source_span")):
            violations.append(f"{prefix} needs a non-empty source_span")
        if item.get("origin") not in ("amd_model", "rule_fallback", "user"):
            violations.append(f"{prefix} needs a supported origin")
        params = item.get("params")
        if not isinstance(params, dict):
            violations.append(f"{prefix}.params must be an object")
            continue
        kind = item.get("type")
        normalized: dict = {"id": cid, "type": kind}

        def working_time(field: str, supplied: Any) -> int | None:
            minutes = _time(supplied)
            start, limit = context["start"], context["maximum"]
            if minutes is None or (start is not None and minutes < start) or (limit is not None and minutes > limit):
                violations.append(f"{prefix}: {field} must be HH:MM inside the working day")
                return None
            return minutes

        if kind == "machine_down":
            machine = params.get("machine")
            if not isinstance(machine, str) or machine not in context["machines"]:
                violations.append(f"{prefix} needs a known machine ID")
            default_start = _clock(context["now"]) if context["now"] is not None else None
            start = working_time("from", params.get("from", default_start))
            end = working_time("until", params.get("until"))
            if start is not None and end is not None and start >= end:
                violations.append(f"{prefix}: outage end must be after its start")
            normalized.update(machine=machine, start=start, end=end)
        elif kind == "due_date":
            job = params.get("job")
            if not isinstance(job, str) or job not in context["ordered"]:
                violations.append(f"{prefix} needs a known job ID")
            due = working_time("time", params.get("time"))
            if type(params.get("hard")) is not bool:
                violations.append(f"{prefix}: hard must be a boolean")
            normalized.update(job=job, due=due, hard=params.get("hard"))
        elif kind == "priority":
            job = params.get("job")
            if not isinstance(job, str) or job not in context["ordered"]:
                violations.append(f"{prefix} needs a known job ID")
            if type(params.get("level")) is not int or params["level"] not in (1, 2, 3):
                violations.append(f"{prefix}: priority level must be an integer from 1 to 3")
            normalized.update(job=job, level=params.get("level"))
        elif kind == "overtime":
            if type(params.get("allowed")) is not bool:
                violations.append(f"{prefix}: allowed must be a boolean")
            until = params.get("until")
            cutoff = context["maximum"] if until is None else working_time("until", until)
            if cutoff is not None and context["end"] is not None and cutoff < context["end"]:
                violations.append(f"{prefix}: overtime cutoff cannot precede shift end")
            normalized.update(allowed=params.get("allowed"), cutoff=cutoff)
        else:
            violations.append(f"{prefix} has an unsupported constraint type")
        if len(violations) == before:
            accepted.append(normalized)

    singletons = {}
    for item in accepted:
        kind = item["type"]
        if kind not in ("due_date", "priority", "overtime"):
            continue
        key = kind, item.get("job")
        semantics = tuple(item.get(field) for field in {"due_date": ("due", "hard"), "priority": ("level",), "overtime": ("allowed",)}[kind])
        if key in singletons and singletons[key][0] != semantics:
            violations.append(f"constraint {item['id']} contradicts {singletons[key][1]}: conflicting {kind} constraints")
        else:
            singletons[key] = semantics, item["id"]
    return accepted


def check(fixture: Any, constraints: Any, schedule: Any) -> dict[str, Any]:
    """Return ``{valid, violations}`` without mutating inputs or importing a solver.

    Checks the contract's one-day, non-preemptive, restart-only model. It checks
    accepted constraints, not a solver policy or human concession approval.
    Malformed JSON-shaped inputs produce violations, never a positive result.
    """
    violations: list[str] = []
    context = _fixture(fixture, violations)
    if context is None:
        if not isinstance(constraints, list):
            violations.append("constraints must be an array")
        if not isinstance(schedule, list):
            violations.append("schedule must be an array of operation objects")
        return {"valid": False, "violations": violations}
    accepted = _constraints(constraints, context, violations)
    rows = _schedule(schedule, "schedule", context["expected"], context["machines"], violations)
    downs = [item for item in accepted if item["type"] == "machine_down"]
    allowed_ot = [item["cutoff"] for item in accepted if item["type"] == "overtime" and item["allowed"]]
    forbidden_ot = any(item["type"] == "overtime" and not item["allowed"] for item in accepted)
    end_limit = context["end"]
    if allowed_ot and not forbidden_ot and context["maximum"] is not None:
        end_limit = min(context["maximum"], *allowed_ot)

    by_key: dict[tuple[str, int], list[_Operation]] = {}
    by_machine: dict[str, list[_Operation]] = {}
    for row in rows:
        by_key.setdefault(row.key, []).append(row)
        by_machine.setdefault(row.machine, []).append(row)
        name = _name(row.key)
        if context["start"] is not None and row.start < context["start"]:
            violations.append(f"{name} starts before shift start {_clock(context['start'])}")
        if end_limit is not None and row.end > end_limit:
            violations.append(f"{name} ends {_clock(row.end)} after allowed end {_clock(end_limit)}")
        base, now = context["base"].get(row.key), context["now"]
        # A completed observation stays frozen. A running operation that touches
        # an outage needs full restart, including an outage predating its start
        # or a repair already completed before now; it cannot keep working
        # through an active outage by claiming the historical/frozen exemption.
        interrupted = bool(base and now is not None and base.start < now < base.end and any(
            down["machine"] == base.machine and base.start < down["end"] and base.end > down["start"] for down in downs))
        frozen = bool(base and now is not None and base.start < now and not interrupted)
        unchanged = bool(base and (row.machine, row.start, row.end) == (base.machine, base.start, base.end))
        if frozen and not unchanged:
            violations.append(f"{name} is frozen: work started before now and must not change")
        elif not frozen and now is not None and row.start < now:
            violations.append(f"{name} starts in the past ({_clock(row.start)}); new or restarted work must start at or after now {_clock(now)}")
        for down in downs:
            if row.machine == down["machine"] and row.start < down["end"] and row.end > down["start"] and not (frozen and unchanged):
                violations.append(f"{name} overlaps outage {down['id']} on {row.machine} ({_clock(down['start'])}–{_clock(down['end'])})")

    for jid, keys in context["ordered"].items():
        for previous, following in zip(keys, keys[1:]):
            if any(right.start < left.end for left in by_key.get(previous, []) for right in by_key.get(following, [])):
                violations.append(f"{jid} op {following[1]} starts before op {previous[1]} ends (precedence)")
    for machine, entries in by_machine.items():
        entries = sorted(entries, key=lambda row: (row.start, row.end, row.key))
        for index, left in enumerate(entries):
            if left.start >= left.end:
                continue
            for right in entries[index + 1:]:
                if right.start >= left.end:
                    break
                if right.start < right.end and left.start < right.end:
                    violations.append(f"overlap on {machine}: {_name(left.key)} and {_name(right.key)}")
    for item in accepted:
        if item["type"] == "due_date" and item["hard"]:
            ends = [row.end for row in rows if row.key[0] == item["job"]]
            if ends and max(ends) > item["due"]:
                violations.append(f"hard due date {item['id']} missed: {item['job']} ends {_clock(max(ends))}, due {_clock(item['due'])}")
    return {"valid": not violations, "violations": violations}
