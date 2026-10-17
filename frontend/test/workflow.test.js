import test from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";
import { describe, effectiveJobs, isReady, outagesFrom, solvePayload } from "../src/lib/workflow.js";
import extract from "../../shared/mocks/extract.json" with { type: "json" };
import review from "../../shared/mocks/extract_review.json" with { type: "json" };
import factory from "../../shared/mocks/factory.json" with { type: "json" };
import solve from "../../shared/mocks/solve.json" with { type: "json" };
import replay from "../../shared/mocks/replay.json" with { type: "json" };

const withDecisions = (constraints, decisions = {}) =>
  constraints.map((c) => ({ ...c, decision: decisions[c.id] ?? null }));

test("blocking items are never ready, even when the planner clicks Accept", () => {
  const [blocked, ambiguous] = withDecisions(review.constraints, { c1: "accepted", c2: "accepted" });
  assert.equal(isReady(blocked), false);
  assert.equal(isReady(ambiguous), true);
  assert.equal(isReady({ ...ambiguous, decision: null }), false);
});

test("solve payload drops rejected items, marks confirmations and never sends UI-only fields", () => {
  const payload = solvePayload(withDecisions(review.constraints, { c1: "rejected", c2: "accepted" }));
  assert.deepEqual(payload.map((c) => [c.id, c.status]), [["c2", "accepted"]]);
  assert.ok(payload.every((c) => !("decision" in c)));
});

test("timeline outages and due dates come only from reviewed constraints", () => {
  const constraints = withDecisions(extract.constraints);
  assert.deepEqual(outagesFrom(constraints, factory.now), [{ machine: "M2", from: "10:00", until: "14:00" }]);
  assert.deepEqual(outagesFrom(withDecisions(extract.constraints, { c1: "rejected" }), factory.now), []);
  assert.deepEqual(outagesFrom(withDecisions(review.constraints), factory.now), []);  // unknown machine, no end
  const jobs = effectiveJobs(factory.jobs, [{ ...extract.constraints[1], params: { job: "J4", time: "16:30", hard: true } }]);
  assert.equal(jobs.find((j) => j.id === "J4").due, "16:30");
  assert.equal(factory.jobs.find((j) => j.id === "J4").due, "17:00");  // fixture untouched
});

test("constraints read as plain English", () => {
  assert.equal(describe(extract.constraints[0], factory), "Mill M2 down 10:00 – 14:00");
  assert.equal(describe(extract.constraints[1], factory), "J7 due 16:00 (hard: must not slip)");
  assert.match(describe(review.constraints[0], factory), /end unknown/);
});

test("workflow components render the contract responses with honest wording", async () => {
  const server = await createServer({ server: { middlewareMode: true, ws: false }, appType: "custom", logLevel: "silent" });
  try {
    const load = async (name) => (await server.ssrLoadModule(`/src/components/${name}.jsx`)).default;
    const [ConstraintList, Alternatives, ReplayPanel] = await Promise.all(
      ["ConstraintList", "Alternatives", "ReplayPanel"].map(load));

    const list = renderToStaticMarkup(createElement(ConstraintList, {
      factory, constraints: withDecisions(review.constraints), trace: review.trace, onActivate() {}, onDecide() {},
      onEdit() {}, canSolve: false, onSolve() {}, blockedReason: "Decide c1, c2 first" }));
    assert.match(list, /Required: Choose a known machine/);
    assert.match(list, /Accept<\/button>/);
    assert.equal((list.match(/<button disabled="" title="Correct the required fields first"/g) || []).length, 1);

    const cards = renderToStaticMarkup(createElement(Alternatives, { solve, selectedId: "alt_reroute", onSelect() {}, onConstraintClick() {} }));
    assert.match(cards, /No plan can meet these/);
    assert.match(cards, /sufficient set, not necessarily minimal/);
    assert.match(cards, /J2 late 190 min/);
    const unknown = { ...solve, alternatives: [], status: "no_feasible_plan",
                      infeasible: [{ ...solve.infeasible[0], solver_status: "UNKNOWN", conflict: [] }] };
    const unknownCards = renderToStaticMarkup(createElement(Alternatives, { solve: unknown, onSelect() {}, onConstraintClick() {} }));
    assert.match(unknownCards, /No plan found in budget/);
    assert.doesNotMatch(unknownCards, /No plan can meet these/);

    const rehearsal = renderToStaticMarkup(createElement(ReplayPanel, {
      alt: solve.alternatives[0], replay, delay: 90, setDelay() {}, onRun() {}, showFailure: false, setShowFailure() {} }));
    assert.match(rehearsal, /on time in <b>239 of 500<\/b>/);
    assert.match(rehearsal, /synthetic, not calibrated to a real factory/);
    assert.doesNotMatch(rehearsal, /reliab/i);
  } finally {
    await server.close();
  }
});
