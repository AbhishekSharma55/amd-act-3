# Independent schedule checker

`app.checker.check(fixture, constraints, schedule)` checks the one-day,
non-preemptive scheduling model independently of the optimizer. It uses only the
Python standard library and returns the existing contract:

```python
from backend.app.checker import check

result = check(fixture, accepted_constraints, schedule)
# {"valid": False, "violations": ["J2 op 1 overlaps outage c1 on M2 (10:00–14:00)", ...]}
```

The checker collects every violation it can evaluate, including malformed input,
instead of stopping after the first failed rule. It never mutates the inputs.
No solver, FastAPI, AMD key, network access, or new HTTP endpoint is needed.

## Rules and boundaries

- Every fixture operation appears exactly once, with known IDs, an eligible
  machine, strict `HH:MM` clocks, and the full positive integer duration for that
  machine. Boolean values cannot masquerade as operation IDs or integer minutes.
- Operations follow their order in `job.ops`. Every overlapping pair on a machine
  is reported, including intervals contained inside a longer interval.
- Machine outages are half-open intervals `[from, until)`. Touching endpoints
  are allowed. Every accepted outage is checked; several intervals on one machine
  are supported. Only an omitted `from` defaults to `now`; null/blank clocks fail.
- Work whose committed start is before `now` stays on its observed machine and
  times. Completed work (`committed.end <= now`) stays frozen even when a
  retroactive outage conflicts with its history; planning does not erase past
  observations. Unchanged frozen observations are exempt from historical outage
  feasibility checks.
- A genuinely running operation (`committed.start < now < committed.end`) that
  intersects any accepted outage on its committed machine must restart with the
  **full** duration of the chosen eligible machine. This includes an outage that
  began at/before its start, or whose repair already finished before `now`.
  New/restarted work cannot begin before `now` or shift start. Restarting on an
  alternate machine may happen before the failed machine is repaired; restarting
  on that machine must avoid its outage. Work beginning exactly at `now` is new
  work; work ending exactly at `now` is completed.
- Normal shift end applies unless an `ok` or `accepted` overtime constraint
  explicitly has `allowed: true`. Its effective cutoff is the minimum of every
  accepted allowed cutoff and the fixture limit. Omitted/null overtime `until`
  defaults to the fixture limit. A cutoff before shift end or beyond the fixture
  limit is invalid. Allowed and forbidden overtime together are contradictory;
  forbidden overtime cannot extend the shift.
- Hard due dates apply to the last completion of every operation in that job.
  A soft due date changes business reporting elsewhere and is not a feasibility
  restriction.

Every active constraint is revalidated, including one marked `accepted`. It
needs a unique ID, supported type and origin, nonempty source span, correctly
typed parameters, `issues` and `blocking_issues` string arrays, an empty blocking
list, and `ok`/`accepted` status. Unknown IDs, unresolved/review items, missing
repair times, unsupported types, invalid hard/allowed booleans, inconsistent due
dates or priorities, and contradictory overtime fail. Rejected items are ignored.
Identical repeated updates with distinct IDs are harmless; multiple allowed
overtime cutoffs narrow the window with their minimum.

The function receives no original disruption message. It checks source-span
structure, while source matching and semantic interpretation remain the
extraction/review layer's responsibility. It also receives no solver policy or
concession acknowledgments: callers must enforce policy and approval separately.
A passing result is neither human approval nor permission to dispatch.

## Server integration

The solver should call this function for each candidate alternative using the
server's fixture and effective accepted constraints. Attach the returned
`{valid, violations}` unchanged to the alternative; never label a failing plan
verified. Replay should start from a checked nominal plan. Variable simulated
durations are not nominal machine durations and are not represented as fresh
checker passes.

Approval must retrieve the immutable fixture, constraints, and schedule from the
server run store, run this checker again, and reject a failing result before
export. A client-supplied checker result or saved frontend report is not authority
for approval. This feature adds the checker module and result display; the
solver/run-store and approval features will connect those calls.

## Reproducible saved frontend reports

`shared/checker-reports.json` contains actual checker results for three synthetic
records: committed work without disruption, the first saved recovery alternative
under the saved extraction constraints, and the original committed work under
those same constraints. The first two must pass; the disrupted original must
fail. These are saved local results, with no live backend validation or AMD call.

The provenance identifies exact JSON pointers and SHA256 hashes of the fixture,
extraction file, solver sample file, and checker implementation. Regenerate after
any of those sources change; the generator refuses unexpected positive/negative
outcomes. From the repository root:

```bash
PYTHONPATH=backend python3 -m app.checker_report
PYTHONPATH=backend python3 -m app.checker_report --check
python3 -m unittest backend.tests.test_checker -v
```

`--check` recomputes the actual outcomes and hashes and exits nonzero for stale or
altered saved records. The frontend's reusable `CheckerResult` consumes the same
result contract, shows all violations, and labels these records as saved checks.
It does not borrow their passing result for a live factory or replay timeline.

The unit suite includes the checked positive samples, six required broken-plan
cases, nested overlaps, malformed input, accepted-constraint bypass attempts,
18:30 versus 18:31 cutoff, every restart/history boundary above, multiple outages,
endpoint adjacency, all-violations aggregation, deterministic report freshness,
and refusal to save unexpected outcomes.
