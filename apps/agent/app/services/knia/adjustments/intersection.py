from __future__ import annotations

from typing import Any

from app.services.knia.adjustments.base import AdjustmentEvaluation, pair


def evaluate(**kwargs: Any) -> AdjustmentEvaluation:
    facts = kwargs.get("facts") or {}
    base = pair(0 if facts.get("opponent_signal_violation") else 100 if facts.get("user_signal_violation") else 45)
    conditional = [
        {"label": "상대 신호위반이 확인되는 경우", "my_range": "0~20%", "other_range": "80~100%", "explanation": "상대 적색 진입이 확인되면 상대 책임이 중심입니다."},
        {"label": "상대 신호가 정상 진행 신호인 경우", "my_range": "60~90%", "other_range": "10~40%", "explanation": "내 차량의 진입 신호와 양보 의무가 더 무겁게 평가될 수 있습니다."},
    ]
    return AdjustmentEvaluation(base_fault=base, final_fault=base, fault_range={"my": "0~90%", "other": "10~100%"}, conditional_outcomes=conditional, policy={"id": "intersection_signal_reference"})
