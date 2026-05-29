from app.services.video_input_contract_guards import apply_video_fact_guards


def test_guard_demotes_pedestrian_context_when_collision_partner_is_vehicle():
    fact_patch = {
        "collision_partner_type": "vehicle",
        "pedestrian_visible": True,
        "pedestrian_signal": "red",
    }
    accepted = [
        {"field": "collision_partner_type", "value": "vehicle"},
        {"field": "pedestrian_visible", "value": True},
        {"field": "pedestrian_signal", "value": "red"},
    ]
    uncertain = []

    apply_video_fact_guards(fact_patch, accepted, uncertain)

    assert fact_patch == {"collision_partner_type": "vehicle"}
    reasons = {item["field"]: item["reason"] for item in uncertain}
    assert reasons["pedestrian_visible"] == "pedestrian_presence_is_context_when_collision_partner_is_vehicle"
    assert reasons["pedestrian_signal"] == "pedestrian_signal_is_context_when_collision_partner_is_vehicle"


def test_guard_aligns_collision_partner_from_direct_contact():
    fact_patch = {
        "collision_partner_type": "pedestrian",
        "direct_collision_partner_type": "vehicle",
    }
    accepted = [
        {"field": "collision_partner_type", "value": "pedestrian"},
        {"field": "direct_collision_partner_type", "value": "vehicle"},
    ]
    uncertain = []

    apply_video_fact_guards(fact_patch, accepted, uncertain)

    assert fact_patch["collision_partner_type"] == "vehicle"
    assert fact_patch["direct_collision_partner_type"] == "vehicle"
    assert uncertain[0]["field"] == "collision_partner_type"
    assert uncertain[0]["reason"] == "pedestrian_collision_partner_requires_direct_contact_evidence"


def test_guard_requires_direct_contact_for_pedestrian_collision_partner():
    fact_patch = {
        "collision_partner_type": "pedestrian",
        "crosswalk_nearby": True,
    }
    accepted = [
        {"field": "collision_partner_type", "value": "pedestrian"},
        {"field": "crosswalk_nearby", "value": True},
    ]
    uncertain = []

    apply_video_fact_guards(fact_patch, accepted, uncertain)

    assert fact_patch == {"crosswalk_nearby": True}
    assert uncertain[0]["field"] == "collision_partner_type"
    assert uncertain[0]["reason"] == "pedestrian_collision_partner_requires_direct_contact_evidence"


def test_guard_demotes_vehicle_partner_when_primary_target_is_non_vehicle():
    fact_patch = {
        "collision_partner_type": "vehicle",
        "primary_collision_target": "pedestrian",
    }
    accepted = [
        {"field": "collision_partner_type", "value": "vehicle"},
        {"field": "primary_collision_target", "value": "pedestrian"},
    ]
    uncertain = []

    apply_video_fact_guards(fact_patch, accepted, uncertain)

    assert fact_patch == {"primary_collision_target": "pedestrian"}
    assert uncertain[0]["field"] == "collision_partner_type"
    assert uncertain[0]["reason"] == "collision_partner_vehicle_conflicts_with_non_vehicle_primary_target"


def test_guard_demotes_vehicle_partner_when_direct_target_is_non_vehicle():
    fact_patch = {
        "collision_partner_type": "vehicle",
        "direct_collision_partner_type": "bicycle",
    }
    accepted = [
        {"field": "collision_partner_type", "value": "vehicle"},
        {"field": "direct_collision_partner_type", "value": "bicycle", "source": "frame_analysis", "confidence": 0.91, "frame_refs": ["frame_1.jpg", "frame_2.jpg"]},
        {"field": "primary_collision_target", "value": "bicycle_candidate", "source": "vision_model:yolo", "confidence": 0.74, "frame_refs": ["frame_1.jpg", "frame_2.jpg"]},
    ]
    uncertain = []

    apply_video_fact_guards(fact_patch, accepted, uncertain)

    assert fact_patch["direct_collision_partner_type"] == "bicycle"
    assert fact_patch["collision_partner_type"] == "bicycle"
    assert uncertain[0]["field"] == "collision_partner_type"
    assert uncertain[0]["reason"] == "collision_partner_vehicle_conflicts_with_non_vehicle_direct_contact"


