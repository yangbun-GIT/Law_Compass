from __future__ import annotations

from typing import Any

from app.services.knia.adjustments.base import AdjustmentEvaluation, pair


def evaluate(**kwargs: Any) -> AdjustmentEvaluation:
    base = pair(70)
    return AdjustmentEvaluation(base_fault=base, final_fault=base, fault_range={"my": "60~90%", "other": "10~40%"}, policy={"id": "pedestrian_reference"})
