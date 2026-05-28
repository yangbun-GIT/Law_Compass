from __future__ import annotations

from typing import Any

from app.services.accident_perspective import LANE_CHANGING_VEHICLE, map_fault_ratio_to_user
from app.services.knia.adjustments.base import AdjustmentEvaluation, pair


def evaluate(**kwargs: Any) -> AdjustmentEvaluation:
    facts = kwargs.get("facts") or {}
    estimate = kwargs.get("knia_fault_estimate") or {}
    description_text = kwargs.get("description_text") or ""
    scenario_type = kwargs.get("scenario_type") or "lane_change_collision"
    source_chart = estimate.get("source_chart")
    base = _mapped_knia_fault(estimate, scenario_type, description_text, facts)
    if not base:
        base = pair(30 if facts.get("lane_change_actor") == "opponent" else 70 if facts.get("lane_change_actor") == "user" else 40)
    final = dict(base)
    applied = []
    if facts.get("turn_signal") in {"no", "not_used", False}:
        applied.append({"factor_id": "turn_signal_not_used", "label": "방향지시등 미사용", "delta_my": -10, "reason": "차선변경 차량의 방향지시등 미사용은 해당 차량 과실 가산 요소입니다."})
        role = map_fault_ratio_to_user(scenario_type=scenario_type, fault=(estimate.get("final_fault") or {}), text=description_text, facts=facts).get("user_vehicle_role")
        if role == LANE_CHANGING_VEHICLE:
            final = pair(min(base["my"] + 10, 100))
        else:
            final = pair(max(base["my"] - 10, 0))
    return AdjustmentEvaluation(
        base_fault=base,
        final_fault=final,
        fault_range={"my": f"{max(final['my'] - 10, 0)}~{min(final['my'] + 10, 100)}%", "other": f"{max(final['other'] - 10, 0)}~{min(final['other'] + 10, 100)}%"},
        applied_adjustments=applied,
        source_chart=source_chart,
        confidence=0.72 if source_chart else 0.45,
        policy={"id": "lane_change_reference", "uses_knia_role_mapping": bool(source_chart)},
    )


def _mapped_knia_fault(
        estimate: dict[str, Any],
        scenario_type: str,
        description_text: str,
        facts: dict[str, Any],
) -> dict[str, int] | None:
    fault = estimate.get("final_fault") or estimate.get("base_fault") or {}
    if isinstance(fault.get("my"), int) and isinstance(fault.get("other"), int):
        return pair(fault["my"], fault["other"])
    if isinstance(fault.get("A"), int) and isinstance(fault.get("B"), int):
        mapped = map_fault_ratio_to_user(
            scenario_type=scenario_type,
            fault=fault,
            text=description_text,
            facts=facts,
        )
        if isinstance(mapped.get("my"), int) and isinstance(mapped.get("other"), int):
            return pair(mapped["my"], mapped["other"])
    return None
