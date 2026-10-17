# Approval and export · issue #8

The approval path is implemented without AMD or solver dependencies. It uses the
existing `POST /api/approve` request and response contract. No backend entrypoint
owned by the foundation work is changed.

## Try the complete synthetic flow

Use the Python environment described in [factory setup](README-factory.md).
It already provides the runtime and test dependencies; no new packages are
needed. From the repository root:

```bash
backend/.venv/bin/python -m uvicorn app.approval_dev:app --app-dir backend --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
cd frontend
npm ci
npm run dev -- --port 5173
```

Open <http://127.0.0.1:5173>, choose **Sample recovery**, accept J2's late
delivery, enter an approver name, and approve. The local service checks its own
stored plan at that moment and returns dispatch CSV and decision JSON. Both
downloads belong to that run. The name is a demo audit field, not authenticated
identity. This service sends no AMD request and dispatches nothing to a factory.

`approval_dev.py` seeds only the checked saved example, including its `MOCK`
extraction trace and stored synthetic replay. Its fixed sample ID matches the
frontend's saved example; its one-hour session expires or disappears on process
restart. Restart the sample service and reload the page to begin a new sample
session. The shared live backend must create fresh solve IDs instead.

## Shared backend integration

The live solver/run-store integration remains with issues #2/#6. Create one
`ApprovalStore` for the app process, or adapt the shared run store to the same
atomic approval behavior. Mount the approval router in the foundation's app:

```python
from app.approval_api import create_approval_router
from app.approval_store import ApprovalStore

approval_store = ApprovalStore()
app.include_router(create_approval_router(approval_store))
```

After source validation and human review, the solve handler stores a **new**
snapshot and returns its new ID instead of the extraction draft ID:

```python
from app.approval import required_concessions

for alternative in alternatives:
    alternative["concessions"] = required_concessions(
        fixture, reviewed_constraints, alternative["schedule"]
    )

run_id = approval_store.save_run({
    "fixture": fixture,
    "message": original_message,
    "trace": actual_extraction_trace,
    "constraints": reviewed_constraints,  # keep rejected decisions too
    "alternatives": {a["id"]: a for a in alternatives},
    "data_notice": "Synthetic demo data",
})
```

Only the server calls `save_run`; there is no HTTP endpoint accepting a client
snapshot. JSON serialization isolates the stored fixture, constraints and
schedules from later mutations. Reusing a run ID fails with 409; `get_run`
returns a copy. Defaults are a fresh UUID-based ID and a one-hour TTL. In-memory
storage is intended for the single-process hackathon deployment; workers do not
share it and restarts lose it.

The replay handler can store the actual result with
`approval_store.save_replay(run_id, alternative_id, response)`. Both IDs must
match that run. Approval captures this stored replay and its assumptions; absent
replay is `null`. Approved runs reject replay replacement. New analysis requiring
changed records should use a fresh solve.

## Approval rules

- Accept exactly four request fields: run ID, alternative ID, approved concession
  IDs, and approver. Reject client schedules, constraints, trace, replay,
  concession definitions, checker results and approval timestamps.
- Retrieve the immutable server snapshot, rerun the independent checker, and
  enforce the alternative's reroute/overtime policy. Hard-date relaxation is
  unsupported; hard dates stay hard.
- Recompute late deliveries using every accepted due-date update. Compute
  occupied overtime per operation with `max(0, end - max(start, shift_end))`;
  charge hourly rate × minutes / 60, rounded to two decimals. Neither cached
  concession lists nor cached KPIs/checker flags can bypass this calculation.
- Require exactly the derived IDs and a nonblank name. IDs follow the guide's
  deterministic `k1`, `k2`, … order: jobs sorted by ID, then overtime.
- Lock the run at approval. An identical retry returns the original record and
  timestamp; a different approval gets 409. A lock makes concurrent clicks
  atomic. Unknown runs/alternatives return 404, expired runs 410, invalid plans
  or missing approvals 422. Errors use the canonical `{error:{...}}` shape.

CSV rows are sorted by machine then start, with a per-machine sequence. Change
labels are derived from the fixture, accepted outages and selected schedule,
rather than trusting cached annotations. The decision JSON contains the original
message, reviewed constraints including rejections, selected plan/fixture,
recomputed concessions, fresh checker result, actual stored trace, stored replay
or `null`, approver and timezone-aware approval time. The extra audit details
live inside `decision_record`; the existing response envelope stays unchanged.

## Frontend integration and checks

`ApprovalPanel` takes `runId`, `alternative`, optional `sample`, `hidden`, and
`onInvalidRun`. A new run/alternative resets the form, cancels pending work and
revokes old download URLs. Hiding a panel while inspecting another timeline
preserves the same plan's decision. The current app uses the saved example;
replace those props with the selected live solve when issue #6 lands.

Approval always uses the service transport, including in sample mode. The shared
mock transport refuses `/api/approve` so a canned response cannot approve a new
decision. Only a matching, passing approval response enables downloads. A lost
response can be retried with the same identity and IDs to retrieve the original
decision. Live integration should handle `onInvalidRun` by returning to a fresh
solve; the reusable component blocks further submissions for expired/locked runs.

```bash
backend/.venv/bin/python -m unittest discover -s backend/tests -v
PYTHONPATH=backend python3 -m app.checker_report --check
cd frontend
npm test
npm run build
```

See [verification evidence](../docs/APPROVAL_QA.md) for the tested trust boundaries,
actual download checks and browser screenshots.
