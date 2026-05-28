from __future__ import annotations

from typing import Any

from app.services.video_input_contract_rules import (
    CONFIRMATION_FIELD_PRIORITIES,
    FACT_FIELDS,
    FIELD_ALIASES,
    FIELD_CONFIDENCE_THRESHOLDS,
    FRAME_REF_REQUIRED_FACT_FIELDS,
    FRAME_REF_REQUIRED_SOURCES,
    MIN_FACT_CONFIDENCE,
    OBSERVATION_CONTAINERS,
    SUPPORTING_OBSERVATION_FIELDS,
    as_float,
    normalize_fact_value,
)


def collect_observations(value: Any) -> list[Any]:
    observations: list[Any] = []
    if isinstance(value, dict):
        for key in OBSERVATION_CONTAINERS:
            nested = value.get(key)
            if isinstance(nested, list):
                observations.extend(nested)
            elif isinstance(nested, dict):
                observations.extend(observations_from_mapping(nested))
        nested_meta = value.get("metadata")
        if isinstance(nested_meta, dict) and nested_meta is not value:
            observations.extend(collect_observations(nested_meta))
        preprocess_payload = value.get("preprocess_payload")
        if isinstance(preprocess_payload, dict):
            observations.extend(collect_observations(preprocess_payload))
    return observations


