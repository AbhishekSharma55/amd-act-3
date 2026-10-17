# Independent review of Muskan PRs 22–27

Reviewed pinned original sources on 2026-10-17. The review did not merge branches, push source changes, or post public reviews. Issue #11 is separately published as draft PR #28. No AMD requests or paid resources were used. The two reproduced findings below remain present after issue 11 / draft PR 28 (`dc98ca1559bf260877ca9ece2ae87aac533632d9`), which does not change the backend implementation.

## Overall assessment

The normal synthetic demo works and the existing automated checks pass. I found **two material P2 correctness issues**, one in review revalidation and one in replay. I found no P1 issue in the reviewed scope. Address these before describing the pipeline as handling the relevant edge cases reliably. The extraction/replay findings do not invalidate the reproduced default demo numbers.

| PR | Pinned head | Assessment |
| --- | --- | --- |
| 22 foundation | `4182d881a70eabcbe4293ad2ebb51f2a0846bc0d` | No material finding. Shared entry point, canonical errors, stored evidence and CI integrate with the already merged checker/approval work. |
| 23 extraction/review | `b8e56bb556b8601fc3f11ac1f9e8f57289a98527` | **P2 finding 1:** an unresolved hard/soft-date review can disappear during unrelated revalidation. Real AMD execution remains unverified. |
| 24 solver | `d532595f380c3b4f1072e7bc61d215c547ff77f7` | No additional material finding. Demo schedules, independent checker, overtime limits/costs, fresh solve IDs, stored reviewed/rejected constraints and approval integration pass the available checks. Inherits finding 1 through its review gate. |
| 25 replay | `003ceb6566cf183bfebfc07bb992aff824ec3e0f` | **P2 finding 2:** running operations can continue through a future outage in sampled futures. Default demo replay is reproducible. |
| 26 workflow UI | `42a71f3f16f1af1b391fdb7bbdc9b271a50523c0` | Original frontend has stale-request/state/provenance problems addressed by issue 11. Treat `dc98ca1` / PR 28 as the accompanying mitigation, not as an optional unrelated UI change. No additional material UI finding from this review. |
| 27 evaluation | `075170f62d22d4f5c4fbcec77c9523fe19e62b2f` | Saved offline metrics and all 19 recovery rows reproduce. Useful draft evidence with the limitations below; no additional code blocker identified. |

## Findings

### P2 — PR 23: retain an unresolved review when rechecking normalized proposals

**Pinned source:** `b8e56bb:backend/app/validate.py:323–329`, especially `_check_one(raw, ...)` at line 323. The lossy normalization occurs at `backend/app/validate.py:195–198`, where a missing `hard` field becomes `hard: false` plus a review warning. This file is unchanged in later pinned PRs.

`review_constraints()` validates the already normalized constraint, so it no longer sees that the model omitted the hard/soft flag. Revalidating another item changes the date from `review` to `ok` without the planner accepting or editing it. This is reachable through the normal UI because editing one item submits all kept constraints to `/api/constraints/revalidate`.

**Deterministic repro:** `docs/reviews/reproduce-muskan-findings.py`, first case. Stub the model with an unknown-machine outage and a due-date proposal that omits `hard`, for this message:

> Mill 4 is down until 14:00. J7 must ship at 12:00.

Extraction returns `c2` as `status: review`, `hard: false`, with the warning that fixedness needs confirmation. Correct only `c1.machine` to `M1` and submit the unchanged, unaccepted `c2` alongside it for revalidation.

**Actual result:** `c2` becomes `status: ok`, loses its warning, and still has `origin: amd_model`. Solving that response returns HTTP 200 with **J7 105 minutes late**. No decision accepting a soft date was made. Independently reproduced by the parent reviewer as well.

**Minimal fix:** preserve the missing-field/interpretation review provenance for unedited items, or revalidate those items against their original raw proposals. Clear it only after an explicit acceptance or a relevant edit. Cross-item contradictions should still be allowed to disappear when the other conflicting item is rejected. Add a regression for revalidating one constraint while another still needs confirmation, and assert that solve rejects the unconfirmed date.

### P2 — PR 25: sampled running work bypasses future outages

**Pinned source:** `003ceb6:backend/app/replay.py:57–66`. The running branch at lines 57–59 keeps the observed start and randomizes remaining work, but outage checks at lines 64–66 run only in the unstarted branch.

A checked plan can finish a currently running operation just before a future outage. Noise can extend its remaining work into that outage. The replay then continues processing during machine unavailability and propagates the premature completion to later operations, understating disruption risk.

**Deterministic repro:** `docs/reviews/reproduce-muskan-findings.py`, second case. Use the unchanged fixture and a reviewed M1 outage **10:11–11:00**. The solver keeps running J6 op 1 at **09:00–10:10**; the independent checker correctly accepts this nominal schedule. Replay 500 samples, seed 7, default duration spread `[0.9, 1.3]`, and zero extra repair delay.

**Actual result:** **156 of 500 samples** run J6 op 1 through the known outage start. Latest sampled finish is minute `612.8176009232654` (about 10:12:49). Its observed start remains 09:00, but it is allowed to keep working after M1 goes down at 10:11. Independently reproduced by the parent reviewer as well.

