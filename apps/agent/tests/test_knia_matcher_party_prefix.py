from app.services.knia import knia_matcher
from app.services.knia.party_guard import reject_mismatched_knia_items


def test_knia_matcher_prefers_chart_prefix_over_stale_party_metadata():
    row = {
        "chart_no": "차41-1",
        "major_party_type": "car_vs_person",
        "accident_party_type": "car_vs_person",
    }

    assert knia_matcher._row_party_type(row) == "car_vs_car"


def test_party_guard_keeps_chart_prefix_match_with_stale_metadata():
    kept, rejected = reject_mismatched_knia_items(
        [
            {
                "chart_no": "차41-1",
                "major_party_type": "car_vs_person",
                "accident_party_type": "car_vs_person",
            }
        ],
        "car_vs_car",
    )

    assert len(kept) == 1
    assert rejected == []
