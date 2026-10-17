"""Small in-memory adapter for immutable solve snapshots and atomic approval.

No browser-facing method can register or replace a plan. The solver calls
save_run() on the shared instance after constructing its checked alternatives.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import re
from threading import RLock
from typing import Callable
from uuid import uuid4

from .approval import ApprovalError, build_approval, validate_request


class ApprovalStore:
    def __init__(self, *, clock: Callable[[], datetime] | None = None):
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._lock = RLock()
        self._runs: dict[str, dict] = {}

    def save_run(self, snapshot: dict, *, run_id: str | None = None, ttl_seconds: int = 3600) -> str:
        """Server-only write; new solves get fresh IDs, and old IDs never change."""
        if not isinstance(snapshot, dict) or not {"fixture", "constraints", "alternatives", "message", "trace"} <= snapshot.keys():
            raise ValueError("Snapshot needs fixture, reviewed constraints, alternatives, message and trace")
        if not isinstance(snapshot["fixture"], dict) or not isinstance(snapshot["constraints"], list) or not isinstance(snapshot["message"], str) or (snapshot["trace"] is not None and not isinstance(snapshot["trace"], dict)):
            raise ValueError("Snapshot fixture, constraints, message and trace have invalid types")
        alternatives = snapshot["alternatives"]
        if not isinstance(alternatives, dict) or not alternatives:
            raise ValueError("Snapshot alternatives must be a nonempty mapping by ID")
        if any(not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", key) or not isinstance(value, dict) or key != value.get("id") or "schedule" not in value for key, value in alternatives.items()):
            raise ValueError("Every alternative mapping key must match its ID and include its schedule")
        run_id = f"r_{uuid4().hex}" if run_id is None else run_id
        if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", run_id):
            raise ValueError("Invalid stored run ID")
        if type(ttl_seconds) is not int or ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be a positive integer")
        saved = {**snapshot, "run_id": run_id}
        saved.pop("replays", None)
        encoded = json.dumps(saved, allow_nan=False)
        with self._lock:
            if run_id in self._runs:
                raise ApprovalError("run_exists", "A solved run cannot be replaced. Save a new solve with a fresh ID.", 409)
            self._runs[run_id] = {"snapshot": encoded, "expires_at": self._clock() + timedelta(seconds=ttl_seconds), "replays": {}, "approval": None, "intent": None}
        return run_id

    def _entry(self, run_id: str) -> dict:
        entry = self._runs.get(run_id)
        if entry is None:
            raise ApprovalError("run_not_found", "This run is unavailable after restart or was not found. Solve again before approval.", 404)
        if self._clock() >= entry["expires_at"]:
            raise ApprovalError("run_expired", "This run has expired. Solve again before approval.", 410)
        return entry

    @staticmethod
    def _snapshot(entry: dict) -> dict:
        return {**json.loads(entry["snapshot"]), "replays": deepcopy(entry["replays"])}

    def get_run(self, run_id: str) -> dict:
        with self._lock:
            return self._snapshot(self._entry(run_id))

    def save_replay(self, run_id: str, alternative_id: str, result: dict) -> None:
        with self._lock:
            entry = self._entry(run_id)
            if entry["approval"] is not None:
                raise ApprovalError("run_locked", "The approved run is locked. Create a fresh solve before changing its replay.", 409)
            if alternative_id not in json.loads(entry["snapshot"])["alternatives"]:
                raise ApprovalError("alternative_not_found", "Alternative not found in the stored run.", 404)
            if not isinstance(result, dict) or (result.get("run_id"), result.get("alternative_id")) != (run_id, alternative_id):
                raise ValueError("Replay IDs must match the selected stored plan")
            entry["replays"][alternative_id] = json.loads(json.dumps(result, allow_nan=False))

    def approve(self, body: dict) -> dict:
        intent = validate_request(body)
        with self._lock:
            entry = self._entry(intent["run_id"])
            if entry["approval"] is not None:
                if entry["intent"] != intent:
                    raise ApprovalError("run_locked", "This run is already approved and locked. Create a fresh solve for another decision.", 409)
                return deepcopy(entry["approval"])
            result = build_approval(self._snapshot(entry), intent, self._clock())
            entry["intent"], entry["approval"] = deepcopy(intent), deepcopy(result)
            return deepcopy(result)
