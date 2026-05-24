from app.services.input_normalizer import normalize_analysis_input
from app.services.video_input_contract import VERSION, normalize_video_input_contract


def test_high_confidence_video_observation_becomes_fact_patch():
    contract = normalize_video_input_contract(
        {
            "metadata": {
                "duration_sec": 12.5,
                "representative_frames": ["/frames/1.jpg", "/frames/2.jpg"],
                "observations": [
                    {
                        "field": "stopped",
                        "value": True,
                        "confidence": 0.92,
                        "source": "frame_analysis",
                        "frame_refs": ["frame_1.jpg"],
                    },
                    {
                        "field": "opponent_behavior",
                        "value": "rear_collision",
                        "confidence": 0.88,
                        "source": "vision_model:v1",
                        "frame_refs": ["frame_1.jpg", "frame_2.jpg"],
                    },
                ],
            }
        }
    )

    assert contract["version"] == VERSION
    assert contract["technical_metadata"]["representative_frame_count"] == 2
    assert contract["fact_patch"]["stopped"] is True
    assert contract["fact_patch"]["opponent_behavior"] == "rear_collision"
    assert len(contract["accepted_observations"]) == 2
    assert contract["observation_quality_summary"]["accepted_count"] == 2


def test_low_confidence_video_observation_is_not_fact_patch():
    contract = normalize_video_input_contract(
        {
            "metadata": {
                "observations": [
                    {"field": "opponent_signal_violation", "value": True, "confidence": 0.4, "source": "frame_analysis"}
                ]
            }
        }
    )

    assert "opponent_signal_violation" not in contract["fact_patch"]
    assert contract["uncertain_observations"][0]["reason"] == "confidence_below_field_threshold"
    assert contract["confirmation_candidates"][0]["field"] == "opponent_signal_violation"
    assert contract["observation_quality_summary"]["confirmation_candidate_count"] == 1


def test_frame_observation_without_frame_reference_is_not_fact_patch():
    contract = normalize_video_input_contract(
        {
            "metadata": {
                "observations": [
                    {"field": "stopped", "value": True, "confidence": 0.96, "source": "frame_analysis:openai"}
                ]
            }
        }
    )

    assert "stopped" not in contract["fact_patch"]
    assert contract["uncertain_observations"][0]["reason"] == "missing_frame_reference"
    assert contract["observation_quality_summary"]["uncertain_reasons"]["missing_frame_reference"] == 1


def test_collision_direction_front_is_kept_as_supporting_observation():
    contract = normalize_video_input_contract(
        {
            "metadata": {
                "observations": [
                    {
                        "field": "collision_direction",
                        "value": "front",
                        "confidence": 0.95,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_8.jpg", "frame_10.jpg"],
                    }
                ]
            }
        }
    )

    assert "opponent_behavior" not in contract["fact_patch"]
    assert contract["uncertain_observations"] == []
    assert contract["supporting_observations"][0]["field"] == "collision_direction"
    assert contract["supporting_observations"][0]["raw_field"] == "collision_direction"
    assert contract["supporting_observations"][0]["value"] == "front"
    assert contract["supporting_observations"][0]["reason"] == "supporting_observation_not_agent_fact"
    assert contract["observation_quality_summary"]["supporting_count"] == 1
    assert contract["confirmation_candidates"] == []


def test_impact_direction_rear_does_not_create_rear_collision_fact_by_itself():
    contract = normalize_video_input_contract(
        {
            "metadata": {
                "observations": [
                    {
                        "field": "impact_direction",
                        "value": "rear",
                        "confidence": 0.96,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_8.jpg", "frame_10.jpg"],
                    }
                ]
            }
        }
    )

    assert contract["fact_patch"] == {}
    assert contract["accepted_observations"] == []
    assert contract["supporting_observations"][0]["field"] == "impact_direction"
    assert contract["supporting_observations"][0]["value"] == "rear"
    assert contract["confirmation_candidates"] == []


def test_signal_violation_uses_stricter_field_threshold():
    contract = normalize_video_input_contract(
        {
            "metadata": {
                "observations": [
                    {
                        "field": "opponent_signal_violation",
                        "value": True,
                        "confidence": 0.84,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_3.jpg"],
                    }
                ]
            }
        }
    )

    assert "opponent_signal_violation" not in contract["fact_patch"]
    assert contract["uncertain_observations"][0]["reason"] == "confidence_below_field_threshold"
    assert contract["uncertain_observations"][0]["quality_gate"]["min_confidence"] == 0.88