**Minimal fix:** handle future-outage intersections for randomized remaining running work as well. Preserve the observed history, then apply the declared interruption/restart policy and propagate its delay; if that case is unsupported, flag or reject it explicitly instead of counting processing through the outage as a valid future. Add a test whose nominal running completion precedes an outage but whose sampled remaining duration crosses it. Avoid fixing this by moving the observed historical start.

## Verification

All Python commands used `AMD_API_KEY='' AMD_API_BASE='' AMD_MODEL=''`. The existing environment is `/tmp/amd-act-3-issue11-env/bin/python`; no credentials were inspected or printed.

| Check | Command / location | Result |
| --- | --- | --- |
| Pinned backend tests | `/tmp/amd-muskan-review`: `python -m pytest -q backend/tests` | **119 passed, 97 subtests passed** |
| Saved checker reports | `PYTHONPATH=backend python -m app.checker_report --check` | Current; hashes match |
| Planning regressions | `plan/prototype`: `python regression_checks.py` | **20 passed** |
| Original PR 26 frontend with PR 27 applied locally | `/tmp/amd-muskan-ui/frontend`: `npm ci --ignore-scripts`, `npm test`, `npm run build` | **24 tests passed; production build passed** |
| Rules evaluation | `python eval/run_eval.py extraction --extractor rules` | **13/23 complete-change accuracy; 2 false acceptances; 9/12 useful review**. Differences from committed results are timestamp/latency only. |
| Recovery evaluation | `python eval/run_eval.py recovery` | All **19 result rows exactly match** pinned `eval/results/recovery.json`; timestamp differs. |
| Edge-case repros | `python /tmp/amd-muskan-repros.py` | Both incorrect behaviors above reproduced |

The frontend assembly was an isolated detached worktree at PR 26 plus `git cherry-pick --no-commit 075170f`; it has no source conflicts. The backend worktree is detached at PR 27. Generated evaluation outputs changed only inside the disposable review worktree. The original issue 11 worktree was read only. I did not repeat the parent's browser suite; the parent reports issue 11 passed 119 backend tests, 30 frontend tests and 31 Chrome/Firefox browser checks.

Re-run the two findings with:

```bash
# From a checkout containing the reviewed backend stack:
AMD_API_KEY='' AMD_API_BASE='' AMD_MODEL='' \
  python docs/reviews/reproduce-muskan-findings.py
```

## Evidence limitations to retain in the demo/submission

- **Live AMD inference is UNVERIFIED.** Tests stub extraction; the offline rule run is not AMD evidence. PRs 22/23/26 correctly leave their real-call done checks open. No Token Factory model, latency, endpoint behavior, JSON-mode compatibility or extraction accuracy has been confirmed here.
- The rule baseline has known semantic errors. Reproduced false acceptances include assigning J6's 17:00 date to J4 in the multi-fact message and expanding “one hour of overtime” to the fixture's full 20:00 limit. A labeled fallback remains a limited parser, even when structural validation passes.
- Labels are still one builder's **DRAFT** labels. Independent labeling/reconciliation is unfinished. Do not present 13/23 or later AMD results as an independently validated benchmark.
- Recovery results are synthetic. Separate selection/evaluation seeds are correctly used, but **h1 is explicitly the existing demo case**, so it should be described as a demo/reference case rather than one of seven wholly held-out scenarios. Preserve/freeze the other cases before further tuning.
- The generated sentence at `075170f:eval/run_eval.py:188` says “10 s budget for every method.” In fact line 139 gives the CPU reference one solve, while line 142 invokes 2–3 policy solves, each with a 10 s cap (`solver.py:228–235`). Describe this as **10 s per policy solve**, or implement/report an equal total optimization budget before making an equal-budget comparison. The reproduced cases finish optimally quickly, so this caveat does not explain away or alter their observed rows.
- Replay shown changes the selected plan in two of six feasible cases; no gain is shown in four, and h5 is infeasible. The h6 choice trades more nominal tardiness/overtime for lower sampled lateness. “All promises kept” uses each selected plan's own nominally on-time jobs; compare it alongside tardiness and weighted lateness rather than as an identical promise set across plans.

## Safe integration approach

1. Keep the current main and original PR heads intact while the user reviews these findings. Do not integrate before that decision.
2. The ancestry is `main(bb58034) → 22 → 23 → 24 → 25`, then sibling PRs **26 and 27**. Issue 11 / PR 28 adds implementation commit `dc98ca1` after 26, followed by this review's documentation. Review/fix the two backend issues in an isolated integration/fix branch based on the accepted stack; do not amend teammates' pinned sources silently.
3. For sequential GitHub integration, merge 22 into main, then **explicitly verify/retarget 23 to main**, then 24, then 25, then 26 and 27 in either order. Never merge a child PR into its old feature branch after that feature branch has already been merged into main. Do not rely on branch deletion or automatic retargeting.
4. Bring issue 11's implementation (`dc98ca1`) and subsequent review documentation onto the accepted 26+27 stack, or retarget/rebase PR 28 onto the resulting main. Its full branch contains ancestors 22–26, so do not treat the entire branch as a standalone pre-stack UI patch. The parent independently confirmed a clean `git merge-tree` for `dc98ca1` plus 27.
5. Run the backend/frontend checks, both new regression cases, offline evaluation and the workflow browser checks on the final combined tree. Preserve the real-AMD and independent-labeling gaps until actual evidence exists. User approval/integration remains the next external action; this reviewer performed neither.
