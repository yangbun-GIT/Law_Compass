from __future__ import annotations

import json
import time
import uuid
from typing import Any

import os
import psycopg

from app.mcp.tool_registry import bootstrap_tools, get_tool

_BOOTSTRAPPED = False


def _db_url() -> str:
    return os.getenv("DATABASE_URL", "")


def execute_tool(tool_name: str, payload: dict[str, Any], trace_id: str | None = None) -> dict[str, Any]:
    global _BOOTSTRAPPED
    if not _BOOTSTRAPPED:
        bootstrap_tools(); _BOOTSTRAPPED = True
    trace = trace_id or str(uuid.uuid4())
    started = time.perf_counter()
    status = "success"
    error = None
    output: dict[str, Any] = {}
    try:
        output = get_tool(tool_name)(payload or {})
        return output
    except Exception as exc:
        status = "failed"; error = str(exc)
        raise
    finally:
        latency = int((time.perf_counter() - started) * 1000)
        url = _db_url()
        if url:
            try:
                with psycopg.connect(url) as conn, conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO mcp_tool_calls(trace_id,tool_name,input_summary,output_summary,status,latency_ms,error_message,metadata) VALUES(%s,%s,%s,%s,%s,%s,%s,%s::jsonb)",
                        (trace, tool_name, json.dumps(payload, ensure_ascii=False)[:1000], json.dumps(output, ensure_ascii=False)[:1000], status, latency, error, json.dumps({}, ensure_ascii=False)),
                    )
                    conn.commit()
            except Exception:
                pass
