"""Reproducible evidence for Rehearsal's claims (issue #10).

    .venv/Scripts/python eval/run_eval.py extraction --extractor amd     # needs .env with Token Factory access
    .venv/Scripts/python eval/run_eval.py extraction --extractor rules   # labeled rule baseline, offline
    .venv/Scripts/python eval/run_eval.py recovery

Results go to eval/results/. Everything here is a builder-labeled smoke test on synthetic data, not a benchmark.
"""
import argparse
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

EVAL = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL.parent / "backend"))

from app import config  # noqa: E402
from app.checker import check  # noqa: E402
from app.extract import ExtractionError, extract_amd, extract_rules  # noqa: E402
from app.fixture import get_fixture  # noqa: E402
from app.replay import simulate  # noqa: E402
from app.solver import effective_due, effective_priority, kpis, label_changes, outage_windows, plan_alternatives, solve  # noqa: E402
from app.timeutil import hm  # noqa: E402
from app.validate import validate_constraints  # noqa: E402

RESULTS = EVAL / "results"


def _jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _labels():
    final = EVAL / "labels" / "final.jsonl"
    if final.exists():
        return {x["id"]: x for x in _jsonl(final)}, "final (reconciled by both builders)"
    return {x["id"]: x for x in _jsonl(EVAL / "labels" / "muskan.jsonl")}, \
        "DRAFT: one builder's labels, not yet independently labeled and reconciled"


def _matches(pred, exp):
    return pred["type"] == exp["type"] and all(pred["params"].get(k) == v for k, v in exp["params"].items())


# ---------------------------------------------------------------- extraction

