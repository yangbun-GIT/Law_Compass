from app.services.fact_arbitration import VERSION, arbitrate_facts


def test_strong_video_primary_physical_fact_wins_conflict():
    result = arbitrate_facts(
        user_facts={"stopped": False},
        video_contract={
            "fact_patch": {"stopped": True},
            "accepted_observations": [
                {
                    "field": "stopped",
                    "value": True,
                    "confidence": 0.96,
                    "source": "frame_analysis:openai",
                    "frame_refs": ["frame_1.jpg", "frame_2.jpg"],
                }
            ],
        },
    )

    assert result["facts"]["stopped"] is True
    assert result["contract"]["version"] == VERSION
    assert result["contract"]["conflicts"][0]["winner"] == "video"
    assert result["contract"]["requires_confirmation"][0]["field"] == "stopped"
    assert result["contract"]["fact_sources"]["stopped"]["source"] == "video"


def test_conflicting_openai_observation_below_override_gate_keeps_user_fact():
    result = arbitrate_facts(
        user_facts={"stopped": True},
        video_contract={
            "fact_patch": {"stopped": False},
            "accepted_observations": [
                {
                    "field": "stopped",
                    "value": False,
                    "confidence": 0.9,
                    "source": "frame_analysis:openai",
                    "frame_refs": ["frame_1.jpg", "frame_3.jpg", "frame_5.jpg"],
                }
            ],
        },
    )

    conflict = result["contract"]["conflicts"][0]
    assert result["facts"]["stopped"] is True
    assert conflict["winner"] == "user"
    assert conflict["needs_confirmation"] is True
    assert conflict["quality_gate"].startswith("video_conflict_quality_gate_not_met")
    assert result["contract"]["kept_user_fields"] == ["stopped"]
    assert result["contract"]["requires_confirmation"][0]["field"] == "stopped"


def test_user_primary_context_wins_conflict():
    result = arbitrate_facts(
        user_facts={"injury": False},
        video_contract={
            "fact_patch": {"injury": True},
            "accepted_observations": [
                {"field": "injury", "value": True, "confidence": 0.8, "source": "frame_analysis:openai"}
            ],
        },
    )

    assert result["facts"]["injury"] is False
    assert result["contract"]["conflicts"][0]["winner"] == "user"
    assert result["contract"]["kept_user_fields"] == ["injury"]


def test_matching_user_and_video_values_are_marked_confirmed():
    result = arbitrate_facts(
        user_facts={"opponent_behavior": "rear_collision"},
        video_contract={
            "fact_patch": {"opponent_behavior": "rear_collision"},
            "accepted_observations": [
                {
                    "field": "opponent_behavior",
                    "value": "rear_collision",
                    "confidence": 0.87,
                    "source": "frame_analysis:openai",
                }
            ],
        },
    )

    assert result["facts"]["opponent_behavior"] == "rear_collision"
    assert result["contract"]["conflicts"] == []
    assert result["contract"]["confirmed_fields"] == ["opponent_behavior"]
    assert result["contract"]["fact_sources"]["opponent_behavior"]["source"] == "user_and_video"


def test_matching_user_alias_and_video_value_are_canonicalized_and_confirmed():
    result = arbitrate_facts(
        user_facts={"opponent_behavior": "rear_vehicle_collision"},
        video_contract={
            "fact_patch": {"opponent_behavior": "rear_collision"},
            "accepted_observations": [
                {
                    "field": "opponent_behavior",
                    "value": "rear_collision",
                    "confidence": 0.85,
                    "source": "frame_analysis:openai",
                    "frame_refs": ["frame_8.jpg", "frame_12.jpg"],
                }
            ],
        },
    )

    assert result["facts"]["opponent_behavior"] == "rear_collision"
    assert result["contract"]["conflicts"] == []
    assert result["contract"]["confirmed_fields"] == ["opponent_behavior"]


