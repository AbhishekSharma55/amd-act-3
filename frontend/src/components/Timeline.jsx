import { useId } from "react";
import {
  clock,
  describeChange,
  isChanged,
  JOB_COLORS,
  markerLanes,
  minutes,
  operationKey,
  timelineBounds,
} from "../lib/timeline.js";

/**
 * Reusable production timeline. See frontend/README.md for the public contract.
 * highlight: {job, op?} or an array of "job:op" keys. No sample-specific logic.
 */
export default function Timeline({
  machines,
  jobs,
  schedule,
  now,
  shift,
  outages = [],
  dueMarkers = [],
  highlight = [],
  selectedKey,
  onInspect,
  label = "Production schedule",
}) {
  const id = useId().replaceAll(":", "");
  const { start, end } = timelineBounds(shift, schedule, outages, dueMarkers);
  const left = 142,
    plotWidth = 936,
    top = 83,
    rowHeight = 94;
  const bottom = top + machines.length * rowHeight;
  const x = (time) =>
    left + ((minutes(time) - start) / (end - start)) * plotWidth;
  const color = (job) =>
    JOB_COLORS[
      Math.max(
        0,
        jobs.findIndex((item) => item.id === job),
      ) % JOB_COLORS.length
    ];
  const highlighted = (operation) =>
    Array.isArray(highlight)
      ? highlight.includes(operationKey(operation))
      : highlight?.job === operation.job &&
        (highlight.op === undefined || highlight.op === operation.op);
  const ticks = Array.from({ length: (end - start) / 60 + 1 }, (_, index) =>
    clock(start + index * 60),
  );

  return (
    <div
      className="timeline-scroll"
      role="region"
      aria-label={`${label}; horizontally scrollable on small screens`}
      tabIndex={0}
    >
      <svg
        className="timeline"
        viewBox={`0 0 1100 ${bottom + 25}`}
        role="group"
        aria-labelledby={`${id}-title ${id}-desc`}
      >
        <title id={`${id}-title`}>{label}</title>
        <desc id={`${id}-desc`}>
          One row per machine. Operation labels are job and operation number.
          Select or focus an operation for details. Hatched areas mark outages.
          The orange line is the current factory time.
        </desc>
        <defs>
          <pattern
            id={`${id}-outage`}
            width="8"
            height="8"
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(45)"
          >
            <rect width="8" height="8" fill="#f4e4db" />
            <line
              x1="0"
              y1="0"
              x2="0"
              y2="8"
              stroke="#ddb99f"
              strokeWidth="2"
            />
          </pattern>
          <pattern
            id={`${id}-overtime`}
            width="7"
            height="7"
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(45)"
          >
            <line
              x1="0"
              y1="0"
              x2="0"
              y2="7"
              stroke="#d6d1bc"
              strokeWidth="1"
            />
          </pattern>
        </defs>

        <text x="12" y="66" className="axis-caption">
          MACHINE
        </text>
        {markerLanes(dueMarkers, x).map((marker) => (
          <g key={`${marker.job}-${marker.time}`} className="due-flag">
            <title>
              {marker.job} due {marker.time}
            </title>
            <path
              d={`M ${x(marker.time)} ${10 + marker.lane * 18} v 16 l 7 -4 v -9 z`}
              fill={color(marker.job)}
              stroke="#777c72"
              strokeWidth=".6"
            />
            <text x={x(marker.time) + 11} y={21 + marker.lane * 18}>
              {marker.job}
            </text>
          </g>
        ))}

        <rect
          x={left}
          y={top}
          width={plotWidth}
          height={machines.length * rowHeight}
          fill="#fcfcf9"
        />
        <rect
          x={left}
          y={top}
          width={Math.max(0, Math.min(plotWidth, x(now) - left))}
          height={machines.length * rowHeight}
          fill="#eeeee7"
          opacity=".6"
        />
        {minutes(shift.end) < end && (
          <>
            <rect
              x={x(shift.end)}
              y={top}
              width={Math.max(0, left + plotWidth - x(shift.end))}
              height={machines.length * rowHeight}
              fill="#f1eee2"
            />
            <rect
              x={x(shift.end)}
              y={top}
              width={Math.max(0, left + plotWidth - x(shift.end))}
              height={machines.length * rowHeight}
              fill={`url(#${id}-overtime)`}
            />
          </>
        )}

        {ticks.map((tick) => (
          <g key={tick}>
            <line
              x1={x(tick)}
              x2={x(tick)}
              y1={top}
              y2={bottom}
              stroke="#e3e5dc"
              strokeDasharray={minutes(tick) % 120 ? "3 4" : undefined}
            />
            <text x={x(tick)} y="66" textAnchor="middle" className="hour-tick">
              {tick}
            </text>
          </g>
        ))}
        {machines.map((machine, index) => {
          const y = top + index * rowHeight;
          const machineOperations = schedule.filter(
            (operation) => operation.machine === machine.id,
          );
          return (
            <g key={machine.id}>
              <text x="12" y={y + 38} className="machine-name">
                {machine.name}
              </text>
              <text x="12" y={y + 58} className="machine-count">
                {machineOperations.length} operations
              </text>
              <line
                x1="0"
                x2="1090"
                y1={y + rowHeight}
                y2={y + rowHeight}
                stroke="#e6e6de"
              />
              {machineOperations.length === 0 && (
                <text x={left + 18} y={y + 48} className="empty-machine">
                  No operations scheduled
                </text>
              )}
              {outages
                .filter((outage) => outage.machine === machine.id)
                .map((outage, outageIndex) => (
                  <g key={`${machine.id}-${outageIndex}`}>
                    <rect
                      x={x(outage.from)}
                      y={y + 8}
                      width={x(outage.until) - x(outage.from)}
                      height={rowHeight - 16}
                      rx="4"
                      fill={`url(#${id}-outage)`}
                      stroke="#d0a68c"
                      strokeDasharray="3 3"
                    />
                    <text
                      x={x(outage.from) + 9}
                      y={y + 22}
                      className="outage-label"
                    >
                      UNAVAILABLE · {outage.from}–{outage.until}
                    </text>
                  </g>
                ))}
              {machineOperations.map((operation) => {
                const job = jobs.find((item) => item.id === operation.job);
                const key = operationKey(operation);
                const active = key === selectedKey;
                const width = Math.max(
                  2,
                  x(operation.end) - x(operation.start),
                );
                const frozen = minutes(operation.start) < minutes(now);
                const showText = width > 33;
                return (
                  <g
                    key={key}
                    role="button"
                    tabIndex={0}
                    aria-label={`${operation.job} operation ${operation.op}, ${job?.customer}, ${machine.name}, ${operation.start} to ${operation.end}, due ${job?.due}. ${describeChange(operation.change)}`}
                    aria-pressed={active}
                    className={`operation ${frozen ? "is-frozen" : ""} ${isChanged(operation) ? "is-changed" : ""} ${highlighted(operation) ? "is-highlighted" : ""} ${active ? "is-selected" : ""}`}
                    onMouseEnter={() => onInspect?.(operation)}
                    onClick={() => onInspect?.(operation)}
                    onFocus={() => onInspect?.(operation)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        onInspect?.(operation);
                      }
                    }}
                  >
                    <title>{`${operation.job} · operation ${operation.op} | ${job?.customer} | ${machine.name} | ${operation.start}–${operation.end} | due ${job?.due}`}</title>
                    <rect
                      className="operation-fill"
                      x={x(operation.start) + 1}
                      y={y + 32}
                      width={Math.max(1, width - 2)}
                      height="35"
                      rx="4"
                      fill={color(operation.job)}
                    />
                    {showText && (
                      <text
                        x={x(operation.start) + Math.min(10, width / 6)}
                        y={y + 54}
                        className="operation-text"
                      >
                        {operation.job}·{operation.op}
                      </text>
                    )}
                    {isChanged(operation) && width > 55 && (
                      <path
                        d={`m ${x(operation.end) - 15} ${y + 40} 5 0 0 5 m 0 -5 -7 7`}
                        className="changed-arrow"
                      />
                    )}
                  </g>
                );
              })}
            </g>
          );
        })}
        <line
          x1={x(shift.end)}
          x2={x(shift.end)}
          y1={top - 8}
          y2={bottom}
          stroke="#b5ad8d"
          strokeDasharray="4 3"
        />
        <text x={x(shift.end) + 8} y={bottom + 18} className="shift-label">
          SHIFT END · OVERTIME →
        </text>
        <line
          x1={x(now)}
          x2={x(now)}
          y1={top - 8}
          y2={bottom}
          className="now-line"
        />
        <rect
          x={x(now) - 36}
          y={top - 19}
          width="72"
          height="21"
          rx="4"
          fill="#c7542a"
        />
        <text x={x(now)} y={top - 5} textAnchor="middle" className="now-label">
          NOW {now}
        </text>
      </svg>
    </div>
  );
}
