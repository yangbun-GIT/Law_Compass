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
        {"field": "collision_partner_type", "value": "bicycle"},
        {"field": "direct_collision_partner_type", "value": "bicycle"},
        {"field": "collision_point_visible", "value": True},
    ]
    uncertain = []

    apply_video_fact_guards(fact_patch, accepted, uncertain)

    assert fact_patch["collision_partner_type"] == "bicycle"
    assert fact_patch["direct_collision_partner_type"] == "bicycle"
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
    assert uncertain[0]["reason"] == "primary_collision_target_candidate_requires_contact_evidence"


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
