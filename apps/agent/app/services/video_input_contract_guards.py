from __future__ import annotations

from typing import Any


def apply_video_fact_guards(
    fact_patch: dict[str, Any],
    accepted: list[dict[str, Any]],
    uncertain: list[dict[str, Any]],
) -> None:
    guard_collision_partner_classification(fact_patch, accepted, uncertain)
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
    if partner != "pedestrian":
        return
    direct_partner = str(fact_patch.get("direct_collision_partner_type") or "").strip().lower()
    target_text = str(fact_patch.get("primary_collision_target") or "").strip().lower()
    has_direct_pedestrian_contact = direct_partner == "pedestrian"
    target_mentions_pedestrian = any(
        token in target_text for token in ("pedestrian", "person", "\ubcf4\ud589\uc790", "\uc0ac\ub78c")
    )
    if has_direct_pedestrian_contact or (fact_patch.get("collision_point_visible") is True and target_mentions_pedestrian):
        return
    move_accepted_to_uncertain(
        "collision_partner_type",
        fact_patch,
        accepted,
        uncertain,
        "pedestrian_collision_partner_requires_direct_contact_evidence",
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
