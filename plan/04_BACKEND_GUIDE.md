# 04. Backend guide (Person A)

Python 3.11+, FastAPI, OR-Tools CP-SAT, NumPy. Optional: PyTorch (ROCm build) for GPU replay.

The solver, checker and replay code below was tested by us against the example fixture in a scratch prototype (OR-Tools 9.15, NumPy 2.5, Python 3.13). The extraction code could not be run without a Token Factory key, so it was only syntax-checked. Treat all of it as a starting point, not finished product code.

## Folder layout

```
backend/
  app/
    main.py          # FastAPI routes (A6)
    config.py        # env vars
    timeutil.py      # "HH:MM" <-> minutes
    fixture.py       # load shared/fixture.json
    extract.py       # A1: Token Factory call
    validate.py      # A2: constraint checks
    solver.py        # A3: CP-SAT + alternatives + conflicts
    checker.py       # A4: independent schedule checker (must NOT import solver)
    replay.py        # A5: Monte Carlo replay (NumPy; torch optional)
    approve.py       # A6: CSV + decision record
    runlog.py        # in-memory run log for the inspector
  tests/
    test_validate.py  test_solver.py  test_checker.py  test_replay.py
  requirements.txt
eval/
  messages.jsonl     # A7 labeled messages
  run_eval.py
```

`requirements.txt` (the versions we tested; pin what you install):

```
fastapi
uvicorn[standard]
ortools==9.15.6755
numpy
openai
python-dotenv
pytest
```

`.env.example` (commit this file; never commit `.env`):

```
AMD_API_BASE=https://<token-factory-host>/.../v1
AMD_API_KEY=
AMD_MODEL=<model id from the portal's model list>
AMD_TIMEOUT_S=30
```

`timeutil.py`:

```python
def hm(s: str) -> int:
    if not isinstance(s, str):
        raise ValueError("Time must be HH:MM")
    parts = s.split(":")
    if len(parts) != 2 or len(parts[0]) != 2 or len(parts[1]) != 2 or not all(p.isdigit() for p in parts):
        raise ValueError("Time must be HH:MM")
    h, m = map(int, parts)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError("Invalid clock time")
    return h * 60 + m

def fmt(x: int) -> str:
    return f"{x // 60:02d}:{x % 60:02d}"
```

---

## A1. Extraction (`extract.py`)

**Goal:** message in, JSON list of proposed constraints out, with a trace that proves the AMD call happened.

Rules:
- Send the fixture's machine names, aliases and job IDs in the prompt so the model can map names. Validation (A2) still re-checks every ID.
- Ask for JSON only. Use `response_format={"type": "json_object"}` if the portal's model supports it (see `06_TECH_RESEARCH.md`). Always parse defensively anyway: strip code fences and take the outermost `{...}`.
- `temperature=0`. For "thinking" models, set a low reasoning effort to cut latency, if the endpoint accepts that parameter.
- Timeout 30 s. Retry on 429 / 5xx / timeout, honoring `Retry-After`, with at most 3 attempts. If the JSON does not parse, retry once with "Return only valid JSON".
- On final failure, return HTTP 502 with a clear message. A **rule-based fallback** is allowed only if it is labeled `origin: "rule_fallback"` and `trace.fallback_used: true`, and the UI shows a warning. Never present fallback output as AMD output.

```python
import json, os, re, time
from openai import OpenAI, APIStatusError, APITimeoutError, APIConnectionError

client = OpenAI(base_url=os.environ["AMD_API_BASE"], api_key=os.environ["AMD_API_KEY"],
                timeout=float(os.getenv("AMD_TIMEOUT_S", "30")), max_retries=0)
MODEL = os.environ["AMD_MODEL"]

SYSTEM = """You convert a factory disruption message into constraints.
Return ONLY a JSON object: {"constraints": [ ... ]}.
Allowed types and params:
- machine_down: {"machine": <machine id or name as written>, "from": "HH:MM" or null, "until": "HH:MM" or null}
- due_date: {"job": <job id>, "time": "HH:MM", "hard": true|false}  (hard=true when the message says must / still needs / cannot slip)
- priority: {"job": <job id>, "level": 1|2|3}
- overtime: {"allowed": true|false, "until": "HH:MM" or null}
- unsupported: {"note": <what cannot be modeled>}
Every constraint MUST include "source_span": the exact words copied from the message.
Never guess a time that is not in the message: use null.
Known machines: {machines}
Known jobs: {jobs}
Current time: {now}. Use 24-hour HH:MM."""

def _prompt(fixture):
    machines = "; ".join(f'{m["id"]} = {m["name"]} (aliases: {", ".join(m["aliases"])})' for m in fixture["machines"])
    jobs = ", ".join(j["id"] for j in fixture["jobs"])
    return SYSTEM.replace("{machines}", machines).replace("{jobs}", jobs).replace("{now}", fixture["now"])

FENCE = "`" * 3  # markdown code fence the model may wrap around its JSON

