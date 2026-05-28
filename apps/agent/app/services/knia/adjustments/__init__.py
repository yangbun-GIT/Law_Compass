from __future__ import annotations

from app.services.knia.adjustments.base import AdjustmentEvaluation

__all__ = ["AdjustmentEvaluation", "evaluate_adjustments"]


def evaluate_adjustments(*args, **kwargs):
    from app.services.knia.adjustments.registry import evaluate_adjustments as _evaluate_adjustments

    return _evaluate_adjustments(*args, **kwargs)