def test_held_video_observation_conflicting_with_user_input_requires_confirmation():
    result = arbitrate_facts(
        user_facts={"collision_partner_type": "vehicle"},
        video_contract={
            "fact_patch": {},
            "accepted_observations": [],
            "uncertain_observations": [
                {
                    "field": "collision_partner_type",
                    "value": "pedestrian",
                    "confidence": 0.8,
                    "source": "frame_analysis:openai",
                    "frame_refs": ["frame_3.jpg", "frame_4.jpg"],
                    "reason": "pedestrian_collision_partner_requires_direct_contact_evidence",
                    "quality_gate": {"status": "rejected", "min_confidence": 0.82, "confidence": 0.8},
                }
            ],
        },
    )

    assert result["facts"]["collision_partner_type"] == "vehicle"
    assert result["contract"]["conflicts"] == []
    assert result["contract"]["held_video_fields"] == ["collision_partner_type"]
    assert result["contract"]["confirmation_fields"] == ["collision_partner_type"]
    pending = result["contract"]["pending_video_confirmations"][0]
    assert pending["status"] == "user_video_conflict_video_held"
    assert pending["winner"] == "user"
    assert pending["needs_confirmation"] is True
    assert result["contract"]["requires_confirmation"][0]["field"] == "collision_partner_type"


def test_held_video_observation_for_missing_user_fact_is_confirmation_candidate():
    result = arbitrate_facts(
        user_facts={"accident_party_type": "car_vs_car"},
        video_contract={
            "fact_patch": {},
            "uncertain_observations": [
                {
                    "field": "opponent_signal_visible",
                    "value": False,
                    "confidence": 0.78,
                    "source": "frame_analysis:openai",
                    "frame_refs": ["frame_6.jpg"],
                    "reason": "confidence_below_field_threshold",
                }
            ],
        },
    )

    assert "opponent_signal_visible" not in result["facts"]
    assert result["contract"]["held_video_fields"] == ["opponent_signal_visible"]
    assert result["contract"]["pending_video_confirmations"][0]["status"] == "missing_user_fact_video_held"
    assert result["contract"]["requires_confirmation"][0]["field"] == "opponent_signal_visible"


def test_held_video_observation_matching_user_input_is_tentative_support_only():
    result = arbitrate_facts(
        user_facts={"stopped": True},
        video_contract={
            "fact_patch": {},
            "uncertain_observations": [
                {
                    "field": "stopped",
                    "value": True,
                    "confidence": 0.79,
                    "source": "frame_analysis:openai",
                    "frame_refs": ["frame_2.jpg"],
                    "reason": "confidence_below_field_threshold",
                }
            ],
        },
    )

    assert result["facts"]["stopped"] is True
    assert result["contract"]["held_video_fields"] == []
    assert result["contract"]["tentatively_supported_fields"] == ["stopped"]
    assert result["contract"]["pending_video_confirmations"][0]["status"] == "user_supported_by_held_video"
    assert result["contract"]["requires_confirmation"] == []


def test_matching_held_video_observation_still_asks_when_context_can_change_accident_type():
    result = arbitrate_facts(
        user_facts={"collision_partner_type": "pedestrian"},
        video_contract={
            "fact_patch": {},
            "uncertain_observations": [
                {
                    "field": "collision_partner_type",
                    "value": "pedestrian",
                    "confidence": 0.84,
                    "source": "frame_analysis:openai",
                    "frame_refs": ["frame_4.jpg", "frame_5.jpg"],
                    "reason": "pedestrian_collision_partner_requires_direct_contact_evidence",
                }
            ],
        },
    )

    assert result["facts"]["collision_partner_type"] == "pedestrian"
    assert result["contract"]["held_video_fields"] == ["collision_partner_type"]
    assert result["contract"]["tentatively_supported_fields"] == []
    pending = result["contract"]["pending_video_confirmations"][0]
    assert pending["status"] == "user_supported_by_held_video_needs_context_confirmation"
    assert pending["needs_confirmation"] is True
    assert result["contract"]["requires_confirmation"][0]["field"] == "collision_partner_type"


