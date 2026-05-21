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
from app.services.llm_policy import attach_llm_usage, evaluate_llm_usage


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

    knia = next((ev for ev in evidence if ev.get("source_type") == "knia_fault_standard"), None)
    user_vehicle_role = infer_user_vehicle_role(text, facts, scenario_type)
    if scenario_type == "rear_end_collision":
        if user_vehicle_role == FRONT_VEHICLE:
            my, other, confidence = 0, 100, 0.82
        elif user_vehicle_role == FOLLOWING_VEHICLE:
            my, other, confidence = 100, 0, 0.82
        else:
            my, other, confidence = (10 if facts.get("stopped") else 20), (90 if facts.get("stopped") else 80), 0.74
    elif scenario_type == "intersection_signal_violation":
        if user_vehicle_role == SIGNAL_COMPLIANT_VEHICLE:
            my, other, confidence = 0, 100, 0.78
        elif user_vehicle_role == SIGNAL_VIOLATION_VEHICLE:
            my, other, confidence = 100, 0, 0.78
        else:
            my, other, confidence = (15 if facts.get("opponent_signal_violation") else 45), (85 if facts.get("opponent_signal_violation") else 55), 0.68
    elif scenario_type == "lane_change_collision":
        if user_vehicle_role == STRAIGHT_VEHICLE:
            my, other, confidence = 30, 70, 0.76
        elif user_vehicle_role == LANE_CHANGING_VEHICLE:
            my, other, confidence = 70, 30, 0.76
        else:
            my, other, confidence = (30 if not facts.get("lane_change") else 45), (70 if not facts.get("lane_change") else 55), 0.62
    elif scenario_type in ("pedestrian_crosswalk_accident", "school_zone_child_accident"):
        my, other, confidence = 70, 30, 0.55
    else:
        my, other, confidence = 50, 50, 0.42

    basis = "사고 유형, 구조화 입력, 법률 RAG 근거를 함께 반영한 참고용 과실 추정입니다."
    if knia:
        basis = "KNIA 과실비율 인정기준과 법률 RAG 근거를 함께 반영한 참고용 과실 추정입니다."
    return attach_llm_usage(guard_fault_ratio_output({
        "my": my,
        "other": other,
        "confidence": confidence,
        "basis": basis,
        "evidence_count": len(evidence),
        "key_factors": ["사고 유형", "신호·정차·차선변경 여부", "인명피해 여부", "관련 법규와 KNIA 기준"],
        "user_vehicle_role": user_vehicle_role,
        "evidence_ids": [ev.get("chunk_id") for ev in evidence[:6] if ev.get("chunk_id")],
    }, evidence), llm_usage, used=False)


def _normalize(data: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    data.setdefault("evidence_count", len(evidence))
    data.setdefault("evidence_ids", [ev.get("chunk_id") for ev in evidence[:6] if ev.get("chunk_id")])
    data.setdefault("key_factors", ["AI 분석", "RAG 근거", "KNIA 기준"])
    return data
