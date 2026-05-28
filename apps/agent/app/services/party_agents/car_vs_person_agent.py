from __future__ import annotations

from app.services.party_agents.base import BasePartyAgent


class CarVsPersonAgent(BasePartyAgent):
    major_party_type = "car_vs_person"
    default_scenario = "pedestrian_crosswalk_accident"
    default_tags = ("pedestrian",)
