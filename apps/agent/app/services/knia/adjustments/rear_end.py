from __future__ import annotations

from typing import Any

from app.services.accident_perspective import FRONT_VEHICLE, FOLLOWING_VEHICLE, infer_user_vehicle_role, map_fault_ratio_to_user
from app.services.knia.adjustments.base import AdjustmentEvaluation, pair


def evaluate(
    *,
    scenario_type: str,
    party_type: str,
    facts: dict[str, Any],
    knia_fault_estimate: dict[str, Any] | None,
    description_text: str,
) -> AdjustmentEvaluation:
    source_chart = (knia_fault_estimate or {}).get("source_chart") or {}
    base = _base_fault(scenario_type, facts, knia_fault_estimate, description_text)
    my = base["my"]
    other = base["other"]
    applied: list[dict[str, Any]] = []
    not_applied: list[dict[str, Any]] = []
    unknown: list[dict[str, Any]] = []
    conditional: list[dict[str, Any]] = [
        {
            "label": "일반적인 신호대기·정체 정차 후 후방추돌",
            "my_range": "0~10%",
            "other_range": "90~100%",
            "explanation": "앞차가 정당하게 정차했고 뒤차가 추돌한 구조라면 뒤차 책임을 중심으로 봅니다.",
        }
    ]

    sudden = _truthy(facts.get("sudden_brake")) or _text_has(description_text, ("급정거", "급제동", "갑자기 멈"))
    stop_reason = _stop_reason(facts, description_text)
    if sudden and stop_reason in {"red_light", "traffic", "pedestrian_or_obstacle", "lawful"}:
        not_applied.append(_not_applied("sudden_brake_without_reason", "이유 없는 급정거", "정당한 정차 사유가 확인되어 적용하지 않았습니다."))
    elif sudden and stop_reason == "no_reason":
        my, other = _apply_delta(my, 10)
        applied.append(_applied("sudden_brake_without_reason", "이유 없는 급정거", 10, "정상적인 이유 없는 급정거로 확인되면 앞차 과실이 일부 증가할 수 있습니다."))
        conditional.append({"label": "이유 없는 급정거인 경우", "my_range": f"{my}~{min(my + 10, 100)}%", "other_range": f"{max(other - 10, 0)}~{other}%", "explanation": "급정거가 불필요했다는 점이 입증되면 앞차 과실이 가산될 수 있습니다."})
    elif sudden:
        unknown.append(_unknown("sudden_brake_without_reason", "급정거 사유", "급정거 사유가 확인되면 앞차 과실 가산 여부가 달라질 수 있습니다.", "0~10%p"))
        conditional.append({"label": "이유 없는 급정거로 확인되는 경우", "my_range": f"{my}~{min(my + 10, 100)}%", "other_range": f"{max(other - 10, 0)}~{other}%", "explanation": "정당한 정차 사유가 없었다면 앞차 과실이 일부 늘 수 있습니다."})

    brake_light = _brake_light_state(facts, description_text)
    if brake_light == "failed":
        my, other = _apply_delta(my, 10)
        applied.append(_applied("brake_light_failure", "제동등 고장 또는 미점등", 10, "브레이크등 고장 또는 미점등이 확인되어 앞차 과실을 일부 반영했습니다."))
        conditional.append({"label": "브레이크등 고장인 경우", "my_range": f"{my}~{min(my + 5, 100)}%", "other_range": f"{max(other - 5, 0)}~{other}%", "explanation": "제동등 미점등은 뒤차의 정지 인지를 어렵게 만든 가산 요소입니다."})
    elif brake_light == "unknown":
        unknown.append(_unknown("brake_light_failure", "브레이크등 작동 여부", "브레이크등 고장 확인 시 내 과실이 0~10%p 증가할 수 있습니다.", "0~10%p"))
        conditional.append({"label": "브레이크등 고장으로 확인되는 경우", "my_range": f"{my}~{min(my + 10, 100)}%", "other_range": f"{max(other - 10, 0)}~{other}%", "explanation": "브레이크등 고장이 입증되면 앞차 과실이 일부 인정될 수 있습니다."})

    if _abnormal_stop(facts, description_text):
        my, other = _apply_delta(my, 10)
        applied.append(_applied("abnormal_stop_position", "비정상 정차 또는 불법 주정차", 10, "정상 차로가 아닌 곳에 정차한 사정을 반영했습니다."))
    if facts.get("stopped_vehicle_without_lights") is True or _text_has(description_text, ("야간 무등화", "스텔스", "등화 없이")):
        my, other = _apply_delta(my, 10)
        applied.append(_applied("night_unlit_or_visibility", "야간 무등화 또는 시야장애", 10, "야간 등화 부재나 시야장애는 발견 가능성에 영향을 줍니다."))
        conditional.append({"label": "야간 무등화/스텔스인 경우", "my_range": f"{my}~{min(my + 10, 100)}%", "other_range": f"{max(other - 10, 0)}~{other}%", "explanation": "식별이 어려운 정차 상태가 입증되면 정차 차량 책임이 더 커질 수 있습니다."})

    return AdjustmentEvaluation(
        base_fault=base,
        final_fault=pair(my, other),
        fault_range=_range_from_unknowns(pair(my, other), unknown),
        applied_adjustments=applied,
        not_applied_adjustments=not_applied,
        unknown_adjustments=unknown,
        conditional_outcomes=conditional,
        required_questions=_required_questions(unknown),
        source_chart=source_chart or None,
        confidence=0.78 if applied else 0.68,
        policy={"id": "car_vs_car_rear_end_adjustments", "unknown_answers_do_not_change_number": True},
    )


