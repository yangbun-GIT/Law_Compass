from __future__ import annotations
from typing import Any
from app.mcp.tool_registry import register_tool
from app.services.rag.two_stage_cache import invalidate_scope

def invalidate_cache_tool(payload: dict[str, Any]) -> dict[str, Any]:
    return invalidate_scope(payload.get("scope") or "knia_json")

def register_cache_tools() -> None:
    register_tool("invalidate_cache_tool", invalidate_cache_tool)