def _parse(text: str) -> dict:
    text = re.sub(rf"^{FENCE}(?:json)?|{FENCE}$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])

def extract(message: str, fixture: dict) -> dict:
    messages = [{"role": "system", "content": _prompt(fixture)}, {"role": "user", "content": message}]
    attempts, t0, last_err = 0, time.perf_counter(), None
    while attempts < 3:
        attempts += 1
        try:
            r = client.chat.completions.create(model=MODEL, messages=messages, temperature=0,
                                               response_format={"type": "json_object"})
            raw = r.choices[0].message.content or ""
            data = _parse(raw)
            return {"constraints": data.get("constraints", []), "trace": {
                "provider": "AMD Token Factory", "model": MODEL, "host": client.base_url.host,
                "latency_ms": round((time.perf_counter() - t0) * 1000), "attempts": attempts,
                "usage": r.usage.model_dump() if r.usage else None, "raw_output": raw, "fallback_used": False}}
        except (json.JSONDecodeError, ValueError) as e:
            last_err = e
            messages.append({"role": "user", "content": "Return only valid JSON in the required format."})
        except APIStatusError as e:
            last_err = e
            if e.status_code != 429 and e.status_code < 500:
                break  # do not retry other 4xx errors
            if attempts < 3:
                time.sleep(float(e.response.headers.get("retry-after", 2 ** attempts)))
        except (APITimeoutError, APIConnectionError) as e:
            last_err = e
            if attempts < 3:
                time.sleep(2 ** attempts)
    raise RuntimeError(f"AMD extraction failed after {attempts} attempts: {last_err}")
```

If the portal's model rejects `response_format`, remove it. The prompt and `_parse` still work.

**Done check:** run five messages (the demo message, one with an alias, one without a time, one with two facts about one job, one off-topic) and save each raw output to `eval/smoke/`.

---

## A2. Validation (`validate.py`)

Apply the seven rules in `02_DATA_MODEL.md`. Key pieces:

```python
import re
from .timeutil import hm

def norm(s): return re.sub(r"\s+", " ", (s or "").strip().lower())

def resolve_machine(name, fixture):
    n = norm(name)
    for m in fixture["machines"]:
        if n in {norm(m["id"]), norm(m["name"]), *map(norm, m["aliases"])}:
            return m["id"]
    return None

def valid_time(t, fixture):
    try:
        x = hm(t)
    except (TypeError, ValueError):
        return False
    return hm(fixture["shift"]["start"]) <= x <= hm(fixture["shift"]["overtime_until"])

def span_ok(span, message):
    return bool(span) and norm(span) in norm(message)

def validate_for_solve(fixture, constraints):
    """Structural gate: a client-set 'accepted' status cannot bypass this."""
    machines = {m["id"] for m in fixture["machines"]}
    jobs = {j["id"] for j in fixture["jobs"]}
    ids, single = set(), {}
    for c in constraints:
        cid, kind, p = c.get("id"), c.get("type"), c.get("params")
        if not isinstance(cid, str) or not cid or cid in ids or not isinstance(p, dict):
            raise ValueError("Constraints need unique IDs and params")
        ids.add(cid)
        if c.get("status") not in {"ok", "accepted"}:
            raise ValueError(f"{cid}: resolve or reject the review item first")
        if c.get("blocking_issues"):
            raise ValueError(f"{cid}: correct blocking fields and revalidate before accepting")
        if kind == "machine_down":
            if p.get("machine") not in machines or not valid_time(p.get("until"), fixture):
                raise ValueError(f"{cid}: choose a known machine and a repair end time")
            start = p.get("from") or fixture["now"]
            if not valid_time(start, fixture) or hm(start) >= hm(p["until"]):
                raise ValueError(f"{cid}: outage end must be after a valid start")
        elif kind == "due_date":
            if p.get("job") not in jobs or not valid_time(p.get("time"), fixture) or type(p.get("hard")) is not bool:
                raise ValueError(f"{cid}: invalid job, due time or hard flag")
        elif kind == "priority":
            if p.get("job") not in jobs or type(p.get("level")) is not int or p["level"] not in (1, 2, 3):
                raise ValueError(f"{cid}: invalid job or priority")
        elif kind == "overtime":
            if type(p.get("allowed")) is not bool:
                raise ValueError(f"{cid}: overtime allowed must be boolean")
            until = p.get("until")
            if until is not None and (not valid_time(until, fixture) or hm(until) < hm(fixture["shift"]["end"])):
                raise ValueError(f"{cid}: invalid overtime cutoff")
        else:
            raise ValueError(f"{cid}: unsupported constraints cannot enter the solver")
        if kind in {"due_date", "priority", "overtime"}:
            key = (kind, p.get("job"))
            if key in single and single[key] != p:
                raise ValueError(f"{cid}: contradictory {kind} constraints")
            single[key] = p
```

For each constraint: give it an `id`, start with `status: "ok"`, append to `issues` for every failed check and set `status: "review"`. Also return `blocking_issues: []`: unknown IDs, missing/invalid required times, unsupported types and contradictions go here. A human can confirm a complete but ambiguous interpretation; a blocking item must be edited and revalidated or rejected. Then run the cross-constraint checks (contradictions, outages that interrupt running work).

Call `validate_for_solve()` again on the backend before solving, including items marked `accepted`. Map its `ValueError` to HTTP 422. Verify source spans against the server-stored extraction message and record user edits separately. Changing a status alone never repairs invalid fields. The helper is the structural gate; it does not replace extraction's source checks or semantic review.

Interrupted operations: for a `machine_down(m, from, until)`, look at `committed_schedule` for an operation on `m` with `start < from < end`. Add the issue "Outage interrupts J1 op 2 (in progress on M2); it will restart after repair". The solver then treats that operation as not started.

---

## A3. Solver (`solver.py`)

A flexible job shop in CP-SAT. This follows the official OR-Tools pattern of one optional interval per eligible machine, `add_exactly_one` over the presence literals and `add_no_overlap` per machine. On top of that it adds frozen work, outages, a shift/overtime window and tardiness.

**Model, in words:**
- Every operation has `start` and `end` variables, plus one optional interval per eligible machine with that machine's duration.
- **Frozen:** an operation whose committed start is before `now`, and that no outage interrupts, is fixed to its committed machine and times.
- **Not frozen:** `start >= now`. If `reroute` is off, only its committed machine is allowed.
- **Outage:** a fixed interval `[from, until)` added to that machine's no-overlap list.
- **Precedence:** `start(op k+1) >= end(op k)` within a job.
- **Shift:** `end <= shift_end`, or the earlier of the accepted overtime cutoff and the fixture's `overtime_until` when both the constraint and policy allow overtime. Overtime minutes are actual occupied overlap: `max(0, end - max(start, shift_end))` per operation.
- **Hard due date** (`due_date` with `hard: true`): `job_end <= due`, guarded by an assumption literal so CP-SAT can report conflicts.
- **Objective:** `100 * priority * tardiness` per job, plus hourly overtime rate × occupied overtime minutes / 60, plus a move penalty (`w_move` per changed machine) and `|start - committed start|` to keep changes small, plus job end times as a tie-break. All accepted due-date updates affect tardiness; hard updates also add a feasibility bound. Multiply the objective by 60 internally to keep integer coefficients, and divide the reported score by 60. These are explicit demo weights, not measured factory costs.

**Alternatives** come from policies. Solve each one, drop infeasible ones into `infeasible[]`, and merge alternatives whose schedules are identical:

| id | `reroute` | `overtime` | `w_move` |
| --- | --- | --- | --- |
| `alt_keep` | false | true if an `overtime` constraint allows it | 5 |
| `alt_reroute` | true | false | 1 |
| `alt_reroute_overtime` | true | true if allowed | 1 |

```python
from ortools.sat.python import cp_model
from .timeutil import hm, fmt
from .validate import validate_for_solve

def solve(F, constraints, reroute, overtime, w_move=1, time_limit_s=10):
    validate_for_solve(F, constraints)
    now = hm(F["now"]); shift_end = hm(F["shift"]["end"]); H = hm(F["shift"]["overtime_until"])
    ot = [c["params"] for c in constraints if c["type"] == "overtime" and c["params"]["allowed"]]
    limit = min(H, *(hm(p.get("until") or F["shift"]["overtime_until"]) for p in ot)) if overtime and ot else shift_end
    downs = {}
    for c in constraints:
        if c["type"] == "machine_down":
            p = c["params"]
            downs.setdefault(p["machine"], []).append((hm(p.get("from") or F["now"]), hm(p["until"])))
    # Merge overlapping outage intervals; one machine can have several outages.
    for mc, windows in downs.items():
        merged = []
        for f, u in sorted(windows):
            if merged and f <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], u))
            else:
                merged.append((f, u))
        downs[mc] = merged
    hard = {c["params"]["job"]: (hm(c["params"]["time"]), c["id"])
            for c in constraints if c["type"] == "due_date" and c["params"].get("hard")}
    due = {j["id"]: hm(j["due"]) for j in F["jobs"]}
    prio = {j["id"]: j["priority"] for j in F["jobs"]}
    for c in constraints:
        if c["type"] == "due_date":
            due[c["params"]["job"]] = hm(c["params"]["time"])
        if c["type"] == "priority":
            prio[c["params"]["job"]] = c["params"]["level"]

    base = {(a["job"], a["op"]): a for a in F["committed_schedule"]}
    m = cp_model.CpModel()
    per_machine = {mc["id"]: [] for mc in F["machines"]}
    rec, obj, ot_terms, job_end, assumption = {}, [], [], {}, {}

    for j in F["jobs"]:
        prev_end = None
        for o in j["ops"]:
            key = (j["id"], o["op"]); b = base[key]
            interrupted = any(hm(b["start"]) < f < hm(b["end"]) for f, u in downs.get(b["machine"], []))
            frozen = hm(b["start"]) < now and not interrupted
            s = m.new_int_var(hm(F["shift"]["start"]), H, f"s{key}")
            e = m.new_int_var(hm(F["shift"]["start"]), H, f"e{key}")
            if frozen:
                m.add(s == hm(b["start"])); m.add(e == hm(b["end"]))
                per_machine[b["machine"]].append(
                    m.new_interval_var(s, hm(b["end"]) - hm(b["start"]), e, f"i{key}"))
                choice = {b["machine"]: None}
            else:
                m.add(s >= now)
                choice = {}
                for mc, d in o["eligible"].items():
                    if not reroute and mc != b["machine"]:
                        continue
                    p = m.new_bool_var(f"p{key}{mc}")
                    per_machine[mc].append(m.new_optional_interval_var(s, d, e, p, f"i{key}{mc}"))
                    choice[mc] = p
                m.add_exactly_one(choice.values())
                obj.append(w_move * sum(p for mc, p in choice.items() if mc != b["machine"]))
                dev = m.new_int_var(0, H, f"dev{key}")
                m.add(dev >= s - hm(b["start"])); m.add(dev >= hm(b["start"]) - s)
                obj.append(dev)
            m.add(e <= limit)
            if limit > shift_end:
                ot = m.new_int_var(0, H - shift_end, f"ot{key}")
                ot_start = m.new_int_var(shift_end, H, f"ot_start{key}")
                m.add_max_equality(ot_start, [s, shift_end])
                m.add_max_equality(ot, [0, e - ot_start]); ot_terms.append(ot)
            if prev_end is not None:
                m.add(s >= prev_end)
            prev_end = e
            rec[key] = (s, e, choice, frozen, interrupted)
        job_end[j["id"]] = prev_end
        tard = m.new_int_var(0, H, f"t{j['id']}")
        m.add(tard >= prev_end - due[j["id"]])
        obj.append(100 * prio[j["id"]] * tard)
        obj.append(prev_end)

    for mc, windows in downs.items():
        for i, (f, u) in enumerate(windows):
            per_machine[mc].append(m.new_fixed_size_interval_var(f, u - f, f"down_{mc}_{i}"))
    for ivs in per_machine.values():
        m.add_no_overlap(ivs)

    lit_to_cid = {}
    for jid, (t, cid) in hard.items():
        lit = m.new_bool_var(f"hard_{cid}")
        m.add(job_end[jid] <= t).only_enforce_if(lit)
        lit_to_cid[lit.index] = cid
    if lit_to_cid:
        m.add_assumptions([m.get_bool_var_from_proto_index(i) for i in lit_to_cid])

    cost = F["shift"]["overtime_cost_per_hour"]
    m.minimize(60 * sum(obj) + (cost * sum(ot_terms) if ot_terms else 0))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_workers = 8
    status = solver.solve(m)
    name = solver.status_name(status)
    if status == cp_model.INFEASIBLE:
        core = [lit_to_cid[i] for i in solver.sufficient_assumptions_for_infeasibility() if i in lit_to_cid]
        return {"status": name, "hard_due_in_conflict": core}
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": name}  # UNKNOWN: "no feasible plan found within the search budget"

    schedule = []
    for (jid, op), (s, e, choice, frozen, interrupted) in rec.items():
        mc = next(k for k, p in choice.items() if p is None or solver.value(p))
        schedule.append({"job": jid, "op": op, "machine": mc,
                         "start": fmt(solver.value(s)), "end": fmt(solver.value(e))})
    overtime_minutes = sum(solver.value(t) for t in ot_terms)
    return {"status": name, "time_ms": round(solver.wall_time * 1000),
            "objective": solver.objective_value / 60, "schedule": schedule,
            "overtime_minutes": overtime_minutes, "overtime_cost": overtime_minutes * cost / 60}