def run_extraction(extractor: str):
    F = get_fixture()
    labels, label_note = _labels()
    rows, latencies = [], []
    for msg in _jsonl(EVAL / "messages.jsonl"):
        lab = labels[msg["id"]]
        try:
            if extractor == "amd":
                try:
                    res = extract_amd(msg["message"], F)
                except ExtractionError as e:
                    if e.code != "amd_rate_limited":
                        raise
                    time.sleep(61)  # shared team key: wait out the per-minute window once
                    res = extract_amd(msg["message"], F)
            else:
                res = extract_rules(msg["message"], F)
            origin = "amd_model" if extractor == "amd" else "rule_fallback"
            pred = validate_constraints(msg["message"], res["constraints"], F, origin=origin)
            trace, error = res["trace"], None
            latencies.append(trace["latency_ms"])
        except ExtractionError as e:
            pred, trace, error = [], None, f"{e.code}: {e}"
        matched = [any(_matches(p, e) for p in pred) for e in lab["expected"]]
        false_ok = [p for p in pred if p["status"] == "ok" and not any(_matches(p, e) for e in lab["expected"])]
        reviewed = any(p["status"] == "review" for p in pred)
        correct = error is None and all(matched) and not false_ok and (reviewed or not lab["expect_review"])
        rows.append({"id": msg["id"], "category": msg["category"], "message": msg["message"], "correct": correct,
                     "expected_found": f"{sum(matched)}/{len(matched)}", "false_acceptances": len(false_ok),
                     "false_acceptance_detail": [{"type": p["type"], "params": p["params"]} for p in false_ok],
                     "expect_review": lab["expect_review"], "review_raised": reviewed, "error": error,
                     "predicted": [{"type": p["type"], "params": p["params"], "status": p["status"],
                                    "blocking": bool(p["blocking_issues"])} for p in pred],
                     "latency_ms": trace and trace["latency_ms"], "model": trace and trace["model"],
                     "raw_output": trace and trace["raw_output"]})
        if extractor == "amd":
            time.sleep(3.5)  # ~17/min: below the 20/min per-account gateway limit on the shared team key
    need_review = [r for r in rows if r["expect_review"]]
    total_ok = sum(1 for r in rows for p in r["predicted"] if p["status"] == "ok")
    summary = {
        "extractor": extractor, "model": next((r["model"] for r in rows if r["model"]), None),
        "host": config.amd_host() if extractor == "amd" else "local",
        "run_at": datetime.now().astimezone().isoformat(timespec="seconds"), "labels": label_note,
        "messages": len(rows),
        "complete_change_accuracy": f"{sum(r['correct'] for r in rows)}/{len(rows)}",
        "false_acceptances": sum(r["false_acceptances"] for r in rows),
        "constraints_auto_ok": total_ok,
        "useful_review": f"{sum(r['review_raised'] for r in need_review)}/{len(need_review)}",
        "errors": sum(1 for r in rows if r["error"]),
        "latency_ms_median": statistics.median(latencies) if latencies else None,
        "latency_ms_max": max(latencies) if latencies else None,
    }
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"extraction_{extractor}.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=2),
                                                          encoding="utf-8")
    md = [f"# Extraction: {extractor}", "",
          f"Builder-labeled set of {len(rows)} messages ({label_note}). Smoke test, not a benchmark. Synthetic factory.",
          "", "| Metric | Value |", "| --- | --- |"]
    md += [f"| {k.replace('_', ' ')} | {v} |" for k, v in summary.items() if k not in {"labels"}]
    md += ["", "| ID | Category | Correct | Expected found | False OK | Review needed / raised | Latency ms |",
           "| --- | --- | --- | --- | --- | --- | --- |"]
    md += [f"| {r['id']} | {r['category']} | {'yes' if r['correct'] else 'no'} | {r['expected_found']} | "
           f"{r['false_acceptances']} | {r['expect_review']} / {r['review_raised']} | {r['latency_ms']} |" for r in rows]
    (RESULTS / f"extraction_{extractor}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


# ---------------------------------------------------------------- recovery

def _replay_stats(F, cs, schedule, seeds, n, spread, delay):
    due, prio = effective_due(F, cs), effective_priority(F, cs)
    outages = outage_windows(F, cs)
    lat = {j: [] for j in due}
    for seed in seeds:
        _, late = simulate(schedule, due, hm(F["now"]), outages, n=n, seed=seed, spread=spread,
                           repair_extra_max=delay)
        for j in due:
            lat[j].append(late[j])
    lat = {j: np.concatenate(v) for j, v in lat.items()}
    return lat, prio


def _with_meta(cs):
    return [dict(c, status="ok", blocking_issues=[], issues=[], source_span="Held-out typed scenario", origin="user") for c in cs]


def run_recovery():
    F = get_fixture()
    spec = json.loads((EVAL / "recovery_cases.json").read_text(encoding="utf-8"))
    n, spread, delay = spec["samples_per_seed"], spec["assumptions"]["duration_spread"], \
        spec["assumptions"]["repair_delay_max_min"]
    rows = []
    for case in spec["cases"]:
        cs = _with_meta(case["constraints"])
        ot = any(c["type"] == "overtime" and c["params"]["allowed"] for c in cs)
        candidates = {}
        ref = solve(F, cs, reroute=True, overtime=ot, w_move=1)
        if ref["status"] in ("OPTIMAL", "FEASIBLE"):
            candidates["reference"] = label_changes(F, ref["schedule"])
        alternatives, infeasible = plan_alternatives(F, cs, {})
        if not alternatives:
            rows.append({"case": case["id"], "kind": case["kind"], "method": "all",
                         "result": "; ".join(f"{x['id']}: {x['solver_status']}" for x in infeasible),
                         "reference_status": ref["status"]})
            continue
        # Replay hidden: predeclared nominal rule (weighted tardiness, then overtime cost, then moved ops).
        hidden = min(alternatives, key=lambda a: (a["kpis"]["weighted_tardiness"], a["kpis"]["overtime_cost"],
                                                  a["kpis"]["moved_ops"]))
        # Replay shown: predeclared risk rule on selection seeds, then the nominal rule.
        risk, exposed = {}, {}
        for a in alternatives:
            lat, prio = _replay_stats(F, cs, a["schedule"], spec["selection_seeds"], n, spread, delay)
            risk[a["id"]] = sum(prio[j] * float((lat[j] > 1e-9).mean()) for j in lat)
            late_plan = {x["job"] for x in a["kpis"]["late_jobs"]}
            exposed[a["id"]] = sorted(j for j in lat if j not in late_plan and (lat[j] > 1e-9).mean() > 0.05)
        shown = min(alternatives, key=lambda a: (round(risk[a["id"]], 6), a["kpis"]["weighted_tardiness"],
                                                 a["kpis"]["overtime_cost"]))
        picks = {"cpu_reference": ("reference", candidates.get("reference")),
                 "rehearsal_replay_hidden": (hidden["id"], hidden["schedule"]),
                 "rehearsal_replay_shown": (shown["id"], shown["schedule"])}
        for method, (aid, schedule) in picks.items():
            if schedule is None:
                rows.append({"case": case["id"], "kind": case["kind"], "method": method, "result": ref["status"]})
                continue
            k = kpis(F, cs, schedule)
            lat, prio = _replay_stats(F, cs, schedule, spec["evaluation_seeds"], n, spread, delay)
            late_plan = {x["job"] for x in k["late_jobs"]}
            promised = [j for j in lat if j not in late_plan]
            kept = np.all(np.stack([lat[j] <= 1e-9 for j in promised]), axis=0).mean() if promised else 1.0
            rows.append({
                "case": case["id"], "kind": case["kind"], "method": method, "alternative": aid,
                "valid": check(F, cs, schedule)["valid"],
                "weighted_tardiness": k["weighted_tardiness"], "overtime_min": k["overtime_minutes"],
                "overtime_cost": k["overtime_cost"],
                "risky_promises_exposed": exposed.get(aid, []) if method == "rehearsal_replay_shown" else [],
                "heldout_expected_weighted_late_min": round(sum(prio[j] * float(np.clip(lat[j], 0, None).mean())
                                                                for j in lat), 1),
                "heldout_all_promises_kept": round(float(kept), 3),
                "heldout_samples": n * len(spec["evaluation_seeds"])})
    RESULTS.mkdir(exist_ok=True)
    meta = {"run_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "selection_seeds": spec["selection_seeds"], "evaluation_seeds": spec["evaluation_seeds"],
            "samples_per_seed": n, "assumptions": spec["assumptions"], "note": spec["note"]}
    (RESULTS / "recovery.json").write_text(json.dumps({"meta": meta, "rows": rows}, indent=2), encoding="utf-8")
    md = ["# Held-out recovery comparison", "",
          f"{len(spec['cases'])} frozen synthetic scenarios: h1 is the demo/reference case, the others are held out. "
          f"Same CP-SAT engine with a 10 s cap per policy solve (the CPU reference is one solve; Rehearsal solves "
          f"2-3 policies), not an equal total budget; every case here solved to optimality well within it. "
          f"Selection seeds {spec['selection_seeds']}; outcomes on separate seeds {spec['evaluation_seeds']} "
          f"x {n} samples. Synthetic uncertainty, not calibrated to a real factory.", "",
          "| Case | Kind | Method | Plan | Valid | Weighted tardiness (min) | Overtime min / cost | "
          "Risky promises exposed | Held-out E[weighted late min] | Held-out P(all promises kept) |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        if "valid" not in r:
            md.append(f"| {r['case']} | {r['kind']} | {r['method']} | {r['result']} | - | - | - | - | - | - |")
            continue
        md.append(f"| {r['case']} | {r['kind']} | {r['method']} | {r['alternative']} | {r['valid']} | "
                  f"{r['weighted_tardiness']} | {r['overtime_min']} / {r['overtime_cost']} | "
                  f"{', '.join(r['risky_promises_exposed']) or '-'} | {r['heldout_expected_weighted_late_min']} | "
                  f"{r['heldout_all_promises_kept']} |")
    (RESULTS / "recovery.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["extraction", "recovery"])
    ap.add_argument("--extractor", choices=["amd", "rules"], default="amd")
    args = ap.parse_args()
    run_extraction(args.extractor) if args.what == "extraction" else run_recovery()
