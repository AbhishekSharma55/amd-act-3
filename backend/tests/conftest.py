import json
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(1, str(ROOT))  # the checker/factory tests import backend.app.*

from app import runstore  # noqa: E402

DEMO_MESSAGE = ("Mill M2 is unavailable until 14:00. Order J7 still needs to ship at 16:00. "
                "Overtime requires approval.")
DEMO_PROPOSALS = [
    {"type": "machine_down", "params": {"machine": "Mill M2", "from": None, "until": "14:00"},
     "source_span": "Mill M2 is unavailable until 14:00"},
    {"type": "due_date", "params": {"job": "J7", "time": "16:00", "hard": True},
     "source_span": "Order J7 still needs to ship at 16:00"},
    {"type": "overtime", "params": {"allowed": True, "until": None}, "source_span": "Overtime requires approval"},
]


def mock(name):
    return json.loads((ROOT / "shared" / "mocks" / name).read_text(encoding="utf-8"))


@pytest.fixture
def F():
    from app.fixture import get_fixture
    return get_fixture()


@pytest.fixture
def demo_constraints():
    return mock("extract.json")["constraints"]


@pytest.fixture
def client(monkeypatch):
    """API client whose AMD call returns given proposals instead of hitting the network."""
    from fastapi.testclient import TestClient
    import app.main as main

    runstore.clear()
    from app import state
    state.approvals._runs.clear()
    state = {"proposals": DEMO_PROPOSALS}

    def fake(message, fixture):
        return {"constraints": state["proposals"], "trace": {
            "provider": "AMD Token Factory", "model": "test-model", "host": "test", "latency_ms": 5, "attempts": 1,
            "usage": {"prompt_tokens": 1, "completion_tokens": 1}, "raw_output": "{}", "fallback_used": False,
            "mode": "test"}}

    try:
        import app.routes_extract as routes_extract
        monkeypatch.setattr(routes_extract, "extract_amd", fake)
        routes_extract.limiter._hits.clear()
    except ImportError:  # foundation-only checkout without the extraction router
        pass
    c = TestClient(main.app)
    c.state = state
    return c
