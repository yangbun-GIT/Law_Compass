from __future__ import annotations
from app.mcp.tool_executor import execute_tool

print(execute_tool("get_knia_myaccident_pages_tool", {}, "test-mcp"))
print(execute_tool("get_knia_menu_tree_tool", {"myaccident_no": 1}, "test-mcp"))
result = execute_tool("search_knia_json_rag_tool", {"query": "후미추돌 정차 중 뒤차 추돌", "accident_party_type": "car_vs_car", "limit": 3}, "test-mcp")
print(result)
assert result["items"], "MCP RAG 결과 없음"
media = execute_tool("get_knia_media_by_query_tool", {"query": "myaccident", "limit": 3}, "test-mcp")
print(media)
print("MCP KNIA JSON tools test passed")
