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
