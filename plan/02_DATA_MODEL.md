# 02. Data model

This file defines what the factory data looks like, what a constraint is, and which demo scenario we build toward. Both tracks use it.

## Conventions

- One working day. All times in JSON are `"HH:MM"` strings in 24-hour local factory time. The backend converts them to integer minutes since 00:00 internally.
- IDs are short and stable: machines `M1`, jobs `J7`, operations are `(job, op)` with `op` starting at 1.
- Durations are integer minutes.
- All business data in the demo is **synthetic** and must be labeled as synthetic in the UI and README.

## Factory fixture (`shared/fixture.json`)

| Field | Meaning |
| --- | --- |
| `now` | The current time. Operations that started before `now` are **frozen** (finished or in progress) unless an outage interrupts them |
| `shift` | Normal shift `start`/`end`, plus an optional overtime window up to `overtime_until`, with a cost per machine-hour. Overtime always needs approval |
| `machines[]` | `id`, display `name` and `aliases`. Aliases are how we resolve "big mill" or "VMC-2" to `M2` without trusting the model |
| `jobs[]` | `id`, `customer`, `due`, `priority` (1 = normal, 3 = critical) and ordered `ops[]` |
| `ops[].eligible` | Map of machine ID → duration in minutes on that machine. This is the **only** source of machine compatibility; the model can never add one |
| `committed_schedule[]` | The plan the shop floor is currently running. One entry per operation: `job`, `op`, `machine`, `start`, `end` |

### Example fixture (also in [`mocks/factory.json`](mocks/factory.json); copy it into `shared/fixture.json`)

The committed schedule below was produced once by our scratch prototype (CP-SAT, minimizing weighted tardiness and then job completion times, with no disruption) and is stored as fixed data. Do not regenerate it during the demo.

```json
{
  "factory": "Demo Machine Shop (synthetic data)",
  "date": "2026-10-16",
  "now": "10:00",
  "shift": {
    "start": "08:00",
    "end": "18:00",
    "overtime_until": "20:00",
    "overtime_cost_per_hour": 45,
    "overtime_requires_approval": true
  },
  "machines": [
    {"id": "M1", "name": "Mill M1", "aliases": ["mill 1", "vmc-1", "m1"]},
    {"id": "M2", "name": "Mill M2", "aliases": ["mill 2", "vmc-2", "big mill", "m2"]},
    {"id": "M3", "name": "Lathe L3", "aliases": ["lathe", "lathe 3", "l3", "m3"]}
  ],
  "jobs": [
    {"id": "J1", "customer": "Acme Pumps", "due": "12:00", "priority": 2,
     "ops": [{"op": 1, "eligible": {"M3": 60}}, {"op": 2, "eligible": {"M2": 45, "M1": 70}}]},
    {"id": "J2", "customer": "Birla Valves", "due": "13:00", "priority": 1,
     "ops": [{"op": 1, "eligible": {"M2": 90}}, {"op": 2, "eligible": {"M3": 40}}]},
    {"id": "J3", "customer": "Coastal Marine", "due": "15:00", "priority": 1,
     "ops": [{"op": 1, "eligible": {"M1": 60, "M2": 50}}, {"op": 2, "eligible": {"M3": 50}}]},
    {"id": "J4", "customer": "Delta Auto", "due": "17:00", "priority": 1,
     "ops": [{"op": 1, "eligible": {"M3": 45}}, {"op": 2, "eligible": {"M1": 90}}]},
    {"id": "J5", "customer": "Everest Tools", "due": "16:00", "priority": 1,
     "ops": [{"op": 1, "eligible": {"M2": 80, "M1": 110}}, {"op": 2, "eligible": {"M3": 30}}]},
    {"id": "J6", "customer": "Fusion Robotics", "due": "17:30", "priority": 1,
     "ops": [{"op": 1, "eligible": {"M1": 70}}, {"op": 2, "eligible": {"M2": 60, "M1": 85}}]},
    {"id": "J7", "customer": "Gamma Aerospace", "due": "16:00", "priority": 3,
     "ops": [{"op": 1, "eligible": {"M3": 40}}, {"op": 2, "eligible": {"M2": 100, "M1": 140}}, {"op": 3, "eligible": {"M3": 30}}]}
  ],
  "committed_schedule": [
    {"job": "J1", "op": 1, "machine": "M3", "start": "08:00", "end": "09:00"},
    {"job": "J1", "op": 2, "machine": "M2", "start": "09:20", "end": "10:05"},
    {"job": "J2", "op": 1, "machine": "M2", "start": "10:05", "end": "11:35"},
    {"job": "J2", "op": 2, "machine": "M3", "start": "11:45", "end": "12:25"},
    {"job": "J3", "op": 1, "machine": "M1", "start": "08:00", "end": "09:00"},
    {"job": "J3", "op": 2, "machine": "M3", "start": "09:00", "end": "09:50"},
    {"job": "J4", "op": 1, "machine": "M3", "start": "10:20", "end": "11:05"},
    {"job": "J4", "op": 2, "machine": "M1", "start": "11:35", "end": "13:05"},
    {"job": "J5", "op": 1, "machine": "M2", "start": "08:00", "end": "09:20"},
    {"job": "J5", "op": 2, "machine": "M3", "start": "09:50", "end": "10:20"},
    {"job": "J6", "op": 1, "machine": "M1", "start": "09:00", "end": "10:10"},
    {"job": "J6", "op": 2, "machine": "M1", "start": "10:10", "end": "11:35"},
    {"job": "J7", "op": 1, "machine": "M3", "start": "11:05", "end": "11:45"},
    {"job": "J7", "op": 2, "machine": "M2", "start": "11:45", "end": "13:25"},
    {"job": "J7", "op": 3, "machine": "M3", "start": "13:25", "end": "13:55"}
  ]
}
```

