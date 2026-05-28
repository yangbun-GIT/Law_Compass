from __future__ import annotations

from typing import Any

from app.services.knia.adjustments import bicycle, centerline, intersection, lane_change, motorcycle, object_collision, parking_stopped_vehicle, pedestrian, rear_end
from app.services.knia.adjustments.base import AdjustmentEvaluation, pair
from app.services.knia.party_guard import canonicalize_party_type


def evaluate_adjustments(
    scenario_type: str,
    party_type: str,
    facts: dict[str, Any],
    knia_fault_estimate: dict[str, Any] | None,
    description_text: str,
) -> dict[str, Any]:
    party = canonicalize_party_type(party_type or facts.get("knia_major_party_type") or facts.get("accident_party_type"))
    kwargs = {
        "scenario_type": scenario_type,
        "party_type": party,
        "facts": facts,
        "knia_fault_estimate": knia_fault_estimate,
        "description_text": description_text,
    }
    if party == "car_vs_car":
        if scenario_type == "rear_end_collision":
            return rear_end.evaluate(**kwargs).to_dict()
        if scenario_type == "lane_change_collision":
            return lane_change.evaluate(**kwargs).to_dict()
        if scenario_type in {"intersection_signal_violation", "intersection_collision"}:
            return intersection.evaluate(**kwargs).to_dict()
        if scenario_type == "centerline_obstacle_collision":
            return centerline.evaluate(**kwargs).to_dict()
        if scenario_type in {"parking_or_stopped_vehicle_accident", "stealth_illegal_parked_vehicle_collision"}:
            return parking_stopped_vehicle.evaluate(**kwargs).to_dict()
        if scenario_type in {"drunk_or_unlicensed_accident", "hit_and_run_risk"}:
            base = _base_from_estimate(knia_fault_estimate)
            return AdjustmentEvaluation(
                base_fault=base,
                final_fault=base,
                fault_range={"my": f"{base['my']}~{min(base['my'] + 20, 100)}%", "other": f"{max(base['other'] - 20, 0)}~{base['other']}%"},
                not_applied_adjustments=[{"factor_id": scenario_type, "label": "12대 중과실 또는 형사 위험", "reason": "대분류나 민사 과실 100:0 자동 확정 사유가 아니라 위험 태그로만 반영합니다."}],
                policy={"id": "risk_tag_only", "civil_fault_not_auto_100_0": True},
                confidence=0.5,
            ).to_dict()
    if party == "car_vs_person":
        return pedestrian.evaluate(**kwargs).to_dict()
    if party == "car_vs_bicycle":
        return bicycle.evaluate(**kwargs).to_dict()
    if party == "car_vs_motorcycle":
        return motorcycle.evaluate(**kwargs).to_dict()
    if party in {"car_vs_object", "single_vehicle"}:
        return object_collision.evaluate(**kwargs).to_dict()
    base = _base_from_estimate(knia_fault_estimate)
    return AdjustmentEvaluation(base_fault=base, final_fault=base, fault_range={"my": f"{base['my']}%", "other": f"{base['other']}%"}, policy={"id": "no_adjustment_registry_match"}).to_dict()


def _base_from_estimate(estimate: dict[str, Any] | None) -> dict[str, int]:
    base = (estimate or {}).get("final_fault") or (estimate or {}).get("base_fault") or {}
    if isinstance(base.get("my"), int) and isinstance(base.get("other"), int):
        return pair(base["my"], base["other"])
    if isinstance(base.get("A"), int) and isinstance(base.get("B"), int):
        return pair(base["A"], base["B"])
    return pair(50, 50)
