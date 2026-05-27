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

    signal_uncertainty = _uncertain_signal_transition_context(facts, text)
    conditional_outcomes: list[dict[str, Any]] = []
    centerline_context = _centerline_obstacle_context(facts, text)
    if centerline_context:
        stopped_or_nearly_stopped = centerline_context.get("stopped_or_nearly_stopped")
        opposing_non_stop = centerline_context.get("opposing_non_stop")
        my, other = (30, 70) if stopped_or_nearly_stopped and opposing_non_stop else (40, 60)
        confidence = 0.68 if stopped_or_nearly_stopped and opposing_non_stop else 0.61
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
    elif signal_uncertainty:
        my, other, confidence = 80, 20, 0.55
        key_factors = ["신호 전환 시점", "내 차량 진입 신호", "상대 차량 진입 신호", "CCTV·신호체계 확인", "좌회전 차량과 직진 차량의 주의의무"]
        conditional_outcomes = [
            {
                "label": "상대 차량 신호가 녹색 또는 정상 진행 신호인 경우",
                "my_range": "70~90%",
                "other_range": "10~30%",
                "explanation": "내 차량이 좌회전 중 황색 전환 뒤 교차로를 계속 진행했고 상대 차량은 정상 직진 신호였다고 확인되면, 좌회전·신호 전환 차량의 진입 시점과 양보 의무가 더 무겁게 평가될 수 있습니다.",
                "basis": ["내 차량 정지선 통과 시점", "황색에서 적색으로 바뀐 시점", "좌회전 차량의 진입 가능성", "상대 차량의 정상 진행 신호 여부"],
            },
            {
                "label": "상대 차량도 적색 또는 신호위반으로 진입한 경우",
                "my_range": "20~40%",
                "other_range": "60~80%",
                "explanation": "상대 차량의 진행 신호가 적색이었거나 신호위반 진입이 확인되면, 상대 차량의 신호준수·전방주시 의무 위반이 중심 쟁점이 되어 상대 책임이 커질 수 있습니다.",
                "basis": ["상대 차량 신호 색상", "상대 차량 정지선 통과 시점", "교차로 CCTV", "신호 주기표 또는 신호체계 자료"],
            },
        ]
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
    payload = {
        "my": my,
        "other": other,
        "confidence": confidence,
        "basis": basis,
        "evidence_count": len(evidence),
        "key_factors": key_factors,
        "user_vehicle_role": user_vehicle_role,
        "fault_estimate_source": fault_estimate_source,
        "evidence_ids": [ev.get("chunk_id") for ev in evidence[:6] if ev.get("chunk_id")],
    }
    if scenario_type == "rear_end_collision" and user_vehicle_role == FRONT_VEHICLE:
        payload["caveats"] = [
            "기본적으로 뒤차 과실이 높게 검토되지만, 이유 없는 급정지, 제동등 고장, 비정상 정차, 선행사고 후 도로상 정차, 야간 무등화, 시야장애 여부는 추가 확인이 필요합니다."
        ]
        payload["adjustment_review_factors"] = ["급정지", "제동등", "비정상 정차", "선행사고 후 정차", "야간 무등화", "시야장애"]
    if conditional_outcomes:
        payload["conditional_outcomes"] = conditional_outcomes
        payload["basis"] = "상대 차량 신호가 확인되지 않은 교차로 사고라서, 신호 조건별 과실 범위를 나누어 제시한 참고용 추정입니다."
    return attach_llm_usage(guard_fault_ratio_output(payload, evidence), llm_usage, used=False)


def _normalize(data: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    data.setdefault("evidence_count", len(evidence))
    data.setdefault("evidence_ids", [ev.get("chunk_id") for ev in evidence[:6] if ev.get("chunk_id")])
    data.setdefault("key_factors", ["AI 분석", "RAG 근거", "KNIA 기준"])
    return data


def _centerline_obstacle_context(facts: dict[str, Any], text: str = "") -> dict[str, bool] | None:
    haystack = " ".join(
        [
            text or "",
            str(facts.get("accident_type") or ""),
            str(facts.get("centerline_cross_reason") or ""),
            str(facts.get("opponent_behavior") or ""),
            str(facts.get("analysis_uncertainty") or ""),
        ]
    ).lower()
    centerline = facts.get("centerline_crossed") is True or any(
        token in haystack for token in ("중앙선", "황색 실선", "centerline", "yellow line")
    )
    obstruction = (
        facts.get("road_obstruction") is True
        or facts.get("illegal_parking_obstruction") is True
        or any(token in haystack for token in ("주차", "주정차", "불법", "장애", "가구", "사물", "obstacle", "parking"))
    )
    oncoming = facts.get("opposing_vehicle_present") is True or any(
        token in haystack for token in ("마주오", "대향", "반대편", "상대차", "oncoming")
    ) or facts.get("accident_type") == "centerline_obstacle_collision"
    if not (centerline and obstruction and oncoming):
        return None
    stopped_or_nearly_stopped = facts.get("stopped") is True or any(
        token in haystack for token in ("멈췄", "멈춘", "정차", "정지", "거의 멈", "감속")
    )
    opposing_non_stop = facts.get("opposing_vehicle_did_not_stop") is True or any(
        token in haystack for token in ("그대로", "달려", "못봤", "못 봤", "멈추지", "감속하지")
    ) or facts.get("accident_type") == "centerline_obstacle_collision"
    return {
        "stopped_or_nearly_stopped": stopped_or_nearly_stopped,
        "opposing_non_stop": opposing_non_stop,
    }


def _unlit_stopped_vehicle_context(facts: dict[str, Any]) -> bool:
    if facts.get("stopped_vehicle_without_lights") is True:
        return True
    text = " ".join(str(facts.get(key) or "") for key in ("opponent_behavior", "accident_type", "analysis_uncertainty"))
    return any(token in text for token in ("무등화", "스텔스", "unlit", "without lights"))


def _bicycle_trigger_rear_end_context(facts: dict[str, Any]) -> bool:
    trigger = str(facts.get("trigger_actor_type") or facts.get("possible_trigger_vehicle") or facts.get("bicycle_behavior") or "").lower()
    return (
        (
            facts.get("non_contact_trigger") is True
            or facts.get("bicycle_involved") is True
            or "bicycle" in trigger
            or "자전거" in trigger
        )
        and (
            facts.get("rear_vehicle_collision") is True
            or facts.get("direct_collision_partner_type") == "vehicle"
            or facts.get("stopped") is True
        )
    )


def _uncertain_signal_transition_context(facts: dict[str, Any], text: str = "") -> bool:
    signal_state = str(facts.get("signal_state") or facts.get("analysis_uncertainty") or "")
    haystack = " ".join([
        text or "",
        signal_state,
        str(facts.get("signal_transition") or ""),
        str(facts.get("user_signal") or ""),
        str(facts.get("opponent_signal") or ""),
        str(facts.get("opponent_behavior") or ""),
    ]).lower()
    return (
        facts.get("signal_timing_uncertain") is True
        or facts.get("cctv_needed") is True
        or (facts.get("intersection") is True and facts.get("opponent_signal_visible") is False and bool(facts.get("user_signal") or facts.get("signal_transition")))
        or ("황색" in signal_state and "적색" in signal_state)
        or ("yellow" in haystack and "red" in haystack and ("left" in haystack or "좌회전" in haystack or facts.get("ego_turn_direction") == "left"))
    )
