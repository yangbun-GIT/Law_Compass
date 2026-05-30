import pytest

from app.mcp.tool_registry import (
    bootstrap_tools,
    get_tool_spec,
    list_tool_metadata,
    list_tool_specs,
    list_tools,
    register_tool,
    validate_registry_specs,
)


def test_bootstrapped_tools_have_schema_scope_and_trace_metadata():
    bootstrap_tools()

    tools = set(list_tools())
    specs = {spec.name: spec for spec in list_tool_specs()}

    assert tools == set(specs)
    assert tools
    for name, spec in specs.items():
        assert spec.input_schema["type"] == "object"
        assert spec.output_schema["type"] == "object"
        assert spec.required_scopes
        assert spec.timeout_ms > 0
        assert isinstance(spec.safe_for_public_trace, bool)
        assert spec.side_effect in {"none", "read", "write"}
        assert get_tool_spec(name).name == name

    metadata = list_tool_metadata()
    assert {item["name"] for item in metadata} == tools
    assert all("safe_for_public_trace" in item and "side_effect" in item for item in metadata)


def test_register_tool_requires_schema_metadata():
    with pytest.raises(ValueError):
        register_tool("unknown_tool_without_spec", lambda payload: payload)


def test_registry_validation_rejects_incomplete_state():
    bootstrap_tools()
    validate_registry_specs()