def _base_fault(scenario_type: str, facts: dict[str, Any], estimate: dict[str, Any] | None, text: str) -> dict[str, int]:
    base_fault = (estimate or {}).get("final_fault") or (estimate or {}).get("base_fault") or {}
    if isinstance(base_fault.get("A"), int) and isinstance(base_fault.get("B"), int):
        return map_fault_ratio_to_user(scenario_type=scenario_type, fault=base_fault, text=text, facts=facts)
    role = infer_user_vehicle_role(text, facts, scenario_type)
    if role == FRONT_VEHICLE:
        return pair(0, 100)
    if role == FOLLOWING_VEHICLE:
        return pair(100, 0)
    return pair(10 if facts.get("stopped") else 20)


def _apply_delta(my: int, delta_my: int) -> tuple[int, int]:
    next_my = max(0, min(100, int(my) + delta_my))
    return next_my, 100 - next_my


def _applied(factor_id: str, label: str, delta_my: int, reason: str) -> dict[str, Any]:
    return {"factor_id": factor_id, "label": label, "delta_my": delta_my, "delta_other": -delta_my, "reason": reason, "source": "KNIA 수정요소"}


def _not_applied(factor_id: str, label: str, reason: str) -> dict[str, Any]:
    return {"factor_id": factor_id, "label": label, "reason": reason, "source": "KNIA 수정요소"}


def _unknown(factor_id: str, label: str, reason: str, possible_delta: str) -> dict[str, Any]:
    return {"factor_id": factor_id, "label": label, "reason": reason, "possible_delta_my": possible_delta, "source": "KNIA 수정요소"}


def _range_from_unknowns(final_fault: dict[str, int], unknown: list[dict[str, Any]]) -> dict[str, str]:
    extra = 10 if unknown else 0
    return {"my": f"{final_fault['my']}~{min(final_fault['my'] + extra, 100)}%", "other": f"{max(final_fault['other'] - extra, 0)}~{final_fault['other']}%"}


def _required_questions(unknown: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mapping = {
        "brake_light_failure": {"fact_key": "brake_light", "question": "브레이크등이 정상적으로 작동했나요?"},
        "sudden_brake_without_reason": {"fact_key": "sudden_brake_reason", "question": "급정거 사유가 확인되나요?"},
    }
    return [mapping[item["factor_id"]] for item in unknown if item.get("factor_id") in mapping]


def _truthy(value: Any) -> bool:
    if value is True:
        return True
    return str(value or "").strip().lower() in {"true", "yes", "1", "예", "있음", "failed", "no_reason"}


def _text_has(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in (text or "") for token in tokens)


def _stop_reason(facts: dict[str, Any], text: str) -> str:
    raw = str(facts.get("stop_reason") or facts.get("sudden_brake_reason") or facts.get("lawful_stop_reason") or "").strip().lower()
    if raw in {"traffic_signal", "red_light", "signal", "stopped_at_red_light"}:
        return "red_light"
    if raw in {"traffic", "congestion", "front_vehicle", "normal_stop"}:
        return "traffic"
    if raw in {"pedestrian_or_obstacle", "pedestrian", "obstacle"}:
        return "pedestrian_or_obstacle"
    if raw in {"no_reason", "without_reason", "unnecessary"}:
        return "no_reason"
    if _text_has(text, ("신호대기", "빨간불에 정차", "적색신호 대기", "정지선에서 대기")):
        return "red_light"
    if _text_has(text, ("정체", "앞차", "차가 막")):
        return "traffic"
    if _text_has(text, ("보행자", "장애물", "낙하물")):
        return "pedestrian_or_obstacle"
    if _text_has(text, ("이유 없이", "별 이유 없이")):
        return "no_reason"
    return "unknown"


def _brake_light_state(facts: dict[str, Any], text: str) -> str:
    value = facts.get("brake_light") or facts.get("brake_light_status") or facts.get("brake_light_failure") or facts.get("front_brake_light")
    raw = str(value or "").strip().lower()
    if value is False or raw in {"normal", "working", "ok", "정상", "no"}:
        return "normal"
    if value is True or raw in {"failed", "failure", "broken", "not_working", "미점등", "고장", "yes"}:
        return "failed"
    if _text_has(text, ("브레이크등 고장", "제동등 고장", "브레이크등 안", "제동등 안")):
        return "failed"
    return "unknown"


def _abnormal_stop(facts: dict[str, Any], text: str) -> bool:
    return _truthy(facts.get("abnormal_stop")) or _truthy(facts.get("illegal_parking")) or _truthy(facts.get("abnormal_stop_position")) or _text_has(text, ("비정상 정차", "불법 주정차", "도로 한가운데 정차", "정차 금지"))
