from __future__ import annotations

from typing import Any


VERSION = "agent-video-input-contract-v1"
MIN_FACT_CONFIDENCE = 0.75
FIELD_CONFIDENCE_THRESHOLDS = {
    "stopped": 0.82,
    "opponent_behavior": 0.88,
    "lane_change_actor": 0.88,
    "intersection": 0.82,
    "opponent_signal_visible": 0.84,
    "opponent_signal_violation": 0.88,
    "signal_transition": 0.82,
    "crosswalk_nearby": 0.85,
    "pedestrian_visible": 0.88,
    "pedestrian_signal": 0.82,
    "school_zone": 0.85,
    "centerline_crossed": 0.86,
    "road_obstruction": 0.84,
    "illegal_parking_obstruction": 0.84,
    "opposing_vehicle_present": 0.82,
    "opposing_vehicle_did_not_stop": 0.88,
    "secondary_collision": 0.84,
    "non_contact_trigger": 0.82,
    "trigger_actor_type": 0.78,
    "trigger_actor_behavior": 0.78,
    "direct_collision_partner_type": 0.82,
    "rear_vehicle_collision": 0.84,
    "centerline_cross_reason": 0.78,
    "collision_partner_type": 0.82,
    "primary_collision_target": 0.78,
    "collision_point_visible": 0.84,
    "collision_point_location": 0.78,
    "front_vehicle_stopped": 0.84,
    "ego_turn_direction": 0.78,
    "stopped_vehicle_without_lights": 0.88,
    "highway_or_expressway": 0.82,
}
CONFIRMATION_FIELD_PRIORITIES = {
    "stopped": 10,
    "collision_partner_type": 20,
    "primary_collision_target": 30,
    "collision_point_visible": 40,
    "collision_point_location": 50,
    "front_vehicle_stopped": 60,
    "ego_turn_direction": 70,
    "opponent_behavior": 80,
    "intersection": 90,
    "user_signal": 100,
    "opponent_signal_visible": 110,
    "opponent_signal": 120,
    "signal_transition": 130,
    "opponent_signal_violation": 140,
    "centerline_crossed": 150,
    "centerline_cross_reason": 160,
    "road_obstruction": 170,
    "illegal_parking_obstruction": 180,
    "opposing_vehicle_present": 190,
    "opposing_vehicle_did_not_stop": 200,
    "secondary_collision": 210,
    "non_contact_trigger": 220,
    "trigger_actor_type": 230,
    "trigger_actor_behavior": 240,
    "direct_collision_partner_type": 250,
    "rear_vehicle_collision": 260,
    "stopped_vehicle_without_lights": 270,
    "highway_or_expressway": 280,
    "lane_change_actor": 290,
    "sudden_brake": 300,
    "turn_signal": 310,
    "crosswalk_nearby": 320,
    "pedestrian_visible": 330,
    "pedestrian_signal": 340,
    "school_zone": 350,
    "injury": 360,
    "damage_level": 370,
}

FRAME_REF_REQUIRED_FACT_FIELDS = {
    "stopped",
    "sudden_brake",
    "opponent_behavior",
    "lane_change_actor",
    "intersection",
    "opponent_signal_visible",
    "opponent_signal_violation",
    "signal_transition",
    "crosswalk_nearby",
    "pedestrian_visible",
    "pedestrian_signal",
    "school_zone",
    "damage_level",
    "centerline_crossed",
    "road_obstruction",
    "illegal_parking_obstruction",
    "opposing_vehicle_present",
    "opposing_vehicle_did_not_stop",
    "secondary_collision",
    "non_contact_trigger",
    "trigger_actor_type",
    "trigger_actor_behavior",
    "direct_collision_partner_type",
    "rear_vehicle_collision",
    "centerline_cross_reason",
    "collision_partner_type",
    "primary_collision_target",
    "collision_point_visible",
    "collision_point_location",
    "front_vehicle_stopped",
    "ego_turn_direction",
    "stopped_vehicle_without_lights",
    "highway_or_expressway",
}

