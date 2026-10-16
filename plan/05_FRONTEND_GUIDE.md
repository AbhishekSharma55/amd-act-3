# 05. Frontend guide (Person B)

React with Vite. Plain JavaScript is fine. No UI framework is required; plain CSS or Tailwind both work. Build every screen from `shared/mocks/` first, then switch to the real API at Sync 1 and Sync 2.

## Setup (B1)

```bash
npm create vite@latest frontend -- --template react
cd frontend && npm install
```

`vite.config.js`: proxy `/api` to the backend in development, so the same URLs work locally and in production:

```js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000" } },
});
```

`src/api.js`: one place that switches between mocks and the real API, so no component cares which one is in use:

```js
const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === "1";

const mocks = {
  "/api/factory": () => import("../../shared/mocks/factory.json"),
  "/api/extract": () => import("../../shared/mocks/extract.json"),
  "/api/solve": () => import("../../shared/mocks/solve.json"),
  "/api/replay": () => import("../../shared/mocks/replay.json"),
  "/api/approve": () => import("../../shared/mocks/approve.json"),
};

export async function api(path, body) {
  if (USE_MOCKS) return (await mocks[path]()).default;
  const res = await fetch(path, body
    ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
    : undefined);
  const data = await res.json();
  if (!res.ok) throw new Error(data?.error?.message || `Request failed (${res.status})`);
  return data;
}
```

Run with mocks: `VITE_USE_MOCKS=1 npm run dev`. Run against the backend: `npm run dev`.

Vite blocks imports from outside the project folder by default. If importing `../../shared/...` fails, copy `shared/mocks/` into `frontend/src/mocks/` and import from there.

## Screen layout

One page, read top to bottom in demo order:

```
┌──────────────────────────────────────────────────────────────────────┐
│ Rehearsal · Demo Machine Shop (synthetic data) now 10:00 [Inspector] │
├──────────────────────────────────────────────────────────────────────┤
│ TIMELINE  M1 ███J3███ ██J6██ │ ...                                    │
│           M2 ██J5██ ▓▓▓▓ OUTAGE ▓▓▓▓ ...    (now line, due markers)   │
│           M3 ...                                                      │
├───────────────────────────────┬──────────────────────────────────────┤
│ 1. MESSAGE                    │ 2. CONSTRAINTS                        │
│ [textarea + sample buttons]   │ ✓ M2 down 10:00-14:00   (source ↗)    │
│ "Mill M2 is unavailable..."   │ ✓ J7 due 16:00 (hard)                 │
│ [Read message]                │ ⚠ Review: unknown machine "Mill 4"   │
│                               │   [Accept] [Reject]                   │
├───────────────────────────────┴──────────────────────────────────────┤
│ 3. ALTERNATIVES   [Find recovery plans]                               │
│ ┌ Keep machines ──────┐ ┌ Re-route ───────────┐                       │
│ │ ✗ No plan meets     │ │ J2 late 190 min     │                       │
│ │ J7 by 16:00         │ │ 0 overtime · 2 moved│                       │
│ │ Conflict: c1 + c2   │ │ Checker ✓           │                       │
│ └─────────────────────┘ └─────────────────────┘                       │
├──────────────────────────────────────────────────────────────────────┤
│ 4. REHEARSE   [Show a failure]  J4 on time in 211 of 500 scenarios    │
│ 5. APPROVE    ☐ J2 ships 190 min late   Approver [____]  [Approve]    │
└──────────────────────────────────────────────────────────────────────┘
```

## Components and phases

