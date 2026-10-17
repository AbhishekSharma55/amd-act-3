"""Issue #6: reviewed constraints → checked recovery alternatives in a fresh immutable run.

Each solve is stored twice: in the run store (inspector evidence) and in the approval store (#8), which
is the only place approval reads plan data from.
"""
from fastapi import APIRouter

from . import config, runstore
from .api_common import ApiError, body_of, draft_for
from .approval import required_concessions
from .checker import check
from .fixture import get_fixture
from .solver import plan_alternatives
from .state import approvals
from .validate import ReviewError, review_constraints, validate_for_solve

router = APIRouter(prefix="/api", tags=["solve"])


@router.post("/solve")
def api_solve(body: dict):
    body = body_of(body, "run_id", "constraints", allowed={"run_id", "constraints", "allow", "time_limit_s"})
    allow = body.get("allow") or {}
    if not isinstance(allow, dict) or set(allow) - {"reroute", "overtime", "relax_hard_due"}:
        raise ApiError(400, "bad_request", "allow must be {reroute, overtime, relax_hard_due}")
    if allow.get("relax_hard_due"):
        raise ApiError(422, "unsupported_policy", "Relaxing a hard due date is not available; edit or reject that "
                                                  "constraint instead.")
    limit = body.get("time_limit_s", 10)
    if not isinstance(limit, (int, float)) or isinstance(limit, bool) or not 1 <= limit <= 30:
        raise ApiError(400, "bad_request", "time_limit_s must be between 1 and 30")
    draft = draft_for(body["run_id"])
    F = get_fixture()
    try:
        constraints, rejected, edits = review_constraints(draft, body["constraints"], F)
    except ReviewError as e:
        raise ApiError(422, "invalid_constraints", str(e))
    pending = [c for c in constraints if c["status"] not in ("ok", "accepted") or c["blocking_issues"]]
    if pending:
        detail = "; ".join(f"{c['id']}: {(c['blocking_issues'] or c['issues'] or ['needs review'])[0]}" for c in pending)
        raise ApiError(422, "review_required", f"Resolve or reject these items first: {detail}")
    try:
        validate_for_solve(F, constraints)
        alternatives, infeasible = plan_alternatives(F, constraints, allow, time_limit_s=float(limit))
    except ValueError as e:
        raise ApiError(422, "invalid_constraints", str(e))

    checked = []
    for alt in alternatives:
        alt["checker"] = check(F, constraints, alt["schedule"])
        if not alt["checker"]["valid"]:  # never show a plan the independent checker rejects
            infeasible.append({"id": alt["id"], "policy": alt["policy"], "label": alt["label"],
                               "solver_status": "CHECK_FAILED", "solver": alt["solver"], "conflict": [],
                               "conflict_kind": None, "possible_concessions": [],
                               "explanation": "The solver returned a plan that failed the independent checker: "
                                              + "; ".join(alt["checker"]["violations"])})
            continue
        alt["concessions"] = required_concessions(F, constraints, alt["schedule"])
        checked.append(alt)

    run_id = runstore.next_solve_id(draft["run_id"])
    if checked:
        approvals.save_run({"fixture": F, "message": draft["message"], "trace": draft["trace"],
                            "constraints": constraints + rejected, "alternatives": {a["id"]: a for a in checked},
                            "data_notice": "Synthetic demo data"}, run_id=run_id, ttl_seconds=config.RUN_TTL_S)
    runstore.put({"run_id": run_id, "kind": "solve", "draft_id": draft["run_id"], "fixture": F,
                  "message": draft["message"], "trace": draft["trace"], "constraints": constraints,
                  "rejected": rejected, "edits": edits, "allow": allow,
                  "alternatives": {a["id"]: a for a in checked}, "infeasible": infeasible})
    runstore.log(run_id, "solve", alternatives=[{"id": a["id"], "status": a["solver"]["status"],
                                                 "time_ms": a["solver"]["time_ms"], "checker_valid": a["checker"]["valid"]}
                                                for a in alternatives],
                 infeasible=[{"id": x["id"], "status": x["solver_status"]} for x in infeasible], edits=edits)
    return {"run_id": run_id, "status": "ok" if checked else "no_feasible_plan", "alternatives": checked,
            "infeasible": infeasible, "constraints": constraints, "rejected": rejected}

