from __future__ import annotations

from typing import Any


def build_knia_json_query(description_text: str, facts: dict[str, Any], keywords: list[str]) -> str:
    parts = [description_text or ""]
    for key in ["accident_type", "opponent_behavior", "signal_state", "weather"]:
        if facts.get(key):
            parts.append(str(facts[key]))
    parts.extend(keywords or [])
    return " ".join(parts)
