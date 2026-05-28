from __future__ import annotations

from typing import Any

from app.services.knia.adjustments.base import AdjustmentEvaluation, pair


def evaluate(**kwargs: Any) -> AdjustmentEvaluation:
    base = pair(50)
    return AdjustmentEvaluation(base_fault=base, final_fault=base, fault_range={"my": "30~70%", "other": "30~70%"}, policy={"id": "motorcycle_reference"})
