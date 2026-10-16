"""Generate valid mock JSON files for plan/mocks from the scratch prototype (demo scenario)."""
import json, sys, os
import numpy as np
from proto import solve, hm, fmt
from replay_proto import replay

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
F = json.load(open("fixture.json"))
base = sorted(json.load(open("baseline.json")), key=lambda a: (a["job"], a["op"]))
F["committed_schedule"] = base
now = hm(F["now"])
downs = {"M2": (now, hm("14:00"))}
dump = lambda name, obj: json.dump(obj, open(os.path.join(OUT, name), "w"), indent=2)
dump("factory.json", F)

MSG = "Mill M2 is unavailable until 14:00. Order J7 still needs to ship at 16:00. Overtime requires approval."
constraints = [
    {"id": "c1", "type": "machine_down", "params": {"machine": "M2", "from": "10:00", "until": "14:00"},
     "source_span": "Mill M2 is unavailable until 14:00", "status": "ok",
     "issues": ["Outage interrupts J1 op 2 (in progress on M2); it will restart after repair"], "origin": "amd_model"},
    {"id": "c2", "type": "due_date", "params": {"job": "J7", "time": "16:00", "hard": True},
     "source_span": "Order J7 still needs to ship at 16:00", "status": "ok", "issues": [], "origin": "amd_model"},
    {"id": "c3", "type": "overtime", "params": {"allowed": True, "until": "20:00"},
     "source_span": "Overtime requires approval", "status": "ok",
     "issues": ["Overtime is a concession and needs approval"], "origin": "amd_model"},
]
RUN = "r_mock_0001"
dump("extract.json", {"run_id": RUN, "message": MSG, "constraints": constraints, "trace": {
    "provider": "AMD Token Factory", "model": "MOCK", "host": "MOCK", "latency_ms": 0, "attempts": 1,
    "usage": {"prompt_tokens": 0, "completion_tokens": 0}, "raw_output": "MOCK - replace with real model output", "fallback_used": False}})

# review example
dump("extract_review.json", {"run_id": "r_mock_0002", "message": "Mill 4 is down after lunch. J7 ships at 4.", "constraints": [
    {"id": "c1", "type": "machine_down", "params": {"machine": "Mill 4", "from": None, "until": None},
     "source_span": "Mill 4 is down after lunch", "status": "review",
     "issues": ["Unknown machine 'Mill 4'. Known: Mill M1, Mill M2, Lathe L3", "No end time given for the outage", "'after lunch' is not a time"], "origin": "amd_model"},
    {"id": "c2", "type": "due_date", "params": {"job": "J7", "time": "16:00", "hard": False},
     "source_span": "J7 ships at 4", "status": "review",
     "issues": ["'4' interpreted as 16:00; please confirm"], "origin": "amd_model"}],
    "trace": {"provider": "AMD Token Factory", "model": "MOCK", "host": "MOCK", "latency_ms": 0, "attempts": 1,
              "usage": {"prompt_tokens": 0, "completion_tokens": 0}, "raw_output": "MOCK", "fallback_used": False}})

bmap = {(a["job"], a["op"]): a for a in base}
def label(s):
    out = []
    for a in sorted(s, key=lambda a: (a["machine"], a["start"])):
        b = bmap[(a["job"], a["op"])]
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

def kpis(s):
    late = []
    for j in F["jobs"]:
        end = max(hm(a["end"]) for a in s if a["job"] == j["id"])
        if end > hm(j["due"]):
            late.append({"job": j["id"], "minutes_late": end - hm(j["due"]), "customer": j["customer"]})
    ot = sum(max(0, hm(a["end"]) - max(hm(a["start"]), hm(F["shift"]["end"]))) for a in s)
    return {"late_jobs": late, "overtime_minutes": ot, "overtime_cost": round(ot / 60 * F["shift"]["overtime_cost_per_hour"], 2),
            "moved_ops": sum(1 for a in s if a["change"].startswith("moved") or a["change"].startswith("restarted_on")),
            "retimed_ops": sum(1 for a in s if a["change"] in ("retimed", "restarted"))}

