"""A2: check every proposed constraint against the fixture and the original message.

The model's output is never trusted: IDs, clock times, required fields, exact source spans and
contradictions are checked here. `blocking_issues` must be corrected (edit + revalidate) or the item
rejected; a complete but ambiguous interpretation only needs confirmation.
"""
import re
from copy import deepcopy

from .timeutil import fmt, hm

TYPES = ("machine_down", "due_date", "priority", "overtime", "unsupported")
VAGUE_START = re.compile(r"\b(after|from|starting|since|later|lunch|tomorrow|tonight|evening|afternoon|morning|"
                         r"around|soon|baad|se)\b", re.I)


def norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _span_norm(s) -> str:
    s = norm(s).replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"[\s\"'.,;:!?()\-]+", " ", s).strip()


def span_ok(span, message) -> bool:
    return bool(_span_norm(span)) and _span_norm(span) in _span_norm(message)


def resolve_machine(name, fixture):
    n = norm(name)
    if not n:
        return None
    for m in fixture["machines"]:
        if n in {norm(m["id"]), norm(m["name"]), *map(norm, m["aliases"])}:
            return m["id"]
    return None


def resolve_job(name, fixture):
    """Job ID ("J7", "order j7") or its customer's name ("Gamma Aerospace")."""
    raw = norm(name)
    n = raw.replace("order ", "").replace("job ", "").replace(" ", "")
    for j in fixture["jobs"]:
        if n == norm(j["id"]) or (raw and raw == norm(j.get("customer"))):
            return j["id"]
    return None


def valid_time(t, fixture) -> bool:
    try:
        x = hm(t)
    except (TypeError, ValueError):
        return False
    return hm(fixture["shift"]["start"]) <= x <= hm(fixture["shift"]["overtime_until"])


def normalize_time(value):
    """Accept what a model plausibly returns ('14:00', '2pm', '2:30 PM', '14.00', '9:00') -> 'HH:MM' or None."""
    if value is None:
        return None
    if isinstance(value, int) and 0 <= value <= 23:
        return fmt(value * 60)
    s = norm(value).replace(".", ":")
    if s in {"", "null", "none", "unknown", "?"}:
        return None
    if s == "noon":
        return "12:00"
    s = re.sub(r"\s*(hrs|hours|hr|h)$", "", s)
    if re.fullmatch(r"\d{4}", s):  # "1430"
        s = f"{s[:2]}:{s[2:]}"
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm|a:m:|p:m:)?", s)
    if not m:
        return value if isinstance(value, str) else None
    h, mins, ap = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").replace(":", "")
    if ap:
        if not 1 <= h <= 12:
            return value
        h = (h % 12) + (12 if ap == "pm" else 0)
    if not (0 <= h <= 23 and 0 <= mins <= 59):
        return value
    return f"{h:02d}:{mins:02d}"


def time_evidenced(t: str, span: str) -> bool:
    """True when the span states this clock time unambiguously (24-hour, or 12-hour with am/pm)."""
    try:
        x = hm(t)
    except ValueError:
        return False
    s = norm(span)
    ampm = r"\s*([ap])\.?\s?m\b\.?"

    def clock(h, mins, ap):
        if ap:
            if not 1 <= h <= 12:
                return None
            h = h % 12 + (12 if ap == "p" else 0)
        return h * 60 + mins

    for m in re.finditer(rf"(?<!\d)(\d{{1,2}})[:.](\d{{2}})(?!\d)(?:{ampm})?", s):
        if clock(int(m.group(1)), int(m.group(2)), m.group(3)) == x:
            return True
    for m in re.finditer(rf"(?<![\d:.])(\d{{1,2}}){ampm}", s):
        if clock(int(m.group(1)), 0, m.group(2)) == x:
            return True
    for m in re.finditer(r"(?<![\d:.])([01]\d|2[0-3])([0-5]\d)(?:\s*hrs?\b|\s*hours\b|(?!\d))", s):  # "1430 hrs"
        if int(m.group(1)) * 60 + int(m.group(2)) == x:
            return True
    return x == 12 * 60 and "noon" in s


def _bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, str) and v.strip().lower() in {"true", "false"}:
        return v.strip().lower() == "true"
    return None


def _params(raw: dict) -> dict:
    p = raw.get("params")
    if isinstance(p, dict):
        return dict(p)
    return {k: v for k, v in raw.items() if k not in {"id", "type", "source_span", "status", "issues",
                                                       "blocking_issues", "origin"}}


