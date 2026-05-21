from __future__ import annotations

from typing import Any


def gate_public_evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    safe = []
    for item in items:
        if not item.get("source_url"):
            continue
        safe.append({
            "title": item.get("title") or "KNIA 과실비율 기준",
            "summary": item.get("summary") or "원문 기준을 확인해 주세요.",
            "source_url": item.get("source_url"),
            "accident_party_label": item.get("accident_party_label") or "사고유형 확인 필요",
            "display_tags": item.get("display_tags") or [],
            "attribution": item.get("attribution") or "자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털",
        })
    return safe
