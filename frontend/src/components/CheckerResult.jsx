import { checkerState } from "../lib/checker.js";

/** Reused by alternative cards, approval, and the run inspector. */
export default function CheckerResult({ result, title, description }) {
  const state = checkerState(result);
  return (
    <div className="checker-result" data-check-status={state.status}>
      <div className="checker-result-heading">
        <strong>{title || "Independent schedule check"}</strong>
        <span className={`checker-badge checker-${state.status}`}>
          <span aria-hidden="true">
            {state.status === "passed"
              ? "✓"
              : state.status === "failed"
                ? "!"
                : "○"}
          </span>
          {state.label}
        </span>
      </div>
      {description && <p>{description}</p>}
      {state.violations.length > 0 && (
        <div className="checker-violations">
          <strong>
            {state.violations.length}{" "}
            {state.violations.length === 1 ? "violation" : "violations"}
          </strong>
          <ul>
            {state.violations.map((violation, index) => (
              <li key={`${index}:${violation}`}>{violation}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
