from __future__ import annotations

from app.services.knia.party_guard import (
    filter_terms_by_party,
    is_chart_allowed_for_party,
    reject_mismatched_knia_items,
)


def test_chart_prefix_policy_for_all_major_parties() -> None:
    assert is_chart_allowed_for_party("차43", "car_vs_car")
    assert is_chart_allowed_for_party("보1", "car_vs_person")
    assert is_chart_allowed_for_party("거1", "car_vs_bicycle")
    assert is_chart_allowed_for_party("차100", "car_vs_motorcycle")
    assert is_chart_allowed_for_party("기1", "car_vs_object")
    assert is_chart_allowed_for_party("단1", "single_vehicle")

    assert not is_chart_allowed_for_party("차43", "car_vs_person")
    assert not is_chart_allowed_for_party("거1", "car_vs_person")
    assert not is_chart_allowed_for_party("보1", "car_vs_car")
    assert not is_chart_allowed_for_party("차41", "car_vs_bicycle")


def test_reject_mismatched_items_keeps_only_requested_party() -> None:
    kept, rejected = reject_mismatched_knia_items(
        [
            {"chart_no": "차43", "major_party_type": "car_vs_car", "title": "진로변경"},
            {"chart_no": "보1", "major_party_type": "car_vs_person", "title": "보행자"},
            {"chart_no": "거1", "major_party_type": "car_vs_bicycle", "title": "자전거"},
        ],
        "car_vs_person",
    )

    assert [item["chart_no"] for item in kept] == ["보1"]
    assert {item["chart_no"] for item in rejected} == {"차43", "거1"}


def test_person_terms_remove_vehicle_and_bicycle_pollution() -> None:
    terms = filter_terms_by_party(
        ["보행자", "공사 담당자", "도로 폭 측정", "차43", "차선변경", "후미추돌", "자전거", "차대차"],
        "car_vs_person",
        {"direct_collision_partner_type": "pedestrian"},
    )

    assert "보행자" in terms
    assert "공사 담당자" in terms
    assert "도로 폭 측정" in terms
    assert "차43" not in terms
    assert "차선변경" not in terms
    assert "후미추돌" not in terms
    assert "자전거" not in terms
