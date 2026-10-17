"""A5: fixed-dispatch Monte Carlo replay of one checked schedule (NumPy, CPU).

Semantics (also stated in the README and shown in the UI):
- Same machine and same order per machine; the simulator never re-optimizes a sampled future.
- Unstarted operations: full duration x triangular(lo, 1.0, hi). Running operations keep their observed
  start and elapsed work; only the planned remaining work is multiplied by the same distribution.
- An unstarted operation starts at the latest of its planned start, machine free, previous op of its job
  done and `now`. If it would overlap an outage it waits for the sampled repair end.
- Each outage that has not ended by `now` gets repair end + uniform(0, repair_delay_max_min).
- Finished work is not randomized. Zero spread and zero repair delay reproduce the plan exactly.
"""
import time

import numpy as np

from .timeutil import fmt, hm

DEFAULTS = {"samples": 500, "seed": 7, "duration_spread": [0.9, 1.3], "repair_delay_max_min": 90}
NOTE = "Synthetic uncertainty, not calibrated to a real factory"


def check_assumptions(a: dict | None) -> dict:
    a = {**DEFAULTS, **(a or {})}
    unknown = set(a) - set(DEFAULTS)
    if unknown:
        raise ValueError(f"Unknown replay assumptions: {', '.join(sorted(unknown))}")
    n, seed, spread, delay = a["samples"], a["seed"], a["duration_spread"], a["repair_delay_max_min"]
    if type(n) is not int or not 1 <= n <= 200_000:
        raise ValueError("samples must be an integer from 1 to 200000")
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    if (not isinstance(spread, (list, tuple)) or len(spread) != 2
            or not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in spread)
            or not 0.5 <= spread[0] <= 1.0 <= spread[1] <= 3.0):
        raise ValueError("duration_spread must be [low, high] with 0.5 <= low <= 1 <= high <= 3")
    if not isinstance(delay, (int, float)) or isinstance(delay, bool) or not 0 <= delay <= 480:
        raise ValueError("repair_delay_max_min must be between 0 and 480")
    return {"samples": n, "seed": seed, "duration_spread": [float(spread[0]), float(spread[1])],
            "repair_delay_max_min": float(delay)}


def simulate(schedule, due, now, outages, n=500, seed=7, spread=(0.9, 1.3), repair_extra_max=90):
    """outages: {machine: [(from_min, until_min), ...]} merged and sorted. Returns (sim, lateness)."""
    rng = np.random.default_rng(seed)
    ops = sorted(schedule, key=lambda a: hm(a["start"]))   # respects precedence and machine order
    mfree, jfree, sim = {}, {}, []
    windows = {m: [(f, u + (rng.uniform(0, repair_extra_max, n) if u > now else np.zeros(n))) for f, u in ws]
               for m, ws in outages.items()}
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
                # A sampled overrun can reach a future outage. The work stops there and, as in the solver's
                # restart policy, runs again in full after the sampled repair; the observed start is unchanged
                # in history, and the restart is what this sample dispatches.
                restarted = np.zeros(n, dtype=bool)
                for f, rend in windows.get(m, []):
                    if f < now:
                        continue
                    cut = ~restarted & (s + dd > f)
                    later = restarted & (s < rend) & (s + dd > f)
                    s = np.where(cut, rend, np.where(later, np.maximum(s, rend), s))
                    dd = np.where(cut, d * factor, dd)
                    restarted |= cut
            else:
                floor = float(max(now, planned_start))
                s = np.maximum.reduce([mfree.get(m, zeros), jfree.get(j, zeros), np.full(n, floor)])
                dd = d * factor
                for f, rend in windows.get(m, []):
                    hit = (s < rend) & (s + dd > f)
                    s = np.where(hit, np.maximum(s, rend), s)
        e = s + dd
        mfree[m] = e; jfree[j] = e
        sim.append((a, s, e))
    lateness = {j: jfree[j] - t for j, t in due.items()}
    return sim, lateness


def run_replay(F, schedule, outages, due, priority, assumptions, device="cpu-numpy"):
    """Build the /api/replay body. `due`/`priority` are the effective (constraint-updated) values."""
    a = check_assumptions(assumptions)
    now, n = hm(F["now"]), a["samples"]
    t0 = time.perf_counter()
    sim, lat = simulate(schedule, due, now, outages, n=n, seed=a["seed"], spread=a["duration_spread"],
                        repair_extra_max=a["repair_delay_max_min"])
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    planned_end = {j["id"]: max(hm(x["end"]) for x in schedule if x["job"] == j["id"]) for j in F["jobs"]}
    jobs = []
    for j in sorted(due):
        finish = lat[j] + due[j]
        jobs.append({"job": j, "on_time": int((lat[j] <= 1e-9).sum()), "of": n,
                     "p90_finish": fmt(int(np.percentile(finish, 90))),
                     "planned_finish": fmt(planned_end[j]), "due": fmt(due[j]),
                     "late_in_plan": planned_end[j] > due[j],
                     "worst_late_min": max(0, int(round(float(lat[j].max()))))})

    order = sorted(due, key=lambda j: (-priority[j], j))
    target = next((j for j in order if planned_end[j] <= due[j] and (lat[j] > 1e-9).any()), None)
    failing = None
    if target:
        idx = int(np.argmax(lat[target]))
        timeline, waits = [], []
        for op, ss, ee in sim:
            row = {"job": op["job"], "op": op["op"], "machine": op["machine"],
                   "start": fmt(int(round(float(ss[idx])))), "end": fmt(int(round(float(ee[idx])))),
                   "planned_start": op["start"], "planned_end": op["end"], "bottleneck": False}
            timeline.append(row)
            if op["job"] == target:
                waits.append((float(ss[idx]) - hm(op["start"]), len(timeline) - 1))
        wait, pos = max(waits)
        timeline[pos]["bottleneck"] = True
        b = timeline[pos]
        late = int(round(float(lat[target][idx])))
        failing = {"index": idx, "job": target, "minutes_late": late,
                   "reason": f"{target} misses {fmt(due[target])} by {late} min",
                   "bottleneck": {"job": b["job"], "op": b["op"], "machine": b["machine"],
                                  "extra_wait_min": int(round(wait)),
                                  "detail": f"{b['job']} op {b['op']} waited {int(round(wait))} min longer than "
                                            f"planned for {b['machine']}"},
                   "timeline": timeline}
    return {"device": device, "samples": n, "elapsed_ms": elapsed_ms,
            "assumptions": {"duration_spread": a["duration_spread"], "repair_delay_max_min": a["repair_delay_max_min"],
                            "seed": a["seed"], "note": NOTE,
                            "dispatch": "Fixed machine order and planned start floors; no re-optimization"},
            "jobs": jobs, "failing_scenario": failing}
