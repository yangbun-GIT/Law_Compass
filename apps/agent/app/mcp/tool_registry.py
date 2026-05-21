from __future__ import annotations

from typing import Any, Callable

ToolFn = Callable[[dict[str, Any]], dict[str, Any]]
_REGISTRY: dict[str, ToolFn] = {}


def register_tool(name: str, fn: ToolFn) -> None:
    _REGISTRY[name] = fn


def get_tool(name: str) -> ToolFn:
    if name not in _REGISTRY:
        raise KeyError(f"unknown MCP tool: {name}")
    return _REGISTRY[name]


def list_tools() -> list[str]:
    return sorted(_REGISTRY.keys())


def bootstrap_tools() -> None:
    from app.mcp.tools.knia_tools import register_knia_tools
    from app.mcp.tools.cache_tools import register_cache_tools
    from app.mcp.tools.legal_rag_tools import register_legal_rag_tools
    from app.mcp.tools.evidence_guard_tools import register_evidence_guard_tools
    register_knia_tools()
    register_cache_tools()
    register_legal_rag_tools()
    register_evidence_guard_tools()
