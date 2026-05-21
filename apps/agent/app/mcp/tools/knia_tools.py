from __future__ import annotations

from typing import Any

from app.mcp.tool_registry import register_tool
from app.services.knia.knia_json_loader import import_knia_json
from app.services.knia.knia_json_menu_builder import get_myaccident_pages, get_myaccident_tree
from app.services.knia.knia_json_media_extractor import build_external_media_response
from app.services.rag.two_stage_cache import search_knia_json_cached
import os
import psycopg


def _db_url() -> str:
    return os.getenv("DATABASE_URL", "")


def import_knia_json_tool(payload: dict[str, Any]) -> dict[str, Any]:
    return import_knia_json(payload.get("path"), force=bool(payload.get("force")), rebuild_embeddings=bool(payload.get("rebuild_embeddings")))


def get_knia_myaccident_pages_tool(payload: dict[str, Any]) -> dict[str, Any]:
    return {"items": get_myaccident_pages()}


def get_knia_menu_tree_tool(payload: dict[str, Any]) -> dict[str, Any]:
    return get_myaccident_tree(int(payload.get("myaccident_no") or 1))


def search_knia_json_rag_tool(payload: dict[str, Any]) -> dict[str, Any]:
    return search_knia_json_cached(payload.get("query") or "", payload.get("accident_party_type"), limit=int(payload.get("limit") or 5))


def get_knia_media_by_query_tool(payload: dict[str, Any]) -> dict[str, Any]:
    query = f"%{payload.get('query') or ''}%"
    party = payload.get("accident_party_type")
    params: list[Any] = [query]
    where = "(title ILIKE %s OR source_url ILIKE %s)" if False else "(title ILIKE %s OR source_url ILIKE %s)"
    params = [query, query]
    if party and party != "all":
        where += " AND accident_party_type=%s"
        params.append(party)
    params.append(int(payload.get("limit") or 5))
    with psycopg.connect(_db_url()) as conn, conn.cursor() as cur:
        cur.execute(f"SELECT asset_type,source_url,embed_url,title,attribution FROM knia_json_media_assets WHERE {where} ORDER BY created_at DESC LIMIT %s", params)
        items = [build_external_media_response({"asset_type": r[0], "source_url": r[1], "embed_url": r[2], "title": r[3], "attribution": r[4]}) for r in cur.fetchall()]
    return {"items": items}


def register_knia_tools() -> None:
    register_tool("import_knia_json_tool", import_knia_json_tool)
    register_tool("get_knia_myaccident_pages_tool", get_knia_myaccident_pages_tool)
    register_tool("get_knia_menu_tree_tool", get_knia_menu_tree_tool)
    register_tool("search_knia_json_rag_tool", search_knia_json_rag_tool)
    register_tool("get_knia_media_by_query_tool", get_knia_media_by_query_tool)
