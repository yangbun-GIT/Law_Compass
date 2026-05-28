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
    extra_payload: dict[str, Any] = {}
    stealth_context = _stealth_illegal_parked_vehicle_context(facts, text, scenario_type)
    centerline_context = _centerline_obstacle_context(facts, text)
    if stealth_context:
        score = _stealth_illegal_parked_vehicle_score(facts, text)
        my = score["my"]
        other = score["other"]
        confidence = score["confidence"]
        key_factors = score["key_factors"]
        conditional_outcomes = score["conditional_outcomes"]
        extra_payload = score["extra_payload"]
        fault_estimate_source = "stealth_illegal_parked_vehicle_rule"
    elif centerline_context:
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
        "base_fault": {"my": my, "other": other},
        "final_fault": {"my": my, "other": other},
        "fault_range": {"my": f"{my}%", "other": f"{other}%"},
        "applied_adjustments": [],
        "not_applied_adjustments": [],
        "unknown_adjustments": [],
        "conditional_outcomes": conditional_outcomes,
        "knia_reference_fault": None,
        "knia_adjustment_policy": {"stage": "scenario_default_before_knia_registry"},
        "no_knia_match_reason": None if knia else "no_knia_fault_standard_in_evidence",
        "confidence": confidence,
        "basis": basis,
        "evidence_count": len(evidence),
        "key_factors": key_factors,
        "user_vehicle_role": user_vehicle_role,
        "fault_estimate_source": fault_estimate_source,
        "evidence_ids": [ev.get("chunk_id") for ev in evidence[:6] if ev.get("chunk_id")],
    }
    if extra_payload:
        payload.update(extra_payload)
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



def _stealth_illegal_parked_vehicle_context(facts: dict[str, Any], text: str = "", scenario_type: str = "") -> bool:
    haystack = " ".join(
        [
            text or "",
            scenario_type or "",
            str(facts.get("accident_type") or ""),
            str(facts.get("accident_subtype") or ""),
            str(facts.get("collision_target") or ""),
            str(facts.get("parked_vehicle_position") or ""),
            str(facts.get("parked_vehicle_lighting") or ""),
            str(facts.get("visibility_condition") or ""),
            str(facts.get("opponent_impairment") or ""),
            str(facts.get("analysis_uncertainty") or ""),
            ]
    ).lower()

    if scenario_type == "stealth_illegal_parked_vehicle_collision":
        return True
    if facts.get("is_stealth_parked_vehicle_collision") is True:
        return True

    collision = any(token in haystack for token in ("부딪", "충돌", "박", "들이받", "들이박", "파손", "폐차"))
    parked_vehicle = any(
        token in haystack
        for token in ("주차", "정차", "방치", "트럭", "화물차", "parked", "stopped vehicle", "truck")
    )
    visibility_risk = (
            facts.get("stopped_vehicle_without_lights") is True
            or facts.get("night_no_lights_or_low_visibility") is True
            or any(token in haystack for token in ("스텔스", "무등화", "미등", "비상등", "차폭등", "야간", "밤", "교량 밑", "교량 아래", "unlit"))
    )
    abnormal_or_drunk = (
            facts.get("abnormal_parking") is True
            or facts.get("opponent_drunk_or_abnormal_operation") is True
            or any(token in haystack for token in ("화단", "중앙분리대", "통행 공간", "음주", "음주운전", "drunk"))
    )

    return collision and parked_vehicle and (visibility_risk or abnormal_or_drunk)


