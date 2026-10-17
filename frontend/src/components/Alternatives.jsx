const POLICY = (p) => `${p.reroute ? "re-route allowed" : "same machines"} · ${p.overtime ? "overtime allowed" : "no overtime"}`;
const MERGED = { alt_keep: "Keep machines", alt_reroute: "Re-route", alt_reroute_overtime: "Re-route + overtime" };

export default function Alternatives({ solve, selectedId, onSelect, onConstraintClick }) {
  if (!solve) return null;
  return (
    <section className="panel wide" aria-labelledby="alt-h">
      <h2 id="alt-h"><span className="step">3</span> Recovery alternatives</h2>
      {solve.status === "no_feasible_plan" && (
        <p className="warn-box">No alternative meets these constraints. Read why below, then edit or reject a constraint and solve again.</p>
      )}
      <div className="cards">
        {solve.infeasible.map((x) => <InfeasibleCard key={x.id || x.label} x={x} onConstraintClick={onConstraintClick} />)}
        {solve.alternatives.map((a) => (
          <AltCard key={a.id} a={a} selected={a.id === selectedId} onSelect={() => onSelect(a.id)} />
        ))}
      </div>
    </section>
  );
}

function AltCard({ a, selected, onSelect }) {
  const k = a.kpis;
  return (
    <button className={`card ${selected ? "selected" : ""}`} onClick={onSelect} aria-pressed={selected}>
      <div className="card-head">
        <b>{a.label}</b>
        <span className={`pill ${a.checker.valid ? "good" : "bad"}`}>{a.checker.valid ? "Checker ✓" : "Checker ✕"}</span>
      </div>
      <div className="muted small">{POLICY(a.policy)} · {a.solver.status === "OPTIMAL" ? "optimal" : "best found in budget"}
        {a.solver.time_ms ? ` · ${a.solver.time_ms} ms` : ""}</div>
      <ul className="kpis">
        <li className={k.late_jobs.length ? "bad" : "good"}>
          {k.late_jobs.length ? k.late_jobs.map((l) => `${l.job} late ${l.minutes_late} min (${l.customer})`).join(", ") : "Every order on time"}
        </li>
        <li>{k.overtime_minutes ? `${k.overtime_minutes} overtime min · cost ${k.overtime_cost}` : "No overtime"}</li>
        <li>{k.moved_ops} moved · {k.retimed_ops} retimed operations</li>
      </ul>
      {a.concessions?.length > 0 && <div className="small">Needs approval: {a.concessions.map((c) => c.detail).join("; ")}</div>}
      {a.merged_with?.length > 0 && (
        <div className="muted small">Same plan as: {a.merged_with.map((m) => MERGED[m] || m).join(", ")} (merged)</div>
      )}
      {!a.checker.valid && <ul className="issues blocking">{a.checker.violations.map((v) => <li key={v}>{v}</li>)}</ul>}
    </button>
  );
}

function InfeasibleCard({ x, onConstraintClick }) {
  const unknown = x.solver_status === "UNKNOWN";
  return (
    <div className={`card ${unknown ? "unknown" : "infeasible"}`}>
      <div className="card-head">
        <b>{x.label}</b>
        <span className="pill bad">{unknown ? "No plan found in budget" : "No plan can meet these"}</span>
      </div>
      <div className="muted small">{POLICY(x.policy)}</div>
      <p>{x.explanation}</p>
      {x.conflict?.length > 0 && (
        <div className="small">
          These constraints together cannot be met ({x.conflict_kind} set, not necessarily minimal):{" "}
          {x.conflict.map((cid) => <button key={cid} className="cid-link" onClick={() => onConstraintClick(cid)}>{cid}</button>)}
        </div>
      )}
      {x.possible_concessions?.length > 0 && (
        <ul className="small concessions">
          {x.possible_concessions.map((p, i) => (
            <li key={i} className={p.available === false ? "muted" : ""}>
              {p.type === "allow_reroute" ? "Allowing re-routing produces a plan (see the other card)"
                : p.type === "allow_overtime" ? "Allowing overtime produces a plan"
                : `Relaxing ${p.constraint}'s hard date: ${p.note || "available"}`}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
