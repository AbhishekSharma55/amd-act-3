# Factory view · issue #3

React/Vite frontend for Rehearsal. This phase displays the committed production
schedule and two clearly labeled, recorded synthetic examples. It does not call
AMD, solve schedules, run simulations, validate recovery feasibility, or approve
anything. Those features will reuse this shell and timeline.

## Run

Use Node **22.12+** (Node 24.21 tested) and npm. From this folder:

```bash
npm ci
npm run dev -- --port 5173
```

Open <http://127.0.0.1:5173>. No account, API key, or backend is needed for the
default sample fixture. The dependency lockfile is committed. Fonts are served
locally, with their SIL Open Font License notices in `public/fonts/`.

```bash
npm test
npm run build
npm run preview -- --port 4173
```

The production build is `dist/`. The build is portable static frontend output;
the development `/api` proxy is not part of that output. Deployment will serve
the frontend and backend together or configure a real API origin.

## Live factory endpoint

Start the factory-only API using `../backend/README-factory.md`. The data-source
selector switches the committed view between the checked sample and
`GET /api/factory`; the Vite proxy forwards `/api` to `127.0.0.1:8000`. It never
silently falls back to sample data. A failed request shows a retryable error.

To start in live mode:

```bash
VITE_USE_MOCKS=0 npm run dev -- --port 5173
```

Optional `VITE_API_BASE_URL` points at a different API origin (which must allow
the frontend origin with CORS). Leave it empty for the same-origin proxy. Never
put AMD credentials into `VITE_*` variables: they are public browser settings.

Only `/api/factory` is needed in live mode. Switching to Sample recovery or
Sample failure always uses that example's own checked sample fixture and says
so above the timeline. These views do not call future `/solve` or `/replay`
endpoints and cannot be mistaken for freshly calculated results.

## Integration contracts

`src/lib/api.js` exports `api(path, body?, options?)` and
`createApi({useMocks, baseUrl, fetchImpl})`. Body omitted means GET; a supplied
body means a JSON POST. `options.signal` supports cancellation. Successful mock
responses are deep copies. Errors carry `code`, `status`, `retryable`, and the
backend's canonical message. Existing factory/extract/solve/replay/approve mock
responses follow `plan/03_API_CONTRACT.md`; mock `/health` is intentionally
unsupported rather than inventing AMD configuration. `App.jsx` owns this first
page's state. Future feature panels should import the shared transport.

`src/components/Timeline.jsx` is independent of the examples:

| Prop          | Shape / meaning                                                                 |
| ------------- | ------------------------------------------------------------------------------- |
| `machines`    | Fixture machine objects, in row order; empty machine rows are supported         |
| `jobs`        | Fixture jobs; array order determines stable job colors                          |
| `schedule`    | Array of `{job, op, machine, start, end, change?}`                              |
| `now`         | `HH:MM`, factory local time                                                     |
| `shift`       | Fixture shift; `start`, `end`, optional `overtime_until`                        |
| `outages`     | `{machine, from, until}[]`; defaults to empty                                   |
| `dueMarkers`  | `{job, time}[]`; coincident/nearby markers use separate lanes                   |
| `highlight`   | `{job, op?}` or array of `"job:op"` keys; defaults to empty                     |
| `selectedKey` | Selected operation key such as `"J7:2"`                                         |
| `onInspect`   | Callback receiving an operation on hover, click, keyboard focus, Enter or Space |
| `label`       | Accessible schedule name                                                        |

The viewport derives its bounds from shift, schedule, outages and due markers,
so overtime is not clipped. The selected-operation detail lives outside the
SVG. The component itself does not know solver, checker, replay, concession, or
AMD semantics. Frozen styling describes started work; approval decisions belong
to the future server flow.

`src/lib/timeline.js` supplies strict clock parsing, schedule-derived delivery
outcomes, stable operation keys, and optional sample annotations.
`shared/fixture.json` and all six `shared/mocks/*.json` are byte-for-byte copies
of the checked plan. Do not regenerate them as a side effect of running the UI.

## Checks and manual QA

`npm test` checks fixture integrity, delivery outcomes from all three schedules,
time bounds, coincident due markers, annotation preservation, mock isolation,
live GET/POST requests, canonical errors, malformed responses, offline behavior,
and cancellation. These use the Node test runner and need no browser download.

For browser QA, verify the three view controls, order Locate/Clear buttons,
operation hover and keyboard focus, source switching, retry after a stopped
backend, and timeline horizontal scrolling at narrow sizes. Spot-check J1·2
09:20–10:05 on Mill M2; J6·2 10:10–11:35 on Mill M1; J7·3 13:25–13:55 on Lathe
L3 in the committed view. The saved recovery has J2 190 minutes late; the saved
failure has J4 61 minutes late. Hatching in the failure shows the **nominal**
outage: the replay response does not supply sampled repair-end metadata.
