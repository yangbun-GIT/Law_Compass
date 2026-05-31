from __future__ import annotations

import re
from typing import Any

from app.services.legal.legal_normalizer import NormalizedLegalDocument, infer_tags

ARTICLE_BOUNDARY_RE = re.compile(r"(?=(제\s*\d+\s*조(?:의\s*\d+)?(?:\s*\([^)]*\))?))")
ARTICLE_NO_RE = re.compile(r"(제\s*\d+\s*조(?:의\s*\d+)?)")


def chunk_legal_document(doc: NormalizedLegalDocument, max_chars: int = 900) -> list[dict[str, Any]]:
    text = re.sub(r"\s+", " ", doc.raw_text or "").strip()
    if not text:
        return []

    units = _article_units(text)
    chunks: list[dict[str, Any]] = []
    for unit in units:
        while len(unit) > max_chars:
            cut = unit.rfind(" ", 0, max_chars)
            if cut < 300:
                cut = max_chars
            chunks.append(_build_chunk(doc, unit[:cut], len(chunks)))
            unit = unit[cut:].strip()
        if unit:
            chunks.append(_build_chunk(doc, unit, len(chunks)))
    return chunks


def _article_units(text: str) -> list[str]:
    pieces = ARTICLE_BOUNDARY_RE.split(text)
    if len(pieces) <= 1:
        return [text]

    units: list[str] = []
    current = ""
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        if ARTICLE_NO_RE.fullmatch(piece):
            if current:
                units.append(current.strip())
            current = piece
        else:
            current = f"{current} {piece}".strip() if current else piece
    if current:
        units.append(current.strip())
    return units or [text]


def _build_chunk(doc: NormalizedLegalDocument, text: str, index: int) -> dict[str, Any]:
    metadata = dict(doc.metadata or {})
    article_no = str(metadata.get("article_no") or "").strip() or _extract_article_no(text)
    article_title = str(metadata.get("article_title") or "").strip() or _extract_article_title(text)
    law_name = str(metadata.get("law_name") or doc.title or "").strip()
    source_url = str(metadata.get("source_url") or doc.source_uri or "").strip()
    tags = sorted(set(doc.scenario_tags + infer_tags(text, doc.keywords)))
    keywords = list(dict.fromkeys(doc.keywords + tags + ([article_no] if article_no else [])))
    summary = text[:260].strip()

    display_metadata = {
        **metadata,
        "source_title": doc.title,
        "article_no": article_no,
        "article_title": article_title,
        "law_name": law_name,
        "source_url": source_url,
    }

    return {
        "chunk_index": index,
        "chunk_text": text,
        "chunk_summary": summary,
        "plain_summary": summary,
        "related_reason": "입력된 사고 사실과 연결해 확인할 수 있는 법령 근거입니다.",
        "display_priority": int(metadata.get("display_priority") or 100),
        "source_url": source_url or None,
        "law_name": law_name or None,
        "article_title": article_title or None,
        "article_no": article_no or None,
        "clause_no": None,
        "scenario_tags": tags,
        "keywords": keywords,
        "metadata": display_metadata,
    }


def _extract_article_no(text: str) -> str | None:
    match = ARTICLE_NO_RE.search(text)
    return re.sub(r"\s+", "", match.group(1)) if match else None


def _extract_article_title(text: str) -> str | None:
    match = re.search(r"제\s*\d+\s*조(?:의\s*\d+)?\s*\(([^)]{1,80})\)", text)
    return match.group(1).strip() if match else None
