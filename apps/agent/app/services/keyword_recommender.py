from __future__ import annotations

from typing import Any

from app.services.input_requirements import build_input_requirements, input_question_texts
from app.services.scenario_search_terms import scenario_search_terms


def recommend_keywords(
    scenario_type: str,
    facts: dict[str, Any],
    selected_keywords: list[str],
    evidence: list[dict[str, Any]] | None = None,
) -> list[str]:
    base = ["블랙박스", "과실비율", "보험접수"]
    scenario_terms = scenario_search_terms(
        scenario_type=scenario_type,
        scenario_tags=[],
        facts=facts,
        selected_keywords=selected_keywords,
    )
    out = [*base, *selected_keywords, *scenario_terms]
    if facts.get("injury"):
        out.extend(["부상", "진단서", "대인접수"])
    for ev in (evidence or [])[:3]:
        for kw in ev.get("keywords", []) or []:
            out.append(str(kw))
    return list(dict.fromkeys([x for x in out if x]))[:16]


def suggest_next_inputs(
    facts: dict[str, Any],
    scenario_type: str,
    missing_fields: list[str],
    input_requirements: dict[str, Any] | None = None,
) -> list[str]:
    requirements = input_requirements or build_input_requirements(
        facts=facts,
        scenario_type=scenario_type,
        missing_fields=missing_fields,
    )
    suggestions = input_question_texts(requirements)
    by_scenario = {
        "school_zone_child_accident": [
            "어린이보호구역 표지나 노면 표시 여부를 확인해 주세요.",
            "피해자의 나이와 진단 여부를 입력해 주세요.",
            "당시 제한속도와 실제 감속 여부를 보완해 주세요.",
        ],
        "intersection_signal_violation": [
            "내 차량과 상대 차량의 신호 상태를 각각 입력해 주세요.",
            "교차로 진입 시점과 직진·좌회전 여부를 보완해 주세요.",
        ],
        "rear_end_collision": [
            "정차 시간이 어느 정도였는지와 급정거 여부를 확인해 주세요.",
            "목·허리 통증 등 대인접수 필요 여부를 입력해 주세요.",
        ],
        "lane_change_collision": [
            "차선을 변경한 차량이 어느 쪽인지 입력해 주세요.",
            "방향지시등 사용 여부와 충돌 부위를 보완해 주세요.",
        ],
        "pedestrian_crosswalk_accident": [
            "횡단보도 또는 보행자 신호 위치를 확인해 주세요.",
            "보행자의 진행 방향과 충돌 지점을 보완해 주세요.",
        ],
        "bicycle_collision": [
            "자전거가 도로·자전거도로·횡단보도 중 어디를 주행했는지 입력해 주세요.",
            "충돌 위치와 양측 진행 방향을 보완해 주세요.",
        ],
        "object_collision": [
            "충돌한 시설물의 종류와 소유 주체를 확인해 주세요.",
            "도로 상태나 미끄럼 등 외부 요인이 있었는지 입력해 주세요.",
        ],
        "single_vehicle_accident": [
            "빗길·눈길·장애물 등 도로 상태를 입력해 주세요.",
            "동승자 부상이나 시설물 파손 여부를 보완해 주세요.",
        ],
        "parking_or_stopped_vehicle_accident": [
            "차량이 주차 중인지 정차 중인지 구분해 주세요.",
            "문 개방, 후진, 출차 등 접촉 직전 행동을 입력해 주세요.",
        ],
        "drunk_or_unlicensed_accident": [
            "음주 측정 여부와 무면허 여부를 구분해 주세요.",
            "경찰 신고와 보험 접수 진행 여부를 입력해 주세요.",
        ],
        "hit_and_run_risk": [
            "상대 차량이 현장을 이탈했는지와 연락처 교환 여부를 입력해 주세요.",
            "경찰 신고 시각과 블랙박스 확보 여부를 확인해 주세요.",
        ],
    }
    suggestions.extend(by_scenario.get(scenario_type, []))
    return list(dict.fromkeys(suggestions))[:8]
