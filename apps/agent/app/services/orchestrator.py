from __future__ import annotations

import os
from typing import Any

from app.personas.accident_scenario_personas import SCENARIO_PERSONA_HINTS
from app.services.agent_execution_trace import VERSION as AGENT_TRACE_VERSION, build_agent_execution_trace
from app.services.elderly_friendly.report_simplifier import build_elderly_friendly_report
from app.services.judgment_contract import apply_judgment_contract_to_output, build_judgment_contract
from app.services.keyword_recommender import recommend_keywords, suggest_next_inputs
from app.services.orchestration_stages import (
    build_case_context,
    collect_evidence_stage,
    run_analysis_stage,
    run_reflection_requery_stage,
)
from app.services.reflection_loop import VERSION as REFLECTION_LOOP_VERSION, build_reflection_loop_result
from app.services.report_composer import compose_analysis_output
from app.services.specialists import pick_specialists


def analyze_case(
    description_text: str,
    structured_facts: dict[str, Any] | None = None,
    selected_keywords: list[str] | None = None,
    analysis_mode: str | None = None,
    ai_profile: str | None = None,
    specialist_roles: list[str] | None = None,
) -> dict[str, Any]:
    return _analyze_core(
        description_text=description_text,
        structured_facts=structured_facts,
        selected_keywords=selected_keywords,
        analysis_mode=analysis_mode,
        ai_profile=ai_profile,
        specialist_roles=specialist_roles,
        video_metadata=None,
    )


def analyze_video_case(
    preprocessed_summary: str,
    ai_profile: str,
    specialist_roles: list[str] | None,
    video_metadata: dict[str, Any] | None,
    structured_facts: dict[str, Any] | None = None,
    selected_keywords: list[str] | None = None,
    analysis_mode: str | None = None,
) -> dict[str, Any]:
    return _analyze_core(
        description_text=preprocessed_summary or "영상 분석 정보가 충분하지 않습니다. 사고 상황을 글로 조금 더 입력해 주세요.",
        structured_facts=structured_facts,
        selected_keywords=selected_keywords,
        analysis_mode=analysis_mode,
        ai_profile=ai_profile,
        specialist_roles=specialist_roles,
        video_metadata=video_metadata,
    )


def analyze_scenario(payload: dict[str, Any]) -> dict[str, Any]:
    return _analyze_core(
        description_text=payload.get("description_text", ""),
        structured_facts=payload.get("structured_facts") or {},
        selected_keywords=payload.get("selected_keywords") or [],
        analysis_mode=payload.get("analysis_mode"),
        ai_profile=payload.get("ai_profile"),
        specialist_roles=payload.get("specialist_roles"),
        video_metadata=payload.get("video_metadata"),
    )


