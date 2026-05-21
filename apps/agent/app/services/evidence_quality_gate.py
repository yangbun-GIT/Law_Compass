from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvidenceProfile:
    tags: tuple[str, ...]
    terms: tuple[str, ...]


SCENARIO_PROFILES: dict[str, EvidenceProfile] = {
    "rear_end_collision": EvidenceProfile(
        tags=("rear_end", "safe_distance"),
        terms=("rear-end", "rear end", "추돌", "후방", "안전거리", "정차", "급정거"),
    ),
    "lane_change_collision": EvidenceProfile(
        tags=("lane_change",),
        terms=("lane change", "차선변경", "진로변경", "끼어들", "방향지시"),
    ),
    "intersection_signal_violation": EvidenceProfile(
        tags=("signal_violation", "intersection"),
        terms=("signal", "red light", "intersection", "신호위반", "교차로", "빨간불", "적색"),
    ),
    "pedestrian_crosswalk_accident": EvidenceProfile(
        tags=("pedestrian", "crosswalk"),
        terms=("pedestrian", "crosswalk", "보행자", "횡단보도"),
    ),
    "school_zone_child_accident": EvidenceProfile(
        tags=("school_zone", "child"),
        terms=("school zone", "child", "어린이보호구역", "스쿨존", "어린이"),
    ),
    "bicycle_collision": EvidenceProfile(
        tags=("bicycle",),
        terms=("bicycle", "자전거"),
    ),
    "object_collision": EvidenceProfile(
        tags=("object",),
        terms=("object", "시설물", "고정물", "물체"),
    ),
    "single_vehicle_accident": EvidenceProfile(
        tags=("single_vehicle",),
        terms=("single vehicle", "단독사고", "공작물"),
    ),
    "general_collision": EvidenceProfile(tags=(), terms=()),
}


def evaluate_evidence_quality(
    *,
    scenario_type: str,
    evidence: list[dict[str, Any]],
    missing_fields: list[str],
) -> dict[str, Any]:
    count = len(evidence)
    avg_score = sum(float(item.get("score", 0) or 0) for item in evidence) / count if count else 0.0
    profile = SCENARIO_PROFILES.get(scenario_type) or SCENARIO_PROFILES["general_collision"]
    family_counts = _family_counts(evidence)

    matched_items: list[dict[str, Any]] = []
    matched_terms: set[str] = set()
    matched_tags: set[str] = set()
    for item in evidence:
        item_match = _match_item(item, profile)
        if not item_match["matched"]:
            continue
        matched_items.append(
            {
                "ref_id": _item_ref(item),
                "family": _family(item),
                "matched_terms": item_match["terms"],
                "matched_tags": item_match["tags"],
            }
        )
        matched_terms.update(item_match["terms"])
        matched_tags.update(item_match["tags"])

    missing_families = []
    if count and family_counts.get("legal", 0) == 0:
        missing_families.append("legal")

    weak_points = []
    if count == 0:
        weak_points.append("검색된 근거가 없어 사고 판단을 확정할 수 없습니다.")
    if count and family_counts.get("legal", 0) == 0:
        weak_points.append("법령 또는 판례 계열 근거가 부족합니다.")
    if profile.tags or profile.terms:
        if not matched_items:
            weak_points.append("사고 유형과 직접 맞는 근거 신호를 확인하지 못했습니다.")
        elif len(matched_items) < 2:
            weak_points.append("사고 유형과 맞는 근거가 1건뿐이라 추가 확인이 필요합니다.")
    if missing_fields:
        weak_points.append("필수 사고 사실 일부가 비어 있어 근거 해석의 신뢰도가 낮아질 수 있습니다.")
    if avg_score and avg_score < 0.25:
        weak_points.append("검색 점수가 낮아 근거 재검토가 필요합니다.")

    coverage_level = _coverage_level(
        evidence_count=count,
        average_score=avg_score,
        relevant_count=len(matched_items),
        has_legal=family_counts.get("legal", 0) > 0,
        has_missing_fields=bool(missing_fields),
        has_profile=bool(profile.tags or profile.terms),
    )

    return {
        "coverage_level": coverage_level,
        "scenario_type": scenario_type,
        "scenario_relevant_count": len(matched_items),
        "evidence_family_counts": family_counts,
        "matched_evidence": matched_items[:8],
        "matched_terms": sorted(matched_terms),
        "matched_tags": sorted(matched_tags),
        "missing_evidence_families": missing_families,
        "weak_points": weak_points,
    }


def _coverage_level(
    *,
    evidence_count: int,
    average_score: float,
    relevant_count: int,
    has_legal: bool,
    has_missing_fields: bool,
    has_profile: bool,
) -> str:
    if evidence_count == 0:
        return "low"
    if not has_profile:
        if evidence_count >= 3 and has_legal and average_score >= 0.25 and not has_missing_fields:
            return "medium"
        return "low"
    if relevant_count >= 2 and evidence_count >= 4 and has_legal and average_score >= 0.3 and not has_missing_fields:
        return "high"
    if relevant_count >= 1 and has_legal:
        return "medium"
    if evidence_count >= 3 and has_legal:
        return "medium"
    return "low"


def _match_item(item: dict[str, Any], profile: EvidenceProfile) -> dict[str, Any]:
    tags = {_normalize_token(value) for value in _list_values(item.get("scenario_tags"))}
    tags.update(_normalize_token(value) for value in _list_values(item.get("keywords")))
    tags.update(_normalize_token(value) for value in _list_values(item.get("display_tags")))
    tags.update(_normalize_token(value) for value in _list_values(item.get("used_for")))

    text = _search_text(item)
    matched_tags = sorted(tag for tag in profile.tags if _normalize_token(tag) in tags or tag.lower() in text)
    matched_terms = sorted(term for term in profile.terms if term.lower() in text)

    return {
        "matched": bool(matched_tags or matched_terms),
        "tags": matched_tags,
        "terms": matched_terms,
    }


def _family_counts(evidence: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"legal": 0, "knia": 0, "general": 0}
    for item in evidence:
        family = _family(item)
        counts[family] = counts.get(family, 0) + 1
    return counts


def _family(item: dict[str, Any]) -> str:
    source_type = str(item.get("source_type") or "").lower()
    source = " ".join(
        [
            str(item.get("source") or ""),
            str(item.get("title") or ""),
            str(item.get("source_url") or ""),
            str(item.get("law_name") or ""),
        ]
    ).lower()
    if source_type.startswith("knia") or "knia" in source or "과실비율" in source:
        return "knia"
    if item.get("chunk_id") or item.get("law_name") or "law.go.kr" in source or "법" in source:
        return "legal"
    return "general"


def _search_text(item: dict[str, Any]) -> str:
    fields = [
        item.get("title"),
        item.get("source"),
        item.get("law_name"),
        item.get("article_title"),
        item.get("plain_summary"),
        item.get("snippet"),
        item.get("chunk_text"),
        item.get("summary"),
    ]
    fields.extend(_list_values(item.get("scenario_tags")))
    fields.extend(_list_values(item.get("keywords")))
    fields.extend(_list_values(item.get("display_tags")))
    fields.extend(_list_values(item.get("used_for")))
    return " ".join(str(value) for value in fields if value).lower()


def _item_ref(item: dict[str, Any]) -> str:
    return str(item.get("chunk_id") or item.get("source_url") or item.get("title") or "unknown")


def _normalize_token(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _list_values(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        return [value]
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return list(value)
    return [value]