def test_opponent_behavior_needs_stronger_video_confidence_before_fact_patch():
    contract = normalize_video_input_contract(
        {
            "metadata": {
                "observations": [
                    {
                        "field": "opponent_behavior",
                        "value": "lane_change",
                        "confidence": 0.85,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_7.jpg", "frame_9.jpg", "frame_10.jpg"],
                    }
                ]
            }
        }
    )

    assert "opponent_behavior" not in contract["fact_patch"]
    assert contract["uncertain_observations"][0]["reason"] == "confidence_below_field_threshold"
    assert contract["uncertain_observations"][0]["quality_gate"]["min_confidence"] == 0.88
    assert contract["confirmation_candidates"][0]["field"] == "opponent_behavior"


def test_uncertain_rear_end_observations_are_grouped_for_confirmation():
    contract = normalize_video_input_contract(
        {
            "metadata": {
                "representative_frames": ["frame_1.jpg", "frame_2.jpg"],
                "observations": [
                    {
                        "field": "stopped",
                        "value": True,
                        "confidence": 0.79,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_1.jpg"],
                    },
                    {
                        "field": "opponent_behavior",
                        "value": "rear_collision",
                        "confidence": 0.8,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_1.jpg", "frame_2.jpg"],
                    },
                ],
            }
        }
    )

    assert contract["fact_patch"] == {}
    assert [item["field"] for item in contract["confirmation_candidates"]] == ["stopped", "opponent_behavior"]
    assert contract["confirmation_candidates"][1]["value"] == "rear_collision"
    assert contract["confirmation_groups"][0]["type"] == "rear_end_candidate"
    assert contract["confirmation_groups"][0]["status"] == "needs_user_confirmation"
    assert contract["observation_quality_summary"]["high_priority_uncertain_fields"] == ["stopped", "opponent_behavior"]


def test_video_road_context_observations_become_agent_facts():
    contract = normalize_video_input_contract(
        {
            "metadata": {
                "observations": [
                    {
                        "field": "centerline_crossed",
                        "value": True,
                        "confidence": 0.9,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_3.jpg", "frame_4.jpg"],
                    },
                    {
                        "field": "centerline_cross_reason",
                        "value": "parked_vehicle_obstruction",
                        "confidence": 0.82,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_3.jpg"],
                    },
                    {
                        "field": "illegal_parking_obstruction",
                        "value": True,
                        "confidence": 0.86,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_2.jpg", "frame_3.jpg"],
                    },
                    {
                        "field": "opposing_vehicle_present",
                        "value": True,
                        "confidence": 0.84,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_5.jpg"],
                    },
                ]
            }
        }
    )

    assert contract["fact_patch"]["centerline_crossed"] is True
    assert contract["fact_patch"]["centerline_cross_reason"] == "parked_vehicle_obstruction"
    assert contract["fact_patch"]["illegal_parking_obstruction"] is True
    assert contract["fact_patch"]["opposing_vehicle_present"] is True
    assert contract["observation_quality_summary"]["accepted_count"] == 4


def test_collision_target_observations_are_prioritized_agent_facts():
    contract = normalize_video_input_contract(
        {
            "metadata": {
                "observations": [
                    {
                        "field": "collision_partner_type",
                        "value": "car",
                        "confidence": 0.9,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_6.jpg", "frame_7.jpg"],
                    },
                    {
                        "field": "primary_collision_target",
                        "value": "oncoming vehicle",
                        "confidence": 0.83,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_7.jpg"],
                    },
                    {
                        "field": "collision_point_visible",
                        "value": True,
                        "confidence": 0.86,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_7.jpg"],
                    },
                ]
            }
        }
    )

    assert contract["fact_patch"]["collision_partner_type"] == "vehicle"
    assert contract["fact_patch"]["primary_collision_target"] == "oncoming vehicle"
    assert contract["fact_patch"]["collision_point_visible"] is True
    assert contract["observation_quality_summary"]["accepted_count"] == 3


def test_crosswalk_and_pedestrian_visibility_are_separate_video_facts():
    contract = normalize_video_input_contract(
        {
            "metadata": {
                "observations": [
                    {
                        "field": "crosswalk_nearby",
                        "value": True,
                        "confidence": 0.9,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_1.jpg"],
                    },
                    {
                        "field": "pedestrian_visible",
                        "value": False,
                        "confidence": 0.93,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_1.jpg"],
                    },
                ]
            }
        }
    )

    assert contract["fact_patch"]["crosswalk_nearby"] is True
    assert contract["fact_patch"]["pedestrian_visible"] is False


