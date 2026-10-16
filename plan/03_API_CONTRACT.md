# 03. API contract

This is the agreement between backend (A) and frontend (B). The examples below are shortened for reading. **Complete, valid versions of every response are in [`mocks/`](mocks/)**, generated from our scratch prototype for the demo scenario. Copy them into `shared/mocks/` in Phase 0. When the contract changes, both people agree first and update the mock in the same commit.

- Base path: `/api`. JSON in and out, except the CSV text inside `/approve`.
- Times are `"HH:MM"`. IDs follow `02_DATA_MODEL.md`.
- Errors always use this shape, with a real HTTP status (400 bad input, 422 validation, 502 AMD call failed, 504 timeout):

```json
{"error": {"code": "amd_unavailable", "message": "Token Factory did not respond within 30 s. Please retry.", "retryable": true}}
```

| Endpoint | Purpose | Owner of logic |
| --- | --- | --- |
| `GET /api/health` | Shows whether the AMD key is configured, plus the model name and replay device | A |
| `GET /api/factory` | Returns the fixture (machines, jobs, committed schedule, now, shift) | A |
| `POST /api/extract` | Message → validated constraints, with the AMD trace | A1 + A2 |
| `POST /api/solve` | Accepted constraints → alternatives or an infeasible result | A3 + A4 |
| `POST /api/replay` | One alternative → simulated outcomes + a failing scenario | A5 |
| `POST /api/approve` | Chosen alternative + concessions → dispatch CSV + decision record | A6 |

---

## `GET /api/health`

```json
{"ok": true, "amd": {"configured": true, "model": "MODEL_NAME_FROM_PORTAL", "host": "TOKEN_FACTORY_HOST"}, "replay_device": "cpu-numpy"}
```

`replay_device` is `cpu-numpy` or `gpu-torch-rocm`. The UI shows it in the run inspector.

## `GET /api/factory`

Returns `shared/fixture.json` as is.

## `POST /api/extract`

**Request**
```json
{"message": "Mill M2 is unavailable until 14:00. Order J7 still needs to ship at 16:00. Overtime requires approval."}
```

**Response 200**
```json
{
  "run_id": "r_20261016_101502_ab12",
  "message": "Mill M2 is unavailable until 14:00. Order J7 still needs to ship at 16:00. Overtime requires approval.",
  "constraints": [
    {
      "id": "c1",
      "type": "machine_down",
      "params": {"machine": "M2", "from": "10:00", "until": "14:00"},
      "source_span": "Mill M2 is unavailable until 14:00",
      "status": "ok",
      "issues": ["Outage interrupts J1 op 2 (in progress on M2); it will restart after repair"],
      "origin": "amd_model"
    },
    {
      "id": "c2",
      "type": "due_date",
      "params": {"job": "J7", "time": "16:00", "hard": true},
      "source_span": "Order J7 still needs to ship at 16:00",
      "status": "ok",
      "issues": [],
      "origin": "amd_model"
    },
    {
      "id": "c3",
      "type": "overtime",
      "params": {"allowed": true, "until": "20:00"},
      "source_span": "Overtime requires approval",
      "status": "ok",
      "issues": ["Overtime is a concession and needs approval"],
      "origin": "amd_model"
    }
  ],
  "trace": {
    "provider": "AMD Token Factory",
    "model": "MODEL_NAME_FROM_PORTAL",
    "host": "TOKEN_FACTORY_HOST",
    "latency_ms": 1840,
    "attempts": 1,
    "usage": {"prompt_tokens": 812, "completion_tokens": 164},
    "raw_output": "{\"constraints\": [ ... ]}",
    "fallback_used": false
  }
}
```

A message with problems returns the same shape. The doubtful items have `"status": "review"` and a non-empty `issues` list. For example, "Mill 4 is down" gives `issues: ["Unknown machine 'Mill 4'. Known: Mill M1, Mill M2, Lathe L3"]`.

## `POST /api/solve`

The frontend sends **only** constraints whose status is `ok` or `accepted`. It also sends the concessions the planner allows the solver to consider.

**Request**
```json
{
  "run_id": "r_20261016_101502_ab12",
  "constraints": [ "...the constraint objects from /extract, with status ok or accepted..." ],
  "allow": {"reroute": true, "overtime": true, "relax_hard_due": false},
  "time_limit_s": 10
}
```

