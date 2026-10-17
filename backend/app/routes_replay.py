"""Issue #7: rehearse one stored alternative under declared synthetic uncertainty."""
from fastapi import APIRouter

from . import config, runstore
from .api_common import ApiError, body_of, load_run
from .checker import check
from .replay import run_replay
from .solver import effective_due, effective_priority, outage_windows
from .state import approvals

router = APIRouter(prefix="/api", tags=["replay"])


@router.post("/replay")
def api_replay(body: dict):
    body = body_of(body, "run_id", "alternative_id", allowed={"run_id", "alternative_id", "assumptions"})
    run = load_run(body["run_id"], "solve")
    alt = run["alternatives"].get(body["alternative_id"])
    if alt is None:
        raise ApiError(404, "alternative_not_found", f"Alternative {body['alternative_id']!r} is not in this run")
    F, constraints = run["fixture"], run["constraints"]
    checked = check(F, constraints, alt["schedule"])
    if not checked["valid"]:
        raise ApiError(422, "check_failed", "Stored schedule failed re-check: " + "; ".join(checked["violations"]))
    try:
        result = run_replay(F, alt["schedule"], outage_windows(F, constraints), effective_due(F, constraints),
                            effective_priority(F, constraints), body.get("assumptions"), device=config.REPLAY_DEVICE)
    except ValueError as e:
        raise ApiError(400, "bad_assumptions", str(e))
    result = {"run_id": run["run_id"], "alternative_id": alt["id"], **result}
    approvals.save_replay(run["run_id"], alt["id"], result)  # 409 once the run is approved and locked
    runstore.add_replay(run["run_id"], alt["id"], result)
    runstore.log(run["run_id"], "replay", alternative_id=alt["id"], device=result["device"], samples=result["samples"],
                 elapsed_ms=result["elapsed_ms"], seed=result["assumptions"]["seed"],
                 failing=(result["failing_scenario"] or {}).get("reason"))
    return result
