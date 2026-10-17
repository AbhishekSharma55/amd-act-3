# Run Rehearsal with Docker

The image runs the built React frontend and the FastAPI backend at one address.
It includes the CPU OR-Tools solver, independent checker, NumPy replay, approval
and exports. AMD inference stays on Token Factory; no model or GPU is installed
in this container.

## Start locally

Install Docker Engine/Desktop with Docker Compose. From the repository root:

```bash
cp .env.example .env
# Fill AMD_API_BASE, AMD_API_KEY and AMD_MODEL in .env using the Token Factory portal.
docker compose up --build --detach
```

Open **http://localhost:7860**. Check health and logs:

```bash
curl --fail http://localhost:7860/api/health
docker compose logs --tail=100 rehearsal
docker compose down
```

Compose reads `.env` to supply runtime configuration. The allowlisted build
context excludes `.env`, credentials, Git history, research and local dependency
directories. The browser receives no AMD key. Do not put credentials in build
arguments or the Dockerfile. Git ignores `.env`.

If Linux reports permission denied on the Docker socket after adding your user
to the Docker group, start a new login session. An existing shell can use
`sg docker -c 'docker compose up --build --detach'`.

The default starts with **real API calls and rule fallback disabled**. Without
all three AMD settings, the UI and health endpoint work, while extraction
returns `503 amd_not_configured`. Health's `amd.configured` confirms configuration
is present; it does not prove the model endpoint accepts a request. Verify a real
extraction separately before recording the demo.

## Try the workflow while AMD access is pending

```bash
ALLOW_RULE_FALLBACK=1 docker compose up --build --detach
```

With no AMD credentials, extraction uses the labeled rule fallback. Solver,
checker, replay and exports still execute. This is an offline functional check;
it provides no evidence of AMD inference or extraction quality. Keep
`ALLOW_RULE_FALLBACK=0` for the real AMD demo so failures remain visible.

## Build and run without Compose

```bash
docker build --tag rehearsal:local .
docker run --rm --init --name rehearsal --publish 127.0.0.1:7860:7860 \
  --env-file .env rehearsal:local
```

To change the application port, set `PORT` and publish that container port too:

```bash
docker run --rm --init --publish 127.0.0.1:8080:8080 \
  --env-file .env --env PORT=8080 rehearsal:local
```

For Compose, `PORT=8080 docker compose up --detach` changes both ports. Local
examples bind to localhost; public hosting is a separate deployment step.

## Runtime settings and lifecycle

| Setting | Container default | Effect |
| --- | --- | --- |
| `PORT` | `7860` | HTTP listener; must be an integer from 1 to 65535 |
| `AMD_API_BASE`, `AMD_API_KEY`, `AMD_MODEL` | Empty | Set at runtime using the host's secret/environment settings |
| `ALLOW_RULE_FALLBACK` | `0` | Explicit opt-in to labeled fallback extraction |
| `SOLVER_WORKERS` | `2` | CP-SAT threads; these are separate from API workers |
| `RUN_TTL_S`, `MAX_RUNS` | `21600`, `2000` | Session expiry in seconds and maximum stored runs |
| `EXTRACT_RATE_PER_MIN` | `12` | Extraction rate limit per client address |
| `STATIC_DIR` | `/app/backend/static` | Packaged production frontend |

Other AMD and logging settings are described in [.env.example](../.env.example)
and the [backend guide](../backend/README.md).

The image runs as UID/GID `1000:1000`, with one Uvicorn worker. Use **one replica**:
runs, approvals and rate limits live in process memory. `WEB_CONCURRENCY` does
not change the entry point's worker count. Restarting the process, replacing the
container or reaching the run expiry loses those sessions. Download the CSV and
decision record before stopping it. A Docker volume does not persist this state.

Startup validates the frontend and fixture. Docker's health check calls
`/api/health` on the configured port. It checks the app and fixture; it does not
make a paid model request. SIGTERM stops the HTTP server gracefully.

## Verify the packaged application

These checks need only host Python 3 and Docker. They require empty AMD settings
and never call a model. Use separate containers so each check has fresh state:

```bash
docker run --detach --init --name rehearsal-strict \
  --publish 127.0.0.1:17860:7860 rehearsal:local
python3 scripts/container_smoke.py http://127.0.0.1:17860 --mode strict

docker run --detach --init --name rehearsal-fallback \
  --publish 127.0.0.1:17861:8080 --env PORT=8080 \
  --env ALLOW_RULE_FALLBACK=1 rehearsal:local
python3 scripts/container_smoke.py http://127.0.0.1:17861 --mode fallback

docker rm --force rehearsal-strict rehearsal-fallback
```

CI builds the image from scratch, checks its runtime user/package, then runs
both checks. They cover same-origin assets, missing-key behavior, real solving,
independent checking, CPU replay, concession approval, CSV/JSON export,
idempotent approval and evidence locking. The custom-port check also sets
`WEB_CONCURRENCY=4` to exercise the fixed single-worker entry point.

### Verify a real AMD request

After setting the Token Factory settings in `.env` and starting Compose with
`ALLOW_RULE_FALLBACK=0`:

```bash
python3 scripts/container_smoke.py http://localhost:7860 --mode amd \
  --save-to eval/smoke/docker_live.json
```

This mode makes one real model request. It requires AMD configuration and
disabled fallback, verifies the model trace, then checks solve, replay,
approval and exports. The optional JSON artifact contains the synthetic
workflow inputs and responses. The API key stays on the server. CI runs only
the two offline modes.

The same command can check a deployed HTTPS URL after deployment. A local
success does not establish that the public host or its AMD secrets work.

## Public AWS deployment

The application is deployed on AWS Lightsail Container Service with managed
HTTPS and server-side AMD credentials. The complete public workflow passed
using a real AMD request with fallback disabled. See [the live URL, deployment
instructions, verification and $15/month hosting estimate](AWS_DEPLOYMENT.md).

The host uses port `7860` and one Small instance. An expiry schedule deletes the
service after 28 days; its precise time and cleanup commands are documented in
the deployment guide. For another Docker host, preserve one API worker and one
instance because run state is held in memory.

References: [Docker multi-stage builds](https://docs.docker.com/build/building/multi-stage/),
[Dockerfile reference](https://docs.docker.com/reference/dockerfile/).
