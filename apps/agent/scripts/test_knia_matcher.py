from __future__ import annotations

import json
import sys
from app.services.knia.knia_matcher import match_knia_charts

query = " ".join(sys.argv[1:]) or "신호대기 중 뒤차가 후미를 추돌했습니다"
result = match_knia_charts(description_text=query, structured_facts={}, selected_keywords=[], scenario_type=None, limit=5)
items = result.get("items") or []
assert items, "KNIA match returned no items. Run migration and collect scripts first."
assert items[0].get("source_url"), "source_url missing"
assert items[0].get("match_reason"), "match_reason missing"
print(json.dumps({"query": query, "cache_hit": result.get("cache_hit"), "top": items[:3]}, ensure_ascii=False, indent=2, default=str))
