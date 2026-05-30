import time

from app.mcp.tool_executor import execute_tool
from app.mcp.tool_registry import register_tool, unregister_tool
from app.services.agent_contracts import MCPToolSpec


def test_execute_tool_rejects_invalid_payload_as_failure_packet():
    result = execute_tool("legal_rag_search_tool", {}, trace_id="trace-test")

    assert result["status"] == "failed"
    assert result["error_code"] == "payload_required_field_missing"
    assert result["trace_id"] == "trace-test"
    assert result["metadata"]["safe_metadata_only"] is True


def test_execute_tool_rejects_missing_scope():
    result = execute_tool("legal_rag_search_tool", {"query": "교통사고"}, granted_scopes=[])

    assert result["status"] == "failed"
    assert result["error_code"] == "tool_scope_denied"
    assert "교통사고" not in str(result)


def test_execute_tool_sanitizes_internal_exception():
    def failing_tool(payload):
        raise RuntimeError("raw secret stack should not leak")

    try:
        register_tool(
            "_test_failing_tool",
            failing_tool,
            spec=MCPToolSpec(
                name="_test_failing_tool",
                description="test only",
                input_schema={"type": "object", "properties": {}},
                output_schema={"type": "object", "properties": {}},
                required_scopes=["legal.read"],
                timeout_ms=5000,
            ),
        )

        result = execute_tool("_test_failing_tool", {}, granted_scopes=["legal.read"])

        assert result["status"] == "failed"
        assert result["error_code"] == "tool_execution_failed"
        assert "raw secret stack" not in str(result)
        assert result["metadata"]["error_type"] == "RuntimeError"
    finally:
        unregister_tool("_test_failing_tool")


def test_execute_tool_returns_timeout_packet_when_elapsed_exceeds_spec():
    def slow_tool(payload):
        time.sleep(0.005)
        return {"ok": True}

    try:
        register_tool(
            "_test_slow_tool",
            slow_tool,
            spec=MCPToolSpec(
                name="_test_slow_tool",
                description="test only",
                input_schema={"type": "object", "properties": {}},
                output_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
                required_scopes=["legal.read"],
                timeout_ms=1,
            ),
        )

        result = execute_tool("_test_slow_tool", {}, granted_scopes=["legal.read"])

        assert result["status"] == "failed"
        assert result["error_code"] == "tool_timeout"
        assert result["retryable"] is True
    finally:
        unregister_tool("_test_slow_tool")
