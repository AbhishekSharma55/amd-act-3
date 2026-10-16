# Rehearsal: build plan

Prepared October 15, 2026, before any product code was written. This folder turns the [project decision](../research/ASTRA_PROJECT_DECISION.md) into a build plan for two people working in parallel.

Start with [HACKATHON_GUIDE.md](HACKATHON_GUIDE.md) for orientation and [PHASES.md](PHASES.md) for the latest feature plan. `01_PHASES.md` preserves the earlier ownership split; its timing sketch is superseded by the newer draft. Technical behavior is defined by `02`-`05` and the checked examples.

PR review corrections cover server-owned approval, blocking input validation, accepted overtime cutoffs, effective due dates, occupied overtime/cost, and replay that preserves planned releases and observed running work. The corrected synthetic demo has J4 on time in **239/500** scenarios. Run `python3 plan/prototype/regression_checks.py` for the 20 focused checks. Evaluation now includes a small held-out recovery comparison as well as extraction accuracy; those product measurements still need to be run during the build.

**Product in one line:** a planner types a disruption message ("Mill M2 is down until 14:00, J7 must still ship at 16:00"). An open model on AMD turns it into typed constraints. A CP-SAT solver builds recovery alternatives, and an independent checker verifies them. A replay engine shows how each alternative can fail. The planner approves one alternative and exports a dispatch CSV with a decision record.

## Read in this order

| File | Who needs it | What it answers |
| --- | --- | --- |
| [01_PHASES.md](01_PHASES.md) | Both | Who builds what, in which order, by when, and how we know it is done |
| [02_DATA_MODEL.md](02_DATA_MODEL.md) | Both | The factory fixture, the constraint language, and the example demo data |
| [03_API_CONTRACT.md](03_API_CONTRACT.md) | Both | The five endpoints and their exact JSON. This is the contract between backend and frontend |
| [04_BACKEND_GUIDE.md](04_BACKEND_GUIDE.md) | Person A | How to build extraction, validation, solver, checker, replay and approval |
| [05_FRONTEND_GUIDE.md](05_FRONTEND_GUIDE.md) | Person B | Screens, components, states and the demo flow |
| [06_TECH_RESEARCH.md](06_TECH_RESEARCH.md) | Both | Verified facts about Token Factory, OR-Tools, PyTorch on ROCm and hosting, with sources |
| [07_DEMO_AND_SUBMISSION.md](07_DEMO_AND_SUBMISSION.md) | Both, mainly B | Video script, slides outline, submission checklist and the questions judges will ask |
| [mocks/](mocks/) | Both | Complete, valid example responses for every endpoint, generated from the prototype. Copy into `shared/mocks/` in Phase 0 |
| [prototype/](prototype/) | A | Rough scripts used to check the demo story and to regenerate the mocks |

## What has and has not been checked

- **Checked by running code:** the example fixture, the solver and checker designs, the replay algorithm and the demo outcomes (infeasible keep-machines plan, re-route plan, J4 failing in replay). See `06_TECH_RESEARCH.md`, section 6.
- **Not checked:** any real Token Factory call (no key yet), the event portal's model list and limits, hosting sleep behavior, the GPU replay.

## Team split

| | Person A: backend | Person B: frontend + submission |
| --- | --- | --- |
| Language | Python 3.11+, FastAPI, OR-Tools, NumPy | React (Vite), plain CSS or Tailwind |
| Folder | `backend/` | `frontend/` |
| Owns | AMD extraction, validation, solver, checker, replay, approval, evaluation | UI, demo flow, Docker/deploy, README, video, slides, cover |
| Works from | `shared/fixture.json` | `shared/fixture.json` + `shared/mocks/*.json` |

The two tracks touch only through `shared/` and the API contract, so neither person waits for the other.

## Original timing sketch (IST, superseded)

These were the initial planning targets. Use the latest draft in `PHASES.md` when assigning work; verify the enforced submission cutoff in the event form because published times disagree.

| When | Milestone |
| --- | --- |
| Oct 15 | Phase 0 done together. Token Factory call works |
| Oct 16, 2 PM | Sync 1: real `/api/extract` connected to the UI |
| Oct 16, 11 PM | Sync 2: all endpoints real and merged into `main` |
| **Oct 17, 12 PM** | **Feature freeze.** Deployed URL works end to end |
| **Oct 17, 6 PM** | **Our target for a complete submission.** This is a protective target, not an official deadline |
| Oct 18, 3:30 PM | Submission deadline in `context/schedule.txt`. Venue pages show other times; see the strategy doc, section 12 |

## Ground rules

1. The API contract in `03_API_CONTRACT.md` is changed only when both people agree, and both update the mocks in the same commit.
2. Never commit API keys. Use `.env` locally and host secrets in deployment.
3. Work on `backend/*` or `frontend/*` branches and merge into `main` at least once a day.
4. Every number we show judges comes from our own run, and is labeled with what it is ("X of N simulated scenarios", "builder-run test").
5. If time runs short, cut nice-to-haves in the order given in `01_PHASES.md`. Never cut a must-have.
