from __future__ import annotations

from typing import Any

from app.services.analyst_output_guard import guard_fault_ratio_output
from app.services.accident_perspective import (
    FRONT_VEHICLE,
    FOLLOWING_VEHICLE,
    LANE_CHANGING_VEHICLE,
    SIGNAL_COMPLIANT_VEHICLE,
    SIGNAL_VIOLATION_VEHICLE,
    STRAIGHT_VEHICLE,
    infer_user_vehicle_role,
)
from app.services.llm_client import generate_fault_ratio_analysis
from app.services.llm_policy import attach_llm_usage, evaluate_llm_usage, mark_llm_output_unavailable


def analyze_fault_ratio(
    *,
    scenario_type: str,
    facts: dict[str, Any],
    evidence: list[dict[str, Any]],
    text: str,
) -> dict[str, Any]:
    llm_usage = evaluate_llm_usage(section="fault_ratio_analysis", evidence=evidence, facts=facts)
    llm = generate_fault_ratio_analysis(text=text, scenario_type=scenario_type, facts=facts, evidence=evidence) if llm_usage["allowed"] else None
    if llm:
        return attach_llm_usage(guard_fault_ratio_output(_normalize(llm, evidence), evidence), llm_usage, used=True)
    if llm_usage["allowed"]:
        llm_usage = mark_llm_output_unavailable(llm_usage, stage="fault_ratio_analysis")

    knia = next((ev for ev in evidence if ev.get("source_type") == "knia_fault_standard"), None)
    user_vehicle_role = infer_user_vehicle_role(text, facts, scenario_type)
    key_factors = ["사고 유형", "신호·정차·차선변경 여부", "인명피해 여부", "관련 법규와 KNIA 기준"]

    if _centerline_obstacle_stop_context(facts):
        my, other, confidence = 30, 70, 0.66
        key_factors = ["중앙선 침범 사유", "정차 여부", "상대 차량 회피 가능성", "후속 추돌 분리"]
        fault_estimate_source = "contextual_complex_case"
    elif _unlit_stopped_vehicle_context(facts):
        my, other, confidence = 40, 60, 0.58
        key_factors = ["무등화 정차 차량", "야간 시인성", "속도위반 여부", "회피 가능성 감정"]
        fault_estimate_source = "contextual_complex_case"
    elif _bicycle_trigger_rear_end_context(facts):
        my, other, confidence = 20, 80, 0.6
        key_factors = ["자전거 비접촉 유발", "정지의 불가피성", "후방 차량 안전거리", "급차로변경·급제동 여부"]
        fault_estimate_source = "contextual_complex_case"
    elif _uncertain_signal_transition_context(facts):
        my, other, confidence = 80, 20, 0.55
        key_factors = ["신호 전환 시점", "내 차량 진입 신호", "상대 차량 진입 신호", "CCTV·신호체계 확인"]
        fault_estimate_source = "contextual_complex_case"
    elif scenario_type == "rear_end_collision":
        if user_vehicle_role == FRONT_VEHICLE:
            my, other, confidence = 0, 100, 0.82
        elif user_vehicle_role == FOLLOWING_VEHICLE:
            my, other, confidence = 100, 0, 0.82
        else:
            my, other, confidence = (10 if facts.get("stopped") else 20), (90 if facts.get("stopped") else 80), 0.74
        fault_estimate_source = "scenario_default"
    elif scenario_type == "intersection_signal_violation":
        if user_vehicle_role == SIGNAL_COMPLIANT_VEHICLE:
            my, other, confidence = 0, 100, 0.78
        elif user_vehicle_role == SIGNAL_VIOLATION_VEHICLE:
            my, other, confidence = 100, 0, 0.78
        else:
            my, other, confidence = (15 if facts.get("opponent_signal_violation") else 45), (85 if facts.get("opponent_signal_violation") else 55), 0.68
        fault_estimate_source = "scenario_default"
    elif scenario_type == "lane_change_collision":
        if user_vehicle_role == STRAIGHT_VEHICLE:
            my, other, confidence = 30, 70, 0.76
        elif user_vehicle_role == LANE_CHANGING_VEHICLE:
            my, other, confidence = 70, 30, 0.76
        else:
            my, other, confidence = (30 if not facts.get("lane_change") else 45), (70 if not facts.get("lane_change") else 55), 0.62
        fault_estimate_source = "scenario_default"
    elif scenario_type in ("pedestrian_crosswalk_accident", "school_zone_child_accident"):
        my, other, confidence = 70, 30, 0.55
        fault_estimate_source = "scenario_default"
    else:
        my, other, confidence = 50, 50, 0.42
        fault_estimate_source = "scenario_default"

    basis = "사고 유형, 구조화 입력, 법률 RAG 근거를 함께 반영한 참고용 과실 추정입니다."
    if knia:
        basis = "KNIA 과실비율 인정기준과 법률 RAG 근거를 함께 반영한 참고용 과실 추정입니다."
    return attach_llm_usage(guard_fault_ratio_output({
        "my": my,
        "other": other,
        "confidence": confidence,
        "basis": basis,
        "evidence_count": len(evidence),
        "key_factors": key_factors,
        "user_vehicle_role": user_vehicle_role,
        "fault_estimate_source": fault_estimate_source,
        "evidence_ids": [ev.get("chunk_id") for ev in evidence[:6] if ev.get("chunk_id")],
    }, evidence), llm_usage, used=False)


def _normalize(data: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    data.setdefault("evidence_count", len(evidence))
    data.setdefault("evidence_ids", [ev.get("chunk_id") for ev in evidence[:6] if ev.get("chunk_id")])
    data.setdefault("key_factors", ["AI 분석", "RAG 근거", "KNIA 기준"])
    return data


def _centerline_obstacle_stop_context(facts: dict[str, Any]) -> bool:
    reason = str(facts.get("centerline_cross_reason") or facts.get("analysis_uncertainty") or "")
    return facts.get("centerline_crossed") is True and facts.get("stopped") is True and any(
        token in reason for token in ("주차", "장애", "obstacle", "parking")
    )


def _unlit_stopped_vehicle_context(facts: dict[str, Any]) -> bool:
    if facts.get("stopped_vehicle_without_lights") is True:
        return True
    text = " ".join(str(facts.get(key) or "") for key in ("opponent_behavior", "accident_type", "analysis_uncertainty"))
    return any(token in text for token in ("무등화", "스텔스", "unlit", "without lights"))


def _bicycle_trigger_rear_end_context(facts: dict[str, Any]) -> bool:
    trigger = str(facts.get("possible_trigger_vehicle") or facts.get("bicycle_behavior") or "").lower()
    return (
        (facts.get("bicycle_involved") is True or "bicycle" in trigger or "자전거" in trigger)
        and (facts.get("rear_vehicle_collision") is True or facts.get("stopped") is True)
    )


def _uncertain_signal_transition_context(facts: dict[str, Any]) -> bool:
    signal_state = str(facts.get("signal_state") or facts.get("analysis_uncertainty") or "")
    return (
        facts.get("signal_timing_uncertain") is True
        or facts.get("cctv_needed") is True
        or ("황색" in signal_state and "적색" in signal_state)
    )
