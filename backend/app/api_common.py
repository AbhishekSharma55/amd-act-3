"""Shared pieces for the API routers: the canonical error shape, input helpers and run lookup."""
import logging
import threading
import time
from collections import deque

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import runstore
from .approval import ApprovalError

log = logging.getLogger("rehearsal")


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.status, self.code, self.message, self.retryable = status, code, message, retryable


def error_response(status, code, message, retryable=False):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "retryable": retryable}})


def install_error_handlers(app: FastAPI) -> None:
    """Every error leaves the API as {"error": {code, message, retryable}} with a real HTTP status."""

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, e: ApiError):
        return error_response(e.status, e.code, e.message, e.retryable)

    @app.exception_handler(ApprovalError)
    async def _approval_error(_: Request, e: ApprovalError):
        return JSONResponse(e.response(), status_code=e.status)

    @app.exception_handler(RequestValidationError)
    async def _bad_request(_: Request, e: RequestValidationError):
        first = e.errors()[0] if e.errors() else {}
        where = ".".join(str(x) for x in first.get("loc", []) if x != "body")
        return error_response(400, "bad_request", f"Invalid request{' at ' + where if where else ''}: "
                                                  f"{first.get('msg', 'bad input')}")

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, e: StarletteHTTPException):
        return error_response(e.status_code, "not_found" if e.status_code == 404 else "http_error", str(e.detail))

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, e: Exception):
        log.exception("Unhandled error on %s %s", request.method, request.url.path)
        return error_response(500, "internal_error", f"Unexpected server error ({type(e).__name__}). Please retry.", True)


def body_of(body, *required, allowed=None):
    if not isinstance(body, dict):
        raise ApiError(400, "bad_request", "Request body must be a JSON object")
    for k in required:
        if k not in body:
            raise ApiError(400, "bad_request", f"Missing field '{k}'")
    if allowed is not None and set(body) - set(allowed):
        raise ApiError(400, "bad_request", f"Unknown fields: {', '.join(sorted(set(body) - set(allowed)))}")
    return body


def load_run(run_id, kind=None):
    try:
        return runstore.get(run_id, kind)
    except runstore.RunExpired:
        raise ApiError(410, "run_expired", "This run has expired. Please read the message and solve again.")
    except runstore.RunNotFound:
        raise ApiError(404, "run_not_found", "Unknown run (the server may have restarted). Please read the message "
                                             "and solve again.")


def draft_for(run_id):
    """The extraction draft behind a draft or solve ID."""
    run = load_run(run_id)
    return run if run["kind"] == "draft" else load_run(run["draft_id"], "draft")


class RateLimiter:
    """Small per-client sliding window; protects the shared AMD quota from accidental floods."""

    def __init__(self, per_minute: int):
        self.per_minute, self._hits, self._lock = per_minute, {}, threading.Lock()

    def check(self, request: Request) -> None:
        if self.per_minute <= 0:
            return
        forwarded = request.headers.get("x-forwarded-for", "")
        key = forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")
        now = time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] > 60:
                hits.popleft()
            if len(hits) >= self.per_minute:
                raise ApiError(429, "rate_limited", "Too many messages in a minute. Wait a moment and retry.", True)
            hits.append(now)
            if len(self._hits) > 10_000:
                self._hits = {k: v for k, v in self._hits.items() if v and now - v[-1] <= 60}
