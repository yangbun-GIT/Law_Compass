from __future__ import annotations

from typing import Any


_STATIC_CHUNKS: list[dict[str, Any]] = [
    {
        "chunk_id": "static:rt-law:safe-distance",
        "title": "Road Traffic Act (safe distance)",
        "source": "Local Legal Fallback",
        "snippet": "Check safe following distance and possible sudden braking duty-of-care issues.",
        "keywords": ["rear", "collision", "distance", "brake", "tail"],
        "score": 0.39,
    },
    {
        "chunk_id": "static:rt-law:signal",
        "title": "Road Traffic Act (signal compliance)",
        "source": "Local Legal Fallback",
        "snippet": "At intersections, signal state, entry timing, and right-of-way are core factors.",
        "keywords": ["intersection", "signal", "left", "right", "straight"],
        "score": 0.38,
    },
    {
        "chunk_id": "static:rt-law:lane-change",
        "title": "Road Traffic Act (lane change)",
        "source": "Local Legal Fallback",
        "snippet": "Lane-change disputes depend on indicator usage, blind-spot checks, and abrupt merge behavior.",
        "keywords": ["lane", "change", "merge", "blind spot"],
        "score": 0.38,
    },
    {
        "chunk_id": "static:special-act:criminal",
        "title": "Traffic Accident Special Act (criminal scope)",
        "source": "Local Legal Fallback",
        "snippet": "Criminal liability review changes significantly by gross negligence and injury severity.",
        "keywords": ["criminal", "report", "gross", "injury", "special"],
        "score": 0.41,
    },
    {
        "chunk_id": "static:criminal-law:injury",
        "title": "Criminal Code (negligent injury framework)",
        "source": "Local Legal Fallback",
        "snippet": "When injury exists, duty-of-care breach, foreseeability, and causation become key.",
        "keywords": ["injury", "causation", "duty"],
        "score": 0.37,
    },
    {
        "chunk_id": "static:fault-guide:rear-end",
        "title": "Fault Ratio Guide (rear-end pattern)",
        "source": "Local Legal Fallback",
        "snippet": "Rear-end collisions into stopped or slow vehicles often imply higher following-vehicle fault.",
        "keywords": ["rear", "collision", "stopped", "slow", "fault"],
        "score": 0.43,
    },
    {
        "chunk_id": "static:fault-guide:intersection",
        "title": "Fault Ratio Guide (intersection pattern)",
        "source": "Local Legal Fallback",
        "snippet": "Intersection fault combines signal compliance, first-entry, visibility, and speed factors.",
        "keywords": ["intersection", "signal", "speed", "fault"],
        "score": 0.42,
    },
    {
        "chunk_id": "static:insurance:process",
        "title": "Insurance Process Checklist",
        "source": "Local Legal Fallback",
        "snippet": "Secure claim number, dashcam/photo/witness records, medical notes, and repair estimate documents.",
        "keywords": ["insurance", "claim", "medical", "estimate", "evidence"],
        "score": 0.36,
    },
]


def retrieve_static_legal_chunks(query: str, limit: int = 5) -> list[dict[str, Any]]:
    q = (query or "").lower()
    ranked: list[tuple[float, dict[str, Any]]] = []
    for item in _STATIC_CHUNKS:
        keyword_hits = sum(1 for k in item["keywords"] if k.lower() in q)
        score = float(item["score"]) + keyword_hits * 0.02
        ranked.append((score, {k: v for k, v in item.items() if k != "keywords"} | {"score": round(score, 3)}))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in ranked[: max(1, limit)]]