```

**Conflict explanation.** In this version, assumptions guard only the hard due dates. The outage and the policy (no re-route / no overtime) are always on, so the conflict reported to the UI is "the hard due date(s) returned by CP-SAT + the outage(s) + the policy". `sufficient_assumptions_for_infeasibility()` returns a **sufficient** set, not necessarily a minimal one, so label it `conflict_kind: "sufficient"`. To prove a set minimal, drop each member in turn and re-solve.

**Concessions offered** for an infeasible policy: relax a hard due date (it becomes soft and appears as a `late_delivery` concession), allow re-routing, or allow overtime. Each one is a separate solve. The UI offers only concessions that actually produced a feasible plan.

**Status rules:**
- `OPTIMAL` / `FEASIBLE`: return the schedule. Report `FEASIBLE` honestly ("best found within 10 s").
- `INFEASIBLE`: proven impossible under this policy.
- `UNKNOWN`: "no feasible plan found within the search budget". Never call this impossible.

**Done check (tests):** with the demo constraints, `alt_keep` returns `INFEASIBLE` with `hard_due_in_conflict == ["c2"]`, and `alt_reroute` returns a schedule in which J7 ends by 16:00 and J2 is late. These are the outcomes our prototype produced; see `02_DATA_MODEL.md`.

---

## A4. Checker (`checker.py`)

Written from the rules, **without importing the solver**. It is the independent check from the project decision. It returns every violation, not only the first.

```python
from .timeutil import hm
from .validate import validate_for_solve

