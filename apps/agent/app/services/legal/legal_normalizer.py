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


TAG_KEYWORDS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("어린이보호구역", "민식이", "스쿨존"), "school_zone"),
    (("제한속도", "속도위반", "과속"), "speed_limit"),
    (("12대 중과실", "중과실"), "twelve_gross_negligence"),
    (("신호", "적색", "녹색", "황색"), "signal_violation"),
    (("중앙선", "중앙선침범"), "center_line"),
    (("횡단보도", "보행자 보호"), "crosswalk"),
    (("보행자", "사람", "도로 작업자"), "pedestrian"),
    (("음주", "음주운전"), "drunk_driving"),
    (("무면허",), "unlicensed"),
    (("도주", "뺑소니", "구호조치"), "hit_and_run"),
    (("후미", "후방", "추돌"), "rear_end"),
    (("안전거리", "전방주시"), "safe_distance"),
    (("차선변경", "진로변경", "끼어들기"), "lane_change"),
    (("사고 후 조치", "신고의무", "보험 접수"), "reporting_duty"),
    (("부상", "상해", "인명피해"), "injury"),
    (("자전거", "자전거도로"), "bicycle"),
    (("정차", "주차", "비상등", "스텔스"), "stopped_vehicle"),
)


def infer_tags(text: str, keywords: list[str] | None = None) -> list[str]:
    haystack = f"{text} {' '.join(keywords or [])}".lower()
    tags: set[str] = set()
    for words, tag in TAG_KEYWORDS:
        if any(word.lower() in haystack for word in words):
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
        source_uri=item.get("source_uri") or item.get("source_url"),
        provider=str(item.get("provider", "local_seed")),
        jurisdiction=str(item.get("jurisdiction", "KR")),
        effective_date=item.get("effective_date"),
        summary=str(item.get("summary", text[:240])),
        keywords=keywords,
        scenario_tags=[str(x) for x in tags],
        metadata=dict(item.get("metadata") or {}),
    )


def normalize_law_api_item(item: dict[str, Any], query: str) -> NormalizedLegalDocument:
    title = str(
        item.get("title")
        or item.get("법령명한글")
        or item.get("법령명")
        or item.get("판례명")
        or item.get("사건명")
        or query
    )
    snippet = str(
        item.get("snippet")
        or item.get("조문내용")
        or item.get("판시사항")
        or item.get("제개정구분명")
        or item.get("법령구분명")
        or title
    )
    source_uri = item.get("source_uri") or item.get("source_url")
    keywords = [query, title]
    metadata = {
        "provider": "law_api",
        "source_family": item.get("source_family") or "law_api_search",
        "retrieval_note": item.get("retrieval_note") or "law_api_search",
        "law_name": item.get("law_name") or title,
        "law_id": item.get("law_id"),
        "mst": item.get("mst"),
        "source_url": source_uri,
        "detail_fetch_failed": bool(item.get("detail_fetch_failed")),
        "display_priority": 60,
    }
    return NormalizedLegalDocument(
        title=title,
        doc_type=str(item.get("doc_type", "law_api")),
        raw_text=snippet,
        source_name=str(item.get("source", "국가법령정보센터 OPEN API")),
        source_type="law_api",
        source_uri=source_uri,
        provider="law_api",
        effective_date=item.get("effective_date"),
        summary=snippet[:240],
        keywords=keywords,
        scenario_tags=infer_tags(f"{title} {snippet}", keywords),
        metadata={key: value for key, value in metadata.items() if value not in (None, "")},
    )


def normalize_law_detail_article(item: dict[str, Any], query: str = "도로교통법") -> NormalizedLegalDocument:
    law_name = str(item.get("law_name") or "도로교통법")
    article_no = str(item.get("article_no") or "").strip()
    article_title = str(item.get("article_title") or "").strip()
    title = " ".join(part for part in [law_name, article_no, article_title] if part).strip() or law_name
    raw_text = str(item.get("article_text") or item.get("snippet") or title).strip()
    source_uri = item.get("source_url") or item.get("source_uri")
    keywords = [value for value in [query, law_name, article_no, article_title] if value]
    metadata = {
        "provider": item.get("provider") or "law_api",
        "source_family": item.get("source_family") or "legal_db_article",
        "retrieval_note": item.get("retrieval_note") or "law_api_detail",
        "law_name": law_name,
        "law_id": item.get("law_id"),
        "mst": item.get("mst"),
        "article_no": article_no,
        "article_title": article_title,
        "source_url": source_uri,
        "effective_date": item.get("effective_date"),
        "promulgation_date": item.get("promulgation_date"),
        "display_priority": 25 if not item.get("detail_fetch_failed") else 60,
        "detail_fetch_failed": bool(item.get("detail_fetch_failed")),
    }
    return NormalizedLegalDocument(
        title=title,
        doc_type="law_api_article" if not item.get("detail_fetch_failed") else "law_api_snippet",
        raw_text=raw_text,
        source_name="국가법령정보센터 OPEN API(법령 조문)",
        source_type="law_api",
        source_uri=source_uri,
        provider="law_api",
        effective_date=item.get("effective_date"),
        summary=str(item.get("plain_summary") or raw_text[:240]),
        keywords=keywords,
        scenario_tags=infer_tags(f"{title} {raw_text}", keywords),
        metadata={key: value for key, value in metadata.items() if value not in (None, "")},
    )
