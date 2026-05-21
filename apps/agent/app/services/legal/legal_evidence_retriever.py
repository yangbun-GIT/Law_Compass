from __future__ import annotations

import hashlib
import json
import os
import random
import re
from typing import Any

import psycopg
import redis

from app.services.elderly_friendly.ui_text_mapper import evidence_confidence_label
from app.services.legal.legal_vectorizer import vectorize_text

DB_URL = os.getenv("DATABASE_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "")


def normalize_query(query: str) -> str:
    lowered = (query or "").lower()
    lowered = re.sub(r"[^\w?-?\s]", " ", lowered)
    replacements = {
        "???": "??",
        "??": "??",
        "??": "??",
        "???": "?? ??",
        "???": "?? ??",
        "??": "????",
        "???": "???? ???????",
    }
    for old, new in replacements.items():
        lowered = lowered.replace(old, new)
    return " ".join(lowered.split())


def _cache_key(query: str, tags: list[str], limit: int) -> str:
    raw = json.dumps({"q": normalize_query(query), "tags": sorted(tags), "limit": limit}, ensure_ascii=False)
    return "rag:v2:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _redis_client():
    if not REDIS_URL:
        return None
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)


def build_legal_query(
    scenario_type: str,
    scenario_tags: list[str],
    description_text: str,
    facts: dict[str, Any],
    selected_keywords: list[str],
    video_context: dict[str, Any] | None = None,
) -> str:
    return normalize_query(
        " ".join(
            [
                scenario_type,
                " ".join(scenario_tags),
                description_text or "",
                " ".join(selected_keywords or []),
                json.dumps(facts or {}, ensure_ascii=False),
                (video_context or {}).get("summary", ""),
            ]
        )
    )


def retrieve_legal_evidence(
    *,
    scenario_type: str,
    scenario_tags: list[str],
    query: str,
    limit: int = 8,
) -> dict[str, Any]:
    cache = _redis_client()
    key = _cache_key(query, scenario_tags, limit)
    if cache:
        cached = cache.get(key)
        if cached:
            try:
                return {"items": json.loads(cached), "cache_hit": True, "cache_key": key}
            except Exception:
                pass

    items = _retrieve_from_postgres(query=query, scenario_type=scenario_type, scenario_tags=scenario_tags, limit=limit)
    if cache:
        # Cache only display metadata/result ids. No vectors or full legal corpus are stored in Redis.
        cache.setex(key, 900 + random.randint(0, 180), json.dumps(items, ensure_ascii=False))
    return {"items": items, "cache_hit": False, "cache_key": key}