def observations_from_mapping(mapping: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for key, value in mapping.items():
        if isinstance(value, dict):
            out.append({"field": key, **value})
        else:
            out.append({"field": key, "value": value})
    return out


def normalize_observation(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    field = raw.get("field") or raw.get("key") or raw.get("name") or raw.get("type")
    value = raw.get("value")
    if field is None:
        direct = [(key, raw.get(key)) for key in FACT_FIELDS.union(FIELD_ALIASES).union(SUPPORTING_OBSERVATION_FIELDS) if key in raw]
        if len(direct) != 1:
            return None
        field, value = direct[0]
    canonical = FIELD_ALIASES.get(str(field), str(field))
    confidence = raw.get("confidence", raw.get("score"))
    return {
        "field": canonical,
        "raw_field": str(field),
        "value": value,
        "confidence": as_float(confidence),
        "verified": bool(raw.get("verified")),
        "source": raw.get("source") or raw.get("provider") or raw.get("detector"),
        "frame_refs": raw.get("frame_refs") or raw.get("frames") or [],
        "reason": raw.get("reason") or raw.get("evidence") or "",
    }


def candidate_observation(observation: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    field = str(observation.get("field") or "")
    normalized_value = normalize_fact_value(field, observation.get("value"), raw)
    if normalized_value is None:
        return observation
    if normalized_value == observation.get("value"):
        return observation
    return {**observation, "raw_value": observation.get("value"), "value": normalized_value}


def has_observation_source(source: str) -> bool:
    base_source = source.split(":", 1)[0]
    return base_source in {
        "frame_analysis",
        "vision_model",
        "video_model",
        "manual_video_review",
        "dashcam_analysis",
        "blackbox_analysis",
        "video_preprocess_observation",
    }


def passes_fact_quality(observation: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    field = str(observation.get("field") or "")
    confidence = observation.get("confidence")
    verified = observation.get("verified")
    source = str(observation.get("source") or "")
    threshold = FIELD_CONFIDENCE_THRESHOLDS.get(field, MIN_FACT_CONFIDENCE)
    frame_ref_count = frame_ref_count_of(observation)
    needs_frame_ref = requires_frame_ref(field, source)
    gate = {
        "status": "accepted",
        "min_confidence": threshold,
        "confidence": confidence,
        "frame_ref_count": frame_ref_count,
        "min_frame_refs": 1 if needs_frame_ref else 0,
    }
    if verified:
        gate["status"] = "accepted_verified"
        return True, "accepted", gate
    if confidence is None or confidence < threshold:
        gate["status"] = "rejected"
        return False, "confidence_below_field_threshold", gate
    if needs_frame_ref and frame_ref_count < 1:
        gate["status"] = "rejected"
        return False, "missing_frame_reference", gate
    return True, "accepted", gate


def requires_frame_ref(field: str, source: str) -> bool:
    return field in FRAME_REF_REQUIRED_FACT_FIELDS and source.split(":", 1)[0] in FRAME_REF_REQUIRED_SOURCES


def frame_ref_count_of(observation: dict[str, Any]) -> int:
    refs = observation.get("frame_refs")
    return len(refs) if isinstance(refs, list) else 0


def quality_summary(
    accepted: list[dict[str, Any]],
    uncertain: list[dict[str, Any]],
    ignored: list[dict[str, Any]],
    supporting: list[dict[str, Any]],
    confirmation_candidates: list[dict[str, Any]] | None = None,
    confirmation_groups: list[dict[str, Any]] | None = None,
    analysis_recovery: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reasons: dict[str, int] = {}
    for item in [*uncertain, *ignored]:
        reason = str(item.get("reason") or "unknown")
        reasons[reason] = reasons.get(reason, 0) + 1
    accepted_frame_ref_counts = [
        int((item.get("quality_gate") or {}).get("frame_ref_count") or 0)
        for item in accepted
        if isinstance(item.get("quality_gate"), dict)
    ]
    candidates = confirmation_candidates or []
    groups = confirmation_groups or []
    return {
        "accepted_count": len(accepted),
        "uncertain_count": len(uncertain),
        "ignored_count": len(ignored),
        "supporting_count": len(supporting),
        "uncertain_reasons": reasons,
        "accepted_single_frame_count": sum(1 for count in accepted_frame_ref_counts if count == 1),
        "accepted_multi_frame_count": sum(1 for count in accepted_frame_ref_counts if count >= 2),
        "confirmation_candidate_count": len(candidates),
        "confirmation_group_count": len(groups),
        "high_priority_uncertain_fields": [str(item.get("field")) for item in candidates[:5] if item.get("field")],
        "recovery_status": (analysis_recovery or {}).get("status"),
        "recovery_actions": (analysis_recovery or {}).get("actions") or [],
    }


def confirmation_candidates(uncertain: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in uncertain:
        field = str(item.get("field") or "")
        if field not in CONFIRMATION_FIELD_PRIORITIES:
            continue
        if item.get("value") in (None, "", [], {}):
            continue
        gate = item.get("quality_gate") if isinstance(item.get("quality_gate"), dict) else {}
        candidates.append({
            "field": field,
            "value": item.get("value"),
            "confidence": item.get("confidence"),
            "reason": item.get("reason") or "confirmation_needed",
            "frame_ref_count": frame_ref_count_of(item),
            "min_confidence": gate.get("min_confidence"),
            "priority": CONFIRMATION_FIELD_PRIORITIES[field],
            "action": "ask_user_confirmation",
        })
    return sorted(
        candidates,
        key=lambda item: (
            int(item.get("priority") or 999),
            -int(item.get("frame_ref_count") or 0),
            -float(item.get("confidence") or 0),
        ),
    )


def confirmation_groups(
    accepted: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    values: dict[str, Any] = {}
    sources: dict[str, str] = {}
    for item in accepted:
        field = str(item.get("field") or "")
        if not field:
            continue
        values[field] = item.get("value")
        sources[field] = "accepted"
    for item in candidates:
        field = str(item.get("field") or "")
        if not field or field in values:
            continue
        values[field] = item.get("value")
        sources[field] = "confirmation_candidate"

    groups: list[dict[str, Any]] = []
    if values.get("stopped") is True and values.get("opponent_behavior") == "rear_collision":
        fields = ["stopped", "opponent_behavior"]
        groups.append({
            "type": "rear_end_candidate",
            "fields": fields,
            "status": "needs_user_confirmation" if any(sources.get(field) == "confirmation_candidate" for field in fields) else "accepted",
            "reason": "stopped_vehicle_and_rear_collision_observed",
        })
    if values.get("lane_change_actor") in {"user", "opponent"}:
        groups.append({
            "type": "lane_change_candidate",
            "fields": ["lane_change_actor"],
            "status": "needs_user_confirmation" if sources.get("lane_change_actor") == "confirmation_candidate" else "accepted",
            "reason": "lane_change_actor_observed",
        })
    if values.get("opponent_signal_violation") is True:
        groups.append({
            "type": "signal_violation_candidate",
            "fields": ["opponent_signal_violation"],
            "status": "needs_user_confirmation" if sources.get("opponent_signal_violation") == "confirmation_candidate" else "accepted",
            "reason": "opponent_signal_violation_observed",
        })
    return groups
