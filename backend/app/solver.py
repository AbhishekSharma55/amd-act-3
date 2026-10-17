"""A3: flexible job-shop recovery with CP-SAT, plus policy alternatives and honest infeasibility."""
from ortools.sat.python import cp_model

from . import config
from .timeutil import fmt, hm
from .validate import validate_for_solve

NUM_WORKERS = config.SOLVER_WORKERS


def solve(F, constraints, reroute, overtime, w_move=1, time_limit_s=10):
    validate_for_solve(F, constraints)
    now = hm(F["now"]); shift_end = hm(F["shift"]["end"]); H = hm(F["shift"]["overtime_until"])
    ot = [c["params"] for c in constraints if c["type"] == "overtime" and c["params"]["allowed"]]
    limit = min(H, *(hm(p.get("until") or F["shift"]["overtime_until"]) for p in ot)) if overtime and ot else shift_end
    downs = outage_windows(F, constraints)
    hard = {c["params"]["job"]: (hm(c["params"]["time"]), c["id"])
            for c in constraints if c["type"] == "due_date" and c["params"].get("hard")}
    due, prio = effective_due(F, constraints), effective_priority(F, constraints)

    base = {(a["job"], a["op"]): a for a in F["committed_schedule"]}
    m = cp_model.CpModel()
    per_machine = {mc["id"]: [] for mc in F["machines"]}
    rec, obj, ot_terms, job_end = {}, [], [], {}

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
                ot_v = m.new_int_var(0, H - shift_end, f"ot{key}")
                ot_start = m.new_int_var(shift_end, H, f"ot_start{key}")
                m.add_max_equality(ot_start, [s, shift_end])
                m.add_max_equality(ot_v, [0, e - ot_start]); ot_terms.append(ot_v)
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
    primary = 60 * sum(obj) + (cost * sum(ot_terms) if ot_terms else 0)
    # Lexicographic tie-break (earlier starts) so equal-cost optima resolve the same way on every host.
    starts = [s for s, *_ in rec.values()]
    m.minimize((len(starts) * H + 1) * primary + sum(starts))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_workers = NUM_WORKERS
    status = solver.solve(m)
    name = solver.status_name(status)
    time_ms = round(solver.wall_time * 1000)
    if status == cp_model.INFEASIBLE:
        core = [lit_to_cid[i] for i in solver.sufficient_assumptions_for_infeasibility() if i in lit_to_cid]
        return {"status": name, "time_ms": time_ms, "hard_due_in_conflict": core}
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": name, "time_ms": time_ms}  # UNKNOWN: no feasible plan found within the search budget

    schedule = []
    for (jid, op), (s, e, choice, frozen, interrupted) in rec.items():
        mc = next(k for k, p in choice.items() if p is None or solver.value(p))
        schedule.append({"job": jid, "op": op, "machine": mc,
                         "start": fmt(solver.value(s)), "end": fmt(solver.value(e))})
    overtime_minutes = sum(solver.value(t) for t in ot_terms)
    return {"status": name, "time_ms": time_ms,
            "objective": solver.value(primary) / 60, "schedule": schedule,
            "overtime_minutes": overtime_minutes, "overtime_cost": overtime_minutes * cost / 60}


def outage_windows(F, constraints):
    """Merged [from, until) windows per machine; one machine can have several outages."""
    downs = {}
    for c in constraints:
        if c["type"] == "machine_down":
            p = c["params"]
            downs.setdefault(p["machine"], []).append((hm(p.get("from") or F["now"]), hm(p["until"])))
    for mc, windows in downs.items():
        merged = []
        for f, u in sorted(windows):
            if merged and f <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], u))
            else:
                merged.append((f, u))
        downs[mc] = merged
    return downs


def effective_due(F, constraints):
    due = {j["id"]: hm(j["due"]) for j in F["jobs"]}
    for c in constraints:
        if c["type"] == "due_date":
            due[c["params"]["job"]] = hm(c["params"]["time"])
    return due


def effective_priority(F, constraints):
    prio = {j["id"]: j["priority"] for j in F["jobs"]}
    for c in constraints:
        if c["type"] == "priority":
            prio[c["params"]["job"]] = c["params"]["level"]
    return prio


# ---------------------------------------------------------------- alternatives

POLICIES = [
    ("alt_keep", "Keep machines", False, True, 5),
    ("alt_reroute", "Re-route to qualified machines", True, False, 1),
    ("alt_reroute_overtime", "Re-route + overtime", True, True, 1),
]


def label_changes(F, schedule):
    now = hm(F["now"])
    base = {(a["job"], a["op"]): a for a in F["committed_schedule"]}
    out = []
    for a in sorted(schedule, key=lambda a: (a["machine"], hm(a["start"]))):
        b = base[(a["job"], a["op"])]
        if hm(b["start"]) < now and a["start"] == b["start"] and a["machine"] == b["machine"]:
            ch = "frozen"
        elif hm(b["start"]) < now:
            ch = "restarted" if a["machine"] == b["machine"] else f"restarted_on_{a['machine']}"
        elif a["machine"] != b["machine"]:
            ch = f"moved_from_{b['machine']}"
        elif a["start"] != b["start"]:
            ch = "retimed"
        else:
            ch = "none"
        out.append({**a, "change": ch})
    return out


def occupied_overtime(F, schedule):
    shift_end = hm(F["shift"]["end"])
    return sum(max(0, hm(a["end"]) - max(hm(a["start"]), shift_end)) for a in schedule)


