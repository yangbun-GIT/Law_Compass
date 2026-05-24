from __future__ import annotations

from typing import Any


VERSION = "agent-fact-arbitration-v1"

VIDEO_PRIMARY_FIELDS = {
    "stopped",
    "sudden_brake",
    "opponent_behavior",
    "lane_change_actor",
    "turn_signal",
    "user_signal",
    "opponent_signal",
    "opponent_signal_violation",
    "crosswalk_nearby",
    "pedestrian_visible",
    "pedestrian_signal",
    "school_zone",
    "victim_is_child",
    "bicycle_location",
    "bicycle_direction",
    "damage_level",
    "centerline_crossed",
    "centerline_cross_reason",
    "road_obstruction",
    "illegal_parking_obstruction",
    "opposing_vehicle_present",
    "opposing_vehicle_did_not_stop",
    "secondary_collision",
    "collision_partner_type",
    "primary_collision_target",
    "collision_point_visible",
    "collision_point_location",
}

USER_PRIMARY_FIELDS = {
    "accident_type",
    "injury",
    "injury_detail",
    "treatment_status",
    "insurance_status",
    "driver_role",
    "accident_party_type",
}

EMPTY_VALUES = {None, "", "unknown", "모름", "None", "null"}
CONFLICT_OVERRIDE_CONFIDENCE = 0.92
CONFLICT_OVERRIDE_MIN_FRAME_REFS = 2


def arbitrate_facts(
    *,
    user_facts: dict[str, Any] | None,
    video_contract: dict[str, Any] | None,
) -> dict[str, Any]:
    """Merge user facts and video-derived facts with source-aware precedence."""
    user = user_facts if isinstance(user_facts, dict) else {}
    contract = video_contract if isinstance(video_contract, dict) else {}
    video_patch = contract.get("fact_patch") if isinstance(contract.get("fact_patch"), dict) else {}
    observations = contract.get("accepted_observations") if isinstance(contract.get("accepted_observations"), list) else []

    facts = dict(user)
    fact_sources: dict[str, dict[str, Any]] = {
        field: {"source": "user", "authority": _authority(field)}
        for field, value in user.items()
        if not _is_empty(value)
    }
    conflicts: list[dict[str, Any]] = []
    applied_video_fields: list[str] = []
    kept_user_fields: list[str] = []
    confirmed_fields: list[str] = []

    for field, video_value in video_patch.items():
        if _is_empty(video_value):
            continue
        authority = _authority(field)
        observation = _observation_for_field(observations, field)
        user_value = facts.get(field)

        if _is_empty(user_value):
            facts[field] = video_value
            fact_sources[field] = _source_info("video", authority, observation)
            applied_video_fields.append(field)
            continue

        if _equivalent(field, user_value, video_value):
            facts[field] = _canonical_fact_value(field, video_value)
            fact_sources[field] = _source_info("user_and_video", authority, observation)
            confirmed_fields.append(field)
            continue

        gate_reason = ""
        if authority == "video_primary" and _video_conflict_override_allowed(observation):
            facts[field] = video_value
            fact_sources[field] = _source_info("video", authority, observation)
            applied_video_fields.append(field)
            winner = "video"
        elif authority == "video_primary":
            kept_user_fields.append(field)
            winner = "user"
            gate_reason = _video_quality_gate_reason(observation)
        elif authority == "user_primary":
            kept_user_fields.append(field)
            winner = "user"
        else:
            kept_user_fields.append(field)
            winner = "user"

        conflicts.append(_conflict(field, user_value, video_value, winner, authority, observation, gate_reason))

    arbitration_contract = {
        "version": VERSION,
        "policy": {
            "video_primary": "Physical facts visible in frames can fill missing values. When they conflict with user text, they win only after passing the conflict override quality gate.",
            "user_primary": "Accident type, injury, treatment, insurance, and role facts remain user-primary unless later confirmed by a dedicated source.",
            "unknown_field": "Unknown fields keep user input when present; video fills only missing values.",
            "conflict_override_gate": f"Conflicting video-primary observations need verified/manual review or confidence >= {CONFLICT_OVERRIDE_CONFIDENCE} with at least {CONFLICT_OVERRIDE_MIN_FRAME_REFS} frame refs.",
        },
        "video_primary_fields": sorted(VIDEO_PRIMARY_FIELDS),
        "user_primary_fields": sorted(USER_PRIMARY_FIELDS),
        "fact_sources": fact_sources,
        "applied_video_fields": sorted(set(applied_video_fields)),
        "kept_user_fields": sorted(set(kept_user_fields)),
        "confirmed_fields": sorted(set(confirmed_fields)),
        "conflicts": conflicts,
        "requires_confirmation": [item for item in conflicts if item.get("needs_confirmation")],
    }
    return {"facts": facts, "contract": arbitration_contract}


