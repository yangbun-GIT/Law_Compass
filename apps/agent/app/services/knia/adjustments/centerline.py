from __future__ import annotations

from typing import Any

from app.services.knia.adjustments.base import AdjustmentEvaluation, pair


def evaluate(**kwargs: Any) -> AdjustmentEvaluation:
    base = pair(30)
    return AdjustmentEvaluation(base_fault=base, final_fault=base, fault_range={"my": "20~40%", "other": "60~80%"}, conditional_outcomes=[{"label": "장애물 회피가 불가피한 경우", "my_range": "20~40%", "other_range": "60~80%", "explanation": "중앙선 침범 사유와 상대 차량 감속 가능성을 함께 봅니다."}], policy={"id": "centerline_obstacle_reference"})
