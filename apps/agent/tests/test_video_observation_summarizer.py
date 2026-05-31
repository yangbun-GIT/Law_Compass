from app.services.scenario_classifier import classify_scenario
from app.services.video_input_contract_guards import apply_video_fact_guards
from app.services.video_observation_summarizer import build_video_scene_summary


def test_video_scene_summary_uses_visual_facts_without_asserting_ambiguous_child_or_speed():
    video_contract = {
        "fact_patch": {
            "ego_vehicle_type": "motorcycle",
            "direct_collision_partner_type": "bicycle",
            "school_zone": True,
            "speed_limit_kmh": 30,
            "oncoming_bicycle_present": True,
            "child_candidate": True,
        },
        "accepted_observations": [
            {"field": "ego_vehicle_type", "value": "motorcycle", "confidence": 0.9, "frame_refs": ["frame_001.jpg", "frame_002.jpg"]},
            {"field": "direct_collision_partner_type", "value": "bicycle", "confidence": 0.88, "frame_refs": ["frame_003.jpg", "frame_004.jpg"]},
            {"field": "school_zone", "value": True, "confidence": 0.86, "frame_refs": ["frame_001.jpg", "frame_002.jpg"]},
            {"field": "speed_limit_kmh", "value": 30, "confidence": 0.87, "frame_refs": ["frame_001.jpg"]},
            {"field": "oncoming_bicycle_present", "value": True, "confidence": 0.84, "frame_refs": ["frame_002.jpg", "frame_003.jpg"]},
        ],
        "uncertain_observations": [
            {"field": "child_candidate", "value": True, "confidence": 0.65, "frame_refs": ["frame_003.jpg"]},
        ],
    }

    summary = build_video_scene_summary(video_contract)

    assert summary["available"] is True
    assert summary["title"] == "영상에서 확인된 사고 개요"
    assert "오토바이" in summary["summary_text"]
    assert "자전거" in summary["summary_text"]
    assert "30km" in summary["summary_text"]
    assert any(item["field"] == "victim_is_child" for item in summary["needs_user_confirmation"])
    assert any(item["field"] == "actual_speed_kmh" for item in summary["needs_user_confirmation"])


def test_bicycle_candidate_with_multiframe_contact_support_is_promoted_to_direct_partner():
    fact_patch = {"impact_visible": True, "primary_collision_target": "bicycle_candidate"}
    accepted = [
        {
            "field": "primary_collision_target",
            "value": "bicycle_candidate",
            "confidence": 0.87,
            "frame_refs": ["frame_003.jpg", "frame_004.jpg"],
            "reason": "cyclist wheels and handlebar visible near contact window",
            "source": "frame_analysis:openai",
        },
        {
            "field": "impact_visible",
            "value": True,
            "confidence": 0.82,
            "frame_refs": ["frame_003.jpg", "frame_004.jpg"],
            "source": "frame_analysis:openai",
        },
    ]
    uncertain = []

    apply_video_fact_guards(fact_patch, accepted, uncertain)

    assert fact_patch["direct_collision_partner_type"] == "bicycle"
    assert fact_patch["collision_partner_type"] == "bicycle"


def test_motorcycle_ego_and_bicycle_partner_routes_to_bicycle_knia_path():
    scenario = classify_scenario(
        "",
        {
            "ego_vehicle_type": "motorcycle",
            "direct_collision_partner_type": "bicycle",
            "school_zone": True,
            "speed_limit_kmh": 30,
            "oncoming_bicycle_present": True,
        },
        [],
    )

    assert scenario["scenario_type"] == "motorcycle_bicycle_collision"
    assert scenario["accident_party_type"] == "car_vs_bicycle"
    assert "bicycle" in scenario["scenario_tags"]
    assert "school_zone" in scenario["scenario_tags"]
