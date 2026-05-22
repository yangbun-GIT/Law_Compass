from __future__ import annotations

from typing import Any

VERSION = "agent-execution-trace-v1"


def build_agent_execution_trace(output: dict[str, Any]) -> dict[str, Any]:
    """Build a safe, packet-like Agent execution trace without raw user text."""

    facts = output.get("structured_facts") or {}
    evidence_audit = output.get("evidence_audit") or {}
    coverage = evidence_audit.get("scenario_evidence_coverage") or {}
    judgment = output.get("agent_judgment") or {}
    fact_arbitration = output.get("fact_arbitration") or {}
    input_requirements = output.get("input_requirements") or {}
    followup_loop = output.get("followup_loop") or {}
    video_contract = output.get("video_input_contract") or {}
    claim_evidence = output.get("claim_evidence") or {}

    steps = [
        _step(
            "input_normalization",
            "perceive",
            _stage_status(judgment, "input_normalization", default="completed"),
            {
                "fact_count": len([key for key in facts.keys() if not str(key).startswith("_")]),
                "missing_field_count": len(facts.get("missing_fields") or []),
                "required_input_count": len(input_requirements.get("blocking_fields") or []),
                "optional_input_count": len(input_requirements.get("optional_fields") or []),
                "has_video_contract": bool(video_contract),
            },
        ),
        _step(
            "fact_arbitration",
            "observe",
            "completed" if fact_arbitration else "skipped",
            {
                "source_count": len(fact_arbitration.get("fact_sources") or {}),
                "conflict_count": len(fact_arbitration.get("conflicts") or []),
                "video_observation_count": len(video_contract.get("accepted_observations") or []),
            },
        ),
        _step(
            "scenario_classification",
            "plan",
            _stage_status(judgment, "scenario_classification", default="completed"),
            {
                "scenario_type": output.get("scenario_type"),
                "accident_party_type": output.get("accident_party_type"),
                "accident_party_label": output.get("accident_party_label"),
            },
        ),
        _step(
            "evidence_retrieval",
            "act",
            _stage_status(judgment, "evidence_retrieval", default="completed"),
            {
                "legal_evidence_count": len(output.get("legal_evidence") or []),
                "knia_evidence_count": len(output.get("knia_evidence") or []),
                "combined_evidence_count": len(output.get("combined_evidence") or output.get("evidence") or []),
                "coverage_level": coverage.get("coverage_level"),
                "decision_ready": coverage.get("decision_ready"),
                "missing_requirement_count": len(coverage.get("missing_requirements") or []),
            },
        ),
        _step(
            "analyst_execution",
            "solve",
            _analyst_status(output),
            {
                "traffic_law": _section_status(output.get("legal_analysis")),
                "fault_ratio": _section_status(output.get("fault_ratio")),
                "criminal_liability": _section_status(output.get("legal_liability")),
                "insurance": _section_status(output.get("insurance_guide")),
            },
        ),
        _step(
            "claim_validation",
            "verify",
            "needs_review" if claim_evidence.get("unsupported_claim_count") else "completed",
            {
                "claim_count": claim_evidence.get("claim_count", 0),
                "coverage_level": claim_evidence.get("coverage_level"),
                "unsupported_claim_count": claim_evidence.get("unsupported_claim_count", 0),
                "weak_claim_count": claim_evidence.get("weak_claim_count", 0),
            },
        ),
        _step(
            "judgment_contract",
            "guard",
            judgment.get("overall_status") or "unknown",
            {
                "must_not_present_as_final": bool(judgment.get("must_not_present_as_final")),
                "blocking_reason_count": len(judgment.get("blocking_reasons") or []),
                "finality": (output.get("presentation_policy") or {}).get("finality"),
            },
        ),
        _step(
            "followup_loop",
            "recover",
            followup_loop.get("status") or "unknown",
            {
                "remaining_question_count": followup_loop.get("remaining_question_count", 0),
                "max_iterations": followup_loop.get("max_iterations"),
                "iteration": followup_loop.get("iteration"),
            },
        ),
    ]

    return {
        "version": VERSION,
        "pattern": "plan_observe_verify_trace",
        "overall_status": judgment.get("overall_status") or "unknown",
        "trace_policy": "safe_metadata_only_no_raw_user_text",
        "step_count": len(steps),
        "steps": steps,
    }


def _step(step_id: str, phase: str, status: str, packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": step_id,
        "phase": phase,
        "status": status,
        "packet": {key: value for key, value in packet.items() if value is not None},
    }


def _stage_status(judgment: dict[str, Any], name: str, *, default: str) -> str:
    for stage in judgment.get("stage_statuses") or []:
        if stage.get("name") == name:
            return stage.get("status") or default
    return default


def _section_status(section: dict[str, Any] | None) -> str:
    if not isinstance(section, dict):
        return "unknown"
    return section.get("judgment_status") or section.get("presentation_status") or section.get("evidence_support_level") or "unknown"


def _analyst_status(output: dict[str, Any]) -> str:
    statuses = [
        _section_status(output.get("legal_analysis")),
        _section_status(output.get("fault_ratio")),
        _section_status(output.get("legal_liability")),
        _section_status(output.get("insurance_guide")),
    ]
    if any(status in {"unsupported", "blocked_for_final"} for status in statuses):
        return "unsupported"
    if any(status in {"needs_review", "review_required", "partial", "insufficient"} for status in statuses):
        return "needs_review"
    return "completed"
