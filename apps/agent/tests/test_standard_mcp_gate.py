from app.mcp.standard_mcp_gate import ADOPTION_CONDITIONS, evaluate_standard_mcp_adoption


def test_standard_mcp_gate_keeps_internal_layer_without_trigger_conditions():
    decision = evaluate_standard_mcp_adoption({})

    assert decision["recommendation"] == "keep_internal_mcp_like"
    assert decision["should_adopt_standard_mcp"] is False
    assert decision["standard_mcp_runtime_changed"] is False
    assert decision["safe_metadata_only"] is True
    assert decision["registered_internal_tool_count"] > 0
    assert decision["met_conditions"] == []
    assert set(decision["condition_table"]) == set(ADOPTION_CONDITIONS)


def test_standard_mcp_gate_recommends_adoption_when_external_tool_or_agent_count_reaches_threshold():
    decision = evaluate_standard_mcp_adoption({"external_tool_count": 2, "external_agent_count": 1})

    assert decision["recommendation"] == "adopt_standard_mcp"
    assert decision["should_adopt_standard_mcp"] is True
    assert decision["met_conditions"] == ["external_tool_or_agent_growth"]


def test_standard_mcp_gate_recommends_adoption_for_security_or_protocol_requirements():
    decision = evaluate_standard_mcp_adoption(
        {
            "permission_split_insufficient": True,
            "cross_host_reuse_required": True,
            "standard_mcp_client_required": True,
            "independent_process_isolation_required": True,
        }
    )

    assert decision["should_adopt_standard_mcp"] is True
    assert set(decision["met_conditions"]) == {
        "permission_split_insufficient",
        "cross_host_reuse_required",
        "standard_mcp_client_required",
        "independent_process_isolation_required",
    }


def test_standard_mcp_gate_handles_untrusted_metric_shapes_safely():
    decision = evaluate_standard_mcp_adoption({"external_tool_count": "not-a-number", "external_agent_count": -4})

    assert decision["external_tool_count"] == 0
    assert decision["external_agent_count"] == 0
    assert decision["should_adopt_standard_mcp"] is False
