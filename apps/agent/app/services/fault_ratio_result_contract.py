from __future__ import annotations

from typing import Any


VERSION = "fault-ratio-result-contract-v1"

SUPPORTED_RANGE = "supported_range"
CONDITIONAL_RANGE = "conditional_range"
FALLBACK_NEEDS_EVIDENCE = "fallback_needs_evidence"

CONTEXTUAL_SOURCES = {
    "contextual_complex_case",
    "stealth_illegal_parked_vehicle_rule",
}


def attach_fault_ratio_result_contract(
    fault_ratio: dict[str, Any],
    *,
    scenario_type: str,
    facts: dict[str, Any],
    evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Attach a user-safe result contract without changing the existing estimate fields."""
    contract = build_fault_ratio_result_contract(
        fault_ratio,
        scenario_type=scenario_type,
        facts=facts,
        evidence=evidence or [],
    )
    fault_ratio["fault_result_contract"] = contract
    fault_ratio["fault_result_contract_version"] = VERSION
    return fault_ratio


def build_fault_ratio_result_contract(
    fault_ratio: dict[str, Any],
    *,
    scenario_type: str,
    facts: dict[str, Any],
    evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    evidence = evidence or []
    display_status = _display_status(fault_ratio)
    source = str(fault_ratio.get("fault_estimate_source") or "")
    conditions = _conditional_outcomes(fault_ratio)
    fallback = display_status == FALLBACK_NEEDS_EVIDENCE
    needs_confirmation = _needs_confirmation_fields(fault_ratio, facts)
    primary_range = _primary_range(fault_ratio, display_status=display_status)
    reference_ratio = _reference_ratio(fault_ratio)

    return {
        "version": VERSION,
        "scenario_type": scenario_type,
        "display_status": display_status,
        "range_basis": _range_basis(fault_ratio, display_status=display_status),
        "primary_range": primary_range,
        "reference_ratio": reference_ratio,
        "is_fallback": fallback,
        "fallback_reason": _fallback_reason(fault_ratio, evidence) if fallback else None,
        "has_conditional_outcomes": bool(conditions),
        "conditional_outcome_count": len(conditions),
        "needs_confirmation_fields": needs_confirmation,
        "adjustment_summary": _adjustment_summary(fault_ratio),
        "presentation_guidance": _presentation_guidance(
            display_status=display_status,
            primary_range=primary_range,
            reference_ratio=reference_ratio,
            needs_confirmation_fields=needs_confirmation,
            source=source,
        ),
    }


def _display_status(fault_ratio: dict[str, Any]) -> str:
    source = str(fault_ratio.get("fault_estimate_source") or "")
    if source == "conditional_fact_gap":
        return CONDITIONAL_RANGE
    if _conditional_outcomes(fault_ratio) and _has_result_splitting_condition(fault_ratio):
        return CONDITIONAL_RANGE
    if source in CONTEXTUAL_SOURCES:
        return SUPPORTED_RANGE
    if _conditional_outcomes(fault_ratio) and _is_flat_default(fault_ratio):
        return CONDITIONAL_RANGE
    if fault_ratio.get("knia_reference_fault") and not fault_ratio.get("knia_reference_only"):
        return SUPPORTED_RANGE
    if fault_ratio.get("evidence_support_level") == "direct":
        return SUPPORTED_RANGE
    if _is_flat_default(fault_ratio):
        return FALLBACK_NEEDS_EVIDENCE
    return SUPPORTED_RANGE if source and source != "scenario_default" else FALLBACK_NEEDS_EVIDENCE


def _is_flat_default(fault_ratio: dict[str, Any]) -> bool:
    return (
        int(fault_ratio.get("my") or 0) == 50
        and int(fault_ratio.get("other") or 0) == 50
        and str(fault_ratio.get("fault_estimate_source") or "") in {"", "scenario_default"}
        and not _conditional_outcomes(fault_ratio)
    )


def _range_basis(fault_ratio: dict[str, Any], *, display_status: str) -> str:
    if display_status == CONDITIONAL_RANGE:
        return "conditional_fact_branches"
    if display_status == FALLBACK_NEEDS_EVIDENCE:
        return "insufficient_direct_basis"
    if fault_ratio.get("knia_reference_fault") and not fault_ratio.get("knia_reference_only"):
        return "knia_or_adjustment"
    source = str(fault_ratio.get("fault_estimate_source") or "")
    if source in CONTEXTUAL_SOURCES:
        return source
    return "agent_supported_estimate"


def _primary_range(fault_ratio: dict[str, Any], *, display_status: str) -> dict[str, Any]:
    fault_range = fault_ratio.get("fault_range") if isinstance(fault_ratio.get("fault_range"), dict) else {}
    my_range = str(fault_range.get("my") or "").strip()
    other_range = str(fault_range.get("other") or "").strip()
    if display_status == CONDITIONAL_RANGE:
        return {"my": None, "other": None, "label": "조건별 범위 확인 필요"}
    if my_range and other_range:
        return {"my": my_range, "other": other_range, "label": f"내 책임 {my_range} / 상대 {other_range} 참고"}
    ratio = _reference_ratio(fault_ratio)
    if ratio["my"] is None or ratio["other"] is None:
        return {"my": None, "other": None, "label": "범위 산정 불가"}
    return {
        "my": f"{ratio['my']}%",
        "other": f"{ratio['other']}%",
        "label": f"내 책임 {ratio['my']}% / 상대 {ratio['other']}% 참고",
    }


def _reference_ratio(fault_ratio: dict[str, Any]) -> dict[str, int | None]:
    my = _bounded_int(fault_ratio.get("my"))
    other = _bounded_int(fault_ratio.get("other"))
    return {"my": my, "other": other}


def _bounded_int(value: Any) -> int | None:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    return max(0, min(100, number))


def _conditional_outcomes(fault_ratio: dict[str, Any]) -> list[dict[str, Any]]:
    items = fault_ratio.get("conditional_outcomes")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _has_result_splitting_condition(fault_ratio: dict[str, Any]) -> bool:
    required = {str(item).strip() for item in fault_ratio.get("conditional_required_facts") or []}
    if "opponent_signal" in required:
        return True
    judgment = fault_ratio.get("conditional_judgment") if isinstance(fault_ratio.get("conditional_judgment"), dict) else {}
    trigger_types = {str(item.get("type") or "") for item in judgment.get("triggers") or [] if isinstance(item, dict)}
    return bool(trigger_types & {"opponent_signal_uncertainty"})


def _needs_confirmation_fields(fault_ratio: dict[str, Any], facts: dict[str, Any]) -> list[str]:
    fields: list[str] = []
    for key in ("conditional_required_facts", "required_questions", "required_facts", "adjustment_review_factors"):
        raw = fault_ratio.get(key) or []
        if isinstance(raw, (str, bytes)):
            raw = [raw]
        if isinstance(raw, list):
            fields.extend(str(item).strip() for item in raw if str(item).strip())
    for item in fault_ratio.get("unknown_adjustments") or []:
        if isinstance(item, dict):
            fields.extend(str(value).strip() for value in item.get("required_facts") or [] if str(value).strip())
            if item.get("label"):
                fields.append(str(item["label"]).strip())
    if facts.get("opponent_signal_visible") is False:
        fields.append("opponent_signal")
    if facts.get("centerline_crossed") is True and not facts.get("centerline_cross_reason"):
        fields.append("centerline_cross_reason")
    if facts.get("front_vehicle_stopped") is True and not facts.get("front_vehicle_stop_reason"):
        fields.append("front_vehicle_stop_reason")
    return list(dict.fromkeys(fields))


def _adjustment_summary(fault_ratio: dict[str, Any]) -> dict[str, int]:
    return {
        "applied_count": _list_count(fault_ratio.get("applied_adjustments")),
        "not_applied_count": _list_count(fault_ratio.get("not_applied_adjustments")),
        "unknown_count": _list_count(fault_ratio.get("unknown_adjustments")),
        "conditional_count": len(_conditional_outcomes(fault_ratio)),
    }


def _list_count(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _fallback_reason(fault_ratio: dict[str, Any], evidence: list[dict[str, Any]]) -> str:
    if not evidence:
        return "direct_evidence_missing"
    if fault_ratio.get("evidence_support_level") in {"insufficient", None}:
        return "knia_or_direct_basis_insufficient"
    return "scenario_default_without_specific_axis_range"


def _presentation_guidance(
    *,
    display_status: str,
    primary_range: dict[str, Any],
    reference_ratio: dict[str, int | None],
    needs_confirmation_fields: list[str],
    source: str,
) -> str:
    if display_status == CONDITIONAL_RANGE:
        return "단일 숫자보다 조건별 결과와 먼저 확인할 사실을 함께 표시해야 합니다."
    if display_status == FALLBACK_NEEDS_EVIDENCE:
        return "일반 50:50 참고값으로 보이고, 직접 근거 또는 핵심 사실 확인 없이는 확정처럼 표시하지 않아야 합니다."
    label = primary_range.get("label") or (
        f"내 책임 {reference_ratio.get('my')}% / 상대 {reference_ratio.get('other')}% 참고"
        if reference_ratio.get("my") is not None
        else "지원 가능한 참고 범위"
    )
    if needs_confirmation_fields:
        return f"{label}를 표시하되 확인 필요 요소를 함께 안내해야 합니다."
    if source in CONTEXTUAL_SOURCES:
        return f"{label}를 사고축 기반 참고 범위로 표시할 수 있습니다."
    return f"{label}를 근거 연결 참고값으로 표시할 수 있습니다."
