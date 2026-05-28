from __future__ import annotations

from typing import Any

from app.services.knia.adjustments.base import AdjustmentEvaluation, pair


def evaluate(**kwargs: Any) -> AdjustmentEvaluation:
    base = pair(60)
    return AdjustmentEvaluation(base_fault=base, final_fault=base, fault_range={"my": "40~80%", "other": "20~60%"}, policy={"id": "bicycle_reference"})
