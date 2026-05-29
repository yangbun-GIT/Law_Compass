from pathlib import Path
from typing import Any


def normalize_openai_observations(
    raw_observations: Any,
    selected_frames: list[dict[str, Any]],
    *,
    detector: str,
) -> list[dict[str, Any]]:
    if not isinstance(raw_observations, list):
        return []
    allowed_frame_refs = {Path(frame["path"]).name for frame in selected_frames}
    observations: list[dict[str, Any]] = []
    for item in raw_observations:
        if not isinstance(item, dict):
            continue
        field = str(item.get("field") or item.get("name") or item.get("type") or "").strip()
        if not field:
            continue
        value = item.get("value", "unknown")
        alias = post_impact_target_alias(field)
        if alias:
            field = "primary_collision_target"
            value = f"{alias}_candidate"
        if should_drop_openai_observation(field, value):
            continue
        frame_refs = [str(ref) for ref in item.get("frame_refs") or item.get("frames") or [] if str(ref) in allowed_frame_refs]
        confidence = normalize_observation_confidence(field, value, item.get("confidence"), frame_refs)
        reason = str(item.get("reason") or item.get("evidence") or "")
        if alias:
            reason = f"{reason}; post_impact_non_vehicle_target_candidate" if reason else "post_impact_non_vehicle_target_candidate"
        observations.append({
            "field": field,
            "value": value,
            "confidence": confidence,
            "source": "frame_analysis:openai",
            "detector": detector,
            "frame_refs": frame_refs,
            "reason": reason,
            "observation_quality": observation_quality(field, confidence, frame_refs),
        })
    return soften_target_contradictions(observations)


def post_impact_target_alias(field: str) -> str:
    normalized = field.strip().lower().replace("-", "_")
    if normalized in {"motorcycle_visible_post_impact", "two_wheeler_visible_post_impact", "two_wheeled_vehicle_visible_post_impact"}:
        return "motorcycle"
    if normalized in {"bicycle_visible_post_impact", "bike_visible_post_impact", "cyclist_visible_post_impact"}:
        return "bicycle"
    if normalized in {"pedestrian_visible_post_impact", "person_visible_post_impact"}:
        return "pedestrian"
    return ""


