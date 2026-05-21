from __future__ import annotations
import sys
from app.services.knia.taxonomy import infer_party_type_from_text
from app.services.rag.two_stage_cache import search_knia_json_cached

queries = [sys.argv[1]] if len(sys.argv) > 1 else [
    "정차 중 뒤차가 박았어",
    "횡단보도에서 사람과 접촉 사고",
    "자전거랑 부딪혔어",
    "혼자 가드레일을 들이받았어",
]
for q in queries:
    party = infer_party_type_from_text(q)["accident_party_type"]
    result = search_knia_json_cached(q, party, limit=5)
    print({"query": q, "accident_party_type": party, "count": len(result["items"]), "cache": result.get("cache")})
    for item in result["items"][:3]:
        print(" -", item.get("title"), item.get("accident_party_label"), item.get("source_url"))
    assert result["items"], f"검색 결과가 없습니다: {q}"
    assert all(x.get("source_url") for x in result["items"]), "source_url 없는 결과가 있습니다"
print("KNIA JSON RAG test passed")
