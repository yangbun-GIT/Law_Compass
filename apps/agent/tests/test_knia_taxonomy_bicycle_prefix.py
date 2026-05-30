from app.services.knia.knia_json_repository import _party_prefix_patterns
from app.services.knia.taxonomy import classify_knia_accident_party_type, infer_party_type_from_text


def test_bicycle_prefix_overrides_incorrect_stored_party_type():
    result = classify_knia_accident_party_type(
        {
            "chart_no": "거33-1",
            "title": "자전거도로 사고",
            "accident_party_type": "car_vs_person",
            "accident_summary": "자전거와 차량의 충돌 사고",
        }
    )

    assert result["accident_party_type"] == "car_vs_bicycle"
    assert result["accident_party_label"] == "차대자전거 사고"


def test_bicycle_keywords_are_enough_for_taxonomy_search_context():
    assert infer_party_type_from_text("자전거도로에서 발생한 자전거 사고", {}) == "car_vs_bicycle"


def test_repository_bicycle_party_filter_includes_both_knia_prefixes():
    assert _party_prefix_patterns("car_vs_bicycle") == ["자%", "거%"]
