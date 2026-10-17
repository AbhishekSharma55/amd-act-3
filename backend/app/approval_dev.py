"""Explicit sample-only service: real approval checks over saved synthetic inputs."""

import json
from pathlib import Path

from fastapi import FastAPI

from .approval_api import create_approval_router
from .approval_store import ApprovalStore
from .factory import router as factory_router


def create_sample_store() -> ApprovalStore:
    root = Path(__file__).resolve().parents[2]

    def load(name):
        return json.loads((root / "shared" / "mocks" / f"{name}.json").read_text(encoding="utf-8"))

    extract, solve, replay = load("extract"), load("solve"), load("replay")
    store = ApprovalStore()
    store.save_run({"fixture": load("factory"), "constraints": extract["constraints"], "alternatives": {alt["id"]: alt for alt in solve["alternatives"]},
                    "message": extract["message"], "trace": extract["trace"],
                    "data_notice": "Synthetic demo data; saved prototype inputs, no live AMD call. Approval was checked by the local service."},
                   run_id=solve["run_id"])
    store.save_replay(solve["run_id"], replay["alternative_id"], replay)
    return store


app = FastAPI(title="Rehearsal · synthetic approval development API")
store = create_sample_store()
app.include_router(factory_router)
app.include_router(create_approval_router(store))
