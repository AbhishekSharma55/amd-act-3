# Factory endpoint · issue #3

This is an isolated factory router so Phase 1 works before the shared backend
foundation or AMD access. It does not create or own `app/main.py`.

## Run the factory-only development server

Use Python 3.12+ (Python 3.14.4 tested). From the repository root:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-factory-dev.txt
backend/.venv/bin/python -m uvicorn app.factory_dev:app --app-dir backend --host 127.0.0.1 --port 8000
```

If your system Python lacks `venv`/`ensurepip`, install your distribution's venv
package or create the environment with `uv venv backend/.venv`. Dependencies
are isolated from the system Python. Runtime-only installations can use
`requirements-factory.txt`; the dev file additionally installs HTTPX for tests.

Check <http://127.0.0.1:8000/api/factory> or `/docs`. The endpoint returns the
checked `shared/fixture.json` unchanged. No key or solver package is needed.

```bash
backend/.venv/bin/python -m unittest discover -s backend/tests -v
```

## Mount in the shared backend

In the main application owned by the foundation work:

```python
from fastapi import FastAPI
from app.factory import router as factory_router

app = FastAPI()
app.include_router(factory_router)
```

Merge the runtime requirements into the shared backend requirements when that
foundation lands. No central entrypoint changes are needed in this branch.
The factory module locates `shared/fixture.json` relative to the repository,
independent of the working directory. A packaged/container deployment must
preserve the `backend/app/` and `shared/` relative layout, or call
`create_factory_router(Path(...))` with the deployed fixture location.

The router loads and checks the fixture on creation, so missing files, invalid
clock strings, unknown identifiers, incorrect operation coverage, ineligible
machines and mismatched durations prevent startup with a readable path and
reason. This is fixture validation, not the separate recovery feasibility
checker. Serve frontend static files after API routes in the eventual shared
application. The factory-only server deliberately has no extraction, solver,
replay, approval, or AMD health endpoints.
