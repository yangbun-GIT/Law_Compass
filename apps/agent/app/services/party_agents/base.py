from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


PARTY_TYPES = {
    "car_vs_car",
    "car_vs_person",
    "car_vs_bicycle",
    "car_vs_motorcycle",
    "car_vs_object",
    "single_vehicle",
    "unknown",
}


PARTY_TO_COLLISION_PARTNER = {
    "car_vs_car": "vehicle",
    "car_vs_person": "pedestrian",
    "car_vs_bicycle": "bicycle",
    "car_vs_motorcycle": "motorcycle",
    "car_vs_object": "object",
    "single_vehicle": "none",
}


@dataclass
class PartyAgentResult:
    major_party_type: str = "unknown"
    scenario_type: str = "general_collision"
    scenario_subtype: str | None = None
    collision_partner_type: str | None = None
    direct_collision_partner_type: str | None = None
    confidence: float = 0.0
    facts_patch: dict[str, Any] = field(default_factory=dict)
    scenario_tags: list[str] = field(default_factory=list)
    question_profile: dict[str, Any] = field(default_factory=dict)
    knia_query_profile: dict[str, Any] = field(default_factory=dict)
    excluded_party_types: list[str] = field(default_factory=list)
    reason: str = "no_party_signal"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["major_party_type"] = canonical_party(data.get("major_party_type"))
        data["facts_patch"] = {k: v for k, v in data["facts_patch"].items() if v is not None}
        return data


class BasePartyAgent:
    major_party_type = "unknown"
    default_scenario = "general_collision"
    default_tags: tuple[str, ...] = ()

    def build_result(
        self,
        *,
        confidence: float,
        reason: str,
        scenario_type: str | None = None,
        scenario_subtype: str | None = None,
        facts_patch: dict[str, Any] | None = None,
        scenario_tags: list[str] | None = None,
    ) -> PartyAgentResult:
        party = canonical_party(self.major_party_type)
        partner = PARTY_TO_COLLISION_PARTNER.get(party)
        patch = {
            "knia_major_party_type": party,
            "accident_party_type": party,
            "collision_partner_type": partner,
            "direct_collision_partner_type": partner,
            **(facts_patch or {}),
        }
        if party == "single_vehicle":
            patch.pop("direct_collision_partner_type", None)
        excluded = sorted(PARTY_TYPES - {party, "unknown"})
        tags = list(dict.fromkeys([*self.default_tags, *(scenario_tags or [])]))
        return PartyAgentResult(
            major_party_type=party,
            scenario_type=scenario_type or self.default_scenario,
            scenario_subtype=scenario_subtype,
            collision_partner_type=patch.get("collision_partner_type"),
            direct_collision_partner_type=patch.get("direct_collision_partner_type"),
            confidence=confidence,
            facts_patch=patch,
            scenario_tags=tags,
            question_profile={"party_type": party, "scenario_type": scenario_type or self.default_scenario},
            knia_query_profile={"party_type": party, "excluded_party_types": excluded},
            excluded_party_types=excluded,
            reason=reason,
        )


def canonical_party(value: Any) -> str:
    text = str(value or "").strip().lower()
    aliases = {
        "vehicle": "car_vs_car",
        "car": "car_vs_car",
        "truck": "car_vs_car",
        "bus": "car_vs_car",
        "parked_vehicle": "car_vs_car",
        "stopped_vehicle": "car_vs_car",
        "car_vs_parked_vehicle": "car_vs_car",
        "vehicle_vs_vehicle": "car_vs_car",
        "person": "car_vs_person",
        "pedestrian": "car_vs_person",
        "vehicle_vs_pedestrian": "car_vs_person",
        "bike": "car_vs_bicycle",
        "bicycle": "car_vs_bicycle",
        "cyclist": "car_vs_bicycle",
        "vehicle_vs_bicycle": "car_vs_bicycle",
        "motorcycle": "car_vs_motorcycle",
        "two_wheeler": "car_vs_motorcycle",
        "motorbike": "car_vs_motorcycle",
        "object": "car_vs_object",
        "fixed_object": "car_vs_object",
        "road_object": "car_vs_object",
        "single": "single_vehicle",
        "vehicle_single": "single_vehicle",
    }
    mapped = aliases.get(text, text)
    return mapped if mapped in PARTY_TYPES else "unknown"

