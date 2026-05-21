from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NormalizedLegalDocument:
    title: str
    doc_type: str
    raw_text: str
    source_name: str
    source_type: str
    source_uri: str | None = None
    provider: str = "local_seed"
    jurisdiction: str = "KR"
    effective_date: str | None = None
    summary: str = ""
    keywords: list[str] = field(default_factory=list)
    scenario_tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def infer_tags(text: str, keywords: list[str] | None = None) -> list[str]:
    haystack = f"{text} {' '.join(keywords or [])}"
    tags: set[str] = set()
    mapping = {
        "어린이보호구역": "school_zone",
        "민식이": "child_protection",
        "제한속도": "speed_limit",
        "12대": "twelve_gross_negligence",
        "중과실": "twelve_gross_negligence",
        "신호": "signal_violation",
        "중앙선": "center_line",
        "횡단보도": "crosswalk",
        "보행자": "pedestrian",
        "음주": "drunk_driving",
        "무면허": "unlicensed",
        "뺑소니": "hit_and_run",
        "도주": "hit_and_run",
        "후미": "rear_end",
        "안전거리": "safe_distance",
        "차선": "lane_change",
        "진로변경": "lane_change",
        "사고 후 조치": "reporting_duty",
        "부상": "injury",
    }
    for word, tag in mapping.items():
        if word in haystack:
            tags.add(tag)
    return sorted(tags)


def normalize_seed_document(item: dict[str, Any]) -> NormalizedLegalDocument:
    text = str(item.get("raw_text") or item.get("text") or item.get("summary") or "")
    keywords = [str(x) for x in item.get("keywords", [])]
    tags = item.get("scenario_tags") or infer_tags(text, keywords)
    return NormalizedLegalDocument(
        title=str(item["title"]),
        doc_type=str(item.get("doc_type", "legal_seed")),
        raw_text=text,
        source_name=str(item.get("source_name", "LawCompass Local Traffic Law Seed")),
        source_type=str(item.get("source_type", "local_seed")),
        source_uri=item.get("source_uri"),
        provider=str(item.get("provider", "local_seed")),
        jurisdiction=str(item.get("jurisdiction", "KR")),
        effective_date=item.get("effective_date"),
        summary=str(item.get("summary", text[:240])),
        keywords=keywords,
        scenario_tags=[str(x) for x in tags],
        metadata=item.get("metadata", {}),
    )


def normalize_law_api_item(item: dict[str, Any], query: str) -> NormalizedLegalDocument:
    title = str(item.get("title") or item.get("법령명한글") or item.get("판례명") or query)
    snippet = str(item.get("snippet") or item.get("조문내용") or item.get("판시사항") or title)
    keywords = [query, title]
    return NormalizedLegalDocument(
        title=title,
        doc_type=str(item.get("doc_type", "law_api")),
        raw_text=snippet,
        source_name=str(item.get("source", "국가법령정보센터 OPEN API")),
        source_type="law_api",
        source_uri=item.get("source_uri"),
        provider="law_api",
        summary=snippet[:240],
        keywords=keywords,
        scenario_tags=infer_tags(f"{title} {snippet}", keywords),
        metadata={"raw": item},
    )
