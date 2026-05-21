from __future__ import annotations
from app.mcp.tool_registry import register_tool
from app.services.rag_client import retrieve_kb

def legal_rag_search_tool(payload):
    return {"items": retrieve_kb(payload.get("query") or "", int(payload.get("limit") or 5))}

def register_legal_rag_tools() -> None:
    register_tool("legal_rag_search_tool", legal_rag_search_tool)
