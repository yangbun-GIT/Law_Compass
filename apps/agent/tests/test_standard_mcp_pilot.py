from app.mcp.standard_mcp_pilot import build_standard_mcp_pilot_plan


def test_standard_mcp_pilot_defaults_to_knia_search_without_runtime_change():
    plan = build_standard_mcp_pilot_plan()

    assert plan["pilot_tool_name"] == "search_knia_json_rag_tool"
    assert plan["internal_executor_source_of_truth"] is True
    assert plan["standard_mcp_adapter_enabled"] is False
    assert plan["standard_mcp_runtime_changed"] is False
    assert plan["compatibility_scope"] == "adapter_contract_only"
    assert plan["safe_metadata_only"] is True


def test_standard_mcp_pilot_preserves_internal_tool_contract():
    plan = build_standard_mcp_pilot_plan("search_knia_json_rag_tool")
    contract = plan["internal_tool_contract"]

    assert contract["name"] == "search_knia_json_rag_tool"
    assert contract["side_effect"] == "read"
    assert contract["safe_for_public_trace"] is True
    assert "knia.read" in contract["required_scopes"]
    assert contract["input_schema"]["required"] == ["query"]


def test_standard_mcp_pilot_maps_failures_to_existing_error_packet():
    plan = build_standard_mcp_pilot_plan("legal_rag_search_tool")
    adapter_contract = plan["standard_mcp_adapter_contract"]

    assert adapter_contract["failure_mapping"] == "map MCP transport/tool errors to MCPToolErrorPacket before Agent aggregation"
    assert plan["internal_executor_source_of_truth"] is True


def test_standard_mcp_pilot_rejects_unsupported_tool():
    try:
        build_standard_mcp_pilot_plan("unknown_tool")
    except ValueError as exc:
        assert "unsupported standard MCP pilot tool" in str(exc)
    else:
        raise AssertionError("unsupported pilot tool must be rejected")
