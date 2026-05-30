from app.services.dynamic_questionnaire import build_dynamic_questionnaire
from app.services.input_normalizer import normalize_analysis_input


def test_initial_intake_sets_party_guard_before_natural_language_claim():
    normalized = normalize_analysis_input(
        "횡단보도 근처 사람이 보였지만 실제 충돌은 차량과 차량 사이입니다.",
        structured_facts={},
        initial_intake={
            "accident_major_category": "car_vs_car",
            "preliminary_accident_type": "lane_change_collision",
            "natural_language_description": "횡단보도 근처 사람이 보였습니다.",
        },
    )

    facts = normalized["structured_facts"]
    assert facts["accident_party_type"] == "car_vs_car"
    assert facts["knia_major_party_type"] == "car_vs_car"
    assert facts["selected_major_category"] == "car_vs_car"
    assert normalized["initial_intake_summary"]["natural_language_used_as"] == "low_weight_supporting_claim"
    assert normalized["fact_source_weights"]["field_sources"]["natural_language_description"]["can_override_video"] is False


def test_two_wheeler_alias_is_kept_in_intake_and_canonicalized_for_agent_party():
    normalized = normalize_analysis_input(
        "",
        structured_facts={},
        initial_intake={
            "accident_major_category": "car_vs_two_wheeler",
            "preliminary_accident_type": "intersection_collision",
        },
    )

    facts = normalized["structured_facts"]
    assert normalized["initial_intake"]["accident_major_category"] == "car_vs_two_wheeler"
    assert facts["accident_party_type"] == "car_vs_motorcycle"
    assert facts["collision_partner_type"] == "motorcycle"


def test_dynamic_questionnaire_skips_already_answered_structured_facts_and_limits_count():
    questionnaire = build_dynamic_questionnaire(
        scenario_type="lane_change_collision",
        accident_party_type="car_vs_car",
        analysis_mode="expert",
        structured_facts={"lane_change_actor": "opponent"},
    )

    fields = [item["fact_key"] for item in questionnaire["questions"]]
    assert "lane_change_actor" not in fields
    assert len(questionnaire["questions"]) <= 6
    assert all(any(choice["value"] == "unknown" for choice in item["choices"]) for item in questionnaire["questions"])
