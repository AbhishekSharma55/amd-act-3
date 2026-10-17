# Development and verification

[Docker](DOCKER.md) is the quickest complete setup and uses Python 3.12/Node 22
inside the build. The following native workflow is useful for backend or UI
editing. Run commands from the repository root unless a step changes directory.

## Native setup

Install **Python 3.12**, **Node 22.12 or newer** and npm, plus Git. CI uses
Python 3.12 and Node 22. Direct Python dependencies are pinned; npm uses the
checked-in lockfile. Python transitive dependencies are not a complete lockfile;
the [license inventory](../licenses/inventory.json) records the inspected image.

macOS/Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
cp .env.example .env
npm --prefix frontend ci
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
Copy-Item .env.example .env
npm --prefix frontend ci
```

Use `.venv\Scripts\python.exe` instead of `python` in subsequent commands on
Windows if the environment is not activated. For a first offline run, leave
`AMD_API_KEY` empty and set `ALLOW_RULE_FALLBACK=1` in `.env`. For real inference,
set all three AMD settings and `ALLOW_RULE_FALLBACK=0`. Process environment
values override `.env`; a server restart is needed after changing settings.

Start the backend in terminal 1:

```bash
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In terminal 2, start the UI in live-service mode (macOS/Linux):

```bash
VITE_USE_MOCKS=0 npm --prefix frontend run dev -- --port 5173
```

PowerShell equivalent:

```powershell
$env:VITE_USE_MOCKS="0"
npm --prefix frontend run dev -- --port 5173
```

Open **http://localhost:5173** and select **Live API** if necessary. Vite proxies
`/api` to `127.0.0.1:8000`. Plain `npm run dev` defaults to recorded previews;
the production build defaults to live API calls. All `VITE_*` values are public:
never put an AMD key in them. For a different API origin, set
`VITE_API_BASE_URL` and allow that frontend origin in backend `CORS_ORIGINS`.

The integrated backend is `app.main:app`. The `factory_dev` and `approval_dev`
apps in older feature guides are isolated development helpers, not the full app.

## Serve a production build without Docker

```bash
npm --prefix frontend run build
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open http://localhost:8000. Backend configuration discovers `frontend/dist`
unless a packaged `backend/static` or explicit `STATIC_DIR` takes precedence.
The development proxy is not part of the static build. Use one worker; adding
workers or replicas breaks access to the process-local runs and approvals.

## Checks and evaluation

After installing development dependencies and activating the virtual environment:

```bash
python -m pytest -q backend/tests
PYTHONPATH=backend python -m app.checker_report --check
(cd plan/prototype && python regression_checks.py)
npm --prefix frontend test
npm --prefix frontend run build
```

On PowerShell, set `$env:PYTHONPATH="backend"` before the checker command and
run the planning regression command after `Push-Location plan/prototype`,
then `Pop-Location`. Backend tests stub model calls; these checks need no AMD key.
CI runs these checks plus the strict/fallback Docker workflow checks in
[`ci.yml`](../.github/workflows/ci.yml).

Rescore saved AMD predictions against Abhishek's unchanged labels without a
model request or overwriting the saved report:

```bash
python eval/rescore_saved.py --predictions eval/results/extraction_amd.json \
  --labels eval/labels/abhishek.jsonl --output /tmp/rehearsal-rescore.json
```

On Windows choose a writable local output path instead of `/tmp/...`.
The complete extraction and recovery runners are documented in
[the evaluation guide](../eval/README.md). They write `eval/results/`; use a
separate checkout/output copy when preserving the published evidence. Live
extraction evaluation consumes shared AMD quota. No label is automatically
changed or reconciled by these scripts.

To check a running container, use the
[strict/fallback smoke commands](DOCKER.md#verify-the-packaged-application).
With real AMD access and fallback disabled, this command makes one model request:

```bash
python scripts/container_smoke.py http://localhost:7860 --mode amd \
  --save-to /tmp/rehearsal-live-check.json
```

## Common setup problems

| Symptom | Check |
| --- | --- |
| Extraction reports `amd_not_configured` | Set base URL, model and key, then restart; or explicitly enable local fallback with empty AMD settings. |
| HTTP 429 / shared key busy | Stop duplicate requests and respect the returned retry guidance. The team shares provider quota. |
| Model call is slow | The backend may retry transient failures. The browser has a two-minute request deadline; recorded previews and offline fallback are explicitly separate modes. |
| UI says Recorded samples | Choose Live API or start Vite with `VITE_USE_MOCKS=0`. |
| Run expired/not found after an update | Start a new extraction/solve. Sessions are in memory and expire. |
| Root page missing from backend | Build the frontend before starting the production backend. For hot reload, use Vite instead. |
| Docker socket permission denied on Linux | Open a new login session after joining the Docker group, or use `sg docker -c 'docker compose up --build --detach'`. |

Public submission access and final video/slides are separate tasks. Setup does
not require changing repository visibility or the saved evaluation evidence.
