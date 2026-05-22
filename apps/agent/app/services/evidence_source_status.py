from __future__ import annotations

from typing import Any


VERSION = "evidence-source-status-v1"


def build_evidence_source_status(evidence_bundle: Any) -> dict[str, Any]:
    legal = _legal_status(_get(evidence_bundle, "retrieval", {}), _get(evidence_bundle, "legal_evidence", []))
    knia_chart = _knia_chart_status(_get(evidence_bundle, "knia_result", {}), _get(evidence_bundle, "knia_matches", []))
    knia_json = _knia_json_status(_get(evidence_bundle, "knia_json_result", {}), _get(evidence_bundle, "knia_json_evidence", []))
    recovery_actions = _recovery_actions(legal, knia_chart, knia_json)
    return {
        "version": VERSION,
        "overall_status": _overall_status(legal, knia_chart, knia_json),
        "sources": {
            "legal_rag": legal,
            "knia_chart_match": knia_chart,
            "knia_json_detail": knia_json,
        },
        "recovery_actions": recovery_actions,
    }


def _legal_status(retrieval: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    fallback_count = sum(1 for item in items if str(item.get("retrieval_note") or "").startswith("static"))
    error = retrieval.get("retrieval_error")
    return _drop_none(
        {
            "name": "legal_rag",
            "status": _source_status(len(items), bool(error), bool(retrieval.get("fallback_used"))),
            "item_count": len(items),
            "cache_hit": retrieval.get("cache_hit"),
            "cache_key": retrieval.get("cache_key"),
            "fallback_used": bool(retrieval.get("fallback_used") or fallback_count),
            "static_support_count": retrieval.get("static_support_count", fallback_count),
            "query_expansion_terms": retrieval.get("query_expansion_terms") or [],
            "failure_observation": _failure_observation("legal_rag", error),
        }
    )


def _knia_chart_status(knia_result: dict[str, Any], matches: list[dict[str, Any]]) -> dict[str, Any]:
    error = knia_result.get("lookup_error")
    return _drop_none(
        {
            "name": "knia_chart_match",
            "status": _source_status(len(matches), bool(error), False),
            "item_count": len(matches),
            "cache_hit": knia_result.get("cache_hit"),
            "cache_key": knia_result.get("cache_key"),
            "accident_party_type": knia_result.get("accident_party_type"),
            "query_expansion_terms": knia_result.get("query_expansion_terms") or [],
            "failure_observation": _failure_observation("knia_chart_match", error),
        }
    )


def _knia_json_status(knia_json_result: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    cache = knia_json_result.get("cache") or {}
    disabled_reason = cache.get("disabled_reason")
    error = {"type": "disabled", "reason": disabled_reason} if disabled_reason else None
    return _drop_none(
        {
            "name": "knia_json_detail",
            "status": _source_status(len(items), bool(error), False),
            "item_count": len(items),
            "exact_cache_hit": cache.get("exact_hit"),
            "semantic_cache_hit": cache.get("semantic_hit"),
            "cache_key": cache.get("key"),
            "disabled_reason": disabled_reason,
            "failure_observation": _failure_observation("knia_json_detail", error),
        }
    )


def _source_status(item_count: int, has_error: bool, fallback_used: bool) -> str:
    if item_count > 0 and fallback_used:
        return "degraded_with_fallback"
    if item_count > 0:
        return "ready"
    if has_error:
        return "unavailable"
    return "empty"


def _overall_status(legal: dict[str, Any], knia_chart: dict[str, Any], knia_json: dict[str, Any]) -> str:
    statuses = {legal.get("status"), knia_chart.get("status"), knia_json.get("status")}
    if legal.get("item_count", 0) > 0 and (knia_chart.get("item_count", 0) > 0 or knia_json.get("item_count", 0) > 0):
        if any(status in {"degraded_with_fallback", "unavailable"} for status in statuses):
            return "degraded"
        return "ready"
    if legal.get("item_count", 0) > 0 or knia_chart.get("item_count", 0) > 0 or knia_json.get("item_count", 0) > 0:
        return "partial"
    return "unavailable"


def _recovery_actions(*sources: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    for source in sources:
        status = source.get("status")
        if status == "unavailable":
            actions.append(f"check_{source.get('name', 'evidence_source')}_availability")
        if source.get("fallback_used"):
            actions.append("refresh_or_rebuild_legal_kb")
        if source.get("disabled_reason") == "DATABASE_URL missing":
            actions.append("configure_database_url")
    if not actions:
        return []
    return list(dict.fromkeys(actions))


def _failure_observation(source: str, error: Any) -> dict[str, Any] | None:
    if not error:
        return None
    if isinstance(error, dict):
        reason = error.get("reason") or error.get("message") or error.get("type")
        error_type = error.get("type") or "evidence_source_error"
    else:
        reason = str(error)
        error_type = "evidence_source_error"
    return {
        "type": "evidence_source_unavailable",
        "source": source,
        "reason": str(reason or "unknown"),
        "error_type": str(error_type or "unknown"),
        "recoverable": True,
    }


def _get(obj: Any, name: str, default: Any) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _drop_none(value: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in value.items() if v is not None}
