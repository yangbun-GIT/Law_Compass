from __future__ import annotations

import json
from app.services.orchestrator import analyze_case

FORBIDDEN = ["chunk_id", "score", "model_info", "embedding", "raw HTML", "S3", "match_score"]

if __name__ == "__main__":
    result = analyze_case(
        "신호대기 중 정차했는데 뒤 차량이 후미를 추돌했습니다. 목이 아픕니다.",
        structured_facts={"accident_type": "rear_end_collision", "stopped": True, "injury": True, "opponent_behavior": "rear_collision"},
        selected_keywords=["후미추돌", "안전거리", "대인접수"],
        analysis_mode="fault-focused",
    )
    report = result.get("elderly_friendly_report") or {}
    assert report.get("related_fault_standard"), "related_fault_standard missing"
    text = json.dumps(report, ensure_ascii=False)
    for word in FORBIDDEN:
        assert word not in text, f"forbidden word in easy report: {word}"
    related_video = report.get("related_video") or {}
    assert related_video.get("display_mode") in ("external_link", "embed", None)
    print(json.dumps({"knia_report_integration": "passed", "headline": report.get("headline"), "related_fault_standard": report.get("related_fault_standard"), "related_video": related_video}, ensure_ascii=False, indent=2))
