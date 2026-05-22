from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SectionPolicy:
    section: str
    mode: str
    required_family: str
    authority: str
    allowed_outputs: tuple[str, ...]
    deterministic_authority: tuple[str, ...]


SECTION_POLICIES: dict[str, SectionPolicy] = {
    "traffic_law_analysis": SectionPolicy(
        section="traffic_law_analysis",
        mode="evidence_bound_interpretation",
        required_family="legal",
        authority="LLM은 검색된 법률 근거의 쉬운 해석만 보조하며 적용 법규 확정권은 갖지 않습니다.",
        allowed_outputs=("legal_issue_summary", "risk_flags", "required_facts"),
        deterministic_authority=("evidence_ids", "applicable_rules", "judgment_status"),
    ),
    "fault_ratio_analysis": SectionPolicy(
        section="fault_ratio_analysis",
        mode="knia_bound_explanation",
        required_family="knia",
        authority="LLM은 KNIA 기준 설명만 보조하며 과실비율 수치는 KNIA 산정기와 사용자 관점 매핑이 우선합니다.",
        allowed_outputs=("basis", "key_factors"),
        deterministic_authority=("my", "other", "knia_reference_fault", "user_vehicle_role", "judgment_status"),
    ),
    "criminal_liability_analysis": SectionPolicy(
        section="criminal_liability_analysis",
        mode="legal_risk_checklist",
        required_family="legal",
        authority="LLM은 수사·법원 판단을 대체하지 않고 법률 근거 기반 체크리스트만 보조합니다.",
        allowed_outputs=("risk_flags", "checklist", "note"),
        deterministic_authority=("reporting_required", "criminal_risk_level", "judgment_status"),
    ),
    "insurance_guidance": SectionPolicy(
        section="insurance_guidance",
        mode="procedural_guidance",
        required_family="any",
        authority="LLM은 보험 처리 절차 설명만 보조하며 보상금액·책임 확정 판단은 생성하지 않습니다.",
        allowed_outputs=("summary", "steps", "required_documents", "next_steps"),
        deterministic_authority=("claim_type", "judgment_status"),
    ),
    "action_plan": SectionPolicy(
        section="action_plan",
        mode="procedural_guidance",
        required_family="any",
        authority="LLM은 사고 후 대응 순서 정리만 보조하며 책임·과실·형사 판단은 생성하지 않습니다.",
        allowed_outputs=("action_plan",),
        deterministic_authority=("reporting_required", "injury", "scenario_type"),
    ),
    "final_report": SectionPolicy(
        section="final_report",
        mode="summary_only",
        required_family="any",
        authority="LLM은 이미 검증된 섹션을 쉬운 문장으로 요약하는 데만 사용됩니다.",
        allowed_outputs=("accident_summary",),
        deterministic_authority=("fault_ratio", "legal_liability", "evidence", "agent_judgment"),
    ),
}