def test_primary_collision_target_candidate_is_bridged_to_direct_target_question():
    result = arbitrate_facts(
        user_facts={"accident_party_type": "car_vs_car", "collision_partner_type": "vehicle"},
        video_contract={
            "fact_patch": {},
            "uncertain_observations": [
                {
                    "field": "primary_collision_target",
                    "value": "vehicle_candidate",
                    "confidence": 0.74,
                    "source": "vision_model:yolo",
                    "frame_refs": ["frame_4.jpg", "frame_5.jpg"],
                    "reason": "primary_collision_target_candidate_requires_direct_contact_evidence",
                }
            ],
        },
    )

    assert result["facts"]["collision_partner_type"] == "vehicle"
    assert "primary_collision_target" not in result["facts"]
    pending = result["contract"]["pending_video_confirmations"][0]
    assert pending["status"] == "user_supported_by_held_video_needs_context_confirmation"
    assert pending["field"] == "primary_collision_target"
    assert pending["source_field"] == "primary_collision_target"
    assert pending["question_field"] == "direct_collision_partner_type"
    assert pending["recommended_fact_field"] == "direct_collision_partner_type"
    assert pending["recommended_fact_value"] == "vehicle"
    assert pending["normalized_video_value"] == "vehicle"
    assert pending["normalized_user_value"] == "vehicle"
    assert pending["matched_user_field"] == "collision_partner_type"
    assert result["contract"]["confirmation_fields"] == ["direct_collision_partner_type", "primary_collision_target"]


def test_primary_collision_target_candidate_conflicts_with_cross_field_user_target():
    result = arbitrate_facts(
        user_facts={"accident_party_type": "car_vs_car", "collision_partner_type": "vehicle"},
        video_contract={
            "fact_patch": {},
            "uncertain_observations": [
                {
                    "field": "primary_collision_target",
                    "value": "pedestrian_candidate",
                    "confidence": 0.74,
                    "source": "vision_model:yolo",
                    "frame_refs": ["frame_2.jpg", "frame_3.jpg"],
                    "reason": "primary_collision_target_candidate_requires_direct_contact_evidence",
                }
            ],
        },
    )

    assert result["facts"]["collision_partner_type"] == "vehicle"
    pending = result["contract"]["pending_video_confirmations"][0]
    assert pending["status"] == "user_video_conflict_video_held"
    assert pending["question_field"] == "direct_collision_partner_type"
    assert pending["normalized_video_value"] == "pedestrian"
    assert pending["normalized_user_value"] == "vehicle"
    assert pending["matched_user_field"] == "collision_partner_type"


def test_arbitration_exposes_fact_states_for_confirmed_confirmation_and_conflict():
    result = arbitrate_facts(
        user_facts={"stopped": True, "collision_partner_type": "vehicle"},
        video_contract={
            "fact_patch": {"stopped": True, "opponent_signal_visible": False},
            "accepted_observations": [
                {
                    "field": "stopped",
                    "value": True,
                    "confidence": 0.96,
                    "source": "frame_analysis:openai",
                    "frame_refs": ["frame_1.jpg", "frame_2.jpg"],
                },
                {
                    "field": "opponent_signal_visible",
                    "value": False,
                    "confidence": 0.9,
                    "source": "frame_analysis:openai",
                    "frame_refs": ["frame_3.jpg"],
                },
            ],
            "uncertain_observations": [
                {
                    "field": "primary_collision_target",
                    "value": "pedestrian_candidate",
                    "confidence": 0.74,
                    "source": "vision_model:yolo",
                    "frame_refs": ["frame_4.jpg", "frame_5.jpg"],
                    "reason": "primary_collision_target_candidate_requires_direct_contact_evidence",
                }
            ],
        },
    )

    states = {item["field"]: item["status"] for item in result["contract"]["fact_states"]}
    assert states["stopped"] == "confirmed"
    assert states["opponent_signal_visible"] == "confirmed"
    assert states["direct_collision_partner_type"] == "needs_confirmation"
    assert result["contract"]["fact_state_summary"]["counts"]["needs_confirmation"] == 1
