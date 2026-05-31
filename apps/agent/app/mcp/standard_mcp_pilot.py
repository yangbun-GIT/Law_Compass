from __future__ import annotations

from typing import Any

from app.mcp.tool_registry import bootstrap_tools, get_tool_spec


VERSION = "standard-mcp-pilot-design-v1"

PILOT_TOOL_CANDIDATES: dict[str, dict[str, Any]] = {
    "search_knia_json_rag_tool": {
        "category": "knia_search",
        "priority": 1,
        "reason": "Read-only KNIA search is directly tied to evidence quality and already has an internal executor contract.",
    },
    "legal_rag_search_tool": {
        "category": "legal_rag_search",
        "priority": 2,
        "reason": "Legal RAG search is useful for adapter compatibility but has broader evidence-source dependencies.",
    },
    "evidence_guard_tool": {
        "category": "evidence_guard",
        "priority": 3,
        "reason": "Evidence guard is deterministic, but it is less representative of external retrieval compatibility.",
    },
}


def build_standard_mcp_pilot_plan(preferred_tool_name: str = "search_knia_json_rag_tool") -> dict[str, Any]:
    """Build a standard MCP compatibility pilot plan without changing runtime behavior.

    P10-2 is a design step. It must keep the internal executor as the source of
    truth and avoid enabling a standard MCP runtime implicitly.
    """

    if preferred_tool_name not in PILOT_TOOL_CANDIDATES:
        raise ValueError(f"unsupported standard MCP pilot tool: {preferred_tool_name}")

    bootstrap_tools()
    spec = get_tool_spec(preferred_tool_name)
    candidate = PILOT_TOOL_CANDIDATES[preferred_tool_name]

    return {
        "version": VERSION,
        "pilot_tool_name": preferred_tool_name,
        "pilot_category": candidate["category"],
        "selection_reason": candidate["reason"],
        "candidate_table": PILOT_TOOL_CANDIDATES,
        "internal_executor_source_of_truth": True,
        "standard_mcp_adapter_enabled": False,
        "standard_mcp_runtime_changed": False,
        "compatibility_scope": "adapter_contract_only",
        "internal_tool_contract": {
            "name": spec.name,
            "description": spec.description,
            "input_schema": spec.input_schema,
            "output_schema": spec.output_schema,
            "required_scopes": spec.required_scopes,
            "timeout_ms": spec.timeout_ms,
            "side_effect": spec.side_effect,
            "safe_for_public_trace": spec.safe_for_public_trace,
        },
        "standard_mcp_adapter_contract": {
            "transport": "not_selected",
            "server_process": "not_created",
            "client_runtime": "not_created",
            "tool_name_mapping": {"standard_tool_name": spec.name, "internal_tool_name": spec.name},
            "input_mapping": "use_internal_input_schema_without_secret_values",
            "output_mapping": "use_internal_output_schema_and_failure_packet_mapping",
            "trace_mapping": "map request_id and trace_id to existing agent_trace and mcp_tool_calls metadata",
            "failure_mapping": "map MCP transport/tool errors to MCPToolErrorPacket before Agent aggregation",
        },
        "pilot_limits": [
            "Do not replace production internal executor calls.",
            "Do not introduce a standard MCP server, client, or transport in this step.",
            "Do not pass API keys, raw prompts, user passwords, original videos, or labels through adapter metadata.",
            "Do not use pilot output as final legal or fault-ratio judgment.",
        ],
        "acceptance_criteria": [
            "The chosen tool can be described by the internal MCPToolSpec without losing scope, timeout, side-effect, and trace metadata.",
            "A future adapter can map the same input/output schemas without changing Agent task packets.",
            "Adapter failure can be represented as MCPToolErrorPacket.",
            "The internal executor remains available as fallback and source of truth.",
        ],
        "next_step": "Decide in P10-3 whether the pilot solves a concrete problem beyond the internal executor.",
        "safe_metadata_only": True,
    }
