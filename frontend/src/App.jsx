import { useEffect, useMemo, useState } from "react";
import Timeline from "./components/Timeline.jsx";
import CheckerResult from "./components/CheckerResult.jsx";
import ApprovalPanel from "./components/ApprovalPanel.jsx";
import { createApi } from "./lib/api.js";
import {
  annotateChanges,
  clock,
  describeChange,
  jobOutcomes,
  minutes,
  operationKey,
} from "./lib/timeline.js";
import sampleFactory from "../../shared/mocks/factory.json";
import sampleSolve from "../../shared/mocks/solve.json";
import sampleReplay from "../../shared/mocks/replay.json";
import sampleExtract from "../../shared/mocks/extract.json";
import checkerReports from "../../shared/checker-reports.json";

const VIEWS = [
  {
    id: "committed",
    title: "Committed schedule",
    subtitle: "The plan on the floor",
    number: "01",
  },
  {
    id: "recovery",
    title: "Sample recovery",
    subtitle: "An alternative after disruption",
    number: "02",
  },
  {
    id: "failure",
    title: "Sample failure",
    subtitle: "A recorded simulation outcome",
    number: "03",
  },
];

function ArrowIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M4 10h12m-5-5 5 5-5 5" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

export default function App() {
  const [source, setSource] = useState(
    import.meta.env.VITE_USE_MOCKS === "0" ? "live" : "sample",
  );
  const [factory, setFactory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [attempt, setAttempt] = useState(0);
  const [view, setView] = useState("committed");
  const [selected, setSelected] = useState(null);
  const [highlight, setHighlight] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    let current = true;
    setLoading(true);
    setError(null);
    setFactory(null);
    setSelected(null);
    setView("committed");
    setHighlight(null);
    const api = createApi({
      useMocks: source === "sample",
      baseUrl: import.meta.env.VITE_API_BASE_URL || "",
    });
    api("/api/factory", undefined, { signal: controller.signal })
      .then((data) => {
        if (
          !Array.isArray(data?.machines) ||
          !Array.isArray(data?.jobs) ||
          !Array.isArray(data?.committed_schedule) ||
          !data.shift
        )
          throw new Error(
            "The factory response is missing schedule data. Check the API fixture.",
          );
        if (current) setFactory(data);
      })
      .catch((failure) => {
        if (current && failure.name !== "AbortError") setError(failure.message);
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    return () => {
      current = false;
      controller.abort();
    };
  }, [source, attempt]);

  const displayedFactory = view === "committed" ? factory : sampleFactory;
  const schedule = useMemo(() => {
    if (!displayedFactory) return [];
    const raw =
      view === "committed"
        ? displayedFactory.committed_schedule
        : view === "recovery"
          ? sampleSolve.alternatives[0].schedule
          : sampleReplay.failing_scenario.timeline;
    return annotateChanges(
      raw,
      displayedFactory.committed_schedule,
      displayedFactory.now,
    );
  }, [view, displayedFactory]);
  const outcomes = displayedFactory
    ? jobOutcomes(displayedFactory.jobs, schedule)
    : [];
  const lateJobs = outcomes.filter((job) => job.late > 0);
  const changedCount = schedule.filter(
    (operation) =>
      operation.change && !["none", "frozen"].includes(operation.change),
  ).length;
  const activeOperation =
    schedule.find((operation) => operationKey(operation) === selected) || null;
  const activeJob = outcomes.find((job) => job.id === activeOperation?.job);
  const activeMachine = displayedFactory?.machines.find(
    (machine) => machine.id === activeOperation?.machine,
  );
  const lastFinish = schedule.length
    ? Math.max(...schedule.map((operation) => minutes(operation.end)))
    : null;
  const outages =
    view === "committed"
      ? []
      : sampleExtract.constraints
          .filter((constraint) => constraint.type === "machine_down")
          .map((constraint) => constraint.params);
  const nominalOutage = outages[0];
  const outageMachine = sampleFactory.machines.find(
    (machine) => machine.id === nominalOutage?.machine,
  );
  const protectedConstraint = sampleExtract.constraints.find(
    (constraint) => constraint.type === "due_date" && constraint.params.hard,
  );
  const recoveryLate = sampleSolve.alternatives[0].kpis.late_jobs[0];
  const currentView = VIEWS.find((item) => item.id === view);

  function changeView(next) {
    setView(next);
    setSelected(null);
    setHighlight(next === "failure" ? { job: "J4", op: 2 } : null);
  }

  return (
    <>
      <a className="skip-link" href="#workspace">
        Skip to schedule
      </a>
      <header className="app-header">
        <a className="brand" href="./" aria-label="Rehearsal home">
          <span className="brand-mark" aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
          Rehearsal<span className="brand-period">.</span>
        </a>
        <span className="header-divider" />
        <span className="header-context">Production workspace</span>
        <div className="team-signature">
          FORGE AHEAD <span> / </span> ACT III
        </div>
      </header>

      <main id="workspace">
        <div className="page-heading">
          <div>
            <div className="eyebrow">PLAN WITH A CLEAR VIEW</div>
            <h1>See the shift. Know the tradeoffs.</h1>
            <p>
              A production schedule you can inspect before the next decision.
            </p>
          </div>
          <label className="source-control">
            <span>FACTORY DATA SOURCE</span>
            <select
              value={source}
              onChange={(event) => setSource(event.target.value)}
            >
              <option value="sample">Sample fixture</option>
              <option value="live">Live factory API</option>
            </select>
          </label>
        </div>

        <div className="provenance">
          <span className="status-dot" />
          <strong>Synthetic demo data</strong>
          <span className="provenance-divider">/</span>
          <span>
            {view !== "committed"
              ? "Saved sample · independent of live factory data"
              : source === "sample"
                ? "Saved fixture · no live AMD calls"
                : "Factory endpoint only · AMD integration pending"}
          </span>
        </div>

        {error && (
          <div className="error-banner" role="alert">
            <div>
              <strong>Factory data couldn’t be loaded.</strong>
              <p>{error}</p>
            </div>
            <button onClick={() => setAttempt((value) => value + 1)}>
              Retry <ArrowIcon />
            </button>
          </div>
        )}
        {loading && (
          <div className="loading-panel" role="status">
            <span className="loading-dot" />
            Loading the factory schedule…
          </div>
        )}

        {!loading && !error && displayedFactory && (
          <>
            <section
              className="schedule-section"
              aria-labelledby="schedule-heading"
            >
              <div className="schedule-topline">
                <div>
                  <span className="factory-icon" aria-hidden="true">
                    ⌑
                  </span>
                  <h2 id="schedule-heading">
                    {displayedFactory.factory.replace(
                      /\s*\(synthetic data\)/i,
                      "",
                    )}
                  </h2>
                </div>
                <span className="factory-date">
                  {new Date(
                    `${displayedFactory.date}T12:00:00`,
                  ).toLocaleDateString("en-GB", {
                    day: "numeric",
                    month: "short",
                    year: "numeric",
                  })}
                  <span>·</span>Local factory time
                </span>
              </div>
              <div
                className="view-controls"
                role="group"
                aria-label="Schedule view"
              >
                {VIEWS.map((item) => (
                  <button
                    key={item.id}
                    aria-pressed={view === item.id}
                    className={view === item.id ? "active" : ""}
                    onClick={() => changeView(item.id)}
                  >
                    <span className="view-number">{item.number}</span>
                    <span>
                      <strong>{item.title}</strong>
                      <small>{item.subtitle}</small>
                    </span>
                    {view === item.id && (
                      <span className="view-indicator" aria-hidden="true">
                        ↗
                      </span>
                    )}
                  </button>
                ))}
              </div>

              <div
                className={`view-note ${view === "failure" ? "failure-note" : ""}`}
              >
                <span className="note-symbol" aria-hidden="true">
                  {view === "committed" ? "↳" : view === "recovery" ? "↗" : "!"}
                </span>
                {view === "committed" ? (
                  <p>
                    <strong>The committed plan.</strong>{" "}
                    {displayedFactory.jobs.length} orders across{" "}
                    {displayedFactory.machines.length} machines. Select an
                    operation to inspect its timing and delivery promise.
                  </p>
                ) : view === "recovery" ? (
                  <p>
                    <strong>Saved synthetic example.</strong>{" "}
                    {outageMachine?.name} is down until {nominalOutage?.until}.
                    Re-routing protects {protectedConstraint?.params.job}’s{" "}
                    {protectedConstraint?.params.time} promise;{" "}
                    {recoveryLate?.job} finishes {recoveryLate?.minutes_late}{" "}
                    minutes late.
                  </p>
                ) : (
                  <p>
                    <strong>
                      Saved synthetic failure · scenario{" "}
                      {sampleReplay.failing_scenario.index}.
                    </strong>{" "}
                    {sampleReplay.failing_scenario.reason}. Hatching shows the
                    nominal outage; sampled repair time is not supplied.
                  </p>
                )}
              </div>

              <Timeline
                machines={displayedFactory.machines}
                jobs={displayedFactory.jobs}
                schedule={schedule}
                now={displayedFactory.now}
                shift={displayedFactory.shift}
                outages={outages}
                dueMarkers={displayedFactory.jobs.map((job) => ({
                  job: job.id,
                  time: job.due,
                }))}
                selectedKey={selected}
                highlight={highlight || []}
                onInspect={(operation) => setSelected(operationKey(operation))}
                label={currentView.title}
              />

              <div className="timeline-legend">
                <span>
                  <i className="legend-block" />
                  Operation
                </span>
                <span>
                  <i className="legend-block frozen" />
                  Started before now
                </span>
                <span>
                  <i className="legend-block changed" />
                  {view === "failure"
                    ? "Varies from committed plan"
                    : "Changed operation"}
                </span>
                <span>
                  <i className="legend-outage" />
                  {view === "failure" ? "Nominal outage" : "Machine outage"}
                </span>
                <span>
                  <i className="legend-flag">⚑</i>Order due time
                </span>
                <span className="keyboard-hint">Hover or Tab to inspect</span>
              </div>

              <div
                className={`operation-detail ${activeOperation ? "has-selection" : ""}`}
                aria-live="polite"
                aria-atomic="true"
              >
                {activeOperation ? (
                  <>
                    <div className="detail-title">
                      <span
                        className="job-swatch"
                        style={{ background: activeJob?.color }}
                      />{" "}
                      <strong>
                        {activeOperation.job} · Operation {activeOperation.op}
                      </strong>
                      <span>{activeJob?.customer}</span>
                    </div>
                    <div className="detail-field">
                      <span>RESOURCE</span>
                      <strong>{activeMachine?.name}</strong>
                    </div>
                    <div className="detail-field">
                      <span>
                        {view === "failure" ? "SAMPLED TIME" : "PLANNED TIME"}
                      </span>
                      <strong>
                        {activeOperation.start}–{activeOperation.end}
                      </strong>
                    </div>
                    <div className="detail-field">
                      <span>ORDER DUE</span>
                      <strong>{activeJob?.due}</strong>
                    </div>
                    <div className="detail-change">
                      {view === "failure" &&
                      activeOperation.change === "retimed"
                        ? "Simulated timing variation"
                        : describeChange(activeOperation.change)}
                    </div>
                  </>
                ) : (
                  <>
                    <span className="inspect-icon" aria-hidden="true">
                      ↖
                    </span>
                    <p>
                      <strong>Every block has a story.</strong> Hover, focus, or
                      select an operation to see the customer, timing, and
                      changes.
                    </p>
                  </>
                )}
              </div>
            </section>

            <section
              className="checker-section"
              aria-label="Independent schedule verification"
              aria-live="polite"
            >
              <div className="checker-section-title">
                <div className="eyebrow">BEFORE YOU COMMIT</div>
                <h2>Check the plan against the rules.</h2>
              </div>
              {view === "committed" ? (
                <CheckerResult
                  result={
                    source === "sample"
                      ? checkerReports.reports.committed
                      : null
                  }
                  title="Committed schedule"
                  description={
                    source === "sample"
                      ? "Saved independent check of the sample fixture, before any disruption. All operations satisfy the factory rules."
                      : "This factory response has no checker report. A saved sample check cannot verify live data."
                  }
                />
              ) : view === "recovery" ? (
                <>
                  <CheckerResult
                    result={checkerReports.reports.recovery}
                    title="Recovery alternative"
                    description="Saved independent check against the sample outage, hard due time and overtime cutoff. J2’s late delivery still needs approval."
                  />
                  <details className="checker-comparison" key="recovery-comparison">
                    <summary>Why the original plan cannot continue</summary>
                    <CheckerResult
                      result={checkerReports.reports.disrupted_committed}
                      title="Original plan with the disruption applied"
                      description="The same checker rejects the unchanged schedule under the new constraints."
                    />
                  </details>
                </>
              ) : (
                <CheckerResult
                  result={null}
                  title="Sampled future"
                  description="This is a simulated outcome with varying durations, rather than a dispatch plan with fixed processing times. The independent check applies to the recovery alternative."
                />
              )}
              <p className="checker-scope">
                Checks cover operation coverage, eligibility, duration, order,
                machine conflicts, outages, started work, working hours and hard
                due times. Saved reports come from the Python checker; they do
                not prove that a disruption message was understood correctly.
              </p>
            </section>

            <section
              className="orders-section"
              aria-labelledby="orders-heading"
            >
              <div className="orders-header">
                <div>
                  <div className="eyebrow">DELIVERY PROMISES</div>
                  <h2 id="orders-heading">
                    Orders in this schedule <span>{outcomes.length}</span>
                  </h2>
                </div>
                <div className="summary">
                  <span>
                    <strong>
                      {outcomes.filter((job) => job.late === 0).length}
                    </strong>{" "}
                    on time
                  </span>
                  <span className={lateJobs.length ? "late-summary" : ""}>
                    <strong>{lateJobs.length}</strong> late
                  </span>
                  <span>
                    <strong>{view === "committed" ? "—" : changedCount}</strong>{" "}
                    changed ops
                  </span>
                  <span>
                    Last finish{" "}
                    <strong>
                      {lastFinish === null ? "—" : clock(lastFinish)}
                    </strong>
                  </span>
                </div>
              </div>
              <div className="orders-table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>ORDER / CUSTOMER</th>
                      <th>PRIORITY</th>
                      <th>DUE</th>
                      <th>
                        {view === "failure"
                          ? "SAMPLED FINISH"
                          : "PLANNED FINISH"}
                      </th>
                      <th>DELIVERY STATUS</th>
                      <th>
                        <span className="sr-only">Highlight order</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {outcomes.map((job) => (
                      <tr
                        key={job.id}
                        className={
                          highlight?.job === job.id ? "highlighted-row" : ""
                        }
                      >
                        <td>
                          <div className="order-name">
                            <span
                              className="job-swatch"
                              style={{ background: job.color }}
                            />
                            <strong>{job.id}</strong>
                            <span>{job.customer}</span>
                          </div>
                        </td>
                        <td>
                          <span className={`priority priority-${job.priority}`}>
                            {job.priority === 3
                              ? "Critical"
                              : job.priority === 2
                                ? "High"
                                : "Normal"}
                          </span>
                        </td>
                        <td className="tabular">{job.due}</td>
                        <td className="tabular">
                          {job.finish === null
                            ? "Unscheduled"
                            : clock(job.finish)}
                        </td>
                        <td>
                          {job.late === null ? (
                            <span>Not scheduled</span>
                          ) : job.late > 0 ? (
                            <span className="delivery-late">
                              {job.late} min late
                            </span>
                          ) : (
                            <span className="delivery-on-time">
                              <span />
                              On time
                            </span>
                          )}
                        </td>
                        <td>
                          <button
                            className="highlight-button"
                            aria-label={`${highlight?.job === job.id ? "Clear highlight for" : "Highlight"} ${job.id} on timeline`}
                            aria-pressed={highlight?.job === job.id}
                            onClick={() =>
                              setHighlight(
                                highlight?.job === job.id
                                  ? null
                                  : { job: job.id },
                              )
                            }
                          >
                            {highlight?.job === job.id ? "Clear" : "Locate"}
                            <ArrowIcon />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}

        <ApprovalPanel
          runId={sampleSolve.run_id}
          alternative={sampleSolve.alternatives[0]}
          sample
          hidden={loading || Boolean(error) || view !== "recovery"}
        />

        {!loading && !error && displayedFactory && (
          <footer className="workspace-footer">
            <span>
              REHEARSAL <span> / </span> Understand the plan before you commit.
            </span>
            <p>
              {view === "failure"
                ? "Recorded simulation with synthetic uncertainty. Not calibrated to a real factory."
                : view === "recovery"
                  ? "Saved synthetic recovery plan. Approval rechecks its stored schedule before export."
                  : "Message understanding and recovery tools are being built."}
            </p>
          </footer>
        )}
      </main>
    </>
  );
}
