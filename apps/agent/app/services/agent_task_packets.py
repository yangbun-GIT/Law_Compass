from __future__ import annotations

from typing import Any

from app.services.agent_contracts import AgentTaskRuntimePacket, TaskStatus


VERSION = "agent-task-packets-v1"

JUDGMENT_TO_TASK_STATUS: dict[str, TaskStatus] = {
    "evidence_supported": "succeeded",
    "needs_review": "needs_review",
    "unsupported": "blocked",
}

TASK_STAGE_MAP = {
    "scenario_classification": "scenario_classification",
    "evidence_retrieval": "evidence_retrieval",
    "knia_matching": "knia_fault_basis",
    "fault_ratio": "fault_ratio_analysis",
    "criminal_liability": "criminal_liability_analysis",
    "insurance_guidance": "insurance_guidance",
    "action_guidance": "action_plan",
}


def attach_agent_task_packets(output: dict[str, Any]) -> dict[str, Any]:
    """Attach safe stage-level task packets and reflect their statuses into agent_plan."""

    packets = build_agent_task_packets(output)
    packet_dicts = [packet.model_dump() for packet in packets]
    output["agent_task_packets"] = {
        "version": VERSION,
        "task_count": len(packet_dicts),
        "status_counts": _status_counts(packet_dicts),
        "packets": packet_dicts,
    }
    _apply_packets_to_plan(output, packet_dicts)
    output.setdefault("model_info", {})["agent_task_packets_version"] = VERSION
    return output


def build_agent_task_packets(output: dict[str, Any]) -> list[AgentTaskRuntimePacket]:
    plan = _dict(output.get("agent_plan"))
    tasks = [task for task in plan.get("tasks") or [] if isinstance(task, dict)]
    return [_packet_for_task(task, output) for task in tasks]


def _packet_for_task(task: dict[str, Any], output: dict[str, Any]) -> AgentTaskRuntimePacket:
    task_id = str(task.get("task_id") or "")
    task_type = str(task.get("task_type") or task_id)
    builder = {
        "input_normalization": _input_normalization_packet,
        "video_observation": _video_observation_packet,
        "fact_arbitration": _fact_arbitration_packet,
        "scenario_classification": _scenario_packet,
        "evidence_retrieval": _evidence_packet,
        "knia_matching": _knia_packet,
        "fault_ratio": _fault_ratio_packet,
        "criminal_liability": _section_packet,
        "insurance_guidance": _section_packet,
        "action_guidance": _action_packet,
        "presentation_policy": _presentation_packet,
    }.get(task_id, _default_packet)
    base = builder(task_id, output)
    return AgentTaskRuntimePacket(
        task_id=task_id,
        task_type=task_type,  # type: ignore[arg-type]
        input_ref_count=len(task.get("input_refs") or []),
        evidence_ref_count=_safe_int(base.pop("evidence_ref_count", 0)),
        output_ref_count=_safe_int(base.pop("output_ref_count", 0)),
        **base,
    )


def _input_normalization_packet(task_id: str, output: dict[str, Any]) -> dict[str, Any]:
    facts = _dict(output.get("structured_facts"))
    visible_fact_count = len([key for key in facts if not str(key).startswith("_")])
    missing_count = len(facts.get("missing_fields") or [])
    status: TaskStatus = "succeeded" if isinstance(output.get("structured_facts"), dict) else "failed"
    return {
        "status": status,
        "result_ref": "structured_facts",
        "output_ref_count": visible_fact_count,
        "packet": {
            "visible_fact_count": visible_fact_count,
            "missing_field_count": missing_count,
            "security_flag_count": len(_dict(_dict(output.get("model_info")).get("security_flags"))),
        },
        "blocking_reasons": [] if status != "failed" else ["structured_facts_missing"],
    }


def _video_observation_packet(task_id: str, output: dict[str, Any]) -> dict[str, Any]:
    contract = _dict(output.get("video_input_contract"))
    technical = _dict(contract.get("technical_metadata"))
    accepted = contract.get("accepted_observations") or []
    quality = _dict(contract.get("observation_quality_summary"))
    frame_count = _safe_int(technical.get("representative_frame_count"))
    candidate_count = _safe_int(quality.get("candidate_count") or quality.get("observation_count"))
    if not contract:
        status: TaskStatus = "blocked"
        blocking = ["video_input_contract_missing"]
    elif accepted:
        status = "succeeded"
        blocking = []
    else:
        status = "needs_review"
        blocking = []
    return {
        "status": status,
        "result_ref": "video_input_contract",
        "output_ref_count": len(accepted),
        "packet": {
            "representative_frame_count": frame_count,
            "accepted_observation_count": len(accepted),
            "candidate_observation_count": candidate_count,
            "quality_status": quality.get("status") or quality.get("quality_status"),
        },
        "observations": _observations("video_observation", status),
        "blocking_reasons": blocking,
    }


