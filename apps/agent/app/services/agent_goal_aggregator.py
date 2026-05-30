from __future__ import annotations

from typing import Any

from app.services.agent_contracts import AgentClaim, AgentGoalResult, AgentInputRef, FinalityStatus, TaskStatus


VERSION = "agent-goal-result-v1"


def attach_agent_goal_result(output: dict[str, Any]) -> dict[str, Any]:
    """Attach a safe final goal merge result after stage task packets are available."""

    goal_result = build_agent_goal_result(output)
    output["agent_goal_result"] = goal_result
    output.setdefault("model_info", {})["agent_goal_result_version"] = VERSION
    return output


def build_agent_goal_result(output: dict[str, Any]) -> dict[str, Any]:
    conflicts = _build_conflict_packets(output)
    status = _goal_status(output, conflicts)
    finality = _goal_finality(output, conflicts, status)
    evidence_refs = _evidence_refs(output)
    uncertainties = _uncertainties(output, conflicts)
    next_inputs = _next_required_inputs(output, conflicts)
    confidence = _confidence(output, conflicts, finality)
    claims = _claims(output, conflicts, finality, evidence_refs)

    goal = AgentGoalResult(
        goal="사고 입력, 영상 관찰값, 법률/KNIA 근거, 과실비율 참고치를 하나의 판단 계약으로 병합한다.",
        status=status,
        claims=claims,
        evidence_refs=evidence_refs,
        confidence=confidence,
        uncertainties=uncertainties,
        next_required_inputs=next_inputs,
        finality=finality,
    )
    return {
        "version": VERSION,
        "merge_policy": {
            "policy": "task_packet_goal_aggregator",
            "law_fault_axis_mismatch_blocks_final": True,
            "video_user_conflict_requires_review": True,
            "specialist_conflict_requires_review": True,
            "safe_metadata_only": True,
        },
        "goal": goal.model_dump(),
        "conflict_packets": conflicts,
        "task_status_counts": dict(_dict(output.get("agent_task_packets")).get("status_counts") or {}),
        "safe_metadata_only": True,
    }


