from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.evidence_quality_gate import evaluate_evidence_quality
from app.services.rag_client import retrieve_for_scenario


@dataclass(frozen=True)
class EvidenceSearchScenario:
    name: str
    scenario_type: str
    scenario_tags: list[str]
    facts: dict[str, Any]
    description_text: str
    required_terms: tuple[str, ...]


SCENARIOS = [
    EvidenceSearchScenario(
        name="rear_end",
        scenario_type="rear_end_collision",
        scenario_tags=["rear_end"],
        facts={
            "stopped": True,
            "opponent_behavior": "rear_collision",
            "damage_level": "minor_rear_bumper_damage",
        },
        description_text="정차 중 뒤차가 추돌한 사고입니다.",
        required_terms=("후미추돌", "안전거리", "정차 차량 추돌"),
    ),
    EvidenceSearchScenario(
        name="opponent_lane_change",
        scenario_type="lane_change_collision",
        scenario_tags=["lane_change"],
        facts={"lane_change_actor": "opponent"},
        description_text="상대 차량이 차선변경 중 접촉했습니다.",
        required_terms=("차선변경", "상대 차량 차선변경", "방향지시등"),
    ),
    EvidenceSearchScenario(
        name="intersection_signal_violation",
        scenario_type="intersection_signal_violation",
        scenario_tags=["intersection", "signal_violation"],
        facts={"opponent_signal_violation": True, "opponent_signal": "red"},
        description_text="교차로에서 상대 차량이 적색신호를 위반했습니다.",
        required_terms=("교차로", "신호위반", "상대 신호위반"),
    ),
    EvidenceSearchScenario(
        name="pedestrian_crosswalk",
        scenario_type="pedestrian_crosswalk_accident",
        scenario_tags=["pedestrian"],
        facts={"crosswalk_nearby": True, "injury": True},
        description_text="횡단보도 주변에서 보행자와 충돌했습니다.",
        required_terms=("보행자", "횡단보도", "보행자 보호의무"),
    ),
    EvidenceSearchScenario(
        name="school_zone_child",
        scenario_type="school_zone_child_accident",
        scenario_tags=["school_zone", "child_protection"],
        facts={"school_zone": True, "victim_is_child": True},
        description_text="어린이보호구역에서 어린이와 사고가 났습니다.",
        required_terms=("어린이보호구역", "어린이", "제한속도"),
    ),
    EvidenceSearchScenario(
        name="bicycle",
        scenario_type="bicycle_collision",
        scenario_tags=["bicycle"],
        facts={"accident_party_type": "car_vs_bicycle", "bicycle_location": "crosswalk"},
        description_text="자전거와 차량이 충돌했습니다.",
        required_terms=("자전거", "차대 자전거", "자전거 통행 위치"),
    ),
    EvidenceSearchScenario(
        name="centerline_obstacle_secondary_collision",
        scenario_type="parking_or_stopped_vehicle_accident",
        scenario_tags=["centerline", "stopped_vehicle", "secondary_collision"],
        facts={
            "centerline_crossed": True,
            "centerline_cross_reason": "parked vehicle avoidance",
            "secondary_collision": True,
            "stopped": True,
        },
        description_text="The vehicle crossed the centerline to avoid a parked car, stopped, then had an oncoming collision and a secondary rear-end collision.",
        required_terms=("centerline obstacle avoidance", "oncoming vehicle collision", "secondary collision"),
    ),
    EvidenceSearchScenario(
        name="unlit_stopped_vehicle_avoidability",
        scenario_type="parking_or_stopped_vehicle_accident",
        scenario_tags=["stopped_vehicle", "visibility", "speed"],
        facts={
            "stopped_vehicle_without_lights": True,
            "light_condition": "night",
            "speed_limit_kmh": 100,
            "reported_speed_kmh": 141,
            "fatality": True,
        },
        description_text="At night the vehicle hit an unlit stopped vehicle. Speed and avoidability at the legal speed are disputed.",
        required_terms=("unlit stopped vehicle", "avoidability analysis", "criminal civil liability split"),
    ),
    EvidenceSearchScenario(
        name="bicycle_non_contact_trigger_bus_rear_end",
        scenario_type="bicycle_collision",
        scenario_tags=["bicycle", "non_contact_trigger", "rear_end"],
        facts={
            "bicycle_involved": True,
            "possible_trigger_vehicle": "bicycle",
            "stopped": True,
            "sudden_brake": True,
            "time_gap_sec": 4,
        },
        description_text="A truck stopped after a bicycle came from the bus side, then a bus hit the truck from behind.",
        required_terms=("non-contact bicycle trigger", "rear-end after bicycle avoidance", "reaction time gap"),
    ),
]


def main() -> None:
    for scenario in SCENARIOS:
        result = retrieve_for_scenario(
            scenario_type=scenario.scenario_type,
            scenario_tags=scenario.scenario_tags,
            description_text=scenario.description_text,
            facts=scenario.facts,
            selected_keywords=[],
            limit=8,
        )
        evidence = result.get("items") or []
        query_terms = result.get("query_expansion_terms") or []
        quality = evaluate_evidence_quality(
            scenario_type=scenario.scenario_type,
            evidence=evidence,
            missing_fields=[],
        )

        missing_terms = [term for term in scenario.required_terms if term not in query_terms]
        missing_families = quality.get("missing_evidence_families") or []
        missing_requirements = quality.get("missing_requirements") or []
        relevant_count = int(quality.get("scenario_relevant_count") or 0)
        level = str(quality.get("coverage_level") or "")

        assert not missing_terms, f"{scenario.name}: missing query terms {missing_terms}; terms={query_terms}"
        assert "family:legal" not in missing_requirements, f"{scenario.name}: legal family missing; {quality}"
        assert "family:knia" not in missing_requirements, f"{scenario.name}: knia family missing; {quality}"
        assert not missing_families, f"{scenario.name}: required evidence families missing; {quality}"
        assert relevant_count >= 2, f"{scenario.name}: expected at least 2 relevant evidence items; {quality}"
        assert level in {"medium", "high"}, f"{scenario.name}: evidence coverage too low; {quality}"

        print(
            "PASS"
            f" {scenario.name}"
            f" scenario={scenario.scenario_type}"
            f" evidence={len(evidence)}"
            f" relevant={relevant_count}"
            f" coverage={level}"
            f" families={quality.get('evidence_family_counts')}"
        )


if __name__ == "__main__":
    main()