def kpis(F, constraints, schedule):
    due = effective_due(F, constraints)
    late = []
    for j in F["jobs"]:
        end = max(hm(a["end"]) for a in schedule if a["job"] == j["id"])
        if end > due[j["id"]]:
            late.append({"job": j["id"], "minutes_late": end - due[j["id"]], "customer": j["customer"]})
    ot = occupied_overtime(F, schedule)
    prio = effective_priority(F, constraints)
    return {"late_jobs": late, "overtime_minutes": ot,
            "overtime_cost": round(ot * F["shift"]["overtime_cost_per_hour"] / 60, 2),
            "moved_ops": sum(1 for a in schedule if a["change"].startswith(("moved_from_", "restarted_on_"))),
            "retimed_ops": sum(1 for a in schedule if a["change"] in ("retimed", "restarted")),
            "weighted_tardiness": sum(prio[x["job"]] * x["minutes_late"] for x in late)}


def _describe_outages(F, constraints):
    names = {m["id"]: m["id"] for m in F["machines"]}
    parts = [f"{names[c['params']['machine']]} down {c['params'].get('from') or F['now']}-{c['params']['until']}"
             for c in constraints if c["type"] == "machine_down"]
    return ", ".join(parts)


def _explain(F, constraints, policy, result, limit):
    by_id = {c["id"]: c for c in constraints}
    outages = _describe_outages(F, constraints)
    pol = ("no re-routing" if not policy["reroute"] else "re-routing") + \
          (" and overtime until " + fmt(limit) if policy["overtime"] else " and no overtime")
    prefix = f"With {outages} and {pol}" if outages else f"With {pol}"
    core = result.get("hard_due_in_conflict", [])
    if core:
        jobs = [f"{by_id[c]['params']['job']} by {by_id[c]['params']['time']}" for c in core]
        return f"{prefix}, " + " and ".join(jobs) + (" cannot both be met." if len(jobs) > 1 else " cannot be met.")
    return f"{prefix}, the remaining work does not fit before {fmt(limit)}."


def plan_alternatives(F, constraints, allow, time_limit_s=10):
    """Solve each allowed policy; return (alternatives, infeasible) with schedules not yet checked."""
    if allow.get("relax_hard_due"):
        raise ValueError("Relaxing a hard due date is not available yet; reject or edit that constraint instead")
    validate_for_solve(F, constraints)
    ot_constraint = any(c["type"] == "overtime" and c["params"]["allowed"] for c in constraints)
    ot_ok = bool(allow.get("overtime", True)) and ot_constraint
    reroute_ok = bool(allow.get("reroute", True))
    ot_limit = min([hm(F["shift"]["overtime_until"])] + [hm(c["params"]["until"] or F["shift"]["overtime_until"])
                                                        for c in constraints if c["type"] == "overtime"
                                                        and c["params"]["allowed"]])
    alternatives, infeasible, results = [], [], {}
    for aid, label, reroute, overtime, w_move in POLICIES:
        if reroute and not reroute_ok:
            continue
        if aid == "alt_reroute_overtime" and not ot_ok:
            continue
        overtime = overtime and ot_ok
        policy = {"reroute": reroute, "overtime": overtime}
        r = solve(F, constraints, reroute=reroute, overtime=overtime, w_move=w_move, time_limit_s=time_limit_s)
        results[aid] = r
        if r["status"] in ("OPTIMAL", "FEASIBLE"):
            schedule = label_changes(F, r["schedule"])
            twin = next((a for a in alternatives if _same(a["schedule"], schedule)), None)
            if twin:
                twin["merged_with"].append(aid)
                continue
            alternatives.append({"id": aid, "label": label, "policy": policy,
                                 "solver": {"status": r["status"], "time_ms": r["time_ms"],
                                            "objective": round(r["objective"], 2)},
                                 "schedule": schedule, "kpis": kpis(F, constraints, schedule), "merged_with": []})
        else:
            limit = ot_limit if overtime else hm(F["shift"]["end"])
            entry = {"id": aid, "policy": policy, "label": label, "solver_status": r["status"],
                     "solver": {"status": r["status"], "time_ms": r["time_ms"]}}
            if r["status"] == "INFEASIBLE":
                core = r.get("hard_due_in_conflict", [])
                outage_ids = [c["id"] for c in constraints if c["type"] == "machine_down"]
                entry.update({"conflict": outage_ids + core, "conflict_kind": "sufficient",
                              "explanation": _explain(F, constraints, policy, r, limit)})
            else:
                entry.update({"conflict": [], "conflict_kind": None,
                              "explanation": f"No feasible plan found within the {time_limit_s} s search budget. "
                                             "This is not a proof that no plan exists."})
            infeasible.append(entry)

    feasible_policies = [a["policy"] for a in alternatives]
    for entry in infeasible:
        options = []
        if not entry["policy"]["reroute"] and any(p["reroute"] for p in feasible_policies):
            options.append({"type": "allow_reroute", "available": True})
        if not entry["policy"]["overtime"] and any(p["overtime"] for p in feasible_policies):
            options.append({"type": "allow_overtime", "available": True})
        for cid in [c for c in entry.get("conflict", []) if c.startswith("c") and _is_hard(constraints, c)]:
            options.append({"type": "relax_hard_due", "constraint": cid, "available": False,
                            "note": "Disabled: reject or edit the hard date and solve again"})
        entry["possible_concessions"] = options
    return alternatives, infeasible


def _is_hard(constraints, cid):
    return any(c["id"] == cid and c["type"] == "due_date" and c["params"].get("hard") for c in constraints)


def _same(a, b):
    key = lambda s: sorted((x["job"], x["op"], x["machine"], x["start"], x["end"]) for x in s)
    return key(a) == key(b)
