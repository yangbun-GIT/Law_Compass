from __future__ import annotations

import pytest

from app.services.party_agents.router import route_party_agent


@pytest.mark.parametrize(
    ("text", "expected_party", "expected_partner"),
    [
        (
            "현재 공사를 하기 위한 공사 담당자가 도로 폭 측정을 위하여, 도로쪽의 차량을 아예 보지도 않고, 갑자기 튀어나와 발생한 사고입니다.",
            "car_vs_person",
            "pedestrian",
        ),
        ("횡단보도에서 보행자와 충돌했다.", "car_vs_person", "pedestrian"),
        ("어두운 도로에서 사람이 갑자기 차도로 뛰어나와 충돌했다.", "car_vs_person", "pedestrian"),
        ("교차로에서 우회전 중 보행자와 충돌했다.", "car_vs_person", "pedestrian"),
        ("교차로에서 직진 중 상대 차량과 충돌했다.", "car_vs_car", "vehicle"),
        ("상대 차량이 깜빡이 없이 차선변경하다가 내 차 옆을 충돌했다.", "car_vs_car", "vehicle"),
        ("자전거와 직접 충돌했다.", "car_vs_bicycle", "bicycle"),
        ("오토바이와 교차로에서 충돌했다.", "car_vs_motorcycle", "motorcycle"),
        ("도로 공사장 라바콘과 방호벽을 들이받았다.", "car_vs_object", "object"),
        ("늦은 밤 교량 밑에 스텔스로 주차해둔 음주운전 트럭과 부딪혀 폐차 수준으로 파손됐다.", "car_vs_car", "vehicle"),
    ],
)
def test_direct_collision_target_wins_over_environment_context(text: str, expected_party: str, expected_partner: str) -> None:
    result = route_party_agent(
        description_text=text,
        structured_facts={},
        selected_keywords=[],
        video_metadata={},
    )

    assert result["major_party_type"] == expected_party
    assert result["direct_collision_partner_type"] == expected_partner


def test_road_worker_text_sets_person_facts_patch() -> None:
    text = "현재 공사를 하기 위한 공사 담당자가 도로 폭 측정을 위하여, 도로쪽의 차량을 아예 보지도 않고, 갑자기 튀어나와 발생한 사고입니다."
    result = route_party_agent(
        description_text=text,
        structured_facts={},
        selected_keywords=[],
        video_metadata={},
    )
    patch = result["facts_patch"]

    assert result["major_party_type"] == "car_vs_person"
    assert result["scenario_type"] in {"pedestrian_road_work_worker_accident", "pedestrian_sudden_entry_accident"}
    assert patch["direct_collision_target"] == "road_work_worker"
    assert patch["pedestrian_worker"] is True
    assert patch["road_work_context"] is True
    assert patch["pedestrian_sudden_entry"] is True
    assert "car_vs_car" in result["excluded_party_types"]
