from app.timeutil import fmt, hm


def tiny_fixture(durations=(60, 60), now="18:00", due="20:00"):
    """One machine, one operation per job; explicit committed release times."""
    jobs, base = [], []
    start = hm(now)
    for i, duration in enumerate(durations, 1):
        jid = f"J{i}"
        jobs.append({"id": jid, "customer": f"Customer {i}", "due": due, "priority": 1,
                     "ops": [{"op": 1, "eligible": {"M1": duration}}]})
        base.append({"job": jid, "op": 1, "machine": "M1", "start": fmt(start), "end": fmt(start + duration)})
        start += duration
    return {"now": now, "shift": {"start": "08:00", "end": "18:00", "overtime_until": "20:00", "overtime_cost_per_hour": 45},
            "machines": [{"id": "M1", "name": "Mill M1", "aliases": []}], "jobs": jobs, "committed_schedule": base}


def constraint(cid, kind, **params):
    return {"id": cid, "type": kind, "params": params, "status": "accepted", "source_span": "Reviewed test input",
            "issues": [], "blocking_issues": [], "origin": "user"}
