# Rehearsal backend

FastAPI + OR-Tools CP-SAT + NumPy. The contract is [plan/03_API_CONTRACT.md](../plan/03_API_CONTRACT.md); complete example responses are in [shared/mocks/](../shared/mocks/).

## Run locally

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements-dev.txt     # macOS/Linux: .venv/bin/python
cp .env.example .env                                                  # fill in the Token Factory values
cd backend && ../.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

The Vite dev server proxies `/api` to port 8000. If `backend/static/index.html` exists (the built frontend), FastAPI serves it at `/`.

Check the AMD connection once (records model, host, JSON mode and latency in `eval/smoke/`, never the key):

```bash
.venv/Scripts/python backend/scripts/amd_smoke.py --models
.venv/Scripts/python backend/scripts/amd_smoke.py --all
```

Tests (from the repository root or `backend/`): `.venv/Scripts/python -m pytest -q backend/tests`. CI runs them, the checker
report freshness check and the frontend tests/build on every pull request (`.github/workflows/ci.yml`).

## Modules

| File | Role |
| --- | --- |
| `app/extract.py` | AMD Token Factory call (OpenAI-compatible), JSON parsing, bounded retries, 30 s timeout. Labeled rule fallback only when `ALLOW_RULE_FALLBACK=1` |
| `app/validate.py` | Checks every proposal: IDs/aliases, clock times, required fields, exact source spans, time evidence, contradictions, interrupted work. Revalidates planner edits against the stored extraction |
| `app/solver.py` | CP-SAT flexible job shop: eligibility, precedence, no-overlap, frozen work, restart after interruption, outages, overtime cutoff, hard dates (assumption literals → sufficient conflict sets). Policy alternatives and merge of identical plans |
| `app/checker.py` | Independent checker written from the rules; does not import the solver |
| `app/replay.py` | Fixed-dispatch NumPy replay with declared synthetic uncertainty |
| `app/runstore.py` | In-memory runs for the inspector: extraction drafts, solve snapshots, replays and the step log. Expires after `RUN_TTL_S`, capped at `MAX_RUNS` |
| `app/state.py` | The process-wide `ApprovalStore` (#8). Solve saves each checked run there; replay attaches its result; approval reads only from it |
| `app/api_common.py` | Canonical error shape, input helpers, run lookup, per-client rate limit for `/api/extract` |
| `app/routes_extract.py`, `routes_solve.py`, `routes_replay.py`, `routes_approval.py` | Feature routers (#5, #6, #7, #8) |
| `app/main.py` | App setup, health, run inspector endpoint, static frontend |

## Endpoints

The five contract endpoints plus two additions used by the frontend:

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | AMD configured?, model, host, replay device, fallback flag |
| `GET /api/factory` | The fixture |
| `POST /api/extract` | `{message}` → validated constraints + AMD trace |
| `POST /api/constraints/revalidate` | **Added.** `{run_id, constraints}` → server-revalidated items after edits/decisions, plus `ready` |
| `POST /api/solve` | `{run_id, constraints, allow?, time_limit_s?}` → fresh immutable `run_id`, checked alternatives, infeasible/unknown cards |
| `POST /api/replay` | `{run_id, alternative_id, assumptions?}` → per-job "X of N", p90 finish, failing scenario with bottleneck |
| `POST /api/approve` | `{run_id, alternative_id, approved_concessions, approver}` → dispatch CSV + decision record |
| `GET /api/runs/{run_id}` | **Added.** Inspector evidence: trace, step log, solver/checker per alternative, replay settings |

Additive fields beyond the mocks: constraint lists are echoed by `/solve` (`constraints`, `rejected`), infeasible entries carry `id` and `solver`, replay jobs carry `planned_finish`, `due`, `late_in_plan`, `worst_late_min`, and the failing scenario carries `job`, `minutes_late` and a `bottleneck` summary.

## Replay semantics

Same machine and same order per machine; no re-optimization per sample. Unstarted operations take duration × triangular(0.9, 1.0, 1.3); running operations keep their observed start and elapsed work and only their remaining work is randomized. An operation never starts before its planned start, its machine being free, its job's previous operation, or `now`, and waits for the sampled repair end if it would overlap an outage. Each outage still open at `now` ends 0-90 min late (uniform). Defaults: 500 samples, seed 7. With zero spread and zero delay the plan is reproduced exactly. These are synthetic assumptions, not calibrated factory reliability.

## Production settings

All optional; see `.env.example`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `AMD_API_BASE`, `AMD_API_KEY`, `AMD_MODEL` | – | Token Factory access. Set the key as a host secret, never in the image or repo |
| `ALLOW_RULE_FALLBACK` | `0` | `1` uses the labeled rule fallback when AMD is unavailable |
| `EXTRACT_RATE_PER_MIN` | `12` | `/api/extract` calls per client per minute (protects the shared AMD quota) |
| `RUN_TTL_S`, `MAX_RUNS` | `21600`, `2000` | Run expiry and memory bound |
| `SOLVER_WORKERS` | CPU count, max 8 | CP-SAT threads |
| `STATIC_DIR` | `backend/static`, else `frontend/dist` | Built frontend served at `/` |
| `LOG_LEVEL` | `INFO` | Server log level; keys and prompts are never logged |

Run one process (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`): runs and approvals are in memory and are not
shared between workers.
