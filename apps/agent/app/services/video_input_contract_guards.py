from __future__ import annotations

from typing import Any


def apply_video_fact_guards(
    fact_patch: dict[str, Any],
    accepted: list[dict[str, Any]],
    uncertain: list[dict[str, Any]],
) -> None:
    guard_collision_partner_classification(fact_patch, accepted, uncertain)
    guard_object_presence_pollution(fact_patch, accepted, uncertain)
    guard_signal_pollution(fact_patch, accepted, uncertain)
    guard_centerline_pollution(fact_patch, accepted, uncertain)
    align_collision_partner_from_direct_contact(fact_patch, accepted, uncertain)
    demote_context_dependent_facts(fact_patch, accepted, uncertain)


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
    if partner not in {"pedestrian", "bicycle", "object"}:
        return
    direct_partner = str(fact_patch.get("direct_collision_partner_type") or "").strip().lower()
    target_text = str(fact_patch.get("primary_collision_target") or "").strip().lower()
    has_direct_contact = direct_partner == partner
    target_mentions_partner = any(
        token in target_text for token in collision_partner_tokens(partner)
    )
    if has_direct_contact or (fact_patch.get("collision_point_visible") is True and target_mentions_partner):
        return
    move_accepted_to_uncertain(
        "collision_partner_type",
        fact_patch,
        accepted,
        uncertain,
        f"{partner}_collision_partner_requires_direct_contact_evidence",
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
    if partner == "object":
        return ("object", "obstacle", "barrier", "median", "debris", "\uc7a5\uc560\ubb3c", "\ub099\ud558\ubb3c", "\uc911\uc559\ubd84\ub9ac\ub300")
    return (partner,)
