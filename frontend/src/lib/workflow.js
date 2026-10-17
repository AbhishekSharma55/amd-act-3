// Helpers for the message → constraints → plans → rehearsal → approval workflow.

/** Plain-English one-liner for a constraint. */
export function describe(c, factory) {
  const p = c.params || {};
  const mname = (id) => factory?.machines.find((m) => m.id === id)?.name || id;
  switch (c.type) {
    case "machine_down":
      return `${mname(p.machine) || "?"} down ${p.from || "now"} – ${p.until || "end unknown"}`;
    case "due_date":
      return `${p.job || "?"} due ${p.time || "?"}${p.hard ? " (hard: must not slip)" : " (soft)"}`;
    case "priority":
      return `${p.job || "?"} priority ${p.level ?? "?"}${p.level === 3 ? " (critical)" : ""}`;
    case "overtime":
      return p.allowed ? `Overtime allowed until ${p.until || "shift limit"} (needs approval)` : "No overtime";
    default:
      return `Cannot be modelled: ${p.note || c.source_span}`;
  }
}

export const isUsable = (c) => c.decision !== "rejected";
export const isReady = (c) =>
  !c.blocking_issues?.length && (c.status === "ok" || c.status === "accepted" || c.decision === "accepted");

/** Constraints the planner kept, in the shape /api/solve expects. */
export function solvePayload(constraints) {
  return constraints.filter(isUsable).map(({ decision, ...c }) => ({
    ...c, status: decision === "accepted" ? "accepted" : c.status,
  }));
}

/** Outages from reviewed constraints, as Timeline `outages` ({machine, from, until}). */
export function outagesFrom(constraints, now) {
  return (constraints || [])
    .filter((c) => c.type === "machine_down" && isUsable(c) && isReady(c) && c.params?.until)
    .map((c) => ({ machine: c.params.machine, from: c.params.from || now, until: c.params.until }));
}

/** Fixture jobs with due dates replaced by reviewed due_date constraints. */
export function effectiveJobs(jobs, constraints) {
  const due = Object.fromEntries((constraints || [])
    .filter((c) => c.type === "due_date" && isUsable(c) && isReady(c)).map((c) => [c.params.job, c.params.time]));
  return jobs.map((j) => (due[j.id] ? { ...j, due: due[j.id] } : j));
}

export function download(name, text, type = "text/csv") {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
