from __future__ import annotations

from typing import Any


STATUS_SUPPORTED = "evidence_supported"
STATUS_NEEDS_REVIEW = "needs_review"
STATUS_UNSUPPORTED = "unsupported"

SECTION_STAGE_MAP = {
    "traffic_law_analysis": "legal_analysis",
    "fault_ratio_analysis": "fault_ratio",
    "criminal_liability_analysis": "legal_liability",
    "insurance_guidance": "insurance_guide",
}

REFERENCE_ONLY_NOTICE = "근거가 부족하거나 추가 확인이 필요한 판단은 확정 결론이 아니라 참고용 검토 결과입니다."
SECTION_REVIEW_NOTICE = "이 항목은 직접 근거가 충분하지 않아 추가 확인이 필요한 참고 판단입니다."
SECTION_UNSUPPORTED_NOTICE = "이 항목은 현재 근거만으로 확정 판단처럼 제시할 수 없습니다."


def build_judgment_contract(
    *,
    scenario: dict[str, Any],
    evidence: list[dict[str, Any]],
    legal_analysis: dict[str, Any],
    fault_ratio: dict[str, Any],
    legal_liability: dict[str, Any],
    insurance_guide: dict[str, Any],
    action_plan: list[str],
    evidence_audit: dict[str, Any],
    claim_evidence: dict[str, Any],
    missing_fields: list[str],
) -> dict[str, Any]:
    stages = [
        _stage(
            name="scenario_classification",
            status=STATUS_SUPPORTED if scenario.get("confidence", 0) >= 0.7 else STATUS_NEEDS_REVIEW,
            evidence_family="input",
            summary=f"{scenario.get('scenario_type', 'general_collision')} / {scenario.get('accident_party_type', 'unknown')}",
        ),
        _stage(
            name="evidence_retrieval",
            status=_retrieval_status(evidence, evidence_audit),
            evidence_family="any",
            summary=_retrieval_summary(evidence, evidence_audit),
        ),
        _analyst_stage("traffic_law_analysis", legal_analysis),
        _analyst_stage("fault_ratio_analysis", fault_ratio),
        _analyst_stage("criminal_liability_analysis", legal_liability),
        _analyst_stage("insurance_guidance", insurance_guide),
        _stage(
            name="action_plan",
            status=STATUS_SUPPORTED if action_plan else STATUS_NEEDS_REVIEW,
            evidence_family="any",
            summary=f"{len(action_plan)} actions",
        ),
        _stage(
            name="claim_evidence_gate",
            status=_coverage_status(claim_evidence),
            evidence_family="claim_evidence",
            summary=f"coverage={claim_evidence.get('coverage_level', 'unknown')}",
        ),
    ]
    blocking_reasons = _blocking_reasons(stages, claim_evidence, missing_fields)
    overall_status = _overall_status(stages, blocking_reasons)
    return {
        "version": "agent-judgment-contract-v1",
        "overall_status": overall_status,
        "user_reference_allowed": overall_status != STATUS_UNSUPPORTED,
        "must_not_present_as_final": overall_status != STATUS_SUPPORTED,
        "blocking_reasons": blocking_reasons,
        "stage_statuses": stages,
        "missing_fields": list(missing_fields or []),
        "claim_coverage": {
            "level": claim_evidence.get("coverage_level"),
            "ratio": claim_evidence.get("coverage_ratio"),
            "unsupported_claim_count": claim_evidence.get("unsupported_claim_count", 0),
            "weak_claim_count": claim_evidence.get("weak_claim_count", 0),
        },
    }


def apply_judgment_contract_to_output(output: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    updated = dict(output)
    updated["agent_judgment"] = contract
    updated.setdefault("model_info", {})["agent_judgment_contract_version"] = contract.get("version")
    updated["model_info"]["agent_judgment_overall_status"] = contract.get("overall_status")
    if contract.get("must_not_present_as_final"):
        disclaimers = list(updated.get("disclaimers") or [])
        if REFERENCE_ONLY_NOTICE not in disclaimers:
            disclaimers.insert(0, REFERENCE_ONLY_NOTICE)
        updated["disclaimers"] = disclaimers
        uncertainty = dict(updated.get("uncertainty") or {})
        if uncertainty.get("level") == "low":
            uncertainty["level"] = "medium"
        uncertainty["reason"] = "Agent 판단 계약과 근거 검증 결과에 따라 추가 확인이 필요한 항목이 있습니다."
        updated["uncertainty"] = uncertainty
    return _apply_presentation_policy(updated, contract)


def _stage(*, name: str, status: str, evidence_family: str, summary: str) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "required_evidence_family": evidence_family,
        "summary": summary,
    }


def _analyst_stage(name: str, output: dict[str, Any]) -> dict[str, Any]:
    return _stage(
        name=name,
        status=output.get("judgment_status") or _status_from_support(output.get("evidence_support_level")),
        evidence_family=output.get("required_evidence_family") or "any",
        summary=f"support={output.get('evidence_support_level', 'unknown')}",
    )


