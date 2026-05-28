from __future__ import annotations

import re
from typing import Any, Iterable

from app.services.party_agents.base import PARTY_TYPES, canonical_party


PARTY_PREFIXES = {
    "car_vs_car": ("차",),
    "car_vs_person": ("보",),
    "car_vs_bicycle": ("거", "자"),
    "car_vs_motorcycle": ("차",),
    "car_vs_object": ("기",),
    "single_vehicle": ("단",),
}

PARTY_BLOCKED_TERMS = {
    "car_vs_car": ("보행자", "차대사람", "사람과", "자전거", "차대자전거", "bicycle", "cyclist", "시설물 충돌", "차대기물", "단독사고"),
    "car_vs_person": ("자전거", "차대자전거", "오토바이", "이륜차", "가드레일", "전봇대", "단독사고", "후미추돌"),
    "car_vs_bicycle": ("보행자", "차대사람", "횡단보도 보행자", "오토바이", "이륜차", "가드레일", "전봇대", "후미추돌"),
    "car_vs_motorcycle": ("보행자", "차대사람", "자전거", "차대자전거", "bicycle", "가드레일", "전봇대", "단독사고"),
    "car_vs_object": ("보행자", "차대사람", "자전거", "차대자전거", "오토바이", "이륜차", "후미추돌"),
    "single_vehicle": ("보행자", "차대사람", "자전거", "차대자전거", "오토바이", "이륜차", "후미추돌", "상대 차량"),
}

PARTY_BLOCKED_TAGS = {
    "car_vs_car": {"pedestrian", "bicycle", "object", "single_vehicle"},
    "car_vs_person": {"bicycle", "object", "single_vehicle", "rear_end", "lane_change"},
    "car_vs_bicycle": {"pedestrian", "object", "single_vehicle", "rear_end"},
    "car_vs_motorcycle": {"pedestrian", "bicycle", "object", "single_vehicle"},
    "car_vs_object": {"pedestrian", "bicycle", "single_vehicle", "rear_end"},
    "single_vehicle": {"pedestrian", "bicycle", "object", "rear_end", "lane_change", "intersection"},
}


def canonicalize_party_type(value: Any) -> str:
    return canonical_party(value)


def allowed_chart_prefixes(party_type: Any) -> tuple[str, ...]:
    return PARTY_PREFIXES.get(canonicalize_party_type(party_type), ())


def is_chart_allowed_for_party(chart_no: Any, party_type: Any) -> bool:
    party = canonicalize_party_type(party_type)
    if party == "unknown":
        return True
    chart = str(chart_no or "").strip()
    if not chart:
        return False
    prefixes = allowed_chart_prefixes(party)
    if party == "car_vs_object" and chart.startswith(("보", "거", "자")):
        return False
    if party == "single_vehicle" and chart.startswith(("보", "거", "자")):
        return False
    if prefixes:
        return chart.startswith(prefixes)
    return False


def filter_terms_by_party(terms: Iterable[Any], party_type: Any, facts: dict[str, Any] | None = None) -> list[str]:
    party = canonicalize_party_type(party_type)
    if party == "unknown":
        return _dedupe(str(value).strip() for value in (terms or []) if str(value or "").strip())
    facts = facts or {}
    out: list[str] = []
    blocked = PARTY_BLOCKED_TERMS.get(party, ())
    for value in terms or []:
        text = str(value or "").strip()
        if not text:
            continue
        if party != "car_vs_bicycle" and _contains_any(text, ("자전거", "차대자전거", "bicycle", "cyclist")):
            # 자전거가 직접 충돌 대상이 아닌 차대차 비접촉 유발 맥락은 검색어에서 제외한다.
            if not (party == "car_vs_car" and facts.get("direct_collision_partner_type") == "vehicle"):
                continue
            continue
        if party != "car_vs_person" and _contains_any(text, ("보행자", "차대사람", "사람과", "횡단보도 보행자")):
            if party == "car_vs_car" and _contains_any(text, ("정차", "신호 정지", "차대차")) and "보행자 보호" not in text:
                out.append(text)
                continue
            continue
        if party != "car_vs_object" and _contains_any(text, ("차대기물", "시설물 충돌")):
            continue
        if any(token.lower() in text.lower() for token in blocked):
            continue
        out.append(text)
    return _dedupe(out)


def filter_tags_by_party(tags: Iterable[Any], party_type: Any, facts: dict[str, Any] | None = None) -> list[str]:
    party = canonicalize_party_type(party_type)
    blocked = PARTY_BLOCKED_TAGS.get(party, set())
    out = []
    for tag in tags or []:
        text = str(tag or "").strip()
        if not text or text in blocked:
            continue
        if party != "car_vs_bicycle" and text == "bicycle":
            continue
        if party != "car_vs_person" and text == "pedestrian":
            continue
        if party != "car_vs_object" and text == "object":
            continue
        out.append(text)
    return _dedupe(out)


def reject_mismatched_knia_items(items: Iterable[dict[str, Any]], party_type: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    party = canonicalize_party_type(party_type)
    kept: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for item in items or []:
        item_party = canonicalize_party_type(item.get("major_party_type") or item.get("accident_party_type") or _party_from_chart_no(item.get("chart_no")))
        chart_no = str(item.get("chart_no") or "")
        text = _item_text(item)
        allowed = True
        reason = ""
        if party != "unknown":
            if item_party != "unknown" and item_party != party:
                allowed = False
                reason = f"party_mismatch:{item_party}"
            elif not item_party or item_party == "unknown":
                allowed = is_chart_allowed_for_party(chart_no, party)
                reason = "chart_prefix_mismatch"
            if party == "car_vs_motorcycle":
                allowed = item_party == "car_vs_motorcycle" or (
                    chart_no.startswith("차")
                    and _contains_any(text, ("오토바이", "이륜", "원동기장치자전거", "motorcycle"))
                )
                reason = "motorcycle_keyword_mismatch"
        if allowed:
            kept.append(item)
        else:
            rejected.append({**item, "exclusion_reason": reason, "requested_party_type": party})
    return kept, rejected


def _party_from_chart_no(chart_no: Any) -> str:
    chart = str(chart_no or "")
    for party, prefixes in PARTY_PREFIXES.items():
        if chart.startswith(prefixes):
            return party
    return "unknown"


def _item_text(item: dict[str, Any]) -> str:
    return " ".join(str(item.get(key) or "") for key in ("chart_no", "title", "scenario_type", "scenario_subtype", "accident_summary", "accident_situation", "basic_fault_text", "display_tags", "keywords")).lower()


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    lower = str(text or "").lower()
    return any(token.lower() in lower for token in tokens)


def _dedupe(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = re.sub(r"\s+", " ", str(value).strip().lower())
        if key and key not in seen:
            out.append(str(value).strip())
            seen.add(key)
    return out
