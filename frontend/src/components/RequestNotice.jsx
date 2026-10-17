export default function RequestNotice({ title, error, busy, onRetry, onDismiss, onCancel }) {
  if (busy) return (
    <div className="loading-panel request-notice" role="status" aria-live="polite">
      <span className="loading-dot" /><span>{busy}</span>
      {onCancel && <button type="button" onClick={onCancel}>Cancel</button>}
    </div>
  );
  if (!error) return null;
  return (
    <div className="error-banner" role="alert">
      <div><strong>{title || "That step didn’t complete."}</strong><p>{error.message}</p></div>
      <div className="wf-actions">
        {onRetry && <button type="button" onClick={onRetry}>Retry</button>}
        {onDismiss && <button type="button" onClick={onDismiss}>Dismiss</button>}
      </div>
    </div>
  );
}
