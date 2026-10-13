# Rehearsal — AMD Developer Hackathon: ACT III

**Test a factory's recovery plan before changing the shift.**

Rehearsal is the selected project for AMD Developer Hackathon: ACT III, entering the **Intelligent Industry** challenge. A production planner supplies the current schedule and an operational disruption. The product will return checked recovery alternatives, threatened delivery commitments, required concessions, replayable failure scenarios, and an approved dispatch revision.

Our objective is to maximize our chances of winning the main AMD award through a useful product, distinctive execution, measurable evidence, and substantive AMD computation.

## Current status

- Hackathon research and independent Astra project selection are complete.
- Product implementation has not started. The next working session begins implementation.
- Team: two members. Project ambition is not capped by team size or assumed effort.
- Budget: **$100 AMD allocation supplied by the hackathon, plus up to $20 personal spending**.
- Benchmarks, GPU acceleration, extraction quality, customer adoption, and business benefits have not yet been validated by our own experiments.

This repository is **private** for preparation, as requested. The event calls for a public GitHub submission; resolve visibility during submission preparation.

## Start here

1. [Astra's project decision](research/ASTRA_PROJECT_DECISION.md) — chosen product, buyer, demo, architecture, alternatives, evaluation, budget, and risks.
2. [Hackathon research and winning strategy](research/AMD_ACT_III_WINNING_STRATEGY.md) — sponsor objectives, judging criteria, past winners, competitors, and submission requirements.
3. [Project selection scorecard](research/PROJECT_SELECTION_SCORECARD.md) — the evidence behind our selection framework.
4. [Organizer clarification questions](research/ORGANIZER_QUESTIONS.md) — deadline, award structure, partner eligibility, and deployment requirements. Nothing has been sent.
5. [Research source guide](research/README.md) — provenance and snapshot notes.

## Proposed product flow

1. Import jobs, machine capabilities, the committed schedule, and shift constraints.
2. Read an operational message using an open model running on AMD.
3. Show source-linked constraint proposals and request review for ambiguity.
4. Generate candidate schedules using a conventional CPU solver.
5. Independently check schedules against the accepted constraints.
6. Rehearse alternatives using declared uncertainty scenarios, including AMD GPU replay.
7. Show tradeoffs and failure examples; obtain approval for concessions.
8. Export a revised dispatch list with a reproducible decision record.

GPU performance gains must be measured against a competent CPU implementation. Simulation outcomes must remain distinguishable from real factory benefits.

## Next working session

- Verify the supplied AMD allocation, available compute, Token Factory models, and service limits.
- Pin the benchmark and software versions; inspect the selected data and supported scheduling semantics.
- Run one real AMD extraction experiment and check the result against a labeled fixture.
- Establish a known feasible scheduling case, an infeasible variation, and an independent schedule checker.
- Establish CPU/GPU replay agreement before making performance claims.
- Define held-out evaluation cases and baselines before tuning.

These are planned checks; they have not been run. The complete design and limitations are in the Astra decision memo.

## Repository contents

```text
context/                     Original hackathon material supplied by the participant
research/                    Strategy, decision, scorecard, and organizer questions
research/sources/            Public source snapshots and extracted page data
research/astra/              Astra's additional research snapshots and source index
research/tools/              Public-source collection helper
```

Public source snapshots preserve the research state; current official requirements can change. Submission timing remains inconsistent across organizer pages, so consult the recorded deadline evidence and obtain authoritative clarification before final submission.

[Official ACT III event](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii)
