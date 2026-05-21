from __future__ import annotations

import sys

from app.services.legal.legal_evidence_retriever import retrieve_legal_evidence
from app.services.scenario_classifier import classify_scenario

QUERIES = [
    "어린이보호구역에서 아이와 충돌한 사고 민식이법",
    "신호위반 교차로 충돌 형사책임",
    "후미추돌 안전거리 과실비율",
    "횡단보도 보행자 사고 신고 의무",
    "차선변경 사고 방향지시등 과실",
]


def run(query: str):
    scenario = classify_scenario(query, {}, [])
    result = retrieve_legal_evidence(
        scenario_type=scenario["scenario_type"],
        scenario_tags=scenario["scenario_tags"],
        query=query,
        limit=5,
    )
    print("=" * 80)
    print(f"query={query}")
    print(f"scenario_type={scenario['scenario_type']}")
    print(f"retrieved evidence count={len(result['items'])}")
    print(f"redis cache hit={result['cache_hit']}")
    for idx, item in enumerate(result["items"][:3], start=1):
        print(f"[{idx}] {item.get('title')} / {item.get('source')} / score={float(item.get('score', 0)):.4f}")
        print(f"    tags={item.get('scenario_tags')} keywords={item.get('keywords')}")
        print(f"    snippet={item.get('snippet')}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(" ".join(sys.argv[1:]))
    else:
        for q in QUERIES:
            run(q)
