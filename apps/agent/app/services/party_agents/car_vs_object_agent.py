from __future__ import annotations

from app.services.party_agents.base import BasePartyAgent


class CarVsObjectAgent(BasePartyAgent):
    major_party_type = "car_vs_object"
    default_scenario = "object_collision"
    default_tags = ("object",)
