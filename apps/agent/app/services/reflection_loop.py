from __future__ import annotations

from typing import Any

VERSION = "agent-reflection-loop-v1"
MAX_REQUERY_ATTEMPTS = 1

REQUERYABLE_REQUIREMENTS = {
    "total_evidence",
    "scenario_relevant_evidence",
    "average_score",
    "family:legal",
    "family:knia",
}

REQUERY_TERMS: dict[str, tuple[str, ...]] = {
    "total_evidence": ("legal basis", "fault ratio basis", "traffic accident evidence"),
    "scenario_relevant_evidence": ("scenario relevant precedent", "same accident type", "fault ratio standard"),
    "average_score": ("direct legal rule", "applicable standard", "authoritative source"),
    "family:legal": ("Road Traffic Act", "traffic accident duty of care", "legal liability"),
    "family:knia": ("KNIA fault ratio standard", "fault ratio guide", "basic fault ratio"),
}


def build_requery_plan(
    *,
    evidence_audit: dict[str, Any],
    input_requirements: dict[str, Any],
    attempt: int = 0,
) -> dict[str, Any]:
    coverage = evidence_audit.get("scenario_evidence_coverage") or {}
    missing_requirements = list(coverage.get("missing_requirements") or [])
    blocking_fields = list(input_requirements.get("blocking_fields") or [])
    requery_reasons = [item for item in missing_requirements if item in REQUERYABLE_REQUIREMENTS]
    should_requery = bool(requery_reasons) and attempt < MAX_REQUERY_ATTEMPTS

    return {
        "version": VERSION,
        "attempt": attempt,
        "max_attempts": MAX_REQUERY_ATTEMPTS,
        "should_requery": should_requery,
        "requery_reasons": requery_reasons,
        "missing_requirements": missing_requirements,
        "blocking_fields": blocking_fields,
        "query_terms": _query_terms(requery_reasons),
        "next_action": "requery_evidence" if should_requery else _next_action(blocking_fields, coverage),
    }


def build_reflection_loop_result(
    *,
    initial_plan: dict[str, Any],
    final_evidence_audit: dict[str, Any],
    input_requirements: dict[str, Any],
    followup_loop: dict[str, Any],
    judgment_contract: dict[str, Any],
    requery_attempted: bool,
    requery_added_count: int,
) -> dict[str, Any]:
    coverage = final_evidence_audit.get("scenario_evidence_coverage") or {}
    blocking_fields = list(input_requirements.get("blocking_fields") or [])
    finality = judgment_contract.get("presentation_policy", {}).get("finality") or judgment_contract.get("finality")
    if judgment_contract.get("overall_status") == "evidence_supported" and coverage.get("decision_ready"):
        status = "resolved"
        next_action = "finalize"
    elif blocking_fields:
        status = "waiting_for_input"
        next_action = "request_missing_input"
    elif finality in {"reference_only", "blocked_for_final"} or judgment_contract.get("must_not_present_as_final"):
        status = "reference_only"
        next_action = "present_reference_only"
    else:
        status = "needs_review"
        next_action = "manual_review"

    return {
        "version": VERSION,
        "status": status,
        "max_iterations": MAX_REQUERY_ATTEMPTS,
        "iterations_used": 1 if requery_attempted else 0,
        "requery_attempted": requery_attempted,
        "requery_added_evidence_count": requery_added_count,
        "initial_requery_reasons": list(initial_plan.get("requery_reasons") or []),
        "final_missing_requirements": list(coverage.get("missing_requirements") or []),
        "blocking_fields": blocking_fields,
        "remaining_question_count": followup_loop.get("remaining_question_count", 0),
        "next_action": next_action,
        "finality": finality,
    }


def _query_terms(reasons: list[str]) -> list[str]:
    terms: list[str] = []
    for reason in reasons:
        terms.extend(REQUERY_TERMS.get(reason, (reason,)))
    return list(dict.fromkeys(terms))[:10]


def _next_action(blocking_fields: list[str], coverage: dict[str, Any]) -> str:
    if blocking_fields or "required_input_fields" in list(coverage.get("missing_requirements") or []):
        return "request_missing_input"
    if coverage.get("decision_ready"):
        return "finalize"
    return "present_reference_only"
