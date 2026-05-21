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
    result = retrieve_legal_evidence(scenario_type=scenario_type, scenario_tags=scenario_tags, query=query, limit=limit)
    if not result["items"]:
        fallback = retrieve_static_legal_chunks(query, limit=limit)
        for item in fallback:
            item.setdefault("retrieval_note", "static_fallback")
        result["items"] = fallback
    for item in result["items"]:
        item["cache_hit"] = result["cache_hit"]
        item["cache_key"] = result["cache_key"]
        item["query_expansion_terms"] = query_terms
    result["query_expansion_terms"] = query_terms
    return result
