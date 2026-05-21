from app.services.knia.knia_matcher import _is_strict_scenario_mismatch


def test_bicycle_scenario_rejects_unrelated_car_chart():
    assert _is_strict_scenario_mismatch(
        "bicycle_collision",
        {"chart_no": "\ucc2843-2", "accident_party_type": "car_vs_car"},
        "lane change car-to-car accident",
    )
    assert not _is_strict_scenario_mismatch(
        "bicycle_collision",
        {"chart_no": "\uc7901-1", "accident_party_type": "car_vs_bicycle"},
        "car and bicycle collision",
    )


def test_pedestrian_scenario_rejects_unrelated_car_chart():
    assert _is_strict_scenario_mismatch(
        "pedestrian_crosswalk_accident",
        {"chart_no": "\ucc2841-1", "accident_party_type": "car_vs_car"},
        "rear-end car-to-car accident",
    )
    assert not _is_strict_scenario_mismatch(
        "pedestrian_crosswalk_accident",
        {"chart_no": "\ubcf41-1", "accident_party_type": "car_vs_person"},
        "crosswalk pedestrian accident",
    )