st, s = solve(F, now, downs, {"J7": hm("16:00")}, allow_alt=True, allow_ot=False, baseline=base, w_move=1)
assert s, st
s = label(s); k = kpis(s)
conc = [{"id": f"k{i+1}", "type": "late_delivery", "job": l["job"], "detail": f"{l['job']} ({l['customer']}) ships {l['minutes_late']} min late"} for i, l in enumerate(k["late_jobs"])]
alt = {"id": "alt_reroute", "label": "Re-route to qualified machines", "policy": {"reroute": True, "overtime": False},
       "solver": {"status": st, "time_ms": 0, "objective": 0}, "schedule": s, "kpis": k, "concessions": conc,
       "checker": {"valid": True, "violations": []}, "merged_with": ["alt_reroute_overtime"]}
st2, _ = solve(F, now, downs, {"J7": hm("16:00")}, allow_alt=False, allow_ot=True, baseline=base, w_move=5)
dump("solve.json", {"run_id": RUN, "status": "ok", "alternatives": [alt], "infeasible": [
    {"policy": {"reroute": False, "overtime": True}, "label": "Keep machines", "solver_status": st2,
     "conflict": ["c1", "c2"], "conflict_kind": "sufficient",
     "explanation": "With M2 down until 14:00 and no re-routing, J7 cannot finish by 16:00.",
     "possible_concessions": [{"type": "relax_hard_due", "constraint": "c2"}, {"type": "allow_reroute"}]}]})
print("reroute:", st, k, "| keep machines + hard J7:", st2)

due = {j["id"]: j["due"] for j in F["jobs"]}
N = 500
sim, lat = replay(s, due, now, {"M2": ("10:00", "14:00")}, n=N, seed=7)
jobs = []
for j in due:
    jobs.append({"job": j, "on_time": int((lat[j] <= 0).sum()), "of": N, "p90_finish": fmt(int(np.percentile(lat[j] + hm(due[j]), 90)))})
order = sorted(due, key=lambda j: -next(x["priority"] for x in F["jobs"] if x["id"] == j))
target = next((j for j in order if (lat[j] > 0).any() and not any(l["job"] == j for l in k["late_jobs"])), None)
fail = None
if target:
    idx = int(np.argmax(lat[target]))
    tl = []
    for a, ss, ee in sim:
        tl.append({"job": a["job"], "op": a["op"], "machine": a["machine"], "start": fmt(int(round(ss[idx]))), "end": fmt(int(round(ee[idx])))})
    fail = {"index": idx, "reason": f"{target} misses {due[target]} by {int(round(lat[target][idx]))} min", "timeline": tl}
dump("replay.json", {"run_id": RUN, "alternative_id": "alt_reroute", "device": "cpu-numpy", "samples": N, "elapsed_ms": 0,
    "assumptions": {"duration_spread": [0.9, 1.3], "repair_delay_max_min": 90, "seed": 7, "note": "Synthetic uncertainty, not calibrated to a real factory"},
    "jobs": jobs, "failing_scenario": fail})
print("replay:", [(x["job"], x["on_time"]) for x in jobs], "fail:", fail and fail["reason"])

rows = ["machine,sequence,job,op,start,end,changed"]
seq = {}
for a in s:
    seq[a["machine"]] = seq.get(a["machine"], 0) + 1
    rows.append(f'{a["machine"]},{seq[a["machine"]]},{a["job"]},{a["op"]},{a["start"]},{a["end"]},{a["change"]}')
dump("approve.json", {"dispatch_csv": "\n".join(rows) + "\n", "decision_record": {
    "run_id": RUN, "approved_at": "2026-10-16T10:21:44+05:30", "approver": "Shift supervisor (demo)", "message": MSG,
    "constraints": constraints, "alternative_id": "alt_reroute", "concessions": conc, "checker": {"valid": True, "violations": []},
    "amd_trace": {"model": "MOCK", "latency_ms": 0}, "replay": {"samples": N, "device": "cpu-numpy"}, "data_notice": "Synthetic demo data"}})
print("\n".join(rows))