def _check_one(raw: dict, message: str, F: dict, edited_fields: set[str] | None = None) -> dict:
    """Normalize one proposal. Returns a constraint with private `_review` / `_blocking` lists.

    Only fields the planner actually changed bypass interpretation confirmation.
    """
    edited_fields = edited_fields or set()
    kind = raw.get("type") if raw.get("type") in TYPES else "unsupported"
    p = _params(raw)
    span = raw.get("source_span") if isinstance(raw.get("source_span"), str) else ""
    review, blocking, notes = [], [], []
    now, shift_end, limit = hm(F["now"]), hm(F["shift"]["end"]), hm(F["shift"]["overtime_until"])
    known = ", ".join(m["name"] for m in F["machines"])

    def need_time(field, value, label, required=True, default=None):
        t = normalize_time(value)
        if t is not None and t == default:
            return t  # the documented default, not something read from the message
        if t is None:
            if required:
                review.append(f"No {label} given")
                blocking.append(f"Provide an explicit {label}")
            return None
        if not valid_time(t, F):
            review.append(f"{label.capitalize()} '{value}' is not a valid time inside the working day "
                          f"({F['shift']['start']}-{F['shift']['overtime_until']})")
            blocking.append(f"Provide a valid {label} (HH:MM)")
            return t
        if span and field not in edited_fields and not time_evidenced(t, span):
            review.append(f"'{span}' was read as {label} {t}; please confirm")
        return t

    if raw.get("type") not in TYPES:
        note = p.get("note") or f"Unsupported request type '{raw.get('type')}'"
        p = {"note": str(note)}
    if kind == "machine_down":
        name = p.get("machine")
        mid = resolve_machine(name, F)
        if mid is None:
            review.append(f"Unknown machine '{name}'. Known: {known}")
            blocking.append("Choose a known machine")
        until = need_time("until", p.get("until"), "repair end time")
        start = None
        if p.get("from") is None:
            if span and VAGUE_START.search(span):
                review.append(f"'{span}' gives no explicit outage start")
                blocking.append("Provide an explicit outage start time")
            else:
                start = F["now"]
        else:
            start = need_time("from", p.get("from"), "outage start", default=F["now"])
        if start and valid_time(start, F) and hm(start) < now:
            notes.append(f"Outage start {start} is before now ({F['now']}); planning treats it from {F['now']}")
            start = F["now"]
        if until and valid_time(until, F):
            if hm(until) <= now:
                review.append(f"Repair end {until} is not after now ({F['now']}); the outage is already over")
                blocking.append("Provide a repair end after now, or reject this item")
            elif start and valid_time(start, F) and hm(start) >= hm(until):
                review.append(f"Outage start {start} is not before its end {until}")
                blocking.append("Outage end must be after its start")
        p = {"machine": mid or name, "from": start, "until": until}
    elif kind == "due_date":
        jid = resolve_job(p.get("job"), F)
        if jid is None:
            review.append(f"Unknown job '{p.get('job')}'. Known: {', '.join(j['id'] for j in F['jobs'])}")
            blocking.append("Choose a known job")
        t = need_time("time", p.get("time"), "due time")
        hard = _bool(p.get("hard"))
        if hard is None:
            review.append("The message does not say whether this date is fixed; treated as a soft date")
            hard = False
        if t and valid_time(t, F) and hm(t) <= now:
            review.append(f"Due time {t} is not after now ({F['now']})")
        p = {"job": jid or p.get("job"), "time": t, "hard": hard}
    elif kind == "priority":
        jid = resolve_job(p.get("job"), F)
        if jid is None:
            review.append(f"Unknown job '{p.get('job')}'")
            blocking.append("Choose a known job")
        level = p.get("level")
        try:
            level = int(level) if not isinstance(level, bool) else None
        except (TypeError, ValueError):
            level = None
        if level not in (1, 2, 3):
            review.append(f"Priority '{p.get('level')}' is not 1 (normal), 2 or 3 (critical)")
            blocking.append("Choose a priority level 1-3")
        p = {"job": jid or p.get("job"), "level": level}
    elif kind == "overtime":
        allowed = _bool(p.get("allowed"))
        if allowed is None:
            review.append("Unclear whether overtime is allowed")
            blocking.append("State whether overtime is allowed")
        until = None
        if allowed and p.get("until") is not None:
            until = normalize_time(p.get("until"))
            if not valid_time(until, F) or hm(until) < shift_end:
                review.append(f"Overtime cutoff '{p.get('until')}' must be between {F['shift']['end']} and "
                              f"{F['shift']['overtime_until']}")
                blocking.append("Provide a valid overtime cutoff")
            elif span and "until" not in edited_fields and until != F["shift"]["overtime_until"] and not time_evidenced(until, span):
                review.append(f"'{span}' was read as overtime until {until}; please confirm")
        if allowed:
            until = until or F["shift"]["overtime_until"]
            notes.append("Overtime is a concession and needs approval")
        p = {"allowed": allowed, "until": until}
    else:
        review.append(f"Rehearsal cannot model this: {p.get('note') or span}")
        blocking.append("Handle this outside the plan and reject it here")
        p = {"note": str(p.get("note") or span)}

    if not span_ok(span, message):
        review.append("The model quoted text that is not in the message")
        blocking.append("Source text must come from the message; reject this item or re-send the message")
    return {"type": kind, "params": p, "source_span": span, "_review": review, "_blocking": blocking,
            "_notes": notes}


