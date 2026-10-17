import { checkerState } from "./checker.js";

export function approvalRequest(runId, alternativeId, approved, approver) {
  return {
    run_id: runId,
    alternative_id: alternativeId,
    approved_concessions: [...approved].sort(),
    approver: approver.trim(),
  };
}

/** A response for a previous plan must never unlock this plan's downloads. */
export function validateApprovalResponse(result, request) {
  const record = result?.decision_record;
  if (
    typeof result?.dispatch_csv !== "string" ||
    !result.dispatch_csv.startsWith("machine,sequence,job,op,start,end,changed\n") ||
    record?.run_id !== request.run_id ||
    record?.alternative_id !== request.alternative_id ||
    record?.approver !== request.approver ||
    !Number.isFinite(Date.parse(record?.approved_at)) ||
    !Array.isArray(record?.concessions) ||
    !Array.isArray(record?.constraints) ||
    checkerState(record?.checker).status !== "passed"
  ) {
    throw new Error("The approval response does not match this checked plan. Retry the same approval to retrieve its record.");
  }
  const actual = record.concessions.map((item) => item?.id).sort();
  if (JSON.stringify(actual) !== JSON.stringify(request.approved_concessions)) {
    throw new Error("The approval response contains different tradeoffs. Review the selected plan again.");
  }
  return result;
}

export function approvalFiles(result) {
  const runId = result.decision_record.run_id;
  if (!/^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/.test(runId)) {
    throw new Error("Invalid run identifier for export.");
  }
  return [
    { name: `dispatch_${runId}.csv`, type: "text/csv;charset=utf-8", text: result.dispatch_csv },
    { name: `decision_${runId}.json`, type: "application/json;charset=utf-8", text: JSON.stringify(result.decision_record, null, 2) + "\n" },
  ];
}