At `now = 10:00`, this committed schedule has every job on time. Three operations are running at 10:00: J1 op 2 on M2, J5 op 2 on M3 and J6 op 1 on M1.

## The constraint language

The model may only propose these types. Anything else becomes `type: "unsupported"` with `status: "review"`. This narrow, typed language is a design rule from the project decision: the model never writes solver code.

| `type` | Fields | Meaning | Example source text |
| --- | --- | --- | --- |
| `machine_down` | `machine`, `from` (optional, defaults to `now`), `until` | Machine is unavailable in `[from, until)` | "Mill M2 is unavailable until 14:00" |
| `due_date` | `job`, `time`, `hard` (bool) | New or confirmed due time. `hard: true` means the plan **must** meet it; the solver never relaxes it silently | "Order J7 still needs to ship at 16:00" |
| `priority` | `job`, `level` (1-3) | Changes the tardiness weight | "J4 is now urgent" |
| `overtime` | `allowed` (bool), `until` (optional) | Whether the overtime window may be used. `allowed: true` still creates a concession that a person must approve | "Overtime requires approval", "No overtime today" |
| `unsupported` | `note` | Something the system cannot model, such as a material shortage or a quality hold | "Wait for the inspection report on J3" |

### Constraint object (as returned by `/api/extract`)

```json
{
  "id": "c1",
  "type": "machine_down",
  "params": {"machine": "M2", "from": "10:00", "until": "14:00"},
  "source_span": "Mill M2 is unavailable until 14:00",
  "status": "ok",
  "issues": [],
  "origin": "amd_model"
}
```

| Field | Values |
| --- | --- |
| `status` | `ok`: passed every check. `review`: a person must decide. `accepted` / `rejected`: decided by a person in the UI (the frontend sets these) |
| `issues[]` | Human-readable reasons, e.g. `"Unknown machine 'Mill 4'"`, `"No end time given for the outage"`, `"Two different due dates for J7"`, `"Outage interrupts J1 op 2, which is in progress; it will restart after repair"` |
| `origin` | `amd_model` for model output, `rule_fallback` when the model was unavailable (the UI must show this clearly), `user` for manual edits |

### Validation rules (A2), applied after the model returns

