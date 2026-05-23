from __future__ import annotations

import json
from typing import Any


SCENARIO_SEARCH_TERMS: dict[str, tuple[str, ...]] = {
    "rear_end_collision": ("후미추돌", "뒤차 추돌", "안전거리", "정차 중 추돌", "급정거"),
    "lane_change_collision": ("차선변경", "진로변경", "방향지시등", "깜빡이", "측면충돌", "사각지대"),
    "intersection_signal_violation": ("교차로", "신호위반", "적색신호", "좌회전", "직진", "우선권"),
    "pedestrian_crosswalk_accident": ("보행자", "횡단보도", "보행자 보호의무", "무단횡단", "인명피해"),
    "school_zone_child_accident": ("어린이보호구역", "민식이법", "어린이", "제한속도", "보행자 보호의무"),
    "bicycle_collision": ("자전거", "차대 자전거", "자전거도로", "교차로 자전거", "취약 교통참여자"),
    "object_collision": ("시설물 충돌", "기물 파손", "가드레일", "전봇대", "중앙분리대", "대물배상"),
    "single_vehicle_accident": ("단독사고", "도로이탈", "전복", "빗길", "눈길", "운전자 부주의"),
    "parking_or_stopped_vehicle_accident": ("주차 차량", "정차 차량", "주정차", "개문 사고", "정차 중 접촉"),
    "drunk_or_unlicensed_accident": ("음주운전", "무면허운전", "12대 중과실", "형사책임", "보험 면책"),
    "hit_and_run_risk": ("뺑소니", "도주", "사고 후 미조치", "신고의무", "구호조치"),
    "general_collision": ("교통사고", "과실비율", "보험접수", "블랙박스", "사고 경위"),
}

SCENARIO_SEARCH_TERMS["parking_or_stopped_vehicle_accident"] = (
    *SCENARIO_SEARCH_TERMS.get("parking_or_stopped_vehicle_accident", ()),
    "centerline obstacle avoidance",
    "unlit stopped vehicle",
    "avoidability analysis",
    "stopped vehicle",
    "parking vehicle",
)

TAG_SEARCH_TERMS: dict[str, tuple[str, ...]] = {
    "injury": ("부상", "진단서", "대인접수"),
    "school_zone": ("어린이보호구역", "제한속도"),
    "child_protection": ("어린이", "보호의무"),
    "pedestrian": ("보행자", "횡단보도"),
    "bicycle": ("자전거", "취약 교통참여자"),
    "object": ("시설물", "기물 파손"),
    "single_vehicle": ("단독사고", "도로이탈"),
    "intersection": ("교차로", "우선권"),
    "signal_violation": ("신호위반", "적색신호"),
    "lane_change": ("차선변경", "진로변경"),
    "rear_end": ("후미추돌", "안전거리"),
    "parking": ("주정차", "정차 차량"),
    "safe_distance": ("안전거리", "급정거"),
    "reporting_duty": ("신고의무", "구호조치"),
    "twelve_gross_negligence": ("12대 중과실", "형사책임"),
    "centerline": ("centerline crossing", "centerline obstacle avoidance", "oncoming vehicle collision"),
    "secondary_collision": ("secondary collision", "front and rear collision", "rear-end after primary collision"),
    "visibility": ("unlit stopped vehicle", "night visibility", "avoidability analysis"),
    "speed": ("speeding", "speed limit", "avoidability analysis"),
    "fatality": ("fatal traffic accident", "criminal civil liability split", "criminal liability"),
    "non_contact_trigger": ("non-contact bicycle trigger", "bicycle induced accident", "reaction time gap"),
}

PARTY_SEARCH_TERMS: dict[str, tuple[str, ...]] = {
    "car_vs_car": ("차대차", "상대 차량"),
    "car_vs_person": ("차대 보행자", "보행자 보호의무"),
    "car_vs_bicycle": ("차대 자전거", "자전거 사고"),
    "car_vs_object": ("차대 시설물", "대물배상"),
    "single_vehicle": ("단독사고", "운전자 부주의"),
}


def scenario_search_terms(
    *,
    scenario_type: str | None,
    scenario_tags: list[str] | None = None,
    facts: dict[str, Any] | None = None,
    selected_keywords: list[str] | None = None,
    accident_party_type: str | None = None,
    max_terms: int = 18,
) -> list[str]:
    facts = facts or {}
    terms: list[str] = []
    _extend_unique(terms, SCENARIO_SEARCH_TERMS.get(scenario_type or "", ()))
    for tag in scenario_tags or []:
        _extend_unique(terms, TAG_SEARCH_TERMS.get(str(tag), ()))

    party = accident_party_type or facts.get("accident_party_type") or facts.get("party_type")
    _extend_unique(terms, PARTY_SEARCH_TERMS.get(str(party or ""), ()))

    if facts.get("injury"):
        _extend_unique(terms, ("부상", "진단서", "대인접수", "인명피해"))
    if facts.get("stopped"):
        _extend_unique(terms, ("정차 중", "정차 차량", "후미추돌"))
    if facts.get("lane_change"):
        _extend_unique(terms, ("차선변경", "진로변경", "방향지시등"))
    if facts.get("intersection"):
        _extend_unique(terms, ("교차로", "우선권", "신호"))
    if facts.get("crosswalk_nearby"):
        _extend_unique(terms, ("횡단보도", "보행자 보호의무"))
    if facts.get("school_zone"):
        _extend_unique(terms, ("어린이보호구역", "제한속도"))
    _extend_unique(terms, _fact_value_terms(facts))

    for keyword in selected_keywords or []:
        if isinstance(keyword, str) and keyword.strip():
            terms.append(keyword.strip())

    return _dedupe(terms)[:max_terms]


