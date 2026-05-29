from app.services.input_normalizer import normalize_analysis_input
from app.services.knia.knia_matcher import match_knia_charts
from app.services.scenario_classifier import classify_scenario


ROAD_WORKER_TEXT = (
    "공사를 하기 위한 공사 담당자가 도로 폭 측정을 위하여 도로쪽의 차량을 아예 보지도 않고 "
    "갑자기 튀어나와 발생한 사고입니다."
)


def test_road_worker_input_stays_car_vs_person_and_matches_real_knia_chart():
    normalized = normalize_analysis_input(ROAD_WORKER_TEXT, {}, [])
    facts = normalized["structured_facts"]
    scenario = classify_scenario(ROAD_WORKER_TEXT, facts, [])

    assert facts["accident_party_type"] == "car_vs_person"
    assert facts["major_party_type"] == "car_vs_person"
    assert facts["collision_partner_type"] == "person"
    assert facts["direct_collision_partner_type"] == "person"
    assert facts["accident_type"] == "pedestrian_roadway_worker_accident"
    assert scenario["accident_party_type"] == "car_vs_person"
    assert scenario["scenario_type"] == "pedestrian_accident"

    result = match_knia_charts(
        description_text=ROAD_WORKER_TEXT,
        structured_facts=facts,
        selected_keywords=["공사 담당자", "차도 진입"],
        scenario_type=scenario["scenario_type"],
        accident_party_type=scenario["accident_party_type"],
        limit=5,
    )
    items = result["items"]

    assert items
    primary = items[0]
    assert primary["major_party_type"] == "car_vs_person"
    assert str(primary["chart_no"]).startswith("보")
    assert primary["chart_no"] != "보-참고"
    assert primary["chart_no"] in {"보25", "보27", "보28", "보30", "보34", "보22", "보23"}
    assert primary.get("source_url")
    assert primary.get("source_family") == "knia" or primary.get("source_type", "").startswith("knia")
    assert all(str(item.get("major_party_type") or item.get("accident_party_type")) == "car_vs_person" for item in items)
    assert not any(str(item.get("chart_no") or "").startswith(("차", "거", "자", "기", "단")) for item in items)
