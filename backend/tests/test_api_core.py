import pytest
from conftest import mock

from app import config, runstore


def test_health_never_exposes_key(client):
    body = client.get("/api/health").json()
    assert body["ok"] and body["replay_device"] == "cpu-numpy"
    assert "key" not in str(body).lower()


def test_factory_returns_fixture(client):
    assert client.get("/api/factory").json()["committed_schedule"] == mock("factory.json")["committed_schedule"]


def test_unknown_run_uses_error_shape(client):
    r = client.get("/api/runs/r_nope")
    assert r.status_code == 404 and set(r.json()["error"]) == {"code", "message", "retryable"}


def test_unknown_path_uses_error_shape(client):
    r = client.get("/api/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


def test_run_store_expiry_and_cap(monkeypatch):
    runstore.clear()
    runstore.put({"run_id": "a", "kind": "draft", "message": "m"})
    monkeypatch.setattr(config, "RUN_TTL_S", -1)
    with pytest.raises(runstore.RunExpired):
        runstore.get("a")
    monkeypatch.setattr(config, "RUN_TTL_S", 3600)
    monkeypatch.setattr(config, "MAX_RUNS", 3)
    for i in range(5):
        runstore.put({"run_id": f"r{i}", "kind": "draft", "message": "m"})
    assert runstore.get("r4")["run_id"] == "r4"
    with pytest.raises(runstore.RunExpired):
        runstore.get("r0")
