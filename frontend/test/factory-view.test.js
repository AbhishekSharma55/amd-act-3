import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createApi, ApiError } from "../src/lib/api.js";
import {
  annotateChanges,
  jobOutcomes,
  markerLanes,
  minutes,
  timelineBounds,
} from "../src/lib/timeline.js";
import factory from "../../shared/fixture.json" with { type: "json" };
import solve from "../../shared/mocks/solve.json" with { type: "json" };
import replay from "../../shared/mocks/replay.json" with { type: "json" };

test("shared fixture and all six mocks are byte-for-byte copies of the checked plan", async () => {
  for (const name of [
    "factory",
    "extract",
    "extract_review",
    "solve",
    "replay",
    "approve",
  ]) {
    assert.deepEqual(
      await readFile(
        new URL(`../../shared/mocks/${name}.json`, import.meta.url),
      ),
      await readFile(new URL(`../../plan/mocks/${name}.json`, import.meta.url)),
    );
  }
  assert.deepEqual(
    await readFile(new URL("../../shared/fixture.json", import.meta.url)),
    await readFile(new URL("../../plan/mocks/factory.json", import.meta.url)),
  );
});

test("saved factory contains all 15 operations, three resources and correct spot-check times", () => {
  assert.equal(factory.jobs.length, 7);
  assert.equal(factory.machines.length, 3);
  assert.equal(factory.committed_schedule.length, 15);
  const find = (job, op) =>
    factory.committed_schedule.find(
      (operation) => operation.job === job && operation.op === op,
    );
  assert.deepEqual(
    [find("J1", 2).machine, find("J1", 2).start, find("J1", 2).end],
    ["M2", "09:20", "10:05"],
  );
  assert.deepEqual(
    [find("J6", 2).machine, find("J6", 2).start, find("J6", 2).end],
    ["M1", "10:10", "11:35"],
  );
  assert.deepEqual(
    [find("J7", 3).machine, find("J7", 3).start, find("J7", 3).end],
    ["M3", "13:25", "13:55"],
  );
});

test("delivery outcomes come from each displayed schedule, including the exposed failure", () => {
  assert.equal(
    jobOutcomes(factory.jobs, factory.committed_schedule).filter(
      (job) => job.late > 0,
    ).length,
    0,
  );
  assert.deepEqual(
    jobOutcomes(factory.jobs, solve.alternatives[0].schedule)
      .filter((job) => job.late > 0)
      .map(({ id, late }) => [id, late]),
    [["J2", 190]],
  );
  assert.equal(
    jobOutcomes(factory.jobs, replay.failing_scenario.timeline).find(
      (job) => job.id === "J4",
    ).late,
    61,
  );
});

test("time domain covers the whole shift and expands for operations after overtime", () => {
  assert.deepEqual(timelineBounds(factory.shift, factory.committed_schedule), {
    start: 480,
    end: 1200,
  });
  assert.deepEqual(
    timelineBounds(factory.shift, [{ start: "07:50", end: "20:30" }]),
    { start: 420, end: 1260 },
  );
  for (const invalid of ["09:99", "24:00", "9:00", null, "after lunch"])
    assert.throws(() => minutes(invalid), /Invalid factory time/);
});

test("coincident due times are assigned separate flag lanes", () => {
  const lanes = markerLanes(
    factory.jobs.map((job) => ({ job: job.id, time: job.due })),
    (time) => minutes(time),
  );
  assert.notEqual(
    lanes.find((marker) => marker.job === "J5").lane,
    lanes.find((marker) => marker.job === "J7").lane,
  );
});

test("sample annotations preserve recovery restart information without mutating the fixture", () => {
  const annotated = annotateChanges(
    solve.alternatives[0].schedule,
    factory.committed_schedule,
    factory.now,
  );
  assert.equal(
    annotated.find((operation) => operation.job === "J1" && operation.op === 2)
      .change,
    "restarted_on_M1",
  );
  assert.equal(
    annotated.find((operation) => operation.job === "J3" && operation.op === 1)
      .change,
    "frozen",
  );
  assert.equal(factory.committed_schedule[0].change, undefined);
});

test("mock transport returns contract samples and isolates callers from shared mutation", async () => {
  const api = createApi({
    useMocks: true,
    fetchImpl: () => {
      throw new Error("must not fetch");
    },
  });
  const first = await api("/api/factory");
  first.machines[0].name = "Changed by caller";
  assert.equal((await api("/api/factory")).machines[0].name, "Mill M1");
  assert.equal((await api("/api/solve", {})).alternatives[0].id, "alt_reroute");
  assert.equal((await api("/api/replay", {})).failing_scenario.index, 24);
  await assert.rejects(
    api("/api/health"),
    (error) => error instanceof ApiError && error.code === "mock_unavailable",
  );
});

test("live factory request is an independent GET and does not call later feature endpoints", async () => {
  const calls = [];
  const api = createApi({
    useMocks: false,
    baseUrl: "https://factory.example/",
    fetchImpl: async (...args) => {
      calls.push(args);
      return new Response(JSON.stringify(factory), { status: 200 });
    },
  });
  assert.deepEqual(await api("/api/factory"), factory);
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], "https://factory.example/api/factory");
  assert.equal(calls[0][1].method, "GET");
});

test("live POST keeps JSON body and canonical backend errors", async () => {
  let request;
  const api = createApi({
    useMocks: false,
    fetchImpl: async (_url, options) => {
      request = options;
      return new Response(
        JSON.stringify({
          error: {
            code: "amd_unavailable",
            message: "AMD is unavailable. Please retry.",
            retryable: true,
          },
        }),
        { status: 502 },
      );
    },
  });
  await assert.rejects(
    api("/api/extract", { message: "M2 down" }),
    (error) =>
      error.code === "amd_unavailable" &&
      error.status === 502 &&
      error.retryable &&
      error.message.includes("AMD is unavailable"),
  );
  assert.equal(request.method, "POST");
  assert.equal(request.headers["Content-Type"], "application/json");
  assert.deepEqual(JSON.parse(request.body), { message: "M2 down" });
});

test("offline and malformed live responses produce visible errors without sample fallback", async () => {
  const offline = createApi({
    useMocks: false,
    fetchImpl: async () => {
      throw new TypeError("offline");
    },
  });
  await assert.rejects(
    offline("/api/factory"),
    (error) => error.code === "network_error" && error.retryable,
  );
  const html = createApi({
    useMocks: false,
    fetchImpl: async () =>
      new Response("<html>Proxy error</html>", { status: 502 }),
  });
  await assert.rejects(
    html("/api/factory"),
    (error) => error.code === "invalid_response" && error.status === 502,
  );
});

test("cancelled requests stay cancelled so stale responses are discarded", async () => {
  const cancelled = createApi({
    useMocks: false,
    fetchImpl: async () => {
      throw new DOMException("Aborted", "AbortError");
    },
  });
  await assert.rejects(
    cancelled("/api/factory"),
    (error) => error.name === "AbortError",
  );
});
