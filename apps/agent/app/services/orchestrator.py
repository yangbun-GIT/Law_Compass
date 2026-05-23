from __future__ import annotations

import os
from typing import Any

from app.personas.accident_scenario_personas import SCENARIO_PERSONA_HINTS
from app.services.judgment_contract import build_judgment_contract
from app.services.keyword_recommender import recommend_keywords, suggest_next_inputs
from app.services.orchestration_stages import (
    build_case_context,
    collect_evidence_stage,
    enrich_analysis_output,
    run_analysis_stage,
    run_reflection_requery_stage,
)
from app.services.reflection_loop import build_reflection_loop_result
from app.services.report_composer import compose_analysis_output
from app.services.specialists import pick_specialists


def analyze_case(
    description_text: str,
    structured_facts: dict[str, Any] | None = None,
    selected_keywords: list[str] | None = None,
    video_metadata: dict[str, Any] | None = None,
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
        video_metadata=video_metadata,
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
    return enrich_analysis_output(
        output=output,
        context=context,
        evidence_bundle=evidence_bundle,
        analysis_bundle=analysis_bundle,
        judgment_contract=judgment_contract,
        reflection_loop=reflection_loop,
    )


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