def soften_target_contradictions(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep visually useful target candidates, but avoid confident ego/target flips.

    Vision models often describe the ego vehicle as the "vehicle" collision
    partner in vehicle-to-pedestrian/bicycle/motorcycle scenes. That is useful
    context, but it must not pass as a direct accident target.
    """
    primary_targets = [
        _target_value(item)
        for item in observations
        if item.get("field") == "primary_collision_target"
    ]
    non_vehicle_primary_targets = {target for target in primary_targets if target in {"pedestrian", "bicycle", "motorcycle", "object"}}
    softened: list[dict[str, Any]] = []
    for item in observations:
        field = str(item.get("field") or "")
        target = _target_value(item)
        if field in {"collision_partner_type", "direct_collision_partner_type"} and target == "vehicle" and non_vehicle_primary_targets:
            softened.append(_demote_direct_vehicle_target(
                item,
                "ego_vehicle_partner_ambiguity_with_non_vehicle_primary_target",
            ))
            continue
        if field == "direct_collision_partner_type" and target in {"pedestrian", "bicycle", "motorcycle", "object"}:
            if len(item.get("frame_refs") or []) < 3:
                softened.append(_cap_observation_confidence(
                    item,
                    0.74,
                    "direct_non_vehicle_target_requires_multi_frame_contact_evidence",
                ))
                continue
        if field == "primary_collision_target" and target in {"pedestrian", "bicycle", "motorcycle"}:
            if len(item.get("frame_refs") or []) < 3:
                softened.append(_cap_observation_confidence(
                    item,
                    0.74,
                    "non_vehicle_primary_target_requires_multi_frame_contact_evidence",
                ))
                continue
        softened.append(item)
    return softened


def _cap_observation_confidence(item: dict[str, Any], cap: float, reason: str) -> dict[str, Any]:
    confidence = min(as_float(item.get("confidence"), 0.0), cap)
    frame_refs = item.get("frame_refs") or []
    text = str(item.get("reason") or "")
    next_reason = f"{text}; {reason}" if text else reason
    return {
        **item,
        "confidence": confidence,
        "reason": next_reason,
        "observation_quality": observation_quality(str(item.get("field") or ""), confidence, frame_refs),
    }


def _demote_direct_vehicle_target(item: dict[str, Any], reason: str) -> dict[str, Any]:
    """Keep the vehicle as context, but do not let it pass as direct target.

    When a non-vehicle target candidate is also visible, a model often labels
    the ego vehicle or a nearby vehicle as the direct partner. For fault
    guidance, that is worse than uncertainty, so the direct fact is downgraded
    to a vehicle candidate.
    """
    confidence = min(as_float(item.get("confidence"), 0.0), 0.74)
    frame_refs = item.get("frame_refs") or []
    text = str(item.get("reason") or "")
    next_reason = f"{text}; {reason}" if text else reason
    return {
        **item,
        "field": "primary_collision_target",
        "value": "vehicle_candidate",
        "confidence": confidence,
        "reason": next_reason,
        "observation_quality": observation_quality("primary_collision_target", confidence, frame_refs),
    }


def _target_value(item: dict[str, Any]) -> str:
    text = str(item.get("value") or "").strip().lower().replace("-", "_")
    if text.endswith("_candidate"):
        text = text[: -len("_candidate")]
    return text


def normalize_accident_event_summary(value: Any, selected_frames: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    allowed_frame_refs = {Path(frame["path"]).name for frame in selected_frames}

    def refs(name: str) -> list[str]:
        return [str(ref) for ref in value.get(name) or [] if str(ref) in allowed_frame_refs]

    output: dict[str, Any] = {
        "impact_visible": bool(value.get("impact_visible")) if value.get("impact_visible") is not None else None,
        "event_frame_refs": refs("event_frame_refs"),
        "pre_impact_frame_refs": refs("pre_impact_frame_refs"),
        "post_impact_frame_refs": refs("post_impact_frame_refs"),
        "rationale": str(value.get("rationale") or "")[:500],
    }
    return {key: item for key, item in output.items() if item not in (None, "", [])}


def derive_accident_event_summary_from_observations(
    observations: list[dict[str, Any]],
    selected_frames: list[dict[str, Any]],
) -> dict[str, Any]:
    event_fields = {
        "collision_partner_type",
        "primary_collision_target",
        "collision_point_visible",
        "collision_point_location",
        "impact_direction",
        "collision_direction",
        "secondary_collision",
        "non_contact_trigger",
        "direct_collision_partner_type",
        "rear_vehicle_collision",
    }
    event_refs: list[str] = []
    for item in observations:
        if not isinstance(item, dict) or item.get("field") not in event_fields:
            continue
        confidence = as_float(item.get("confidence"), 0.0)
        if confidence < 0.75:
            continue
        for ref in item.get("frame_refs") or []:
            text = str(ref)
            if text not in event_refs:
                event_refs.append(text)
    if not event_refs:
        return {}
    frame_names = [Path(frame["path"]).name for frame in selected_frames]
    event_refs = [ref for ref in event_refs if ref in frame_names]
    if not event_refs:
        return {}
    first_index = min(frame_names.index(ref) for ref in event_refs)
    last_index = max(frame_names.index(ref) for ref in event_refs)
    pre_refs = frame_names[max(0, first_index - 2):first_index]
    post_refs = frame_names[last_index + 1:last_index + 3]
    return {
        "impact_visible": True,
        "event_frame_refs": event_refs,
        "pre_impact_frame_refs": pre_refs,
        "post_impact_frame_refs": post_refs,
        "rationale": "Derived from high-confidence collision-related observations because the model omitted accident_event_summary.",
    }


def normalize_observation_confidence(field: str, value: Any, confidence_value: Any, frame_refs: list[str]) -> float:
    confidence = as_float(confidence_value, 0.0)
    if field == "stopped" and value is False:
        # Moving dashcam pixels are easy to overread as "not stopped".
        # Keep negative stopped observations below Agent fact threshold unless
        # a later provider adds stronger motion evidence in the contract.
        if len(frame_refs) < 3:
            return min(confidence, 0.74)
        return min(confidence, 0.81)
    return confidence


def observation_quality_summary(observations: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {"high": 0, "medium": 0, "low": 0, "none": 0}
    no_frame_ref = 0
    single_frame = 0
    multi_frame = 0
    for item in observations:
        quality = item.get("observation_quality") if isinstance(item.get("observation_quality"), dict) else {}
        level = str(quality.get("level") or "none")
        counts[level if level in counts else "none"] += 1
        frame_count = len(item.get("frame_refs") or []) if isinstance(item.get("frame_refs"), list) else 0
        if frame_count == 0:
            no_frame_ref += 1
        elif frame_count == 1:
            single_frame += 1
        else:
            multi_frame += 1
    return {
        "observation_count": len(observations),
        "quality_counts": counts,
        "no_frame_reference_count": no_frame_ref,
        "single_frame_observation_count": single_frame,
        "multi_frame_observation_count": multi_frame,
    }


def observation_quality(field: str, confidence: float, frame_refs: list[str]) -> dict[str, Any]:
    frame_count = len(frame_refs)
    flags: list[str] = []
    if frame_count == 0:
        flags.append("missing_frame_reference")
    elif frame_count == 1:
        flags.append("single_frame_observation")
    if confidence < 0.75:
        flags.append("low_confidence")
    if confidence >= 0.9 and frame_count >= 2:
        level = "high"
    elif confidence >= 0.82 and frame_count >= 1:
        level = "medium"
    elif confidence >= 0.75:
        level = "low"
    else:
        level = "none"
    return {
        "level": level,
        "frame_ref_count": frame_count,
        "confidence": confidence,
        "field": field,
        "risk_flags": flags,
    }


def should_drop_openai_observation(field: str, value: Any) -> bool:
    text = str(value).strip().lower()
    if text in {"", "unknown", "unclear", "not_visible", "not visible", "none"}:
        return True
    if field == "injury":
        return True
    if field == "damage_level" and text in {"none", "no_damage", "no damage"}:
        return True
    if value is False and field in {
        "opponent_signal_violation",
        "crosswalk_nearby",
        "school_zone",
        "turn_signal",
        "user_signal",
        "opponent_signal",
        "centerline_crossed",
        "road_obstruction",
        "illegal_parking_obstruction",
        "opposing_vehicle_present",
        "opposing_vehicle_did_not_stop",
        "secondary_collision",
        "non_contact_trigger",
        "rear_vehicle_collision",
        "collision_point_visible",
        "front_vehicle_stopped",
        "intersection",
        "opponent_signal_visible",
        "stopped_vehicle_without_lights",
        "highway_or_expressway",
        "recaptured_screen",
        "dashcam_screen_visible",
        "screen_glare_or_reflection",
    }:
        return True
    return False


def as_float(value: Any, default: float) -> float:
    try:
        number = float(value)
        return max(0.0, min(1.0, number))
    except (TypeError, ValueError):
        return default
