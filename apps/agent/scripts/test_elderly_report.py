from __future__ import annotations
import json
import sys
from typing import Any
from app.services.orchestrator import analyze_scenario

FORBIDDEN = ["rear_end_collision", "school_zone_child_accident", "intersection_signal_violation", "lane_change_collision", "REAR_END", "SAFE_DISTANCE", "score", "chunk_id", "model_info", "medium", "high", "low"]
SCENARIOS: list[dict[str, Any]] = [
    {"name": "후미추돌", "description_text": "신호대기 중 정차했는데 뒤 차량이 추돌했습니다. 목이 아픕니다.", "structured_facts": {"accident_type": "rear_end_collision", "stopped": True, "injury": True, "signal_state": "red", "opponent_behavior": "rear_collision"}, "selected_keywords": ["후미추돌", "안전거리", "대인접수", "진단서"], "analysis_mode": "fault-focused"},
    {"name": "어린이보호구역", "description_text": "어린이보호구역에서 아이와 접촉 사고가 났습니다.", "structured_facts": {"accident_type": "pedestrian", "school_zone": True, "victim_is_child": True, "injury": True, "crosswalk_nearby": True}, "selected_keywords": ["민식이법", "어린이보호구역", "보행자", "형사책임"], "analysis_mode": "criminal-liability-focused"},
    {"name": "차선변경", "description_text": "상대 차량이 방향지시등 없이 갑자기 차선을 변경해 충돌했습니다.", "structured_facts": {"accident_type": "lane_change_collision", "lane_change": True, "turn_signal": False, "side_collision": True}, "selected_keywords": ["차선변경", "방향지시등", "측면충돌"], "analysis_mode": "fault-focused"},
    {"name": "교차로 신호위반", "description_text": "교차로에서 상대 차량이 빨간불에 진입해 충돌했습니다.", "structured_facts": {"accident_type": "intersection_collision", "intersection": True, "opponent_signal_violation": True, "signal_state": "green"}, "selected_keywords": ["신호위반", "교차로", "과실비율"], "analysis_mode": "fault-focused"},
]

def default_visible_text(report: dict[str, Any]) -> str:
    visible = {k: report.get(k) for k in ["headline", "summary_for_user", "top_actions", "fault_explanation", "insurance_explanation", "legal_explanation", "legal_basis_cards", "missing_info"]}
    return json.dumps(visible, ensure_ascii=False)

def assert_easy_report(result: dict[str, Any], name: str) -> None:
    report = result.get("elderly_friendly_report")
    assert isinstance(report, dict) and report, f"{name}: elderly_friendly_report missing"
    assert report.get("headline"), f"{name}: headline missing"
    assert len(report.get("top_actions") or []) >= 3, f"{name}: top actions missing"
    assert report.get("fault_explanation", {}).get("easy_explanation"), f"{name}: fault easy explanation missing"
    cards = report.get("legal_basis_cards") or []
    assert len(cards) >= 1, f"{name}: legal basis card missing"
    assert cards[0].get("easy_explanation"), f"{name}: legal basis easy explanation missing"
    visible_text = default_visible_text(report)
    leaked = [token for token in FORBIDDEN if token in visible_text]
    assert not leaked, f"{name}: internal tokens leaked in default cards: {leaked}"
    details = report.get("detail_sections") or {}
    assert isinstance(details.get("raw_evidence", []), list), f"{name}: detail raw evidence invalid"

def main() -> int:
    results = []
    for scenario in SCENARIOS:
        result = analyze_scenario(scenario)
        assert_easy_report(result, scenario["name"])
        report = result["elderly_friendly_report"]
        results.append({"name": scenario["name"], "headline": report["headline"], "top_action_count": len(report["top_actions"]), "legal_basis_count": len(report["legal_basis_cards"])})
    print(json.dumps({"elderly_report_tests": "passed", "scenarios": results}, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    try: raise SystemExit(main())
    except AssertionError as exc:
        print(f"elderly_report_tests=failed {exc}", file=sys.stderr)
        raise SystemExit(1)