def _authority(field: str) -> str:
    if field in VIDEO_PRIMARY_FIELDS:
        return "video_primary"
    if field in USER_PRIMARY_FIELDS:
        return "user_primary"
    return "user_when_present"


def _observation_for_field(observations: list[Any], field: str) -> dict[str, Any]:
    for item in observations:
        if isinstance(item, dict) and item.get("field") == field:
            return item
    return {}


def _source_info(source: str, authority: str, observation: dict[str, Any]) -> dict[str, Any]:
    info: dict[str, Any] = {"source": source, "authority": authority}
    if observation:
        info["confidence"] = observation.get("confidence")
        info["provider"] = observation.get("source")
        if observation.get("frame_refs"):
            info["frame_refs"] = observation.get("frame_refs")
        if observation.get("reason"):
            info["reason"] = observation.get("reason")
    return info


def _video_conflict_override_allowed(observation: dict[str, Any]) -> bool:
    if not observation:
        return False
    if observation.get("verified") is True:
        return True
    source_base = str(observation.get("source") or "").split(":", 1)[0]
    if source_base == "manual_video_review":
        return True
    confidence = _as_confidence(observation.get("confidence"))
    return confidence >= CONFLICT_OVERRIDE_CONFIDENCE and _frame_ref_count(observation) >= CONFLICT_OVERRIDE_MIN_FRAME_REFS


def _video_quality_gate_reason(observation: dict[str, Any]) -> str:
    confidence = _as_confidence(observation.get("confidence")) if observation else 0.0
    frame_count = _frame_ref_count(observation)
    return (
        "video_conflict_quality_gate_not_met:"
        f" confidence={confidence:.2f}, frame_refs={frame_count},"
        f" required_confidence={CONFLICT_OVERRIDE_CONFIDENCE:.2f},"
        f" required_frame_refs={CONFLICT_OVERRIDE_MIN_FRAME_REFS}"
    )


def _as_confidence(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _frame_ref_count(observation: dict[str, Any]) -> int:
    frame_refs = observation.get("frame_refs") if isinstance(observation, dict) else []
    return len(frame_refs) if isinstance(frame_refs, list) else 0


def _conflict(
    field: str,
    user_value: Any,
    video_value: Any,
    winner: str,
    authority: str,
    observation: dict[str, Any],
    gate_reason: str = "",
) -> dict[str, Any]:
    item = {
        "field": field,
        "user_value": user_value,
        "video_value": video_value,
        "winner": winner,
        "authority": authority,
        "reason": _conflict_reason(field, winner, authority),
        "needs_confirmation": True,
    }
    if gate_reason:
        item["quality_gate"] = gate_reason
    if observation:
        item["video_confidence"] = observation.get("confidence")
        item["video_source"] = observation.get("source")
        if observation.get("frame_refs"):
            item["frame_refs"] = observation.get("frame_refs")
        if observation.get("reason"):
            item["video_reason"] = observation.get("reason")
    return item


def _conflict_reason(field: str, winner: str, authority: str) -> str:
    if winner == "video" and authority == "video_primary":
        return f"{field} is treated as a frame-observable physical fact."
    if winner == "user" and authority == "user_primary":
        return f"{field} is treated as user-primary context."
    return "User input is kept because no source authority is defined for this field."


def _equivalent(field: str, left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return _as_bool(left) is _as_bool(right)
    return _canonical_fact_value(field, left) == _canonical_fact_value(field, right)


def _canonical_fact_value(field: str, value: Any) -> Any:
    if field == "opponent_behavior":
        text = str(value).strip().lower()
        if text in {"rear_collision", "rear_vehicle_collision", "rear_end", "rear_end_collision", "rear_impact"}:
            return "rear_collision"
        if text in {"lane_change", "cut_in", "opponent_lane_change"}:
            return "lane_change"
        if text in {"signal_violation", "red_light_violation"}:
            return "signal_violation"
    if field == "lane_change_actor":
        text = str(value).strip().lower()
        if text in {"opponent", "other", "target", "other_vehicle"}:
            return "opponent"
        if text in {"user", "ego", "self", "my_vehicle"}:
            return "user"
    if isinstance(value, str):
        return value.strip().lower()
    return value


def _is_empty(value: Any) -> bool:
    if isinstance(value, (dict, list, set, tuple)):
        return len(value) == 0
    if value in EMPTY_VALUES:
        return True
    if isinstance(value, str) and value.strip() in EMPTY_VALUES:
        return True
    return False


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "y", "1", "observed", "detected", "예"}:
            return True
        if lowered in {"false", "no", "n", "0", "not_observed", "none", "아니오"}:
            return False
    return None
