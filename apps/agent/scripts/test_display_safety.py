from __future__ import annotations

import json
import sys
from typing import Any
from app.services.orchestrator import analyze_scenario

FORBIDDEN = [
    "chunk_id", "score", "model_info", "cache_key", "rag_top_k", "ai_profile", "llm_enabled", "orchestrator", "scenario_classifier",
    "rear_end_collision", "school_zone_child_accident", "REAR_END_SAFE_DISTANCE", "ROAD_ACCIDENT_REPORTING_DUTY",
    "null", "true", "false", "?" + "??", "??" + "??", '"injury":', '"stopped":', '"weather":'
]
SCENARIOS: list[dict[str, Any]] = [
    {"name": "후미추돌", "description_text": "신호대기 중 정차했는데 뒤 차량이 추돌했습니다. 목이 아픕니다.", "structured_facts": {"accident_type": "rear_end_collision", "stopped": True, "injury": True, "weather": "모름", "opponent_behavior": "rear_collision", "signal_state": "red"}, "selected_keywords": ["후미추돌", "안전거리", "대인접수", "진단서"], "analysis_mode": "fault-focused"},
    {"name": "어린이보호구역", "description_text": "어린이보호구역에서 아이와 접촉 사고가 났습니다.", "structured_facts": {"accident_type": "pedestrian", "school_zone": True, "victim_is_child": True, "injury": True, "crosswalk_nearby": True}, "selected_keywords": ["민식이법", "어린이보호구역", "보행자", "형사책임"], "analysis_mode": "criminal-liability-focused"},
]

def fail_if_forbidden(report: dict[str, Any], name: str) -> None:
    text = json.dumps(report, ensure_ascii=False)
    leaked = [token for token in FORBIDDEN if token in text]
    if leaked:
        raise AssertionError(f"{name}: forbidden display tokens leaked: {leaked}\n{text[:1200]}")
    if not report.get("headline"):
        raise AssertionError(f"{name}: headline missing")
    if len(report.get("top_actions") or []) < 3:
        raise AssertionError(f"{name}: top actions missing")
    if not report.get("legal_basis_cards"):
        raise AssertionError(f"{name}: legal basis missing")

def main() -> int:
    checked = []
    for scenario in SCENARIOS:
        result = analyze_scenario(scenario)
        report = result.get("elderly_friendly_report") or {}
        fail_if_forbidden(report, scenario["name"])
        checked.append({"name": scenario["name"], "headline": report.get("headline")})
    print(json.dumps({"display_safety": "passed", "checked": checked}, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"display_safety=failed {exc}", file=sys.stderr)
        raise SystemExit(1)
