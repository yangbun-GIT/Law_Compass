from __future__ import annotations

from app.services.party_agents.base import BasePartyAgent


class CarVsMotorcycleAgent(BasePartyAgent):
    major_party_type = "car_vs_motorcycle"
    default_scenario = "motorcycle_collision"
    default_tags = ("motorcycle", "two_wheeler")
