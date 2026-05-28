from __future__ import annotations

from typing import Any

from app.services.knia.adjustments.base import AdjustmentEvaluation, pair


def evaluate(**kwargs: Any) -> AdjustmentEvaluation:
    base = pair(100)
    return AdjustmentEvaluation(base_fault=base, final_fault=base, fault_range={"my": "70~100%", "other": "0~30%"}, policy={"id": "object_collision_reference"})
