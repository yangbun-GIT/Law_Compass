from __future__ import annotations
import json
from app.services.knia.knia_matcher import match_knia_charts

CASES = [
    ("신호대기 중 정차했는데 뒤차가 박았어.", "car_vs_car"),
    ("횡단보도에서 사람과 접촉 사고가 났어.", "car_vs_person"),
    ("자전거랑 부딪혔어.", "car_vs_bicycle"),
    ("혼자 가드레일을 들이받았어.", "car_vs_object"),
    ("빗길에 미끄러져 혼자 사고가 났어.", "single_vehicle"),
]

def main() -> int:
    rows = []
    for text, party in CASES:
        result = match_knia_charts(description_text=text, structured_facts={"accident_party_type": party}, selected_keywords=[], accident_party_type=party, limit=3)
        items = result.get("items") or []
        assert items, f"{text}: no KNIA match"
        assert any(item.get("accident_party_type") == party for item in items), f"{text}: party mismatch {items}"
        first = items[0]
        assert first.get("source_url"), f"{text}: source_url missing"
        assert "match_score" in first, "internal score may exist in agent result for ranking, but gateway/frontend hides it"
        rows.append({"text": text, "expected_party": party, "top": {k: first.get(k) for k in ["chart_no", "title", "accident_party_type", "accident_party_label", "source_url"]}})
    print(json.dumps({"party_type_matcher_tests": "passed", "items": rows}, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
