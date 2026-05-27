from __future__ import annotations

from typing import Any

from app.services.accident_perspective import map_fault_ratio_to_user
from app.services.knia.knia_matcher import is_knia_match_compatible_with_scenario


VERSION = "agent-knia-adjustment-agent-v1"


def apply_knia_adjustment_agent(
    *,
    fault_ratio: dict[str, Any],
    knia_fault_estimate: dict[str, Any] | None,
    scenario_type: str,
    description_text: str,
    structured_facts: dict[str, Any] | None,
) -> dict[str, Any]:
    facts = structured_facts or {}
    source_chart = (knia_fault_estimate or {}).get("source_chart") or {}
    if source_chart and not is_knia_match_compatible_with_scenario(source_chart, scenario_type):
        result = _empty_result("rejected_incompatible_knia_basis")
        result["caveats"].append("현재 사고유형과 맞지 않는 KNIA 기준이라 가감요소 계산에 사용하지 않았습니다.")
        fault_ratio["knia_adjustment_agent"] = result
        return result

    if scenario_type != "rear_end_collision":
        result = _empty_result("not_applicable_for_scenario")
        fault_ratio["knia_adjustment_agent"] = result
        return result

    base_user_fault = _base_user_fault(fault_ratio, knia_fault_estimate, scenario_type, description_text, facts)
    my = int(base_user_fault["my"])
    other = int(base_user_fault["other"])
    applied: list[dict[str, Any]] = []
    not_applied: list[dict[str, Any]] = []
    caveats: list[str] = []

    sudden = _truthy(facts.get("sudden_brake")) or _text_has(description_text, ("급정거", "급제동", "갑자기 멈"))
    stop_reason = _stop_reason(facts, description_text)
    if sudden and stop_reason in {"red_light", "traffic", "pedestrian_or_obstacle", "lawful"}:
        not_applied.append({
            "factor_id": "sudden_brake_without_reason",
            "label": "이유 없는 급정거",
            "answer": stop_reason,
            "reason": "빨간불 신호대기, 정체, 보행자·장애물 회피처럼 정당한 정차 사유가 있어 적용하지 않았습니다.",
        })
    elif sudden and stop_reason == "no_reason":
        my, other = _apply_delta(my, other, 10)
        applied.append(_applied("sudden_brake_without_reason", "이유 없는 급정거", "yes", 10, "정상적인 이유 없이 급정거한 경우 앞차 과실이 일부 인정될 수 있습니다."))
    elif sudden:
        caveats.append("급정거 사유가 확인되지 않았습니다. 이유 없는 급정거로 확인되면 내 과실이 일부 올라갈 수 있습니다.")
        not_applied.append({
            "factor_id": "sudden_brake_without_reason",
            "label": "급정거 사유 불명확",
            "answer": "unknown",
            "reason": "잘 모르겠어요 또는 확인 불가로 보아 숫자 조정은 적용하지 않았습니다.",
        })

    brake_light = _brake_light_state(facts, description_text)
    if brake_light == "failed":
        my, other = _apply_delta(my, other, 10)
        applied.append(_applied("brake_light_failure", "제동등 고장 또는 미점등", "yes", 10, "브레이크등이 고장 나 있었다면 뒤차가 정지를 알아보기 어려워 앞차 과실이 일부 인정될 수 있습니다."))
    elif brake_light == "unknown":
        caveats.append("브레이크등 정상 작동 여부가 확인되지 않았습니다.")
        not_applied.append({
            "factor_id": "brake_light_failure",
            "label": "제동등 고장",
            "answer": "unknown",
            "reason": "확인되지 않아 적용하지 않았습니다.",
        })

    if _abnormal_stop(facts, description_text):
        my, other = _apply_delta(my, other, 10)
        applied.append(_applied("abnormal_stop_position", "비정상 정차 또는 불법 주정차", "yes", 10, "정상 차로가 아닌 곳에 비정상 정차했다면 앞차 과실이 일부 올라갈 수 있습니다."))

    if _truthy(facts.get("stopped_after_prior_accident")) or _text_has(description_text, ("선행사고", "먼저 사고", "사고 후 도로상 정차")):
        my, other = _apply_delta(my, other, 10)
        applied.append(_applied("stopped_after_prior_accident", "선행사고 후 도로상 정차", "yes", 10, "선행사고 후 도로 위에 멈춰 있던 상황이면 시인성과 회피 가능성을 따로 봅니다."))

    if _truthy(facts.get("stopped_vehicle_without_lights")) or _text_has(description_text, ("야간 무등화", "불 꺼", "등화 없이")):
        my, other = _apply_delta(my, other, 10)
        applied.append(_applied("night_unlit_or_visibility", "야간 무등화 또는 시야장애", "yes", 10, "야간에 등화 없이 정차했거나 시야장애가 있으면 앞차 과실이 일부 올라갈 수 있습니다."))

    if not applied and not caveats:
        caveats.append("기본적으로 뒤차 책임이 높지만, 급정거·제동등·비정상 정차 여부는 확인하면 더 정확해집니다.")

    result = {
        "version": VERSION,
        "status": "applied" if applied else "reference_only",
        "base_fault": base_user_fault,
        "applied_adjustments": applied,
        "not_applied_adjustments": not_applied,
        "final_fault": {"my": my, "other": other},
        "confidence": 0.78 if applied else 0.68,
        "caveats": caveats,
        "source": "deterministic_knia_adjustment_agent",
    }
    fault_ratio["my"] = my
    fault_ratio["other"] = other
    fault_ratio["knia_adjustment_agent"] = result
    fault_ratio["deterministic_adjustment_source"] = VERSION
    if applied:
        factors = list(fault_ratio.get("key_factors") or [])
        fault_ratio["key_factors"] = [*factors, *[item["label"] for item in applied]]
        fault_ratio["basis"] = "KNIA 기본과실과 확인된 가감요소를 deterministic하게 반영한 참고 산정입니다."
    return result


