from __future__ import annotations

from typing import Any


VERSION = "agent-replan-v1"
MAX_REPLAN_ITERATIONS = 1

ALLOWED_REASON_CODES = {
    "required_evidence_not_ready": "evidence_retrieval",
    "knia_basis_missing_or_incomplete": "knia_matching",
    "knia_basis_mismatch": "knia_matching",
    "knia_party_type_mismatch": "knia_matching",
    "video_fact_not_directly_applied": "fact_arbitration",
    "required_input_fields_missing": "input_normalization",
}


def attach_agent_replan(output: dict[str, Any]) -> dict[str, Any]:
    """Attach bounded replan metadata without changing the already produced analysis result."""

    replan = build_agent_replan(output)
    output["agent_replan"] = replan
    _reflect_replan_on_plan(output, replan)
    output.setdefault("model_info", {})["agent_replan_version"] = VERSION
    return output


def build_agent_replan(output: dict[str, Any]) -> dict[str, Any]:
    reasons = _replan_reasons(output)
    iterations_used = _iterations_used(output)
    can_replan = bool(reasons) and iterations_used < MAX_REPLAN_ITERATIONS
    proposed_tasks = _proposed_tasks(reasons) if can_replan else []
    status = _status(reasons=reasons, can_replan=can_replan, iterations_used=iterations_used)
    return {
        "version": VERSION,
        "status": status,
        "policy": "bounded_allowed_blockers_only",
        "max_iterations": MAX_REPLAN_ITERATIONS,
        "iterations_used": iterations_used,
        "replan_allowed": can_replan,
        "replan_reasons": reasons,
        "proposed_tasks": proposed_tasks,
        "next_action": _next_action(status),
        "safe_metadata_only": True,
    }


def _replan_reasons(output: dict[str, Any]) -> list[dict[str, Any]]:
    reasons: list[dict[str, Any]] = []
    judgment = _dict(output.get("agent_judgment"))
    for reason in judgment.get("blocking_reasons") or []:
        _append_reason(reasons, str(reason), source="agent_judgment")

    goal_result = _dict(output.get("agent_goal_result"))
    for conflict in goal_result.get("conflict_packets") or []:
        if not isinstance(conflict, dict):
            continue
        _append_reason(
            reasons,
            str(conflict.get("reason_code") or ""),
            source=f"agent_goal_result.{conflict.get('conflict_type') or 'conflict'}",
        )

    arbitration = _dict(output.get("fact_arbitration"))
    if arbitration.get("conflicts") or arbitration.get("held_video_fields") or arbitration.get("pending_video_confirmations"):
        _append_reason(reasons, "video_fact_not_directly_applied", source="fact_arbitration")

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in reasons:
        code = str(item.get("reason_code") or "")
        if code in seen:
            continue
        seen.add(code)
        deduped.append(item)
    return deduped


def _append_reason(reasons: list[dict[str, Any]], reason_code: str, *, source: str) -> None:
    if reason_code not in ALLOWED_REASON_CODES:
        return
    reasons.append(
        {
            "reason_code": reason_code,
            "source": source,
            "target_task_type": ALLOWED_REASON_CODES[reason_code],
            "safe_metadata_only": True,
        }
    )


def _proposed_tasks(reasons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for reason in reasons:
        task_type = str(reason.get("target_task_type") or "")
        task_id = f"replan_{task_type}"
        tasks.append(
            {
                "task_id": task_id,
                "task_type": task_type,
                "status": "pending",
                "trigger_reason": reason.get("reason_code"),
                "execution_policy": "next_iteration_only",
                "safe_metadata_only": True,
            }
        )
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for task in tasks:
        task_id = str(task.get("task_id") or "")
        if task_id in seen:
            continue
        seen.add(task_id)
        deduped.append(task)
    return deduped


def _iterations_used(output: dict[str, Any]) -> int:
    reflection = _dict(output.get("reflection_loop"))
    try:
        return max(0, int(reflection.get("iterations_used") or 0))
    except (TypeError, ValueError):
        return 0


def _status(*, reasons: list[dict[str, Any]], can_replan: bool, iterations_used: int) -> str:
    if not reasons:
        return "not_needed"
    if can_replan:
        return "proposed"
    if iterations_used >= MAX_REPLAN_ITERATIONS:
        return "exhausted_reference_only"
    return "blocked"


def _next_action(status: str) -> str:
    return {
        "not_needed": "continue_current_result",
        "proposed": "run_next_bounded_iteration",
        "exhausted_reference_only": "present_reference_only",
        "blocked": "manual_review",
    }.get(status, "manual_review")


def _reflect_replan_on_plan(output: dict[str, Any], replan: dict[str, Any]) -> None:
    plan = _dict(output.get("agent_plan"))
    if not plan:
        return
    if replan.get("replan_allowed"):
        plan["replan_policy"] = "bounded_on_blocker"
    plan["replan_summary"] = {
        "version": replan.get("version"),
        "status": replan.get("status"),
        "reason_count": len(replan.get("replan_reasons") or []),
        "proposed_task_count": len(replan.get("proposed_tasks") or []),
        "max_iterations": replan.get("max_iterations"),
        "iterations_used": replan.get("iterations_used"),
        "safe_metadata_only": True,
    }
    output["agent_plan"] = plan


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
