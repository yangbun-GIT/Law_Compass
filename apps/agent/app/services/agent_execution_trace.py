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
    reflection_loop = output.get("reflection_loop") or {}
    video_contract = output.get("video_input_contract") or {}
    claim_evidence = output.get("claim_evidence") or {}
    agent_plan = output.get("agent_plan") or {}
    task_packets = output.get("agent_task_packets") or {}
    goal_result = output.get("agent_goal_result") or {}
    replan = output.get("agent_replan") or {}
    specialist_results = output.get("specialist_agent_results") or {}
    prompt_registry = output.get("specialist_prompt_registry") or {}
    specialist_consensus = output.get("specialist_consensus") or {}

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
            "specialist_agent_results",
            "solve",
            "completed" if specialist_results.get("result_count") else "skipped",
            {
                "result_count": specialist_results.get("result_count", 0),
                "role_ids": list(specialist_results.get("role_ids") or []),
                "safe_metadata_only": specialist_results.get("safe_metadata_only") is True,
            },
        ),
        _step(
            "specialist_prompt_registry",
            "guard",
            "completed" if prompt_registry.get("coverage_complete") else "needs_review",
            {
                "guardrail_version": prompt_registry.get("guardrail_version"),
                "role_count": prompt_registry.get("role_count", 0),
                "coverage_complete": prompt_registry.get("coverage_complete"),
                "safe_metadata_only": prompt_registry.get("safe_metadata_only") is True,
            },
        ),
        _step(
            "specialist_consensus",
            "verify",
            "completed" if specialist_consensus.get("status") in {"ready", "resolved_by_priority"} else "needs_review",
            {
                "version": specialist_consensus.get("version"),
                "status": specialist_consensus.get("status"),
                "conflict_count": specialist_consensus.get("conflict_count", 0),
                "blocking_conflict_count": specialist_consensus.get("blocking_conflict_count", 0),
                "conditional_conflict_count": specialist_consensus.get("conditional_conflict_count", 0),
                "answer_policy": (specialist_consensus.get("resolution") or {}).get("answer_policy"),
                "safe_metadata_only": specialist_consensus.get("safe_metadata_only") is True,
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
            "reflection_loop",
            "recover",
            reflection_loop.get("status") or "unknown",
            {
                "requery_attempted": bool(reflection_loop.get("requery_attempted")),
                "requery_added_evidence_count": reflection_loop.get("requery_added_evidence_count", 0),
                "iterations_used": reflection_loop.get("iterations_used", 0),
                "next_action": reflection_loop.get("next_action"),
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
        "task_plan": _task_plan_summary(agent_plan),
        "task_packets": _task_packet_summary(task_packets),
        "goal_result": _goal_result_summary(goal_result),
        "replan": _replan_summary(replan),
        "specialist_agent_results": _specialist_results_summary(specialist_results),
        "specialist_prompt_registry": _prompt_registry_summary(prompt_registry),
        "specialist_consensus": _specialist_consensus_summary(specialist_consensus),
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


def _task_plan_summary(agent_plan: dict[str, Any]) -> dict[str, Any]:
    tasks = agent_plan.get("tasks") if isinstance(agent_plan.get("tasks"), list) else []
    return {
        "version": agent_plan.get("version"),
        "plan_id": agent_plan.get("plan_id"),
        "input_mode": agent_plan.get("input_mode"),
        "plan_status": agent_plan.get("plan_status"),
        "created_by": agent_plan.get("created_by"),
        "task_count": len(tasks),
        "execution_order": list(agent_plan.get("execution_order") or []),
        "blocked_task_count": len([task for task in tasks if isinstance(task, dict) and task.get("status") == "blocked"]),
        "safe_metadata_only": True,
    }


def _task_packet_summary(task_packets: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": task_packets.get("version"),
        "task_count": task_packets.get("task_count", 0),
        "status_counts": dict(task_packets.get("status_counts") or {}),
        "safe_metadata_only": True,
    }


def _goal_result_summary(goal_result: dict[str, Any]) -> dict[str, Any]:
    goal = goal_result.get("goal") if isinstance(goal_result.get("goal"), dict) else {}
    conflicts = goal_result.get("conflict_packets") if isinstance(goal_result.get("conflict_packets"), list) else []
    return {
        "version": goal_result.get("version"),
        "status": goal.get("status"),
        "finality": goal.get("finality"),
        "confidence": goal.get("confidence"),
        "conflict_count": len(conflicts),
        "blocking_conflict_count": len([item for item in conflicts if isinstance(item, dict) and item.get("severity") == "block"]),
        "safe_metadata_only": True,
    }


def _replan_summary(replan: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": replan.get("version"),
        "status": replan.get("status"),
        "replan_allowed": bool(replan.get("replan_allowed")),
        "reason_count": len(replan.get("replan_reasons") or []),
        "proposed_task_count": len(replan.get("proposed_tasks") or []),
        "max_iterations": replan.get("max_iterations"),
        "iterations_used": replan.get("iterations_used"),
        "safe_metadata_only": True,
    }


def _specialist_results_summary(specialist_results: dict[str, Any]) -> dict[str, Any]:
    results = specialist_results.get("results") if isinstance(specialist_results.get("results"), list) else []
    finalities = [item.get("finality") for item in results if isinstance(item, dict)]
    return {
        "version": specialist_results.get("version"),
        "result_count": specialist_results.get("result_count", 0),
        "role_ids": list(specialist_results.get("role_ids") or []),
        "needs_review_count": len([value for value in finalities if value == "needs_review"]),
        "decision_ready_count": len([value for value in finalities if value == "decision_ready"]),
        "safe_metadata_only": specialist_results.get("safe_metadata_only") is True,
    }


def _prompt_registry_summary(prompt_registry: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": prompt_registry.get("version"),
        "guardrail_version": prompt_registry.get("guardrail_version"),
        "role_count": prompt_registry.get("role_count", 0),
        "coverage_complete": prompt_registry.get("coverage_complete") is True,
        "safe_metadata_only": prompt_registry.get("safe_metadata_only") is True,
    }


def _specialist_consensus_summary(specialist_consensus: dict[str, Any]) -> dict[str, Any]:
    resolution = specialist_consensus.get("resolution") if isinstance(specialist_consensus.get("resolution"), dict) else {}
    return {
        "version": specialist_consensus.get("version"),
        "status": specialist_consensus.get("status"),
        "conflict_count": specialist_consensus.get("conflict_count", 0),
        "blocking_conflict_count": specialist_consensus.get("blocking_conflict_count", 0),
        "conditional_conflict_count": specialist_consensus.get("conditional_conflict_count", 0),
        "unresolved_conflict_count": specialist_consensus.get("unresolved_conflict_count", 0),
        "answer_policy": resolution.get("answer_policy"),
        "safe_metadata_only": specialist_consensus.get("safe_metadata_only") is True,
    }
