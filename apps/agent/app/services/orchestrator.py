from __future__ import annotations

import os
from typing import Any

from app.personas.accident_scenario_personas import SCENARIO_PERSONA_HINTS
from app.services.accident_party_action_guide import build_party_type_action_guide
from app.services.accident_perspective import infer_user_vehicle_role, map_fault_ratio_to_user
from app.services.agent_execution_trace import VERSION as AGENT_TRACE_VERSION, build_agent_execution_trace
from app.services.analysts.action_plan_analyst import analyze_action_plan
from app.services.analysts.criminal_liability_analyst import analyze_criminal_liability
from app.services.analysts.evidence_auditor import audit_evidence
from app.services.analysts.fault_ratio_analyst import analyze_fault_ratio
from app.services.analysts.insurance_analyst import analyze_insurance
from app.services.analysts.traffic_law_analyst import analyze_traffic_law
from app.services.claim_evidence_validator import apply_claim_evidence_audit, validate_claim_evidence
from app.services.elderly_friendly.report_simplifier import build_elderly_friendly_report
from app.services.input_normalizer import normalize_analysis_input
from app.services.input_requirements import build_followup_loop_state, build_input_requirements
from app.services.judgment_contract import apply_judgment_contract_to_output, build_judgment_contract
from app.services.keyword_recommender import recommend_keywords, suggest_next_inputs
from app.services.knia.knia_matcher import match_knia_charts
from app.services.knia.knia_fault_adjuster import estimate_knia_fault
from app.services.knia.knia_report_adapter import build_knia_evidence
from app.services.knia.knia_repository import KniaRepository
from app.services.rag_client import retrieve_for_scenario
from app.services.rag.two_stage_cache import search_knia_json_cached
from app.services.report_composer import compose_analysis_output
from app.services.scenario_classifier import classify_scenario
from app.services.scenario_search_terms import evidence_query_payload
from app.services.specialists import pick_specialists
from app.services.video_context_analyzer import summarize_video_context


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
    video_context = summarize_video_context(video_metadata)
    normalized = normalize_analysis_input(
        description_text=description_text,
        structured_facts=structured_facts,
        selected_keywords=selected_keywords,
        video_metadata=video_metadata,
        analysis_mode=analysis_mode,
    )
    scenario = classify_scenario(normalized["merged_text"], normalized["structured_facts"], normalized["selected_keywords"])
    user_vehicle_role = infer_user_vehicle_role(
        normalized["description_text"],
        normalized["structured_facts"],
        scenario.get("scenario_type"),
    )
    if user_vehicle_role != "unknown":
        normalized["structured_facts"] = {**normalized["structured_facts"], "user_vehicle_role": user_vehicle_role}
    party_type_action_guide = build_party_type_action_guide(
        scenario.get("accident_party_type", "unknown"),
        normalized["structured_facts"],
        scenario.get("scenario_type"),
    )
    input_requirements = build_input_requirements(
        facts=normalized["structured_facts"],
        scenario_type=scenario["scenario_type"],
        accident_party_type=scenario.get("accident_party_type"),
        missing_fields=normalized["missing_fields"],
        description_text=normalized["description_text"],
    )
    followup_loop = build_followup_loop_state(input_requirements, normalized["structured_facts"])
    decision_blocking_missing_fields = list(input_requirements.get("blocking_fields") or [])
    knia_result = match_knia_charts(
        description_text=normalized["description_text"],
        structured_facts=normalized["structured_facts"],
        selected_keywords=normalized["selected_keywords"],
        scenario_type=scenario["scenario_type"],
        accident_party_type=scenario.get("accident_party_type"),
        limit=5,
    )
    knia_matches = knia_result.get("items") or []
    evidence_query = evidence_query_payload(
        description_text=normalized["description_text"],
        facts=normalized["structured_facts"],
        selected_keywords=normalized["selected_keywords"],
        scenario_type=scenario.get("scenario_type"),
        scenario_tags=scenario.get("scenario_tags"),
        accident_party_type=scenario.get("accident_party_type"),
    )
    knia_json_result = search_knia_json_cached(
        evidence_query["query_text"],
        accident_party_type=scenario.get("accident_party_type"),
        scenario_type=scenario.get("scenario_type"),
        limit=5,
    )
    knia_json_evidence = knia_json_result.get("items") or []
    knia_fault_estimate: dict[str, Any] | None = None
    knia_reference_evidence: list[dict[str, Any]] = []
    if knia_matches:
        primary = knia_matches[0]
        try:
            knia_fault_estimate = estimate_knia_fault(
                chart_no=primary.get("chart_no"),
                chart_type=primary.get("chart_type") or "1",
                description_text=normalized["description_text"],
                selected_keywords=normalized["selected_keywords"],
                structured_facts=normalized["structured_facts"],
                video_metadata=video_metadata or {},
                scenario_type=scenario.get("scenario_type"),
                accident_party_type=scenario.get("accident_party_type"),
            )
            knia_reference_evidence.extend(_knia_estimate_to_evidence(knia_fault_estimate))
            refs = KniaRepository().get_chart_references(primary.get("chart_no"), primary.get("chart_type") or "1")
            knia_reference_evidence.extend(_knia_refs_to_evidence(primary, refs))
        except Exception:
            knia_fault_estimate = None
    knia_evidence = _normalize_evidence_items([*build_knia_evidence(knia_matches), *knia_reference_evidence, *knia_json_evidence], default_source="과실비율정보포털")
    retrieval = retrieve_for_scenario(
        scenario_type=scenario["scenario_type"],
        scenario_tags=scenario["scenario_tags"],
        description_text=normalized["description_text"],
        facts={**normalized["structured_facts"], "accident_party_type": scenario.get("accident_party_type")},
        selected_keywords=normalized["selected_keywords"],
        video_context=video_context,
        limit=8,
    )
    legal_evidence = _normalize_evidence_items(retrieval["items"], default_source="법률 근거")
    evidence = [*knia_evidence, *legal_evidence]
    text = normalized["merged_text"]
    legal_analysis = analyze_traffic_law(scenario_type=scenario["scenario_type"], facts=normalized["structured_facts"], evidence=evidence, text=text)
    fault_ratio = analyze_fault_ratio(scenario_type=scenario["scenario_type"], facts=normalized["structured_facts"], evidence=evidence, text=text)
    if knia_fault_estimate:
        final_fault = knia_fault_estimate.get("final_fault") or {}
        fault_ratio["knia_reference_fault"] = final_fault
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
    legal_liability = analyze_criminal_liability(scenario_type=scenario["scenario_type"], facts=normalized["structured_facts"], evidence=evidence, legal_analysis=legal_analysis, text=text)
    insurance_guide = analyze_insurance(scenario_type=scenario["scenario_type"], facts=normalized["structured_facts"], evidence=evidence, text=text)
    action_plan = analyze_action_plan(scenario_type=scenario["scenario_type"], facts=normalized["structured_facts"], legal_liability=legal_liability, insurance_guide=insurance_guide, evidence=evidence, text=text)
    evidence_audit = audit_evidence(
        scenario_type=scenario["scenario_type"],
        evidence=evidence,
        legal_analysis=legal_analysis,
        fault_ratio=fault_ratio,
        missing_fields=decision_blocking_missing_fields,
        input_requirements=input_requirements,
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
    judgment_contract = build_judgment_contract(
        scenario=scenario,
        evidence=evidence,
        legal_analysis=legal_analysis,
        fault_ratio=fault_ratio,
        legal_liability=legal_liability,
        insurance_guide=insurance_guide,
        action_plan=action_plan,
        evidence_audit=evidence_audit,
        claim_evidence=claim_evidence,
        missing_fields=decision_blocking_missing_fields,
        input_requirements=input_requirements,
        knia_matches=knia_matches,
        knia_fault_estimate=knia_fault_estimate,
    )
    recommended_keywords = recommend_keywords(scenario_type=scenario["scenario_type"], facts=normalized["structured_facts"], selected_keywords=normalized["selected_keywords"], evidence=evidence)
    suggested_next_inputs = suggest_next_inputs(
        normalized["structured_facts"],
        scenario["scenario_type"],
        decision_blocking_missing_fields,
        input_requirements=input_requirements,
    )
    profile = ai_profile or _profile_for_scenario(scenario["scenario_type"])
    recommended_specialists = specialist_roles or pick_specialists(profile, None)
    recommended_specialists = list(dict.fromkeys([*recommended_specialists, *SCENARIO_PERSONA_HINTS.get(scenario["scenario_type"], [])]))[:12]
    output = compose_analysis_output(
        normalized_input=normalized,
        scenario=scenario,
        party_type_action_guide=party_type_action_guide,
        video_context=video_context,
        evidence=evidence,
        legal_evidence=legal_evidence,
        knia_evidence=knia_evidence,
        knia_matches=knia_matches,
        knia_primary_match=knia_matches[0] if knia_matches else None,
        legal_analysis=legal_analysis,
        fault_ratio=fault_ratio,
        legal_liability=legal_liability,
        insurance_guide=insurance_guide,
        action_plan=action_plan,
        evidence_audit=evidence_audit,
        recommended_keywords=recommended_keywords,
        recommended_specialists=recommended_specialists,
        input_requirements=input_requirements,
        followup_loop=followup_loop,
        suggested_next_inputs=suggested_next_inputs,
        llm_enabled=bool(os.getenv("OPENAI_API_KEY")),
        ai_profile=profile,
    )
    output = apply_judgment_contract_to_output(output, judgment_contract)
    output["agent_trace"] = build_agent_execution_trace(output)
    output["model_info"]["agent_trace_version"] = AGENT_TRACE_VERSION
    output["elderly_friendly_report"] = build_elderly_friendly_report(output)
    output["claim_evidence"] = claim_evidence
    output["knia_json_evidence"] = knia_json_evidence
    if knia_fault_estimate:
        output["knia_base_fault"] = knia_fault_estimate.get("base_fault")
        output["knia_final_fault"] = knia_fault_estimate.get("final_fault")
        output["knia_applied_adjustments"] = knia_fault_estimate.get("selected_adjustments") or []
        output["knia_rejected_adjustments"] = knia_fault_estimate.get("rejected_adjustments") or []
        output["knia_calculation_steps"] = knia_fault_estimate.get("calculation_steps") or []
        output["knia_adjustment_evidence"] = knia_fault_estimate.get("evidence_used") or []
        output["knia_reference_evidence"] = knia_reference_evidence
        output.setdefault("elderly_friendly_report", {})["knia_fault_adjustment_card"] = {
            "title": "KNIA 원문 근거 및 가감요소 적용",
            "base_fault": knia_fault_estimate.get("base_fault"),
            "final_fault": knia_fault_estimate.get("final_fault"),
            "user_fault": {
                "my": fault_ratio.get("my"),
                "other": fault_ratio.get("other"),
                "role": fault_ratio.get("user_vehicle_role"),
                "role_label": fault_ratio.get("user_vehicle_role_label"),
            },
            "applied_adjustments": knia_fault_estimate.get("selected_adjustments") or [],
            "rejected_adjustments": (knia_fault_estimate.get("rejected_adjustments") or [])[:5],
            "calculation_steps": knia_fault_estimate.get("calculation_steps") or [],
            "notice": knia_fault_estimate.get("notice"),
        }
    output["related_knia_source_links"] = [x.get("source_url") for x in knia_json_evidence if x.get("source_url")]
    output["model_info"]["retrieval"] = {
        "cache_hit": retrieval.get("cache_hit"),
        "cache_key": retrieval.get("cache_key"),
        "knia_cache_hit": knia_result.get("cache_hit"),
        "knia_cache_key": knia_result.get("cache_key"),
        "knia_json_cache": knia_json_result.get("cache"),
        "query_expansion_terms": retrieval.get("query_expansion_terms") or evidence_query.get("query_terms"),
        "knia_query_expansion_terms": knia_result.get("query_expansion_terms") or [],
    }
    output["model_info"]["scenario_classifier"] = scenario
    return output


def _knia_estimate_to_evidence(estimate: dict[str, Any]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    source_chart = estimate.get("source_chart") or {}
    base = estimate.get("base_fault") or {}
    if base:
        evidence.append({
            "source_type": "knia_base_fault",
            "title": f"KNIA 원문 기본과실 A{base.get('A')}:B{base.get('B')}",
            "plain_summary": "KNIA 상세 기준에서 수집한 기본과실을 사용했습니다.",
            "source_url": source_chart.get("source_detail_url"),
            "used_for": "과실비율 기본값",
        })
    for item in estimate.get("selected_adjustments") or []:
        effect = item.get("applied_effect") or {}
        evidence.append({
            "source_type": "knia_adjustment_factor",
            "title": f"가감요소: {item.get('label')}",
            "plain_summary": f"A {effect.get('A', 0):+d}, B {effect.get('B', 0):+d}로 반영했습니다.",
            "related_reason": ", ".join(item.get("matched_by") or []),
            "source_url": item.get("source_detail_url") or source_chart.get("source_detail_url"),
            "used_for": "과실비율 가감요소",
        })
    return evidence


def _normalize_evidence_items(items: list[dict[str, Any]], *, default_source: str) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("article_title") or item.get("law_name") or "교통사고 관련 근거"
        source = item.get("source") or item.get("source_label") or default_source
        normalized.append({**item, "title": str(title), "source": str(source)})
    return normalized


def _knia_refs_to_evidence(primary: dict[str, Any], refs: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    source_url = primary.get("source_detail_url") or primary.get("source_url")
    evidence: list[dict[str, Any]] = []
    for item in (refs.get("adjustment_explanations") or [])[:3]:
        evidence.append({
            "source_type": "knia_adjustment_explanation",
            "title": item.get("title") or "KNIA 수정요소해설",
            "plain_summary": item.get("body"),
            "source_url": item.get("source_detail_url") or source_url,
            "used_for": "가감요소 적용 취지",
        })
    for item in (refs.get("related_laws") or [])[:3]:
        evidence.append({
            "source_type": "knia_related_law",
            "title": item.get("law_title") or "KNIA 관련법규",
            "law_name": item.get("law_title"),
            "plain_summary": item.get("law_text"),
            "source_url": item.get("source_detail_url") or source_url,
            "used_for": "관련 법규 근거",
        })
    for item in (refs.get("case_references") or [])[:2]:
        evidence.append({
            "source_type": "knia_case_reference",
            "title": item.get("case_title") or "KNIA 판례·조정사례",
            "plain_summary": item.get("decision_summary") or item.get("case_body"),
            "source_url": item.get("source_detail_url") or source_url,
            "used_for": "유사 사례 근거",
        })
    return evidence


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

