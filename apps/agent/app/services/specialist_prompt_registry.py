from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any, Literal

from app.services.agent_contracts import STANDARD_SPECIALIST_ROLE_IDS


VERSION = "specialist-prompt-registry-v1"
PROMPT_GUARDRAIL_VERSION = "analyst-prompt-guardrails-v1"

ExecutionKind = Literal["deterministic", "llm_guarded", "presentation_only"]

PROMPT_GUARDRAILS: tuple[str, ...] = (
    "no_final_verdict",
    "no_fabricated_law_or_precedent",
    "no_new_fact_without_input_or_evidence",
    "no_video_candidate_promotion",
    "conditional_results_must_expose_uncertainty",
    "role_handoff_required_outside_authority",
    "json_object_only_when_llm_is_used",
)


@dataclass(frozen=True)
class SpecialistPromptProfile:
    role_id: str
    execution_kind: ExecutionKind
    prompt_version: str
    prompt_source: str
    llm_section: str | None
    model_env_key: str | None
    handoff_required: tuple[str, ...]

    def to_public_dict(self, *, model_name: str | None, provider_enabled: bool) -> dict[str, Any]:
        data = asdict(self)
        data["model"] = model_name if self.execution_kind == "llm_guarded" else None
        data["provider_enabled"] = provider_enabled if self.execution_kind == "llm_guarded" else False
        data["safe_metadata_only"] = True
        return data


PROMPT_PROFILES: dict[str, SpecialistPromptProfile] = {
    "video_observation_agent": SpecialistPromptProfile("video_observation_agent", "deterministic", "video-observation-deterministic-v1", "worker_video_observation_contract", None, None, ("fact_arbitration_agent", "evidence_audit_agent")),
    "fact_arbitration_agent": SpecialistPromptProfile("fact_arbitration_agent", "deterministic", "fact-arbitration-deterministic-v1", "fact_arbitration_rules", None, None, ("traffic_law_agent", "knia_fault_standard_agent", "evidence_audit_agent")),
    "traffic_law_agent": SpecialistPromptProfile("traffic_law_agent", "llm_guarded", "traffic-law-analyst-prompt-v1", "llm_client.generate_traffic_law_analysis", "traffic_law_analysis", "OPENAI_MODEL", ("criminal_liability_agent", "fault_ratio_agent", "insurance_claim_agent")),
    "knia_fault_standard_agent": SpecialistPromptProfile("knia_fault_standard_agent", "deterministic", "knia-standard-deterministic-v1", "knia_matcher_and_adjustment_registry", None, None, ("fault_ratio_agent", "evidence_audit_agent")),
    "fault_ratio_agent": SpecialistPromptProfile("fault_ratio_agent", "llm_guarded", "fault-ratio-analyst-prompt-v1", "llm_client.generate_fault_ratio_analysis", "fault_ratio_analysis", "OPENAI_MODEL", ("traffic_law_agent", "evidence_audit_agent", "presentation_policy_agent")),
    "criminal_liability_agent": SpecialistPromptProfile("criminal_liability_agent", "llm_guarded", "criminal-liability-analyst-prompt-v1", "llm_client.generate_criminal_liability_analysis", "criminal_liability_analysis", "OPENAI_MODEL", ("traffic_law_agent", "insurance_claim_agent")),
    "insurance_claim_agent": SpecialistPromptProfile("insurance_claim_agent", "llm_guarded", "insurance-guidance-analyst-prompt-v1", "llm_client.generate_insurance_analysis", "insurance_guidance", "OPENAI_MODEL", ("traffic_law_agent", "presentation_policy_agent")),
    "evidence_audit_agent": SpecialistPromptProfile("evidence_audit_agent", "deterministic", "evidence-audit-deterministic-v1", "evidence_auditor_and_claim_evidence_validator", None, None, ("presentation_policy_agent", "fact_arbitration_agent")),
    "action_guidance_agent": SpecialistPromptProfile("action_guidance_agent", "llm_guarded", "action-guidance-analyst-prompt-v1", "llm_client.generate_action_plan", "action_plan", "OPENAI_MODEL", ("presentation_policy_agent",)),
    "presentation_policy_agent": SpecialistPromptProfile("presentation_policy_agent", "presentation_only", "final-report-presentation-policy-v1", "report_composer_and_elderly_friendly_report", "final_report", "OPENAI_MODEL", ("evidence_audit_agent",)),
}


def attach_specialist_prompt_registry(output: dict[str, Any]) -> dict[str, Any]:
    output["specialist_prompt_registry"] = build_specialist_prompt_registry()
    return output


def build_specialist_prompt_registry() -> dict[str, Any]:
    provider_enabled = _provider_enabled()
    model_name = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    roles = [
        PROMPT_PROFILES[role_id].to_public_dict(model_name=model_name, provider_enabled=provider_enabled)
        for role_id in sorted(PROMPT_PROFILES)
    ]
    return {
        "version": VERSION,
        "guardrail_version": PROMPT_GUARDRAIL_VERSION,
        "guardrails": list(PROMPT_GUARDRAILS),
        "role_count": len(roles),
        "roles": roles,
        "coverage_complete": set(PROMPT_PROFILES) == STANDARD_SPECIALIST_ROLE_IDS,
        "safe_metadata_only": True,
    }


def _provider_enabled() -> bool:
    return os.getenv("ENABLE_OPENAI_ANALYSTS", "0") == "1" and bool(os.getenv("OPENAI_API_KEY"))
