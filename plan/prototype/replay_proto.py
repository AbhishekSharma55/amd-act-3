import json, numpy as np

def hm(s):
    h, m = s.split(":"); return int(h) * 60 + int(m)

def replay(schedule, jobs_due, now, outages, n=500, seed=7, dur_spread=(0.9, 1.3), repair_extra_max=90):
    """Fixed dispatch policy: same machine + same order per machine. Only durations / repair time are random."""
    rng = np.random.default_rng(seed)
    ops = sorted(schedule, key=lambda a: hm(a["start"]))       # planned order respects precedence + machine order
    mfree = {}                                                  # machine -> array[n] of free time
    jfree = {}                                                  # job -> array[n] of last op end
    repair_end = {m: hm(u) + rng.uniform(0, repair_extra_max, n) for m, (f, u) in outages.items()}
    out_start = {m: hm(f) for m, (f, u) in outages.items()}
    sim = []
    for a in ops:
        d = hm(a["end"]) - hm(a["start"])
        m, j = a["machine"], a["job"]
        if hm(a["end"]) <= now:                                 # already finished: no randomness
            s = np.full(n, float(hm(a["start"])))
            dd = np.full(n, float(d))
        else:
            s = np.maximum.reduce([mfree.get(m, np.zeros(n)), jfree.get(j, np.zeros(n)), np.full(n, float(hm(a["start"])) if hm(a["start"]) < now else float(now))])
            dd = d * rng.triangular(dur_spread[0], 1.0, dur_spread[1], n)
            if m in repair_end:                                 # op would overlap outage -> wait for repair
                hit = (s < repair_end[m]) & (s + dd > out_start[m])
                s = np.where(hit, np.maximum(s, repair_end[m]), s)
        e = s + dd
        mfree[m] = e; jfree[j] = e
        sim.append((a, s, e))
    lateness = {j: jfree[j] - hm(due) for j, due in jobs_due.items()}
    return sim, lateness

if __name__ == "__main__":
    F = json.load(open("fixture.json")); B = json.load(open("baseline.json"))
    due = {j["id"]: j["due"] for j in F["jobs"]}
    sim, late = replay(B, due, hm("08:00"), {}, n=1000)
    for j, l in late.items():
        print(j, "on time in", int((l <= 0).sum()), "/ 1000 scenarios;  worst late min:", round(float(l.max())))
    worst = int(np.argmax(late["J7"]))
    print("worst scenario index for J7:", worst)
