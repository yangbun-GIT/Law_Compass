from __future__ import annotations

from typing import Any

from app.services.knia.adjustments.base import AdjustmentEvaluation, pair


def evaluate(**kwargs: Any) -> AdjustmentEvaluation:
    facts = kwargs.get("facts") or {}
    stealth = facts.get("is_stealth_parked_vehicle_collision") is True
    speed_over_limit = _speed_over_limit(facts)
    if stealth and speed_over_limit:
        base = pair(40, 60)
        fault_range = {"my": "20~40%", "other": "60~80%"}
    else:
        base = pair(10 if stealth else 30, 90 if stealth else 70)
        fault_range = {"my": "0~30%", "other": "70~100%"}
    conditional = [
        {"label": "야간 무등화/스텔스인 경우", "my_range": "0~20%", "other_range": "80~100%", "explanation": "등화 부재, 비정상 위치, 회피 불가능성이 입증되면 상대 책임을 강하게 주장할 수 있습니다."},
        {"label": "과속 확인 시", "my_range": "20~40%", "other_range": "60~80%", "explanation": "내 차량 과속이 확인되면 회피 가능성 평가가 불리해질 수 있습니다."},
    ]
    applied = []
    if facts.get("stopped_vehicle_without_lights"):
        applied.append({"factor_id": "unlit_stopped_vehicle", "label": "무등화 정차 차량", "delta_my": -10, "reason": "상대 차량 식별 곤란 요소를 반영합니다."})
    if speed_over_limit:
        applied.append({"factor_id": "speeding_over_limit", "label": "제한속도 초과", "delta_my": 30 if stealth else 10, "reason": "과속 사실이 있으면 회피 가능성 판단에서 내 차량 책임이 커질 수 있습니다."})
    return AdjustmentEvaluation(base_fault=base, final_fault=base, fault_range=fault_range, applied_adjustments=applied, conditional_outcomes=conditional, policy={"id": "parking_stopped_vehicle_reference"})


def _speed_over_limit(facts: dict[str, Any]) -> bool:
    reported = _to_float(facts.get("reported_speed_kmh") or facts.get("ego_speed_kmh") or facts.get("speed_kmh"))
    limit = _to_float(facts.get("speed_limit_kmh"))
    if reported is None or limit is None:
        return bool(facts.get("speeding") or facts.get("overspeeding") or facts.get("speeding_over_limit"))
    return reported > limit


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