def check(F, constraints, schedule):
    v = []
    try:
        validate_for_solve(F, constraints)
    except ValueError as error:
        return {"valid": False, "violations": [str(error)]}
    now = hm(F["now"]); shift_end = hm(F["shift"]["end"])
    ot = [c["params"] for c in constraints if c["type"] == "overtime" and c["params"]["allowed"]]
    limit = min(hm(F["shift"]["overtime_until"]), *(hm(p.get("until") or F["shift"]["overtime_until"]) for p in ot)) if ot else shift_end
    ops = {(j["id"], o["op"]): o for j in F["jobs"] for o in j["ops"]}
    base = {(a["job"], a["op"]): a for a in F["committed_schedule"]}
    got = {}
    for a in schedule:
        key = (a["job"], a["op"])
        if key not in ops:
            v.append(f"{key} is not a fixture operation")
            continue
        try:
            hm(a["start"]); hm(a["end"])
        except (KeyError, TypeError, ValueError):
            v.append(f"{key} has invalid times")
            continue
        if key in got: v.append(f"{key} scheduled twice")
        got[key] = a
    for key in ops:
        if key not in got: v.append(f"{key} missing")
    downs = [(c["params"]["machine"], hm(c["params"].get("from") or F["now"]), hm(c["params"]["until"]))
             for c in constraints if c["type"] == "machine_down"]
    for key, a in got.items():
        s, e, mc = hm(a["start"]), hm(a["end"]), a["machine"]
        elig = ops[key]["eligible"]
        if mc not in elig: v.append(f"{key} on ineligible machine {mc}")
        elif e - s != elig[mc]: v.append(f"{key} duration {e - s} != {elig[mc]} on {mc}")
        if e > limit: v.append(f"{key} ends {a['end']} after allowed end")
        b = base[key]
        interrupted = any(m == b["machine"] and hm(b["start"]) < f < hm(b["end"]) for m, f, u in downs)
        if hm(b["start"]) < now and not interrupted:
            if (a["machine"], a["start"], a["end"]) != (b["machine"], b["start"], b["end"]):
                v.append(f"{key} was started before now and must not change")
        elif s < now:
            v.append(f"{key} starts in the past ({a['start']})")
        for m, f, u in downs:
            if m == mc and s < u and e > f and not (hm(b["start"]) < now and not interrupted):
                v.append(f"{key} overlaps outage on {m}")
    for j in F["jobs"]:
        for o1, o2 in zip(j["ops"], j["ops"][1:]):
            a1, a2 = got.get((j["id"], o1["op"])), got.get((j["id"], o2["op"]))
            if a1 and a2 and hm(a2["start"]) < hm(a1["end"]):
                v.append(f"{j['id']} op {o2['op']} starts before op {o1['op']} ends")
    by_m = {}
    for a in got.values(): by_m.setdefault(a["machine"], []).append(a)
    for mc, lst in by_m.items():
        lst.sort(key=lambda a: hm(a["start"]))
        for x, y in zip(lst, lst[1:]):
            if hm(y["start"]) < hm(x["end"]):
                v.append(f"overlap on {mc}: {x['job']}-{x['op']} and {y['job']}-{y['op']}")
    for c in constraints:
        if c["type"] == "due_date" and c["params"].get("hard"):
            ends = [hm(a["end"]) for a in got.values() if a["job"] == c["params"]["job"]]
            if not ends:
                continue  # already reported missing operations
            end = max(ends)
            if end > hm(c["params"]["time"]):
                v.append(f"hard due date {c['id']} missed: {c['params']['job']} ends {end // 60:02d}:{end % 60:02d}")
    return {"valid": not v, "violations": v}