FRAME_REF_REQUIRED_SOURCES = {
    "frame_analysis",
    "vision_model",
    "video_model",
    "dashcam_analysis",
    "blackbox_analysis",
}

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
    "opponent_signal_visible",
    "opponent_signal_violation",
    "signal_transition",
    "intersection",
    "crosswalk_nearby",
    "pedestrian_visible",
    "pedestrian_signal",
    "school_zone",
    "victim_is_child",
    "bicycle_location",
    "bicycle_direction",
    "injury",
    "damage_level",
    "centerline_crossed",
    "centerline_cross_reason",
    "road_obstruction",
    "illegal_parking_obstruction",
    "opposing_vehicle_present",
    "opposing_vehicle_did_not_stop",
    "secondary_collision",
    "non_contact_trigger",
    "trigger_actor_type",
    "trigger_actor_behavior",
    "direct_collision_partner_type",
    "rear_vehicle_collision",
    "collision_partner_type",
    "primary_collision_target",
    "collision_point_visible",
    "collision_point_location",
    "front_vehicle_stopped",
    "ego_turn_direction",
    "stopped_vehicle_without_lights",
    "highway_or_expressway",
}

_SUPPORTING_OBSERVATION_FIELDS = {
    "impact_direction",
    "collision_direction",
    "recaptured_screen",
    "dashcam_screen_visible",
    "screen_glare_or_reflection",
    "visual_evidence_limited",
}

