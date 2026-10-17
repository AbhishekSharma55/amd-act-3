"""Issue #8 approval mounted on the shared run store: the approval store owns the logic and locking."""
from fastapi import APIRouter

from . import runstore
from .state import approvals

router = APIRouter(prefix="/api", tags=["approval"])


@router.post("/approve")
def api_approve(body: dict):
    """IDs + approved concession IDs + approver; plan data always comes from the stored solve."""
    result = approvals.approve(body)
    rec = result["decision_record"]
    try:
        first = not any(step["step"] == "approve" for step in runstore.get(rec["run_id"])["log"])
    except KeyError:
        first = False
    if first:  # an identical retry returns the stored record; log the decision once
        runstore.log(rec["run_id"], "approve", alternative_id=rec["alternative_id"], approver=rec["approver"],
                     concessions=[c["id"] for c in rec["concessions"]])
    return result