def test_guard_requires_direct_contact_for_bicycle_collision_partner():
    fact_patch = {
        "collision_partner_type": "bicycle",
        "bicycle_location": "right_side",
    }
    accepted = [
        {"field": "collision_partner_type", "value": "bicycle"},
        {"field": "bicycle_location", "value": "right_side"},
    ]
    uncertain = []

    apply_video_fact_guards(fact_patch, accepted, uncertain)

    assert fact_patch == {"bicycle_location": "right_side"}
    assert uncertain[0]["field"] == "collision_partner_type"
    assert uncertain[0]["reason"] == "bicycle_collision_partner_requires_direct_contact_evidence"


def test_guard_allows_bicycle_direct_collision_partner_when_contact_is_clear():
    fact_patch = {
        "collision_partner_type": "bicycle",
        "direct_collision_partner_type": "bicycle",
        "collision_point_visible": True,
    }
    accepted = [
        {"field": "collision_partner_type", "value": "bicycle", "source": "frame_analysis", "confidence": 0.91, "frame_refs": ["frame_1.jpg", "frame_2.jpg"]},
        {"field": "direct_collision_partner_type", "value": "bicycle", "source": "frame_analysis", "confidence": 0.91, "frame_refs": ["frame_1.jpg", "frame_2.jpg"]},
        {"field": "primary_collision_target", "value": "bicycle_candidate", "source": "vision_model:yolo", "confidence": 0.74, "frame_refs": ["frame_1.jpg", "frame_2.jpg"]},
        {"field": "collision_point_visible", "value": True},
    ]
    uncertain = []

    apply_video_fact_guards(fact_patch, accepted, uncertain)

    assert fact_patch["collision_partner_type"] == "bicycle"
    assert fact_patch["direct_collision_partner_type"] == "bicycle"
    assert uncertain == []


def test_guard_requires_direct_contact_for_motorcycle_collision_partner():
    fact_patch = {
        "collision_partner_type": "motorcycle",
        "intersection": True,
    }
    accepted = [
        {"field": "collision_partner_type", "value": "motorcycle"},
        {"field": "intersection", "value": True},
    ]
    uncertain = []

    apply_video_fact_guards(fact_patch, accepted, uncertain)

    assert fact_patch == {"intersection": True}
    assert uncertain[0]["field"] == "collision_partner_type"
    assert uncertain[0]["reason"] == "motorcycle_collision_partner_requires_direct_contact_evidence"


def test_guard_allows_motorcycle_direct_collision_partner_when_contact_is_clear():
    fact_patch = {
        "collision_partner_type": "motorcycle",
        "direct_collision_partner_type": "motorcycle",
        "collision_point_visible": True,
    }
    accepted = [
        {"field": "collision_partner_type", "value": "motorcycle", "source": "frame_analysis", "confidence": 0.92, "frame_refs": ["frame_1.jpg", "frame_2.jpg"]},
        {"field": "direct_collision_partner_type", "value": "motorcycle", "source": "frame_analysis", "confidence": 0.92, "frame_refs": ["frame_1.jpg", "frame_2.jpg"]},
        {"field": "primary_collision_target", "value": "motorcycle_candidate", "source": "vision_model:yolo", "confidence": 0.74, "frame_refs": ["frame_1.jpg", "frame_2.jpg"]},
        {"field": "collision_point_visible", "value": True},
    ]
    uncertain = []

    apply_video_fact_guards(fact_patch, accepted, uncertain)

    assert fact_patch["collision_partner_type"] == "motorcycle"
    assert fact_patch["direct_collision_partner_type"] == "motorcycle"
    assert uncertain == []


