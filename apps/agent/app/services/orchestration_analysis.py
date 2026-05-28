from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.accident_perspective import map_fault_ratio_to_user
from app.services.knia.adjustments.registry import evaluate_adjustments
from app.services.knia.party_guard import canonicalize_party_type
from app.services.knia.knia_matcher import is_knia_match_compatible_with_scenario
from app.services.analysts.action_plan_analyst import analyze_action_plan
from app.services.analysts.criminal_liability_analyst import analyze_criminal_liability
from app.services.analysts.evidence_auditor import audit_evidence
from app.services.analysts.fault_ratio_analyst import analyze_fault_ratio
from app.services.analysts.insurance_analyst import analyze_insurance
from app.services.analysts.traffic_law_analyst import analyze_traffic_law
from app.services.claim_evidence_validator import apply_claim_evidence_audit, validate_claim_evidence
from app.services.orchestration_context import CaseContext
from app.services.orchestration_evidence import EvidenceBundle, _filter_primary_knia_evidence, merge_evidence_items, normalize_evidence_items
from app.services.rag_client import retrieve_for_scenario
from app.services.reflection_loop import build_requery_plan


@dataclass
class AnalysisBundle:
    text: str
    legal_analysis: dict[str, Any]
    fault_ratio: dict[str, Any]
    legal_liability: dict[str, Any]
    insurance_guide: dict[str, Any]
    action_plan: dict[str, Any]
    evidence_audit: dict[str, Any]
    claim_evidence: dict[str, Any]


@dataclass
class ReflectionStageResult:
    evidence_bundle: EvidenceBundle
    analysis_bundle: AnalysisBundle
    requery_plan: dict[str, Any]
    requery_added_count: int


def run_analysis_stage(context: CaseContext, evidence_bundle: EvidenceBundle) -> AnalysisBundle:
    normalized = context.normalized
    scenario = context.scenario
    evidence = evidence_bundle.evidence
    text = normalized["merged_text"]
    legal_analysis = analyze_traffic_law(
        scenario_type=scenario["scenario_type"],
        facts=normalized["structured_facts"],
        evidence=evidence,
        text=text,
    )
    fault_ratio = analyze_fault_ratio(
        scenario_type=scenario["scenario_type"],
        facts=normalized["structured_facts"],
        evidence=evidence,
        text=text,
    )
    _apply_knia_fault_estimate(
        fault_ratio=fault_ratio,
        knia_fault_estimate=evidence_bundle.knia_fault_estimate,
        scenario=scenario,
        normalized=normalized,
    )
    _apply_adjustment_registry(
        fault_ratio=fault_ratio,
        knia_fault_estimate=evidence_bundle.knia_fault_estimate,
        scenario=scenario,
        normalized=normalized,
        knia_result=evidence_bundle.knia_result,
    )
    legal_liability = analyze_criminal_liability(
        scenario_type=scenario["scenario_type"],
        facts=normalized["structured_facts"],
        evidence=evidence,
        legal_analysis=legal_analysis,
        text=text,
    )
    insurance_guide = analyze_insurance(
        scenario_type=scenario["scenario_type"],
        facts=normalized["structured_facts"],
        evidence=evidence,
        text=text,
    )
    action_plan = analyze_action_plan(
        scenario_type=scenario["scenario_type"],
        facts=normalized["structured_facts"],
        legal_liability=legal_liability,
        insurance_guide=insurance_guide,
        evidence=evidence,
        text=text,
    )
    evidence_audit = audit_evidence(
        scenario_type=scenario["scenario_type"],
        evidence=evidence,
        legal_analysis=legal_analysis,
        fault_ratio=fault_ratio,
        missing_fields=context.decision_blocking_missing_fields,
        input_requirements=context.input_requirements,
    )
    claim_evidence = validate_claim_evidence(
        legal_analysis=legal_analysis,
        fault_ratio=fault_ratio,
        legal_liability=legal_liability,
        insurance_guide=insurance_guide,
        action_plan=action_plan,
        evidence=evidence,
    )
    evidence_audit = apply_claim_evidence_audit(evidence_audit, claim_evidence)
    return AnalysisBundle(
        text=text,
        legal_analysis=legal_analysis,
        fault_ratio=fault_ratio,
        legal_liability=legal_liability,
        insurance_guide=insurance_guide,
        action_plan=action_plan,
        evidence_audit=evidence_audit,
        claim_evidence=claim_evidence,
    )