**Response 200, feasible**
```json
{
  "run_id": "r_20261016_101502_ab12",
  "status": "ok",
  "alternatives": [
    {
      "id": "alt_reroute",
      "label": "Re-route to qualified machines",
      "policy": {"reroute": true, "overtime": false},
      "solver": {"status": "OPTIMAL", "time_ms": 820, "objective": 19720},
      "schedule": [
        {"job": "J1", "op": 2, "machine": "M1", "start": "10:10", "end": "11:20", "change": "restarted_on_M1"},
        {"job": "J7", "op": 2, "machine": "M1", "start": "11:20", "end": "13:40", "change": "moved_from_M2"}
      ],
      "kpis": {
        "late_jobs": [{"job": "J2", "minutes_late": 190, "customer": "Birla Valves"}],
        "overtime_minutes": 0,
        "overtime_cost": 0,
        "moved_ops": 2,
        "retimed_ops": 7
      },
      "concessions": [
        {"id": "k1", "type": "late_delivery", "job": "J2", "detail": "J2 (Birla Valves) ships 190 min late"}
      ],
      "checker": {"valid": true, "violations": []},
      "merged_with": ["alt_reroute_overtime"]
    }
  ],
  "infeasible": [
    {
      "policy": {"reroute": false, "overtime": true},
      "label": "Keep machines",
      "solver_status": "INFEASIBLE",
      "conflict": ["c1", "c2"],
      "conflict_kind": "sufficient",
      "explanation": "With M2 down until 14:00 and no re-routing, J7 cannot finish by 16:00.",
      "possible_concessions": [{"type": "relax_hard_due", "constraint": "c2"}, {"type": "allow_reroute"}]
    }
  ]
}
```

- `schedule` lists **every** operation, including frozen ones (`"change": "frozen"`). The example above is shortened.
- `change` is `none`, `frozen`, `retimed`, `moved_from_<M>`, `restarted` (same machine) or `restarted_on_<M>`.
- `time_ms` and `objective` above are placeholders; the mock sets them to 0.
- `conflict_kind` is `sufficient` (CP-SAT's sufficient assumptions, not guaranteed minimal) or `minimal` (only if we actually minimized it). The UI must show this wording honestly.
- `status` is `"no_feasible_plan"` when `alternatives` is empty. A solver timeout without proof is reported as `UNKNOWN`: "no feasible plan found within the search budget", never as "impossible".

## `POST /api/replay`

**Request**
```json
{
  "run_id": "r_20261016_101502_ab12",
  "alternative_id": "alt_reroute",
  "schedule": [ "...the alternative's full schedule..." ],
  "constraints": [ "...the accepted constraints..." ],
  "assumptions": {"samples": 500, "seed": 7, "duration_spread": [0.9, 1.3], "repair_delay_max_min": 90}
}
```

**Response 200**
```json
{
  "run_id": "r_20261016_101502_ab12",
  "alternative_id": "alt_reroute",
  "device": "cpu-numpy",
  "samples": 500,
  "elapsed_ms": 38,
  "assumptions": {"duration_spread": [0.9, 1.3], "repair_delay_max_min": 90, "seed": 7, "note": "Synthetic uncertainty, not calibrated to a real factory"},
  "jobs": [
    {"job": "J7", "on_time": 500, "of": 500, "p90_finish": "14:49"},
    {"job": "J4", "on_time": 211, "of": 500, "p90_finish": "17:29"},
    {"job": "J2", "on_time": 0, "of": 500, "p90_finish": "17:38"}
  ],
  "failing_scenario": {
    "index": 24,
    "reason": "J4 misses 17:00 by 65 min",
    "timeline": [
      {"job": "J4", "op": 2, "machine": "M1", "start": "...", "end": "...", "bottleneck": true}
    ]
  }
}
```

- The `on_time` counts above are the scratch prototype's results for the re-route plan (see `02_DATA_MODEL.md`). The full failing timeline is in `mocks/replay.json`.
- The UI wording is "211 of 500 simulated scenarios under these assumptions", never "42% reliable".
- `bottleneck: true` marks the operation that pushed the failing job late. The mock does not set it yet; A5 adds it (see `04_BACKEND_GUIDE.md`).

## `POST /api/approve`

**Request**
```json
{
  "run_id": "r_20261016_101502_ab12",
  "alternative": {"id": "alt_reroute", "...": "the full alternative object from /solve"},
  "constraints": [ "...the accepted constraints..." ],
  "approved_concessions": ["k1"],
  "approver": "Shift supervisor (demo)",
  "replay_summary": {"samples": 500, "device": "cpu-numpy"}
}
```

The backend **re-runs the checker** and verifies that every concession in `alternative.concessions` is listed in `approved_concessions`. If either check fails → 422.

**Response 200**
```json
{
  "dispatch_csv": "machine,sequence,job,op,start,end,changed\nM1,1,J3,1,08:00,09:00,frozen\n...",
  "decision_record": {
    "run_id": "r_20261016_101502_ab12",
    "approved_at": "2026-10-16T10:21:44+05:30",
    "approver": "Shift supervisor (demo)",
    "message": "Mill M2 is unavailable until 14:00. ...",
    "constraints": [ "..." ],
    "alternative_id": "alt_reroute",
    "concessions": [ "..." ],
    "checker": {"valid": true, "violations": []},
    "amd_trace": {"model": "MODEL_NAME_FROM_PORTAL", "latency_ms": 1840},
    "replay": {"samples": 500, "device": "cpu-numpy"},
    "data_notice": "Synthetic demo data"
  }
}
```

The frontend offers two downloads: `dispatch_<run_id>.csv` and `decision_<run_id>.json`.
