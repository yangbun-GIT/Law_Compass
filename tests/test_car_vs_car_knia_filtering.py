import app.services.knia.knia_matcher as knia_matcher


def test_matcher_filters_out_bicycle_and_pedestrian_candidates(monkeypatch):
    def fake_lookup(query, tags, party, limit, *, scenario_type=None):
        return [
            {"chart_no": "자1", "title": "자전거 사고", "accident_party_type": "car_vs_bicycle", "match_score": 0.9},
            {"chart_no": "보1", "title": "보행자 사고", "accident_party_type": "car_vs_person", "match_score": 0.8},
            {"chart_no": "차41-1", "title": "후미추돌", "accident_party_type": "car_vs_car", "match_score": 0.7},
        ]

    monkeypatch.setattr(knia_matcher, "_hybrid_lookup", fake_lookup)
    monkeypatch.setattr(knia_matcher, "_redis_client", lambda: None)

    result = knia_matcher.match_knia_charts(
        description_text="빨간불 신호대기 중 정차해 있었는데 뒤차가 추돌했다. 자전거는 주변에 있었다.",
        structured_facts={"knia_major_party_type": "car_vs_car", "accident_party_type": "car_vs_car"},
        selected_keywords=["자전거", "후미추돌"],
        scenario_type="rear_end_collision",
        accident_party_type="car_vs_car",
    )

    assert [item["chart_no"] for item in result["items"]] == ["차41-1"]
    assert result["requested_party_type"] == "car_vs_car"
    assert result["rejected_mismatch_count"] == 2
    assert "자전거" not in " ".join(result["query_expansion_terms"])


def test_motorcycle_fallback_keeps_motorcycle_reference_and_rejects_person(monkeypatch):
    calls = []

    def fake_lookup(query, tags, party, limit, *, scenario_type=None):
        calls.append((query, tags, party, scenario_type))
        if len(calls) == 1:
            return []
        return [
            {"chart_no": "차77", "title": "오토바이와 진로변경 사고", "accident_party_type": "car_vs_car", "match_score": 0.6},
            {"chart_no": "보1", "title": "보행자 사고", "accident_party_type": "car_vs_person", "match_score": 0.7},
        ]

    monkeypatch.setattr(knia_matcher, "_hybrid_lookup", fake_lookup)
    monkeypatch.setattr(knia_matcher, "_redis_client", lambda: None)

    result = knia_matcher.match_knia_charts(
        description_text="오토바이와 교차로에서 충돌했다.",
        structured_facts={"knia_major_party_type": "car_vs_motorcycle"},
        selected_keywords=[],
        scenario_type="motorcycle_collision",
        accident_party_type="car_vs_motorcycle",
    )

    assert result["fallback_used"] is True
    assert [item["chart_no"] for item in result["items"]] == ["차77"]
