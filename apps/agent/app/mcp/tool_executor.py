from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any

import psycopg

from app.mcp.tool_registry import bootstrap_tools, get_tool, get_tool_spec
from app.services.agent_contracts import MCPToolSpec, build_tool_error_packet


_BOOTSTRAPPED = False
SENSITIVE_MARKERS = ("password", "secret", "api_key", "token", "refresh_token", ".env")


def _db_url() -> str:
    return os.getenv("DATABASE_URL", "")


def execute_tool(
    tool_name: str,
    payload: dict[str, Any] | None,
    trace_id: str | None = None,
    *,
    granted_scopes: list[str] | None = None,
    raise_on_error: bool = False,
) -> dict[str, Any]:
    global _BOOTSTRAPPED
    if not _BOOTSTRAPPED:
        bootstrap_tools()
        _BOOTSTRAPPED = True

    trace = trace_id or str(uuid.uuid4())
    started = time.perf_counter()
    status = "success"
    error_message = None
    output: dict[str, Any] = {}
    safe_payload = payload or {}

    try:
        spec = get_tool_spec(tool_name)
        _validate_payload(spec, safe_payload)
        _validate_scope(spec, granted_scopes)
        output = get_tool(tool_name)(safe_payload)
        _validate_output(spec, output)
        latency = _latency_ms(started)
        if latency > spec.timeout_ms:
            output = _failure_packet(
                tool_name,
                trace_id=trace,
                error_code="tool_timeout",
                safe_message="Tool execution exceeded the configured timeout.",
                retryable=True,
                metadata={"timeout_ms": spec.timeout_ms, "latency_ms": latency},
            )
            status = "failed"
            error_message = "tool_timeout"
        return output
    except Exception as exc:
        status = "failed"
        error_message = _safe_error_code(exc)
        output = _failure_packet(
            tool_name,
            trace_id=trace,
            error_code=error_message,
            safe_message=_safe_error_message(error_message),
            retryable=error_message in {"tool_timeout", "tool_execution_failed"},
            metadata={"error_type": type(exc).__name__},
        )
        if raise_on_error:
            raise
        return output
    finally:
        _record_tool_call(
            trace_id=trace,
            tool_name=tool_name,
            payload=safe_payload,
            output=output,
            status=status,
            latency_ms=_latency_ms(started),
            error_message=error_message,
        )


def _validate_payload(spec: MCPToolSpec, payload: dict[str, Any]) -> None:
    schema = spec.input_schema or {}
    if schema.get("type") == "object" and not isinstance(payload, dict):
        raise ValueError("payload_type_invalid")
    required = schema.get("required") or []
    for field in required:
        if field not in payload or payload.get(field) is None:
            raise ValueError("payload_required_field_missing")
    properties = schema.get("properties") or {}
    for field, rules in properties.items():
        if field not in payload or payload.get(field) is None:
            continue
        if not _matches_type(payload.get(field), str(_dict(rules).get("type") or "")):
            raise ValueError("payload_field_type_invalid")


def _validate_scope(spec: MCPToolSpec, granted_scopes: list[str] | None) -> None:
    if granted_scopes is None:
        return
    granted = set(granted_scopes)
    missing = [scope for scope in spec.required_scopes if scope not in granted]
    if missing:
        raise PermissionError("tool_scope_denied")


def _validate_output(spec: MCPToolSpec, output: Any) -> None:
    schema = spec.output_schema or {}
    if schema.get("type") == "object" and not isinstance(output, dict):
        raise ValueError("tool_output_schema_invalid")
    if not isinstance(output, dict):
        return
    required = schema.get("required") or []
    for field in required:
        if field not in output or output.get(field) is None:
            raise ValueError("tool_output_schema_invalid")
    properties = schema.get("properties") or {}
    for field, rules in properties.items():
        if field not in output or output.get(field) is None:
            continue
        if not _matches_type(output.get(field), str(_dict(rules).get("type") or "")):
            raise ValueError("tool_output_schema_invalid")


def _matches_type(value: Any, expected: str) -> bool:
    if not expected:
        return True
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return True


def _failure_packet(
    tool_name: str,
    *,
    trace_id: str,
    error_code: str,
    safe_message: str,
    retryable: bool,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    packet = build_tool_error_packet(
        tool_name,
        safe_message,
        error_code=error_code,
        retryable=retryable,
        trace_id=trace_id,
    )
    packet["metadata"] = {
        **metadata,
        "safe_metadata_only": True,
        "public_message": safe_message,
    }
    return packet


def _safe_error_code(exc: Exception) -> str:
    if isinstance(exc, PermissionError):
        return "tool_scope_denied"
    if isinstance(exc, ValueError) and str(exc) in {
        "payload_type_invalid",
        "payload_required_field_missing",
        "payload_field_type_invalid",
        "tool_output_schema_invalid",
    }:
        return str(exc)
    if isinstance(exc, KeyError):
        return "tool_not_found"
    return "tool_execution_failed"


def _safe_error_message(error_code: str) -> str:
    return {
        "payload_type_invalid": "Tool payload must be an object.",
        "payload_required_field_missing": "Tool payload is missing a required field.",
        "payload_field_type_invalid": "Tool payload field type is invalid.",
        "tool_output_schema_invalid": "Tool output did not match the declared schema.",
        "tool_scope_denied": "Tool execution scope is not granted.",
        "tool_not_found": "Requested tool is not registered.",
        "tool_execution_failed": "Tool execution failed with a sanitized internal error.",
    }.get(error_code, "Tool execution failed.")


def _record_tool_call(
    *,
    trace_id: str,
    tool_name: str,
    payload: dict[str, Any],
    output: dict[str, Any],
    status: str,
    latency_ms: int,
    error_message: str | None,
) -> None:
    url = _db_url()
    if not url:
        return
    try:
        with psycopg.connect(url) as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO mcp_tool_calls(trace_id,tool_name,input_summary,output_summary,status,latency_ms,error_message,metadata) VALUES(%s,%s,%s,%s,%s,%s,%s,%s::jsonb)",
                (
                    trace_id,
                    tool_name,
                    _json_summary(payload),
                    _json_summary(output),
                    status,
                    latency_ms,
                    error_message,
                    json.dumps({"safe_metadata_only": True}, ensure_ascii=False),
                ),
            )
            conn.commit()
    except Exception:
        pass


def _json_summary(value: dict[str, Any]) -> str:
    return json.dumps(_scrub_sensitive(value), ensure_ascii=False, default=str)[:1000]


def _scrub_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if any(marker in str(key).lower() for marker in SENSITIVE_MARKERS):
                cleaned[str(key)] = "[redacted]"
            else:
                cleaned[str(key)] = _scrub_sensitive(item)
        return cleaned
    if isinstance(value, list):
        return [_scrub_sensitive(item) for item in value]
    return value


def _latency_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
