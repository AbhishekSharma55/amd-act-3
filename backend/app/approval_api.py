"""Mountable existing-contract endpoint; the foundation owns app/main.py."""

import json

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .approval import ApprovalError
from .approval_store import ApprovalStore


def create_approval_router(store: ApprovalStore) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["approval"])

    @router.post("/approve")
    async def approve(request: Request):
        """IDs + approved concession IDs + approver; never client plan replacements."""
        try:
            try:
                body = await request.json()
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise ApprovalError("invalid_json", "Send a JSON approval request.", 400) from None
            return store.approve(body)
        except ApprovalError as error:
            return JSONResponse(error.response(), status_code=error.status)

    return router
