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
                        "field": "impact_direction",
                        "value": "rear",
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


def test_collision_direction_front_is_not_treated_as_opponent_behavior():
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
    assert contract["uncertain_observations"][0]["field"] == "opponent_behavior"
    assert contract["uncertain_observations"][0]["raw_value"] == "front"
    assert contract["uncertain_observations"][0]["value"] is None
    assert contract["uncertain_observations"][0]["reason"] == "value_not_actionable"
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
                        "field": "impact_direction",
                        "value": "rear",
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
                        "field": "impact_direction",
                        "value": "rear",
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