def _analyze_core(
    *,
    description_text: str,
    structured_facts: dict[str, Any] | None,
    selected_keywords: list[str] | None,
    analysis_mode: str | None,
    ai_profile: str | None,
    specialist_roles: list[str] | None,
    video_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    context = build_case_context(
        description_text=description_text,
        structured_facts=structured_facts,
        selected_keywords=selected_keywords,
        analysis_mode=analysis_mode,
        video_metadata=video_metadata,
    )
    evidence_bundle = collect_evidence_stage(context, video_metadata)
    analysis_bundle = run_analysis_stage(context, evidence_bundle)
    reflection_stage = run_reflection_requery_stage(context, evidence_bundle, analysis_bundle)
    evidence_bundle = reflection_stage.evidence_bundle
    analysis_bundle = reflection_stage.analysis_bundle
    judgment_contract = build_judgment_contract(
        scenario=context.scenario,
        evidence=evidence_bundle.evidence,
        legal_analysis=analysis_bundle.legal_analysis,
        fault_ratio=analysis_bundle.fault_ratio,
        legal_liability=analysis_bundle.legal_liability,
        insurance_guide=analysis_bundle.insurance_guide,
        action_plan=analysis_bundle.action_plan,
        evidence_audit=analysis_bundle.evidence_audit,
        claim_evidence=analysis_bundle.claim_evidence,
        missing_fields=context.decision_blocking_missing_fields,
        input_requirements=context.input_requirements,
        knia_matches=evidence_bundle.knia_matches,
        knia_fault_estimate=evidence_bundle.knia_fault_estimate,
    )
    reflection_loop = build_reflection_loop_result(
        initial_plan=reflection_stage.requery_plan,
        final_evidence_audit=analysis_bundle.evidence_audit,
        input_requirements=context.input_requirements,
        followup_loop=context.followup_loop,
        judgment_contract=judgment_contract,
        requery_attempted=bool(reflection_stage.requery_plan.get("should_requery")),
        requery_added_count=reflection_stage.requery_added_count,
    )
    recommended_keywords = recommend_keywords(
        scenario_type=context.scenario["scenario_type"],
        facts=context.normalized["structured_facts"],
        selected_keywords=context.normalized["selected_keywords"],
        evidence=evidence_bundle.evidence,
    )
    suggested_next_inputs = suggest_next_inputs(
        context.normalized["structured_facts"],
        context.scenario["scenario_type"],
        context.decision_blocking_missing_fields,
        input_requirements=context.input_requirements,
    )
    profile = ai_profile or _profile_for_scenario(context.scenario["scenario_type"])
    recommended_specialists = specialist_roles or pick_specialists(profile, None)
    recommended_specialists = list(dict.fromkeys([*recommended_specialists, *SCENARIO_PERSONA_HINTS.get(context.scenario["scenario_type"], [])]))[:12]
    output = compose_analysis_output(
        normalized_input=context.normalized,
        scenario=context.scenario,
        party_type_action_guide=context.party_type_action_guide,
        video_context=context.video_context,
        evidence=evidence_bundle.evidence,
        legal_evidence=evidence_bundle.legal_evidence,
        knia_evidence=evidence_bundle.knia_evidence,
        knia_matches=evidence_bundle.knia_matches,
        knia_primary_match=evidence_bundle.knia_matches[0] if evidence_bundle.knia_matches else None,
        legal_analysis=analysis_bundle.legal_analysis,
        fault_ratio=analysis_bundle.fault_ratio,
        legal_liability=analysis_bundle.legal_liability,
        insurance_guide=analysis_bundle.insurance_guide,
        action_plan=analysis_bundle.action_plan,
        evidence_audit=analysis_bundle.evidence_audit,
        recommended_keywords=recommended_keywords,
        recommended_specialists=recommended_specialists,
        input_requirements=context.input_requirements,
        followup_loop=context.followup_loop,
        suggested_next_inputs=suggested_next_inputs,
        llm_enabled=bool(os.getenv("OPENAI_API_KEY")),
        ai_profile=profile,
    )
    output = apply_judgment_contract_to_output(output, judgment_contract)
    output["reflection_loop"] = reflection_loop
    output["model_info"]["reflection_loop_version"] = REFLECTION_LOOP_VERSION
    output["agent_trace"] = build_agent_execution_trace(output)
    output["model_info"]["agent_trace_version"] = AGENT_TRACE_VERSION
    output["elderly_friendly_report"] = build_elderly_friendly_report(output)
    output["claim_evidence"] = analysis_bundle.claim_evidence
    output["knia_json_evidence"] = evidence_bundle.knia_json_evidence
    if evidence_bundle.knia_fault_estimate:
        output["knia_base_fault"] = evidence_bundle.knia_fault_estimate.get("base_fault")
        output["knia_final_fault"] = evidence_bundle.knia_fault_estimate.get("final_fault")
        output["knia_applied_adjustments"] = evidence_bundle.knia_fault_estimate.get("selected_adjustments") or []
        output["knia_rejected_adjustments"] = evidence_bundle.knia_fault_estimate.get("rejected_adjustments") or []
        output["knia_calculation_steps"] = evidence_bundle.knia_fault_estimate.get("calculation_steps") or []
        output["knia_adjustment_evidence"] = evidence_bundle.knia_fault_estimate.get("evidence_used") or []
        output["knia_reference_evidence"] = evidence_bundle.knia_reference_evidence
        output.setdefault("elderly_friendly_report", {})["knia_fault_adjustment_card"] = {
            "title": "KNIA 원문 근거 및 가감요소 적용",
            "base_fault": evidence_bundle.knia_fault_estimate.get("base_fault"),
            "final_fault": evidence_bundle.knia_fault_estimate.get("final_fault"),
            "user_fault": {
                "my": analysis_bundle.fault_ratio.get("my"),
                "other": analysis_bundle.fault_ratio.get("other"),
                "role": analysis_bundle.fault_ratio.get("user_vehicle_role"),
                "role_label": analysis_bundle.fault_ratio.get("user_vehicle_role_label"),
            },
            "applied_adjustments": evidence_bundle.knia_fault_estimate.get("selected_adjustments") or [],
            "rejected_adjustments": (evidence_bundle.knia_fault_estimate.get("rejected_adjustments") or [])[:5],
            "calculation_steps": evidence_bundle.knia_fault_estimate.get("calculation_steps") or [],
            "notice": evidence_bundle.knia_fault_estimate.get("notice"),
        }
    output["related_knia_source_links"] = [x.get("source_url") for x in evidence_bundle.knia_json_evidence if x.get("source_url")]
    output["model_info"]["retrieval"] = {
        "cache_hit": evidence_bundle.retrieval.get("cache_hit"),
        "cache_key": evidence_bundle.retrieval.get("cache_key"),
        "knia_cache_hit": evidence_bundle.knia_result.get("cache_hit"),
        "knia_cache_key": evidence_bundle.knia_result.get("cache_key"),
        "knia_json_cache": evidence_bundle.knia_json_result.get("cache"),
        "query_expansion_terms": evidence_bundle.retrieval.get("query_expansion_terms") or evidence_bundle.evidence_query.get("query_terms"),
        "knia_query_expansion_terms": evidence_bundle.knia_result.get("query_expansion_terms") or [],
    }
    output["model_info"]["scenario_classifier"] = context.scenario
    return output


def _profile_for_scenario(scenario_type: str) -> str:
    return {
        "rear_end_collision": "rear_end_focus",
        "school_zone_child_accident": "pedestrian_focus",
        "intersection_signal_violation": "intersection_focus",
        "lane_change_collision": "lane_change_focus",
        "pedestrian_crosswalk_accident": "pedestrian_focus",
        "bicycle_collision": "pedestrian_focus",
        "object_collision": "default_vehicle_collision",
        "single_vehicle_accident": "default_vehicle_collision",
    }.get(scenario_type, "default_vehicle_collision")

