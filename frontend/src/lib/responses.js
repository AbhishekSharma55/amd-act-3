import { ApiError } from "./api.js";
import { minutes } from "./timeline.js";

const object = (value) => value && typeof value === "object" && !Array.isArray(value);
const strings = (value) => Array.isArray(value) && value.every((item) => typeof item === "string");
const id = (value) => typeof value === "string" && value.length > 0;
const clock = (value) => { try { minutes(value); return true; } catch { return false; } };
const schedule = (rows) => Array.isArray(rows) && rows.every((row) => object(row) && id(row.job) && Number.isInteger(row.op) && id(row.machine) && clock(row.start) && clock(row.end));
const constraints = (rows) => Array.isArray(rows) && rows.every((c) => object(c) && id(c.id) && id(c.type) && id(c.status) && object(c.params) && strings(c.issues) && strings(c.blocking_issues) && typeof c.source_span === "string");
const checker = (value) => object(value) && typeof value.valid === "boolean" && strings(value.violations);

function require(condition, name) {
  if (!condition) throw new ApiError(`The service returned incomplete ${name} data. Retry or contact the project team.`, { code: "invalid_response", retryable: true });
}

export function factoryResponse(data) {
  require(object(data) && id(data.factory) && id(data.date) && Number.isFinite(Date.parse(data.date)) && clock(data.now) && object(data.shift), "factory");
  require(clock(data.shift.start) && clock(data.shift.end) && clock(data.shift.overtime_until || data.shift.end), "factory hours");
  require(Array.isArray(data.machines) && data.machines.length > 0 && data.machines.every((m) => object(m) && id(m.id) && id(m.name)), "machine");
  require(Array.isArray(data.jobs) && data.jobs.every((j) => object(j) && id(j.id) && typeof j.customer === "string" && clock(j.due) && Number.isInteger(j.priority)), "order");
  require(schedule(data.committed_schedule), "schedule");
  return data;
}

export function workflowResponse(stage, data) {
  require(object(data) && id(data.run_id), stage);
  if (stage === "extract") {
    require(typeof data.message === "string" && constraints(data.constraints) && object(data.trace), "extraction");
  } else if (stage === "revalidate") {
    require(constraints(data.constraints), "reviewed constraints");
  } else if (stage === "solve") {
    require(Array.isArray(data.alternatives) && Array.isArray(data.infeasible), "recovery");
    for (const alt of data.alternatives) {
      require(object(alt) && id(alt.id) && id(alt.label) && schedule(alt.schedule) && checker(alt.checker) && object(alt.policy) && object(alt.solver), "alternative");
      require(object(alt.kpis) && Array.isArray(alt.kpis.late_jobs) && alt.kpis.late_jobs.every((job) => object(job) && id(job.job) && Number.isFinite(job.minutes_late) && typeof job.customer === "string") && Array.isArray(alt.concessions) && alt.concessions.every((c) => object(c) && id(c.id) && typeof c.detail === "string"), "alternative outcomes");
      require(["overtime_minutes", "overtime_cost", "moved_ops", "retimed_ops"].every((key) => Number.isFinite(alt.kpis[key])) && typeof alt.policy.reroute === "boolean" && typeof alt.policy.overtime === "boolean" && ["OPTIMAL", "FEASIBLE"].includes(alt.solver.status), "alternative metrics");
    }
    require(data.infeasible.every((item) => object(item) && id(item.label) && object(item.policy) && ["INFEASIBLE", "UNKNOWN"].includes(item.solver_status) && typeof item.explanation === "string" && (!item.conflict || strings(item.conflict)) && (!item.possible_concessions || (Array.isArray(item.possible_concessions) && item.possible_concessions.every(object)))), "solver result");
  } else if (stage === "replay") {
    require(id(data.alternative_id) && Number.isInteger(data.samples) && data.samples > 0 && object(data.assumptions) && Array.isArray(data.jobs), "rehearsal");
    require(Array.isArray(data.assumptions.duration_spread) && data.assumptions.duration_spread.length === 2 && data.assumptions.duration_spread.every(Number.isFinite), "rehearsal assumptions");
    require(data.jobs.every((j) => object(j) && id(j.job) && Number.isInteger(j.on_time) && Number.isInteger(j.of) && j.of > 0 && j.on_time >= 0 && j.on_time <= j.of && typeof j.p90_finish === "string"), "rehearsal outcomes");
    require(data.failing_scenario === null || (object(data.failing_scenario) && schedule(data.failing_scenario.timeline) && typeof data.failing_scenario.reason === "string"), "failure timeline");
  }
  return data;
}
