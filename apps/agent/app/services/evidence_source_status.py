from __future__ import annotations

from collections import Counter
from typing import Any


VERSION = "evidence-source-status-v2"
ORIGINAL_SOURCE_QUALITIES = {"collected_original"}
STATIC_SOURCE_QUALITIES = {"static_support"}
CURATED_SOURCE_QUALITIES = {"curated_reference", "practice_reference"}


def build_evidence_source_status(evidence_bundle: Any) -> dict[str, Any]:
    legal = _legal_status(_get(evidence_bundle, "retrieval", {}), _get(evidence_bundle, "legal_evidence", []))
    knia_chart = _knia_chart_status(_get(evidence_bundle, "knia_result", {}), _get(evidence_bundle, "knia_matches", []))
    knia_json = _knia_json_status(_get(evidence_bundle, "knia_json_result", {}), _get(evidence_bundle, "knia_json_evidence", []))
    recovery_actions = _recovery_actions(legal, knia_chart, knia_json)
    source_quality_totals = _merge_source_quality_counts(legal, knia_chart, knia_json)
    source_counts = _source_counts_from_quality(source_quality_totals)
    return {
        "version": VERSION,
        "overall_status": _overall_status(legal, knia_chart, knia_json),
        "source_quality_totals": source_quality_totals,
        **source_counts,
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
    quality = _source_quality_summary(items, default_quality="static_support" if fallback_count else "curated_reference")
    static_support_count = max(
        int(quality.get("static_support_count") or 0),
        int(retrieval.get("static_support_count") or fallback_count or 0),
    )
    return _drop_none(
        {
            "name": "legal_rag",
            "status": _source_status(len(items), bool(error), bool(retrieval.get("fallback_used"))),
            "item_count": len(items),
            **quality,
            "cache_hit": retrieval.get("cache_hit"),
            "cache_key": retrieval.get("cache_key"),
            "fallback_used": bool(retrieval.get("fallback_used") or fallback_count),
            "static_support_count": static_support_count,
            "query_expansion_terms": retrieval.get("query_expansion_terms") or [],
            "failure_observation": _failure_observation("legal_rag", error),
        }
    )


def _knia_chart_status(knia_result: dict[str, Any], matches: list[dict[str, Any]]) -> dict[str, Any]:
    error = knia_result.get("lookup_error")
    quality = _source_quality_summary(matches, default_quality="curated_reference")
    return _drop_none(
        {
            "name": "knia_chart_match",
            "status": _source_status(len(matches), bool(error), False),
            "item_count": len(matches),
            **quality,
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
    quality = _source_quality_summary(items, default_quality="collected_original")
    return _drop_none(
        {
            "name": "knia_json_detail",
            "status": _source_status(len(items), bool(error), False),
            "item_count": len(items),
            **quality,
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
        if source.get("static_support_count", 0) > 0:
            actions.append("expand_original_source_collection")
        if source.get("coverage_status") in {"fallback_only", "reference_only"}:
            actions.append(f"add_original_sources_for_{source.get('name', 'evidence_source')}")
        if source.get("disabled_reason") == "DATABASE_URL missing":
            actions.append("configure_database_url")
    if not actions:
        return []
    return list(dict.fromkeys(actions))


def _source_quality_summary(items: list[dict[str, Any]], default_quality: str) -> dict[str, Any]:
    counts = Counter(_source_quality_key(item, default_quality) for item in items if isinstance(item, dict))
    counts = Counter({key: value for key, value in counts.items() if key})
    source_counts = _source_counts_from_quality(dict(sorted(counts.items())))
    source_url_count = sum(1 for item in items if isinstance(item, dict) and _source_url(item))
    item_count = len(items)
    original_count = int(source_counts["original_or_collected_count"])
    static_count = int(source_counts["static_support_count"])
    coverage_status = _coverage_status(item_count, original_count, static_count, source_url_count)
    return {
        "source_quality_counts": dict(sorted(counts.items())),
        **source_counts,
        "source_url_count": source_url_count,
        "original_source_ratio": round(original_count / item_count, 3) if item_count else 0,
        "coverage_status": coverage_status,
    }


def _source_quality_key(item: dict[str, Any], default_quality: str) -> str:
    raw = str(item.get("source_quality") or "").strip()
    if raw:
        return raw
    retrieval_note = str(item.get("retrieval_note") or item.get("source_note") or "").lower()
    if retrieval_note.startswith("static") or "static" in retrieval_note:
        return "static_support"
    source_url = _source_url(item)
    if source_url:
        if "accident.knia.or.kr" in source_url or "law.go.kr" in source_url:
            return "collected_original"
        return "curated_reference"
    return default_quality


def _source_url(item: dict[str, Any]) -> str:
    for key in ("source_url", "url", "origin_url"):
        value = str(item.get(key) or "").strip()
        if value.startswith(("http://", "https://")):
            return value
    return ""


def _source_counts_from_quality(counts: dict[str, int]) -> dict[str, int]:
    return {
        "original_or_collected_count": sum(int(counts.get(key) or 0) for key in ORIGINAL_SOURCE_QUALITIES),
        "static_support_count": sum(int(counts.get(key) or 0) for key in STATIC_SOURCE_QUALITIES),
        "curated_reference_count": sum(int(counts.get(key) or 0) for key in CURATED_SOURCE_QUALITIES),
    }


def _merge_source_quality_counts(*sources: dict[str, Any]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for source in sources:
        counts.update(source.get("source_quality_counts") or {})
    return dict(sorted(counts.items()))


def _coverage_status(item_count: int, original_count: int, static_count: int, source_url_count: int) -> str:
    if item_count <= 0:
        return "empty"
    if original_count > 0 and static_count == 0:
        return "original_source_ready"
    if original_count > 0:
        return "mixed_with_static_support"
    if static_count > 0:
        return "fallback_only"
    if source_url_count > 0:
        return "linked_reference"
    return "reference_only"


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
