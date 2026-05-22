from __future__ import annotations

from fastapi import APIRouter, Header

from app.routers.internal_auth import check_internal_token
from app.services.rag.two_stage_cache import invalidate_scope

router = APIRouter()


@router.post("/cache/invalidate")
async def cache_invalidate(payload: dict | None = None, x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
    payload = payload or {}
    return invalidate_scope(payload.get("scope") or "knia_json")
