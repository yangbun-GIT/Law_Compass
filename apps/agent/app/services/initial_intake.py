from __future__ import annotations

from typing import Any


VERSION = "agent-initial-intake-v1"
DESCRIPTION_LIMIT = 1200

PARTY_ALIASES = {
    "car_vs_motorcycle": "car_vs_two_wheeler",
    "car_vs_two_wheeler": "car_vs_two_wheeler",
    "car_vs_object": "single_vehicle",
}

CANONICAL_PARTY = {
    "car_vs_two_wheeler": "car_vs_motorcycle",
    "parking_or_stationary": "car_vs_car",
}

PARTY_DEFAULTS = {
    "car_vs_car": {
        "collision_partner_type": "vehicle",
        "direct_collision_partner_type": "vehicle",
        "excluded_knia_party_types": ["car_vs_person", "car_vs_bicycle", "car_vs_motorcycle", "car_vs_object", "single_vehicle"],
    },
    "car_vs_person": {
        "collision_partner_type": "pedestrian",
        "direct_collision_partner_type": "pedestrian",
        "excluded_knia_party_types": ["car_vs_car", "car_vs_bicycle", "car_vs_motorcycle", "car_vs_object", "single_vehicle"],
    },
    "car_vs_bicycle": {
        "collision_partner_type": "bicycle",
        "direct_collision_partner_type": "bicycle",
        "excluded_knia_party_types": ["car_vs_car", "car_vs_person", "car_vs_motorcycle", "car_vs_object", "single_vehicle"],
    },
    "car_vs_motorcycle": {
        "collision_partner_type": "motorcycle",
        "direct_collision_partner_type": "motorcycle",
        "excluded_knia_party_types": ["car_vs_car", "car_vs_person", "car_vs_bicycle", "car_vs_object", "single_vehicle"],
    },
    "single_vehicle": {
        "collision_partner_type": "none",
        "excluded_knia_party_types": ["car_vs_car", "car_vs_person", "car_vs_bicycle", "car_vs_motorcycle", "car_vs_object"],
    },
}


def normalize_initial_intake(
    payload: dict[str, Any] | None,
    *,
    structured_facts: dict[str, Any] | None = None,
    video_upload_id: str | None = None,
) -> dict[str, Any]:
    source = payload if isinstance(payload, dict) else {}
    facts = structured_facts if isinstance(structured_facts, dict) else {}
    provided = _has_initial_intake_payload(source, facts, video_upload_id)
    major = normalize_major_category(
        source.get("accident_major_category")
        or facts.get("initial_accident_major_category")
        or facts.get("selected_major_category")
    )
    preliminary = _safe_text(
        source.get("preliminary_accident_type")
        or facts.get("initial_preliminary_accident_type")
        or facts.get("selected_preliminary_accident_type")
        or "unknown"
    ) or "unknown"
    natural = _safe_text(source.get("natural_language_description") or "")[:DESCRIPTION_LIMIT]
    upload_id = _safe_text(video_upload_id or source.get("video_upload_id") or "")
    return {
        "version": VERSION,
        "provided": provided,
        "accident_major_category": major,
        "canonical_party_type": canonical_party_type(major),
        "preliminary_accident_type": preliminary if preliminary != "" else "unknown",
        **({"video_upload_id": upload_id} if upload_id else {}),
        **({"natural_language_description": natural} if natural else {}),
        "natural_language_policy": {
            "weight": "low",
            "source_type": "subjective_user_claim",
            "can_override_video": False,
            "can_override_structured_followup": False,
        },
    }


def build_fact_candidates_from_initial_intake(initial_intake: dict[str, Any] | None) -> dict[str, Any]:
    intake = initial_intake if isinstance(initial_intake, dict) else {}
    if not intake.get("provided"):
        return {}
    major = normalize_major_category(intake.get("accident_major_category"))
    party = canonical_party_type(major)
    preliminary = _safe_text(intake.get("preliminary_accident_type") or "unknown") or "unknown"
    patch: dict[str, Any] = {}
    if major != "unknown":
        patch["initial_accident_major_category"] = major
        patch["selected_major_category"] = major
    if party != "unknown":
        patch["accident_party_type"] = party
        patch["knia_major_party_type"] = party
        patch.update(PARTY_DEFAULTS.get(party, {}))
    if preliminary and preliminary != "unknown":
        patch["initial_preliminary_accident_type"] = preliminary
        patch["selected_preliminary_accident_type"] = preliminary
        patch["accident_type"] = preliminary
    if major == "parking_or_stationary":
        patch["accident_party_type"] = "car_vs_car"
        patch["knia_major_party_type"] = "car_vs_car"
        patch["is_parked_vehicle_collision"] = True
        patch.setdefault("accident_type", "parking_or_stopped_vehicle_accident")
        patch.update(PARTY_DEFAULTS["car_vs_car"])
    return patch


def enforce_initial_intake_priority(facts: dict[str, Any], initial_intake: dict[str, Any] | None) -> dict[str, Any]:
    intake = initial_intake if isinstance(initial_intake, dict) else {}
    if not intake.get("provided"):
        return facts
    major = normalize_major_category(intake.get("accident_major_category"))
    if major == "unknown":
        return facts
    patch = build_fact_candidates_from_initial_intake(intake)
    protected = {
        "initial_accident_major_category",
        "selected_major_category",
        "initial_preliminary_accident_type",
        "selected_preliminary_accident_type",
        "accident_party_type",
        "knia_major_party_type",
        "collision_partner_type",
        "direct_collision_partner_type",
        "excluded_knia_party_types",
    }
    merged = dict(facts)
    for key in protected:
        if key in patch:
            merged[key] = patch[key]
    if patch.get("accident_type") and patch.get("accident_type") != "unknown":
        merged.setdefault("accident_type", patch["accident_type"])
    if major == "parking_or_stationary":
        merged["is_parked_vehicle_collision"] = True
    return merged


def normalize_major_category(value: Any) -> str:
    raw = _safe_text(value)
    if not raw:
        return "unknown"
    return PARTY_ALIASES.get(raw, raw)


def canonical_party_type(value: Any) -> str:
    major = normalize_major_category(value)
    return CANONICAL_PARTY.get(major, major)


def _safe_text(value: Any) -> str:
    return str(value or "").replace("\x00", "").strip()


def _has_initial_intake_payload(
    source: dict[str, Any],
    facts: dict[str, Any],
    video_upload_id: str | None = None,
) -> bool:
    keys = (
        "accident_major_category",
        "preliminary_accident_type",
        "natural_language_description",
        "video_upload_id",
    )
    fact_keys = (
        "initial_accident_major_category",
        "selected_major_category",
        "initial_preliminary_accident_type",
        "selected_preliminary_accident_type",
    )
    return any(_safe_text(source.get(key)) for key in keys) or any(_safe_text(facts.get(key)) for key in fact_keys) or bool(_safe_text(video_upload_id))
