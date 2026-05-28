from __future__ import annotations

from typing import Any

from app.services.knia.adjustments.base import AdjustmentEvaluation, pair


def evaluate(**kwargs: Any) -> AdjustmentEvaluation:
    facts = kwargs.get("facts") or {}
    base = pair(30 if facts.get("lane_change_actor") == "opponent" else 70 if facts.get("lane_change_actor") == "user" else 40)
    applied = []
    if facts.get("turn_signal") in {"no", "not_used", False}:
        applied.append({"factor_id": "turn_signal_not_used", "label": "방향지시등 미사용", "delta_my": -10, "reason": "차선변경 차량의 방향지시등 미사용은 해당 차량 과실 가산 요소입니다."})
    return AdjustmentEvaluation(base_fault=base, final_fault=base, fault_range={"my": "30~70%", "other": "30~70%"}, applied_adjustments=applied, policy={"id": "lane_change_reference"})
