from __future__ import annotations

from typing import Any


VERSION = "specialist-consensus-v1"

PRIORITY_ORDER = (
    ("confirmed_video_fact", "확정 영상 fact"),
    ("explicit_user_fact", "사용자 명시 입력"),
    ("direct_evidence", "KNIA/법령/판례 직접 근거"),
    ("llm_summary", "LLM 요약"),
    ("fallback", "fallback"),
)

CONFLICT_TAXONOMY = {
    "accident_target_conflict",
    "accident_type_conflict",
    "signal_status_conflict",
    "knia_standard_conflict",
    "fault_direction_conflict",
    "civil_criminal_conflict",
}


def attach_specialist_consensus(output: dict[str, Any]) -> dict[str, Any]:
    output["specialist_consensus"] = build_specialist_consensus(output)
    return output


def build_specialist_consensus(output: dict[str, Any]) -> dict[str, Any]:
    conflicts = _dedupe_conflicts(
        [
            *_goal_result_conflicts(output),
            *_fact_arbitration_conflicts(output),
            *_conditional_outcome_conflicts(output),
            *_specialist_uncertainty_conflicts(output),
        ]
    )
    next_inputs = _next_required_inputs(conflicts)
    unresolved = [item for item in conflicts if item.get("resolution_status") != "resolved_by_priority"]
    conditional_count = len([item for item in conflicts if item.get("resolution_status") == "conditional_result_required"])
    consensus_status = _consensus_status(conflicts, unresolved, conditional_count)

    return {
        "version": VERSION,
        "status": consensus_status,
        "priority_order": [
            {"rank": index + 1, "source_type": source_type, "label": label}
            for index, (source_type, label) in enumerate(PRIORITY_ORDER)
        ],
        "conflict_taxonomy": sorted(CONFLICT_TAXONOMY),
        "conflict_count": len(conflicts),
        "blocking_conflict_count": len([item for item in conflicts if item.get("severity") == "block"]),
        "conditional_conflict_count": conditional_count,
        "unresolved_conflict_count": len(unresolved),
        "conflicts": conflicts,
        "resolution": {
            "answer_policy": _answer_policy(consensus_status),
            "must_not_use_flat_50_50_fallback": bool(conflicts),
            "next_required_inputs": next_inputs,
            "safe_user_message_code": _safe_user_message_code(consensus_status),
        },
        "safe_metadata_only": True,
    }


def _goal_result_conflicts(output: dict[str, Any]) -> list[dict[str, Any]]:
    conflicts = []
    for item in _dict(output.get("agent_goal_result")).get("conflict_packets") or []:
        if not isinstance(item, dict):
            continue
        conflict_type = _map_goal_conflict_type(item)
        conflicts.append(
            _conflict(
                conflict_type=conflict_type,
                severity=str(item.get("severity") or "review"),
                reason_code=str(item.get("reason_code") or "agent_goal_conflict"),
                source_refs=[str(ref) for ref in item.get("source_refs") or []],
                resolution_status="blocked_until_reconciled" if item.get("severity") == "block" else "needs_question",
                priority_source="direct_evidence" if conflict_type == "knia_standard_conflict" else "explicit_user_fact",
                details={
                    "origin": "agent_goal_result",
                    "goal_conflict_type": item.get("conflict_type"),
                    "goal_status": item.get("status"),
                },
            )
        )
    return conflicts


def _fact_arbitration_conflicts(output: dict[str, Any]) -> list[dict[str, Any]]:
    arbitration = _dict(output.get("fact_arbitration"))
    conflicts: list[dict[str, Any]] = []
    for item in arbitration.get("conflicts") or []:
        if not isinstance(item, dict):
            continue
        field = str(item.get("field") or item.get("field_path") or item.get("name") or "")
        conflicts.append(
            _conflict(
                conflict_type=_map_field_conflict_type(field),
                severity="review",
                reason_code=f"fact_conflict:{field or 'unknown'}",
                source_refs=["fact_arbitration", "video_input_contract", "structured_facts"],
                resolution_status="needs_question",
                priority_source="confirmed_video_fact",
                details={
                    "origin": "fact_arbitration",
                    "field": field or "unknown",
                },
            )
        )
    return conflicts


def _conditional_outcome_conflicts(output: dict[str, Any]) -> list[dict[str, Any]]:
    fault_ratio = _dict(output.get("fault_ratio"))
    outcomes = [item for item in fault_ratio.get("conditional_outcomes") or [] if isinstance(item, dict)]
    if not outcomes:
        return []
    source_refs = ["fault_ratio.conditional_outcomes"]
    if _has_signal_uncertainty(output):
        source_refs.extend(["structured_facts.signal_state", "structured_facts.opponent_signal_visible"])
    return [
        _conflict(
            conflict_type="signal_status_conflict" if _has_signal_uncertainty(output) else "fault_direction_conflict",
            severity="review",
            reason_code="conditional_fault_outcomes_require_branching",
            source_refs=source_refs,
            resolution_status="conditional_result_required",
            priority_source="direct_evidence",
            details={
                "origin": "fault_ratio",
                "conditional_outcome_count": len(outcomes),
                "branches": [_safe_branch_summary(item) for item in outcomes[:4]],
            },
        )
    ]


