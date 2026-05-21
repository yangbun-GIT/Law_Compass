from __future__ import annotations
from app.mcp.tool_registry import register_tool
from app.services.rag.evidence_gate import gate_public_evidence

def evidence_guard_tool(payload):
    return {"items": gate_public_evidence(payload.get("items") or [])}

def register_evidence_guard_tools() -> None:
    register_tool("evidence_guard_tool", evidence_guard_tool)