1. `type` is one of the supported types; otherwise `unsupported` + `review`.
2. `machine` / `job` resolve to a fixture ID via ID or alias (case-insensitive). If one does not resolve → `review`.
3. Times parse as `HH:MM` and fall inside the working day. `until` is after `from`. Otherwise → `review`.
4. `source_span` appears in the original message (case- and whitespace-insensitive). If it does not → `review` ("model quoted text that is not in the message").
5. Two constraints contradict each other (two due dates for one job, overtime both allowed and forbidden) → both `review`.
6. A `machine_down` that starts while an operation is running on that machine → `ok`, plus an issue explaining that the operation restarts after the repair. The supported model is non-preemptive with restart. Rework or partial completion is out of scope and must say so.
7. A missing `until` on an outage → `review` with "end time unknown". Never invent a repair time.

Passing these checks proves that the constraint refers to real things. It does not prove that the model understood the meaning correctly, which is why A7 measures semantic accuracy separately.

## Demo scenario and expected outcomes

**Demo message:**

> Mill M2 is unavailable until 14:00. Order J7 still needs to ship at 16:00. Overtime requires approval.

**Expected constraints:** `machine_down(M2, 10:00-14:00)`, `due_date(J7, 16:00, hard)`, `overtime(allowed, needs approval)`. The outage also creates the issue "interrupts J1 op 2".

**What our scratch prototype produced for this scenario** (CP-SAT, 10 s limit, 8 workers; the full solver must re-confirm these results):

| Policy | J7 hard at 16:00 | Result |
| --- | --- | --- |
| Keep machines (no re-routing, overtime allowed) | Yes | **Infeasible.** This is the honest "no plan meets your requirements" moment |
| Keep machines (no re-routing, overtime allowed) | No (relaxed as a concession) | J1 late 165 min, J2 late 335 min, J7 late 55 min, 35 overtime minutes |
| Re-route (alternate eligible machines, no overtime) | Yes | Feasible (OPTIMAL): J1 op 2 restarts on M1, J7 op 2 moves to M1, 7 operations retimed, J7 on time, **J2 late 190 min** (J2 op 1 can only run on M2) |
| Re-route + overtime | Yes | Same as re-route. Overtime does not help here, so the UI should merge identical alternatives instead of showing a fake third option |

**Replay of the re-route plan** (scratch prototype: 500 samples, seed 7, operation durations × triangular(0.9, 1.0, 1.3), M2 repair end 14:00 + uniform(0, 90) min):

| Job | On time in |
| --- | --- |
| J1, J3, J5, J6, J7 | 500 of 500 |
| **J4** | **211 of 500**. On paper J4 finishes at 16:35 against a 17:00 due time, but M1 now carries J1 and J7, so normal duration variation pushes J4 late |
| J2 | 0 of 500 (already late in the plan; an approved concession) |

What these results mean for the demo:
- The planner sees an infeasible result first, together with the reason: J7's hard due time conflicts with "keep machines".
- Re-routing saves J7, but J2 must be accepted as late. This is a concession that has to be approved, and J2's customer is affected.
- **Show a failure** then exposes a weak point the plan does not show: J4 looks safe (25 min slack) but is late in most simulated futures, because M1 became the bottleneck. This is exactly the "broken promise exposed before it reaches the shop floor" moment from the project decision.

Every result above was produced only by our scratch prototype for this fixture. If you tune the fixture, re-run the solver and update this table. Do not present these numbers as measured product results. The full outputs are in [`mocks/`](mocks/).

## Dispatch CSV (output of `/api/approve`)

First rows for the re-route alternative (full file in `mocks/approve.json`):

```csv
machine,sequence,job,op,start,end,changed
M1,1,J3,1,08:00,09:00,frozen
M1,2,J6,1,09:00,10:10,frozen
M1,3,J1,2,10:10,11:20,restarted_on_M1
M1,4,J7,2,11:20,13:40,moved_from_M2
M1,5,J6,2,13:40,15:05,retimed
```

`changed` is `none`, `frozen`, `retimed`, `moved_from_<machine>`, `restarted` (same machine) or `restarted_on_<machine>`.
