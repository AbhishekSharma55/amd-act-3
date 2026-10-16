# 07. Demo, video and submission

Main owner: B. A narrates the backend and AMD parts. The judging criteria are **Application of Technology, Presentation, Business Value and Originality** (`context/guidlines.txt`). Every section below serves at least one of them.

## The story in one line

> "Your machine stopped. Rehearsal shows which orders you can still promise, and tests the recovery before you commit."

## Live demo script (also the video's core, about 2.5 minutes)

| # | Screen action | What we say | Criterion |
| --- | --- | --- | --- |
| 1 | Timeline at 10:00, all jobs on time | "A machine shop's day plan. Seven orders, three machines. It's 10 a.m." | Presentation |
| 2 | Paste: *"Mill M2 is unavailable until 14:00. Order J7 still needs to ship at 16:00. Overtime requires approval."* → **Read message** | "The supervisor's note goes to an open model running on AMD." | Application of Technology |
| 3 | Constraints appear; click each to highlight its source text. Point at the issue "interrupts J1 op 2" | "Every constraint is tied to the exact words it came from, and checked against the real machine list. The model cannot invent a machine or a deadline." | Originality |
| 4 | Change the message to "Mill 4 is down after lunch" → review items → Reject | "When it's unsure, it asks a person instead of guessing." | Originality |
| 5 | Back to the demo message → **Find recovery plans** | "A CP-SAT solver builds the alternatives; a separate checker verifies every one." | Application of Technology |
| 6 | Red card: keep machines is impossible, conflict c1 + c2 | "Keeping the machines can't save J7. It tells us why, instead of quietly moving the deadline." | Business Value |
| 7 | Re-route card: J7 on time, J2 late 190 min | "Re-routing saves J7, but J2 will be late. That's a decision for a person." | Business Value |
| 8 | **Show a failure** → J4 on time in only 239 of 500 scenarios; the failing timeline shows M1 as the bottleneck | "On paper J4 has 25 minutes of slack. In simulated futures where operations run a little long, it misses its date. That's the promise we would have broken." | Originality, Presentation |
| 9 | Tick the concession, approver name → **Approve** → CSV + decision record download | "The planner approves with the trade-offs in plain view, and the shop floor gets a dispatch list plus an audit record." | Business Value |
| 10 | Open the Run inspector | "Here is the actual AMD call: model, latency, tokens and raw output, plus the checker and replay records." | Application of Technology |

Before recording, re-check every number in this script against the real deployed app. The numbers above come from our scratch prototype (see `02_DATA_MODEL.md`).

## Video (target 4-4.5 minutes; confirm the limit in the form)

| Time | Content |
| --- | --- |
| 0:00-0:25 | Problem and user: a production planner at a make-to-order machine shop. A machine goes down, and today the reschedule happens by hand, under time pressure, with promises at risk |
| 0:25-3:00 | The live demo script above, sped up where it waits on loading |
| 3:00-3:30 | Evidence: the extraction evaluation table (A7), checker results, replay counts, and what is synthetic |
| 3:30-3:55 | Architecture: AMD model → validation → CP-SAT → checker → replay → approval. What runs on AMD |
| 3:55-4:30 | Business value and the honest limits: who buys it, an illustrative planner-time calculation, what is not yet validated, next steps |

Recording tips: 1080p, browser zoom at 110-125%, a short silent mouse pause on every key number, one take per section, then join them.

## Slides (PDF, about 10 slides)

1. Title + one-line pitch
2. The user and the problem (a planner's disruption morning)
3. What Rehearsal does: the 5-step flow
4. Demo screenshots: source-linked constraints and review
5. Alternatives + infeasible explanation
6. "Show a failure": the J4 counterexample
7. Architecture and **what runs on AMD** (diagram)
8. Evidence: extraction results (N messages, builder-labeled), checker, replay, latency
9. Business value: planner minutes × incidents × hourly cost, labeled as illustrative; the pilot path (shadow planning first)
10. Limits, next steps, team

The project decision gives an illustrative example: 40 incidents × 30 minutes × $35/hour = $700/month of released planner capacity. It is **unvalidated**: label it as illustrative and do not call it savings.

## Submission checklist (lablab form)

| Item | Owner | Done |
| --- | --- | --- |
| Project title: "Rehearsal" | B | ☐ |
| Short description (one sentence) | B | ☐ |
| Long description: problem, user, what it does, what runs on AMD, evidence, limits | A + B | ☐ |
| Challenge selected: **Intelligent Industry** | B | ☐ |
| Technology tags (AMD, Token Factory, the model name, OR-Tools, FastAPI, React) | B | ☐ |
| Cover image | B | ☐ |
| Video uploaded, plays from a logged-out browser | B | ☐ |
| Slides PDF | B | ☐ |
| GitHub repo **public**, README runs, no keys in history, `research/sources/` removed or justified | A | ☐ |
| Application URL works from a logged-out browser | B | ☐ |
| Demo platform named (e.g. Hugging Face Spaces) | B | ☐ |
| Both members: AMD AI Developer Program + lablab team membership confirmed | Both | ☐ |
| Submitted by **Oct 17, 6 PM IST** (protective target) | Both | ☐ |

## README must answer (B6, with A's input)

- What Rehearsal does, in 3 lines, plus a screenshot or GIF.
- **What runs on AMD**: the model, the endpoint (no key) and where in the code it is called.
- How to run: `.env` setup, `docker build` / `docker run`, or the local dev commands.
- Data notice: the fixture and messages are synthetic or team-authored.
- Evaluation: the A7 table, with N and who labeled it.
- Replay assumptions and what "X of N" means.
- Limits: non-preemptive restart only, a single day, no ERP integration, unvalidated business numbers.
- License and third-party notices (OR-Tools is Apache-2.0; check the licenses of any dataset or model we use).

## Questions judges may ask (prepare one-line answers)

- What does the AMD model do that matters? *It turns the unstructured note into the constraints that decide the plan, and every call is visible in the inspector.*
- What if the model is wrong? *Validation catches unknown IDs, bad times and quotes that are not in the message; complete ambiguous interpretations need confirmation; missing fields or unknown IDs need correction and revalidation or rejection. False acceptance is measured in A7.*
- Isn't this just Siemens APS with chat? *APS tools schedule. Our contribution is the checked path from the message to an approved decision: source spans, an independent checker, a replayed counterexample and an audit record.*
- How do you know the plan is valid? *A separate checker, with no solver code, re-verifies every alternative and again at approval.*
- Is "239 of 500" a real probability? *No. It is a count under declared synthetic assumptions, and we say so on screen.*
- What would a pilot look like? *Shadow planning on historical disruptions first, measuring planner time to a correct approved plan.*
