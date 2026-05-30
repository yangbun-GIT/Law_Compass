from __future__ import annotations
from typing import Any
from app.services.elderly_friendly.report_simplifier import build_elderly_friendly_report
from app.services.elderly_friendly.ui_text_mapper import scenario_label
from app.services.analysis_modes import normalize_analysis_mode
from app.services.llm_client import generate_final_report
from app.services.llm_policy import evaluate_llm_usage, mark_llm_output_unavailable, summarize_case_llm_policy


def compose_analysis_output(
    *,
    normalized_input: dict[str, Any],
    scenario: dict[str, Any],
    party_type_action_guide: dict[str, Any] | None = None,
    video_context: dict[str, Any],
    evidence: list[dict[str, Any]],
    legal_evidence: list[dict[str, Any]] | None = None,
    knia_evidence: list[dict[str, Any]] | None = None,
    knia_matches: list[dict[str, Any]] | None = None,
    knia_primary_match: dict[str, Any] | None = None,
    legal_analysis: dict[str, Any],
    fault_ratio: dict[str, Any],
    legal_liability: dict[str, Any],
    insurance_guide: dict[str, Any],
    action_plan: list[str],
    evidence_audit: dict[str, Any],
    recommended_keywords: list[str],
    recommended_specialists: list[str],
    suggested_next_inputs: list[str],
    llm_enabled: bool,
    ai_profile: str,
    input_requirements: dict[str, Any] | None = None,
    followup_loop: dict[str, Any] | None = None,
) -> dict[str, Any]:
    final_report_usage = evaluate_llm_usage(section="final_report", evidence=evidence, facts=normalized_input.get("structured_facts") or {})
    final = generate_final_report(normalized_input=normalized_input, scenario=scenario, evidence=evidence, legal_analysis=legal_analysis, fault_ratio=fault_ratio, legal_liability=legal_liability, insurance_guide=insurance_guide, action_plan=action_plan) if final_report_usage["allowed"] else None
    accident_title = final.get("accident_title") if isinstance(final, dict) else None
    summary = final.get("accident_summary") if isinstance(final, dict) else None
    if final_report_usage["allowed"] and not summary:
        final_report_usage = mark_llm_output_unavailable(final_report_usage, stage="final_report")
    final_report_usage = {**final_report_usage, "used": bool(summary)}
    if not accident_title:
        accident_title = _fallback_title(normalized_input)
    if not summary:
        summary = _fallback_summary(normalized_input, scenario, legal_analysis)
    uncertainty_level = evidence_audit.get("uncertainty_level", "medium")
    party_type_action_guide = party_type_action_guide or {}
    input_requirements = input_requirements or {}
    followup_loop = followup_loop or {}
    analysis_mode = normalize_analysis_mode(normalized_input.get("analysis_mode"))
    guided_questions = (input_requirements.get("guided_questionnaire") or {}).get("questions") or []
    uncertain_facts = _build_uncertain_facts(input_requirements, normalized_input)
    followup_required = bool(uncertain_facts or guided_questions or input_requirements.get("blocking_fields"))
    technical = {
        "analysis_status": "provisional" if followup_required else "final_or_review_required",
        "followup_required": followup_required,
        "confidence": _build_confidence_block(uncertainty_level, scenario, fault_ratio, knia_primary_match),
        "initial_intake_summary": normalized_input.get("initial_intake_summary") or {},
        "uncertain_facts": uncertain_facts,
        "followup_questions_structured": guided_questions,
        "provisional_result": {
            "scenario_type": scenario.get("scenario_type"),
            "fault_ratio": {
                "my": fault_ratio.get("my"),
                "other": fault_ratio.get("other"),
            },
            "knia_chart_no": (knia_primary_match or {}).get("chart_no") or (knia_primary_match or {}).get("aggregate_chart_no"),
        },
        "analysis_mode": analysis_mode,
        "display_mode": analysis_mode,
        "accident_title": accident_title,
        "accident_summary": summary,
        "scenario_type": scenario["scenario_type"],
        "accident_party_type": scenario.get("accident_party_type", "unknown"),
        "accident_party_label": scenario.get("accident_party_label", "사고유형 확인 필요"),
        "party_type_action_guide": party_type_action_guide,
        "structured_facts": {
            **normalized_input["structured_facts"],
            "scenario_type": scenario["scenario_type"],
            "scenario_tags": scenario["scenario_tags"],
            "accident_party_type": scenario.get("accident_party_type", "unknown"),
            "accident_party_label": scenario.get("accident_party_label", "사고유형 확인 필요"),
            "video_context": video_context,
            "_video_input_contract": normalized_input.get("video_input_contract") or {},
            "_fact_arbitration": normalized_input.get("fact_arbitration") or {},
            "_fact_sources": (normalized_input.get("fact_arbitration") or {}).get("fact_sources") or {},
            "_fact_source_weights": normalized_input.get("fact_source_weights") or {},
            "_initial_intake": normalized_input.get("initial_intake") or {},
            "missing_fields": normalized_input["missing_fields"],
            "required_input_fields": input_requirements.get("blocking_fields") or [],
            "optional_input_fields": input_requirements.get("optional_fields") or [],
        },
        "legal_analysis": legal_analysis,
        "fault_ratio": fault_ratio,
        "legal_liability": legal_liability,
        "insurance_guide": insurance_guide,
        "action_plan": action_plan,
        "evidence": evidence,
        "legal_evidence": legal_evidence or evidence,
        "knia_evidence": knia_evidence or [],
        "combined_evidence": evidence,
        "knia_matches": knia_matches or [],
        "knia_primary_match": knia_primary_match,
        "evidence_audit": evidence_audit,
        "uncertainty": {"level": uncertainty_level, "reason": "근거 문서와 입력 사실의 충분성에 따라 추정 신뢰도가 달라질 수 있습니다.", "confidence": {"low": 0.78, "medium": 0.55, "high": 0.35}.get(uncertainty_level, 0.5)},
        "disclaimers": ["본 결과는 법률/보험 자문이 아닌 AI 기반 참고 정보입니다.", "최종 과실비율, 보상금액, 형사책임은 수사기관, 보험사, 법원의 판단에 따릅니다.", "개인정보와 원본 영상은 필요한 범위에서만 보관하고, 민감정보 입력은 최소화해 주세요."],
        "followup_questions": evidence_audit.get("followup_questions", []) or [
            str(item.get("plain_question") or item.get("question"))
            for item in guided_questions
            if isinstance(item, dict) and (item.get("plain_question") or item.get("question"))
        ],
        "input_requirements": input_requirements,
        "guided_questionnaire": input_requirements.get("guided_questionnaire") or {},
        "followup_loop": followup_loop,
        "video_input_contract": normalized_input.get("video_input_contract") or {},
        "fact_arbitration": normalized_input.get("fact_arbitration") or {},
        "fact_source_weights": normalized_input.get("fact_source_weights") or {},
        "required_input_questions": input_requirements.get("questions") or [],
        "recommended_keywords": recommended_keywords,
        "recommended_specialists": recommended_specialists,
        "suggested_next_inputs": suggested_next_inputs,
        "model_info": {
            "orchestrator": "legal-rag-multi-analyst-v2-party-type",
            "ai_profile": ai_profile,
            "analysis_mode": analysis_mode,
            "llm_enabled": llm_enabled,
            "rag_top_k": len(evidence),
            "evidence_cache_key": evidence[0].get("cache_key") if evidence else None,
            "security_flags": normalized_input["security_flags"],
            "video_input_contract": normalized_input.get("video_input_contract") or {},
            "fact_arbitration": normalized_input.get("fact_arbitration") or {},
            "llm_policy": summarize_case_llm_policy({
                "traffic_law_analysis": legal_analysis,
                "fault_ratio_analysis": fault_ratio,
                "criminal_liability_analysis": legal_liability,
                "insurance_guidance": insurance_guide,
                "final_report": {"llm_usage": final_report_usage},
            }),
            "followup_loop": followup_loop,
        },
    }
    technical["elderly_friendly_report"] = build_elderly_friendly_report(technical)
    return technical


