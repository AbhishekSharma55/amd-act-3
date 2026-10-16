# 01. Phases and ownership

This is the original ownership/timing sketch. Use `PHASES.md` for the latest feature plan, and `02`-`05` for the corrected validation, scheduling, replay and approval rules.

**A** = backend (Python). **B** = frontend + submission (React). Each phase lists its input and output, so the other person can keep working from mocks without waiting.

```
Oct 15            Oct 16                              Oct 17                    Oct 18
|-- Phase 0 --|-- A1 --|-- A2 -- A3 -- A4 -- A5 -- A6 --|-- A7 --|== FREEZE ==|-- submit --|buffer|
 (together)   |-- B1 --|-- B2 -- B3 -- B4 -- B5 ------|-- B6 --|  12:00 PM  |-- B7 ------|      |
                              ^ Sync 1         ^ Sync 2                ^ Sync 3   ^ 6 PM target
```

---

## Phase 0: Foundation (Oct 15, about 2 hours, together)

This is the only phase that both people do together. After it, the two tracks split.

| # | Task | Output |
| --- | --- | --- |
| 0.1 | Create `backend/`, `frontend/`, `shared/`, `shared/mocks/`, `eval/` in the repo | Folder structure on `main` |
| 0.2 | Copy the example fixture from `02_DATA_MODEL.md` into `shared/fixture.json`. It includes the **committed schedule** and the **"now" time** | `shared/fixture.json` |
| 0.3 | Copy the example responses from `03_API_CONTRACT.md` into `shared/mocks/` | `factory.json`, `extract.json`, `solve.json`, `replay.json`, `approve.json` |
| 0.4 | Each person confirms their own AMD AI Developer Program signup, lablab enrollment and team membership | Screenshot in the team chat |
| 0.5 | Get a Token Factory API key, list the models, and send one chat request (see `06_TECH_RESEARCH.md`) | Base URL, model name and one working response recorded in `.env.example` (without the key) |

**Done when:** the fixture and mocks are on `main`, and one real Token Factory request has returned text.
**If 0.5 fails:** stop and fix this first. It is the AMD requirement, and the rest of the plan depends on it.

---

## Track A: Backend

| Phase | When | Build | Input → Output | Done when |
| --- | --- | --- | --- | --- |
| **A1. Extraction** | Oct 15 evening | `extract.py`: send the message plus the fixture's machine/job list to Token Factory and parse the JSON reply. Add a timeout, retry on 429/5xx, and a clear error when the call fails | message → raw constraint proposals | Five different messages return parseable JSON |
| **A2. Validation** | Oct 16 morning | `validate.py`: resolve aliases ("big mill" → M2), check that IDs exist, parse times, check that `source_span` exists in the message, detect contradictions. Anything doubtful gets `status: "review"` with a reason | proposals → checked constraints | An unknown machine, a missing time and two conflicting due dates each produce `review` |
| **A3. Solver** | Oct 16 morning | `solver.py`: CP-SAT flexible job shop that freezes started work, blocks outages and builds alternatives from policies (keep machines, re-route, overtime). When there is no solution, report the conflicting constraints | factory + accepted constraints → alternatives or an infeasible result | The demo scenario gives the outcomes listed in `02_DATA_MODEL.md` |
| **A4. Checker** | Oct 16 afternoon | `checker.py`: separate code with no solver import. It checks every operation once, eligibility, duration, precedence, machine overlap, outages, frozen work, shift/overtime window and hard due dates | schedule → `{valid, violations[]}` | Hand-broken schedules fail with the right reason, and every solver output passes |
| **A5. Replay** | Oct 16 evening | `replay.py`: NumPy Monte Carlo with a fixed dispatch policy and random durations and repair time. It returns "X of N on time" per job and the worst scenario as a timeline | schedule → per-job outcomes + one failing timeline | A failing scenario is found for at least one alternative in the demo |
| **A6. API + approval** | Oct 16 night | `main.py`: FastAPI endpoints that match the contract exactly. `/approve` re-runs the checker and returns the CSV and the decision record. Add an in-memory run log | HTTP | All endpoints work from curl/Postman, and the responses match the mocks |
| **A7. Evaluation + inspector data** | Oct 17 morning | 15-20 labeled extraction messages plus 5-8 held-out recovery cases, a competent CPU optimizer reference and a replay-hidden/shown comparison (see `PHASES.md`, 9f). Record model, latency and tokens per AMD call | labeled messages + recovery scenarios → results table | Reproducible table committed and pasted into the README; no improvement claimed unless measured |
| A8. GPU replay (nice-to-have) | Oct 17 morning, only if A1-A7 are done | The same replay with PyTorch on an AMD GPU, compared with the CPU result on identical samples | — | CPU and GPU results match; timing is recorded honestly |

