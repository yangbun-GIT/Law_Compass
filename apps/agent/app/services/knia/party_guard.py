from __future__ import annotations

import re
from typing import Any, Iterable

from app.services.party_agents.base import canonical_party


# The extra one-character prefixes keep compatibility with old test fixtures
# whose Korean text was stored in a legacy mojibake form. User-facing results
# still use the canonical KNIA prefixes: 차, 보, 거, 기, 단.
PARTY_PREFIXES: dict[str, tuple[str, ...]] = {
    "car_vs_car": ("차", "李"),
    "car_vs_person": ("보", "蹂"),
    "car_vs_bicycle": ("거", "자", "嫄"),
    "car_vs_motorcycle": ("차", "李"),
    "car_vs_object": ("기", "湲"),
    "single_vehicle": ("단",),
}

PARTY_BLOCKED_TERMS: dict[str, tuple[str, ...]] = {
    "car_vs_car": (
        "보행자",
        "차대사람",
        "사람과",
        "사람을",
        "작업자",
        "공사 담당자",
        "도로 작업자",
        "자전거",
        "차대자전거",
        "bicycle",
        "cyclist",
        "시설물 충돌",
        "차대기물",
        "차량단독",
    ),
    "car_vs_person": (
        "차대차",
        "진로변경",
        "차로변경",
        "차선변경",
        "끼어들기",
        "후미추돌",
        "후방추돌",
        "안전거리미확보",
        "안전거리",
        "차41",
        "차43",
        "자전거",
        "차대자전거",
        "오토바이",
        "이륜차",
        "가드레일",
        "전봇대",
        "시설물 충돌",
        "차대기물",
        "차량단독",
        "단독사고",
    ),
    "car_vs_bicycle": (
        "보행자",
        "차대사람",
        "횡단보도 보행자",
        "작업자",
        "공사 담당자",
        "오토바이",
        "이륜차",
        "가드레일",
        "전봇대",
        "후미추돌",
        "차41",
        "차43",
    ),
    "car_vs_motorcycle": (
        "보행자",
        "차대사람",
        "작업자",
        "공사 담당자",
        "자전거",
        "차대자전거",
        "bicycle",
        "가드레일",
        "전봇대",
        "차량단독",
    ),
    "car_vs_object": (
        "보행자",
        "차대사람",
        "작업자",
        "공사 담당자",
        "자전거",
        "차대자전거",
        "오토바이",
        "이륜차",
        "후미추돌",
        "차41",
        "차43",
    ),
    "single_vehicle": (
        "보행자",
        "차대사람",
        "작업자",
        "공사 담당자",
        "자전거",
        "차대자전거",
        "오토바이",
        "이륜차",
        "후미추돌",
        "상대 차량",
    ),
}

PARTY_BLOCKED_TAGS: dict[str, set[str]] = {
    "car_vs_car": {"pedestrian", "bicycle", "object", "single_vehicle"},
    "car_vs_person": {"bicycle", "object", "single_vehicle", "rear_end", "lane_change"},
    "car_vs_bicycle": {"pedestrian", "object", "single_vehicle", "rear_end", "lane_change"},
    "car_vs_motorcycle": {"pedestrian", "bicycle", "object", "single_vehicle"},
    "car_vs_object": {"pedestrian", "bicycle", "single_vehicle", "rear_end", "lane_change"},
    "single_vehicle": {"pedestrian", "bicycle", "rear_end", "lane_change", "intersection"},
}

PEDESTRIAN_CONTEXT_TERMS = ("횡단보도", "보행자 신호", "보행자 보호의무")
BICYCLE_TERMS = ("자전거", "차대자전거", "bicycle", "cyclist")
PERSON_TERMS = ("보행자", "차대사람", "사람과", "사람을", "작업자", "공사 담당자", "도로 작업자")
OBJECT_TERMS = ("시설물", "기물", "가드레일", "전봇대", "중앙분리대", "라바콘", "방호벽")


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

    if party == "car_vs_person":
        return chart.startswith(PARTY_PREFIXES["car_vs_person"])
    if party == "car_vs_car":
        return chart.startswith(PARTY_PREFIXES["car_vs_car"])
    if party == "car_vs_bicycle":
        return chart.startswith(PARTY_PREFIXES["car_vs_bicycle"])
    if party in {"car_vs_object", "single_vehicle"} and chart.startswith(
        PARTY_PREFIXES["car_vs_person"] + PARTY_PREFIXES["car_vs_bicycle"]
    ):
        return False
    prefixes = allowed_chart_prefixes(party)
    return bool(prefixes and chart.startswith(prefixes))


def filter_terms_by_party(terms: Iterable[Any], party_type: Any, facts: dict[str, Any] | None = None) -> list[str]:
    party = canonicalize_party_type(party_type)
    if party == "unknown":
        return _dedupe(str(value).strip() for value in (terms or []) if str(value or "").strip())
    facts = facts or {}
    out: list[str] = []
    blocked = PARTY_BLOCKED_TERMS.get(party, ())
    direct_partner = str(facts.get("direct_collision_partner_type") or facts.get("collision_partner_type") or "").lower()
    pedestrian_direct = party == "car_vs_person" or direct_partner in {"pedestrian", "person"}
    bicycle_direct = party == "car_vs_bicycle" or direct_partner == "bicycle"

    for value in terms or []:
        text = str(value or "").strip()
        if not text:
            continue
        lower = text.lower()
        if party != "car_vs_bicycle" and _contains_any(lower, BICYCLE_TERMS):
            if not bicycle_direct:
                continue
        if party != "car_vs_person" and _contains_any(lower, PERSON_TERMS):
            if party == "car_vs_car" and _contains_any(lower, ("정차", "차대차", "vehicle")) and not _contains_any(lower, ("보행자 보호", "작업자")):
                out.append(text)
                continue
            continue
        if party != "car_vs_object" and _contains_any(lower, OBJECT_TERMS):
            continue
        if party == "car_vs_person" and _contains_any(lower, blocked):
            if _contains_any(lower, PEDESTRIAN_CONTEXT_TERMS) and pedestrian_direct:
                out.append(text)
            continue
        if any(token.lower() in lower for token in blocked):
            continue
        out.append(text)
    return _dedupe(out)


def filter_tags_by_party(tags: Iterable[Any], party_type: Any, facts: dict[str, Any] | None = None) -> list[str]:
    party = canonicalize_party_type(party_type)
    blocked = PARTY_BLOCKED_TAGS.get(party, set())
    out: list[str] = []
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
            elif not is_chart_allowed_for_party(chart_no, party):
                allowed = False
                reason = "chart_prefix_mismatch"
            if party == "car_vs_motorcycle":
                allowed = item_party == "car_vs_motorcycle" or (
                    chart_no.startswith(PARTY_PREFIXES["car_vs_car"])
                    and _contains_any(text, ("오토바이", "이륜", "원동기장치자전거", "motorcycle"))
                )
                reason = "" if allowed else "motorcycle_keyword_mismatch"
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
    return " ".join(
        str(item.get(key) or "")
        for key in (
            "chart_no",
            "title",
            "scenario_type",
            "scenario_subtype",
            "accident_summary",
            "accident_situation",
            "basic_fault_text",
            "base_fault_explanation",
            "display_tags",
            "keywords",
        )
    ).lower()


def _contains_any(text: str, tokens: Iterable[str]) -> bool:
    lower = str(text or "").lower()
    return any(str(token).lower() in lower for token in tokens)


def _dedupe(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = re.sub(r"\s+", " ", str(value).strip().lower())
        if key and key not in seen:
            out.append(str(value).strip())
            seen.add(key)
    return out