```

**Done check:** every solver alternative passes. Hand-broken schedules (two operations overlapping on M1, J7 op 3 before op 2, an operation on M2 during the outage, a frozen operation moved) each fail with the right message.

---

## A5. Replay (`replay.py`)

**Semantics (keep these fixed and state them in the README):**
- The dispatch policy is fixed: same machine, same order per machine. The simulator never re-optimizes a future, because that would use perfect foresight.
- Random inputs per sample: each unstarted operation's duration × triangular(0.9, 1.0, 1.3), and each future outage repair end + uniform(0, 90 min). For an operation already running, preserve its observed start and elapsed time and multiply only its planned remaining duration. These are synthetic assumptions, shown in the UI.
- An unstarted operation starts at the latest of: its **planned start**, its machine being free, its job's previous operation ending, and `now`. It cannot dispatch early. If it would overlap an outage, it waits for the sampled repair end. Operations are non-preemptive. Start from a checked schedule; an interrupted operation must already be represented as a future restart.
- Operations that ended before `now` are not randomized.
- Historical starts and completed repairs are observations and stay fixed. With duration multipliers of 1 and zero extra repair delay, every operation must reproduce its planned times exactly.

```python
import numpy as np
from .timeutil import hm

def replay(schedule, due, now, outages, n=500, seed=7, spread=(0.9, 1.3), repair_extra_max=90):
    rng = np.random.default_rng(seed)
    ops = sorted(schedule, key=lambda a: hm(a["start"]))   # respects precedence and machine order
    mfree, jfree, sim = {}, {}, []
    repair_end = {m: hm(u) + (rng.uniform(0, repair_extra_max, n) if hm(u) > now else np.zeros(n))
                  for m, (f, u) in outages.items()}
    out_start = {m: hm(f) for m, (f, u) in outages.items()}
    zeros = np.zeros(n)
    for a in ops:
        d = hm(a["end"]) - hm(a["start"]); m, j = a["machine"], a["job"]
        planned_start, planned_end = hm(a["start"]), hm(a["end"])
        if planned_end <= now:
            s = np.full(n, float(planned_start)); dd = np.full(n, float(d))
        else:
            factor = rng.triangular(spread[0], 1.0, spread[1], n) if spread[0] < spread[1] else np.ones(n)
            if planned_start < now:  # observed running: randomize remaining work only
                s = np.full(n, float(planned_start))
                dd = (now - planned_start) + (planned_end - now) * factor
            else:
                floor = float(max(now, planned_start))
                s = np.maximum.reduce([mfree.get(m, zeros), jfree.get(j, zeros), np.full(n, floor)])
                dd = d * factor
                if m in repair_end:
                    hit = (s < repair_end[m]) & (s + dd > out_start[m])
                    s = np.where(hit, np.maximum(s, repair_end[m]), s)
        e = s + dd
        mfree[m] = e; jfree[j] = e
        sim.append((a, s, e))
    lateness = {j: jfree[j] - hm(t) for j, t in due.items()}
    return sim, lateness
