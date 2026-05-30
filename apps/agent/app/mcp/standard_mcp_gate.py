from __future__ import annotations

from typing import Any

from app.mcp.tool_registry import bootstrap_tools, list_tool_specs


VERSION = "standard-mcp-adoption-gate-v1"

EXTERNAL_TOOL_OR_AGENT_THRESHOLD = 3

ADOPTION_CONDITIONS: dict[str, dict[str, Any]] = {
    "external_tool_or_agent_growth": {
        "metric": "external_tool_count + external_agent_count",
        "threshold": EXTERNAL_TOOL_OR_AGENT_THRESHOLD,
        "reason": "Three or more external tools/agents require protocol-level lifecycle and compatibility review.",
    },
    "permission_split_insufficient": {
        "metric": "permission_split_insufficient",
        "threshold": True,
        "reason": "The internal executor scope model no longer separates permissions clearly enough.",
    },
    "cross_host_reuse_required": {
        "metric": "cross_host_reuse_required",
        "threshold": True,
        "reason": "The same tool must be reused by another host or runtime.",
    },
    "standard_mcp_client_required": {
        "metric": "standard_mcp_client_required",
        "threshold": True,
        "reason": "A standard MCP client integration is an explicit product or infrastructure requirement.",
    },
    "independent_process_isolation_required": {
        "metric": "independent_process_isolation_required",
        "threshold": True,
        "reason": "Tool isolation, security, or fault containment requires an independent process boundary.",
    },
}


def evaluate_standard_mcp_adoption(metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a deterministic adoption decision for standard MCP Host/Client/Server.

    P3-4 is only a decision gate. It must not introduce a standard MCP runtime or
    change tool execution behavior.
    """

    metrics = metrics or {}
    bootstrap_tools()
    registered_tool_count = len(list_tool_specs())
    external_tool_count = _safe_int(metrics.get("external_tool_count"))
    external_agent_count = _safe_int(metrics.get("external_agent_count"))

    met_conditions: list[str] = []
    if external_tool_count + external_agent_count >= EXTERNAL_TOOL_OR_AGENT_THRESHOLD:
        met_conditions.append("external_tool_or_agent_growth")
    for condition, metric_name in (
        ("permission_split_insufficient", "permission_split_insufficient"),
        ("cross_host_reuse_required", "cross_host_reuse_required"),
        ("standard_mcp_client_required", "standard_mcp_client_required"),
        ("independent_process_isolation_required", "independent_process_isolation_required"),
    ):
        if bool(metrics.get(metric_name)):
            met_conditions.append(condition)

    should_adopt = bool(met_conditions)
    return {
        "version": VERSION,
        "recommendation": "adopt_standard_mcp" if should_adopt else "keep_internal_mcp_like",
        "should_adopt_standard_mcp": should_adopt,
        "registered_internal_tool_count": registered_tool_count,
        "external_tool_count": external_tool_count,
        "external_agent_count": external_agent_count,
        "met_conditions": met_conditions,
        "condition_table": ADOPTION_CONDITIONS,
        "next_review_trigger": (
            "prepare_standard_mcp_migration_plan"
            if should_adopt
            else "review_again_when_external_tools_agents_or_isolation_requirements_change"
        ),
        "safe_metadata_only": True,
        "standard_mcp_runtime_changed": False,
    }


def evaluate_standard_mcp_gate(metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    """Backward-compatible alias for the P3-4 decision gate."""

    return evaluate_standard_mcp_adoption(metrics)


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0
