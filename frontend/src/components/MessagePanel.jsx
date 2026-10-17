const SAMPLES = [
  { label: "Demo", text: "Mill M2 is unavailable until 14:00. Order J7 still needs to ship at 16:00. Overtime requires approval." },
  { label: "Unknown machine", text: "Mill 4 is down after lunch. J7 ships at 4." },
  { label: "No repair time", text: "Big mill just stopped, no idea when it will be fixed." },
  { label: "No overtime", text: "Lathe L3 is down until 12:30. No overtime today." },
  { label: "Hinglish", text: "M2 machine 2 baje tak band hai, J7 ko 4 baje tak ship karna hi hai." },
];
export const MAX_CHARS = 1000;

export default function MessagePanel({ message, onChange, onSubmit, busy, constraints, activeId }) {
  const tooLong = message.length > MAX_CHARS;
  return (
    <section className="panel" aria-labelledby="msg-h">
      <h2 id="msg-h"><span className="step">1</span> Disruption message</h2>
      <p className="hint">Type what happened on the floor, the way a planner would. An open model on AMD reads it.</p>
      <div className="samples">
        {SAMPLES.map((s) => (
          <button key={s.label} className="chip" disabled={busy} onClick={() => onChange(s.text)}>{s.label}</button>
        ))}
      </div>
      <textarea value={message} onChange={(e) => onChange(e.target.value)} rows={4} disabled={busy}
                placeholder="e.g. Mill M2 is unavailable until 14:00. Order J7 still needs to ship at 16:00."
                aria-label="Disruption message" />
      <div className="row-between">
        <span className={`count ${tooLong ? "bad" : ""}`}>{message.length}/{MAX_CHARS}</span>
        <button className="primary" disabled={busy || !message.trim() || tooLong} onClick={onSubmit}>
          {busy ? <><span className="spin" /> AMD model is reading…</> : "Read message"}
        </button>
      </div>
      {constraints?.length > 0 && <SourceHighlight message={message} constraints={constraints} activeId={activeId} />}
    </section>
  );
}

// Renders the message with each constraint's source span marked; the active one is stronger.
export function SourceHighlight({ message, constraints, activeId }) {
  const lower = message.toLowerCase();
  const marks = [];
  for (const c of constraints) {
    const span = (c.source_span || "").trim();
    if (!span) continue;
    const i = lower.indexOf(span.toLowerCase());
    if (i >= 0 && !marks.some((m) => i < m.end && i + span.length > m.start)) {
      marks.push({ start: i, end: i + span.length, id: c.id, status: c.decision === "rejected" ? "rejected" : c.status });
    }
  }
  marks.sort((a, b) => a.start - b.start);
  const parts = [];
  let pos = 0;
  for (const m of marks) {
    if (m.start > pos) parts.push(message.slice(pos, m.start));
    parts.push(<mark key={m.id} className={`${m.status} ${m.id === activeId ? "active" : ""}`}
                     title={`Source of ${m.id}`}>{message.slice(m.start, m.end)}<sup>{m.id}</sup></mark>);
    pos = m.end;
  }
  parts.push(message.slice(pos));
  return <p className="source">{parts}</p>;
}
