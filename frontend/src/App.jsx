import { useCallback, useEffect, useMemo, useReducer, useState } from "react";
import Timeline from "./components/Timeline.jsx";
import CheckerResult from "./components/CheckerResult.jsx";
import MessagePanel from "./components/MessagePanel.jsx";
import ConstraintList from "./components/ConstraintList.jsx";
import Alternatives from "./components/Alternatives.jsx";
import ReplayPanel from "./components/ReplayPanel.jsx";
import ApprovalPanel from "./components/ApprovalPanel.jsx";
import RunInspector from "./components/RunInspector.jsx";
import { ApiError, createApi } from "./lib/api.js";
import {
  annotateChanges,
  clock,
  describeChange,
  jobOutcomes,
  minutes,
  operationKey,
} from "./lib/timeline.js";
import { effectiveJobs, isReady, isUsable, outagesFrom, solvePayload } from "./lib/workflow.js";
import sampleReview from "../../shared/mocks/extract_review.json";
import checkerReports from "../../shared/checker-reports.json";
import "./workflow.css";

const VIEWS = [
  { id: "committed", title: "Committed schedule", subtitle: "The plan on the floor", number: "01" },
  { id: "recovery", title: "Recovery plan", subtitle: "The selected alternative", number: "02" },
  { id: "failure", title: "Failing future", subtitle: "A sampled way it breaks", number: "03" },
];

// Development defaults to recorded samples (frontend/README.md); the built app served by FastAPI is live.
const DEFAULT_SOURCE = import.meta.env.VITE_USE_MOCKS === "1" ? "sample"
  : import.meta.env.VITE_USE_MOCKS === "0" || import.meta.env.PROD ? "live" : "sample";

const DOWNSTREAM = { solve: null, selectedAltId: null, replay: null, view: "committed" };
const RESET = { message: "", draft: null, constraints: null, activeId: null, ...DOWNSTREAM, busy: null, error: null };

function reducer(s, a) {
  switch (a.type) {
    case "reset": return { ...s, ...RESET };
    case "message": return a.message === s.message ? s : { ...s, message: a.message, draft: null, constraints: null, activeId: null, ...DOWNSTREAM };
    case "busy": return { ...s, busy: a.busy, error: null };
    case "error": return { ...s, busy: null, error: a.error };
    case "dismiss": return { ...s, error: null };
    case "extracted": return { ...s, busy: null, message: a.draft.message, draft: a.draft,
                               constraints: a.draft.constraints.map((c) => ({ ...c, decision: null })), ...DOWNSTREAM };
    case "decide": return { ...s, ...DOWNSTREAM, constraints: s.constraints.map((c) => (c.id === a.id ? { ...c, decision: a.decision } : c)) };
    case "revalidated": {
      const byId = Object.fromEntries(a.constraints.map((c) => [c.id, c]));
      return { ...s, busy: null, ...DOWNSTREAM, constraints: s.constraints.map((c) => (byId[c.id]
        ? { ...byId[c.id], decision: byId[c.id].status === "accepted" ? "accepted" : null } : c)) };
    }
    case "active": return { ...s, activeId: a.id };
    case "solved": return { ...s, busy: null, ...DOWNSTREAM, solve: a.solve,
                            selectedAltId: a.solve.alternatives[0]?.id || null,
                            view: a.solve.alternatives.length ? "recovery" : "committed" };
    case "select": return { ...s, selectedAltId: a.id, replay: null, view: "recovery" };
    case "replayed": return { ...s, busy: null, replay: a.replay };
    case "view": return { ...s, view: a.view };
    default: return s;
  }
}

function ArrowIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M4 10h12m-5-5 5 5-5 5" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

