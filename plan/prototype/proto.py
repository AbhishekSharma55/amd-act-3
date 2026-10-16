"""Scratch prototype: validate the example fixture + demo story for the plan docs."""
import json, sys
from ortools.sat.python import cp_model

def hm(s):
    h, m = s.split(":"); return int(h) * 60 + int(m)
def fmt(x):
    return f"{x//60:02d}:{x%60:02d}"


def solve(F, now, downs, hard_due, allow_alt, allow_ot, baseline=None, w_move=0, time_limit=10):
    m = cp_model.CpModel()
    shift_end = hm(F["shift"]["end"]); ot_end = hm(F["shift"]["overtime_until"])
    H = ot_end
    per_m = {k["id"]: [] for k in F["machines"]}
    ends, starts, pres_map, job_end = {}, {}, {}, {}
    base = {(a["job"], a["op"]): a for a in (baseline or [])}
    obj = []
    ot_vars = []
    for j in F["jobs"]:
        prev_end = None
        for o in j["ops"]:
            key = (j["id"], o["op"])
            b = base.get(key)
            fixed = b is not None and hm(b["start"]) < now and not (b["machine"] in downs and hm(b["end"]) > downs[b["machine"]][0])  # frozen unless interrupted by outage
            s = m.new_int_var(hm(F["shift"]["start"]), H, f"s{key}")
            e = m.new_int_var(hm(F["shift"]["start"]), H, f"e{key}")
            if fixed:
                m.add(s == hm(b["start"])); m.add(e == hm(b["end"]))
                iv = m.new_interval_var(s, hm(b["end"]) - hm(b["start"]), e, f"i{key}")
                per_m[b["machine"]].append(iv)
                pres_map[key] = {b["machine"]: None}
            else:
                if baseline is not None:
                    m.add(s >= now)
                lits = {}
                for mc, d in o["eligible"].items():
                    if not allow_alt and b and mc != b["machine"]:
                        continue
                    p = m.new_bool_var(f"p{key}{mc}")
                    iv = m.new_optional_interval_var(s, d, e, p, f"i{key}{mc}")
                    per_m[mc].append(iv); lits[mc] = p
                m.add_exactly_one(lits.values())
                pres_map[key] = lits
                if b and w_move:
                    obj.append(w_move * sum(p for mc, p in lits.items() if mc != b["machine"]))
                    dev = m.new_int_var(0, H, f"dev{key}")
                    m.add(dev >= s - hm(b["start"])); m.add(dev >= hm(b["start"]) - s)
                    obj.append(dev)
            if not allow_ot:
                m.add(e <= shift_end)
            else:
                ot = m.new_int_var(0, ot_end - shift_end, f"ot{key}")
                m.add(ot >= e - shift_end); ot_vars.append(ot)
            if prev_end is not None:
                m.add(s >= prev_end)
            prev_end = e; ends[key] = e; starts[key] = s
        job_end[j["id"]] = prev_end
        tard = m.new_int_var(0, H, f"t{j['id']}")
        m.add(tard >= prev_end - hm(j["due"]))
        obj.append(100 * j["priority"] * tard)
        obj.append(prev_end)  # tie-break: finish early
    for mc, d in downs.items():
        per_m[mc].append(m.new_fixed_size_interval_var(d[0], d[1] - d[0], f"down{mc}"))
    for mc, ivs in per_m.items():
        m.add_no_overlap(ivs)
    for jid, t in hard_due.items():
        m.add(job_end[jid] <= t)
    obj.append(F["shift"]["overtime_cost_per_hour"] * sum(ot_vars) if ot_vars else 0)
    m.minimize(sum(obj))
    sv = cp_model.CpSolver(); sv.parameters.max_time_in_seconds = time_limit; sv.parameters.num_workers = 8
    st = sv.solve(m)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return sv.status_name(st), None
    out = []
    for key, lits in pres_map.items():
        mc = next(k for k, p in lits.items() if p is None or sv.value(p))
        out.append({"job": key[0], "op": key[1], "machine": mc, "start": fmt(sv.value(starts[key])), "end": fmt(sv.value(ends[key]))})
    out.sort(key=lambda a: (a["machine"], a["start"]))
    return sv.status_name(st), out

def late(F, sched):
    res = {}
    for j in F["jobs"]:
        end = max(hm(a["end"]) for a in sched if a["job"] == j["id"])
        res[j["id"]] = max(0, end - hm(j["due"]))
    return {k: v for k, v in res.items() if v}

if __name__ == "__main__":
    F = json.load(open(sys.argv[1]))
    st, base = solve(F, now=hm(F["shift"]["start"]), downs={}, hard_due={}, allow_alt=True, allow_ot=False)
    print("BASELINE", st, "late:", late(F, base))
    for a in base: print("  ", a)
    now = hm(F["now"])
    downs = {"M2": (now, hm("14:00"))}
    for name, kw in [("A keep-machines+OT", dict(allow_alt=False, allow_ot=True, w_move=5)),
                     ("B reroute", dict(allow_alt=True, allow_ot=False, w_move=1)),
                     ("C overtime", dict(allow_alt=True, allow_ot=True, w_move=1))]:
        for hard in ({}, {"J7": hm("16:00")}):
            st, s = solve(F, now, downs, hard, baseline=base, **kw)
            ot = sum(max(0, hm(a["end"]) - hm(F["shift"]["end"])) for a in s) if s else None
            moved = sum(1 for a in s for b in base if (a["job"], a["op"]) == (b["job"], b["op"]) and a["machine"] != b["machine"]) if s else None
            print(name, "hardJ7" if hard else "soft", st, "late:", late(F, s) if s else "-", "ot_min:", ot, "moved:", moved)
    json.dump(base, open(sys.argv[2], "w"), indent=1)