def _fact_arbitration_packet(task_id: str, output: dict[str, Any]) -> dict[str, Any]:
    arbitration = _dict(output.get("fact_arbitration"))
    conflicts = arbitration.get("conflicts") or []
    pending = arbitration.get("pending_video_confirmations") or []
    held = arbitration.get("held_video_fields") or []
    applied = arbitration.get("applied_video_fields") or []
    if not arbitration:
        status: TaskStatus = "blocked"
        blocking = ["fact_arbitration_missing"]
    elif conflicts or pending or held:
        status = "needs_review"
        blocking = []
    else:
        status = "succeeded"
        blocking = []
    return {
        "status": status,
        "result_ref": "fact_arbitration",
        "output_ref_count": len(applied),
        "packet": {
            "source_count": len(arbitration.get("fact_sources") or {}),
            "applied_video_field_count": len(applied),
            "held_video_field_count": len(held),
            "conflict_count": len(conflicts),
            "pending_confirmation_count": len(pending),
        },
        "observations": _observations("fact_arbitration", status),
        "blocking_reasons": blocking,
    }


def _scenario_packet(task_id: str, output: dict[str, Any]) -> dict[str, Any]:
    stage = _stage(output, TASK_STAGE_MAP[task_id])
    return {
        "status": _status_from_stage(stage),
        "result_ref": "scenario_type",
        "packet": {
            "scenario_type": output.get("scenario_type"),
            "accident_party_type": output.get("accident_party_type"),
            "stage_status": stage.get("status"),
        },
        "confidence": _safe_float(_dict(_dict(output.get("model_info")).get("scenario_classifier")).get("confidence")),
        "blocking_reasons": _blocking_reasons(stage),
    }


def _evidence_packet(task_id: str, output: dict[str, Any]) -> dict[str, Any]:
    stage = _stage(output, TASK_STAGE_MAP[task_id])
    evidence_audit = _dict(output.get("evidence_audit"))
    return {
        "status": _status_from_stage(stage),
        "result_ref": "combined_evidence",
        "evidence_ref_count": len(output.get("combined_evidence") or output.get("evidence") or []),
        "packet": {
            "legal_evidence_count": len(output.get("legal_evidence") or []),
            "knia_evidence_count": len(output.get("knia_evidence") or []),
            "combined_evidence_count": len(output.get("combined_evidence") or output.get("evidence") or []),
            "evidence_quality": evidence_audit.get("evidence_quality"),
            "coverage_level": _dict(evidence_audit.get("scenario_evidence_coverage")).get("coverage_level"),
            "missing_requirement_count": len(_dict(evidence_audit.get("scenario_evidence_coverage")).get("missing_requirements") or []),
        },
        "blocking_reasons": _blocking_reasons(stage),
    }


def _knia_packet(task_id: str, output: dict[str, Any]) -> dict[str, Any]:
    stage = _stage(output, TASK_STAGE_MAP[task_id])
    matches = output.get("knia_matches") or []
    return {
        "status": _status_from_stage(stage, default="succeeded" if matches else "needs_review"),
        "result_ref": "knia_matches",
        "evidence_ref_count": len(output.get("knia_evidence") or []),
        "packet": {
            "knia_match_count": len(matches),
            "has_primary_match": bool(output.get("knia_primary_match")),
            "has_fault_estimate": bool(output.get("knia_final_fault") or output.get("knia_base_fault")),
            "stage_status": stage.get("status"),
        },
        "blocking_reasons": _blocking_reasons(stage),
    }


def _fault_ratio_packet(task_id: str, output: dict[str, Any]) -> dict[str, Any]:
    stage = _stage(output, TASK_STAGE_MAP[task_id])
    fault = _dict(output.get("fault_ratio"))
    has_numbers = isinstance(fault.get("my"), int) and isinstance(fault.get("other"), int)
    status = _status_from_stage(stage, default="succeeded" if has_numbers else "needs_review")
    return {
        "status": status,
        "result_ref": "fault_ratio",
        "packet": {
            "has_fault_numbers": has_numbers,
            "fault_estimate_source": fault.get("fault_estimate_source"),
            "conditional_outcome_count": len(fault.get("conditional_outcomes") or []),
            "key_factor_count": len(fault.get("key_factors") or []),
            "stage_status": stage.get("status"),
        },
        "blocking_reasons": _blocking_reasons(stage),
    }


