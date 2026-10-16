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
    h, m = s.split(":")
    return int(h) * 60 + int(m)

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
    if not isinstance(t, str) or not re.fullmatch(r"\d{1,2}:\d{2}", t):
        return False
    x = hm(t)
    return hm(fixture["shift"]["start"]) <= x <= hm(fixture["shift"]["overtime_until"])

def span_ok(span, message):
    return bool(span) and norm(span) in norm(message)
```

For each constraint: give it an `id`, start with `status: "ok"`, append to `issues` for every failed check and set `status: "review"`. Then run the cross-constraint checks (contradictions, outages that interrupt running work).

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
- **Shift:** `end <= shift_end`, or `end <= overtime_until` when overtime is allowed. Overtime minutes are `max(0, end - shift_end)` per operation.
- **Hard due date** (`due_date` with `hard: true`): `job_end <= due`, guarded by an assumption literal so CP-SAT can report conflicts.
- **Objective:** `100 * priority * tardiness` per job, plus `overtime_cost` per overtime minute, plus a move penalty (`w_move` per changed machine) and `|start - committed start|` to keep changes small, plus job end times as a tie-break.

**Alternatives** come from policies. Solve each one, drop infeasible ones into `infeasible[]`, and merge alternatives whose schedules are identical:

| id | `reroute` | `overtime` | `w_move` |
| --- | --- | --- | --- |
| `alt_keep` | false | true if an `overtime` constraint allows it | 5 |
| `alt_reroute` | true | false | 1 |
| `alt_reroute_overtime` | true | true if allowed | 1 |

```python
from ortools.sat.python import cp_model
from .timeutil import hm, fmt

def solve(F, constraints, reroute, overtime, w_move=1, time_limit_s=10):
    now = hm(F["now"]); shift_end = hm(F["shift"]["end"]); H = hm(F["shift"]["overtime_until"])
    downs = {c["params"]["machine"]: (hm(c["params"].get("from") or F["now"]), hm(c["params"]["until"]))
             for c in constraints if c["type"] == "machine_down"}
    hard = {c["params"]["job"]: (hm(c["params"]["time"]), c["id"])
            for c in constraints if c["type"] == "due_date" and c["params"].get("hard")}
    due = {j["id"]: hm(j["due"]) for j in F["jobs"]}
    prio = {j["id"]: j["priority"] for j in F["jobs"]}
    for c in constraints:
        if c["type"] == "due_date" and not c["params"].get("hard"):
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
            interrupted = b["machine"] in downs and hm(b["start"]) < downs[b["machine"]][0] < hm(b["end"])
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
            if overtime:
                ot = m.new_int_var(0, H - shift_end, f"ot{key}")
                m.add(ot >= e - shift_end); ot_terms.append(ot)
            else:
                m.add(e <= shift_end)
            if prev_end is not None:
                m.add(s >= prev_end)
            prev_end = e
            rec[key] = (s, e, choice, frozen, interrupted)
        job_end[j["id"]] = prev_end
        tard = m.new_int_var(0, H, f"t{j['id']}")
        m.add(tard >= prev_end - due[j["id"]])
        obj.append(100 * prio[j["id"]] * tard)
        obj.append(prev_end)

    for mc, (f, u) in downs.items():
        per_machine[mc].append(m.new_fixed_size_interval_var(f, u - f, f"down_{mc}"))
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
    m.minimize(sum(obj) + (cost * sum(ot_terms) if ot_terms else 0))

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
    return {"status": name, "time_ms": round(solver.wall_time * 1000),
            "objective": solver.objective_value, "schedule": schedule}
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

def check(F, constraints, schedule):
    v = []
    now = hm(F["now"]); shift_end = hm(F["shift"]["end"])
    ot_ok = any(c["type"] == "overtime" and c["params"].get("allowed") for c in constraints)
    limit = hm(F["shift"]["overtime_until"]) if ot_ok else shift_end
    ops = {(j["id"], o["op"]): o for j in F["jobs"] for o in j["ops"]}
    base = {(a["job"], a["op"]): a for a in F["committed_schedule"]}
    got = {}
    for a in schedule:
        key = (a["job"], a["op"])
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
            end = max(hm(a["end"]) for a in got.values() if a["job"] == c["params"]["job"])
            if end > hm(c["params"]["time"]):
                v.append(f"hard due date {c['id']} missed: {c['params']['job']} ends {end // 60:02d}:{end % 60:02d}")
    return {"valid": not v, "violations": v}
```

**Done check:** every solver alternative passes. Hand-broken schedules (two operations overlapping on M1, J7 op 3 before op 2, an operation on M2 during the outage, a frozen operation moved) each fail with the right message.

---

## A5. Replay (`replay.py`)

**Semantics (keep these fixed and state them in the README):**
- The dispatch policy is fixed: same machine, same order per machine. The simulator never re-optimizes a future, because that would use perfect foresight.
- Random inputs per sample: each unfinished operation's duration × triangular(0.9, 1.0, 1.3), and each outage's repair end + uniform(0, 90 min). These are synthetic assumptions, shown in the UI.
- An operation starts at the latest of: its machine being free, its job's previous operation ending, and `now`. If it would overlap an outage, it waits for the sampled repair end. Operations are non-preemptive.
- Operations that ended before `now` are not randomized.

```python
import numpy as np
from .timeutil import hm

def replay(schedule, due, now, outages, n=500, seed=7, spread=(0.9, 1.3), repair_extra_max=90):
    rng = np.random.default_rng(seed)
    ops = sorted(schedule, key=lambda a: hm(a["start"]))   # respects precedence and machine order
    mfree, jfree, sim = {}, {}, []
    repair_end = {m: hm(u) + rng.uniform(0, repair_extra_max, n) for m, (f, u) in outages.items()}
    out_start = {m: hm(f) for m, (f, u) in outages.items()}
    zeros = np.zeros(n)
    for a in ops:
        d = hm(a["end"]) - hm(a["start"]); m, j = a["machine"], a["job"]
        if hm(a["end"]) <= now:
            s = np.full(n, float(hm(a["start"]))); dd = np.full(n, float(d))
        else:
            floor = float(hm(a["start"])) if hm(a["start"]) < now else float(now)
            s = np.maximum.reduce([mfree.get(m, zeros), jfree.get(j, zeros), np.full(n, floor)])
            dd = d * (rng.triangular(spread[0], 1.0, spread[1], n) if spread[0] < spread[1] else np.ones(n))
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
- For the demo's re-route plan, our prototype found J4 on time in 211 of 500 samples. See `02_DATA_MODEL.md`.

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

`/api/approve` must:
1. Re-run `check()` on the submitted schedule. If it is not valid → 422.
2. Verify that every concession in `alternative.concessions` is in `approved_concessions`. If any is missing → 422.
3. Return the CSV (rows sorted by machine, then start) and the decision record from `03_API_CONTRACT.md`.

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

---

## Tests to write

| File | Cases |
| --- | --- |
| `test_validate.py` | alias → ID; unknown machine → review; "after lunch" → review; source span not in the message → review; two due dates for J7 → both review; outage interrupting J1 op 2 → issue text |
| `test_solver.py` | No disruption → committed schedule stays feasible; demo `alt_keep` → INFEASIBLE with `["c2"]`; demo `alt_reroute` → J7 on time; every result passes `check()` |
| `test_checker.py` | The four hand-broken schedules above fail; the committed schedule passes |
| `test_replay.py` | Zero spread and zero repair delay reproduce the plan's times exactly; same seed gives the same output |
