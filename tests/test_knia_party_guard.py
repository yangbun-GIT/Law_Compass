from app.services.knia.party_guard import (
    canonicalize_party_type,
    filter_tags_by_party,
    filter_terms_by_party,
    is_chart_allowed_for_party,
    reject_mismatched_knia_items,
)


def test_car_vs_car_allows_only_vehicle_chart_prefix():
    assert canonicalize_party_type("truck") == "car_vs_car"
    assert is_chart_allowed_for_party("차41-1", "car_vs_car")
    assert not is_chart_allowed_for_party("보1", "car_vs_car")
    assert not is_chart_allowed_for_party("자2", "car_vs_car")


def test_terms_and_tags_are_filtered_by_party():
    terms = filter_terms_by_party(["후미추돌", "자전거", "보행자", "정차 차량"], "car_vs_car", {})
    tags = filter_tags_by_party(["rear_end", "bicycle", "pedestrian", "safe_distance"], "car_vs_car", {})

    assert terms == ["후미추돌", "정차 차량"]
    assert tags == ["rear_end", "safe_distance"]


def test_rejects_mismatched_knia_items():
    kept, rejected = reject_mismatched_knia_items(
        [
            {"chart_no": "차41-1", "title": "후미추돌"},
            {"chart_no": "보1", "title": "보행자"},
            {"chart_no": "자1", "title": "자전거"},
        ],
        "car_vs_car",
    )

    assert [item["chart_no"] for item in kept] == ["차41-1"]
    assert {item["chart_no"] for item in rejected} == {"보1", "자1"}
