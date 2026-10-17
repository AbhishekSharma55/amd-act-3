"""Factory-only local server. The shared backend owns app/main.py."""

from fastapi import FastAPI

from .factory import router

app = FastAPI(title="Rehearsal · factory-only development API")
app.include_router(router)
