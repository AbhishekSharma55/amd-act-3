"""Issue #5: disruption message → validated, source-linked constraints, plus planner revalidation."""
from fastapi import APIRouter, Request

from . import config, runstore
from .api_common import ApiError, RateLimiter, body_of, draft_for, log
from .extract import ExtractionError, extract_amd, extract_rules
from .fixture import get_fixture
from .validate import ReviewError, review_constraints, validate_constraints

router = APIRouter(prefix="/api", tags=["extract"])
limiter = RateLimiter(config.EXTRACT_RATE_PER_MIN)
global_limiter = RateLimiter(config.EXTRACT_GLOBAL_PER_MIN)


@router.post("/extract")
def api_extract(body: dict, request: Request):
    message = body_of(body, "message", allowed={"message"})["message"]
    if not isinstance(message, str) or not message.strip():
        raise ApiError(400, "empty_message", "Type a disruption message first.")
    if len(message) > config.MAX_MESSAGE_CHARS:
        raise ApiError(400, "message_too_long", f"Keep the message under {config.MAX_MESSAGE_CHARS} characters.")
    limiter.check(request)
    if config.amd_configured():
        global_limiter.check(None, key="server", message="The shared AMD key is busy right now. Wait a few seconds "
                                                              "and retry.")
    F = get_fixture()
    try:
        result = extract_amd(message, F)
        origin = "amd_model"
    except ExtractionError as e:
        log.warning("AMD extraction failed: %s (%s)", e.code, e)
        if not config.ALLOW_RULE_FALLBACK:
            raise ApiError(e.status, e.code, str(e), retryable=e.code != "amd_not_configured")
        result = extract_rules(message, F)
        result["trace"]["fallback_reason"] = str(e)
        origin = "rule_fallback"
    constraints = validate_constraints(message, result["constraints"], F, origin=origin)
    run_id = runstore.new_run_id()
    runstore.put({"run_id": run_id, "kind": "draft", "message": message, "constraints": constraints,
                  "trace": result["trace"], "proposals": result["constraints"]})
    t = result["trace"]
    runstore.log(run_id, "extract", provider=t["provider"], model=t["model"], latency_ms=t["latency_ms"],
                 attempts=t["attempts"], fallback_used=t["fallback_used"],
                 review=[c["id"] for c in constraints if c["status"] == "review"])
    return {"run_id": run_id, "message": message, "constraints": constraints, "trace": t}


@router.post("/constraints/revalidate")
def api_revalidate(body: dict):
    """Check a planner's edits and decisions against the stored extraction without solving."""
    body = body_of(body, "run_id", "constraints", allowed={"run_id", "constraints"})
    draft = draft_for(body["run_id"])
    try:
        constraints, rejected, edits = review_constraints(draft, body["constraints"], get_fixture())
    except ReviewError as e:
        raise ApiError(422, "invalid_constraints", str(e))
    runstore.log(draft["run_id"], "revalidate", edits=edits, rejected=[c["id"] for c in rejected])
    return {"run_id": draft["run_id"], "constraints": constraints, "rejected": rejected, "edits": edits,
            "ready": all(c["status"] in ("ok", "accepted") for c in constraints)}
