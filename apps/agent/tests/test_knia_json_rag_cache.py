from app.services.rag import two_stage_cache as cache


def test_knia_json_public_items_infer_chart_and_party_from_chunk_text():
    rows = [
        (
            "chunk-1",
            "과실비율 인정기준",
            "안전거리미확보로 인한 추돌사고 차41-1 양 차량 주행 중 후방 추돌",
            "https://accident.knia.or.kr/example",
            "car_vs_person",
            "차대보행자 사고",
            [],
            [],
            "KNIA 자동차사고 과실비율 정보포털",
            None,
            None,
            None,
            "rag",
            False,
            {},
        )
    ]

    item = cache._rows_to_public_items(rows)[0]

    assert item["chart_no"] == "차41-1"
    assert item["accident_party_type"] == "car_vs_car"
    assert item["accident_party_label"] == "차대차 사고"


def test_knia_literal_patterns_expand_rear_end_terms():
    patterns = cache._literal_patterns("후미추돌 정차 안전거리")

    assert "%후방 추돌%" in patterns
    assert "%안전거리미확보%" in patterns
    assert "%주정차%" in patterns