export default function App() {
  const [source, setSource] = useState(DEFAULT_SOURCE);
  const [factory, setFactory] = useState(null);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [attempt, setAttempt] = useState(0);
  const [selected, setSelected] = useState(null);
  const [highlight, setHighlight] = useState(null);
  const [inspector, setInspector] = useState(false);
  const [delay, setDelay] = useState(90);
  const [s, d] = useReducer(reducer, RESET);
  const sampleMode = source === "sample";
  const api = useMemo(() => createApi({ useMocks: sampleMode, baseUrl: import.meta.env.VITE_API_BASE_URL || "" }), [sampleMode]);

  useEffect(() => {
    const controller = new AbortController();
    let current = true;
    setLoading(true);
    setLoadError(null);
    setFactory(null);
    setSelected(null);
    setHighlight(null);
    d({ type: "reset" });
    api("/api/factory", undefined, { signal: controller.signal })
      .then((data) => {
        if (!Array.isArray(data?.machines) || !Array.isArray(data?.jobs) || !Array.isArray(data?.committed_schedule) || !data.shift)
          throw new Error("The factory response is missing schedule data. Check the API fixture.");
        if (current) setFactory(data);
      })
      .catch((failure) => {
        if (current && failure.name !== "AbortError") setLoadError(failure.message);
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    if (!sampleMode) api("/api/health").then((h) => current && setHealth(h)).catch(() => current && setHealth(null));
    else setHealth(null);
    return () => {
      current = false;
      controller.abort();
    };
  }, [api, sampleMode, attempt]);

  // Every workflow call goes through one place: busy state, one error banner, retry when it makes sense.
  const run = useCallback((busy, fn) => async () => {
    d({ type: "busy", busy });
    try {
      await fn();
    } catch (e) {
      const expired = e.code === "run_expired" || e.code === "run_not_found";
      d({ type: "error", error: { message: expired ? `${e.message}` : e.message,
                                  retry: !expired && e.retryable ? run(busy, fn) : null } });
    }
  }, []);

  const extract = run("extract", async () => {
    let draft;
    if (sampleMode) {
      draft = /mill\s*4/i.test(s.message) ? structuredClone(sampleReview) : await api("/api/extract", { message: s.message });
    } else {
      draft = await api("/api/extract", { message: s.message });
    }
    d({ type: "extracted", draft });
  });
  const edit = (id, params) => run("revalidate", async () => {
    if (sampleMode) throw new ApiError("Editing is checked by the server. Switch the data source to Live to revalidate edits.");
    const constraints = solvePayload(s.constraints).map((c) => (c.id === id ? { ...c, params } : c));
    const r = await api("/api/constraints/revalidate", { run_id: s.draft.run_id, constraints });
    d({ type: "revalidated", constraints: r.constraints });
  })();
  const solve = run("solve", async () => {
    const r = await api("/api/solve", { run_id: s.draft.run_id, constraints: solvePayload(s.constraints),
                                        allow: { reroute: true, overtime: true, relax_hard_due: false }, time_limit_s: 10 });
    d({ type: "solved", solve: r });
  });
  const replay = run("replay", async () => {
    const r = await api("/api/replay", { run_id: s.solve.run_id, alternative_id: s.selectedAltId,
      assumptions: { samples: 500, seed: 7, duration_spread: [0.9, 1.3], repair_delay_max_min: delay } });
    d({ type: "replayed", replay: r });
  });

  const alt = s.solve?.alternatives.find((a) => a.id === s.selectedAltId) || null;
  const failing = s.replay?.failing_scenario || null;
  const view = (s.view === "recovery" && !alt) || (s.view === "failure" && !failing) ? "committed" : s.view;
  const pending = s.constraints?.filter(isUsable).filter((c) => !isReady(c)) || [];
  const canSolve = !!s.draft && pending.length === 0 && !s.busy;
  const blockedReason = !s.constraints ? "" : pending.length
    ? `Decide ${pending.map((c) => c.id).join(", ")} first (accept, edit or reject).` : "";

  const jobs = useMemo(() => (factory ? effectiveJobs(factory.jobs, s.constraints) : []), [factory, s.constraints]);
  const schedule = useMemo(() => {
    if (!factory) return [];
    const raw = view === "recovery" ? alt.schedule : view === "failure" ? failing.timeline : factory.committed_schedule;
    return annotateChanges(raw, factory.committed_schedule, factory.now);
  }, [view, factory, alt, failing]);
  const outages = outagesFrom(s.constraints, factory?.now);
  const outcomes = factory ? jobOutcomes(view === "committed" ? factory.jobs : jobs, schedule) : [];
  const lateJobs = outcomes.filter((job) => job.late > 0);
  const changedCount = schedule.filter((o) => o.change && !["none", "frozen"].includes(o.change)).length;
  const activeOperation = schedule.find((o) => operationKey(o) === selected) || null;
  const activeJob = outcomes.find((job) => job.id === activeOperation?.job);
  const activeMachine = factory?.machines.find((m) => m.id === activeOperation?.machine);
  const lastFinish = schedule.length ? Math.max(...schedule.map((o) => minutes(o.end))) : null;
  const currentView = VIEWS.find((item) => item.id === view);
  const failingJob = failing?.job || failing?.reason?.split(" ")[0];  // recorded samples predate the job field
  const timelineHighlight = highlight || (view === "failure" && failing ? { job: failingJob, op: failing.bottleneck?.op } : null);

  function changeView(next) {
    d({ type: "view", view: next });
    setSelected(null);
    setHighlight(null);
  }
  const viewEnabled = { committed: true, recovery: !!alt, failure: !!failing };

  return (
    <>
      <a className="skip-link" href="#workspace">Skip to schedule</a>
      <header className="app-header">
        <a className="brand" href="./" aria-label="Rehearsal home">
          <span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>
          Rehearsal<span className="brand-period">.</span>
        </a>
        <span className="header-divider" />
        <span className="header-context">Production workspace</span>
        <div className="team-signature">
          <button className="wf-header-button" onClick={() => setInspector(!inspector)} aria-expanded={inspector}>
            Run inspector
          </button>
          FORGE AHEAD <span> / </span> ACT III
        </div>
      </header>

      <main id="workspace">
        <div className="page-heading">
          <div>
            <div className="eyebrow">TEST THE RECOVERY BEFORE THE SHIFT CHANGES</div>
            <h1>See the shift. Know the tradeoffs.</h1>
            <p>Describe a disruption. An open model on AMD reads it, a solver proposes checked recovery plans,
              and a rehearsal shows how each plan can fail before you approve it.</p>
          </div>
          <label className="source-control">
            <span>DATA SOURCE</span>
            <select value={source} onChange={(event) => setSource(event.target.value)}>
              <option value="sample">Recorded samples</option>
              <option value="live">Live API</option>
            </select>
          </label>
        </div>

        <div className="provenance">
          <span className="status-dot" />
          <strong>Synthetic demo data</strong>
          <span className="provenance-divider">/</span>
          <span>
            {sampleMode ? "Recorded sample responses · no live AMD, solver or replay calls"
              : health?.amd.configured ? `Live · AMD Token Factory model ${health.amd.model}`
              : health?.fallback_enabled ? "Live · AMD not configured, messages use the labeled rule fallback"
              : "Live · AMD not configured on this server"}
          </span>
        </div>

        {loadError && (
          <div className="error-banner" role="alert">
            <div><strong>Factory data couldn’t be loaded.</strong><p>{loadError}</p></div>
            <button onClick={() => setAttempt((value) => value + 1)}>Retry <ArrowIcon /></button>
          </div>
        )}
        {s.error && (
          <div className="error-banner" role="alert">
            <div><strong>That step didn’t complete.</strong><p>{s.error.message}</p></div>
            <div className="wf-actions">
              {s.error.retry && <button onClick={s.error.retry}>Retry <ArrowIcon /></button>}
              <button onClick={() => d({ type: "dismiss" })}>Dismiss</button>
            </div>
          </div>
        )}
        {loading && (
          <div className="loading-panel" role="status"><span className="loading-dot" />Loading the factory schedule…</div>
        )}

        {!loading && !loadError && factory && (
          <>
            <section className="schedule-section" aria-labelledby="schedule-heading">
              <div className="schedule-topline">
                <div>
                  <span className="factory-icon" aria-hidden="true">⌑</span>
                  <h2 id="schedule-heading">{factory.factory.replace(/\s*\(synthetic data\)/i, "")}</h2>
                </div>
                <span className="factory-date">
                  {new Date(`${factory.date}T12:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}
                  <span>·</span>now {factory.now} local factory time
                </span>
              </div>
              <div className="view-controls" role="group" aria-label="Schedule view">
                {VIEWS.map((item) => (
                  <button key={item.id} aria-pressed={view === item.id} className={view === item.id ? "active" : ""}
                          disabled={!viewEnabled[item.id]} onClick={() => changeView(item.id)}>
                    <span className="view-number">{item.number}</span>
                    <span>
                      <strong>{item.title}</strong>
                      <small>{viewEnabled[item.id] ? item.subtitle : item.id === "recovery" ? "Available after step 3" : "Available after step 4"}</small>
                    </span>
                    {view === item.id && <span className="view-indicator" aria-hidden="true">↗</span>}
                  </button>
                ))}
              </div>

              <div className={`view-note ${view === "failure" ? "failure-note" : ""}`}>
                <span className="note-symbol" aria-hidden="true">{view === "committed" ? "↳" : view === "recovery" ? "↗" : "!"}</span>
                {view === "committed" ? (
                  <p><strong>The committed plan.</strong> {factory.jobs.length} orders across {factory.machines.length} machines.
                    {outages.length ? " Hatching shows the reported outages it now runs into." : " Select an operation to inspect its timing and delivery promise."}</p>
                ) : view === "recovery" ? (
                  <p><strong>{alt.label}.</strong>{" "}
                    {alt.kpis.late_jobs.length ? alt.kpis.late_jobs.map((l) => `${l.job} finishes ${l.minutes_late} min late`).join(", ") : "Every order on time"}
                    {` · ${alt.kpis.moved_ops} moved, ${alt.kpis.retimed_ops} retimed`}{sampleMode ? " · recorded sample" : ""}.</p>
                ) : (
                  <p><strong>Sampled future #{failing.index}.</strong> {failing.reason}. {failing.bottleneck?.detail}.
                    Hatching shows the nominal outage; the sampled repair time may be later.</p>
                )}
              </div>

              <Timeline machines={factory.machines} jobs={factory.jobs} schedule={schedule} now={factory.now} shift={factory.shift}
                        outages={outages} dueMarkers={(view === "committed" ? factory.jobs : jobs).map((job) => ({ job: job.id, time: job.due }))}
                        selectedKey={selected} highlight={timelineHighlight || []}
                        onInspect={(operation) => setSelected(operationKey(operation))} label={currentView.title} />

              <div className="timeline-legend">
                <span><i className="legend-block" />Operation</span>
                <span><i className="legend-block frozen" />Started before now</span>
                <span><i className="legend-block changed" />{view === "failure" ? "Varies from committed plan" : "Changed operation"}</span>
                <span><i className="legend-outage" />{view === "failure" ? "Nominal outage" : "Machine outage"}</span>
                <span><i className="legend-flag">⚑</i>Order due time</span>
                <span className="keyboard-hint">Hover or Tab to inspect</span>
              </div>

              <div className={`operation-detail ${activeOperation ? "has-selection" : ""}`} aria-live="polite" aria-atomic="true">
                {activeOperation ? (
                  <>
                    <div className="detail-title">
                      <span className="job-swatch" style={{ background: activeJob?.color }} />{" "}
                      <strong>{activeOperation.job} · Operation {activeOperation.op}</strong>
                      <span>{activeJob?.customer}</span>
                    </div>
                    <div className="detail-field"><span>RESOURCE</span><strong>{activeMachine?.name}</strong></div>
                    <div className="detail-field">
                      <span>{view === "failure" ? "SAMPLED TIME" : "PLANNED TIME"}</span>
                      <strong>{activeOperation.start}–{activeOperation.end}</strong>
                    </div>
                    <div className="detail-field"><span>ORDER DUE</span><strong>{activeJob?.due}</strong></div>
                    <div className="detail-change">
                      {view === "failure" && activeOperation.change === "retimed" ? "Simulated timing variation" : describeChange(activeOperation.change)}
                    </div>
                  </>
                ) : (
                  <>
                    <span className="inspect-icon" aria-hidden="true">↖</span>
                    <p><strong>Every block has a story.</strong> Hover, focus, or select an operation to see the customer, timing, and changes.</p>
                  </>
                )}
              </div>
            </section>

            {sampleMode && (
              <p className="wf-sample-note">Recorded samples: every step below returns the same saved demo responses, whatever you type.
                Switch the data source to <b>Live API</b> for real AMD extraction, solving and rehearsal.</p>
            )}

            <div className="wf">
              <div className="wf-grid2">
                <MessagePanel message={s.message} onChange={(m) => d({ type: "message", message: m })} onSubmit={extract}
                              busy={s.busy === "extract"} constraints={s.constraints} activeId={s.activeId} />
                <ConstraintList factory={factory} constraints={s.constraints} trace={s.draft?.trace} activeId={s.activeId}
                                onActivate={(id) => d({ type: "active", id })} onDecide={(id, decision) => d({ type: "decide", id, decision })}
                                onEdit={edit} busy={!!s.busy} canSolve={canSolve} onSolve={solve}
                                solving={s.busy === "solve"} blockedReason={blockedReason} />
              </div>
              <Alternatives solve={s.solve} selectedId={s.selectedAltId} onSelect={(id) => d({ type: "select", id })}
                            onConstraintClick={(id) => d({ type: "active", id })} />
            </div>

            <section className="checker-section" aria-label="Independent schedule verification" aria-live="polite">
              <div className="checker-section-title">
                <div className="eyebrow">BEFORE YOU COMMIT</div>
                <h2>Check the plan against the rules.</h2>
              </div>
              {view === "recovery" ? (
                <CheckerResult result={alt.checker} title={alt.label}
                               description={`${sampleMode ? "Saved" : "Server-side"} independent check against the reviewed constraints. ${
                                 alt.concessions?.length ? "Concessions still need approval below." : "No concessions needed."}`} />
              ) : view === "failure" ? (
                <CheckerResult result={null} title="Sampled future"
                               description="This is a simulated outcome with varying durations, not a dispatch plan. The independent check applies to the recovery plan." />
              ) : (
                <CheckerResult result={sampleMode ? checkerReports.reports.committed : null} title="Committed schedule"
                               description={sampleMode ? "Saved independent check of the sample fixture, before any disruption."
                                 : "Every recovery plan is checked on the server when it is solved, and again before approval."} />
              )}
              <p className="checker-scope">Checks cover operation coverage, eligibility, duration, order, machine conflicts, outages,
                started work, working hours and hard due times. They do not prove that a disruption message was understood correctly;
                that is why every constraint links to its source words and doubtful ones need a person.</p>
            </section>

            <div className="wf">
              <ReplayPanel alt={alt} replay={s.replay} busy={s.busy === "replay"} onRun={replay} delay={delay} setDelay={setDelay}
                           showFailure={view === "failure"} setShowFailure={(on) => changeView(on ? "failure" : "recovery")} />
              {alt && (
                <ApprovalPanel runId={s.solve.run_id} alternative={alt} sample={sampleMode}
                               onInvalidRun={() => d({ type: "error", error: { message: "That plan can no longer be approved. Find recovery plans again to get a fresh run." } })} />
              )}
            </div>

            <section className="orders-section" aria-labelledby="orders-heading">
              <div className="orders-header">
                <div>
                  <div className="eyebrow">DELIVERY PROMISES</div>
                  <h2 id="orders-heading">Orders in this schedule <span>{outcomes.length}</span></h2>
                </div>
                <div className="summary">
                  <span><strong>{outcomes.filter((job) => job.late === 0).length}</strong> on time</span>
                  <span className={lateJobs.length ? "late-summary" : ""}><strong>{lateJobs.length}</strong> late</span>
                  <span><strong>{view === "committed" ? "—" : changedCount}</strong> changed ops</span>
                  <span>Last finish <strong>{lastFinish === null ? "—" : clock(lastFinish)}</strong></span>
                </div>
              </div>
              <div className="orders-table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>ORDER / CUSTOMER</th><th>PRIORITY</th><th>DUE</th>
                      <th>{view === "failure" ? "SAMPLED FINISH" : "PLANNED FINISH"}</th><th>DELIVERY STATUS</th>
                      <th><span className="sr-only">Highlight order</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    {outcomes.map((job) => (
                      <tr key={job.id} className={highlight?.job === job.id ? "highlighted-row" : ""}>
                        <td>
                          <div className="order-name">
                            <span className="job-swatch" style={{ background: job.color }} />
                            <strong>{job.id}</strong><span>{job.customer}</span>
                          </div>
                        </td>
                        <td><span className={`priority priority-${job.priority}`}>{job.priority === 3 ? "Critical" : job.priority === 2 ? "High" : "Normal"}</span></td>
                        <td className="tabular">{job.due}</td>
                        <td className="tabular">{job.finish === null ? "Unscheduled" : clock(job.finish)}</td>
                        <td>
                          {job.late === null ? <span>Not scheduled</span>
                            : job.late > 0 ? <span className="delivery-late">{job.late} min late</span>
                            : <span className="delivery-on-time"><span />On time</span>}
                        </td>
                        <td>
                          <button className="highlight-button"
                                  aria-label={`${highlight?.job === job.id ? "Clear highlight for" : "Highlight"} ${job.id} on timeline`}
                                  aria-pressed={highlight?.job === job.id}
                                  onClick={() => setHighlight(highlight?.job === job.id ? null : { job: job.id })}>
                            {highlight?.job === job.id ? "Clear" : "Locate"}<ArrowIcon />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <footer className="workspace-footer">
              <span>REHEARSAL <span> / </span> Understand the plan before you commit.</span>
              <p>Message reading: open model on AMD Token Factory · recovery plans: OR-Tools CP-SAT on CPU ·
                independent checker on every plan · rehearsal uses synthetic uncertainty, not calibrated to a real factory.</p>
            </footer>
          </>
        )}
      </main>

      <RunInspector open={inspector} onClose={() => setInspector(false)} health={health} draft={s.draft} solve={s.solve}
                    replay={s.replay} runId={s.solve?.run_id || s.draft?.run_id} api={api} sampleMode={sampleMode} />
    </>
  );
}