def _retrieval_status(evidence: list[dict[str, Any]], evidence_audit: dict[str, Any]) -> str:
    quality = evidence_audit.get("evidence_quality")
    coverage = evidence_audit.get("scenario_evidence_coverage") or {}
    coverage_level = coverage.get("coverage_level")
    if not evidence:
        return STATUS_UNSUPPORTED
    if quality == "high" and coverage_level == "high" and coverage.get("decision_ready") is True:
        return STATUS_SUPPORTED
    if quality in {"high", "medium"} or coverage_level in {"high", "medium"}:
        return STATUS_NEEDS_REVIEW
    return STATUS_NEEDS_REVIEW


def _retrieval_summary(evidence: list[dict[str, Any]], evidence_audit: dict[str, Any]) -> str:
    coverage = evidence_audit.get("scenario_evidence_coverage") or {}
    missing = coverage.get("missing_requirements") or []
    return (
        f"{len(evidence)} evidence items, "
        f"quality={evidence_audit.get('evidence_quality', 'unknown')}, "
        f"coverage={coverage.get('coverage_level', 'unknown')}, "
        f"missing_requirements={len(missing)}"
    )


def _coverage_status(claim_evidence: dict[str, Any]) -> str:
    level = claim_evidence.get("coverage_level")
    unsupported = int(claim_evidence.get("unsupported_claim_count") or 0)
    weak = int(claim_evidence.get("weak_claim_count") or 0)
    if level == "high" and unsupported == 0:
        return STATUS_SUPPORTED
    if level == "low" or unsupported > 0:
        return STATUS_UNSUPPORTED
    if weak > 0:
        return STATUS_NEEDS_REVIEW
    return STATUS_NEEDS_REVIEW


def _status_from_support(support: Any) -> str:
    if support == "direct":
        return STATUS_SUPPORTED
    if support == "partial":
        return STATUS_NEEDS_REVIEW
    return STATUS_UNSUPPORTED


def _blocking_reasons(stages: list[dict[str, Any]], claim_evidence: dict[str, Any], missing_fields: list[str]) -> list[str]:
    reasons: list[str] = []
    if any(stage["status"] == STATUS_UNSUPPORTED for stage in stages):
        reasons.append("unsupported_stage_present")
    if int(claim_evidence.get("unsupported_claim_count") or 0) > 0:
        reasons.append("unsupported_claims_present")
    if int(claim_evidence.get("weak_claim_count") or 0) > 0:
        reasons.append("weak_claims_present")
    if missing_fields:
        reasons.append("required_input_fields_missing")
    return list(dict.fromkeys(reasons))


def _overall_status(stages: list[dict[str, Any]], blocking_reasons: list[str]) -> str:
    if "unsupported_stage_present" in blocking_reasons or "unsupported_claims_present" in blocking_reasons:
        return STATUS_UNSUPPORTED
    if blocking_reasons or any(stage["status"] == STATUS_NEEDS_REVIEW for stage in stages):
        return STATUS_NEEDS_REVIEW
    return STATUS_SUPPORTED


def _apply_presentation_policy(output: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    updated = dict(output)
    stages = {stage.get("name"): stage for stage in contract.get("stage_statuses") or []}
    restricted_sections: list[str] = []
    for stage_name, section_key in SECTION_STAGE_MAP.items():
        stage = stages.get(stage_name) or {}
        status = stage.get("status")
        if status == STATUS_SUPPORTED:
            continue
        section = updated.get(section_key)
        if not isinstance(section, dict):
            continue
        restricted_sections.append(section_key)
        updated[section_key] = _soften_section_for_presentation(section, status)

    finality = "supported"
    if contract.get("overall_status") == STATUS_UNSUPPORTED:
        finality = "blocked_for_final"
    elif contract.get("must_not_present_as_final"):
        finality = "reference_only"

    updated["presentation_policy"] = {
        "finality": finality,
        "user_message": REFERENCE_ONLY_NOTICE if finality != "supported" else "근거와 연결된 참고 판단입니다.",
        "restricted_sections": restricted_sections,
        "blocking_reasons": list(contract.get("blocking_reasons") or []),
    }
    return updated


def _soften_section_for_presentation(section: dict[str, Any], status: Any) -> dict[str, Any]:
    softened = dict(section)
    is_unsupported = status == STATUS_UNSUPPORTED
    notice = SECTION_UNSUPPORTED_NOTICE if is_unsupported else SECTION_REVIEW_NOTICE
    softened["presentation_status"] = "blocked_for_final" if is_unsupported else "review_required"
    softened["finality_notice"] = notice
    softened.setdefault("judgment_status", status or STATUS_NEEDS_REVIEW)
    _append_unique(softened, "caveats", notice)
    if "confidence" in softened:
        softened["confidence"] = _cap_confidence(softened.get("confidence"), 0.35 if is_unsupported else 0.65)
    return softened


def _append_unique(target: dict[str, Any], key: str, value: str) -> None:
    raw = target.get(key) or []
    items = [raw] if isinstance(raw, (str, bytes)) else list(raw)
    if value not in items:
        items.append(value)
    target[key] = items


def _cap_confidence(value: Any, maximum: float) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        confidence = maximum
    return round(max(0.0, min(maximum, confidence)), 2)
