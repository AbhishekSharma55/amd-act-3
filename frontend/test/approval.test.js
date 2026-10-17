import test from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";
import { approvalFiles, approvalRequest, validateApprovalResponse } from "../src/lib/approval.js";
import { createApi } from "../src/lib/api.js";
import saved from "../../shared/mocks/approve.json" with { type: "json" };
import solve from "../../shared/mocks/solve.json" with { type: "json" };

const record = saved.decision_record;
const request = approvalRequest(record.run_id, record.alternative_id, ["k1"], record.approver);

test("approval sends only IDs, explicit decisions and a trimmed identity", () => {
  assert.deepEqual(
    approvalRequest("run", "alt", ["k2", "k1"], " Abhishek "),
    { run_id: "run", alternative_id: "alt", approved_concessions: ["k1", "k2"], approver: "Abhishek" },
  );
});

test("saved transport cannot turn a recorded approval into a new approval", async () => {
  await assert.rejects(
    createApi({ useMocks: true })("/api/approve", request),
    (error) => error.code === "approval_requires_service",
  );
});

test("downloads require a matching checked approval instead of a stale response", () => {
  assert.equal(validateApprovalResponse(saved, request), saved);
  for (const update of [
    { run_id: "previous_run" },
    { alternative_id: "previous_alternative" },
    { approver: "Other person" },
    { approved_at: null },
    { checker: { valid: true, violations: ["Broken plan"] } },
    { checker: null },
    { concessions: [] },
    { constraints: null },
  ]) {
    assert.throws(() => validateApprovalResponse({ ...saved, decision_record: { ...record, ...update } }, request));
  }
});

test("export filenames and bytes belong to the selected run", () => {
  const [csv, decision] = approvalFiles(saved);
  assert.equal(csv.name, `dispatch_${record.run_id}.csv`);
  assert.equal(csv.text, saved.dispatch_csv);
  assert.equal(decision.name, `decision_${record.run_id}.json`);
  assert.deepEqual(JSON.parse(decision.text), record);
  assert.throws(() => approvalFiles({ decision_record: { run_id: "../bad" } }));
});

test("panel exposes every tradeoff and requires review before the initial approval", async () => {
  const server = await createServer({ server: { middlewareMode: true, ws: false }, appType: "custom" });
  try {
    const { default: ApprovalPanel } = await server.ssrLoadModule("/src/components/ApprovalPanel.jsx");
    const markup = renderToStaticMarkup(createElement(ApprovalPanel, { runId: solve.run_id, alternative: solve.alternatives[0], sample: true }));
    assert.match(markup, /J2 \(Birla Valves\) ships 190 min late/);
    assert.match(markup, /name="approver"/);
    assert.match(markup, /type="submit" disabled=""/);
    assert.doesNotMatch(markup, /download=/);
    assert.match(markup, /No live AMD call/);
  } finally {
    await server.close();
  }
});
