from __future__ import annotations

from typing import Any

from app.services.knia.knia_matcher import match_knia_charts


def find_knia_for_chat(message: str, draft_case: dict[str, Any] | None = None, scenario_type: str | None = None) -> dict[str, Any]:
    facts = (draft_case or {}).get("structured_facts") or {}
    keywords = (draft_case or {}).get("selected_keywords") or []
    scenario = scenario_type or facts.get("accident_type")
    party = facts.get("accident_party_type")
    result = match_knia_charts(
        description_text=message,
        structured_facts=facts,
        selected_keywords=keywords,
        scenario_type=scenario,
        accident_party_type=party,
        limit=3,
    )
    safe_items = [_safe_match(x) for x in result.get("items") or []]
    return {"items": safe_items, "primary": safe_items[0] if safe_items else None}


def _safe_match(item: dict[str, Any]) -> dict[str, Any]:
    media = item.get("media") or {}
    return {
        "chart_no": item.get("chart_no"),
        "chart_type": item.get("chart_type") or "1",
        "title": item.get("title"),
        "accident_party_type": item.get("accident_party_type"),
        "accident_party_label": item.get("accident_party_label"),
        "match_reason": item.get("match_reason") or "입력하신 사고 상황과 비슷한 과실비율 기준입니다.",
        "source_url": item.get("source_url"),
        "video_url": item.get("video_url"),
        "thumbnail_url": item.get("thumbnail_url"),
        "base_fault_a": item.get("base_fault_a"),
        "base_fault_b": item.get("base_fault_b"),
        "display_tags": item.get("display_tags") or [],
        "recommended_user_actions": item.get("recommended_user_actions") or [],
        "display_mode": media.get("display_mode") or "external_link",
        "button_label": media.get("button_label") or "과실비율정보포털에서 보기",
        "attribution": item.get("attribution") or "출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털",
    }
