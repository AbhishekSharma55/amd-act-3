"""Load and sanity-check the factory fixture once at startup."""
import json
from copy import deepcopy
from pathlib import Path

from . import config
from .timeutil import hm


class FixtureError(RuntimeError):
    pass


def check_fixture(F: dict) -> None:
    problems = []
    try:
        now, start, end, limit = (hm(F["now"]), hm(F["shift"]["start"]), hm(F["shift"]["end"]),
                                  hm(F["shift"]["overtime_until"]))
        if not start <= now <= limit or not start < end <= limit:
            problems.append("now/shift times are out of order")
    except (KeyError, TypeError, ValueError) as e:
        raise FixtureError(f"Fixture times are invalid: {e}") from e
    machines = {m["id"] for m in F["machines"]}
    ops = {}
    for j in F["jobs"]:
        try:
            hm(j["due"])
        except ValueError:
            problems.append(f"{j['id']} has an invalid due time")
        if j.get("priority") not in (1, 2, 3):
            problems.append(f"{j['id']} priority must be 1-3")
        for o in j["ops"]:
            if not o["eligible"] or set(o["eligible"]) - machines:
                problems.append(f"{j['id']} op {o['op']} lists unknown machines")
            ops[(j["id"], o["op"])] = o
    seen = set()
    for a in F["committed_schedule"]:
        key = (a["job"], a["op"])
        if key not in ops:
            problems.append(f"committed schedule has unknown operation {key}")
            continue
        if key in seen:
            problems.append(f"committed schedule lists {key} twice")
        seen.add(key)
        try:
            d = hm(a["end"]) - hm(a["start"])
        except ValueError:
            problems.append(f"{key} has invalid committed times")
            continue
        if ops[key]["eligible"].get(a["machine"]) != d:
            problems.append(f"{key} committed machine/duration does not match eligibility")
    for key in ops:
        if key not in seen:
            problems.append(f"{key} missing from committed schedule")
    if problems:
        raise FixtureError("Invalid fixture: " + "; ".join(problems))


def load_fixture(path: Path | None = None) -> dict:
    path = Path(path or config.FIXTURE_PATH)
    try:
        F = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise FixtureError(f"Cannot read fixture {path}: {e}") from e
    check_fixture(F)
    return F


_FIXTURE: dict | None = None


def get_fixture() -> dict:
    """A copy, so no request can mutate the shared fixture."""
    global _FIXTURE
    if _FIXTURE is None:
        _FIXTURE = load_fixture()
    return deepcopy(_FIXTURE)
