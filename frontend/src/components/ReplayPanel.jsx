export default function ReplayPanel({ alt, replay, busy, onRun, delay, setDelay, showFailure, setShowFailure }) {
  if (!alt) return null;
  return (
    <section className="panel wide" aria-labelledby="rp-h">
      <h2 id="rp-h"><span className="step">4</span> Rehearse “{alt.label}”</h2>
      <p className="hint">Run the plan through many sampled futures: operations take a little longer or shorter, repairs finish late.
        The dispatch order stays fixed, as on the shop floor.</p>
      <div className="row-between wrap">
        <label className="slider">Repair may overrun by up to <b>{delay} min</b>
          <input type="range" min="0" max="180" step="15" value={delay} disabled={busy}
                 onChange={(e) => setDelay(Number(e.target.value))} />
        </label>
        <button className="primary" disabled={busy} onClick={onRun}>
          {busy ? <><span className="spin" /> Rehearsing…</> : replay ? "Rehearse again" : "Rehearse plan"}
        </button>
      </div>
      {replay && <ReplayResult replay={replay} showFailure={showFailure} setShowFailure={setShowFailure} />}
    </section>
  );
}

function ReplayResult({ replay, showFailure, setShowFailure }) {
  const f = replay.failing_scenario;
  const a = replay.assumptions;
  return (
    <>
      <div className="bars">
        {replay.jobs.map((j) => {
          const pct = (100 * j.on_time) / j.of;
          return (
            <div key={j.job} className={`bar-row ${f?.job === j.job ? "focus" : ""}`}>
              <span className="bar-label">{j.job}</span>
              <div className="bar" role="img" aria-label={`${j.job} on time in ${j.on_time} of ${j.of}`}>
                <div className={`fill ${pct === 100 ? "good" : pct >= 50 ? "mid" : "bad"}`} style={{ width: `${pct}%` }} />
              </div>
              <span className="bar-text">
                on time in <b>{j.on_time} of {j.of}</b>
                <span className="muted"> · 90% finish by {j.p90_finish}{j.late_in_plan ? " · late in plan (concession)" : ""}</span>
              </span>
            </div>
          );
        })}
      </div>
      <div className="failure">
        {f ? (
          <>
            <button className={showFailure ? "danger" : "primary"} onClick={() => setShowFailure(!showFailure)}>
              {showFailure ? "Hide failure" : "Show a failure"}
            </button>
            <span><b>{f.reason}</b> in sampled future #{f.index}. {f.bottleneck?.detail}.</span>
          </>
        ) : (
          <span className="good-text">No failure found in {replay.samples} scenarios for orders that are on time in the plan.</span>
        )}
      </div>
      <p className="assumptions">
        {replay.samples} simulated scenarios under these assumptions (synthetic, not calibrated to a real factory):
        durations × triangular({a.duration_spread[0]}, 1.0, {a.duration_spread[1]}); open repairs end 0–{a.repair_delay_max_min} min late;
        seed {a.seed}; fixed machine order and planned start floors; {replay.device}, {replay.elapsed_ms} ms.
      </p>
    </>
  );
}