def _retrieve_from_postgres(query: str, scenario_type: str, scenario_tags: list[str], limit: int) -> list[dict[str, Any]]:
    if not DB_URL:
        return []
    normalized = normalize_query(query)
    vec, _model = vectorize_text(normalized)
    sql = """
    WITH tag_candidates AS (
      SELECT kc.id, kd.id AS document_id, kd.title, kd.doc_type, kd.metadata AS document_metadata,
             ks.name AS source_name, ks.source_uri,
             kc.chunk_text, kc.chunk_summary, kc.article_no, kc.clause_no, kc.scenario_tags, kc.keywords,
             kc.plain_summary, kc.related_reason, kc.display_priority, kc.source_url, kc.law_name, kc.article_title,
             CASE WHEN kc.scenario_tags && %(tags)s::text[] THEN 0.24 ELSE 0 END AS tag_score
      FROM kb_chunks kc
      JOIN kb_documents kd ON kd.id = kc.document_id
      JOIN kb_sources ks ON ks.id = kd.source_id
      WHERE (%(tags)s::text[] = '{}'::text[] OR kc.scenario_tags && %(tags)s::text[])
      ORDER BY kc.display_priority ASC
      LIMIT 60
    ), fts AS (
      SELECT kc.id, kd.id AS document_id, kd.title, kd.doc_type, kd.metadata AS document_metadata,
             ks.name AS source_name, ks.source_uri,
             kc.chunk_text, kc.chunk_summary, kc.article_no, kc.clause_no, kc.scenario_tags, kc.keywords,
             kc.plain_summary, kc.related_reason, kc.display_priority, kc.source_url, kc.law_name, kc.article_title,
             ts_rank_cd(kc.tsv, plainto_tsquery('simple', %(q)s)) AS fts_score
      FROM kb_chunks kc
      JOIN kb_documents kd ON kd.id = kc.document_id
      JOIN kb_sources ks ON ks.id = kd.source_id
      WHERE kc.tsv @@ plainto_tsquery('simple', %(q)s)
      ORDER BY fts_score DESC
      LIMIT 60
    ), vec AS (
      SELECT kc.id, kd.id AS document_id, kd.title, kd.doc_type, kd.metadata AS document_metadata,
             ks.name AS source_name, ks.source_uri,
             kc.chunk_text, kc.chunk_summary, kc.article_no, kc.clause_no, kc.scenario_tags, kc.keywords,
             kc.plain_summary, kc.related_reason, kc.display_priority, kc.source_url, kc.law_name, kc.article_title,
             1 - (ke.embedding <=> %(vec)s::vector) AS vec_score
      FROM kb_embeddings ke
      JOIN kb_chunks kc ON kc.id = ke.chunk_id
      JOIN kb_documents kd ON kd.id = kc.document_id
      JOIN kb_sources ks ON ks.id = kd.source_id
      ORDER BY ke.embedding <=> %(vec)s::vector
      LIMIT 60
    ), merged AS (
      SELECT
        COALESCE(t.id, f.id, v.id) AS id,
        COALESCE(t.document_id, f.document_id, v.document_id) AS document_id,
        COALESCE(t.title, f.title, v.title) AS title,
        COALESCE(t.doc_type, f.doc_type, v.doc_type) AS doc_type,
        COALESCE(t.document_metadata, f.document_metadata, v.document_metadata) AS document_metadata,
        COALESCE(t.source_name, f.source_name, v.source_name) AS source_name,
        COALESCE(t.source_uri, f.source_uri, v.source_uri) AS source_uri,
        COALESCE(t.chunk_text, f.chunk_text, v.chunk_text) AS chunk_text,
        COALESCE(t.chunk_summary, f.chunk_summary, v.chunk_summary) AS chunk_summary,
        COALESCE(t.article_no, f.article_no, v.article_no) AS article_no,
        COALESCE(t.clause_no, f.clause_no, v.clause_no) AS clause_no,
        COALESCE(t.scenario_tags, f.scenario_tags, v.scenario_tags) AS scenario_tags,
        COALESCE(t.keywords, f.keywords, v.keywords) AS keywords,
        COALESCE(t.plain_summary, f.plain_summary, v.plain_summary) AS plain_summary,
        COALESCE(t.related_reason, f.related_reason, v.related_reason) AS related_reason,
        COALESCE(t.display_priority, f.display_priority, v.display_priority, 100) AS display_priority,
        COALESCE(t.source_url, f.source_url, v.source_url, t.source_uri, f.source_uri, v.source_uri) AS source_url,
        COALESCE(t.law_name, f.law_name, v.law_name) AS law_name,
        COALESCE(t.article_title, f.article_title, v.article_title) AS article_title,
        COALESCE(t.tag_score, 0) AS tag_score,
        COALESCE(f.fts_score, 0) AS fts_score,
        COALESCE(v.vec_score, 0) AS vec_score
      FROM tag_candidates t
      FULL OUTER JOIN fts f ON f.id = t.id
      FULL OUTER JOIN vec v ON v.id = COALESCE(t.id, f.id)
    )
    SELECT id, document_id, title, doc_type, document_metadata, source_name, source_uri,
           LEFT(chunk_text, 420) AS snippet, chunk_summary, article_no, clause_no, scenario_tags, keywords,
           plain_summary, related_reason, display_priority, source_url, law_name, article_title,
           (tag_score + fts_score * 0.48 + vec_score * 0.42 + GREATEST(0, (100 - display_priority)) * 0.001) AS score
    FROM merged
    ORDER BY score DESC, display_priority ASC
    LIMIT %(limit)s;
    """
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"q": normalized, "vec": vec, "tags": scenario_tags, "limit": limit})
            rows = cur.fetchall()
    items = []
    for row in rows:
        score = float(row[19] or 0.0)
        tags = list(row[11] or [])
        keywords = list(row[12] or [])
        items.append(
            {
                "chunk_id": str(row[0]),
                "document_id": str(row[1]),
                "title": row[2],
                "doc_type": row[3],
                "document_metadata": row[4] or {},
                "source": row[5],
                "source_uri": row[6],
                "snippet": row[7],
                "chunk_summary": row[8],
                "article_no": row[9],
                "clause_no": row[10],
                "scenario_tags": tags,
                "keywords": keywords,
                "plain_summary": row[13],
                "related_reason": row[14],
                "display_priority": int(row[15] or 100),
                "source_url": row[16] or row[6],
                "law_name": row[17],
                "article_title": row[18],
                "score": score,
                "confidence_label": evidence_confidence_label(score),
                "used_for": _infer_used_for(scenario_type, tags, keywords),
            }
        )
    return items


def _infer_used_for(scenario_type: str, tags: list[str], keywords: list[str]) -> str:
    joined = " ".join([scenario_type, *tags, *keywords])
    if "school_zone" in joined or "child" in joined:
        return "어린이보호구역 사고의 주의의무 판단 근거"
    if "signal" in joined:
        return "교차로 신호위반 여부 판단 근거"
    if "rear_end" in joined or "safe_distance" in joined:
        return "후미추돌 안전거리 판단 근거"
    if "lane_change" in joined:
        return "차선변경 주의의무 판단 근거"
    if "reporting" in joined or "hit_and_run" in joined:
        return "사고 후 조치와 신고 필요 여부 판단 근거"
    if "insurance" in joined:
        return "보험 처리와 필요 서류 안내 근거"
    return "교통사고 분석에 참고할 수 있는 근거"
