import { useEffect, useRef, useState } from "react";
import { createApi } from "../lib/api.js";
import { approvalFiles, approvalRequest, validateApprovalResponse } from "../lib/approval.js";
import { checkerState } from "../lib/checker.js";
import CheckerResult from "./CheckerResult.jsx";
import "./approval.css";

const requestApproval = createApi({
  useMocks: false,
  baseUrl: import.meta.env?.VITE_API_BASE_URL || "",
});

export default function ApprovalPanel(props) {
  // A new immutable plan resets synchronously, before an old response can render.
  return <ApprovalSession key={`${props.runId}:${props.alternative?.id}`} {...props} />;
}

function ApprovalSession({ runId, alternative, hidden = false, sample = false, onInvalidRun }) {
  const [approved, setApproved] = useState([]);
  const [approver, setApprover] = useState("");
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [links, setLinks] = useState([]);
  const session = useRef(0);
  const busy = useRef(false);
  const controller = useRef(null);

  useEffect(() => {
    session.current += 1;
    busy.current = false;
    controller.current?.abort();
    setApproved([]);
    setApprover("");
    setPending(false);
    setResult(null);
    setError(null);
    return () => {
      session.current += 1;
      controller.current?.abort();
    };
  }, [runId, alternative?.id]);

  useEffect(() => {
    if (!result) {
      setLinks([]);
      return;
    }
    const next = approvalFiles(result).map((file) => ({
      ...file,
      url: URL.createObjectURL(new Blob([file.text], { type: file.type })),
    }));
    setLinks(next);
    return () => next.forEach((file) => URL.revokeObjectURL(file.url));
  }, [result]);

  const concessions = alternative?.concessions || [];
  const unavailable = ["run_not_found", "run_expired", "alternative_not_found", "run_locked"].includes(error?.code);
  const checked = checkerState(alternative?.checker).status === "passed";
  const ready = Boolean(runId && alternative?.id && checked && approver.trim() && approver.trim().length <= 120 &&
    concessions.every((item) => approved.includes(item.id)) && !pending && !result && !unavailable);

  async function submit(event) {
    event.preventDefault();
    if (!ready || busy.current) return;
    busy.current = true;
    const generation = session.current;
    const body = approvalRequest(runId, alternative.id, approved, approver);
    controller.current = new AbortController();
    setPending(true);
    setError(null);
    try {
      const response = await requestApproval("/api/approve", body, { signal: controller.current.signal });
      if (session.current !== generation) return;
      setResult(validateApprovalResponse(response, body));
    } catch (failure) {
      if (session.current === generation && failure.name !== "AbortError") {
        setError({ message: failure.message, code: failure.code });
      }
    } finally {
      if (session.current === generation) {
        busy.current = false;
        setPending(false);
      }
    }
  }

  return (
    <section className="approval-section" aria-labelledby="approval-heading" hidden={hidden}>
      <div className="approval-header">
        <div>
          <div className="eyebrow">MAKE THE CALL</div>
          <h2 id="approval-heading">Approve the tradeoffs. Keep the record.</h2>
          <p>{sample ? "Sample approval · saved synthetic plan, checked by the service when you approve. No live AMD call." : "Review this recovery plan’s tradeoffs before exporting its dispatch instructions."}</p>
        </div>
        <span className={`approval-stage ${result ? "is-locked" : ""}`}>{result ? "Plan locked" : "Awaiting approval"}</span>
      </div>

      {result ? (
        <div className="approval-success" role="status">
          <CheckerResult
            result={result.decision_record.checker}
            title="Rechecked at approval"
            description={`Approved by ${result.decision_record.approver} at ${new Date(result.decision_record.approved_at).toLocaleString(undefined, { timeZoneName: "short" })}.`}
          />
          <p>This decision is locked to the selected run and alternative. Create a new recovery plan for a different decision.</p>
          <div className="approval-downloads">
            {links.map((file) => <a key={file.name} href={file.url} download={file.name}>{file.type.startsWith("text/csv") ? "Download dispatch CSV" : "Download decision JSON"}<span aria-hidden="true">↓</span></a>)}
          </div>
          <span className="approval-run-id">{runId} / {alternative.id}</span>
        </div>
      ) : (
        <form onSubmit={submit} aria-busy={pending}>
          <fieldset disabled={pending || unavailable} className="approval-tradeoffs">
            <legend>Required tradeoffs for {alternative?.label || "this plan"}</legend>
            {concessions.length ? concessions.map((item) => (
              <label className="approval-concession" key={item.id}>
                <input type="checkbox" name="concession" value={item.id} checked={approved.includes(item.id)}
                  onChange={(event) => setApproved((current) => event.target.checked ? [...current, item.id] : current.filter((id) => id !== item.id))} />
                <span><strong>I accept: {item.detail}</strong>{item.type === "overtime" && <small>Occupied machine time: {item.minutes} min · cost: {Number(item.cost).toFixed(2)} in the fixture’s cost units</small>}</span>
              </label>
            )) : <p>No tradeoffs are listed for this alternative.</p>}
          </fieldset>
          <p className="approval-recheck-note">The service recalculates required tradeoffs and checks the stored schedule again. Every required tradeoff must be accepted before export.</p>
          <div className="approval-actions">
            <label className="approver-input">Approver name
              <input name="approver" type="text" maxLength={120} autoComplete="name" placeholder="Shift supervisor" value={approver} disabled={pending || unavailable} onChange={(event) => setApprover(event.target.value)} />
            </label>
            <button type="submit" disabled={!ready}>{pending ? "Checking and approving…" : error && !unavailable ? "Retry approval" : sample ? "Approve synthetic sample" : "Approve and export"}<span aria-hidden="true">↗</span></button>
          </div>
          {!checked && <p className="approval-not-ready">A passing schedule check is required before approval.</p>}
          {error && <div className="approval-error" role="alert"><strong>Approval was not confirmed.</strong><p>{error.message}</p>{unavailable && onInvalidRun && <button type="button" onClick={onInvalidRun}>Choose a new recovery plan</button>}</div>}
        </form>
      )}
    </section>
  );
}
