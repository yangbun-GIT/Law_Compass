from __future__ import annotations

from typing import Any


def rerank_evidence(items: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    # 점수는 사용자에게 노출하지 않고, 표시 품질만 위해 내부 정렬만 수행합니다.
    words = [w for w in query.split() if len(w) >= 2]
    def score(item: dict[str, Any]) -> int:
        text = " ".join([str(item.get("title", "")), str(item.get("summary", "")), " ".join(item.get("display_tags") or [])])
        return sum(1 for w in words if w in text)
    return sorted(items, key=score, reverse=True)
