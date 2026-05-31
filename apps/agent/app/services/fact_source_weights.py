from __future__ import annotations

from typing import Any


VERSION = "agent-fact-source-weights-v1"

SOURCE_WEIGHTS = {
    "selected_major_category": 0.85,
    "selected_preliminary_accident_type": 0.70,
    "video_observation": 0.90,
    "structured_followup_answer": 0.85,
    "natural_language_claim": 0.30,
    "knia_evidence": 0.55,
    "legal_evidence": 0.50,
}


def build_fact_source_weight_contract(initial_intake: dict[str, Any] | None, facts: dict[str, Any] | None) -> dict[str, Any]:
    intake = initial_intake if isinstance(initial_intake, dict) else {}
    fact_map = facts if isinstance(facts, dict) else {}
    sources: dict[str, dict[str, Any]] = {}
    if intake.get("accident_major_category") and intake.get("accident_major_category") != "unknown":
        sources["accident_party_type"] = {
            "source_type": "selected_major_category",
            "weight": SOURCE_WEIGHTS["selected_major_category"],
            "can_be_overridden_by": ["high_confidence_video_observation", "structured_followup_answer"],
        }
    if intake.get("preliminary_accident_type") and intake.get("preliminary_accident_type") != "unknown":
        sources["accident_type"] = {
            "source_type": "selected_preliminary_accident_type",
            "weight": SOURCE_WEIGHTS["selected_preliminary_accident_type"],
            "can_be_overridden_by": ["high_confidence_video_observation", "structured_followup_answer"],
        }
    for key in _string_list(fact_map.get("_followup_answered_fields")):
        sources[key] = {
            "source_type": "structured_followup_answer",
            "weight": SOURCE_WEIGHTS["structured_followup_answer"],
            "can_be_overridden_by": ["verified_video_observation"],
        }
    if intake.get("natural_language_description"):
        sources["natural_language_description"] = {
            "source_type": "natural_language_claim",
            "weight": SOURCE_WEIGHTS["natural_language_claim"],
            "can_override_video": False,
            "can_override_structured_followup": False,
        }
    return {
        "version": VERSION,
        "weights": SOURCE_WEIGHTS,
        "field_sources": sources,
    }


def _string_list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []
