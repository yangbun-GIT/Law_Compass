from __future__ import annotations

from typing import Any

from app.services.agent_quality_packet import (
    VERSION as AGENT_QUALITY_PACKET_VERSION,
    build_agent_quality_packet,
)
from app.services.agent_execution_trace import (
    VERSION as AGENT_TRACE_VERSION,
    build_agent_execution_trace,
)
from app.services.analysis_modes import build_analysis_mode_contract, normalize_analysis_mode
from app.services.dynamic_questionnaire import build_dynamic_questionnaire
from app.services.elderly_friendly.report_simplifier import build_elderly_friendly_report
from app.services.evidence_source_status import (
    VERSION as EVIDENCE_SOURCE_STATUS_VERSION,
    build_evidence_source_status,
)
from app.services.expert_guidance_sections import build_expert_guidance_sections
from app.services.judgment_contract import apply_judgment_contract_to_output
from app.services.orchestration_analysis import AnalysisBundle
from app.services.orchestration_context import CaseContext
from app.services.orchestration_evidence import EvidenceBundle
from app.services.reflection_loop import VERSION as REFLECTION_LOOP_VERSION


def enrich_analysis_output(
    *,
    output: dict[str, Any],
    context: CaseContext,
    evidence_bundle: EvidenceBundle,
    analysis_bundle: AnalysisBundle,
    judgment_contract: dict[str, Any],
    reflection_loop: dict[str, Any],
) -> dict[str, Any]:
    output = apply_judgment_contract_to_output(output, judgment_contract)
    output["reflection_loop"] = reflection_loop
    analysis_mode = normalize_analysis_mode(context.normalized.get("analysis_mode"))
    output["analysis_mode"] = analysis_mode
    output["display_mode"] = analysis_mode
    output["analysis_mode_contract"] = build_analysis_mode_contract(analysis_mode)
    output["guided_questionnaire"] = build_dynamic_questionnaire(
        scenario_type=context.scenario.get("scenario_type"),
        accident_party_type=context.scenario.get("accident_party_type"),
        analysis_mode=context.normalized.get("analysis_mode"),
        description_text=context.normalized.get("description_text") or "",
        structured_facts=context.normalized.get("structured_facts") or {},
        selected_keywords=context.normalized.get("selected_keywords") or [],
        video_observations=context.video_context,
        matched_knia_chart=evidence_bundle.knia_matches[0] if evidence_bundle.knia_matches else None,
        knia_adjustment_factors=(evidence_bundle.knia_fault_estimate or {}).get("selected_adjustments")
        or (evidence_bundle.knia_fault_estimate or {}).get("rejected_adjustments")
        or [],
    )
    output["model_info"]["reflection_loop_version"] = REFLECTION_LOOP_VERSION
    output["claim_evidence"] = analysis_bundle.claim_evidence
    output["expert_guidance_sections"] = build_expert_guidance_sections(
        scenario=context.scenario,
        facts=context.normalized["structured_facts"],
        legal_analysis=analysis_bundle.legal_analysis,
        fault_ratio=analysis_bundle.fault_ratio,
        legal_liability=analysis_bundle.legal_liability,
        insurance_guide=analysis_bundle.insurance_guide,
        evidence=evidence_bundle.evidence,
        evidence_audit=analysis_bundle.evidence_audit,
        claim_evidence=analysis_bundle.claim_evidence,
        input_requirements=context.input_requirements,
        reflection_loop=reflection_loop,
    )
    output["knia_json_evidence"] = evidence_bundle.knia_json_evidence
    output["knia_adjustment_agent"] = analysis_bundle.fault_ratio.get("knia_adjustment_agent") or {}
    _attach_knia_fault_estimate(output, evidence_bundle, analysis_bundle)
    knia_match_summary = _build_knia_match_summary(evidence_bundle, context)
    if knia_match_summary:
        output["knia_match_summary"] = knia_match_summary
        output.setdefault("elderly_friendly_report", {})["knia_match_summary"] = knia_match_summary
    output["related_knia_source_links"] = [
        x.get("source_url") for x in evidence_bundle.knia_json_evidence if x.get("source_url")
    ]
    output["model_info"]["retrieval"] = _build_retrieval_model_info(evidence_bundle)
    if (analysis_bundle.fault_ratio or {}).get("rejected_knia_fault_estimate"):
        observation = {
            "type": "knia_basis_mismatch",
            "reason": "primary KNIA chart was incompatible with scenario_type and was not used to overwrite fault_ratio",
        }
        output.setdefault("evidence_audit", {}).setdefault("observations", []).append(observation)
        output["model_info"].setdefault("evidence_mismatch", []).append(observation)
    output["model_info"]["scenario_classifier"] = context.scenario
    output["model_info"]["evidence_source_status"] = build_evidence_source_status(evidence_bundle)
    output["model_info"]["evidence_source_status_version"] = EVIDENCE_SOURCE_STATUS_VERSION
    output["agent_trace"] = build_agent_execution_trace(output)
    output["model_info"]["agent_trace_version"] = AGENT_TRACE_VERSION
    output["agent_quality_packet"] = build_agent_quality_packet(output)
    output["model_info"]["agent_quality_packet_version"] = AGENT_QUALITY_PACKET_VERSION
    output["elderly_friendly_report"] = build_elderly_friendly_report(output)
    return output


