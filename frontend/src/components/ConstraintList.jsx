import { useState } from "react";
import { describe } from "../lib/workflow.js";

export default function ConstraintList({ factory, constraints, trace, activeId, onActivate, onDecide, onEdit, busy,
                                         canSolve, onSolve, solving, blockedReason, onBeginEdit }) {
  if (!constraints) {
    return (
      <section className="panel" aria-labelledby="c-h">
        <h2 id="c-h"><span className="step">2</span> Constraints</h2>
        <p className="empty">Constraints read from the message appear here, each linked to the words it came from.</p>
      </section>
    );
  }
  const fallback = trace?.fallback_used;
  return (
    <section className="panel" aria-labelledby="c-h">
      <h2 id="c-h"><span className="step">2</span> Constraints</h2>
      {fallback && (
        <p className="warn-box">Rule-based fallback, <b>not</b> the AMD model: {trace.fallback_reason || "AMD unavailable"}</p>
      )}
      {constraints.length === 0 && <p className="empty">The model found nothing Rehearsal can plan from this message.</p>}
      <ul className="clist">
        {constraints.map((c) => (
          <ConstraintItem key={c.id} c={c} factory={factory} active={c.id === activeId} busy={busy}
                          onActivate={() => onActivate(c.id)} onDecide={(d) => onDecide(c.id, d)}
                          onEdit={(params) => onEdit(c.id, params)} onBeginEdit={onBeginEdit} />
        ))}
      </ul>
      <div className="row-between">
        <span className="hint">{blockedReason}</span>
        <button className="primary" disabled={!canSolve || solving} onClick={onSolve}>
          {solving ? <><span className="spin" /> Solving…</> : "Find recovery plans"}
        </button>
      </div>
    </section>
  );
}

function ConstraintItem({ c, factory, active, busy, onActivate, onDecide, onEdit, onBeginEdit }) {
  const [editing, setEditing] = useState(false);
  const rejected = c.decision === "rejected";
  const accepted = c.decision === "accepted" || c.status === "accepted";
  const blocking = c.blocking_issues?.length > 0;
  const icon = rejected ? "✕" : c.status === "ok" ? "✓" : accepted ? "✓" : "⚠";
  const cls = rejected ? "rejected" : c.status === "ok" || accepted ? "ok" : "review";
  const editable = ["machine_down", "due_date", "priority", "overtime"].includes(c.type);
  return (
    <li className={`citem ${cls} ${active ? "active" : ""}`} onMouseEnter={onActivate} onFocus={onActivate}>
      <div className="citem-head">
        <span className={`badge-icon ${cls}`} aria-label={cls}>{icon}</span>
        <button className="linklike" onClick={onActivate} title="Highlight the source text">
          <span className="cid">{c.id}</span> {describe(c, factory)}
        </button>
        <span className={`origin ${c.origin}`}>{c.origin === "amd_model" ? "AMD model" : c.origin === "user" ? "edited" : "fallback"}</span>
      </div>
      <div className="quote">“{c.source_span}”</div>
      {c.issues?.length > 0 && (
        <ul className="issues">{c.issues.map((i) => <li key={i}>{i}</li>)}</ul>
      )}
      {blocking && !rejected && (
        <ul className="issues blocking">{c.blocking_issues.map((i) => <li key={i}>Required: {i}</li>)}</ul>
      )}
      {c.status === "review" && !rejected && (
        <div className="actions">
          <button disabled={busy || blocking || accepted} onClick={() => onDecide("accepted")}
                  title={blocking ? "Correct the required fields first" : "Confirm this interpretation"}>
            {accepted ? "Accepted" : "Accept"}
          </button>
          {editable && <button disabled={busy} onClick={() => { if (!editing) onBeginEdit?.(); setEditing((v) => !v); }}>{editing ? "Cancel edit" : "Edit / map"}</button>}
          <button disabled={busy} onClick={() => onDecide("rejected")}>Reject</button>
        </div>
      )}
      {c.status === "ok" && !rejected && (
        <div className="actions subtle"><button disabled={busy} onClick={() => onDecide("rejected")}>Reject</button></div>
      )}
      {rejected && (
        <div className="actions subtle"><button disabled={busy} onClick={() => onDecide(null)}>Undo reject</button></div>
      )}
      {editing && !rejected && (
        <EditForm c={c} factory={factory} busy={busy} onSave={(p) => { onEdit(p); setEditing(false); }} />
      )}
    </li>
  );
}

function EditForm({ c, factory, busy, onSave }) {
  const [p, setP] = useState({ ...c.params });
  const set = (k, v) => setP((old) => ({ ...old, [k]: v === "" ? null : v }));
  const time = (k, label) => (
    <label>{label}<input type="time" value={p[k] || ""} min={factory.shift.start} max={factory.shift.overtime_until}
                         onChange={(e) => set(k, e.target.value)} /></label>
  );
  return (
    <form className="edit" noValidate onSubmit={(e) => { e.preventDefault(); onSave(p); }}>
      {c.type === "machine_down" && <>
        <label>Machine
          <select value={factory.machines.some((m) => m.id === p.machine) ? p.machine : ""} onChange={(e) => set("machine", e.target.value)}>
            <option value="">Choose…</option>
            {factory.machines.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
        </label>
        {time("from", "From")}{time("until", "Repair end")}
      </>}
      {(c.type === "due_date" || c.type === "priority") && (
        <label>Job
          <select value={factory.jobs.some((j) => j.id === p.job) ? p.job : ""} onChange={(e) => set("job", e.target.value)}>
            <option value="">Choose…</option>
            {factory.jobs.map((j) => <option key={j.id} value={j.id}>{j.id} · {j.customer}</option>)}
          </select>
        </label>
      )}
      {c.type === "due_date" && <>
        {time("time", "Due")}
        <label className="check"><input type="checkbox" checked={!!p.hard} onChange={(e) => setP({ ...p, hard: e.target.checked })} /> Hard date</label>
      </>}
      {c.type === "priority" && (
        <label>Level
          <select value={p.level ?? ""} onChange={(e) => setP({ ...p, level: Number(e.target.value) })}>
            <option value="1">1 normal</option><option value="2">2 high</option><option value="3">3 critical</option>
          </select>
        </label>
      )}
      {c.type === "overtime" && <>
        <label className="check"><input type="checkbox" checked={!!p.allowed} onChange={(e) => setP({ ...p, allowed: e.target.checked })} /> Allowed</label>
        {p.allowed && time("until", "Until")}
      </>}
      <button type="submit" className="primary small" disabled={busy}>Revalidate</button>
    </form>
  );
}
