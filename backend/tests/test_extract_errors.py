"""Token Factory failure modes (documented in the event's Token Factory docs) map to clear, honest errors."""
import json
from types import SimpleNamespace

import httpx
import openai
import pytest

from app import config, extract
from app.extract import ExtractionError, extract_amd

GOOD = json.dumps({"constraints": [{"type": "overtime", "params": {"allowed": False}, "source_span": "No overtime"}]})


def status_error(cls, status, message, headers=None):
    request = httpx.Request("POST", "https://developer.amd.com.cn/radeon/api/v1/chat/completions")
    response = httpx.Response(status, headers=headers or {}, request=request)
    return cls(message, response=response, body={"error": {"message": message}})


class FakeClient:
    def __init__(self, *outcomes):
        self.outcomes, self.calls = list(outcomes), []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(model="DeepSeek-V4-Flash", usage=None,
                               choices=[SimpleNamespace(message=SimpleNamespace(content=outcome))])


@pytest.fixture
def amd(monkeypatch, F):
    monkeypatch.setattr(config, "AMD_API_BASE", "https://developer.amd.com.cn/radeon/api/v1")
    monkeypatch.setattr(config, "AMD_API_KEY", "rc-test")
    monkeypatch.setattr(config, "AMD_MODEL", "DeepSeek-V4-Flash")
    monkeypatch.setattr(extract.time, "sleep", lambda s: None)

    def use(*outcomes):
        client = FakeClient(*outcomes)
        monkeypatch.setattr(extract, "_get_client", lambda: client)
        return client
    return use


def test_success_records_live_trace(amd, F):
    client = amd(GOOD)
    out = extract_amd("No overtime", F)
    assert out["trace"]["mode"] == "live" and out["trace"]["host"] == "developer.amd.com.cn"
    assert client.calls[0]["response_format"] == {"type": "json_object"} and client.calls[0]["temperature"] == 0


def test_concurrency_429_is_retried(amd, F):
    client = amd(status_error(openai.RateLimitError, 429, "concurrency", {"retry-after": "1"}), GOOD)
    assert extract_amd("No overtime", F)["trace"]["attempts"] == 2 and len(client.calls) == 2


def test_per_minute_429_fails_fast_with_wait_time(amd, F):
    client = amd(status_error(openai.RateLimitError, 429, "rpm", {"retry-after": "60"}))
    with pytest.raises(ExtractionError) as e:
        extract_amd("No overtime", F)
    assert (e.value.code, e.value.status) == ("amd_rate_limited", 429) and "60 s" in str(e.value)
    assert len(client.calls) == 1


@pytest.mark.parametrize("cls, status, message, code", [
    (openai.AuthenticationError, 401, "invalid key", "amd_auth_failed"),
    (openai.PermissionDeniedError, 403, "account_not_verified", "amd_account_review"),
    (openai.BadRequestError, 400, "Requested model Old-Model not supported", "amd_model_unavailable"),
    (openai.BadRequestError, 400, "not enough credits", "amd_bad_request"),
    (openai.NotFoundError, 404, "not found", "amd_bad_endpoint"),
])
def test_unfixable_errors_are_named_and_not_retried(amd, F, cls, status, message, code):
    client = amd(status_error(cls, status, message))
    with pytest.raises(ExtractionError) as e:
        extract_amd("No overtime", F)
    assert e.value.code == code and len(client.calls) == 1


def test_json_mode_rejection_retries_without_it(amd, F):
    client = amd(status_error(openai.BadRequestError, 400, "response_format is not supported for this model"), GOOD)
    out = extract_amd("No overtime", F)
    assert "response_format" not in client.calls[1] and out["trace"]["json_mode"] is False


def test_server_errors_retry_then_fail_clearly(amd, F):
    errors = [status_error(openai.InternalServerError, 503, "saturated") for _ in range(3)]
    client = amd(*errors)
    with pytest.raises(ExtractionError) as e:
        extract_amd("No overtime", F)
    assert e.value.code == "amd_unavailable" and len(client.calls) == 3 and "HTTP 503" in str(e.value)


def test_platform_error_shape_is_read():
    request = httpx.Request("POST", "https://x")
    err = openai.PermissionDeniedError("x", response=httpx.Response(403, request=request),
                                       body={"detail": {"error": {"message": "account_not_verified"}}})
    assert extract._error_text(err) == "account_not_verified"


def test_server_wide_limit_protects_the_shared_key(client, monkeypatch):
    import app.routes_extract as routes
    monkeypatch.setattr(config, "AMD_API_KEY", "rc-test")
    monkeypatch.setattr(config, "AMD_API_BASE", "https://developer.amd.com.cn/radeon/api/v1")
    monkeypatch.setattr(config, "AMD_MODEL", "DeepSeek-V4-Flash")
    monkeypatch.setattr(routes.global_limiter, "per_minute", 2)
    codes = [client.post("/api/extract", json={"message": "No overtime today."},
                         headers={"x-forwarded-for": f"10.0.0.{i}"}).status_code for i in range(3)]
    assert codes == [200, 200, 429]
