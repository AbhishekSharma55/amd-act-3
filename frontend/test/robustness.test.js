import test from "node:test";
import assert from "node:assert/strict";
import { createRequestScope } from "../src/lib/request-scope.js";
import { createApi } from "../src/lib/api.js";
import { factoryResponse, workflowResponse } from "../src/lib/responses.js";
import factory from "../../shared/mocks/factory.json" with { type: "json" };
import extract from "../../shared/mocks/extract.json" with { type: "json" };
import solve from "../../shared/mocks/solve.json" with { type: "json" };
import replay from "../../shared/mocks/replay.json" with { type: "json" };

test("a superseded request cannot commit even if its server ignores cancellation", async () => {
  const scope = createRequestScope();
  const first = scope.begin();
  assert.equal(scope.begin(), null, "duplicate clicks must not start another operation");
  scope.cancel();
  assert.equal(first.controller.signal.aborted, true);
  const second = scope.begin();
  assert.equal(scope.matches(first), false);
  scope.finish(first);
  assert.equal(scope.matches(second), true, "old completion must not release the new request");
  scope.finish(second);
  assert.equal(scope.matches(second), false);
});

test("transport times out explicitly without substituting recorded results", async () => {
  const api = createApi({ useMocks: false, timeoutMs: 15, fetchImpl: (_url, { signal }) => new Promise((_resolve, reject) => {
    signal.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
  }) });
  await assert.rejects(api("/api/extract", { message: "M2 down" }), (error) => error.code === "request_timeout" && error.retryable);
});

test("explicit cancellation remains cancellation, including already-aborted samples", async () => {
  const controller = new AbortController();
  controller.abort();
  for (const useMocks of [true, false]) {
    await assert.rejects(createApi({ useMocks })("/api/factory", undefined, { signal: controller.signal }), (error) => error.name === "AbortError");
  }
});

test("noncanonical rate-limit responses remain retryable", async () => {
  const api = createApi({ useMocks: false, fetchImpl: async () => new Response(JSON.stringify({ message: "rate limited" }), { status: 429 }) });
  await assert.rejects(api("/api/extract", {}), (error) => error.status === 429 && error.retryable);
});

test("response boundaries accept real contract samples and empty outcomes", () => {
  assert.equal(factoryResponse(factory), factory);
  for (const [stage, data] of [["extract", extract], ["solve", solve], ["replay", replay]]) assert.equal(workflowResponse(stage, data), data);
  assert.equal(workflowResponse("replay", { ...replay, failing_scenario: null }).failing_scenario, null);
  assert.equal(workflowResponse("solve", { ...solve, alternatives: [] }).alternatives.length, 0);
});

test("malformed JSON payloads become recoverable errors before rendering", () => {
  for (const bad of [null, {}, { ...factory, now: "09:99" }, { ...factory, jobs: null }, { ...factory, machines: [{}] }]) {
    assert.throws(() => factoryResponse(bad), (error) => error.code === "invalid_response");
  }
  const malformedAlternative = { ...solve.alternatives[0], kpis: { ...solve.alternatives[0].kpis, late_jobs: [null] } };
  for (const [stage, bad] of [["extract", { ...extract, constraints: [null] }], ["solve", { ...solve, alternatives: [{}] }], ["solve", { ...solve, alternatives: [malformedAlternative] }], ["solve", { ...solve, infeasible: [{ ...solve.infeasible[0], solver_status: "MODEL_INVALID" }] }], ["replay", { ...replay, jobs: [{}] }]]) {
    assert.throws(() => workflowResponse(stage, bad), (error) => error.code === "invalid_response");
  }
});
