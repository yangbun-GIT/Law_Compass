from __future__ import annotations

from typing import Any


VERSION = "agent-quality-packet-v1"

REQUIRED_PACKETS = (
    "input_context",
    "evidence_audit",
    "claim_evidence",
    "judgment_contract",
    "reflection_loop",
    "presentation_policy",
    "agent_trace",
)


def build_agent_quality_packet(output: dict[str, Any]) -> dict[str, Any]:
    """Build safe metadata for evaluating an Agent run without exposing raw user input."""

    judgment = _dict(output.get("agent_judgment"))
    reflection = _dict(output.get("reflection_loop"))
    evidence_audit = _dict(output.get("evidence_audit"))
    claim_evidence = _dict(output.get("claim_evidence"))
    llm_policy = _dict(_dict(output.get("model_info")).get("llm_policy"))
    packets = _packet_presence(output)
    missing_packets = [name for name, present in packets.items() if not present]
    failed_sections = _llm_failed_sections(llm_policy)
    failure_observations = _failure_observations(output, llm_policy, missing_packets, failed_sections)

    return {
        "version": VERSION,
        "evaluation": {
            "overall_status": _overall_status(judgment, reflection, evidence_audit, missing_packets),
            "scenario_type": output.get("scenario_type"),
            "finality": judgment.get("finality"),
            "decision_ready": judgment.get("decision_ready"),
            "evidence_coverage_level": claim_evidence.get("coverage_level")
            or evidence_audit.get("claim_evidence_coverage"),
            "scenario_relevant_evidence_count": _safe_int(evidence_audit.get("scenario_relevant_evidence_count")),
            "unsupported_claim_count": _safe_int(claim_evidence.get("unsupported_count")),
            "weak_claim_count": _safe_int(claim_evidence.get("weak_count")),
            "next_action": reflection.get("next_action"),
        },
        "packet_contract": {
            "required_packets_present": not missing_packets,
            "present_packets": [name for name, present in packets.items() if present],
            "missing_packets": missing_packets,
            "optional_packets": {
                "video_input_contract": bool(output.get("video_input_contract")),
                "fact_arbitration": bool(output.get("fact_arbitration")),
                "knia_json_evidence": bool(output.get("knia_json_evidence")),
            },
        },
        "guardrail_checks": {
            "trace_policy": _dict(output.get("agent_trace")).get("trace_policy"),
            "safe_metadata_only": _dict(output.get("agent_trace")).get("trace_policy")
            == "safe_metadata_only_no_raw_user_text",
            "llm_has_final_authority": False,
            "deterministic_judgment_required": True,
            "raw_user_text_in_packet": False,
        },
        "cost_observability": _cost_observability(output, llm_policy, failed_sections),
        "failure_observations": failure_observations,
    }


def _packet_presence(output: dict[str, Any]) -> dict[str, bool]:
    presentation = _dict(output.get("presentation_policy") or _dict(output.get("agent_judgment")).get("presentation_policy"))
    return {
        "input_context": bool(output.get("structured_facts")),
        "evidence_audit": bool(output.get("evidence_audit")),
        "claim_evidence": bool(output.get("claim_evidence")),
        "judgment_contract": bool(output.get("agent_judgment")),
        "reflection_loop": bool(output.get("reflection_loop")),
        "presentation_policy": bool(presentation),
        "agent_trace": bool(output.get("agent_trace")),
    }


def _overall_status(
    judgment: dict[str, Any],
    reflection: dict[str, Any],
    evidence_audit: dict[str, Any],
    missing_packets: list[str],
) -> str:
    if missing_packets:
        return "contract_incomplete"
    next_action = reflection.get("next_action")
    if next_action in {"manual_review", "request_missing_input"}:
        return "needs_human_or_input"
    if judgment.get("decision_ready") is False:
        return "reference_only"
    if evidence_audit.get("uncertainty_level") == "high":
        return "evidence_weak"
    return "ready"


def _cost_observability(
    output: dict[str, Any],
    llm_policy: dict[str, Any],
    failed_sections: list[str],
) -> dict[str, Any]:
    video_contract = _dict(output.get("video_input_contract"))
    technical = _dict(video_contract.get("technical_metadata"))
    return {
        "provider_enabled": bool(llm_policy.get("provider_enabled")),
        "used_sections": list(llm_policy.get("used_sections") or []),
        "blocked_sections": list(llm_policy.get("blocked_sections") or []),
        "failed_sections": failed_sections,
        "token_usage_available": False,
        "token_usage_reason": "OpenAI token usage is not persisted by the current guarded analyst client.",
        "video_frame_count": _safe_int(technical.get("representative_frame_count")),
    }


def _failure_observations(
    output: dict[str, Any],
    llm_policy: dict[str, Any],
    missing_packets: list[str],
    failed_sections: list[str],
) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for section, details in _dict(llm_policy.get("sections")).items():
        failure = _dict(details).get("failure_observation")
        if isinstance(failure, dict):
            observations.append({"section": section, **failure})
    for section in failed_sections:
        if not any(item.get("section") == section for item in observations):
            observations.append(
                {
                    "section": section,
                    "type": "llm_output_unavailable",
                    "recoverable": True,
                    "safe_message": "LLM output was unavailable, so deterministic fallback was used.",
                }
            )
    if missing_packets:
        observations.append(
            {
                "section": "agent_contract",
                "type": "missing_required_packets",
                "recoverable": False,
                "missing_packets": missing_packets,
            }
        )
    judgment = _dict(output.get("agent_judgment"))
    if judgment.get("decision_ready") is False:
        observations.append(
            {
                "section": "judgment_contract",
                "type": "reference_only_judgment",
                "recoverable": True,
                "safe_message": "The Agent marked this result as reference-only because required evidence or facts were insufficient.",
            }
        )
    return observations


def _llm_failed_sections(llm_policy: dict[str, Any]) -> list[str]:
    failed: list[str] = []
    for section, details in _dict(llm_policy.get("sections")).items():
        details = _dict(details)
        if details.get("allowed") and not details.get("used") and details.get("reason") != "allowed":
            failed.append(section)
        elif isinstance(details.get("failure_observation"), dict):
            failed.append(section)
    return list(dict.fromkeys(failed))


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
