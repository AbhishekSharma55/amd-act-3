import { useEffect, useState } from "react";

// Evidence drawer: what the AMD model did, and the checks behind the chosen plan.
export default function RunInspector({ open, onClose, health, draft, solve, replay, runId, api, sampleMode }) {
  const [details, setDetails] = useState(null);
  useEffect(() => {
    if (!open || !runId || sampleMode) return setDetails(null);
    api(`/api/runs/${runId}`).then(setDetails).catch(() => setDetails(null));
  }, [open, runId, replay, solve, api, sampleMode]);
  if (!open) return null;
  const t = draft?.trace;
  const mode = sampleMode ? "recorded sample" : !t ? "—" : t.fallback_used ? "fallback (not AMD)" : t.mode === "live" ? "live AMD call" : t.mode || "live";
  return (
    <aside className="drawer" role="dialog" aria-label="Run inspector">
      <div className="drawer-head">
        <b>Run inspector</b>
        <button onClick={onClose} aria-label="Close inspector">✕</button>
      </div>
      <dl>
        <dt>Mode</dt><dd><span className={`pill ${sampleMode || t?.fallback_used ? "bad" : "good"}`}>{mode}</span></dd>
        <dt>Run</dt><dd className="mono">{runId || "—"}</dd>
      </dl>
      <h3>AMD Token Factory</h3>
      <dl>
        <dt>Configured</dt><dd>{health ? (health.amd.configured ? "yes" : "no — set AMD_API_BASE, AMD_API_KEY, AMD_MODEL") : "?"}</dd>
        <dt>Provider</dt><dd>{t?.provider || health?.amd.provider || "—"}</dd>
        <dt>Model</dt><dd className="mono">{t?.model || health?.amd.model || "—"}</dd>
        <dt>Host</dt><dd className="mono">{t?.host || health?.amd.host || "—"}</dd>
        <dt>Latency</dt><dd>{t ? `${t.latency_ms} ms` : "—"}</dd>
        <dt>Attempts</dt><dd>{t?.attempts ?? "—"}</dd>
        <dt>Tokens</dt><dd>{t?.usage ? `${t.usage.prompt_tokens ?? "?"} in · ${t.usage.completion_tokens ?? "?"} out` : "—"}</dd>
      </dl>
      {t?.raw_output && (
        <details><summary>Raw model output</summary><pre>{pretty(t.raw_output)}</pre></details>
      )}
      {draft && (
        <>
          <h3>Validation</h3>
          <ul className="small">
            {draft.constraints.map((c) => (
              <li key={c.id}><b>{c.id}</b> {c.type} · {c.status}{c.issues.length ? `: ${c.issues.join("; ")}` : ""}</li>
            ))}
          </ul>
        </>
      )}
      {solve && (
        <>
          <h3>Solver and checker</h3>
          <ul className="small">
            {solve.alternatives.map((a) => (
              <li key={a.id}><b>{a.label}</b>: {a.solver.status}, {a.solver.time_ms} ms · checker {a.checker.valid ? "valid" : `invalid (${a.checker.violations.length})`}</li>
            ))}
            {solve.infeasible.map((x) => <li key={x.id || x.label}><b>{x.label}</b>: {x.solver_status}</li>)}
          </ul>
        </>
      )}
      {replay && (
        <>
          <h3>Replay</h3>
          <dl>
            <dt>Device</dt><dd>{replay.device}</dd>
            <dt>Samples</dt><dd>{replay.samples}</dd>
            <dt>Time</dt><dd>{replay.elapsed_ms} ms</dd>
            <dt>Seed</dt><dd>{replay.assumptions.seed}</dd>
          </dl>
        </>
      )}
      {details?.log && (
        <>
          <h3>Step log</h3>
          <ol className="small">{details.log.map((s, i) => <li key={i}>{s.at.slice(11, 19)} · {s.step}</li>)}</ol>
        </>
      )}
      <p className="muted small">Synthetic demo data. The API key is never sent to the browser.</p>
    </aside>
  );
}

function pretty(raw) {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}
