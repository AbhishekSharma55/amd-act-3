"""Mountable Phase 1 factory endpoint; no dependency on AMD or the solver."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from fastapi import APIRouter

DEFAULT_FIXTURE = Path(__file__).resolve().parents[2] / "shared" / "fixture.json"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _time(value: Any, field: str) -> int:
    _require(isinstance(value, str) and re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value) is not None,
             f"{field} must be a valid HH:MM time (00:00–23:59)")
    hour, minute = map(int, value.split(":"))
    return hour * 60 + minute


def validate_fixture(data: Any) -> None:
    """Check fixture identity, references, clocks and operation coverage at startup.

    This validates the input fixture structure. It is not the independent
    feasibility checker for generated recovery plans (a separate feature).
    """
    _require(isinstance(data, dict), "fixture must be a JSON object")
    for field in ("factory", "date"):
        _require(isinstance(data.get(field), str) and bool(data[field]), f"{field} is required")
    _time(data.get("now"), "now")
    shift = data.get("shift")
    _require(isinstance(shift, dict), "shift must be an object")
    shift_start = _time(shift.get("start"), "shift.start")
    shift_end = _time(shift.get("end"), "shift.end")
    limit = _time(shift.get("overtime_until", shift.get("end")), "shift.overtime_until")
    _require(shift_start < shift_end <= limit, "shift must satisfy start < end <= overtime_until")
    _require(isinstance(shift.get("overtime_cost_per_hour"), (int, float)) and not isinstance(shift.get("overtime_cost_per_hour"), bool) and shift["overtime_cost_per_hour"] >= 0,
             "shift.overtime_cost_per_hour must be nonnegative")

    machines = data.get("machines")
    jobs = data.get("jobs")
    schedule = data.get("committed_schedule")
    _require(isinstance(machines, list) and bool(machines), "machines must be a non-empty list")
    _require(isinstance(jobs, list) and bool(jobs), "jobs must be a non-empty list")
    _require(isinstance(schedule, list), "committed_schedule must be a list")
    machine_ids: set[str] = set()
    for machine in machines:
        _require(isinstance(machine, dict) and isinstance(machine.get("id"), str) and bool(machine["id"]), "each machine needs an id")
        _require(machine["id"] not in machine_ids, f"duplicate machine {machine['id']}")
        _require(isinstance(machine.get("name"), str) and bool(machine["name"]), f"machine {machine['id']} needs a name")
        machine_ids.add(machine["id"])

    expected: dict[tuple[str, int], dict[str, int]] = {}
    job_ids: set[str] = set()
    for job in jobs:
        _require(isinstance(job, dict) and isinstance(job.get("id"), str) and bool(job["id"]), "each job needs an id")
        job_id = job["id"]
        _require(job_id not in job_ids, f"duplicate job {job_id}")
        job_ids.add(job_id)
        _time(job.get("due"), f"{job_id}.due")
        _require(isinstance(job.get("customer"), str), f"{job_id}.customer is required")
        _require(type(job.get("priority")) is int and job["priority"] in (1, 2, 3), f"{job_id}.priority must be 1, 2 or 3")
        _require(isinstance(job.get("ops"), list) and bool(job["ops"]), f"{job_id}.ops must be a non-empty list")
        for operation in job["ops"]:
            _require(isinstance(operation, dict) and type(operation.get("op")) is int and operation["op"] > 0, f"{job_id} needs positive integer operation numbers")
            key = (job_id, operation["op"])
            _require(key not in expected, f"duplicate operation {key}")
            eligible = operation.get("eligible")
            _require(isinstance(eligible, dict) and bool(eligible), f"{key} needs eligible machines")
            _require(set(eligible) <= machine_ids, f"{key} references unknown eligible machines")
            _require(all(type(duration) is int and duration > 0 for duration in eligible.values()), f"{key} durations must be positive integer minutes")
            expected[key] = eligible

    seen: set[tuple[str, int]] = set()
    for index, operation in enumerate(schedule):
        prefix = f"committed_schedule[{index}]"
        _require(isinstance(operation, dict) and isinstance(operation.get("job"), str) and type(operation.get("op")) is int, f"{prefix} needs job and operation identifiers")
        key = (operation["job"], operation["op"])
        _require(key in expected, f"{prefix} references unknown operation {key}")
        _require(key not in seen, f"{prefix} duplicates operation {key}")
        seen.add(key)
        _require(isinstance(operation.get("machine"), str) and operation["machine"] in expected[key], f"{prefix} references an ineligible machine")
        start = _time(operation.get("start"), f"{prefix}.start")
        end = _time(operation.get("end"), f"{prefix}.end")
        _require(start < end, f"{prefix} must start before it ends")
        _require(end - start == expected[key][operation["machine"]], f"{prefix} duration does not match the eligible machine")
    _require(seen == set(expected), f"committed_schedule is missing operations: {sorted(set(expected) - seen)}")


def load_fixture(path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        validate_fixture(data)
    except (OSError, ValueError) as error:
        raise ValueError(f"Invalid factory fixture at {path}: {error}") from error
    return data


def create_factory_router(path: Path = DEFAULT_FIXTURE) -> APIRouter:
    fixture = load_fixture(path)  # Fail immediately when this router is created.
    factory_router = APIRouter(prefix="/api", tags=["factory"])

    @factory_router.get("/factory")
    def get_factory() -> dict[str, Any]:
        """Return the checked fixture unchanged, as defined by the API contract."""
        return fixture

    return factory_router


router = create_factory_router()
