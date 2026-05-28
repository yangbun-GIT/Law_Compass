from __future__ import annotations

from typing import Any

from app.services.video_input_contract_metadata import (
    analysis_recovery_plan,
    frame_rich_zero_observation_fallback,
    technical_metadata,
)
from app.services.video_input_contract_observations import (
    candidate_observation,
    collect_observations,
    confirmation_candidates as build_confirmation_candidates,
    confirmation_groups as build_confirmation_groups,
    has_observation_source,
    normalize_observation,
    passes_fact_quality,
    quality_summary,
)
from app.services.video_input_contract_rules import (
    FACT_FIELDS,
    FIELD_CONFIDENCE_THRESHOLDS,
    MIN_FACT_CONFIDENCE,
    SUPPORTING_OBSERVATION_FIELDS,
    VERSION,
    normalize_fact_value,
)


def normalize_video_input_contract(
    video_metadata: dict[str, Any] | None,
    *,
    preprocessed_summary: str | None = None,
) -> dict[str, Any]:
    meta = video_metadata if isinstance(video_metadata, dict) else {}
    nested = meta.get("metadata") if isinstance(meta.get("metadata"), dict) else meta
    technical = technical_metadata(meta, nested)
    observations = collect_observations(meta)
    fallback_observation = frame_rich_zero_observation_fallback(meta, nested, technical, observations)
    if fallback_observation:
        observations.append(fallback_observation)
    fact_patch: dict[str, Any] = {}
    accepted: list[dict[str, Any]] = []
    uncertain: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []
    supporting: list[dict[str, Any]] = []

    for raw in observations:
        observation = normalize_observation(raw)
        if not observation:
            ignored.append({"reason": "unsupported_observation_shape"})
            continue
        field = str(observation["field"])
        confidence = observation.get("confidence")
        source = str(observation.get("source") or "")
        if field in SUPPORTING_OBSERVATION_FIELDS:
            supporting.append({**observation, "reason": "supporting_observation_not_agent_fact"})
            continue
        if field not in FACT_FIELDS:
            ignored.append({**observation, "reason": "field_not_in_agent_fact_contract"})
            continue
        if not has_observation_source(source):
            uncertain.append({**candidate_observation(observation, raw), "reason": "missing_observation_source"})
            continue
        passed, gate_reason, gate = passes_fact_quality(observation)
        if not passed:
            uncertain.append({**candidate_observation(observation, raw), "reason": gate_reason, "quality_gate": gate})
            continue
        value = normalize_fact_value(field, observation.get("value"), raw)
        if value is None:
            uncertain.append({
                **observation,
                "raw_value": observation.get("value"),
                "value": None,
                "reason": "value_not_actionable",
                "quality_gate": gate,
            })
            continue
        fact_patch[field] = value
        accepted.append({**observation, "value": value, "quality_gate": gate})

    _guard_collision_partner_classification(fact_patch, accepted, uncertain)
    _align_collision_partner_from_direct_contact(fact_patch, accepted, uncertain)
    _demote_context_dependent_facts(fact_patch, accepted, uncertain)
    confirmation_candidates = build_confirmation_candidates(uncertain)
    confirmation_groups = build_confirmation_groups(accepted, confirmation_candidates)
    warnings: list[str] = []
    if technical and not accepted:
        warnings.append("technical_video_metadata_not_treated_as_accident_fact")
    if preprocessed_summary and not accepted:
        warnings.append("preprocessed_summary_requires_text_or_structured_observations_for_fact_extraction")
    analysis_recovery = analysis_recovery_plan(meta, nested, technical, accepted, uncertain, ignored, supporting)

    return {
        "version": VERSION,
        "source": "video_preprocess",
        "technical_metadata": technical,
        "fact_patch": fact_patch,
        "accepted_observations": accepted,
        "uncertain_observations": uncertain,
        "supporting_observations": supporting,
        "ignored_observations": ignored,
        "confirmation_candidates": confirmation_candidates,
        "confirmation_groups": confirmation_groups,
        "analysis_recovery": analysis_recovery,
        "observation_quality_summary": quality_summary(accepted, uncertain, ignored, supporting, confirmation_candidates, confirmation_groups, analysis_recovery),
        "warnings": warnings,
        "fact_confidence_threshold": MIN_FACT_CONFIDENCE,
        "field_confidence_thresholds": FIELD_CONFIDENCE_THRESHOLDS,
    }


