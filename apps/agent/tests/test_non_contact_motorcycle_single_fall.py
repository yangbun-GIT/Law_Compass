from app.services.analysts.fault_ratio_analyst import analyze_fault_ratio
from app.services.input_normalizer import normalize_analysis_input
from app.services.input_requirements import build_input_requirements
from app.services.scenario_classifier import classify_scenario


CASE_TEXT = (
    "Narrow curved road width 3.8m, speed limit 30. Ego dashcam car kept right. "
    "There was no direct contact with the ego vehicle. An oncoming motorcycle near the center "
    "fell alone after a near miss and failed to keep right."
)


def _normalized_case():
    return normalize_analysis_input(
        CASE_TEXT,
        structured_facts={
            "direct_contact_with_ego": False,
            "ego_collision_confirmed": False,
            "opponent_single_fall": True,
            "non_contact_near_miss": True,
            "opposing_motorcycle_present": True,
            "curve_road": True,
            "narrow_road": True,
            "road_width_m": 3.8,
            "ego_kept_right": True,
            "ego_vehicle_position": "right_edge",
            "opponent_vehicle_position": "center",
            "opponent_failed_keep_right": True,
            "opponent_speed_fast_claimed": True,
            "ego_speed_within_limit_claimed": True,
            "speed_limit_kmh": 30,
        },
        initial_intake={
            "accident_major_category": "car_vs_motorcycle",
            "preliminary_accident_type": "motorcycle_collision",
            "natural_language_description": CASE_TEXT,
        },
    )


def test_normalizer_preserves_non_contact_motorcycle_facts_over_initial_intake_defaults():
    normalized = _normalized_case()
    facts = normalized["structured_facts"]

    assert facts["direct_contact_with_ego"] is False
    assert facts["ego_collision_confirmed"] is False
    assert facts["opponent_single_fall"] is True
    assert facts["non_contact_near_miss"] is True
    assert facts["accident_party_type"] == "non_contact_involving_motorcycle"
    assert facts["scenario_type"] == "narrow_curve_oncoming_motorcycle_loss_of_control"
    assert facts["collision_partner_type"] == "opponent_motorcycle_nearby"
    assert "direct_collision_partner_type" not in facts
    assert facts["physical_contact_frame_refs"] == []


def test_non_contact_motorcycle_fault_ratio_returns_conditional_zero_to_one_hundred_candidate():
    normalized = _normalized_case()
    facts = normalized["structured_facts"]
    scenario = classify_scenario(CASE_TEXT, facts, [])

    fault = analyze_fault_ratio(
        scenario_type=scenario["scenario_type"],
        facts=facts,
        evidence=[],
        text=CASE_TEXT,
    )

    assert fault["fault_estimate_source"] == "non_contact_motorcycle_single_fall_rule"
    assert fault["my"] == 0
    assert fault["other"] == 100
    assert fault["fault_range"] == {"my": "0%", "other": "100%"}
    assert fault["conditional_outcomes"]
    assert "direct_contact_with_ego" not in fault.get("conditional_required_facts", [])


def test_non_contact_motorcycle_questions_avoid_irrelevant_signal_questions():
    normalized = _normalized_case()
    facts = normalized["structured_facts"]
    requirements = build_input_requirements(
        facts={key: value for key, value in facts.items() if key not in {"opponent_failed_keep_right"}},
        scenario_type="narrow_curve_oncoming_motorcycle_loss_of_control",
        missing_fields=["signal_state", "opponent_behavior"],
        description_text=CASE_TEXT,
        accident_party_type="non_contact_involving_motorcycle",
    )
    fields = [item["field"] for item in requirements["questions"]]

    assert "opponent_failed_keep_right" in fields
    assert "signal_state" not in fields
    assert "user_signal" not in fields
    assert "opponent_signal" not in fields
