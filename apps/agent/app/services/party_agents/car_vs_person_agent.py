from __future__ import annotations

from app.services.party_agents.base import BasePartyAgent


class CarVsPersonAgent(BasePartyAgent):
    major_party_type = "car_vs_person"
    default_scenario = "pedestrian_road_work_worker_accident"
    default_tags = ("pedestrian",)

    worker_keywords = (
        "작업자",
        "공사 담당자",
        "공사 인부",
        "도로 작업자",
        "측량 작업자",
        "신호수",
        "교통 통제원",
        "도로 폭 측정",
        "도로공사 인원",
    )

    scenario_candidates = (
        "pedestrian_crosswalk_accident",
        "pedestrian_near_crosswalk_accident",
        "pedestrian_no_crosswalk_road_crossing",
        "pedestrian_road_work_worker_accident",
        "pedestrian_sudden_entry_accident",
        "pedestrian_on_road_edge_accident",
        "pedestrian_construction_zone_accident",
    )
