from __future__ import annotations

from typing import Any, Callable

from app.services.agent_contracts import MCPToolSpec, P1_INTERNAL_TOOL_SPECS


ToolFn = Callable[[dict[str, Any]], dict[str, Any]]
_REGISTRY: dict[str, ToolFn] = {}
_TOOL_SPECS: dict[str, MCPToolSpec] = {}


def register_tool(name: str, fn: ToolFn, spec: MCPToolSpec | None = None) -> None:
    resolved_spec = spec or P1_INTERNAL_TOOL_SPECS.get(name)
    if resolved_spec is None:
        raise ValueError(f"MCP tool spec is required: {name}")
    if resolved_spec.name != name:
        raise ValueError(f"MCP tool spec name mismatch: {name} != {resolved_spec.name}")
    _REGISTRY[name] = fn
    _TOOL_SPECS[name] = resolved_spec


def get_tool(name: str) -> ToolFn:
    if name not in _REGISTRY:
        raise KeyError(f"unknown MCP tool: {name}")
    return _REGISTRY[name]


def get_tool_spec(name: str) -> MCPToolSpec:
    if name not in _TOOL_SPECS:
        raise KeyError(f"unknown MCP tool spec: {name}")
    return _TOOL_SPECS[name]


def list_tools() -> list[str]:
    return sorted(_REGISTRY.keys())


def list_tool_specs() -> list[MCPToolSpec]:
    return [_TOOL_SPECS[name] for name in sorted(_TOOL_SPECS)]


def list_tool_metadata() -> list[dict[str, Any]]:
    return [spec.model_dump() for spec in list_tool_specs()]


def validate_registry_specs() -> None:
    missing_specs = sorted(set(_REGISTRY) - set(_TOOL_SPECS))
    missing_fns = sorted(set(_TOOL_SPECS) - set(_REGISTRY))
    if missing_specs or missing_fns:
        raise ValueError(f"MCP registry/spec mismatch: missing_specs={missing_specs}, missing_fns={missing_fns}")
    for name, spec in _TOOL_SPECS.items():
        if not spec.input_schema or not spec.output_schema or not spec.required_scopes:
            raise ValueError(f"MCP tool spec incomplete: {name}")


def bootstrap_tools() -> None:
    from app.mcp.tools.knia_tools import register_knia_tools
    from app.mcp.tools.cache_tools import register_cache_tools
    from app.mcp.tools.legal_rag_tools import register_legal_rag_tools
    from app.mcp.tools.evidence_guard_tools import register_evidence_guard_tools

    register_knia_tools()
    register_cache_tools()
    register_legal_rag_tools()
    register_evidence_guard_tools()
    validate_registry_specs()
