from __future__ import annotations

from typing import Any


VERSION = "specialist-role-inventory-v1"

ROLE_GROUPS: dict[str, dict[str, Any]] = {
    "judgment_responsibility_agents": {
        "purpose": "Produce bounded legal, KNIA, fault-ratio, criminal, or insurance guidance claims.",
        "role_ids": [
            "traffic_law_agent",
            "knia_fault_standard_agent",
            "fault_ratio_agent",
            "criminal_liability_agent",
            "insurance_claim_agent",
        ],
        "must_not_do": [
            "invent_law_or_precedent",
            "treat_reference_ratio_as_final_verdict",
            "override_evidence_or_judgment_contract",
        ],
    },
    "observation_validation_agents": {
        "purpose": "Validate video, user input, evidence, and claim support before judgment claims are used.",
        "role_ids": [
            "video_observation_agent",
            "evidence_audit_agent",
        ],
        "must_not_do": [
            "decide_fault_ratio",
            "decide_criminal_liability",
            "promote_candidate_video_fact_without_guard",
        ],
    },
    "presentation_guidance_agents": {
        "purpose": "Convert verified packets into user-safe guidance without adding new facts.",
        "role_ids": [
            "action_guidance_agent",
            "presentation_policy_agent",
        ],
        "must_not_do": [
            "hide_uncertainty",
            "expose_internal_trace_or_raw_diagnostics",
            "add_unverified_legal_claim",
        ],
    },
}

CURRENT_AGENT_INVENTORY: list[dict[str, Any]] = [
    {
        "artifact": "apps/agent/app/services/analysts/traffic_law_analyst.py",
        "current_kind": "deterministic_or_llm_guarded_analyzer",
        "target_role_id": "traffic_law_agent",
        "current_output": "traffic_law_analysis",
        "role_group": "judgment_responsibility_agents",
    },
    {
        "artifact": "apps/agent/app/services/orchestration_evidence.py",
        "current_kind": "evidence_stage_service",
        "target_role_id": "knia_fault_standard_agent",
        "current_output": "knia_result, knia_fault_estimate, combined_evidence",
        "role_group": "judgment_responsibility_agents",
    },
    {
        "artifact": "apps/agent/app/services/analysts/fault_ratio_analyst.py",
        "current_kind": "deterministic_or_llm_guarded_analyzer",
        "target_role_id": "fault_ratio_agent",
        "current_output": "fault_ratio",
        "role_group": "judgment_responsibility_agents",
    },
    {
        "artifact": "apps/agent/app/services/analysts/criminal_liability_analyst.py",
        "current_kind": "deterministic_or_llm_guarded_analyzer",
        "target_role_id": "criminal_liability_agent",
        "current_output": "legal_liability",
        "role_group": "judgment_responsibility_agents",
    },
    {
        "artifact": "apps/agent/app/services/analysts/insurance_analyst.py",
        "current_kind": "deterministic_or_llm_guarded_analyzer",
        "target_role_id": "insurance_claim_agent",
        "current_output": "insurance_guide",
        "role_group": "judgment_responsibility_agents",
    },
    {
        "artifact": "apps/agent/app/services/video_input_contract.py",
        "current_kind": "video_fact_contract_service",
        "target_role_id": "video_observation_agent",
        "current_output": "video_input_contract, fact_patch, pending_video_confirmations",
        "role_group": "observation_validation_agents",
    },
    {
        "artifact": "apps/agent/app/services/analysts/evidence_auditor.py",
        "current_kind": "deterministic_evidence_auditor",
        "target_role_id": "evidence_audit_agent",
        "current_output": "evidence_audit",
        "role_group": "observation_validation_agents",
    },
    {
        "artifact": "apps/agent/app/services/analysts/action_plan_analyst.py",
        "current_kind": "deterministic_or_llm_guarded_guidance",
        "target_role_id": "action_guidance_agent",
        "current_output": "action_plan",
        "role_group": "presentation_guidance_agents",
    },
    {
        "artifact": "apps/agent/app/services/report_composer.py",
        "current_kind": "presentation_composer",
        "target_role_id": "presentation_policy_agent",
        "current_output": "final_report, model_info, user_safe_payload",
        "role_group": "presentation_guidance_agents",
    },
]

ROLE_BOUNDARY_RULES: list[dict[str, str]] = [
    {
        "rule_id": "no_agent_final_verdict",
        "description": "Every specialist produces guidance claims, not a final legal verdict.",
    },
    {
        "rule_id": "evidence_first",
        "description": "Legal, KNIA, and fault claims must carry direct or partial evidence refs before decision-ready output.",
    },
    {
        "rule_id": "video_candidate_guard",
        "description": "Video candidates remain candidates until fact arbitration or user confirmation promotes them.",
    },
    {
        "rule_id": "role_handoff_required",
        "description": "A role must hand off claims outside its authority instead of deciding them.",
    },
    {
        "rule_id": "presentation_cannot_add_facts",
        "description": "Presentation agents can simplify or order guidance but cannot add new accident facts.",
    },
]


def build_specialist_role_inventory() -> dict[str, Any]:
    missing_groups = sorted(
        {
            item["role_group"]
            for item in CURRENT_AGENT_INVENTORY
            if item["role_group"] not in ROLE_GROUPS
        }
    )
    duplicate_targets = _duplicates([item["target_role_id"] for item in CURRENT_AGENT_INVENTORY])
    return {
        "version": VERSION,
        "role_groups": ROLE_GROUPS,
        "current_inventory": CURRENT_AGENT_INVENTORY,
        "boundary_rules": ROLE_BOUNDARY_RULES,
        "summary": {
            "group_count": len(ROLE_GROUPS),
            "inventory_count": len(CURRENT_AGENT_INVENTORY),
            "boundary_rule_count": len(ROLE_BOUNDARY_RULES),
            "missing_groups": missing_groups,
            "duplicate_target_roles": duplicate_targets,
            "safe_metadata_only": True,
        },
        "next_step": "implement_specialist_agent_interface",
    }


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)
