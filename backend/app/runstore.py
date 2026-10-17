"""In-memory run store and run log. Emptied on restart; that is acceptable for the hackathon demo.

Extraction drafts hold the server's copy of the message and model output. Each solve creates a fresh,
immutable snapshot (fixture, reviewed constraints, alternatives). Replays and approvals are stored under it.
"""
import secrets
import threading
import time
from copy import deepcopy
from datetime import datetime

from . import config


class RunNotFound(KeyError):
    pass


class RunExpired(KeyError):
    pass


_lock = threading.Lock()
_runs: dict[str, dict] = {}
_expired: set[str] = set()


def _now() -> float:
    return time.time()


def new_run_id() -> str:
    return f"r_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(2)}"


def _purge() -> None:
    cutoff = _now() - config.RUN_TTL_S
    for rid in [r for r, v in _runs.items() if v["created"] < cutoff]:
        del _runs[rid]
        _expired.add(rid)


def _cap() -> None:
    while len(_runs) > config.MAX_RUNS:  # dicts keep insertion order: drop the oldest
        rid = next(iter(_runs))
        del _runs[rid]
        _expired.add(rid)
    if len(_expired) > 10 * config.MAX_RUNS:
        _expired.clear()


def put(run: dict) -> dict:
    with _lock:
        _purge()
        run = deepcopy(run)
        run.setdefault("created", _now())
        run.setdefault("log", [])
        run.setdefault("replays", {})
        _runs[run["run_id"]] = run
        _cap()
        return deepcopy(run)


def get(run_id: str, kind: str | None = None) -> dict:
    with _lock:
        _purge()
        if not isinstance(run_id, str) or run_id not in _runs:
            if run_id in _expired:
                raise RunExpired(run_id)
            raise RunNotFound(run_id)
        run = _runs[run_id]
        if kind and run["kind"] != kind:
            raise RunNotFound(run_id)
        return deepcopy(run)


def next_solve_id(draft_id: str) -> str:
    with _lock:
        draft = _runs.get(draft_id)
        if draft is None:
            raise RunNotFound(draft_id)
        draft["solve_count"] = draft.get("solve_count", 0) + 1
        return f"{draft_id}_s{draft['solve_count']}"


def add_replay(run_id: str, alternative_id: str, result: dict) -> None:
    """Replays are evidence attached to a snapshot; they do not change its plan data."""
    with _lock:
        _runs[run_id]["replays"][alternative_id] = deepcopy(result)


def set_approval(run_id: str, approval: dict) -> dict | None:
    """Store the first approval; return an existing one instead of overwriting it."""
    with _lock:
        run = _runs[run_id]
        if run.get("approval"):
            return deepcopy(run["approval"])
        run["approval"] = deepcopy(approval)
        return None


def log(run_id: str, step: str, **details) -> None:
    with _lock:
        run = _runs.get(run_id)
        if run is not None:
            run["log"].append({"step": step, "at": datetime.now().astimezone().isoformat(timespec="seconds"),
                               **deepcopy(details)})


def clear() -> None:
    with _lock:
        _runs.clear()
        _expired.clear()