def _demote_context_dependent_facts(
    fact_patch: dict[str, Any],
    accepted: list[dict[str, Any]],
    uncertain: list[dict[str, Any]],
) -> None:
    if fact_patch.get("ego_turn_direction") in {"left", "right", "u_turn"} and not any(
        fact_patch.get(field) is True for field in ("intersection", "crosswalk_nearby")
    ):
        _move_accepted_to_uncertain(
            "ego_turn_direction",
            fact_patch,
            accepted,
            uncertain,
            "turn_direction_requires_intersection_or_crosswalk_context",
        )

    if fact_patch.get("front_vehicle_stopped") is True:
        location = str(fact_patch.get("collision_point_location") or "")
        has_front_stop_context = (
            fact_patch.get("crosswalk_nearby") is True
            or fact_patch.get("intersection") is True
            or location in {"front_rear", "rear", "rear_end"}
        )
        if not has_front_stop_context:
            _move_accepted_to_uncertain(
                "front_vehicle_stopped",
                fact_patch,
                accepted,
                uncertain,
                "front_vehicle_stop_requires_rear_end_or_crosswalk_context",
            )

    vehicle_collision_context = (
        fact_patch.get("collision_partner_type") == "vehicle"
        or fact_patch.get("direct_collision_partner_type") == "vehicle"
    )
    if vehicle_collision_context:
        if fact_patch.get("pedestrian_visible") is True:
            _move_accepted_to_uncertain(
                "pedestrian_visible",
                fact_patch,
                accepted,
                uncertain,
                "pedestrian_presence_is_context_when_collision_partner_is_vehicle",
            )
        if fact_patch.get("pedestrian_signal") is not None:
            _move_accepted_to_uncertain(
                "pedestrian_signal",
                fact_patch,
                accepted,
                uncertain,
                "pedestrian_signal_is_context_when_collision_partner_is_vehicle",
            )


def _guard_collision_partner_classification(
    fact_patch: dict[str, Any],
    accepted: list[dict[str, Any]],
    uncertain: list[dict[str, Any]],
) -> None:
    partner = str(fact_patch.get("collision_partner_type") or "").strip().lower()
    if partner != "pedestrian":
        return
    direct_partner = str(fact_patch.get("direct_collision_partner_type") or "").strip().lower()
    target_text = str(fact_patch.get("primary_collision_target") or "").strip().lower()
    has_direct_pedestrian_contact = direct_partner == "pedestrian"
    target_mentions_pedestrian = any(token in target_text for token in ("pedestrian", "person", "보행자", "사람"))
    if has_direct_pedestrian_contact or (fact_patch.get("collision_point_visible") is True and target_mentions_pedestrian):
        return
    _move_accepted_to_uncertain(
        "collision_partner_type",
        fact_patch,
        accepted,
        uncertain,
        "pedestrian_collision_partner_requires_direct_contact_evidence",
    )


def _align_collision_partner_from_direct_contact(
    fact_patch: dict[str, Any],
    accepted: list[dict[str, Any]],
    uncertain: list[dict[str, Any]],
) -> None:
    direct_partner = fact_patch.get("direct_collision_partner_type")
    if not direct_partner:
        return
    partner = fact_patch.get("collision_partner_type")
    if partner == direct_partner:
        return
    if partner is not None:
        _move_accepted_to_uncertain(
            "collision_partner_type",
            fact_patch,
            accepted,
            uncertain,
            "direct_collision_partner_overrides_broader_collision_partner",
        )
    fact_patch["collision_partner_type"] = direct_partner


def _move_accepted_to_uncertain(
    field: str,
    fact_patch: dict[str, Any],
    accepted: list[dict[str, Any]],
    uncertain: list[dict[str, Any]],
    reason: str,
) -> None:
    fact_patch.pop(field, None)
    remaining: list[dict[str, Any]] = []
    for item in accepted:
        if item.get("field") == field:
            uncertain.append({**item, "reason": reason})
        else:
            remaining.append(item)
    accepted[:] = remaining
