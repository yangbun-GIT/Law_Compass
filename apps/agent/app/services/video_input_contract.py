from __future__ import annotations

from typing import Any


VERSION = "agent-video-input-contract-v1"
MIN_FACT_CONFIDENCE = 0.75

_OBSERVATION_CONTAINERS = (
    "observations",
    "video_observations",
    "analysis_observations",
    "detected_events",
    "events",
    "frame_observations",
)

_FACT_FIELDS = {
    "stopped",
    "sudden_brake",
    "opponent_behavior",
    "lane_change_actor",
    "turn_signal",
    "user_signal",
    "opponent_signal",
    "opponent_signal_violation",
    "crosswalk_nearby",
    "pedestrian_signal",
    "school_zone",
    "victim_is_child",
    "bicycle_location",
    "bicycle_direction",
    "injury",
    "damage_level",
}

_FIELD_ALIASES = {
    "ego_stopped": "stopped",
    "vehicle_stopped": "stopped",
    "is_stopped": "stopped",
    "stationary": "stopped",
    "hard_brake": "sudden_brake",
    "emergency_brake": "sudden_brake",
    "rear_impact": "opponent_behavior",
    "impact_direction": "opponent_behavior",
    "collision_direction": "opponent_behavior",
    "opponent_lane_change": "lane_change_actor",
    "my_lane_change": "lane_change_actor",
    "signal_violation": "opponent_signal_violation",
    "traffic_light_user": "user_signal",
    "traffic_light_opponent": "opponent_signal",
    "pedestrian_crosswalk": "crosswalk_nearby",
    "child_victim": "victim_is_child",
}

_TECHNICAL_FIELDS = (
    "duration_sec",
    "width",
    "height",
    "fps",
    "codec",
    "extension",
    "file_size_bytes",
    "upload_status",
)


def normalize_video_input_contract(
    video_metadata: dict[str, Any] | None,
    *,
    preprocessed_summary: str | None = None,
) -> dict[str, Any]:
    meta = video_metadata if isinstance(video_metadata, dict) else {}
    nested = meta.get("metadata") if isinstance(meta.get("metadata"), dict) else meta
    technical = _technical_metadata(meta, nested)
    observations = _collect_observations(meta)
    fact_patch: dict[str, Any] = {}
    accepted: list[dict[str, Any]] = []
    uncertain: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []

    for raw in observations:
        observation = _normalize_observation(raw)
        if not observation:
            ignored.append({"reason": "unsupported_observation_shape"})
            continue
        field = str(observation["field"])
        confidence = observation.get("confidence")
        source = str(observation.get("source") or "")
        if field not in _FACT_FIELDS:
            ignored.append({**observation, "reason": "field_not_in_agent_fact_contract"})
            continue
        if not _has_observation_source(source):
            uncertain.append({**observation, "reason": "missing_observation_source"})
            continue
        if not _is_high_confidence(confidence, observation.get("verified")):
            uncertain.append({**observation, "reason": "confidence_below_fact_threshold"})
            continue
        value = _normalize_fact_value(field, observation.get("value"), raw)
        if value is None:
            uncertain.append({**observation, "reason": "value_not_actionable"})
            continue
        fact_patch[field] = value
        accepted.append({**observation, "value": value})

    warnings: list[str] = []
    if technical and not accepted:
        warnings.append("technical_video_metadata_not_treated_as_accident_fact")
    if preprocessed_summary and not accepted:
        warnings.append("preprocessed_summary_requires_text_or_structured_observations_for_fact_extraction")

    return {
        "version": VERSION,
        "source": "video_preprocess",
        "technical_metadata": technical,
        "fact_patch": fact_patch,
        "accepted_observations": accepted,
        "uncertain_observations": uncertain,
        "ignored_observations": ignored,
        "warnings": warnings,
        "fact_confidence_threshold": MIN_FACT_CONFIDENCE,
    }


