from __future__ import annotations

from typing import Any

ATTRIBUTION = "자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털"
DISCLAIMER = "본 서비스의 과실비율 분석은 참고용입니다. 최종 과실비율은 보험사, 과실비율분쟁심의위원회, 법원 판단에 따라 달라질 수 있습니다."


def build_knia_evidence(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for match in matches[:5]:
        title = match.get("title") or "과실비율 인정기준"
        chart_no = match.get("chart_no") or "기준번호 미확인"
        evidence.append({
            "source_type": "knia_fault_standard",
            "title": f"{chart_no} {title}",
            "law_name": "과실비율 인정기준",
            "article_title": title,
            "plain_summary": match.get("basic_fault_text") or match.get("accident_summary") or "유사 사고의 과실비율 판단에 참고할 수 있는 KNIA 기준입니다.",
            "related_reason": match.get("match_reason") or "입력하신 사고 상황과 유사한 과실비율 인정기준입니다.",
            "source_url": match.get("source_url"),
            "source": "과실비율정보포털",
            "confidence_label": match.get("match_label") or "관련성이 있는 기준입니다.",
            "used_for": "과실비율 참고 기준",
        })
    return evidence


def adapt_knia_for_report(report: dict[str, Any], primary: dict[str, Any] | None, matches: list[dict[str, Any]]) -> dict[str, Any]:
    if not primary:
        return report
    standard = {
        "title": "이 사고와 비슷한 과실비율 인정기준",
        "chart_no": primary.get("chart_no"),
        "chart_title": primary.get("title"),
        "accident_party_type": primary.get("accident_party_type"),
        "accident_party_label": primary.get("accident_party_label"),
        "display_tags": primary.get("display_tags") or [],
        "recommended_user_actions": primary.get("recommended_user_actions") or [],
        "base_fault_label": _fault_label(primary),
        "easy_explanation": primary.get("basic_fault_text") or "유사한 사고 유형에서 과실비율을 참고할 수 있는 기준입니다.",
        "why_similar": primary.get("match_reason") or "입력하신 사고 상황과 기준의 사고 유형이 비슷합니다.",
        "source_url": primary.get("source_url"),
        "source_label": ATTRIBUTION,
        "disclaimer": DISCLAIMER,
    }
    report["related_fault_standard"] = standard
    media = primary.get("media") or {}
    report["related_video"] = _drop_none({
        "title": "관련 영상 또는 원문 보기",
        "display_mode": media.get("display_mode") or "external_link",
        "source_url": media.get("source_url") or primary.get("source_url"),
        "embed_url": media.get("embed_url"),
        "thumbnail_url": media.get("thumbnail_url") or primary.get("thumbnail_url"),
        "button_label": media.get("button_label") or "과실비율정보포털에서 보기",
        "notice": "영상 파일은 LawCompass 서버에 저장하지 않고, 원본 사이트 링크로만 제공합니다.",
        "source_label": ATTRIBUTION,
    })
    report["related_knia_video_card"] = _drop_none({
        "title": "비슷한 사고 영상",
        "description": "과실비율정보포털에서 제공하는 유사 사고 기준과 영상을 확인할 수 있습니다.",
        "chart_no": primary.get("chart_no"),
        "chart_title": primary.get("title"),
        "accident_party_label": primary.get("accident_party_label"),
        "video_url": primary.get("video_url"),
        "source_url": primary.get("source_url"),
        "thumbnail_url": primary.get("thumbnail_url"),
        "display_mode": (primary.get("media") or {}).get("display_mode") or "external_link",
        "button_label": "관련 영상 보기" if primary.get("video_url") else "원문 기준 보기",
        "attribution": ATTRIBUTION,
    })
    report["knia_basis_cards"] = [
        {
            "chart_no": m.get("chart_no"),
            "title": m.get("title"),
            "easy_explanation": m.get("basic_fault_text") or m.get("accident_summary") or "유사 사고의 과실비율 기준입니다.",
            "why_similar": m.get("match_reason") or "입력하신 사고와 비슷한 요소가 있습니다.",
            "source_url": m.get("source_url"),
            "source_label": ATTRIBUTION,
        }
        for m in matches[:3]
    ]
    disclaimers = report.get("disclaimers") or []
    if isinstance(disclaimers, list) and DISCLAIMER not in disclaimers:
        report["disclaimers"] = [*disclaimers, DISCLAIMER]
    return report


def _fault_label(match: dict[str, Any]) -> str:
    a = match.get("base_fault_a")
    b = match.get("base_fault_b")
    if isinstance(a, int) and isinstance(b, int):
        return f"기본 참고: A차량 {a}%, B차량 {b}%"
    return "기본 과실은 사고 세부 상황에 따라 달라질 수 있습니다."


def _drop_none(value: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in value.items() if v is not None}
