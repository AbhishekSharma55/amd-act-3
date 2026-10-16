"""Replay example, kept identical to A5 in the backend guide."""
import json
from proto import hm
import numpy as np

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

if __name__ == "__main__":
    F = json.load(open("fixture.json")); B = json.load(open("baseline.json"))
    due = {j["id"]: j["due"] for j in F["jobs"]}
    sim, late = replay(B, due, hm("08:00"), {}, n=1000)
    for j, l in late.items():
        print(j, "on time in", int((l <= 0).sum()), "/ 1000 scenarios;  worst late min:", round(float(l.max())))
    worst = int(np.argmax(late["J7"]))
    print("worst scenario index for J7:", worst)
