from __future__ import annotations

from app.services.party_agents.base import BasePartyAgent


class SingleVehicleAgent(BasePartyAgent):
    major_party_type = "single_vehicle"
    default_scenario = "single_vehicle_accident"
    default_tags = ("single_vehicle",)