def _build_conflict_packets(output: dict[str, Any]) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    conflicts.extend(_axis_conflicts(output))
    conflicts.extend(_video_fact_conflicts(output))
    conflicts.extend(_specialist_stage_conflicts(output))

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for conflict in conflicts:
        key = (str(conflict.get("conflict_type")), str(conflict.get("reason_code")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(conflict)
    return deduped


def _axis_conflicts(output: dict[str, Any]) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    accident_party = str(output.get("accident_party_type") or "")
    primary = _dict(output.get("knia_primary_match"))
    primary_party = str(primary.get("major_party_type") or primary.get("accident_party_type") or "")
    if accident_party and primary_party and accident_party != primary_party:
        conflicts.append(
            _conflict(
                conflict_type="law_fault_axis_mismatch",
                severity="block",
                status="blocked_for_consistency",
                reason_code="knia_party_type_mismatch",
                source_refs=["accident_party_type", "knia_primary_match.major_party_type"],
                details={
                    "accident_party_type": accident_party,
                    "knia_party_type": primary_party,
                },
            )
        )

    evidence_mismatches = _dict(output.get("model_info")).get("evidence_mismatch") or []
    if evidence_mismatches or _dict(output.get("fault_ratio")).get("rejected_knia_fault_estimate"):
        conflicts.append(
            _conflict(
                conflict_type="law_fault_axis_mismatch",
                severity="block",
                status="blocked_for_consistency",
                reason_code="knia_basis_mismatch",
                source_refs=["model_info.evidence_mismatch", "fault_ratio.rejected_knia_fault_estimate"],
                details={"mismatch_count": len(evidence_mismatches)},
            )
        )
    return conflicts


def _video_fact_conflicts(output: dict[str, Any]) -> list[dict[str, Any]]:
    arbitration = _dict(output.get("fact_arbitration"))
    if not arbitration:
        return []
    conflict_count = len(arbitration.get("conflicts") or [])
    held_count = len(arbitration.get("held_video_fields") or [])
    pending_count = len(arbitration.get("pending_video_confirmations") or [])
    if conflict_count + held_count + pending_count == 0:
        return []
    return [
        _conflict(
            conflict_type="video_user_fact_conflict",
            severity="review",
            status="needs_review",
            reason_code="video_fact_not_directly_applied",
            source_refs=["fact_arbitration", "video_input_contract"],
            details={
                "conflict_count": conflict_count,
                "held_video_field_count": held_count,
                "pending_confirmation_count": pending_count,
            },
        )
    ]


def _specialist_stage_conflicts(output: dict[str, Any]) -> list[dict[str, Any]]:
    task_packets = _dict(output.get("agent_task_packets")).get("packets") or []
    by_id = {packet.get("task_id"): packet for packet in task_packets if isinstance(packet, dict)}
    fault = _dict(by_id.get("fault_ratio"))
    evidence = _dict(by_id.get("evidence_retrieval"))
    knia = _dict(by_id.get("knia_matching"))
    conflicts: list[dict[str, Any]] = []

    if fault.get("status") == "succeeded" and evidence.get("status") in {"blocked", "failed", "needs_review"}:
        conflicts.append(
            _conflict(
                conflict_type="specialist_stage_conflict",
                severity="review",
                status="needs_review",
                reason_code="fault_ratio_without_ready_evidence",
                source_refs=["agent_task_packets.fault_ratio", "agent_task_packets.evidence_retrieval"],
                details={
                    "fault_ratio_status": fault.get("status"),
                    "evidence_retrieval_status": evidence.get("status"),
                },
            )
        )
    if _dict(fault.get("packet")).get("has_fault_numbers") and knia.get("status") in {"blocked", "failed"}:
        conflicts.append(
            _conflict(
                conflict_type="specialist_stage_conflict",
                severity="block",
                status="blocked_for_consistency",
                reason_code="fault_ratio_without_knia_basis",
                source_refs=["agent_task_packets.fault_ratio", "agent_task_packets.knia_matching"],
                details={
                    "fault_ratio_status": fault.get("status"),
                    "knia_matching_status": knia.get("status"),
                },
            )
        )
    return conflicts


def _goal_status(output: dict[str, Any], conflicts: list[dict[str, Any]]) -> TaskStatus:
    if _has_blocking_conflict(conflicts):
        return "blocked"
    judgment_status = str(_dict(output.get("agent_judgment")).get("overall_status") or "")
    if judgment_status == "unsupported":
        return "blocked"
    if judgment_status == "evidence_supported" and not conflicts:
        return "succeeded"
    return "needs_review"


def _goal_finality(output: dict[str, Any], conflicts: list[dict[str, Any]], status: TaskStatus) -> FinalityStatus:
    if status == "blocked" or _has_blocking_conflict(conflicts):
        return "blocked"
    if conflicts:
        return "reference_only"
    judgment = _dict(output.get("agent_judgment"))
    if judgment.get("overall_status") == "evidence_supported" and judgment.get("must_not_present_as_final") is False:
        return "decision_ready"
    return "reference_only"


def _evidence_refs(output: dict[str, Any]) -> list[AgentInputRef]:
    refs: list[AgentInputRef] = []
    for index, item in enumerate(output.get("combined_evidence") or output.get("evidence") or []):
        if not isinstance(item, dict):
            continue
        ref_id = str(item.get("chunk_id") or item.get("id") or item.get("chart_no") or f"evidence-{index}")
        refs.append(AgentInputRef(ref_type="evidence", ref_id=ref_id, field_path=f"combined_evidence[{index}]", visibility="internal"))
        if len(refs) >= 5:
            break
    return refs


def _claims(
    output: dict[str, Any],
    conflicts: list[dict[str, Any]],
    finality: FinalityStatus,
    evidence_refs: list[AgentInputRef],
) -> list[AgentClaim]:
    support_level = "direct" if finality == "decision_ready" else "partial"
    if _has_blocking_conflict(conflicts):
        support_level = "unsupported"
    claims = [
        AgentClaim(
            claim_type="goal_merge_status",
            text="Agent stage 결과를 최종 goal 판단 계약으로 병합했습니다.",
            evidence_refs=evidence_refs if support_level != "unsupported" else [],
            support_level=support_level,
        )
    ]
    if conflicts:
        claims.append(
            AgentClaim(
                claim_type="goal_conflict_gate",
                text="일부 stage 결과가 서로 맞지 않아 확정 판단 대신 보류 상태로 유지했습니다.",
                support_level="unsupported" if _has_blocking_conflict(conflicts) else "partial",
            )
        )
    fault = _dict(output.get("fault_ratio"))
    if isinstance(fault.get("my"), int) and isinstance(fault.get("other"), int):
        claims.append(
            AgentClaim(
                claim_type="fault_ratio_merge",
                text="과실비율 참고치는 법률/KNIA/입력 fact 병합 상태에 따라 확정 또는 참고로 제한됩니다.",
                evidence_refs=evidence_refs,
                support_level=support_level,
            )
        )
    return claims


def _uncertainties(output: dict[str, Any], conflicts: list[dict[str, Any]]) -> list[str]:
    uncertainties = [str(conflict.get("reason_code")) for conflict in conflicts if conflict.get("reason_code")]
    judgment = _dict(output.get("agent_judgment"))
    uncertainties.extend(str(item) for item in judgment.get("blocking_reasons") or [])
    return list(dict.fromkeys(uncertainties))


def _next_required_inputs(output: dict[str, Any], conflicts: list[dict[str, Any]]) -> list[str]:
    requirements = _dict(output.get("input_requirements"))
    fields = [str(item) for item in requirements.get("blocking_fields") or []]
    for conflict in conflicts:
        if conflict.get("conflict_type") == "video_user_fact_conflict":
            fields.append("video_user_fact_confirmation")
        elif conflict.get("conflict_type") == "law_fault_axis_mismatch":
            fields.append("accident_axis_confirmation")
    return list(dict.fromkeys(fields))


def _confidence(output: dict[str, Any], conflicts: list[dict[str, Any]], finality: FinalityStatus) -> float:
    if finality == "blocked":
        return 0.0
    base = 0.8 if finality == "decision_ready" else 0.55
    status_counts = _dict(_dict(output.get("agent_task_packets")).get("status_counts"))
    review_count = int(status_counts.get("needs_review") or 0)
    blocked_count = int(status_counts.get("blocked") or 0) + int(status_counts.get("failed") or 0)
    penalty = min(0.45, review_count * 0.05 + blocked_count * 0.2 + len(conflicts) * 0.08)
    return round(max(0.0, min(1.0, base - penalty)), 2)


def _conflict(
    *,
    conflict_type: str,
    severity: str,
    status: str,
    reason_code: str,
    source_refs: list[str],
    details: dict[str, Any],
) -> dict[str, Any]:
    return {
        "conflict_type": conflict_type,
        "severity": severity,
        "status": status,
        "reason_code": reason_code,
        "source_refs": source_refs,
        "details": details,
        "safe_metadata_only": True,
    }


def _has_blocking_conflict(conflicts: list[dict[str, Any]]) -> bool:
    return any(conflict.get("severity") == "block" for conflict in conflicts)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
