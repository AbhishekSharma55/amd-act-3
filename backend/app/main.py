"""Rehearsal API. Contract: plan/03_API_CONTRACT.md. Every error uses {"error": {code, message, retryable}}.

Feature routes live in their own routers: factory (#3), extract (#5), solve (#6), replay (#7), approval (#8).
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config, runstore
from .api_common import install_error_handlers, load_run
from .factory import router as factory_router
from .fixture import get_fixture
from .routes_approval import router as approval_router
from .routes_extract import router as extract_router
from .routes_replay import router as replay_router
from .routes_solve import router as solve_router

logging.basicConfig(level=config.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Rehearsal", description="Test a factory's recovery plan before changing the shift.")
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["GET", "POST"],
                   allow_headers=["Content-Type"])
install_error_handlers(app)
for router in [factory_router, extract_router, solve_router, replay_router, approval_router]:
    app.include_router(router)


@app.get("/api/health")
def health():
    F = get_fixture()
    return {"ok": True,
            "amd": {"configured": config.amd_configured(), "provider": "AMD Token Factory",
                    "model": config.AMD_MODEL or None, "host": config.amd_host()},
            "fallback_enabled": config.ALLOW_RULE_FALLBACK,
            "replay_device": config.REPLAY_DEVICE,
            "fixture": {"factory": F["factory"], "now": F["now"], "synthetic": True}}


@app.get("/api/runs/{run_id}")
def run_details(run_id: str):
    """Inspector evidence for a run (#9). Credentials are never stored, so none can leak here."""
    run = load_run(run_id)
    out = {"run_id": run["run_id"], "kind": run["kind"], "message": run["message"], "trace": run.get("trace"),
           "log": run["log"]}
    if run["kind"] == "solve":
        try:
            draft_log = runstore.get(run["draft_id"])["log"]
        except KeyError:
            draft_log = []
        out.update({"draft_id": run["draft_id"], "log": draft_log + run["log"], "constraints": run["constraints"],
                    "rejected": run["rejected"], "edits": run["edits"],
                    "alternatives": [{"id": a["id"], "label": a["label"], "solver": a["solver"], "checker": a["checker"],
                                      "merged_with": a["merged_with"]} for a in run["alternatives"].values()],
                    "infeasible": run["infeasible"],
                    "replays": {k: {kk: v[kk] for kk in ("device", "samples", "elapsed_ms", "assumptions")}
                                for k, v in run["replays"].items()}})
    else:
        out["constraints"] = run["constraints"]
    return out


# Last: serve the built React app from the same process, if present.
if (config.STATIC_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=config.STATIC_DIR, html=True), name="static")