def _empty_result(status: str) -> dict[str, Any]:
    return {
        "version": VERSION,
        "status": status,
        "base_fault": None,
        "applied_adjustments": [],
        "not_applied_adjustments": [],
        "final_fault": None,
        "confidence": 0.0,
        "caveats": [],
    }


def _base_user_fault(
    fault_ratio: dict[str, Any],
    estimate: dict[str, Any] | None,
    scenario_type: str,
    description_text: str,
    facts: dict[str, Any],
) -> dict[str, int]:
    my = fault_ratio.get("my")
    other = fault_ratio.get("other")
    if isinstance(my, int) and isinstance(other, int):
        return {"my": _clamp(my), "other": _clamp(other)}
    base_fault = (estimate or {}).get("final_fault") or (estimate or {}).get("base_fault") or {}
    if isinstance(base_fault.get("A"), int) and isinstance(base_fault.get("B"), int):
        mapped = map_fault_ratio_to_user(
            scenario_type=scenario_type,
            fault=base_fault,
            text=description_text,
            facts=facts,
        )
        return {"my": _clamp(mapped.get("my", 10)), "other": _clamp(mapped.get("other", 90))}
    return {"my": 10, "other": 90}


def _apply_delta(my: int, other: int, delta_my: int) -> tuple[int, int]:
    next_my = _clamp(my + delta_my)
    return next_my, _clamp(100 - next_my)


def _applied(factor_id: str, label: str, answer: str, delta_my: int, reason: str) -> dict[str, Any]:
    return {
        "factor_id": factor_id,
        "label": label,
        "answer": answer,
        "direction": "increase_my_fault",
        "delta_my": delta_my,
        "delta_other": -delta_my,
        "reason": reason,
        "source": "KNIA 수정요소",
    }


def _truthy(value: Any) -> bool:
    if value is True:
        return True
    text = str(value or "").strip().lower()
    return text in {"true", "yes", "y", "1", "예", "있음", "failed", "abnormal_stop", "no_reason"}


def _unknown(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text in {"", "unknown", "모름", "잘 모르겠어요", "확인 중", "none", "null"}


def _text_has(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in (text or "") for token in tokens)


def _stop_reason(facts: dict[str, Any], text: str) -> str:
    value = facts.get("stop_reason") or facts.get("sudden_brake_reason") or facts.get("lawful_stop_reason")
    raw = str(value or "").strip().lower()
    if raw in {"traffic_signal", "red_light", "signal", "stopped_at_red_light"}:
        return "red_light"
    if raw in {"traffic", "congestion", "front_vehicle"}:
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
    if _text_has(text, ("이유 없이", "별 이유 없이", "갑자기 정지")):
        return "no_reason"
    return "unknown"


def _brake_light_state(facts: dict[str, Any], text: str) -> str:
    value = facts.get("brake_light") or facts.get("brake_light_status") or facts.get("brake_light_failure")
    raw = str(value or "").strip().lower()
    if value is False or raw in {"normal", "working", "ok", "정상", "no"}:
        return "normal"
    if value is True or raw in {"failed", "failure", "broken", "not_working", "미점등", "고장", "yes"}:
        return "failed"
    if _text_has(text, ("브레이크등 고장", "제동등 고장", "브레이크등 안", "제동등 안")):
        return "failed"
    if _unknown(value):
        return "unknown"
    return "unknown"


def _abnormal_stop(facts: dict[str, Any], text: str) -> bool:
    return (
        _truthy(facts.get("abnormal_stop"))
        or _truthy(facts.get("illegal_parking"))
        or _truthy(facts.get("abnormal_stop_position"))
        or _text_has(text, ("비정상 정차", "불법 주정차", "도로 한가운데 정차", "정차 금지"))
    )


def _clamp(value: Any) -> int:
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return 0