def run_reflection_requery_stage(
    context: CaseContext,
    evidence_bundle: EvidenceBundle,
    analysis_bundle: AnalysisBundle,
) -> ReflectionStageResult:
    requery_plan = build_requery_plan(
        evidence_audit=analysis_bundle.evidence_audit,
        input_requirements=context.input_requirements,
        scenario_type=context.scenario.get("scenario_type"),
        description_text=context.normalized.get("description_text"),
    )
    if not requery_plan.get("should_requery"):
        return ReflectionStageResult(
            evidence_bundle=evidence_bundle,
            analysis_bundle=analysis_bundle,
            requery_plan=requery_plan,
            requery_added_count=0,
        )

    normalized = context.normalized
    scenario = context.scenario
    retry_selected_keywords = list(dict.fromkeys([*normalized["selected_keywords"], *requery_plan.get("query_terms", [])]))
    retry_retrieval = retrieve_for_scenario(
        scenario_type=scenario["scenario_type"],
        scenario_tags=scenario["scenario_tags"],
        description_text=normalized["description_text"],
        facts={**normalized["structured_facts"], "accident_party_type": scenario.get("accident_party_type")},
        selected_keywords=retry_selected_keywords,
        video_context=context.video_context,
        limit=10,
    )
    before_count = len(evidence_bundle.legal_evidence)
    legal_evidence = merge_evidence_items(
        [
            *evidence_bundle.legal_evidence,
            *normalize_evidence_items(retry_retrieval["items"], default_source="법률 근거"),
        ]
    )
    legal_evidence = _filter_primary_knia_evidence(legal_evidence, scenario.get("scenario_tags") or [], scenario.get("scenario_type"))
    next_evidence_bundle = EvidenceBundle(
        **{
            **evidence_bundle.__dict__,
            "legal_evidence": legal_evidence,
            "evidence": merge_evidence_items([*evidence_bundle.knia_evidence, *legal_evidence]),
        }
    )
    return ReflectionStageResult(
        evidence_bundle=next_evidence_bundle,
        analysis_bundle=run_analysis_stage(context, next_evidence_bundle),
        requery_plan=requery_plan,
        requery_added_count=max(0, len(legal_evidence) - before_count),
    )