def test_right_turn_front_vehicle_and_signal_visibility_video_facts():
    contract = normalize_video_input_contract(
        {
            "metadata": {
                "observations": [
                    {
                        "field": "collision_partner_type",
                        "value": "vehicle",
                        "confidence": 0.91,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_4.jpg", "frame_5.jpg"],
                    },
                    {
                        "field": "front_vehicle_stopped",
                        "value": True,
                        "confidence": 0.88,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_5.jpg"],
                    },
                    {
                        "field": "crosswalk_nearby",
                        "value": True,
                        "confidence": 0.9,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_4.jpg", "frame_5.jpg"],
                    },
                    {
                        "field": "ego_turn_direction",
                        "value": "right_turn",
                        "confidence": 0.83,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_4.jpg"],
                    },
                    {
                        "field": "pedestrian_signal",
                        "value": "red_light",
                        "confidence": 0.86,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_4.jpg"],
                    },
                    {
                        "field": "opponent_signal_visible",
                        "value": False,
                        "confidence": 0.9,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_4.jpg", "frame_5.jpg"],
                    },
                    {
                        "field": "signal_transition",
                        "value": "yellow_to_red",
                        "confidence": 0.84,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_3.jpg", "frame_5.jpg"],
                    },
                ]
            }
        }
    )

    assert contract["fact_patch"]["collision_partner_type"] == "vehicle"
    assert contract["fact_patch"]["front_vehicle_stopped"] is True
    assert contract["fact_patch"]["crosswalk_nearby"] is True
    assert contract["fact_patch"]["ego_turn_direction"] == "right"
    assert contract["fact_patch"]["pedestrian_signal"] == "red"
    assert contract["fact_patch"]["opponent_signal_visible"] is False
    assert contract["fact_patch"]["signal_transition"] == "yellow_to_red"


def test_turn_direction_without_intersection_or_crosswalk_context_needs_confirmation():
    contract = normalize_video_input_contract(
        {
            "metadata": {
                "observations": [
                    {
                        "field": "ego_turn_direction",
                        "value": "right",
                        "confidence": 0.9,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_4.jpg", "frame_5.jpg"],
                    }
                ]
            }
        }
    )

    assert "ego_turn_direction" not in contract["fact_patch"]
    assert contract["accepted_observations"] == []
    assert contract["uncertain_observations"][0]["reason"] == "turn_direction_requires_intersection_or_crosswalk_context"


def test_technical_preprocess_metadata_does_not_create_accident_facts():
    contract = normalize_video_input_contract(
        {"metadata": {"duration_sec": 8.0, "width": 1920, "height": 1080, "representative_frames": ["/frames/1.jpg"]}},
        preprocessed_summary="Local video verified.",
    )

    assert contract["fact_patch"] == {}
    assert "technical_video_metadata_not_treated_as_accident_fact" in contract["warnings"]
    assert contract["technical_metadata"]["width"] == 1920


def test_video_physical_fact_overrides_conflicting_user_fact():
    normalized = normalize_analysis_input(
        "rear impact while stopped",
        structured_facts={"stopped": False},
        video_metadata={
            "metadata": {
                "observations": [
                    {
                        "field": "stopped",
                        "value": True,
                        "confidence": 0.96,
                        "source": "frame_analysis",
                        "frame_refs": ["frame_1.jpg", "frame_2.jpg"],
                    },
                    {
                        "field": "opponent_behavior",
                        "value": "rear_collision",
                        "confidence": 0.96,
                        "source": "frame_analysis",
                        "frame_refs": ["frame_1.jpg", "frame_2.jpg"],
                    },
                ]
            }
        },
    )

    assert normalized["structured_facts"]["stopped"] is True
    assert normalized["structured_facts"]["opponent_behavior"] == "rear_collision"
    assert normalized["video_input_contract"]["version"] == VERSION
    assert normalized["fact_arbitration"]["conflicts"][0]["field"] == "stopped"
    assert normalized["fact_arbitration"]["conflicts"][0]["winner"] == "video"


def test_user_context_fact_remains_primary_over_video_observation():
    normalized = normalize_analysis_input(
        "rear impact while stopped",
        structured_facts={"injury": False},
        video_metadata={
            "metadata": {
                "observations": [
                    {"field": "injury", "value": True, "confidence": 0.95, "source": "frame_analysis"},
                ]
            }
        },
    )

    assert normalized["structured_facts"]["injury"] is False
    assert normalized["fact_arbitration"]["conflicts"][0]["field"] == "injury"
    assert normalized["fact_arbitration"]["conflicts"][0]["winner"] == "user"
