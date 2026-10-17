# Evaluation (issue #10)

Small, reproducible evidence for Rehearsal's claims. All data is synthetic and the message labels are builder-authored, so this is a smoke test, not a benchmark.

## Files

| File | What |
| --- | --- |
| `messages.jsonl` | 18 builder-written disruption messages: aliases, 12-hour and bare-hour times, missing/vague times, unknown machine/job, negation, contradiction, out-of-scope, multi-fact, Hinglish |
| `labels/muskan.jsonl` | Muskan's labels (expected typed constraints + whether review is needed) |
| `labels/abhishek.jsonl` | Abhishek's independent labels (PR #29) |
| `labels/final.jsonl` | **To do:** reconciled labels after discussing disagreements. `run_eval.py` uses this when present and says so in every result |
| `recovery_cases.json` | 7 recovery scenarios frozen with the selection rule and seeds: **h1 is the demo/reference case**; h2-h7 (outage, changed due dates, limited overtime, infeasible, two machines) are held out |
| `run_eval.py` | Runs both evaluations and writes `results/` |
| `smoke/` | Raw outputs from `backend/scripts/amd_smoke.py` (model, host, latency; never the key) |

## Run

```bash
.venv/Scripts/python eval/run_eval.py extraction --extractor amd     # live Token Factory, sequential, ~17 calls/min on the shared team key
.venv/Scripts/python eval/run_eval.py extraction --extractor rules   # labeled rule baseline (offline)
.venv/Scripts/python eval/run_eval.py recovery
```

## Extraction metrics

A predicted constraint matches an expected one when the type is equal and every labeled parameter is equal.

| Metric | Definition |
| --- | --- |
| Complete-change accuracy | Every expected constraint found, no wrong item marked `ok`, and review raised when the label requires it |
| False acceptance | Items marked `ok` (auto-accepted) that match no expected constraint. **The most important number** |
| Useful review | Messages that need review and did produce a `review` item |
| Latency | Median and max per live call |

## Recovery comparison

The same CP-SAT engine and search budget are used for every method; it receives the correct typed constraints, so it is a competent reference, not a strawman. The AMD model's role is message interpretation and review. Replay's role is exposing risk before approval.

- **cpu_reference**: one CP-SAT solve with re-routing (and overtime when allowed), minimizing the documented weighted objective.
- **rehearsal_replay_hidden**: Rehearsal's alternatives, chosen by the predeclared nominal rule: lowest weighted tardiness, then overtime cost, then moved operations.
- **rehearsal_replay_shown**: the same alternatives, chosen by the predeclared risk rule on selection seeds 101-103: lowest priority-weighted sampled late probability, then the nominal rule.
- Outcomes are measured on separate held-out seeds 9001-9005 × 500 samples. "Risky promises exposed" lists jobs that are on time in the plan but late in more than 5% of selection samples.
- **Budget:** each policy solve has the same 10 s cap; the reference is one solve and Rehearsal runs 2-3, so this is not an equal-total-budget comparison. All cases solve to optimality in well under a second.
- **"All promises kept"** counts each selected plan's own on-time-in-plan jobs, so two plans can be promising different sets. Read it next to weighted tardiness and expected weighted lateness, not on its own.

Report what the table shows, including cases where replay changes nothing or trades nominal tardiness for lower sampled lateness. No gain is claimed where none is observed.