def evaluate_llm_usage(
    *,
    section: str,
    evidence: list[dict[str, Any]],
    facts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = SECTION_POLICIES.get(section) or SectionPolicy(
        section=section,
        mode="disabled_unknown_section",
        required_family="any",
        authority="정의되지 않은 섹션에서는 LLM을 사용하지 않습니다.",
        allowed_outputs=(),
        deterministic_authority=(),
    )
    provider_enabled = _provider_enabled()
    family_counts = _family_counts(evidence)
    has_required_evidence = _has_required_family(policy.required_family, family_counts, evidence)
    facts = facts or {}
    missing_blocking_fields = list(facts.get("required_input_fields") or facts.get("missing_fields") or [])
    allowed = provider_enabled and has_required_evidence and not _has_blocking_input_for_section(section, missing_blocking_fields)
    reason = "allowed"
    if not provider_enabled:
        reason = "llm_provider_disabled"
    elif not has_required_evidence:
        reason = f"required_{policy.required_family}_evidence_missing"
    elif _has_blocking_input_for_section(section, missing_blocking_fields):
        reason = "required_input_fields_missing"
    return {
        "section": policy.section,
        "provider_enabled": provider_enabled,
        "allowed": allowed,
        "used": False,
        "reason": reason,
        "mode": policy.mode,
        "required_evidence_family": policy.required_family,
        "evidence_family_counts": family_counts,
        "authority": policy.authority,
        "allowed_outputs": list(policy.allowed_outputs),
        "deterministic_authority": list(policy.deterministic_authority),
    }


def should_call_llm(*, section: str, evidence: list[dict[str, Any]], facts: dict[str, Any] | None = None) -> bool:
    return bool(evaluate_llm_usage(section=section, evidence=evidence, facts=facts).get("allowed"))


def attach_llm_usage(output: dict[str, Any], usage: dict[str, Any], *, used: bool) -> dict[str, Any]:
    updated = dict(output)
    updated["llm_usage"] = {**usage, "used": used}
    if not used:
        updated.setdefault("analysis_source", "deterministic_fallback")
    else:
        updated.setdefault("analysis_source", "llm_assisted_guarded")
    return updated


def mark_llm_output_unavailable(usage: dict[str, Any], *, stage: str) -> dict[str, Any]:
    return {
        **usage,
        "reason": "llm_output_unavailable",
        "failure_observation": {
            "type": "llm_output_unavailable",
            "stage": stage,
            "recoverable": True,
            "safe_message": "LLM output was unavailable or rejected, so deterministic fallback was used.",
        },
    }


def summarize_case_llm_policy(section_outputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sections: dict[str, Any] = {}
    used_sections: list[str] = []
    blocked_sections: list[str] = []
    failed_sections: list[str] = []
    failure_observations: list[dict[str, Any]] = []
    for section, output in section_outputs.items():
        usage = output.get("llm_usage") if isinstance(output, dict) else None
        if not isinstance(usage, dict):
            continue
        sections[section] = {
            "allowed": usage.get("allowed"),
            "used": usage.get("used"),
            "reason": usage.get("reason"),
            "mode": usage.get("mode"),
            "required_evidence_family": usage.get("required_evidence_family"),
        }
        if isinstance(usage.get("failure_observation"), dict):
            sections[section]["failure_observation"] = usage["failure_observation"]
            failure_observations.append({"section": section, **usage["failure_observation"]})
        if usage.get("used"):
            used_sections.append(section)
        elif not usage.get("allowed"):
            blocked_sections.append(section)
        elif usage.get("reason") != "allowed":
            failed_sections.append(section)
    return {
        "version": "llm-policy-v1",
        "provider_enabled": _provider_enabled(),
        "used_sections": used_sections,
        "blocked_sections": blocked_sections,
        "failed_sections": failed_sections,
        "failure_observations": failure_observations,
        "cost_metadata": {
            "used_section_count": len(used_sections),
            "blocked_section_count": len(blocked_sections),
            "failed_section_count": len(failed_sections),
            "token_usage_available": False,
            "token_usage_reason": "OpenAI token usage is not persisted by the current guarded analyst client.",
        },
        "sections": sections,
        "principle": "LLM은 설명과 요약을 보조하고, 과실 수치·KNIA 매칭·법률 근거 존재 여부는 결정론적 로직과 RAG 근거가 우선합니다.",
    }


def _provider_enabled() -> bool:
    return os.getenv("ENABLE_OPENAI_ANALYSTS", "0") == "1" and bool(os.getenv("OPENAI_API_KEY"))


def _has_required_family(required_family: str, family_counts: dict[str, int], evidence: list[dict[str, Any]]) -> bool:
    if required_family == "any":
        return bool(evidence)
    return family_counts.get(required_family, 0) > 0


def _has_blocking_input_for_section(section: str, missing_fields: list[str]) -> bool:
    if not missing_fields:
        return False
    if section in {"traffic_law_analysis", "fault_ratio_analysis", "criminal_liability_analysis"}:
        return True
    return False


def _family_counts(evidence: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"legal": 0, "knia": 0, "general": 0}
    for item in evidence:
        family = _family(item)
        counts[family] = counts.get(family, 0) + 1
    return counts


def _family(item: dict[str, Any]) -> str:
    source_type = str(item.get("source_type") or "").lower()
    source = " ".join(
        [
            str(item.get("source") or ""),
            str(item.get("title") or ""),
            str(item.get("source_url") or ""),
            str(item.get("law_name") or ""),
        ]
    ).lower()
    if source_type.startswith("knia") or "knia" in source or "과실비율정보포털" in source:
        return "knia"
    if item.get("chunk_id") or item.get("law_name") or "law.go.kr" in source or "법" in source:
        return "legal"
    return "general"
