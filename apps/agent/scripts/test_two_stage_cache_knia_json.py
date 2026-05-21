from __future__ import annotations
from app.services.rag.two_stage_cache import invalidate_scope, search_knia_json_cached

invalidate_scope("knia_json")
a = search_knia_json_cached("정차 중 뒤차가 박았어", "car_vs_car", limit=3)
print("first", a.get("cache"))
assert not a["cache"]["exact_hit"]
b = search_knia_json_cached("정차 중 뒤차가 박았어", "car_vs_car", limit=3)
print("second", b.get("cache"))
assert b["cache"]["exact_hit"]
c = search_knia_json_cached("정차하고 있는데 뒤 차량이 추돌", "car_vs_car", limit=3)
print("similar", c.get("cache"))
assert c["cache"]["semantic_hit"] or c["items"]
d = search_knia_json_cached("정차 중 뒤차가 박았어", "car_vs_person", limit=3)
print("different party", d.get("cache"))
assert not d["cache"]["exact_hit"]
print("two-stage cache test passed")
