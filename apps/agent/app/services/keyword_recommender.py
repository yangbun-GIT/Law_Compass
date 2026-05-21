from __future__ import annotations

from typing import Any


def recommend_keywords(
    scenario_type: str,
    facts: dict[str, Any],
    selected_keywords: list[str],
    evidence: list[dict[str, Any]] | None = None,
) -> list[str]:
    base = ["블랙박스", "과실비율", "보험접수"]
    by_scenario = {
        "rear_end_collision": ["후미추돌", "안전거리", "정차중", "대인접수", "진단서"],
        "school_zone_child_accident": ["민식이법", "어린이보호구역", "제한속도", "보행자", "형사책임"],
        "intersection_signal_violation": ["신호위반", "교차로", "우선권", "12대 중과실"],
        "lane_change_collision": ["차선변경", "방향지시등", "사각지대", "측면충돌"],
        "pedestrian_crosswalk_accident": ["횡단보도", "보행자 보호의무", "인명피해", "신고의무"],
        "drunk_or_unlicensed_accident": ["음주운전", "무면허운전", "형사책임"],
        "hit_and_run_risk": ["뺑소니", "사고 후 조치", "신고의무"],
    }
    out = [*base, *selected_keywords, *by_scenario.get(scenario_type, [])]
    if facts.get("injury"):
        out.extend(["부상", "진단서", "대인접수"])
    for ev in (evidence or [])[:3]:
        for kw in ev.get("keywords", []) or []:
            out.append(str(kw))
    return list(dict.fromkeys([x for x in out if x]))[:16]


def suggest_next_inputs(facts: dict[str, Any], scenario_type: str, missing_fields: list[str]) -> list[str]:
    suggestions = [f"{field} 정보를 보완하면 정확도가 올라갑니다." for field in missing_fields]
    if scenario_type == "school_zone_child_accident":
        suggestions.extend(["어린이보호구역 표지/노면표시 여부를 확인해 주세요.", "피해자 나이와 진단 여부를 입력해 주세요.", "당시 제한속도와 실제 감속 여부를 보완해 주세요."])
    if scenario_type == "intersection_signal_violation":
        suggestions.extend(["내 차량과 상대 차량의 신호 상태를 각각 입력해 주세요.", "교차로 진입 시점과 선진입 여부를 보완해 주세요."])
    if scenario_type == "rear_end_collision":
        suggestions.extend(["정차 시간이 얼마나 되었는지, 급정거 여부를 확인해 주세요.", "목/허리 통증 등 대인 접수 필요 여부를 입력해 주세요."])
    return list(dict.fromkeys(suggestions))[:8]