def test_guard_demotes_signal_violation_without_signal_state_or_transition():
    fact_patch = {
        "opponent_signal_violation": True,
        "opponent_signal_visible": True,
    }
    accepted = [
        {"field": "opponent_signal_violation", "value": True},
        {"field": "opponent_signal_visible", "value": True},
    ]
    uncertain = []

    apply_video_fact_guards(fact_patch, accepted, uncertain)

    assert fact_patch == {"opponent_signal_visible": True}
    assert uncertain[0]["field"] == "opponent_signal_violation"
    assert uncertain[0]["reason"] == "signal_violation_requires_signal_state_or_transition_context"


def test_guard_keeps_signal_violation_with_signal_transition_context():
    fact_patch = {
        "opponent_signal_violation": True,
        "signal_transition": "yellow_to_red",
    }
    accepted = [
        {"field": "opponent_signal_violation", "value": True},
        {"field": "signal_transition", "value": "yellow_to_red"},
    ]
    uncertain = []

    apply_video_fact_guards(fact_patch, accepted, uncertain)

    assert fact_patch["opponent_signal_violation"] is True
    assert fact_patch["signal_transition"] == "yellow_to_red"
    assert uncertain == []


def test_guard_demotes_candidate_collision_target():
    fact_patch = {
        "primary_collision_target": "vehicle_candidate",
    }
    accepted = [
        {"field": "primary_collision_target", "value": "vehicle_candidate"},
    ]
    uncertain = []

    apply_video_fact_guards(fact_patch, accepted, uncertain)

    assert fact_patch == {}
    assert uncertain[0]["field"] == "primary_collision_target"
    assert uncertain[0]["reason"] == "primary_collision_target_candidate_requires_direct_contact_evidence"


def test_guard_demotes_vehicle_target_without_vehicle_collision_context():
    fact_patch = {
        "primary_collision_target": "vehicle",
    }
    accepted = [
        {
            "field": "primary_collision_target",
            "value": "vehicle",
            "source": "frame_analysis",
            "confidence": 0.91,
            "frame_refs": ["frame_10.jpg", "frame_11.jpg", "frame_12.jpg"],
        },
    ]
    uncertain = [
        {
            "field": "primary_collision_target",
            "value": "vehicle_candidate",
            "source": "vision_model:yolo",
            "confidence": 0.72,
            "frame_refs": ["frame_10.jpg", "frame_11.jpg", "frame_12.jpg"],
        }
    ]

    apply_video_fact_guards(fact_patch, accepted, uncertain)

    assert fact_patch == {}
    assert uncertain[-1]["reason"] == "primary_collision_target_vehicle_target_requires_collision_context_or_user_confirmation"


def test_guard_keeps_vehicle_target_with_rear_collision_context():
    fact_patch = {
        "primary_collision_target": "vehicle",
        "rear_vehicle_collision": True,
    }
    accepted = [
        {
            "field": "primary_collision_target",
            "value": "vehicle",
            "source": "frame_analysis",
            "confidence": 0.91,
            "frame_refs": ["frame_10.jpg", "frame_11.jpg", "frame_12.jpg"],
        },
        {"field": "rear_vehicle_collision", "value": True},
    ]
    uncertain = []

    apply_video_fact_guards(fact_patch, accepted, uncertain)

    assert fact_patch["primary_collision_target"] == "vehicle"
    assert fact_patch["rear_vehicle_collision"] is True


def test_guard_demotes_non_vehicle_target_without_cross_model_support():
    fact_patch = {
        "primary_collision_target": "pedestrian",
    }
    accepted = [
        {
            "field": "primary_collision_target",
            "value": "pedestrian",
            "source": "frame_analysis",
            "confidence": 0.95,
            "frame_refs": ["frame_10.jpg", "frame_11.jpg", "frame_12.jpg"],
        }
    ]
    uncertain = [
        {
            "field": "primary_collision_target",
            "value": "pedestrian_candidate",
            "source": "vision_model:yolo",
            "confidence": 0.3,
            "frame_refs": ["frame_11.jpg"],
        }
    ]

    apply_video_fact_guards(fact_patch, accepted, uncertain)

    assert fact_patch == {}
    assert uncertain[-1]["reason"] == "primary_collision_target_pedestrian_requires_cross_model_or_multi_frame_contact_support"


