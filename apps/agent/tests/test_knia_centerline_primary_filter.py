from app.services.knia.knia_matcher import _is_centerline_primary_mismatch


def test_centerline_primary_context_rejects_rear_end_and_pedestrian_primary_charts():
    tags = ["centerline", "road_obstruction", "oncoming_vehicle"]

    assert _is_centerline_primary_mismatch(tags, {"chart_no": "\ucc2841-1", "accident_party_type": "car_vs_car"})
    assert _is_centerline_primary_mismatch(tags, {"chart_no": "\ucc2842-2", "accident_party_type": "car_vs_car"})
    assert _is_centerline_primary_mismatch(tags, {"chart_no": "\ubcf41", "accident_party_type": "car_vs_person"})
    assert _is_centerline_primary_mismatch(tags, {"title": "\ubcf41 KNIA \uacfc\uc2e4\ube44\uc728 \uc778\uc815\uae30\uc900", "accident_party_type": "car_vs_car"})
    assert _is_centerline_primary_mismatch(tags, {"title": "\ud6c4\ubbf8\ucd94\ub3cc \uacfc\uc2e4\ube44\uc728 \ucc38\uace0 \uae30\uc900"})
    assert _is_centerline_primary_mismatch(tags, {"title": "\ubb34\ub4f1\ud654 \uc815\ucc28 \ucc28\ub7c9 \uc0ac\uace0 \ucc38\uace0 \uae30\uc900"})
    assert _is_centerline_primary_mismatch(tags, {"title": "\ud6a1\ub2e8\ubcf4\ub3c4 \uc55e \uc55e\ucc28 \uc815\ucc28 \ud6c4 \ud6c4\ubc29\ucd94\ub3cc"})
    assert not _is_centerline_primary_mismatch(tags, {"chart_no": "\ucc2843-2", "accident_party_type": "car_vs_car"})