def expand_query_text(
    base_text: str,
    *,
    scenario_type: str | None,
    scenario_tags: list[str] | None = None,
    facts: dict[str, Any] | None = None,
    selected_keywords: list[str] | None = None,
    accident_party_type: str | None = None,
    max_terms: int = 18,
) -> str:
    terms = scenario_search_terms(
        scenario_type=scenario_type,
        scenario_tags=scenario_tags,
        facts=facts,
        selected_keywords=selected_keywords,
        accident_party_type=accident_party_type,
        max_terms=max_terms,
    )
    normalized_base = _compact_text(base_text)
    additions = [term for term in terms if _compact_text(term) not in normalized_base]
    if not additions:
        return base_text
    return " ".join([base_text or "", "검색보강", *additions]).strip()


def evidence_query_payload(
    *,
    description_text: str,
    facts: dict[str, Any] | None,
    selected_keywords: list[str] | None,
    scenario_type: str | None,
    scenario_tags: list[str] | None,
    accident_party_type: str | None,
) -> dict[str, Any]:
    terms = scenario_search_terms(
        scenario_type=scenario_type,
        scenario_tags=scenario_tags,
        facts=facts,
        selected_keywords=selected_keywords,
        accident_party_type=accident_party_type,
    )
    return {
        "scenario_type": scenario_type or "general_collision",
        "accident_party_type": accident_party_type or (facts or {}).get("accident_party_type") or "unknown",
        "query_terms": terms,
        "query_text": " ".join(
            [
                description_text or "",
                json.dumps(facts or {}, ensure_ascii=False),
                " ".join(selected_keywords or []),
                " ".join(terms),
            ]
        ).strip(),
    }


def _extend_unique(target: list[str], values: tuple[str, ...]) -> None:
    for value in values:
        if value:
            target.append(value)


def _fact_value_terms(facts: dict[str, Any]) -> tuple[str, ...]:
    terms: list[str] = []
    opponent_behavior = str(facts.get("opponent_behavior") or "")
    lane_change_actor = str(facts.get("lane_change_actor") or "")
    signal_state = str(facts.get("signal_state") or "")
    opponent_signal = str(facts.get("opponent_signal") or "")
    user_signal = str(facts.get("user_signal") or "")
    damage_level = str(facts.get("damage_level") or "")

    if opponent_behavior in {"rear_collision", "rear_vehicle_collision"}:
        terms.extend(["뒤차 추돌", "후미추돌", "정차 차량 추돌"])
    if opponent_behavior in {"lane_change", "opponent_lane_change"} or lane_change_actor == "opponent":
        terms.extend(["상대 차량 차선변경", "상대 진로변경", "끼어들기 사고"])
    if lane_change_actor == "user":
        terms.extend(["내 차량 차선변경", "진로변경 차량", "차선변경 가해"])
    if facts.get("opponent_signal_violation") or opponent_signal in {"red", "red_light", "signal_violation"}:
        terms.extend(["상대 신호위반", "적색신호 위반", "교차로 신호위반"])
    if signal_state in {"red", "red_light"}:
        terms.extend(["적색신호", "신호대기", "교차로 신호"])
    if user_signal in {"green", "blue", "green_light"} and facts.get("opponent_signal_violation"):
        terms.extend(["정상 신호 직진", "신호 준수 차량"])
    if "bumper" in damage_level or "rear" in damage_level or "후미" in damage_level:
        terms.extend(["후방 범퍼 파손", "후미 추돌"])
    if facts.get("victim_is_child"):
        terms.extend(["어린이 피해", "어린이 보호의무"])
    if facts.get("bicycle_location"):
        terms.extend(["자전거 통행 위치", "자전거도로"])
    if facts.get("centerline_crossed"):
        terms.extend([
            "centerline crossing",
            "centerline obstacle avoidance",
            "oncoming vehicle collision",
            "중앙선 침범",
            "중앙선 회피",
        ])
    if facts.get("secondary_collision"):
        terms.extend([
            "secondary collision",
            "front and rear collision",
            "rear-end after primary collision",
            "후속 추돌",
            "2차 충돌",
        ])
    if facts.get("stopped_vehicle_without_lights"):
        terms.extend([
            "unlit stopped vehicle",
            "stealth stopped vehicle",
            "night visibility",
            "avoidability analysis",
            "무등화 정차 차량",
            "야간 시인성",
        ])
    if facts.get("reported_speed_kmh") or facts.get("speed_limit_kmh"):
        terms.extend([
            "speeding",
            "speed limit",
            "avoidability analysis",
            "criminal civil liability split",
            "속도위반",
            "회피 가능성",
        ])
    if facts.get("fatality"):
        terms.extend([
            "fatal traffic accident",
            "criminal liability",
            "civil fault ratio",
            "사망 사고",
            "형사 민사 구분",
        ])
    if facts.get("bicycle_involved") or facts.get("possible_trigger_vehicle") == "bicycle":
        terms.extend([
            "non-contact bicycle trigger",
            "bicycle induced accident",
            "rear-end after bicycle avoidance",
            "자전거 비접촉 유발",
            "자전거 회피 정지",
        ])
    if facts.get("time_gap_sec"):
        terms.extend([
            "reaction time gap",
            "sudden braking time gap",
            "safe distance reaction time",
            "시간적 여유",
            "급제동 대응 시간",
        ])
    return tuple(terms)


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        key = _compact_text(text)
        if text and key and key not in seen:
            out.append(text)
            seen.add(key)
    return out


def _compact_text(value: str | None) -> str:
    return " ".join(str(value or "").lower().split())