def test_guard_keeps_non_vehicle_target_with_single_source_contact_bundle():
    fact_patch = {
        "collision_partner_type": "bicycle",
    }
    accepted = [
        {
            "field": "collision_partner_type",
            "value": "bicycle",
            "source": "frame_analysis:openai",
            "confidence": 0.9,
            "frame_refs": ["frame_14.jpg", "frame_15.jpg"],
        }
    ]
    uncertain = [
        {
            "field": "primary_collision_target",
            "value": "bicycle",
            "source": "frame_analysis:openai",
            "confidence": 0.74,
            "frame_refs": ["frame_14.jpg", "frame_15.jpg"],
        },
        {
            "field": "direct_collision_partner_type",
            "value": "bicycle",
            "source": "frame_analysis:openai",
            "confidence": 0.74,
            "frame_refs": ["frame_14.jpg", "frame_15.jpg"],
        },
        {
            "field": "collision_point_visible",
            "value": True,
            "source": "frame_analysis:openai",
            "confidence": 0.8,
            "frame_refs": ["frame_14.jpg", "frame_15.jpg"],
        },
    ]

    apply_video_fact_guards(fact_patch, accepted, uncertain)

    assert fact_patch["collision_partner_type"] == "bicycle"


def test_guard_rejects_single_source_non_vehicle_target_without_contact_point():
    fact_patch = {
        "collision_partner_type": "bicycle",
    }
    accepted = [
        {
            "field": "collision_partner_type",
            "value": "bicycle",
            "source": "frame_analysis:openai",
            "confidence": 0.9,
            "frame_refs": ["frame_14.jpg", "frame_15.jpg"],
        }
    ]
    uncertain = [
        {
            "field": "primary_collision_target",
            "value": "bicycle",
            "source": "frame_analysis:openai",
            "confidence": 0.74,
            "frame_refs": ["frame_14.jpg", "frame_15.jpg"],
        }
    ]

    apply_video_fact_guards(fact_patch, accepted, uncertain)

    assert fact_patch == {}
    assert uncertain[-1]["reason"] == "bicycle_collision_partner_requires_direct_contact_evidence"


def test_guard_keeps_non_vehicle_target_with_cross_model_support():
    fact_patch = {
        "primary_collision_target": "pedestrian",
    }
    accepted = [
        {
            "field": "primary_collision_target",
            "value": "pedestrian",
            "source": "frame_analysis",
            "confidence": 0.91,
            "frame_refs": ["frame_10.jpg", "frame_11.jpg", "frame_12.jpg"],
        }
    ]
    uncertain = [
        {
            "field": "primary_collision_target",
            "value": "pedestrian_candidate",
            "source": "vision_model:yolo",
            "confidence": 0.74,
            "frame_refs": ["frame_10.jpg", "frame_11.jpg"],
        }
    ]

    apply_video_fact_guards(fact_patch, accepted, uncertain)

    assert fact_patch["primary_collision_target"] == "pedestrian"


def test_guard_demotes_centerline_crossing_without_actor_reason_or_road_context():
    fact_patch = {
        "centerline_crossed": True,
    }
    accepted = [
        {"field": "centerline_crossed", "value": True},
    ]
    uncertain = []

    apply_video_fact_guards(fact_patch, accepted, uncertain)

    assert fact_patch == {}
    assert uncertain[0]["field"] == "centerline_crossed"
    assert uncertain[0]["reason"] == "centerline_crossing_requires_actor_reason_or_road_context"
