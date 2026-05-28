from __future__ import annotations

from app.services.party_agents.base import BasePartyAgent


class CarVsCarAgent(BasePartyAgent):
    major_party_type = "car_vs_car"
    default_scenario = "general_vehicle_collision"
    default_tags = ("vehicle",)
