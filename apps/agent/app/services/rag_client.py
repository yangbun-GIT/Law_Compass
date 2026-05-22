from __future__ import annotations

from typing import Any

from app.services.legal.legal_evidence_retriever import build_legal_query, normalize_query, retrieve_legal_evidence
from app.services.scenario_search_terms import expand_query_text, scenario_search_terms
from app.services.static_legal_fallback import retrieve_static_legal_chunks


def retrieve_kb(query: str, limit: int = 5) -> list[dict[str, Any]]:
    result = retrieve_legal_evidence(
        scenario_type="general_collision",
        scenario_tags=[],
        query=normalize_query(query),
        limit=limit,
    )
    items = result["items"]
    if not items:
        items = retrieve_static_legal_chunks(query, limit=limit)
        for item in items:
            item.setdefault("retrieval_note", "static_fallback")
    return items[:limit]


def retrieve_for_scenario(
    *,
    scenario_type: str,
    scenario_tags: list[str],
    description_text: str,
    facts: dict[str, Any],
    selected_keywords: list[str],
    video_context: dict[str, Any] | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    base_query = build_legal_query(
        scenario_type=scenario_type,
        scenario_tags=scenario_tags,
        description_text=description_text,
        facts=facts,
        selected_keywords=selected_keywords,
        video_context=video_context,
    )
    query_terms = scenario_search_terms(
        scenario_type=scenario_type,
        scenario_tags=scenario_tags,
        facts=facts,
        selected_keywords=selected_keywords,
    )
    query = expand_query_text(
        base_query,
        scenario_type=scenario_type,
        scenario_tags=scenario_tags,
        facts=facts,
        selected_keywords=selected_keywords,
    )
    try:
        result = retrieve_legal_evidence(scenario_type=scenario_type, scenario_tags=scenario_tags, query=query, limit=limit)
        result.setdefault("retrieval_error", None)
    except Exception as exc:
        result = {
            "items": [],
            "cache_hit": False,
            "cache_key": None,
            "retrieval_error": _safe_error(exc),
        }
    if not result["items"]:
        fallback = retrieve_static_legal_chunks(query, limit=limit)
        for item in fallback:
            item.setdefault("retrieval_note", "static_fallback")
        result["items"] = fallback
        result["fallback_used"] = bool(fallback)
        result["static_support_count"] = len(fallback)
    else:
        support = retrieve_static_legal_chunks(query, limit=4)
        for item in support:
            item.setdefault("retrieval_note", "static_scenario_support")
        result["fallback_used"] = False
        result["static_support_count"] = len(support)
        result["items"] = _merge_static_support(result["items"], support, limit=limit)
    for item in result["items"]:
        item["cache_hit"] = result["cache_hit"]
        item["cache_key"] = result["cache_key"]
        item["query_expansion_terms"] = query_terms
    result["query_expansion_terms"] = query_terms
    return result


def _safe_error(exc: Exception) -> dict[str, str]:
    return {"type": exc.__class__.__name__, "message": "legal evidence retrieval failed"}


def _merge_static_support(items: list[dict[str, Any]], support: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    if not support:
        return items[:limit]
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(item: dict[str, Any]) -> None:
        key = str(item.get("chunk_id") or item.get("source_url") or item.get("title") or "")
        if key and key in seen:
            return
        if key:
            seen.add(key)
        merged.append(item)

    for item in items:
        add(item)
    for item in support:
        add(item)
    return merged[: min(len(merged), limit + 3)]
