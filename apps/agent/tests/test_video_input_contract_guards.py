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
