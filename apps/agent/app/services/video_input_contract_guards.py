from __future__ import annotations

from typing import Any

TARGET_FACT_FIELDS = {
    "primary_collision_target",
    "collision_partner_type",
    "direct_collision_partner_type",
}
CANONICAL_TARGETS = {"vehicle", "pedestrian", "bicycle", "motorcycle", "object"}
NON_VEHICLE_TARGETS = {"pedestrian", "bicycle", "motorcycle", "object"}


def apply_video_fact_guards(
    fact_patch: dict[str, Any],
    accepted: list[dict[str, Any]],
    uncertain: list[dict[str, Any]],
) -> None:
    guard_collision_partner_classification(fact_patch, accepted, uncertain)
    guard_ego_vehicle_partner_pollution(fact_patch, accepted, uncertain)
    guard_candidate_target_values(fact_patch, accepted, uncertain)
    guard_object_presence_pollution(fact_patch, accepted, uncertain)
    guard_signal_pollution(fact_patch, accepted, uncertain)
    guard_centerline_pollution(fact_patch, accepted, uncertain)
    align_collision_partner_from_direct_contact(fact_patch, accepted, uncertain)
    guard_target_fact_consensus(fact_patch, accepted, uncertain)
    demote_context_dependent_facts(fact_patch, accepted, uncertain)


def guard_candidate_target_values(
    fact_patch: dict[str, Any],
    accepted: list[dict[str, Any]],
    uncertain: list[dict[str, Any]],
) -> None:
    for field in TARGET_FACT_FIELDS:
        value = str(fact_patch.get(field) or "").strip().lower()
        if value.endswith("_candidate"):
            move_accepted_to_uncertain(
                field,
                fact_patch,
                accepted,
                uncertain,
                f"{field}_candidate_requires_direct_contact_evidence",
            )


def guard_target_fact_consensus(
    fact_patch: dict[str, Any],
    accepted: list[dict[str, Any]],
    uncertain: list[dict[str, Any]],
) -> None:
    for field in list(TARGET_FACT_FIELDS):
        target = target_value(fact_patch.get(field))
        if target not in CANONICAL_TARGETS:
            continue
        if not has_sourced_target_observation(field, target, accepted):
            continue
        if has_manual_or_verified_target(field, target, accepted):
            continue
        if target == "vehicle":
            if field == "direct_collision_partner_type" and fact_patch.get("collision_point_visible") is True:
                continue
            if has_vehicle_collision_context(fact_patch) and not has_competing_non_vehicle_target(target, accepted, uncertain):
                continue
            if (
                field in TARGET_FACT_FIELDS
                and fact_patch.get("collision_point_visible") is True
                and not has_competing_non_vehicle_target(target, accepted, uncertain)
            ):
                continue
            move_accepted_to_uncertain(
                field,
                fact_patch,
                accepted,
                uncertain,
                f"{field}_vehicle_target_requires_collision_context_or_user_confirmation",
            )
            continue
        if has_non_vehicle_target_support(target, accepted, uncertain):
            continue
        if has_single_source_contact_bundle(target, accepted, uncertain):
            continue
        move_accepted_to_uncertain(
            field,
            fact_patch,
            accepted,
            uncertain,
            f"{field}_{target}_requires_cross_model_or_multi_frame_contact_support",
        )