def _apply_knia_fault_estimate(
    *,
    fault_ratio: dict[str, Any],
    knia_fault_estimate: dict[str, Any] | None,
    scenario: dict[str, Any],
    normalized: dict[str, Any],
) -> None:
    if not knia_fault_estimate:
        return
    final_fault = knia_fault_estimate.get("final_fault") or {}
    fault_ratio["knia_reference_fault"] = final_fault
    source_chart = knia_fault_estimate.get("source_chart") or {}
    if source_chart and not is_knia_match_compatible_with_scenario(source_chart, scenario.get("scenario_type")):
        fault_ratio["rejected_knia_fault_estimate"] = {
            "source_chart": source_chart,
            "final_fault": final_fault,
            "reason": "knia_basis_mismatch",
        }
        fault_ratio["knia_override_policy"] = "rejected_incompatible_knia_basis"
        factors = list(fault_ratio.get("key_factors") or [])
        if "KNIA 기준 불일치" not in factors:
            fault_ratio["key_factors"] = [*factors, "KNIA 기준 불일치"]
        fault_ratio["basis"] = (
            f"{fault_ratio.get('basis') or '사고 사실 기반 참고용 과실 추정입니다.'} "
            "검색된 KNIA 기준이 현재 사고 유형과 맞지 않아 과실비율 덮어쓰기에 사용하지 않았습니다."
        ).strip()
        return
    if fault_ratio.get("fault_estimate_source") == "contextual_complex_case":
        fault_ratio["basis"] = (
            "복합 사고 맥락과 KNIA 과실비율 인정기준을 함께 검토한 참고용 과실 추정입니다. "
            "KNIA 기본값은 참고 기준으로 보존하되, 정차 사유·시인성·회피 가능성·후속 추돌 여부가 우선 반영되었습니다."
        )
        fault_ratio["knia_override_policy"] = "preserved_contextual_complex_case_estimate"
        return
    fault_ratio["basis"] = "KNIA 원문 기본과실과 수집된 가감요소를 함께 반영한 참고 산정입니다."
    if isinstance(final_fault.get("A"), int) and isinstance(final_fault.get("B"), int):
        mapped_fault = map_fault_ratio_to_user(
            scenario_type=scenario.get("scenario_type"),
            fault=final_fault,
            text=normalized["description_text"],
            facts=normalized["structured_facts"],
        )
        fault_ratio["my"] = mapped_fault["my"]
        fault_ratio["other"] = mapped_fault["other"]
        fault_ratio["user_vehicle_role"] = mapped_fault.get("user_vehicle_role")
        fault_ratio["user_vehicle_role_label"] = mapped_fault.get("user_vehicle_role_label")


def _apply_adjustment_registry(
    *,
    fault_ratio: dict[str, Any],
    knia_fault_estimate: dict[str, Any] | None,
    scenario: dict[str, Any],
    normalized: dict[str, Any],
    knia_result: dict[str, Any],
) -> None:
    facts = normalized["structured_facts"]
    party = canonicalize_party_type(facts.get("knia_major_party_type") or scenario.get("accident_party_type"))
    source_chart = (knia_fault_estimate or {}).get("source_chart") or {}
    if source_chart and not is_knia_match_compatible_with_scenario(source_chart, scenario.get("scenario_type")):
        fault_ratio.setdefault("rejected_knia_fault_estimate", {"source_chart": source_chart, "reason": "knia_basis_mismatch"})
        return
    evaluation = evaluate_adjustments(
        scenario.get("scenario_type") or "general_collision",
        party,
        facts,
        knia_fault_estimate,
        normalized["description_text"],
    )
    if evaluation.get("base_fault"):
        fault_ratio["base_fault"] = evaluation["base_fault"]
    if evaluation.get("final_fault"):
        fault_ratio["final_fault"] = evaluation["final_fault"]
        fault_ratio["my"] = evaluation["final_fault"].get("my", fault_ratio.get("my"))
        fault_ratio["other"] = evaluation["final_fault"].get("other", fault_ratio.get("other"))
    if evaluation.get("fault_range"):
        fault_ratio["fault_range"] = evaluation["fault_range"]
    for key in ("applied_adjustments", "not_applied_adjustments", "unknown_adjustments", "conditional_outcomes"):
        if evaluation.get(key):
            existing = fault_ratio.get(key)
            if isinstance(existing, list) and key == "conditional_outcomes":
                fault_ratio[key] = [*existing, *evaluation[key]]
            else:
                fault_ratio[key] = evaluation[key]
    fault_ratio["knia_adjustment_policy"] = evaluation.get("policy") or {}
    fault_ratio["knia_adjustment_registry"] = evaluation
    fault_ratio["knia_reference_fault"] = (knia_fault_estimate or {}).get("final_fault") or fault_ratio.get("knia_reference_fault")
    if not knia_fault_estimate:
        fault_ratio["no_knia_match_reason"] = knia_result.get("no_knia_match_reason") or "knia_fault_estimate_unavailable"
