import test from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";
import { annotateChanges } from "../src/lib/timeline.js";

test("failure timeline paints processing segments with a real outage gap", async () => {
  const server = await createServer({ server: { middlewareMode: true }, appType: "custom" });
  try {
    const { default: Timeline } = await server.ssrLoadModule("/src/components/Timeline.jsx");
    const original = { job: "J6", op: 1, machine: "M1", start: "09:00", end: "10:10" };
    const interrupted = { ...original, end: "12:20", segments: [
      { start: "09:00", end: "10:11", kind: "interrupted" },
      { start: "11:00", end: "12:20", kind: "restart" },
    ] };
    const schedule = annotateChanges([interrupted], [original], "10:00");
    const html = renderToStaticMarkup(React.createElement(Timeline, {
      machines: [{ id: "M1", name: "Mill M1" }],
      jobs: [{ id: "J6", customer: "Factory customer", due: "17:00" }],
      schedule, now: "10:00", shift: { start: "08:00", end: "18:00", overtime_until: "20:00" },
      outages: [{ machine: "M1", from: "10:11", until: "11:00" }],
    }));
    const rects = html.match(/<rect class="operation-fill"[^>]*>/g);
    assert.equal(rects.length, 2);
    assert.match(rects[0], /data-segment-kind="interrupted"/);
    assert.match(rects[1], /data-segment-kind="restart"/);
    const number = (rect, attr) => Number(rect.match(new RegExp(` ${attr}="([^"]+)"`))[1]);
    const gapPixels = number(rects[1], "x") - number(rects[0], "x") - number(rects[0], "width");
    assert.ok(gapPixels > 60, "the 49-minute outage must not be filled by an operation bar");
    assert.match(html, /Restarted after interruption/);
    assert.match(html, /Processing: 09:00 to 10:11 \(interrupted\); 11:00 to 12:20 \(restart\)/);
    assert.equal((html.match(/role="button"/g) || []).length, 1, "segments remain one logical operation");
    assert.equal(original.segments, undefined);
  } finally {
    await server.close();
  }
});