def _cross_checks(items: list[dict], F: dict) -> None:
    groups: dict[tuple, list[dict]] = {}
    for c in items:
        if c["type"] in {"due_date", "priority"} and c["params"].get("job"):
            groups.setdefault((c["type"], c["params"]["job"]), []).append(c)
        elif c["type"] == "overtime":
            groups.setdefault(("overtime", None), []).append(c)
    for (kind, job), lst in groups.items():
        if len({repr(sorted(c["params"].items())) for c in lst}) > 1:
            what = {"due_date": f"Two different due dates for {job}", "priority": f"Two different priorities for {job}",
                    "overtime": "The message gives conflicting overtime instructions"}[kind]
            for c in lst:
                c["_review"].append(what)
                c["_blocking"].append("Resolve the contradiction: keep one item and reject the other")
    for c in items:
        if c["type"] != "machine_down" or c["_blocking"]:
            continue
        p = c["params"]
        f, u = hm(p["from"]), hm(p["until"])
        for a in F["committed_schedule"]:
            if a["machine"] == p["machine"] and hm(a["start"]) < f < hm(a["end"]):
                c["_notes"].append(f"Outage interrupts {a['job']} op {a['op']} (in progress on {a['machine']}); "
                                   f"it will restart after repair")
        if p["machine"] and f >= hm(F["shift"]["end"]) and u > f:
            c["_notes"].append("Outage is outside the normal shift")


def _finish(c: dict, cid: str, origin: str) -> dict:
    review, blocking, notes = c.pop("_review"), c.pop("_blocking"), c.pop("_notes")
    return {"id": cid, "type": c["type"], "params": c["params"], "source_span": c["source_span"],
            "status": "review" if review or blocking else "ok",
            "blocking_issues": list(dict.fromkeys(blocking)), "issues": list(dict.fromkeys(review + notes)),
            "origin": origin}


def validate_constraints(message: str, proposals: list, F: dict, origin: str = "amd_model") -> list[dict]:
    """Model proposals -> constraint objects as returned by /api/extract."""
    items = [_check_one(raw if isinstance(raw, dict) else {"type": "unsupported", "params": {"note": str(raw)}},
                        message, F) for raw in (proposals or [])]
    _cross_checks(items, F)
    return [_finish(c, f"c{i}", origin) for i, c in enumerate(items, 1)]


class ReviewError(ValueError):
    pass


def review_constraints(draft: dict, client: list, F: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Revalidate the planner's reviewed list against the server-stored extraction.

    `client` holds the items the planner kept, each with status ok/accepted (or review while still
    undecided) and possibly edited params. Returns (constraints, rejected, edits). The source span
    and type must match the stored extraction; edited params are revalidated and marked origin "user".
    """
    if not isinstance(client, list):
        raise ReviewError("constraints must be a list")
    stored = {c["id"]: c for c in draft["constraints"]}
    # Defaults in normalized params are not evidence that the model supplied a
    # value. Recheck the original proposal and overlay only explicit edits.
    raw_proposals = draft.get("proposals")
    proposals = ({c["id"]: (raw if isinstance(raw, dict) else
                            {"type": "unsupported", "params": {"note": str(raw)}})
                  for c, raw in zip(draft["constraints"], raw_proposals)}
                 if isinstance(raw_proposals, list) and len(raw_proposals) == len(draft["constraints"]) else {})
    seen, kept, edits = set(), [], []
    for c in client:
        if not isinstance(c, dict) or c.get("id") not in stored:
            raise ReviewError(f"Unknown constraint {c.get('id') if isinstance(c, dict) else c!r}; "
                              f"only items from this extraction can be planned")
        cid = c["id"]
        if cid in seen:
            raise ReviewError(f"{cid} is listed twice")
        seen.add(cid)
        s = stored[cid]
        if c.get("type", s["type"]) != s["type"] or c.get("source_span", s["source_span"]) != s["source_span"]:
            raise ReviewError(f"{cid}: type and source text cannot be changed; reject it instead")
        params = c.get("params", s["params"])
        if not isinstance(params, dict):
            raise ReviewError(f"{cid}: params must be an object")
        edited = params != s["params"]
        changed_fields = {key for key in params.keys() | s["params"].keys()
                          if (key in params) != (key in s["params"])
                          or params.get(key) != s["params"].get(key)}
        if edited:
            edits.append({"id": cid, "before": deepcopy(s["params"]), "after": deepcopy(params)})
        proposal = proposals.get(cid, s)
        original_params = _params(proposal if isinstance(proposal, dict) else s)
        for key in changed_fields:
            if key in params:
                original_params[key] = deepcopy(params[key])
            else:
                original_params.pop(key, None)
        raw = {"type": proposal.get("type", s["type"]), "params": original_params,
               "source_span": s["source_span"]}
        kept.append((c, raw, "user" if edited else s["origin"], changed_fields))
    items = [_check_one(raw, draft["message"], F, edited_fields=fields) for _, raw, _, fields in kept]
    _cross_checks(items, F)
    out = []
    for (c, _, origin, _), item in zip(kept, items):
        checked = _finish(item, c["id"], origin)
        if checked["status"] == "review" and not checked["blocking_issues"] and c.get("status") == "accepted":
            checked["status"] = "accepted"
        out.append(checked)
    rejected = [deepcopy(s) | {"status": "rejected"} for cid, s in stored.items() if cid not in seen]
    return out, rejected, edits


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