def _attach_knia_fault_estimate(
    output: dict[str, Any],
    evidence_bundle: EvidenceBundle,
    analysis_bundle: AnalysisBundle,
) -> None:
    if not evidence_bundle.knia_fault_estimate:
        return

    estimate = evidence_bundle.knia_fault_estimate
    adjustment_agent = analysis_bundle.fault_ratio.get("knia_adjustment_agent") or {}
    deterministic_applied = adjustment_agent.get("applied_adjustments") or []
    deterministic_not_applied = adjustment_agent.get("not_applied_adjustments") or []
    output["knia_base_fault"] = estimate.get("base_fault")
    output["knia_final_fault"] = estimate.get("final_fault")
    output["knia_applied_adjustments"] = [*(estimate.get("selected_adjustments") or []), *deterministic_applied]
    output["knia_rejected_adjustments"] = [*(estimate.get("rejected_adjustments") or []), *deterministic_not_applied]
    output["knia_calculation_steps"] = estimate.get("calculation_steps") or []
    output["knia_adjustment_evidence"] = estimate.get("evidence_used") or []
    output["knia_reference_evidence"] = evidence_bundle.knia_reference_evidence
    output.setdefault("elderly_friendly_report", {})["knia_fault_adjustment_card"] = {
        "title": "KNIA 원문 근거 및 가감요소 적용",
        "base_fault": estimate.get("base_fault"),
        "final_fault": estimate.get("final_fault"),
        "user_fault": {
            "my": analysis_bundle.fault_ratio.get("my"),
            "other": analysis_bundle.fault_ratio.get("other"),
            "role": analysis_bundle.fault_ratio.get("user_vehicle_role"),
            "role_label": analysis_bundle.fault_ratio.get("user_vehicle_role_label"),
        },
        "applied_adjustments": estimate.get("selected_adjustments") or [],
        "deterministic_adjustments": deterministic_applied,
        "not_applied_adjustments": deterministic_not_applied[:8],
        "rejected_adjustments": (estimate.get("rejected_adjustments") or [])[:5],
        "calculation_steps": estimate.get("calculation_steps") or [],
        "notice": " ".join([str(estimate.get("notice") or ""), " ".join(adjustment_agent.get("caveats") or [])]).strip(),
    }