def demote_context_dependent_facts(
    fact_patch: dict[str, Any],
    accepted: list[dict[str, Any]],
    uncertain: list[dict[str, Any]],
) -> None:
    if fact_patch.get("ego_turn_direction") in {"left", "right", "u_turn"} and not any(
        fact_patch.get(field) is True for field in ("intersection", "crosswalk_nearby")
    ):
        move_accepted_to_uncertain(
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
            move_accepted_to_uncertain(
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
            move_accepted_to_uncertain(
                "pedestrian_visible",
                fact_patch,
                accepted,
                uncertain,
                "pedestrian_presence_is_context_when_collision_partner_is_vehicle",
            )
        if fact_patch.get("pedestrian_signal") is not None:
            move_accepted_to_uncertain(
                "pedestrian_signal",
                fact_patch,
                accepted,
                uncertain,
                "pedestrian_signal_is_context_when_collision_partner_is_vehicle",
            )


def guard_collision_partner_classification(
    fact_patch: dict[str, Any],
    accepted: list[dict[str, Any]],
    uncertain: list[dict[str, Any]],
) -> None:
    partner = str(fact_patch.get("collision_partner_type") or "").strip().lower()
    if partner not in {"pedestrian", "bicycle", "motorcycle", "object"}:
        return
    direct_partner = str(fact_patch.get("direct_collision_partner_type") or "").strip().lower()
    target_text = str(fact_patch.get("primary_collision_target") or "").strip().lower()
    has_direct_contact = direct_partner == partner
    target_mentions_partner = any(
        token in target_text for token in collision_partner_tokens(partner)
    )
    if (
        has_direct_contact
        or (fact_patch.get("collision_point_visible") is True and target_mentions_partner)
        or has_single_source_contact_bundle(partner, accepted, uncertain)
    ):
        return
    move_accepted_to_uncertain(
        "collision_partner_type",
        fact_patch,
        accepted,
        uncertain,
        f"{partner}_collision_partner_requires_direct_contact_evidence",
    )


def guard_ego_vehicle_partner_pollution(
    fact_patch: dict[str, Any],
    accepted: list[dict[str, Any]],
    uncertain: list[dict[str, Any]],
) -> None:
    partner = str(fact_patch.get("collision_partner_type") or "").strip().lower()
    direct_partner = str(fact_patch.get("direct_collision_partner_type") or "").strip().lower()
    target = str(fact_patch.get("primary_collision_target") or "").strip().lower()
    if partner == "vehicle" and direct_partner in NON_VEHICLE_TARGETS:
        move_accepted_to_uncertain(
            "collision_partner_type",
            fact_patch,
            accepted,
            uncertain,
            "collision_partner_vehicle_conflicts_with_non_vehicle_direct_contact",
        )
        return
    if partner == "vehicle" and target in NON_VEHICLE_TARGETS:
        move_accepted_to_uncertain(
            "collision_partner_type",
            fact_patch,
            accepted,
            uncertain,
            "collision_partner_vehicle_conflicts_with_non_vehicle_primary_target",
        )


def guard_object_presence_pollution(
    fact_patch: dict[str, Any],
    accepted: list[dict[str, Any]],
    uncertain: list[dict[str, Any]],
) -> None:
    target_text = str(fact_patch.get("primary_collision_target") or "").strip().lower()
    if "candidate" in target_text:
        move_accepted_to_uncertain(
            "primary_collision_target",
            fact_patch,
            accepted,
            uncertain,
            "primary_collision_target_candidate_requires_contact_evidence",
        )

    if fact_patch.get("stopped_vehicle_without_lights") is True and not has_contact_or_target_context(
        fact_patch,
        ("vehicle", "car", "truck", "bus", "van", "\ucc28\ub7c9", "\uc790\ub3d9\ucc28"),
    ):
        move_accepted_to_uncertain(
            "stopped_vehicle_without_lights",
            fact_patch,
            accepted,
            uncertain,
            "unlit_stopped_vehicle_requires_collision_target_context",
        )

    if (
        fact_patch.get("front_vehicle_stopped") is True
        and fact_patch.get("rear_vehicle_collision") is not True
        and fact_patch.get("crosswalk_nearby") is not True
        and fact_patch.get("intersection") is not True
    ):
        location = str(fact_patch.get("collision_point_location") or "")
        if location not in {"front_rear", "rear", "rear_end"} and fact_patch.get("collision_point_visible") is not True:
            move_accepted_to_uncertain(
                "front_vehicle_stopped",
                fact_patch,
                accepted,
                uncertain,
                "front_vehicle_stop_requires_collision_or_rear_end_context",
            )

    if fact_patch.get("non_contact_trigger") is True and not (
        fact_patch.get("trigger_actor_type") or fact_patch.get("trigger_actor_behavior")
    ):
        move_accepted_to_uncertain(
            "non_contact_trigger",
            fact_patch,
            accepted,
            uncertain,
            "non_contact_trigger_requires_trigger_actor_or_behavior",
        )


def guard_signal_pollution(
    fact_patch: dict[str, Any],
    accepted: list[dict[str, Any]],
    uncertain: list[dict[str, Any]],
) -> None:
    if fact_patch.get("opponent_signal_violation") is True:
        has_signal_basis = (
            fact_patch.get("opponent_signal_visible") is True
            and fact_patch.get("opponent_signal") not in {None, "", "unknown", "none"}
        )
        has_transition_basis = fact_patch.get("signal_transition") not in {None, "", "unknown", "none"}
        if not (has_signal_basis or has_transition_basis):
            move_accepted_to_uncertain(
                "opponent_signal_violation",
                fact_patch,
                accepted,
                uncertain,
                "signal_violation_requires_signal_state_or_transition_context",
            )

    if fact_patch.get("opponent_signal") not in {None, "", "unknown", "none"} and fact_patch.get("opponent_signal_visible") is False:
        move_accepted_to_uncertain(
            "opponent_signal",
            fact_patch,
            accepted,
            uncertain,
            "opponent_signal_requires_visible_opponent_signal_context",
        )

    if fact_patch.get("pedestrian_signal") not in {None, "", "unknown", "none"} and not (
        fact_patch.get("crosswalk_nearby") is True or fact_patch.get("pedestrian_visible") is True
    ):
        move_accepted_to_uncertain(
            "pedestrian_signal",
            fact_patch,
            accepted,
            uncertain,
            "pedestrian_signal_requires_crosswalk_or_pedestrian_context",
        )


def guard_centerline_pollution(
    fact_patch: dict[str, Any],
    accepted: list[dict[str, Any]],
    uncertain: list[dict[str, Any]],
) -> None:
    if fact_patch.get("centerline_crossed") is not True:
        return
    has_context = any(
        fact_patch.get(field) not in {None, "", False, "unknown"}
        for field in (
            "centerline_cross_reason",
            "road_obstruction",
            "illegal_parking_obstruction",
            "opposing_vehicle_present",
            "opposing_vehicle_did_not_stop",
            "secondary_collision",
        )
    )
    if not has_context:
        move_accepted_to_uncertain(
            "centerline_crossed",
            fact_patch,
            accepted,
            uncertain,
            "centerline_crossing_requires_actor_reason_or_road_context",
        )


def align_collision_partner_from_direct_contact(
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
        move_accepted_to_uncertain(
            "collision_partner_type",
            fact_patch,
            accepted,
            uncertain,
            "direct_collision_partner_overrides_broader_collision_partner",
        )
    fact_patch["collision_partner_type"] = direct_partner


def has_manual_or_verified_target(field: str, target: str, accepted: list[dict[str, Any]]) -> bool:
    for item in accepted:
        if item.get("field") != field or target_value(item.get("value")) != target:
            continue
        source = str(item.get("source") or "").split(":", 1)[0]
        if item.get("verified") is True or source == "manual_video_review":
            return True
    return False


def has_sourced_target_observation(field: str, target: str, accepted: list[dict[str, Any]]) -> bool:
    for item in accepted:
        if item.get("field") == field and target_value(item.get("value")) == target and source_family(item):
            return True
    return False


def has_vehicle_collision_context(fact_patch: dict[str, Any]) -> bool:
    if fact_patch.get("rear_vehicle_collision") is True:
        return True
    if fact_patch.get("front_vehicle_stopped") is True:
        return True
    if fact_patch.get("opposing_vehicle_present") is True:
        return True
    if fact_patch.get("lane_change_actor") in {"user", "opponent"}:
        return True
    if fact_patch.get("opponent_behavior") in {"rear_collision", "lane_change", "signal_violation"}:
        return True
    if fact_patch.get("centerline_crossed") is True and (
        fact_patch.get("opposing_vehicle_present") is True or fact_patch.get("road_obstruction") is True
    ):
        return True
    return False


def has_competing_non_vehicle_target(
    target: str,
    accepted: list[dict[str, Any]],
    uncertain: list[dict[str, Any]],
) -> bool:
    for item in [*accepted, *uncertain]:
        if str(item.get("field") or "") not in TARGET_FACT_FIELDS:
            continue
        other_target = target_value(item.get("value"))
        if other_target in NON_VEHICLE_TARGETS and other_target != target and frame_ref_count(item) >= 2:
            return True
    return False


def has_non_vehicle_target_support(
    target: str,
    accepted: list[dict[str, Any]],
    uncertain: list[dict[str, Any]],
) -> bool:
    quality_sources: set[str] = set()
    frame_refs: set[str] = set()
    for item in [*accepted, *uncertain]:
        if str(item.get("field") or "") not in TARGET_FACT_FIELDS:
            continue
        if target_value(item.get("value")) != target:
            continue
        source = source_family(item)
        refs = item.get("frame_refs")
        if isinstance(refs, list):
            frame_refs.update(str(ref) for ref in refs if ref)
        confidence = as_float(item.get("confidence"))
        if confidence >= 0.74 and frame_ref_count(item) >= 2:
            quality_sources.add(source)
    return len(quality_sources) >= 2 and len(frame_refs) >= 2


def has_single_source_contact_bundle(
    target: str,
    accepted: list[dict[str, Any]],
    uncertain: list[dict[str, Any]],
) -> bool:
    """Allow one vision model to pass only when it reports a full contact bundle."""
    items = [*accepted, *uncertain]
    by_source: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        source = source_family(item)
        if not source or source == "vision_model:yolo":
            continue
        by_source.setdefault(source, []).append(item)

    for source_items in by_source.values():
        target_items = [
            item
            for item in source_items
            if str(item.get("field") or "") in TARGET_FACT_FIELDS
            and target_value(item.get("value")) == target
            and not str(item.get("value") or "").strip().lower().endswith("_candidate")
            and as_float(item.get("confidence")) >= 0.72
            and frame_ref_count(item) >= 2
        ]
        if not target_items:
            continue
        target_fields = {str(item.get("field") or "") for item in target_items}
        contact_items = [
            item
            for item in source_items
            if item.get("field") == "collision_point_visible"
            and item.get("value") is True
            and as_float(item.get("confidence")) >= 0.78
            and frame_ref_count(item) >= 2
        ]
        if not contact_items:
            continue
        target_refs = union_frame_refs(target_items)
        contact_refs = union_frame_refs(contact_items)
        if len(target_refs & contact_refs) < 1:
            continue
        if "collision_partner_type" in target_fields and (
            "primary_collision_target" in target_fields
            or "direct_collision_partner_type" in target_fields
        ):
            return True
        if any(as_float(item.get("confidence")) >= 0.88 for item in target_items):
            return True
    return False


def target_value(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text.endswith("_candidate"):
        text = text[: -len("_candidate")]
    if text in {"vehicle", "car", "truck", "bus", "van", "motor_vehicle", "other_vehicle"}:
        return "vehicle"
    if text in {"pedestrian", "person"}:
        return "pedestrian"
    if text in {"bicycle", "bike", "cyclist"}:
        return "bicycle"
    if text in {"motorcycle", "motorbike", "scooter", "moped", "two_wheeler", "two-wheeler"}:
        return "motorcycle"
    if text in {"object", "fixed_object", "road_object", "obstacle"}:
        return "object"
    return text


def source_family(item: dict[str, Any]) -> str:
    source = str(item.get("source") or "").strip().lower()
    if not source:
        return ""
    if "yolo" in source:
        return "vision_model:yolo"
    return source.split(":", 1)[0]


def frame_ref_count(item: dict[str, Any]) -> int:
    refs = item.get("frame_refs")
    return len(refs) if isinstance(refs, list) else 0


def union_frame_refs(items: list[dict[str, Any]]) -> set[str]:
    refs: set[str] = set()
    for item in items:
        value = item.get("frame_refs")
        if isinstance(value, list):
            refs.update(str(ref) for ref in value if ref)
    return refs


def as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def move_accepted_to_uncertain(
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


def has_contact_or_target_context(fact_patch: dict[str, Any], target_tokens: tuple[str, ...]) -> bool:
    if fact_patch.get("collision_point_visible") is True:
        return True
    if fact_patch.get("direct_collision_partner_type") == "vehicle":
        return True
    if fact_patch.get("collision_partner_type") == "vehicle":
        return True
    target_text = str(fact_patch.get("primary_collision_target") or "").strip().lower()
    return any(token in target_text for token in target_tokens)


def collision_partner_tokens(partner: str) -> tuple[str, ...]:
    if partner == "pedestrian":
        return ("pedestrian", "person", "\ubcf4\ud589\uc790", "\uc0ac\ub78c")
    if partner == "bicycle":
        return ("bicycle", "bike", "cyclist", "\uc790\uc804\uac70")
    if partner == "motorcycle":
        return ("motorcycle", "motorbike", "scooter", "moped", "two_wheeler", "two-wheeler", "\uc624\ud1a0\ubc14\uc774", "\uc774\ub95c\ucc28")
    if partner == "object":
        return ("object", "obstacle", "barrier", "median", "debris", "\uc7a5\uc560\ubb3c", "\ub099\ud558\ubb3c", "\uc911\uc559\ubd84\ub9ac\ub300")
    return (partner,)