def _technical_metadata(meta: dict[str, Any], nested: dict[str, Any]) -> dict[str, Any]:
    technical: dict[str, Any] = {}
    for source in (nested, meta):
        for field in _TECHNICAL_FIELDS:
            if field in technical:
                continue
            value = source.get(field) if isinstance(source, dict) else None
            if value not in (None, "", [], {}):
                technical[field] = value
    frames = _frame_list(nested) or _frame_list(meta)
    if frames:
        technical["representative_frame_count"] = len(frames)
    return technical


def _frame_list(value: dict[str, Any]) -> list[Any]:
    for key in ("representative_frames", "extracted_frame_paths", "frames", "frame_paths"):
        frames = value.get(key)
        if isinstance(frames, list):
            return frames
    return []


def _collect_observations(value: Any) -> list[Any]:
    observations: list[Any] = []
    if isinstance(value, dict):
        for key in _OBSERVATION_CONTAINERS:
            nested = value.get(key)
            if isinstance(nested, list):
                observations.extend(nested)
            elif isinstance(nested, dict):
                observations.extend(_observations_from_mapping(nested))
        nested_meta = value.get("metadata")
        if isinstance(nested_meta, dict) and nested_meta is not value:
            observations.extend(_collect_observations(nested_meta))
        preprocess_payload = value.get("preprocess_payload")
        if isinstance(preprocess_payload, dict):
            observations.extend(_collect_observations(preprocess_payload))
    return observations


def _observations_from_mapping(mapping: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for key, value in mapping.items():
        if isinstance(value, dict):
            out.append({"field": key, **value})
        else:
            out.append({"field": key, "value": value})
    return out


def _normalize_observation(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    field = raw.get("field") or raw.get("key") or raw.get("name") or raw.get("type")
    value = raw.get("value")
    if field is None:
        direct = [(key, raw.get(key)) for key in _FACT_FIELDS.union(_FIELD_ALIASES) if key in raw]
        if len(direct) != 1:
            return None
        field, value = direct[0]
    canonical = _FIELD_ALIASES.get(str(field), str(field))
    confidence = raw.get("confidence", raw.get("score"))
    return {
        "field": canonical,
        "raw_field": str(field),
        "value": value,
        "confidence": _as_float(confidence),
        "verified": bool(raw.get("verified")),
        "source": raw.get("source") or raw.get("provider") or raw.get("detector"),
    }


def _has_observation_source(source: str) -> bool:
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


def _is_high_confidence(confidence: float | None, verified: Any) -> bool:
    if verified:
        return True
    return confidence is not None and confidence >= MIN_FACT_CONFIDENCE


def _normalize_fact_value(field: str, value: Any, raw: dict[str, Any]) -> Any:
    if field == "opponent_behavior":
        text = " ".join(str(item).lower() for item in (value, raw.get("raw_field"), raw.get("label")) if item is not None)
        if any(token in text for token in ("rear", "back", "behind", "rear_end")):
            return "rear_collision"
        if any(token in text for token in ("lane_change", "cut_in")):
            return "lane_change"
        if any(token in text for token in ("signal", "red_light")):
            return "signal_violation"
        return value if isinstance(value, str) and value.strip() else None
    if field == "lane_change_actor":
        text = str(value).lower()
        if text in {"opponent", "other", "target", "other_vehicle"}:
            return "opponent"
        if text in {"user", "ego", "self", "my_vehicle"}:
            return "user"
        return value if isinstance(value, str) and value.strip() else None
    if field in {"stopped", "sudden_brake", "opponent_signal_violation", "crosswalk_nearby", "school_zone", "victim_is_child", "injury"}:
        return _as_bool(value)
    if isinstance(value, str):
        return value.strip() or None
    return value


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "y", "1", "observed", "detected"}:
            return True
        if lowered in {"false", "no", "n", "0", "not_observed", "none"}:
            return False
    return None


def _as_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