def _section_packet(task_id: str, output: dict[str, Any]) -> dict[str, Any]:
    section_key = {
        "criminal_liability": "legal_liability",
        "insurance_guidance": "insurance_guide",
    }.get(task_id, task_id)
    stage = _stage(output, TASK_STAGE_MAP.get(task_id, task_id))
    section = _dict(output.get(section_key))
    return {
        "status": _status_from_stage(stage, default="succeeded" if section else "needs_review"),
        "result_ref": section_key,
        "packet": {
            "section_present": bool(section),
            "evidence_support_level": section.get("evidence_support_level"),
            "judgment_status": section.get("judgment_status"),
            "stage_status": stage.get("status"),
        },
        "blocking_reasons": _blocking_reasons(stage),
    }


def _action_packet(task_id: str, output: dict[str, Any]) -> dict[str, Any]:
    stage = _stage(output, TASK_STAGE_MAP[task_id])
    actions = output.get("action_plan") or []
    return {
        "status": _status_from_stage(stage, default="succeeded" if actions else "needs_review"),
        "result_ref": "action_plan",
        "output_ref_count": len(actions),
        "packet": {"action_count": len(actions), "stage_status": stage.get("status")},
        "blocking_reasons": _blocking_reasons(stage),
    }


def _presentation_packet(task_id: str, output: dict[str, Any]) -> dict[str, Any]:
    policy = _dict(output.get("presentation_policy") or _dict(output.get("agent_judgment")).get("presentation_policy"))
    finality = policy.get("finality")
    return {
        "status": "succeeded" if policy else "needs_review",
        "result_ref": "presentation_policy",
        "packet": {
            "policy_present": bool(policy),
            "finality": finality,
            "must_not_present_as_final": bool(_dict(output.get("agent_judgment")).get("must_not_present_as_final")),
            "disclaimer_count": len(output.get("disclaimers") or []),
        },
        "observations": _observations("presentation_policy", "needs_review" if finality in {"reference_only", "needs_review"} else "succeeded"),
        "blocking_reasons": [] if policy else ["presentation_policy_missing"],
    }


def _default_packet(task_id: str, output: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "needs_review",
        "result_ref": task_id,
        "packet": {"task_id": task_id, "status_reason": "no_specific_packet_builder"},
        "observations": [{"type": "task_packet_builder_missing", "recoverable": True}],
    }


def _apply_packets_to_plan(output: dict[str, Any], packets: list[dict[str, Any]]) -> None:
    plan = _dict(output.get("agent_plan"))
    if not plan:
        return
    packet_by_id = {packet.get("task_id"): packet for packet in packets}
    updated_tasks: list[dict[str, Any]] = []
    for task in plan.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        packet = packet_by_id.get(task.get("task_id"))
        updated = dict(task)
        if packet:
            updated["status"] = packet.get("status") or updated.get("status")
            updated["result_ref"] = packet.get("result_ref") or updated.get("result_ref")
            updated["blocking_reasons"] = packet.get("blocking_reasons") or []
        updated_tasks.append(updated)
    plan["tasks"] = updated_tasks
    plan["task_status_counts"] = _status_counts(packets)
    output["agent_plan"] = plan


def _stage(output: dict[str, Any], name: str) -> dict[str, Any]:
    for stage in _dict(output.get("agent_judgment")).get("stage_statuses") or []:
        if isinstance(stage, dict) and stage.get("name") == name:
            return stage
    return {}


def _status_from_stage(stage: dict[str, Any], *, default: TaskStatus = "needs_review") -> TaskStatus:
    return JUDGMENT_TO_TASK_STATUS.get(str(stage.get("status") or ""), default)


def _blocking_reasons(stage: dict[str, Any]) -> list[str]:
    status = _status_from_stage(stage)
    if status not in {"blocked", "failed"}:
        return []
    summary = str(stage.get("summary") or "").strip()
    return [summary[:96] or "stage_blocked"]


def _observations(section: str, status: str) -> list[dict[str, Any]]:
    if status == "needs_review":
        return [{"section": section, "type": "needs_review", "recoverable": True}]
    if status in {"blocked", "failed"}:
        return [{"section": section, "type": "blocked", "recoverable": True}]
    return []


def _status_counts(packets: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for packet in packets:
        status = str(packet.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return None
