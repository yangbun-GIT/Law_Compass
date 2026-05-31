from app.services.evidence_axis_router import classify_evidence_axis, route_evidence_by_accident_axis


def test_car_vs_car_excludes_direct_pedestrian_party_evidence_from_primary():
    item = {
        "chunk_id": "static:fault-guide:pedestrian-crosswalk",
        "accident_party_type": "car_vs_person",
        "scenario_tags": ["pedestrian", "crosswalk"],
        "title": "pedestrian crosswalk fault guide",
    }

    result = classify_evidence_axis(
        item,
        facts={"accident_party_type": "car_vs_car", "direct_collision_partner_type": "vehicle"},
        accident_party_type="car_vs_car",
        scenario_type="intersection_signal_violation",
    )

    assert result["status"] == "excluded"
    assert result["reason"] == "party_axis_mismatch"


def test_car_vs_car_crosswalk_context_is_secondary_not_direct_primary():
    item = {
        "chunk_id": "static:fault-guide:crosswalk-front-stop-rear-end",
        "accident_party_type": "car_vs_car",
        "scenario_tags": ["rear_end", "crosswalk", "safe_distance"],
        "title": "crosswalk front vehicle stop rear-end fault guide",
    }

    routed = route_evidence_by_accident_axis(
        [item],
        facts={
            "accident_party_type": "car_vs_car",
            "direct_collision_partner_type": "vehicle",
            "front_vehicle_stopped": True,
            "crosswalk_nearby": True,
        },
        accident_party_type="car_vs_car",
        scenario_type="rear_end_collision",
    )

    assert routed["primary"] == []
    assert routed["secondary"][0]["evidence_axis"]["reason"] == "vehicle_case_environment_axis"
    assert routed["summary"]["secondary_count"] == 1


def test_car_vs_car_vehicle_rear_end_evidence_stays_primary():
    item = {
        "chunk_id": "static:fault-guide:rear-end-vehicle",
        "accident_party_type": "car_vs_car",
        "chart_no": "차41-1",
        "scenario_tags": ["rear_end", "safe_distance"],
        "title": "정차 또는 감속 차량을 뒤에서 추돌한 사고",
    }

    routed = route_evidence_by_accident_axis(
        [item],
        facts={
            "accident_party_type": "car_vs_car",
            "direct_collision_partner_type": "vehicle",
            "collision_partner_type": "vehicle",
        },
        accident_party_type="car_vs_car",
        scenario_type="rear_end_collision",
    )

    assert routed["primary"][0]["evidence_axis"]["status"] == "primary"
    assert routed["secondary"] == []
    assert routed["excluded"] == []


def test_pedestrian_direct_collision_keeps_pedestrian_evidence_primary():
    item = {
        "chunk_id": "static:fault-guide:pedestrian-crosswalk",
        "accident_party_type": "car_vs_person",
        "scenario_tags": ["pedestrian", "crosswalk"],
        "title": "pedestrian crosswalk fault guide",
    }

    routed = route_evidence_by_accident_axis(
        [item],
        facts={"direct_collision_partner_type": "pedestrian"},
        accident_party_type="car_vs_person",
        scenario_type="pedestrian_crosswalk_accident",
    )

    assert routed["primary"][0]["evidence_axis"]["status"] == "primary"
    assert routed["secondary"] == []
    assert routed["excluded"] == []