def _build_knia_match_summary(evidence_bundle: EvidenceBundle, context: CaseContext) -> dict[str, Any]:
    primary = _first_real_knia_match(evidence_bundle.knia_matches)
    if not primary:
        return {}

    party = str(
        primary.get("major_party_type")
        or primary.get("accident_party_type")
        or context.scenario.get("accident_party_type")
        or ""
    )
    menu_path = [str(item) for item in (primary.get("menu_path") or []) if item]
    major_category = _major_category_label(party)
    title = str(primary.get("title") or primary.get("article_title") or "").strip()
    chart_no = str(primary.get("aggregate_chart_no") or primary.get("chart_no") or "").strip()
    subchart_no = str(primary.get("subchart_no") or "").strip() or None
    source_url = str(primary.get("source_detail_url") or primary.get("source_url") or "").strip()

    candidates = []
    for item in evidence_bundle.knia_matches[:5]:
        if not _is_real_knia_chart(item):
            continue
        candidates.append(
            {
                "chart_no": item.get("aggregate_chart_no") or item.get("chart_no"),
                "subchart_no": item.get("subchart_no"),
                "title": item.get("title") or item.get("article_title"),
                "major_party_type": item.get("major_party_type") or item.get("accident_party_type"),
                "score": item.get("match_score") or item.get("score"),
                "confidence": item.get("confidence") or item.get("parsing_confidence"),
                "source_url": item.get("source_detail_url") or item.get("source_url"),
                "source_url_is_fallback": bool(item.get("source_url_is_fallback")),
                "reference_only": bool(item.get("reference_only")),
            }
        )

    missing_facts = _knia_missing_facts(primary, context)
    source_is_fallback = bool(primary.get("source_url_is_fallback"))
    return {
        "major_category": major_category,
        "menu_path": menu_path or [major_category, title],
        "chart_no": chart_no,
        "subchart_no": subchart_no,
        "title": title,
        "source_url": source_url,
        "source_url_is_fallback": source_is_fallback,
        "match_confidence": primary.get("confidence") or primary.get("parsing_confidence") or primary.get("match_score"),
        "reference_only": bool(primary.get("reference_only") or primary.get("review_required")),
        "presentation_status": "reference_only" if primary.get("reference_only") or primary.get("review_required") else "matched",
        "source_quality": primary.get("source_quality") or "structured_json",
        "source_quality_label": primary.get("source_quality_label") or "KNIA 구조화 기준 후보",
        "why_matched": primary.get("match_reason") or "사고 대분류와 핵심 사실이 같은 KNIA 구조화 기준 후보입니다.",
        "missing_facts": missing_facts,
        "candidate_charts": candidates,
        "fallback_used": bool(primary.get("fallback_used")),
    }


def _first_real_knia_match(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in items:
        if _is_real_knia_chart(item):
            return item
    return None


def _is_real_knia_chart(item: dict[str, Any]) -> bool:
    chart_no = str(item.get("aggregate_chart_no") or item.get("chart_no") or "").strip()
    if not chart_no or "참고" in chart_no:
        return False
    return chart_no[0] in {"차", "보", "거", "자", "기", "단"}


def _major_category_label(party: str) -> str:
    return {
        "car_vs_car": "자동차와 자동차의 사고",
        "car_vs_person": "자동차와 보행자의 사고",
        "car_vs_bicycle": "자동차와 자전거의 사고",
        "car_vs_motorcycle": "자동차와 이륜차의 사고",
        "car_vs_object": "자동차와 기물의 사고",
        "single_vehicle": "차량 단독 사고",
    }.get(party, "KNIA 과실비율 인정기준")


def _knia_missing_facts(primary: dict[str, Any], context: CaseContext) -> list[str]:
    facts = context.normalized.get("structured_facts") or {}
    accident_type = str(facts.get("accident_type") or context.scenario.get("accident_type") or "")
    party = str(primary.get("major_party_type") or primary.get("accident_party_type") or "")
    if party == "car_vs_person" and accident_type in {"pedestrian_roadway_worker_accident", "pedestrian_road_work_worker_accident"}:
        return [
            "보행자가 차도 가장자리였는지 중앙부분이었는지 확인 필요",
            "횡단보도 여부 확인 필요",
            "야간/시야장애 여부 확인 필요",
        ]
    if str(primary.get("chart_no") or "").startswith("차7"):
        return ["한쪽 지시표지의 위치와 양 차량 신호·진행 방향 확인 필요"]
    if str(primary.get("chart_no") or "").startswith("차43"):
        return ["차선변경 주체, 방향지시등, 차선변경 완료 여부 확인 필요"]
    if str(primary.get("chart_no") or "").startswith("차41"):
        return ["앞차 급정거 사유와 제동등 정상 작동 여부 확인 필요"]
    if str(primary.get("chart_no") or "").startswith("차42"):
        return ["정차 위치, 야간 등화, 시야장애 및 회피 가능성 확인 필요"]
    return []


def _build_retrieval_model_info(evidence_bundle: EvidenceBundle) -> dict[str, Any]:
    return {
        "cache_hit": evidence_bundle.retrieval.get("cache_hit"),
        "cache_key": evidence_bundle.retrieval.get("cache_key"),
        "knia_cache_hit": evidence_bundle.knia_result.get("cache_hit"),
        "knia_cache_key": evidence_bundle.knia_result.get("cache_key"),
        "knia_json_cache": evidence_bundle.knia_json_result.get("cache"),
        "query_expansion_terms": evidence_bundle.retrieval.get("query_expansion_terms")
        or evidence_bundle.evidence_query.get("query_terms"),
        "knia_query_expansion_terms": evidence_bundle.knia_result.get("query_expansion_terms") or [],
    }
