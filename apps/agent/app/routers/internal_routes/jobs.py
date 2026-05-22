from __future__ import annotations

from fastapi import APIRouter, Header

from app.routers.internal_auth import check_internal_token

router = APIRouter()


@router.post("/jobs/process")
async def process_job(payload: dict, x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
    return {"ok": True, "received": payload}