```

Then build the response:
- Per job: `on_time = (lateness <= 0).sum()` and the 90th-percentile finish.
- **Failing scenario:** choose the highest-priority job that is on time in the plan but late in some samples. Take the sample where it is latest, and return all operations' times for that sample.
- **Bottleneck:** in that sample, mark the failing job's operation with the largest extra wait (simulated start minus planned start). Its machine is the bottleneck. Check this rule against the demo before trusting it.
- Use the freshly generated count in `mocks/replay.json`; the old 211/500 result used an early-dispatch policy and is superseded. See `02_DATA_MODEL.md`.

This compact example handles one outage interval per machine in replay. If extraction yields several, either implement all intervals or return a clear unsupported-input error for replay; never silently overwrite them. The solver and checker handle multiple intervals.

### A8. GPU replay (nice-to-have)

The same loop with `torch` tensors of shape `[n]` on `device="cuda"`. PyTorch's ROCm builds use the `cuda` device name. Detect AMD with `torch.version.hip`. To compare fairly:
1. Generate the random samples once on CPU with NumPy and copy the same arrays to the GPU, so both paths use identical inputs.
2. Assert that CPU and GPU lateness match (`np.allclose`).
3. Time both at n = 1k, 10k and 100k, including the transfer and `torch.cuda.synchronize()`.
4. Report whatever the numbers show. If the GPU is slower at our sizes, say so; the AMD requirement is already met by the extraction.

---

## A6. API (`main.py`) and approval

```python
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Rehearsal")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health")
def health(): ...

