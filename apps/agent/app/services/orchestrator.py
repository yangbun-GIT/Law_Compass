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
from app.services.planner import AGENT_PLAN_VERSION, build_safe_fallback_plan, build_task_plan
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
    case_id: str | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    input_mode = _input_mode_for_text(structured_facts, selected_keywords, video_metadata)
    return _analyze_core(
        description_text=description_text,
        structured_facts=structured_facts,
        selected_keywords=selected_keywords,
        analysis_mode=analysis_mode,
        ai_profile=ai_profile,
        specialist_roles=specialist_roles,
        video_metadata=video_metadata,
        input_mode=input_mode,
        case_id=case_id,
        trace_id=trace_id,
    )


def analyze_video_case(
    preprocessed_summary: str,
    ai_profile: str,
    specialist_roles: list[str] | None,
    video_metadata: dict[str, Any] | None,
    structured_facts: dict[str, Any] | None = None,
    selected_keywords: list[str] | None = None,
    analysis_mode: str | None = None,
    case_id: str | None = None,
    upload_id: str | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    input_mode = _input_mode_for_video(structured_facts, selected_keywords, video_metadata)
    return _analyze_core(
        description_text=preprocessed_summary or "영상 분석 정보가 충분하지 않습니다. 사고 상황을 글로 조금 더 입력해 주세요.",
        structured_facts=structured_facts,
        selected_keywords=selected_keywords,
        analysis_mode=analysis_mode,
        ai_profile=ai_profile,
        specialist_roles=specialist_roles,
        video_metadata=video_metadata,
        input_mode=input_mode,
        case_id=case_id,
        upload_id=upload_id,
        trace_id=trace_id,
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
        input_mode="admin_diagnostic",
        case_id=payload.get("case_id"),
        upload_id=payload.get("upload_id"),
        trace_id=payload.get("trace_id"),
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
    input_mode: str | None,
    case_id: str | None,
    upload_id: str | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    agent_plan = _build_agent_plan_safe(
        description_text=description_text,
        structured_facts=structured_facts,
        selected_keywords=selected_keywords,
        video_metadata=video_metadata,
        analysis_mode=analysis_mode,
        input_mode=input_mode,
        case_id=case_id,
        upload_id=upload_id,
        trace_id=trace_id,
    )
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
    output["agent_plan"] = agent_plan.model_dump()
    trace_id = _safe_trace_id(trace_id) or output["agent_plan"].get("trace_id")
    if trace_id:
        output["trace_id"] = trace_id
        output["agent_plan"]["trace_id"] = trace_id
        output["model_info"]["trace_id"] = trace_id
    output["model_info"]["agent_plan_version"] = AGENT_PLAN_VERSION
    return enrich_analysis_output(
        output=output,
        context=context,
        evidence_bundle=evidence_bundle,
        analysis_bundle=analysis_bundle,
        judgment_contract=judgment_contract,
        reflection_loop=reflection_loop,
    )


def _build_agent_plan_safe(
    *,
    description_text: str,
    structured_facts: dict[str, Any] | None,
    selected_keywords: list[str] | None,
    video_metadata: dict[str, Any] | None,
    analysis_mode: str | None,
    input_mode: str | None,
    case_id: str | None,
    upload_id: str | None,
    trace_id: str | None = None,
) -> Any:
    try:
        return build_task_plan(
            description_text=description_text,
            structured_facts=structured_facts,
            selected_keywords=selected_keywords,
            video_metadata=video_metadata,
            analysis_mode=analysis_mode,
            input_mode=input_mode,  # type: ignore[arg-type]
            case_id=case_id,
            upload_id=upload_id,
            trace_id=trace_id,
        )
    except Exception as exc:  # pragma: no cover - defensive guard for production safety
        return build_safe_fallback_plan(
            error=exc,
            input_mode=input_mode if input_mode in {"text_only", "video_only", "text_and_video", "followup_reanalysis", "admin_diagnostic"} else None,  # type: ignore[arg-type]
            case_id=case_id,
            trace_id=trace_id,
        )


def _input_mode_for_text(
    structured_facts: dict[str, Any] | None,
    selected_keywords: list[str] | None,
    video_metadata: dict[str, Any] | None,
) -> str:
    facts = structured_facts if isinstance(structured_facts, dict) else {}
    if _has_followup_markers(facts):
        return "followup_reanalysis"
    if _has_video_metadata(video_metadata):
        return "text_and_video"
    if selected_keywords:
        return "text_only"
    return "text_only"


def _safe_trace_id(value: Any) -> str | None:
    text = str(value or "").strip()
    return text[:120] or None


def _input_mode_for_video(
    structured_facts: dict[str, Any] | None,
    selected_keywords: list[str] | None,
    video_metadata: dict[str, Any] | None,
) -> str:
    facts = structured_facts if isinstance(structured_facts, dict) else {}
    if _has_followup_markers(facts):
        return "followup_reanalysis"
    if facts or selected_keywords:
        return "text_and_video"
    return "video_only" if _has_video_metadata(video_metadata) else "text_only"


def _has_followup_markers(structured_facts: dict[str, Any]) -> bool:
    return any(str(key).startswith("_followup_") for key in structured_facts)


def _has_video_metadata(video_metadata: dict[str, Any] | None) -> bool:
    if not isinstance(video_metadata, dict) or not video_metadata:
        return False
    metadata = video_metadata.get("metadata") if isinstance(video_metadata.get("metadata"), dict) else video_metadata
    return bool(
        metadata.get("representative_frames")
        or metadata.get("observations")
        or metadata.get("duration_sec")
        or metadata.get("file_name")
        or video_metadata.get("upload_id")
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

