from app.services.input_normalizer import normalize_analysis_input
from app.services.knia.knia_matcher import match_knia_charts
from app.services.scenario_classifier import classify_scenario


def _match(text: str, facts: dict | None = None, scenario_type: str | None = None):
    normalized = normalize_analysis_input(text, facts or {}, [])
    scenario = classify_scenario(text, normalized["structured_facts"], [])
    return normalized, scenario, match_knia_charts(
        description_text=text,
        structured_facts=normalized["structured_facts"],
        selected_keywords=[],
        scenario_type=scenario_type or scenario["scenario_type"],
        accident_party_type=scenario["accident_party_type"],
        limit=5,
    )


def test_one_side_traffic_sign_intersection_matches_chart7_subchart():
    text = "한쪽 지시표지가 있는 교차로에서 내 차는 녹색 직진, 상대차는 적색 직진으로 측면에서 진입해 충돌했습니다."
    _, scenario, result = _match(text)
    primary = result["items"][0]
    menu_path = " ".join(primary.get("menu_path") or [])

    assert scenario["accident_party_type"] == "car_vs_car"
    assert primary["major_party_type"] == "car_vs_car"
    assert str(primary["chart_no"]).startswith("차7")
    assert primary.get("subchart_no") in {None, "차7-1"} or str(primary.get("display_chart_no", "")).startswith("차7")
    assert "교차로" in menu_path
    assert "한쪽 지시표지" in menu_path
    assert "직진 대 직진" in menu_path
    assert primary.get("source_url")


def test_same_direction_lane_change_matches_chart43_family():
    text = "상대 차량이 같은 방향에서 차선변경으로 끼어들어 내 직진 차량과 충돌했습니다."
    _, scenario, result = _match(text, {"lane_change_actor": "opponent"}, "lane_change_collision")
    primary = result["items"][0]
    menu_path = " ".join(primary.get("menu_path") or [])

    assert scenario["accident_party_type"] == "car_vs_car"
    assert primary["major_party_type"] == "car_vs_car"
    assert str(primary["chart_no"]).startswith("차43")
    assert "같은 방향 진행차량 상호 간의 사고" in menu_path
    assert "진로변경 사고" in menu_path


def test_following_vehicle_rear_end_matches_chart41_family():
    text = "내 차가 앞차를 들이받았습니다. 앞차가 갑자기 급정거했습니다."
    normalized, scenario, result = _match(text, {"user_vehicle_role": "following_vehicle"}, "rear_end_collision")
    primary = result["items"][0]
    menu_path = " ".join(primary.get("menu_path") or [])

    assert scenario["accident_party_type"] == "car_vs_car"
    assert str(primary["chart_no"]).startswith("차41")
    assert "같은 방향 진행차량 상호 간의 사고" in menu_path
    assert normalized["structured_facts"].get("user_vehicle_role") in {"following_vehicle", "rear_vehicle", None}


def test_stealth_parked_truck_matches_same_major_parked_vehicle_candidate():
    text = "야간에 도로에 스텔스로 주차된 트럭을 들이받았습니다."
    _, scenario, result = _match(text, {}, "stealth_illegal_parked_vehicle_collision")
    primary = result["items"][0]

    assert scenario["accident_party_type"] == "car_vs_car"
    assert primary["major_party_type"] == "car_vs_car"
    assert str(primary["chart_no"]).startswith("차42") or primary.get("reference_only") is True
    assert not str(primary["chart_no"]).startswith(("보", "거", "자", "기", "단"))
