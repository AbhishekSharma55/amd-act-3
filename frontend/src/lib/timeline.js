export const JOB_COLORS = [
  "#c7d8e6",
  "#e5c5b0",
  "#c9d5bc",
  "#dacbe2",
  "#dfd6aa",
  "#bcd6d2",
  "#c5cced",
];

export function minutes(value) {
  if (typeof value !== "string" || !/^([01]\d|2[0-3]):[0-5]\d$/.test(value))
    throw new Error(`Invalid factory time: ${value}`);
  const [hour, minute] = value.split(":").map(Number);
  return hour * 60 + minute;
}

export function clock(value) {
  return `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`;
}

export const operationKey = (operation) => `${operation.job}:${operation.op}`;

/** Greedy packing keeps coincident/nearby due flags readable. */
export function markerLanes(markers, x, minimumGap = 42) {
  const occupied = [];
  return [...markers]
    .sort((a, b) => minutes(a.time) - minutes(b.time))
    .map((marker) => {
      const position = x(marker.time);
      let lane = occupied.findIndex((last) => position - last >= minimumGap);
      if (lane < 0) lane = occupied.length;
      occupied[lane] = position;
      return { ...marker, lane };
    });
}

export function isChanged(operation) {
  return Boolean(
    operation.change && !["none", "frozen"].includes(operation.change),
  );
}

export function describeChange(change) {
  if (!change || change === "none") return "Committed operation";
  if (change === "frozen") return "Started before now · fixed";
  if (change === "retimed") return "Start time changed";
  if (change === "restarted") return "Restarted after interruption";
  return change
    .replace("restarted_on_", "Restarted on ")
    .replace("moved_from_", "Moved from ");
}

export function timelineBounds(shift, schedule, outages = [], dueMarkers = []) {
  const start = Math.min(
    minutes(shift.start),
    ...schedule.map((operation) => minutes(operation.start)),
  );
  const end = Math.max(
    minutes(shift.overtime_until || shift.end),
    ...schedule.map((operation) => minutes(operation.end)),
    ...outages.map((outage) => minutes(outage.until)),
    ...dueMarkers.map((marker) => minutes(marker.time)),
  );
  return { start: Math.floor(start / 60) * 60, end: Math.ceil(end / 60) * 60 };
}

export function jobOutcomes(jobs, schedule) {
  return jobs.map((job, index) => {
    const operations = schedule.filter((operation) => operation.job === job.id);
    const finish = operations.length
      ? Math.max(...operations.map((operation) => minutes(operation.end)))
      : null;
    return {
      ...job,
      color: JOB_COLORS[index % JOB_COLORS.length],
      finish,
      late: finish === null ? null : Math.max(0, finish - minutes(job.due)),
    };
  });
}

/** Give recorded failure operations change styles relative to the committed plan. */
export function annotateChanges(schedule, committed, now) {
  const originals = new Map(
    committed.map((operation) => [operationKey(operation), operation]),
  );
  return schedule.map((operation) => {
    if (operation.change) return operation;
    const original = originals.get(operationKey(operation));
    let change = "none";
    if (original) {
      if (operation.machine !== original.machine)
        change = `moved_from_${original.machine}`;
      else if (
        operation.start !== original.start ||
        operation.end !== original.end
      )
        change = "retimed";
      else if (minutes(operation.start) < minutes(now)) change = "frozen";
    }
    return { ...operation, change };
  });
}