@app.post("/api/extract")
def api_extract(body: dict): ...   # extract() -> validate() -> runlog.save() -> response per 03_API_CONTRACT.md

# ... /api/factory, /api/solve, /api/replay, /api/approve

# Last: serve the built React app from the same container (see 05_FRONTEND_GUIDE.md, B6)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

`/api/solve` must save the accepted constraints, fixture snapshot and alternatives in the server's run store. Give each solve a fresh `run_id`, so an old alternative ID cannot point to a different schedule. Save replay results under that run and alternative. An in-memory store is enough for this hackathon; return 404/410 with a retry instruction after a server restart.

`/api/approve` takes IDs, approved concession IDs and an approver name. It loads the stored schedule and constraints, re-runs `check()`, **derives concessions from that schedule and the accepted due dates**, and requires every one to be approved. Never accept a client-supplied schedule, constraints, concessions list or replay summary as authority. This small pure helper illustrates that boundary (map `ValueError` to 422, unknown run/alternative to 404):

```python
from .timeutil import hm
from .checker import check

def required_concessions(F, constraints, schedule):
    due = {j["id"]: hm(j["due"]) for j in F["jobs"]}
    for c in constraints:
        if c["type"] == "due_date":
            due[c["params"]["job"]] = hm(c["params"]["time"])
    concessions = []
    for j in sorted(F["jobs"], key=lambda j: j["id"]):
        end = max(hm(a["end"]) for a in schedule if a["job"] == j["id"])
        if end > due[j["id"]]:
            concessions.append({"id": f"k{len(concessions) + 1}", "type": "late_delivery", "job": j["id"],
                                "detail": f"{j['id']} ({j['customer']}) ships {end - due[j['id']]} min late"})
    shift_end = hm(F["shift"]["end"])
    minutes = sum(max(0, hm(a["end"]) - max(hm(a["start"]), shift_end)) for a in schedule)
    if minutes:
        concessions.append({"id": f"k{len(concessions) + 1}", "type": "overtime",
                            "detail": f"{minutes} machine-minutes overtime",
                            "minutes": minutes, "cost": minutes * F["shift"]["overtime_cost_per_hour"] / 60})
    return concessions

def prepare_approval(run, body):
    allowed = {"run_id", "alternative_id", "approved_concessions", "approver"}
    if set(body) - allowed:
        raise ValueError("Approval accepts IDs and decisions, not client-owned plan data")
    if body.get("run_id") != run["run_id"]:
        raise ValueError("Run ID does not match the stored snapshot")
    alternative = run["alternatives"][body["alternative_id"]]
    F, constraints, schedule = run["fixture"], run["constraints"], alternative["schedule"]
    checked = check(F, constraints, schedule)
    if not checked["valid"]:
        raise ValueError("Stored schedule failed re-check: " + "; ".join(checked["violations"]))
    concessions = required_concessions(F, constraints, schedule)
    approved = body.get("approved_concessions", [])
    if not isinstance(approved, list) or any(not isinstance(cid, str) for cid in approved):
        raise ValueError("approved_concessions must be a list of IDs")
    if set(approved) != {c["id"] for c in concessions}:
        raise ValueError("Approve every required concession from the stored plan")
    if not isinstance(body.get("approver"), str) or not body["approver"].strip():
        raise ValueError("Approver name is required")
    return {"schedule": schedule, "constraints": constraints, "concessions": concessions,
            "checker": checked, "replay": run.get("replays", {}).get(alternative["id"])}
```

