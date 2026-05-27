from __future__ import annotations

from typing import Any
import re

from app.services.knia.knia_matcher import is_knia_match_compatible_with_scenario
from app.services.knia.knia_media_selector import (
    KNIA_SOURCE_LINK_NOTICE,
    safe_knia_thumbnail_url,
    safe_knia_url,
    select_media,
)
from app.services.knia.knia_repository import KniaRepository

ATTRIBUTION = "자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털"
DISCLAIMER = "본 서비스의 과실비율 분석은 참고용입니다. 최종 과실비율은 보험사, 과실비율분쟁심의위원회, 법원 판단에 따라 달라질 수 있습니다."
MISSING_KNIA_SOURCE_NOTICE = "수집된 KNIA 원문 링크가 없습니다. 관리자 KNIA 상세 수집을 먼저 실행해 주세요."
MAX_CHART_DETAIL_LOOKUPS = 3
MAX_DISPLAY_CANDIDATES = 3


def build_knia_evidence(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for match in matches[:5]:
        title = match.get("title") or "과실비율 인정기준"
        chart_no = match.get("chart_no") or "기준번호 미확인"
        evidence.append({
            "source_type": "knia_fault_standard",
            "title": f"{chart_no} {title}",
            "chart_no": match.get("chart_no"),
            "chart_type": match.get("chart_type"),
            "law_name": "과실비율 인정기준",
            "article_title": title,
            "plain_summary": match.get("basic_fault_text") or match.get("accident_summary") or "유사 사고의 과실비율 판단에 참고할 수 있는 KNIA 기준입니다.",
            "related_reason": match.get("match_reason") or "입력하신 사고 상황과 유사한 과실비율 인정기준입니다.",
            "source_url": match.get("source_detail_url") or match.get("source_url"),
            "source_detail_url": match.get("source_detail_url"),
            "video_url": match.get("video_url"),
            "source": "과실비율정보포털",
            "confidence_label": match.get("match_label") or "관련성이 있는 기준입니다.",
            "used_for": "과실비율 참고 기준",
        })
    return evidence


def adapt_knia_for_report(
    report: dict[str, Any],
    primary: dict[str, Any] | None,
    matches: list[dict[str, Any]],
    technical_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = technical_result or {}
    scenario_type = str(source.get("scenario_type") or source.get("structured_facts", {}).get("scenario_type") or "")
    candidates = _collect_knia_candidates(primary, matches, source)
    candidates = _enrich_candidates_from_repository(candidates)
    if not any(_safe_display_url(item) for item in candidates):
        candidates = [*_repository_display_fallback_candidates(source, candidates), *candidates]
    candidates = [
        item for item in candidates
        if _is_user_display_candidate(item, scenario_type)
    ]
    selected = _select_display_candidate(candidates)
    if not selected:
        return _remove_duplicate_knia_legacy_video(report)

    report["related_fault_standard"] = _build_related_fault_standard(selected)

    media_card = _build_media_card(selected)
    report["related_knia_video_card"] = {
        **media_card,
        "title": "KNIA 원문 기준 및 관련 영상",
        "description": "과실비율정보포털에서 제공하는 유사 사고 기준을 원문 링크로 확인할 수 있습니다.",
        "chart_no": selected.get("chart_no"),
        "chart_title": selected.get("title"),
        "accident_party_label": selected.get("accident_party_label"),
    }

    # KNIA media is represented by related_knia_video_card only.
    # Keeping the same KNIA card in related_video causes duplicate cards in easy/result UIs.
    report = _remove_duplicate_knia_legacy_video(report)

    report["knia_link_cards"] = [
        _build_media_card(item)
        for item in candidates[:MAX_DISPLAY_CANDIDATES]
        if _safe_display_url(item)
    ]
    report["knia_basis_cards"] = [
        _build_basis_card(item)
        for item in candidates[:MAX_DISPLAY_CANDIDATES]
        if item.get("chart_no") or _safe_display_url(item)
    ]

    disclaimers = report.get("disclaimers") or []
    if isinstance(disclaimers, list) and DISCLAIMER not in disclaimers:
        report["disclaimers"] = [*disclaimers, DISCLAIMER]
    return report


def _collect_knia_candidates(
    primary: dict[str, Any] | None,
    matches: list[dict[str, Any]],
    result: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    _append_candidate(candidates, primary, "knia_primary_match")
    for item in matches:
        _append_candidate(candidates, item, "knia_matches")
    for key in ("knia_evidence", "combined_evidence", "evidence"):
        for item in result.get(key) or []:
            if _looks_like_knia_candidate(item):
                _append_candidate(candidates, item, key)
    for key in ("related_fault_standard", "related_video", "related_knia_video_card"):
        _append_candidate(candidates, result.get(key), key)
    for item in result.get("knia_basis_cards") or []:
        _append_candidate(candidates, item, "knia_basis_cards")

    report = result.get("elderly_friendly_report") or {}
    for key in ("related_fault_standard", "related_video", "related_knia_video_card"):
        _append_candidate(candidates, report.get(key), f"elderly_friendly_report.{key}")
    for item in report.get("knia_basis_cards") or []:
        _append_candidate(candidates, item, "elderly_friendly_report.knia_basis_cards")
    for item in report.get("knia_link_cards") or []:
        _append_candidate(candidates, item, "elderly_friendly_report.knia_link_cards")

    fault_ratio = result.get("fault_ratio") or {}
    for key in ("knia_reference_fault", "knia_fault_estimate"):
        value = fault_ratio.get(key) or result.get(key)
        if isinstance(value, dict):
            _append_candidate(candidates, value.get("source_chart") or value, key)
    return _dedupe_candidates(candidates)


def _append_candidate(candidates: list[dict[str, Any]], item: Any, source_key: str) -> None:
    if not isinstance(item, dict) or _is_rejected_candidate(item):
        return
    candidate = dict(item)
    candidate.setdefault("candidate_source", source_key)
    if candidate.get("chart_title") and not candidate.get("title"):
        candidate["title"] = candidate.get("chart_title")
    if isinstance(candidate.get("media"), dict):
        media = candidate["media"]
        for key in ("video_url", "source_url", "source_detail_url", "source_page_url", "thumbnail_url", "media_provider"):
            if not candidate.get(key) and media.get(key):
                candidate[key] = media.get(key)
    candidates.append(candidate)


def _looks_like_knia_candidate(item: Any) -> bool:
    if not isinstance(item, dict) or _is_rejected_candidate(item):
        return False
    joined = " ".join(
        str(item.get(key) or "")
        for key in (
            "source_type",
            "source",
            "title",
            "law_name",
            "article_title",
            "source_url",
            "source_detail_url",
            "source_page_url",
            "video_url",
            "chart_no",
        )
    ).lower()
    return bool(item.get("chart_no")) or "knia" in joined or "과실비율" in joined or "accident.knia.or.kr" in joined


def _dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for item in candidates:
        key = _candidate_key(item)
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def _candidate_key(item: dict[str, Any]) -> str:
    chart_no = str(item.get("chart_no") or "").strip().lower()
    chart_type = str(item.get("chart_type") or "").strip().lower()
    if chart_no:
        return f"chart:{chart_no}:{chart_type}"
    for key in ("video_url", "source_detail_url", "source_url", "source_page_url", "button_url"):
        url = safe_knia_url(item.get(key))
        if url:
            return f"url:{url.lower()}"
    title = str(item.get("title") or item.get("chart_title") or item.get("article_title") or "").strip().lower()
    return f"title:{title}" if title else ""


def _enrich_candidates_from_repository(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    repo: KniaRepository | None = None
    lookups = 0
    output: list[dict[str, Any]] = []
    for item in candidates:
        enriched = dict(item)
        if _needs_chart_detail(enriched) and lookups < MAX_CHART_DETAIL_LOOKUPS:
            chart_no = str(enriched.get("chart_no") or "").strip()
            chart_type = str(enriched.get("chart_type") or "1").strip() or "1"
            if chart_no:
                try:
                    repo = repo or KniaRepository()
                    chart = repo.get_chart(chart_no, chart_type)
                except Exception:
                    chart = None
                lookups += 1
                if chart:
                    enriched = _merge_chart_detail(enriched, chart)
        output.append(enriched)
    return output


def _needs_chart_detail(item: dict[str, Any]) -> bool:
    return bool(item.get("chart_no")) and not _safe_display_url(item)


def _merge_chart_detail(candidate: dict[str, Any], chart: dict[str, Any]) -> dict[str, Any]:
    merged = dict(chart)
    merged.update({k: v for k, v in candidate.items() if v not in (None, "", [])})
    for key in (
        "video_url",
        "source_detail_url",
        "source_url",
        "source_page_url",
        "thumbnail_url",
        "media_embed_url",
        "media_provider",
        "license_status",
        "attribution",
        "chart_type",
        "title",
    ):
        if not merged.get(key) and chart.get(key):
            merged[key] = chart.get(key)
    return merged



def _repository_display_fallback_candidates(
    source: dict[str, Any],
    existing_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Find displayable KNIA chart rows when the analysis candidate has only a scenario label.

    This is a bounded DB fallback only. It does not fetch external pages.
    """
    scenario_type = str(source.get("scenario_type") or source.get("structured_facts", {}).get("scenario_type") or "")
    accident_party_type = str(source.get("accident_party_type") or source.get("structured_facts", {}).get("accident_party_type") or "")
    hint_text = _fallback_hint_text(source, existing_candidates)
    terms = _scenario_link_terms(scenario_type, hint_text)
    if not terms:
        return []

    try:
        repo = KniaRepository()
        rows = repo.display_link_candidates(accident_party_type=accident_party_type or None, limit=150)
        if not rows and accident_party_type:
            rows = repo.display_link_candidates(accident_party_type=None, limit=150)
    except Exception:
        return []

    ranked: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        score = _display_fallback_score(row, terms, hint_text)
        if score <= 0:
            continue
        ranked.append((score, row))
    ranked.sort(key=lambda pair: (-pair[0], 0 if safe_knia_url(pair[1].get("video_url")) else 1))
    return [row for _, row in ranked[:MAX_DISPLAY_CANDIDATES]]


def _fallback_hint_text(source: dict[str, Any], existing_candidates: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for key in ("scenario_type", "accident_type", "accident_party_label", "description_text", "summary"):
        value = source.get(key)
        if value:
            parts.append(str(value))
    facts = source.get("structured_facts") or {}
    if isinstance(facts, dict):
        for key, value in facts.items():
            if value not in (None, "", [], {}, False):
                parts.append(f"{key} {value}")
    for item in existing_candidates[:8]:
        for key in (
            "chart_no",
            "title",
            "chart_title",
            "article_title",
            "plain_summary",
            "easy_explanation",
            "why_similar",
            "related_reason",
        ):
            value = item.get(key)
            if value:
                parts.append(str(value))
    return " ".join(parts).lower()


def _scenario_link_terms(scenario_type: str, hint_text: str) -> list[str]:
    base_terms: dict[str, list[str]] = {
        "rear_end_collision": ["후방 추돌", "후방추돌", "후미추돌", "뒤차", "뒷차", "안전거리", "정차", "선행차", "앞차", "차41", "차42"],
        "intersection_signal_violation": ["교차로", "신호", "신호위반", "적색", "좌회전", "직진", "차12", "차16"],
        "lane_change_collision": ["진로 변경", "진로변경", "차로변경", "차선변경", "진입", "차43"],
        "centerline_obstacle_collision": ["중앙선", "장애물", "대향", "불법 주정차", "진로변경", "차43"],
        "pedestrian_crosswalk_accident": ["보행자", "횡단보도", "보행자 신호", "어린이", "보"],
        "bicycle_collision": ["자전거", "이륜차", "비접촉", "거", "자"],
        "object_collision": ["기물", "시설물", "주차", "물체"],
        "single_vehicle_accident": ["단독", "전도", "공작물", "시설물", "단"],
    }
    terms = list(base_terms.get(scenario_type, []))
    if "후미" in hint_text or "뒤차" in hint_text or "뒷차" in hint_text or "후방" in hint_text:
        terms.extend(base_terms["rear_end_collision"])
    if "좌회전" in hint_text or "교차로" in hint_text or "신호" in hint_text:
        terms.extend(base_terms["intersection_signal_violation"])
    if "차선" in hint_text or "차로" in hint_text or "진로" in hint_text:
        terms.extend(base_terms["lane_change_collision"])
    if "중앙선" in hint_text or "대향" in hint_text or "장애물" in hint_text:
        terms.extend(base_terms["centerline_obstacle_collision"])
    if "보행자" in hint_text or "횡단보도" in hint_text:
        terms.extend(base_terms["pedestrian_crosswalk_accident"])
    return list(dict.fromkeys(term.lower() for term in terms if term))


def _display_fallback_score(row: dict[str, Any], terms: list[str], hint_text: str) -> float:
    text = " ".join(
        str(row.get(key) or "")
        for key in (
            "chart_no",
            "title",
            "category_path",
            "accident_summary",
            "applicable_text",
            "basic_fault_text",
            "scenario_summary_easy",
            "display_tags",
            "source_url",
            "source_detail_url",
            "video_url",
        )
    ).lower()
    score = 0.0
    for term in terms:
        if term in text:
            score += 1.0
    for token in re.findall(r"[가-힣A-Za-z0-9]{2,}", hint_text):
        if token.lower() in text:
            score += 0.12
    if safe_knia_url(row.get("video_url")):
        score += 0.5
    if safe_knia_url(row.get("source_detail_url")) or safe_knia_url(row.get("source_url")):
        score += 0.25
    return score


def _is_user_display_candidate(item: dict[str, Any], scenario_type: str) -> bool:
    if _is_rejected_candidate(item):
        return False
    if scenario_type and (item.get("chart_no") or item.get("title")):
        return is_knia_match_compatible_with_scenario(item, scenario_type)
    return _looks_like_knia_candidate(item)


def _is_rejected_candidate(item: dict[str, Any]) -> bool:
    joined = " ".join(
        str(item.get(key) or "")
        for key in ("status", "reason", "exclusion_reason", "mismatch_reason", "knia_override_policy", "candidate_source")
    ).lower()
    return any(token in joined for token in ("rejected", "mismatch", "incompatible", "basis_mismatch", "불일치", "제외"))


def _select_display_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda item: (
            0 if safe_knia_url(item.get("video_url")) else 1,
            0 if _safe_display_url(item) else 1,
            -_numeric_score(item),
        ),
    )[0]


def _build_related_fault_standard(primary: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": "이 사고와 비슷한 과실비율 인정기준",
        "chart_no": primary.get("chart_no"),
        "chart_title": primary.get("title"),
        "accident_party_type": primary.get("accident_party_type"),
        "accident_party_label": primary.get("accident_party_label"),
        "display_tags": primary.get("display_tags") or [],
        "recommended_user_actions": primary.get("recommended_user_actions") or [],
        "base_fault_label": _fault_label(primary),
        "easy_explanation": primary.get("basic_fault_text") or primary.get("accident_summary") or "유사한 사고 유형에서 과실비율을 참고할 수 있는 기준입니다.",
        "why_similar": primary.get("match_reason") or primary.get("related_reason") or "입력하신 사고 상황과 기준의 사고 유형이 비슷합니다.",
        "source_url": _safe_non_video_source_url(primary) or None,
        "source_label": ATTRIBUTION,
        "disclaimer": DISCLAIMER,
    }


def _build_media_card(primary: dict[str, Any]) -> dict[str, Any]:
    media = primary.get("media") if isinstance(primary.get("media"), dict) else None
    selected_media = media or select_media(primary) or {}

    video_url = (
        safe_knia_url(primary.get("video_url"))
        or safe_knia_url(selected_media.get("video_url"))
        or _video_url_from_source(selected_media.get("source_url"))
        or _video_url_from_source(primary.get("source_url"))
    )
    source_detail_url = safe_knia_url(primary.get("source_detail_url")) or safe_knia_url(selected_media.get("source_detail_url"))
    source_page_url = (
        safe_knia_url(primary.get("source_page_url"))
        or safe_knia_url(selected_media.get("source_page_url"))
        or safe_knia_url(primary.get("source_url"))
        or safe_knia_url(selected_media.get("source_url"))
    )
    display_url = video_url or source_detail_url or source_page_url
    has_url = bool(display_url)
    return _drop_none({
        "title": "KNIA 원문 기준 및 관련 영상",
        "description": "과실비율정보포털에서 제공하는 유사 사고 기준을 원문 링크로 확인할 수 있습니다.",
        "display_mode": "external_link",
        "button_url": display_url or None,
        "source_url": display_url or None,
        "video_url": video_url or None,
        "source_detail_url": source_detail_url or None,
        "source_page_url": source_page_url or None,
        "embed_url": None,
        "media_embed_url": None,
        "thumbnail_url": safe_knia_thumbnail_url(primary.get("thumbnail_url") or selected_media.get("thumbnail_url")) or None,
        "button_label": "KNIA 관련 영상 보기" if video_url else "KNIA 원문 기준 보기",
        "notice": KNIA_SOURCE_LINK_NOTICE if has_url and _needs_notice(primary) else (MISSING_KNIA_SOURCE_NOTICE if not has_url else None),
        "missing_source_notice": MISSING_KNIA_SOURCE_NOTICE if not has_url else None,
        "has_knia_candidate": True,
        "source_label": ATTRIBUTION,
        "attribution": primary.get("attribution") or ATTRIBUTION,
    })


def _build_basis_card(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "chart_no": item.get("chart_no"),
        "title": item.get("title") or item.get("article_title") or "KNIA 과실비율 인정기준",
        "easy_explanation": item.get("basic_fault_text") or item.get("accident_summary") or item.get("plain_summary") or "유사 사고의 과실비율 기준입니다.",
        "why_similar": item.get("match_reason") or item.get("related_reason") or "입력하신 사고와 비슷한 요소가 있습니다.",
        "source_url": _safe_display_url(item) or None,
        "source_label": ATTRIBUTION,
    }


def _safe_display_url(item: dict[str, Any]) -> str:
    media = item.get("media") if isinstance(item.get("media"), dict) else {}
    return (
        safe_knia_url(item.get("video_url"))
        or _video_url_from_source(item.get("source_url"))
        or safe_knia_url(item.get("source_detail_url"))
        or safe_knia_url(item.get("source_page_url"))
        or safe_knia_url(item.get("source_url"))
        or safe_knia_url(item.get("button_url"))
        or safe_knia_url(media.get("video_url"))
        or _video_url_from_source(media.get("source_url"))
        or safe_knia_url(media.get("source_detail_url"))
        or safe_knia_url(media.get("source_page_url"))
        or safe_knia_url(media.get("source_url"))
    )


def _safe_non_video_source_url(item: dict[str, Any]) -> str:
    media = item.get("media") if isinstance(item.get("media"), dict) else {}
    return (
        safe_knia_url(item.get("source_detail_url"))
        or safe_knia_url(item.get("source_page_url"))
        or (safe_knia_url(item.get("source_url")) if not _is_video_url(str(item.get("source_url") or "")) else "")
        or safe_knia_url(media.get("source_detail_url"))
        or safe_knia_url(media.get("source_page_url"))
        or (safe_knia_url(media.get("source_url")) if not _is_video_url(str(media.get("source_url") or "")) else "")
    )


def _video_url_from_source(value: Any) -> str:
    url = safe_knia_url(value)
    return url if url and _is_video_url(url) else ""


def _is_video_url(value: str) -> bool:
    return value.lower().split("?", 1)[0].endswith((".mp4", ".mov", ".m4v", ".webm"))


def _needs_notice(item: dict[str, Any]) -> bool:
    return item.get("license_status") == "source_link_only" or item.get("media_provider") == "external_url" or bool(_safe_display_url(item))


def _remove_duplicate_knia_legacy_video(report: dict[str, Any]) -> dict[str, Any]:
    legacy = report.get("related_video")
    if isinstance(legacy, dict) and _looks_like_knia_candidate(legacy):
        report.pop("related_video", None)
    return report


def _numeric_score(item: dict[str, Any]) -> float:
    try:
        return float(item.get("score") or item.get("match_score") or 0)
    except (TypeError, ValueError):
        return 0.0


def _fault_label(match: dict[str, Any]) -> str:
    a = match.get("base_fault_a")
    b = match.get("base_fault_b")
    if isinstance(a, int) and isinstance(b, int):
        return f"기본 참고: A차량 {a}%, B차량 {b}%"
    return "기본 과실은 사고 세부 상황에 따라 달라질 수 있습니다."


def _drop_none(value: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in value.items() if v is not None}
