from __future__ import annotations

from app.services.party_agents.base import BasePartyAgent


class CarVsBicycleAgent(BasePartyAgent):
    major_party_type = "car_vs_bicycle"
    default_scenario = "bicycle_collision"
    default_tags = ("bicycle",)