Use the same `required_concessions()` when building alternative cards. Build the CSV (rows sorted by machine, then start) and decision record from these server-owned values. The helper covers the demo's unrelaxed hard due dates. If adding hard-due relaxation, store each alternative's explicitly relaxed constraint IDs and effective constraints, check those, and derive an additional relaxation concession against the original constraints. Keep that feature disabled until this path is implemented; never silently relax a hard date.

Use Pydantic models for request bodies once the contract is stable. They give 422 errors and `/docs` for free.

---

## A7. Evaluation

`eval/messages.jsonl`: one labeled message per line. One person writes the messages, the other labels them independently, and the two settle disagreements before running the evaluation.

```json
{"id": "m01", "message": "Big mill is out till 2pm, J7 must ship by 4.", "expected": [{"type": "machine_down", "params": {"machine": "M2", "until": "14:00"}}, {"type": "due_date", "params": {"job": "J7", "time": "16:00", "hard": true}}], "expect_review": false}
{"id": "m02", "message": "Mill 4 stopped.", "expected": [], "expect_review": true}
```

Cover: aliases, 12-hour times ("2pm", "4"), missing end times, unknown machines, negation ("no overtime today"), two updates to the same job, and something out of scope (material shortage).

`run_eval.py` reports:

| Metric | Definition |
| --- | --- |
| Complete-change accuracy | Messages where every expected constraint was extracted correctly and nothing extra was `ok` |
| False acceptance | Constraints marked `ok` that are wrong. **This is the most important number** |
| Useful review | Messages that should need review and did produce `review` |
| Latency | Median and max per call |

Report the result as "builder-labeled set of N messages". With 15-20 messages, this is a smoke test, not a benchmark. Say so.

Also reserve a small held-out set of 5-8 disruption scenarios, including an outage, a changed due date, an overtime cutoff and an infeasible case. Freeze these before tuning the demo. Run three comparisons with the same time budget: (1) a CPU CP-SAT optimizer supplied correct typed constraints, (2) Rehearsal with replay hidden, and (3) Rehearsal with replay shown. The CPU optimizer is the scheduling reference, not a weak strawman; the AMD contribution is message interpretation and review, and replay's contribution is exposing risk before approval. For (2)/(3), predeclare a selection rule (e.g. fewest sampled late priority jobs, then nominal weighted tardiness/cost) and assess the chosen schedule on a separate fixed set of replay seeds. Report schedule validity, weighted tardiness, occupied overtime/cost, risky promises exposed and held-out sampled outcomes. Report no gain when none is observed; label all data and uncertainty synthetic. A short table is enough—no large benchmark is required.

---

## Tests to write

| File | Cases |
| --- | --- |
| `test_validate.py` | alias → ID; unknown machine → review; "after lunch" → review; source span not in the message → review; two due dates for J7 → both review; outage interrupting J1 op 2 → issue text |
| `test_solver.py` | No disruption → committed schedule stays feasible; demo `alt_keep` → INFEASIBLE with `["c2"]`; demo `alt_reroute` → J7 on time; every result passes `check()` |
| `test_checker.py` | The four hand-broken schedules above fail; the committed schedule passes |
| `test_replay.py` | Zero spread and zero repair delay reproduce the plan's times exactly; future operations never dispatch early; running work never finishes before now; same seed gives the same output |
| `test_approve.py` | Missing approval fails even if cached concessions are empty; client-owned plan fields fail; unchanged stored plan + all derived concessions succeeds |

The planning examples themselves are checked by `python3 plan/prototype/regression_checks.py` (requires OR-Tools and NumPy). Port these regressions into backend tests during implementation.
