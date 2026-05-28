from __future__ import annotations

from typing import Any

from app.services.knia.adjustments.base import AdjustmentEvaluation, pair


def evaluate(**kwargs: Any) -> AdjustmentEvaluation:
    facts = kwargs.get("facts") or {}
    stealth = facts.get("is_stealth_parked_vehicle_collision") is True
    base = pair(10 if stealth else 30, 90 if stealth else 70)
    conditional = [
        {"label": "야간 무등화/스텔스인 경우", "my_range": "0~20%", "other_range": "80~100%", "explanation": "등화 부재, 비정상 위치, 회피 불가능성이 입증되면 상대 책임을 강하게 주장할 수 있습니다."},
        {"label": "과속 확인 시", "my_range": "20~40%", "other_range": "60~80%", "explanation": "내 차량 과속이 확인되면 회피 가능성 평가가 불리해질 수 있습니다."},
    ]
    applied = []
    if facts.get("stopped_vehicle_without_lights"):
        applied.append({"factor_id": "unlit_stopped_vehicle", "label": "무등화 정차 차량", "delta_my": -10, "reason": "상대 차량 식별 곤란 요소를 반영합니다."})
    return AdjustmentEvaluation(base_fault=base, final_fault=base, fault_range={"my": "0~30%", "other": "70~100%"}, applied_adjustments=applied, conditional_outcomes=conditional, policy={"id": "parking_stopped_vehicle_reference"})
