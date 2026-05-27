from app.services.orchestration_evidence import _filter_primary_knia_evidence


def test_centerline_evidence_filter_keeps_primary_collision_matches_only():
    items = [
        {"chart_no": "\ucc2843-2", "accident_party_type": "car_vs_car"},
        {"chart_no": "\ucc2841-1", "accident_party_type": "car_vs_car"},
        {"chart_no": "\ubcf41", "accident_party_type": "car_vs_person"},
    ]

    filtered = _filter_primary_knia_evidence(items, ["centerline", "road_obstruction", "oncoming_vehicle"])

    assert [item["chart_no"] for item in filtered] == ["\ucc2843-2"]


def test_rear_end_filter_drops_intersection_left_turn_primary_links():
    items = [
        {"chart_no": "\ucc2841-1", "title": "후미추돌", "accident_party_type": "car_vs_car", "source_url": "https://accident.knia.or.kr/car41-1"},
        {"chart_no": "\ucc2816-1", "title": "교차로 직진 대 좌회전", "accident_party_type": "car_vs_car", "source_url": "https://accident.knia.or.kr/car16-1"},
        {"chart_no": "\ucc2843-2", "title": "후행 직진 대 선행 진로변경", "accident_party_type": "car_vs_car"},
    ]

    filtered = _filter_primary_knia_evidence(items, ["rear_end", "safe_distance"], "rear_end_collision")

    assert [item["chart_no"] for item in filtered] == ["\ucc2841-1"]
    assert "car16-1" not in str(filtered)