def _specialist_uncertainty_conflicts(output: dict[str, Any]) -> list[dict[str, Any]]:
    results = _dict(output.get("specialist_agent_results")).get("results") or []
    conflicts: list[dict[str, Any]] = []
    for result in results:
        if not isinstance(result, dict):
            continue
        role_id = str(result.get("role_id") or "")
        uncertainties = [str(item) for item in result.get("uncertainties") or [] if item]
        unsupported = [str(item) for item in result.get("unsupported_claims") or [] if item]
        if not uncertainties and not unsupported:
            continue
        conflict_type = _map_role_conflict_type(role_id)
        conflicts.append(
            _conflict(
                conflict_type=conflict_type,
                severity="review",
                reason_code=f"specialist_needs_review:{role_id or 'unknown'}",
                source_refs=[f"specialist_agent_results.{role_id or 'unknown'}"],
                resolution_status="needs_question",
                priority_source="llm_summary" if role_id in _llm_like_roles() else "explicit_user_fact",
                details={
                    "origin": "specialist_agent_results",
                    "role_id": role_id or "unknown",
                    "uncertainty_count": len(uncertainties),
                    "unsupported_claim_count": len(unsupported),
                },
            )
        )
    return conflicts


def _map_goal_conflict_type(item: dict[str, Any]) -> str:
    goal_type = str(item.get("conflict_type") or "")
    reason = str(item.get("reason_code") or "")
    if "knia" in reason or goal_type == "law_fault_axis_mismatch":
        return "knia_standard_conflict"
    if "fault_ratio" in reason:
        return "fault_direction_conflict"
    if "video" in reason or "fact" in reason:
        return "accident_target_conflict"
    return "accident_type_conflict"


def _map_field_conflict_type(field: str) -> str:
    lowered = field.lower()
    if any(token in lowered for token in ("signal", "traffic_light", "light_state")):
        return "signal_status_conflict"
    if any(token in lowered for token in ("party", "target", "partner", "pedestrian", "bicycle", "motorcycle", "vehicle")):
        return "accident_target_conflict"
    if any(token in lowered for token in ("scenario", "accident_type", "collision_type")):
        return "accident_type_conflict"
    if "fault" in lowered:
        return "fault_direction_conflict"
    return "accident_type_conflict"


def _map_role_conflict_type(role_id: str) -> str:
    if role_id in {"video_observation_agent", "fact_arbitration_agent"}:
        return "accident_target_conflict"
    if role_id in {"knia_fault_standard_agent", "traffic_law_agent"}:
        return "knia_standard_conflict"
    if role_id == "fault_ratio_agent":
        return "fault_direction_conflict"
    if role_id == "criminal_liability_agent":
        return "civil_criminal_conflict"
    return "accident_type_conflict"


def _llm_like_roles() -> set[str]:
    return {
        "traffic_law_agent",
        "fault_ratio_agent",
        "criminal_liability_agent",
        "insurance_claim_agent",
        "action_guidance_agent",
    }


def _has_signal_uncertainty(output: dict[str, Any]) -> bool:
    facts = _dict(output.get("structured_facts"))
    text = " ".join(
        str(value)
        for value in (
            facts.get("signal_state"),
            facts.get("opponent_signal_visible"),
            facts.get("opponent_signal_state"),
            facts.get("signal_transition"),
            output.get("scenario_type"),
        )
    ).lower()
    return any(token in text for token in ("signal", "yellow", "red", "green", "신호", "황색", "적색", "녹색", "unknown", "false"))


def _safe_branch_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": item.get("label") or item.get("scenario") or item.get("condition") or "conditional_branch",
        "my": item.get("my"),
        "other": item.get("other"),
        "confidence": item.get("confidence"),
    }


def _next_required_inputs(conflicts: list[dict[str, Any]]) -> list[str]:
    mapping = {
        "accident_target_conflict": "direct_collision_target_confirmation",
        "accident_type_conflict": "accident_type_confirmation",
        "signal_status_conflict": "signal_status_confirmation",
        "knia_standard_conflict": "accident_axis_or_knia_basis_confirmation",
        "fault_direction_conflict": "fault_direction_basis_confirmation",
        "civil_criminal_conflict": "injury_or_criminal_issue_confirmation",
    }
    fields = [mapping.get(str(item.get("conflict_type")), "additional_fact_confirmation") for item in conflicts]
    return list(dict.fromkeys(fields))


def _consensus_status(conflicts: list[dict[str, Any]], unresolved: list[dict[str, Any]], conditional_count: int) -> str:
    if not conflicts:
        return "ready"
    if any(item.get("severity") == "block" for item in conflicts):
        return "blocked_for_consistency"
    if conditional_count:
        return "needs_conditionals"
    if unresolved:
        return "needs_question"
    return "resolved_by_priority"


def _answer_policy(status: str) -> str:
    if status == "ready":
        return "single_reference_result_allowed"
    if status == "needs_conditionals":
        return "present_conditional_results_before_fault_ratio"
    if status == "resolved_by_priority":
        return "present_priority_resolution_with_caveat"
    return "ask_targeted_question_or_reference_only"


def _safe_user_message_code(status: str) -> str:
    return {
        "ready": "consensus_ready",
        "needs_conditionals": "conditional_outcomes_required",
        "needs_question": "targeted_confirmation_required",
        "blocked_for_consistency": "consistency_blocked",
        "resolved_by_priority": "priority_resolution_applied",
    }.get(status, "targeted_confirmation_required")


def _conflict(
    *,
    conflict_type: str,
    severity: str,
    reason_code: str,
    source_refs: list[str],
    resolution_status: str,
    priority_source: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    if conflict_type not in CONFLICT_TAXONOMY:
        conflict_type = "accident_type_conflict"
    return {
        "conflict_type": conflict_type,
        "severity": severity,
        "reason_code": reason_code,
        "source_refs": source_refs,
        "resolution_status": resolution_status,
        "priority_source": priority_source,
        "details": details,
        "safe_metadata_only": True,
    }


def _dedupe_conflicts(conflicts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in conflicts:
        key = (
            str(item.get("conflict_type")),
            str(item.get("reason_code")),
            ",".join(str(ref) for ref in item.get("source_refs") or []),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
