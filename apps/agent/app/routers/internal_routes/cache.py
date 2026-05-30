from __future__ import annotations

from fastapi import APIRouter, Header

from app.mcp.tool_executor import execute_tool
from app.routers.internal_auth import check_internal_token

router = APIRouter()


@router.post("/cache/invalidate")
async def cache_invalidate(payload: dict | None = None, x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
    payload = payload or {}
    return execute_tool("invalidate_cache_tool", {"scope": payload.get("scope") or "knia_json"}, granted_scopes=["cache.write"])