def _stealth_illegal_parked_vehicle_score(facts: dict[str, Any], text: str = "") -> dict[str, Any]:
    haystack = " ".join(
        [
            text or "",
            str(facts.get("collision_target") or ""),
            str(facts.get("parked_vehicle_position") or ""),
            str(facts.get("parked_vehicle_lighting") or ""),
            str(facts.get("visibility_condition") or ""),
            str(facts.get("opponent_impairment") or ""),
            str(facts.get("avoidability") or ""),
            ]
    ).lower()

    reasoning: list[str] = []
    opponent_score = 60

    is_unlit = (
            facts.get("stopped_vehicle_without_lights") is True
            or str(facts.get("parked_vehicle_lighting") or "") in {"unlit_stealth", "no_lights", "unknown_but_dark"}
            or any(token in haystack for token in ("스텔스", "무등화", "미등", "비상등", "차폭등", "unlit"))
    )
    is_dark = (
            facts.get("night_no_lights_or_low_visibility") is True
            or str(facts.get("visibility_condition") or "") in {"night_dark", "under_bridge_dark", "low_visibility"}
            or any(token in haystack for token in ("야간", "밤", "늦은 밤", "새벽", "어두", "교량 밑", "교량 아래"))
    )
    abnormal_position = (
            facts.get("abnormal_parking") is True
            or str(facts.get("parked_vehicle_position") or "") in {"traffic_space", "flowerbed_or_median", "under_bridge", "roadside"}
            or any(token in haystack for token in ("화단", "중앙분리대", "통행 공간", "갓길", "교량 밑", "교량 아래"))
    )
    drunk = (
            facts.get("opponent_drunk_or_abnormal_operation") is True
            or str(facts.get("opponent_impairment") or "") in {"drunk_driving_confirmed", "suspected_drunk"}
            or any(token in haystack for token in ("음주", "음주운전", "만취", "술", "drunk"))
    )
    hard_to_avoid = (
            facts.get("low_avoidability") is True
            or str(facts.get("avoidability") or "") in {"limited", "nearly_impossible"}
            or any(token in haystack for token in ("피하지 못", "발견 즉시", "회피 불가", "못 피"))
    )

    if is_unlit:
        opponent_score += 10
        reasoning.append("상대 차량이 야간에 미등·비상등·차폭등 등 식별 조치가 없는 스텔스 상태로 보입니다.")
    if is_dark:
        opponent_score += 8
        reasoning.append("야간 또는 교량 아래 조도 불량으로 후속 차량의 발견 가능성이 낮습니다.")
    if abnormal_position:
        opponent_score += 10
        reasoning.append("상대 차량이 화단, 교량 아래, 통행 공간 등 정상 주차구역이 아닌 위험 위치에 있었습니다.")
    if drunk:
        opponent_score += 7
        reasoning.append("상대 차량의 음주운전 또는 음주운전 기인 비정상 정차 정황이 있어 상대 과실 가산 요소입니다.")
    if hard_to_avoid:
        opponent_score += 5
        reasoning.append("충돌 직전 발견·회피 가능성이 낮은 정황이 있어 내 차량 과실 감산 요소입니다.")

    opponent_score = max(80, min(opponent_score, 90))
    my_score = 100 - opponent_score

    can_argue_100_0 = is_unlit and is_dark and abnormal_position and drunk and hard_to_avoid
    if can_argue_100_0:
        my_score, opponent_score = 0, 100
        confidence = 0.62
        reasoning.append("위 조건이 모두 사실로 입증되면 상대 100 대 내 차량 0 주장을 별도로 제시할 수 있습니다.")
    else:
        confidence = 0.66 if opponent_score >= 90 else 0.61

    return {
        "my": my_score,
        "other": opponent_score,
        "confidence": confidence,
        "key_factors": [
            "야간 스텔스 정차 차량",
            "비정상 주차 위치",
            "등화·경고조치 부재",
            "상대 음주운전 정황",
            "발견·회피 가능성",
        ],
        "conditional_outcomes": [
            {
                "label": "현실적 협상 기준",
                "my_range": "10~20%",
                "other_range": "80~90%",
                "explanation": "야간, 스텔스, 비정상 위치, 음주운전 기인 정차가 인정되면 상대 차량 과실을 80~90%로 강하게 주장할 수 있습니다.",
                "basis": ["블랙박스", "현장 사진", "등화 상태", "주차 위치", "음주운전 확인 자료"],
            },
            {
                "label": "100:0 주장 가능 조건",
                "my_range": "0%",
                "other_range": "100%",
                "explanation": "내 차량의 과속·전방주시 태만이 없고, 상대 차량이 통행 공간에 식별 불가능한 상태로 있었으며 회피가 거의 불가능했다는 점이 입증되어야 합니다.",
                "basis": ["속도 자료", "조도", "교량 아래 시야", "상대 차량 등화", "충돌 직전 인지 가능성"],
            },
        ],
        "extra_payload": {
            "scenario_subtype": "night_unlit_illegal_parked_vehicle_collision",
            "recommended_claim": "상대 차량 100 : 내 차량 0을 우선 주장하되, 현실 목표는 상대 90 : 내 차량 10, 최소 수용선은 상대 80 : 내 차량 20입니다.",
            "legal_caution": "음주운전은 형사상 중대 위반이자 민사상 강한 과실 가산 요소이지만, 그 자체만으로 민사 과실 100:0이 자동 확정되는 것은 아닙니다.",
            "adjustment_review_factors": [
                "상대 차량 음주운전 확인 여부",
                "미등·비상등·차폭등 점등 여부",
                "교량 아래 조도와 시야",
                "화단 또는 통행 공간 침범 정도",
                "내 차량 과속 여부",
                "충돌 직전 회피 가능성",
            ],
            "reasoning": reasoning,
        },
    }

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
