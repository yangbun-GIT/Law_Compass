from app.services.orchestration_evidence import _filter_primary_knia_evidence


def test_centerline_evidence_filter_keeps_primary_collision_matches_only():
    items = [
        {"chart_no": "\ucc2843-2", "accident_party_type": "car_vs_car"},
        {"chart_no": "\ucc2841-1", "accident_party_type": "car_vs_car"},
        {"chart_no": "\ubcf41", "accident_party_type": "car_vs_person"},
    ]

    filtered = _filter_primary_knia_evidence(items, ["centerline", "road_obstruction", "oncoming_vehicle"])

    assert [item["chart_no"] for item in filtered] == ["\ucc2843-2"]