## Track B: Frontend + submission

| Phase | When | Build | Data source | Done when |
| --- | --- | --- | --- | --- |
| **B1. Setup + timeline** | Oct 15 evening | Vite React app. Gantt timeline with machines as rows, operations as colored blocks per job, a "now" line, outage blocks and due markers | `shared/fixture.json` | The committed schedule renders correctly |
| **B2. Message + constraints** | Oct 16 morning | Message box with sample messages. Constraint list highlights `source_span`. Complete ambiguous items can be confirmed; blocking IDs/times/contradictions require correction and backend revalidation or rejection. Send complete `ok` / `accepted` items to `/solve` | `mocks/extract.json` | Highlight works; Accept cannot bypass missing fields; Solve stays disabled while non-rejected reviews/blockers remain |
| **B3. Alternatives** | Oct 16 afternoon | Alternative cards: late jobs, overtime minutes and cost, moved operations, checker badge. Selecting a card shows the before/after timeline. An **infeasible** result shows a red card with the conflicting constraints and the concessions on offer | `mocks/solve.json` | Switching cards updates the timeline, and the infeasible card renders |
| **B4. Replay + approval** | Oct 16 evening | **Show a failure** button that draws the failing scenario timeline and highlights the bottleneck operation. Approval panel: concessions as checkboxes and the approver's name; then **Approve** downloads the CSV and the decision record | `mocks/replay.json`, `mocks/approve.json` | Approve is disabled until every concession is ticked; the CSV downloads |
| **B5. Run inspector** | Oct 16 night | Collapsible panel: AMD model, endpoint host, latency, tokens, raw model output, validation results, solver status/time, checker result and replay sample count | run log fields | Panel shows real values after Sync 2 |
| **B6. Deploy + README** | Oct 17 morning | One Dockerfile (build React, serve it from FastAPI). Deploy and set secrets. README covering what runs on AMD, how to run, synthetic data notice and evaluation results | — | The public URL runs the full demo |
| **B7. Submission material** | Oct 17 afternoon | Cover image, video (aim for 4-4.5 minutes), PDF slides, short and long descriptions, tags. See `07_DEMO_AND_SUBMISSION.md` | — | Everything is uploaded on lablab |

---

## Sync points

| Sync | When | What happens | If it slips |
| --- | --- | --- | --- |
| **Sync 1** | Oct 16, ~2 PM | A's real `/api/extract` and `/api/factory` are live locally. B switches those two calls from mocks to the API | B keeps using mocks; A sends the exact JSON of a failing case |
| **Sync 2** | Oct 16, ~11 PM | All endpoints are real. Both merge into `main` and run the whole flow twice: the demo message, plus one changed message (different outage end) | Cut A5 down to CPU-only with fewer samples, but keep the endpoint |
| **Sync 3** | **Oct 17, 12 PM: freeze** | Run the full demo on the deployed URL. After this, only bug fixes, documentation and submission work | Drop the nice-to-haves immediately |

## Submission phase (Oct 17, 12 PM to 6 PM, both)

- B records the video. A explains the backend and AMD part on camera or in narration.
- A removes `research/sources/` (about 19 MB of scraped pages) from the public repo, or moves it out. Check licenses and notices, then make the repo public.
- Fill the lablab form together and check every link from a logged-out browser.

## Buffer (Oct 18 until 12 PM)

Only re-check the links, the video, the app URL and the repo visibility. Nothing new.

---

## Must-haves and cut order

**Must-haves, never cut:** AMD extraction visible in the demo (A1), validation with human Accept/Reject (A2, B2), solver with alternatives and the infeasible result (A3, B3), independent checker (A4), approval with concessions and CSV (A6, B4), deployed URL (B6), video, slides and public repo (B7).

**Cut in this order when short of time:**
1. A8 GPU replay
2. Evaluation size: 20 → 10 messages (keep at least 10, labeled honestly)
3. B5 run inspector: show only model, latency and checker result
4. A5 replay: fewer samples, simpler failure view. Keep the "Show a failure" button, because it is our most memorable moment

## Daily routine

- **Morning, 10 minutes:** today's phase for each person, plus any blocker.
- **Night, 10 minutes:** what works, what is stuck, merge into `main`.
- Post blockers in chat immediately, without waiting for the sync.

## Gaps this plan closes (compared with the first draft)

Six steps from the README's product flow were missing from the first phase draft and are now included above: the committed schedule and "now" time (0.2), frozen started work (A3), human Accept/Reject for review items (A2/B2), the infeasible result with conflicting constraints (A3/B3), concession approval (B4), and the decision record (A6). Two further items cover judging: graceful failure of the AMD call (A1) and measured evidence (A7/B7).