def _build_uncertain_facts(input_requirements: dict[str, Any], normalized_input: dict[str, Any]) -> list[dict[str, Any]]:
    questions = input_requirements.get("questions") or []
    arbitration = normalized_input.get("fact_arbitration") or {}
    conflict_fields = {
        str(item.get("field"))
        for item in (arbitration.get("requires_confirmation") or [])
        if isinstance(item, dict) and item.get("field")
    }
    out: list[dict[str, Any]] = []
    for question in questions[:6]:
        if not isinstance(question, dict):
            continue
        field = str(question.get("field") or question.get("fact_key") or "").strip()
        if not field:
            continue
        confidence = 0.35 if field in conflict_fields else 0.55
        out.append({
            "field": field,
            "label": question.get("label") or field.replace("_", " "),
            "reason": question.get("reason") or "과실비율 판단에 영향을 줄 수 있어 추가 확인이 필요합니다.",
            "impact": "fault_adjustment" if question.get("blocks_decision") else "context",
            "confidence": confidence,
        })
    return out


def _build_confidence_block(
    uncertainty_level: str,
    scenario: dict[str, Any],
    fault_ratio: dict[str, Any],
    knia_primary_match: dict[str, Any] | None,
) -> dict[str, Any]:
    base = {"low": 0.42, "medium": 0.62, "high": 0.82}.get(str(uncertainty_level), 0.58)
    return {
        "overall": uncertainty_level,
        "scenario_type": _as_confidence(scenario.get("confidence"), base),
        "fault_ratio": _as_confidence(fault_ratio.get("confidence"), base),
        "knia_match": _as_confidence((knia_primary_match or {}).get("confidence") or (knia_primary_match or {}).get("score"), base),
    }


def _as_confidence(value: Any, fallback: float) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 2)
    except (TypeError, ValueError):
        return round(fallback, 2)


def _fallback_summary(normalized_input: dict[str, Any], scenario: dict[str, Any], legal_analysis: dict[str, Any]) -> str:
    text = (normalized_input.get("user_visible_summary_text") or normalized_input.get("description_text") or "입력하신 사고").strip()[:180]
    label = scenario_label(scenario.get("scenario_type"))
    if text.endswith(("입니다.", "했습니다.", "발생했습니다.", "사고입니다.")):
        return text
    return f"{text} 상황은 {label}로 보입니다."


def _fallback_title(normalized_input: dict[str, Any]) -> str:
    text = (normalized_input.get("user_visible_summary_text") or normalized_input.get("description_text") or "입력한 사고 상황").strip()
    text = text.lstrip(" ,，.")
    marker = " 사고"
    if marker in text:
        return text[: text.find(marker) + len(marker)].strip()
    first_sentence = text.split(".")[0].strip()
    return first_sentence[:80] or "입력한 사고 상황"