| Component | Phase | Props / data | Behavior |
| --- | --- | --- | --- |
| `Timeline` | B1 | `machines`, `schedule`, `now`, `outages`, `dueMarkers`, `highlight` | SVG. Rows are machines, x-axis 08:00-20:00, with the shift end at 18:00 and overtime shaded. One color per job, labeled `J7·2`. Outages hatched. A vertical "now" line. Frozen operations dimmed. Changed operations outlined. |
| `MessagePanel` | B2 | `onSubmit(message)` | Textarea plus 3-4 sample buttons (the demo message, one with an unknown machine, one with no time, one "no overtime today"). Loading state while the AMD call runs. |
| `SourceHighlight` | B2 | `message`, `spans[]`, `activeId` | Renders the message with each constraint's `source_span` wrapped in `<mark>`; the active one is stronger. Match case-insensitively. If a span is not found, show nothing; the backend has already flagged it. |
| `ConstraintList` | B2 | `constraints`, `onDecide(id, "accepted" \| "rejected")` | Icon per status. Shows `issues` under each item. **Review items require Accept or Reject.** Rejected items are struck through. Shows `origin`; `rule_fallback` gets a visible warning badge. |
| `AlternativeCard` | B3 | one alternative or one infeasible entry | KPIs: late jobs with minutes, overtime minutes and cost, moved/retimed counts, checker badge, solver status. "Merged with: re-route + overtime" note when present. Infeasible: red card, `explanation`, conflicting constraint IDs that link back to the list, and `conflict_kind` worded as "these constraints together cannot be met (sufficient set)". |
| `CompareTimeline` | B3 | committed + selected schedules | Before/after stacked, or a toggle. Highlight operations where `change !== "none"`. |
| `ReplayPanel` | B4 | replay response | Per-job bar: "on time in X of N simulated scenarios". **Show a failure** draws `failing_scenario.timeline` in `Timeline` and highlights the bottleneck. Lists the assumptions under it in small text. |
| `ApprovalPanel` | B4 | selected alternative | One checkbox per concession, plus the approver's name. Approve is disabled until all are ticked. After success: download `dispatch_<run_id>.csv` and `decision_<run_id>.json`, and show "Approved by … at …". |
| `RunInspector` | B5 | extract `trace`, solve/replay metadata | Drawer: provider, model, host, latency, attempts, tokens, raw model output (collapsible `<pre>`), validation issues, solver status/time per alternative, checker results, replay device and samples, data notice. |

## App state

Keep it in one place (`useReducer` or a small store). The flow is linear:

```
idle → extracting → constraints (needs decisions?) → solving → alternatives → (replaying) → approving → approved
```

- **Find recovery plans** stays disabled while any constraint is `review` and undecided.
- Send only `ok` and `accepted` constraints to `/api/solve`.
- Editing the message clears everything after step 1, so a stale plan is never shown for a new message.
- Every API error goes to one visible banner with the backend's message and a **Retry** button. For a failed AMD call, the banner says so plainly; the app must not crash.

## CSV download

```js
function download(name, text, type = "text/csv") {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  a.click();
  URL.revokeObjectURL(url);
}
// download(`dispatch_${r.decision_record.run_id}.csv`, r.dispatch_csv);
// download(`decision_${r.decision_record.run_id}.json`, JSON.stringify(r.decision_record, null, 2), "application/json");
```

## Wording rules (judges will read these)

- "211 of 500 simulated scenarios under these assumptions", never "42% reliable".
- "Schedule simulator", never "digital twin".
- "No feasible plan found within 10 s" for `UNKNOWN`; "No plan can meet these constraints" only for `INFEASIBLE`.
- Show "Synthetic demo data" in the header.
- Label any recorded or fallback output as recorded or fallback.

## B6. Docker and deploy

One container: build React, then serve it from FastAPI. This Dockerfile goes in the repo root.

```dockerfile
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
COPY shared/ /shared/
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY shared/ ./shared/
COPY --from=web /web/dist ./static
ENV PORT=7860
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
```

The backend must mount `static/` last, after all `/api` routes (see `04_BACKEND_GUIDE.md`, A6). Adjust the `shared/` copy paths to match how `fixture.py` loads the fixture.

**Hosting.** Our first choice is a Hugging Face Space with the Docker SDK. The free CPU basic tier is 2 vCPU and 16 GB RAM, the app must listen on the port set by `app_port` (7860), and secrets are set in the Space settings. See `06_TECH_RESEARCH.md` for sources and open questions such as sleep behavior. Add the API key as a **secret**, never in the image.

Before the freeze, check from a logged-out browser on a phone and a laptop that the full demo runs on the public URL.

## B7. Submission material

See `07_DEMO_AND_SUBMISSION.md`.
