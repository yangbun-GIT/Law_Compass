from __future__ import annotations

import re

from app.services.legal.legal_normalizer import NormalizedLegalDocument, infer_tags


def chunk_legal_document(doc: NormalizedLegalDocument, max_chars: int = 900) -> list[dict]:
    text = re.sub(r"\s+", " ", doc.raw_text or "").strip()
    if not text:
        return []

    article_splits = re.split(r"(?=(?:제\s*\d+\s*조|제\d+조|\d+\.\s))", text)
    units = [x.strip() for x in article_splits if x.strip()] or [text]

    chunks: list[dict] = []
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


def _build_chunk(doc: NormalizedLegalDocument, text: str, index: int) -> dict:
    article_no = None
    match = re.search(r"제\s*(\d+)\s*조", text)
    if match:
        article_no = f"제{match.group(1)}조"
    tags = sorted(set(doc.scenario_tags + infer_tags(text, doc.keywords)))
    return {
        "chunk_index": index,
        "chunk_text": text,
        "chunk_summary": text[:260],
        "article_no": article_no,
        "clause_no": None,
        "scenario_tags": tags,
        "keywords": list(dict.fromkeys(doc.keywords + tags)),
        "metadata": {"source_title": doc.title},
    }