_FIELD_ALIASES = {
    "ego_stopped": "stopped",
    "vehicle_stopped": "stopped",
    "is_stopped": "stopped",
    "stationary": "stopped",
    "hard_brake": "sudden_brake",
    "emergency_brake": "sudden_brake",
    "rear_impact": "opponent_behavior",
    "opponent_lane_change": "lane_change_actor",
    "my_lane_change": "lane_change_actor",
    "signal_violation": "opponent_signal_violation",
    "traffic_light_user": "user_signal",
    "traffic_light_opponent": "opponent_signal",
    "opponent_traffic_light_visible": "opponent_signal_visible",
    "traffic_signal_transition": "signal_transition",
    "signal_phase_transition": "signal_transition",
    "intersection_visible": "intersection",
    "pedestrian_crosswalk": "crosswalk_nearby",
    "pedestrian_in_crosswalk": "pedestrian_visible",
    "visible_pedestrian": "pedestrian_visible",
    "pedestrian_traffic_light": "pedestrian_signal",
    "child_victim": "victim_is_child",
    "crossed_centerline": "centerline_crossed",
    "yellow_centerline_crossed": "centerline_crossed",
    "centerline_reason": "centerline_cross_reason",
    "obstruction": "road_obstruction",
    "parked_vehicle_obstruction": "illegal_parking_obstruction",
    "oncoming_vehicle": "opposing_vehicle_present",
    "oncoming_vehicle_present": "opposing_vehicle_present",
    "oncoming_vehicle_did_not_stop": "opposing_vehicle_did_not_stop",
    "second_collision": "secondary_collision",
    "noncontact_trigger": "non_contact_trigger",
    "non_contact_cause": "non_contact_trigger",
    "trigger_actor": "trigger_actor_type",
    "trigger_object": "trigger_actor_type",
    "trigger_vehicle": "trigger_actor_type",
    "trigger_actor_motion": "trigger_actor_behavior",
    "actual_collision_partner": "direct_collision_partner_type",
    "direct_collision_partner": "direct_collision_partner_type",
    "rear_vehicle_impact": "rear_vehicle_collision",
    "rear_bus_collision": "rear_vehicle_collision",
    "collision_object_type": "collision_partner_type",
    "collision_target_type": "collision_partner_type",
    "collision_object": "primary_collision_target",
    "collision_target": "primary_collision_target",
    "impact_point_visible": "collision_point_visible",
    "impact_location": "collision_point_location",
    "lead_vehicle_stopped": "front_vehicle_stopped",
    "front_car_stopped": "front_vehicle_stopped",
    "vehicle_ahead_stopped": "front_vehicle_stopped",
    "turn_direction": "ego_turn_direction",
    "ego_turn": "ego_turn_direction",
    "ego_direction": "ego_turn_direction",
    "unlit_stopped_vehicle": "stopped_vehicle_without_lights",
    "dark_stopped_vehicle": "stopped_vehicle_without_lights",
    "expressway": "highway_or_expressway",
    "highway": "highway_or_expressway",
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
    supporting: list[dict[str, Any]] = []

    for raw in observations:
        observation = _normalize_observation(raw)
        if not observation:
            ignored.append({"reason": "unsupported_observation_shape"})
            continue
        field = str(observation["field"])
        confidence = observation.get("confidence")
        source = str(observation.get("source") or "")
        if field in _SUPPORTING_OBSERVATION_FIELDS:
            supporting.append({**observation, "reason": "supporting_observation_not_agent_fact"})
            continue
        if field not in _FACT_FIELDS:
            ignored.append({**observation, "reason": "field_not_in_agent_fact_contract"})
            continue
        if not _has_observation_source(source):
            uncertain.append({**_candidate_observation(observation, raw), "reason": "missing_observation_source"})
            continue
        passed, gate_reason, gate = _passes_fact_quality(observation)
        if not passed:
            uncertain.append({**_candidate_observation(observation, raw), "reason": gate_reason, "quality_gate": gate})
            continue
        value = _normalize_fact_value(field, observation.get("value"), raw)
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

    _demote_context_dependent_facts(fact_patch, accepted, uncertain)
    confirmation_candidates = _confirmation_candidates(uncertain)
    confirmation_groups = _confirmation_groups(accepted, confirmation_candidates)
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
        "supporting_observations": supporting,
        "ignored_observations": ignored,
        "confirmation_candidates": confirmation_candidates,
        "confirmation_groups": confirmation_groups,
        "observation_quality_summary": _quality_summary(accepted, uncertain, ignored, supporting, confirmation_candidates, confirmation_groups),
        "warnings": warnings,
        "fact_confidence_threshold": MIN_FACT_CONFIDENCE,
        "field_confidence_thresholds": FIELD_CONFIDENCE_THRESHOLDS,
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
    event_summary = _accident_event_summary(meta, nested)
    if event_summary:
        technical["accident_event_summary"] = event_summary
    frames = _frame_list(nested) or _frame_list(meta)
    if frames:
        technical["representative_frame_count"] = len(frames)
    return technical


def _accident_event_summary(meta: dict[str, Any], nested: dict[str, Any]) -> dict[str, Any]:
    for source in (nested, meta):
        if not isinstance(source, dict):
            continue
        frame_analysis = source.get("openai_frame_analysis")
        if not isinstance(frame_analysis, dict):
            continue
        event_summary = frame_analysis.get("accident_event_summary")
        if not isinstance(event_summary, dict):
            continue
        output = {
            "impact_visible": event_summary.get("impact_visible"),
            "event_frame_count": _safe_len(event_summary.get("event_frame_refs")),
            "pre_impact_frame_count": _safe_len(event_summary.get("pre_impact_frame_refs")),
            "post_impact_frame_count": _safe_len(event_summary.get("post_impact_frame_refs")),
        }
        return {key: value for key, value in output.items() if value not in (None, "", [], {})}
    return {}


def _safe_len(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


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
        direct = [(key, raw.get(key)) for key in _FACT_FIELDS.union(_FIELD_ALIASES).union(_SUPPORTING_OBSERVATION_FIELDS) if key in raw]
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
        "frame_refs": raw.get("frame_refs") or raw.get("frames") or [],
        "reason": raw.get("reason") or raw.get("evidence") or "",
    }


def _candidate_observation(observation: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    field = str(observation.get("field") or "")
    normalized_value = _normalize_fact_value(field, observation.get("value"), raw)
    if normalized_value is None:
        return observation
    if normalized_value == observation.get("value"):
        return observation
    return {**observation, "raw_value": observation.get("value"), "value": normalized_value}


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


def _passes_fact_quality(observation: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    field = str(observation.get("field") or "")
    confidence = observation.get("confidence")
    verified = observation.get("verified")
    source = str(observation.get("source") or "")
    threshold = FIELD_CONFIDENCE_THRESHOLDS.get(field, MIN_FACT_CONFIDENCE)
    frame_ref_count = _frame_ref_count(observation)
    needs_frame_ref = _requires_frame_ref(field, source)
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


def _requires_frame_ref(field: str, source: str) -> bool:
    return field in FRAME_REF_REQUIRED_FACT_FIELDS and source.split(":", 1)[0] in FRAME_REF_REQUIRED_SOURCES


def _frame_ref_count(observation: dict[str, Any]) -> int:
    refs = observation.get("frame_refs")
    return len(refs) if isinstance(refs, list) else 0


def _quality_summary(
    accepted: list[dict[str, Any]],
    uncertain: list[dict[str, Any]],
    ignored: list[dict[str, Any]],
    supporting: list[dict[str, Any]],
    confirmation_candidates: list[dict[str, Any]] | None = None,
    confirmation_groups: list[dict[str, Any]] | None = None,
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
    }


def _confirmation_candidates(uncertain: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
            "frame_ref_count": _frame_ref_count(item),
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


def _confirmation_groups(
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


def _normalize_fact_value(field: str, value: Any, raw: dict[str, Any]) -> Any:
    if field == "opponent_behavior":
        text = " ".join(str(item).lower() for item in (value, raw.get("raw_field"), raw.get("label")) if item is not None)
        if str(value).lower() in {"rear_collision", "lane_change", "signal_violation"}:
            return str(value).lower()
        if any(token in text for token in ("rear", "back", "behind", "rear_end")):
            return "rear_collision"
        if any(token in text for token in ("lane_change", "cut_in")):
            return "lane_change"
        if any(token in text for token in ("signal", "red_light")):
            return "signal_violation"
        return None
    if field == "lane_change_actor":
        text = str(value).lower()
        if text in {"opponent", "other", "target", "other_vehicle"}:
            return "opponent"
        if text in {"user", "ego", "self", "my_vehicle"}:
            return "user"
        return value if isinstance(value, str) and value.strip() else None
    if field == "collision_partner_type":
        return _normalize_actor_type(value)
    if field in {"trigger_actor_type", "direct_collision_partner_type"}:
        return _normalize_actor_type(value)
    if field == "trigger_actor_behavior":
        text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        if text in {"wrong_way", "reverse_direction", "opposite_direction", "sudden_entry", "sudden_appearance", "cut_in", "obstacle_avoidance", "stopped_obstruction"}:
            return text
        if any(token in text for token in ("wrong", "reverse", "opposite", "역주행", "역방향")):
            return "wrong_way"
        if any(token in text for token in ("sudden", "갑자기", "튀어나", "진입")):
            return "sudden_entry"
        if text and text != "unknown":
            return text
        return None
    if field in {"ego_turn_direction"}:
        text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        if text in {"right", "right_turn", "turn_right"}:
            return "right"
        if text in {"left", "left_turn", "turn_left"}:
            return "left"
        if text in {"straight", "go_straight", "forward"}:
            return "straight"
        if text in {"u_turn", "uturn"}:
            return "u_turn"
        return None
    if field in {"user_signal", "opponent_signal", "pedestrian_signal"}:
        return _normalize_signal(value)
    if field == "signal_transition":
        text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        if text in {"green_to_yellow", "yellow_to_red", "red_to_green", "green_to_red", "flashing", "none"}:
            return text
        return text if text and text != "unknown" else None
    if field in {"stopped", "sudden_brake", "opponent_signal_visible", "opponent_signal_violation", "intersection", "crosswalk_nearby", "pedestrian_visible", "school_zone", "victim_is_child", "injury", "centerline_crossed", "road_obstruction", "illegal_parking_obstruction", "opposing_vehicle_present", "opposing_vehicle_did_not_stop", "secondary_collision", "non_contact_trigger", "rear_vehicle_collision", "collision_point_visible", "front_vehicle_stopped", "stopped_vehicle_without_lights", "highway_or_expressway"}:
        return _as_bool(value)
    if isinstance(value, str):
        return value.strip() or None
    return value


def _normalize_signal(value: Any) -> str | None:
    text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    if text in {"green", "go", "blue", "green_light", "blue_light"}:
        return "green"
    if text in {"yellow", "amber", "yellow_light"}:
        return "yellow"
    if text in {"red", "stop", "red_light"}:
        return "red"
    if text in {"flashing", "blink", "blinking"}:
        return "flashing"
    if text in {"none", "no_signal", "not_visible"}:
        return "none"
    return text if text and text != "unknown" else None


def _normalize_actor_type(value: Any) -> str | None:
    text = str(value).strip().lower()
    if text in {"vehicle", "car", "truck", "bus", "van", "motor_vehicle", "other_vehicle"}:
        return "vehicle"
    if text in {"pedestrian", "person"}:
        return "pedestrian"
    if text in {"bicycle", "bike", "cyclist"}:
        return "bicycle"
    if text in {"motorcycle", "two_wheeler", "two-wheeler", "motorbike"}:
        return "motorcycle"
    if text in {"object", "fixed_object", "road_object", "obstacle"}:
        return "object"
    return None


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
