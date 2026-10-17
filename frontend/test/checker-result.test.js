import test from "node:test";
import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";
import { createServer } from "vite";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { checkerState } from "../src/lib/checker.js";

test("saved UI checks are tied to the current checker and exact synthetic inputs", async () => {
  const reports = JSON.parse(
    await readFile(new URL("../../shared/checker-reports.json", import.meta.url)),
  );
  assert.equal(reports.format_version, 1);
  assert.equal(reports.provenance.synthetic, true);
  assert.equal(reports.provenance.amd_request_made, false);
  const sources = reports.provenance.source_files;
  assert.deepEqual(Object.keys(sources).sort(), ["checker", "extract", "fixture", "solve"]);
  for (const source of Object.values(sources)) {
    const contents = await readFile(new URL(`../../${source.path}`, import.meta.url));
    assert.equal(
      source.sha256,
      createHash("sha256").update(contents).digest("hex"),
      `${source.path} changed: regenerate independent checker reports`,
    );
  }
  assert.equal(checkerState(reports.reports.committed).status, "passed");
  assert.equal(checkerState(reports.reports.recovery).status, "passed");
  assert.equal(checkerState(reports.reports.disrupted_committed).status, "failed");
});

test("missing, malformed and contradictory reports cannot produce a passing badge", () => {
  for (const report of [
    null,
    {},
    { valid: "true", violations: [] },
    { valid: true },
    { valid: true, violations: ["Machine overlap"] },
    { valid: false, violations: [] },
    { valid: false, violations: [null] },
    { valid: false, violations: [""] },
  ]) {
    assert.equal(checkerState(report).status, "unavailable");
  }
});

test("reusable result renders every backend violation as text and a rejection badge", async () => {
  const server = await createServer({
    server: { middlewareMode: true, ws: false },
    appType: "custom",
  });
  try {
    const { default: CheckerResult } = await server.ssrLoadModule(
      "/src/components/CheckerResult.jsx",
    );
    const violations = [
      "J7 op 3 starts before op 2 ends",
      'Unknown machine <img src=x onerror="alert(1)">',
      "J1 op 2 overlaps outage on M2",
    ];
    const markup = renderToStaticMarkup(
      createElement(CheckerResult, {
        result: { valid: false, violations },
        title: "Recovery alternative",
      }),
    );
    assert.match(markup, /data-check-status="failed"/);
    assert.match(markup, /Plan rejected/);
    assert.match(markup, /3 violations/);
    assert.equal((markup.match(/<li>/g) || []).length, violations.length);
    assert.match(markup, /J1 op 2 overlaps outage on M2/);
    assert.match(markup, /&lt;img/);
    assert.doesNotMatch(markup, /<img/);

    const unverified = renderToStaticMarkup(
      createElement(CheckerResult, { result: null }),
    );
    assert.match(unverified, /Not checked/);
    assert.doesNotMatch(unverified, /Passed checks/);

    const valid = renderToStaticMarkup(
      createElement(CheckerResult, {
        result: { valid: true, violations: [] },
      }),
    );
    assert.match(valid, /Passed checks/);
    assert.doesNotMatch(valid, /checker-violations/);
  } finally {
    await server.close();
  }
});
