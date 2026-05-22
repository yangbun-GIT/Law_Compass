from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any

import psycopg
import redis

from app.providers.embedding import get_embedding_provider, vector_literal


def _db_url() -> str | None:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        return None
    return url


def normalize_query(query: str) -> str:
    return " ".join((query or "").strip().lower().split())


def query_hash(query: str) -> str:
    return hashlib.sha256(normalize_query(query).encode("utf-8")).hexdigest()


def _redis() -> redis.Redis | None:
    try:
        return redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379"), decode_responses=True)
    except Exception:
        return None


def get_knia_json_version() -> str:
    db_url = _db_url()
    if not db_url:
        return "dev"
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute("SELECT source_file_hash FROM knia_json_import_runs WHERE status='success' ORDER BY finished_at DESC NULLS LAST, started_at DESC LIMIT 1")
        row = cur.fetchone()
        return row[0][:16] if row and row[0] else "dev"


def invalidate_scope(scope: str = "knia_json") -> dict[str, Any]:
    deleted_redis = 0
    db_url = _db_url()
    if not db_url:
        return {"scope": scope, "redis_deleted": deleted_redis, "semantic_cache_deleted": 0, "disabled_reason": "DATABASE_URL missing"}
    r = _redis()
    if r and scope == "knia_json":
        try:
            for key in r.scan_iter("knia_json:exact:v1:*"):
                deleted_redis += r.delete(key)
        except Exception:
            deleted_redis = 0
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM semantic_query_cache WHERE source_scope=%s", (scope,))
        deleted_pg = cur.rowcount
        conn.commit()
    return {"scope": scope, "redis_deleted": deleted_redis, "semantic_cache_deleted": deleted_pg}


def _public_items_from_refs(refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not refs:
        return []
    db_url = _db_url()
    if not db_url:
        return []
    ids = [x.get("chunk_id") for x in refs if x.get("chunk_id")]
    if not ids:
        return []
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT kc.id, kd.title, kc.plain_summary, kc.source_url, kc.accident_party_type, kc.accident_party_label,
                   kc.display_tags, kc.keywords, kd.source
            FROM knia_reference_chunks kc JOIN knia_reference_documents kd ON kd.id=kc.document_id
            WHERE kc.id::text = ANY(%s)
            """,
            (ids,),
        )
        by_id = {str(r[0]): r for r in cur.fetchall()}
    out = []
    for ref in refs:
        r = by_id.get(ref.get("chunk_id"))
        if not r:
            continue
        out.append({
            "title": r[1],
            "summary": r[2],
            "source_url": r[3],
            "accident_party_type": r[4],
            "accident_party_label": r[5],
            "display_tags": r[6] or [],
            "keywords": r[7] or [],
            "source": r[8] or "KNIA 자동차사고 과실비율 정보포털",
            "attribution": "자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털",
        })
    return out


def search_knia_json_cached(query: str, accident_party_type: str | None = None, scenario_type: str | None = None, limit: int = 5) -> dict[str, Any]:
    normalized = normalize_query(query)
    qh = query_hash(normalized)
    version = get_knia_json_version()
    party = accident_party_type or "unknown"
    key = f"knia_json:exact:v1:{version}:{party}:{qh}"
    db_url = _db_url()
    if not db_url:
        return {"items": [], "cache": {"exact_hit": False, "semantic_hit": False, "key": key, "disabled_reason": "DATABASE_URL missing"}}
    r = _redis()
    if r:
        try:
            cached = r.get(key)
            if cached:
                refs = json.loads(cached)
                return {"items": _public_items_from_refs(refs), "cache": {"exact_hit": True, "semantic_hit": False, "key": key}}
        except Exception:
            r = None

    provider = get_embedding_provider()
    vec_literal = vector_literal(provider.embed(normalized[:4000]))
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT result_refs
            FROM semantic_query_cache
            WHERE source_scope='knia_json'
              AND coalesce(accident_party_type,'unknown')=%s
              AND (expires_at IS NULL OR expires_at > now())
            ORDER BY query_embedding <=> %s::vector ASC
            LIMIT 1
            """,
            (party, vec_literal),
        )
        semantic = cur.fetchone()
        if semantic:
            refs = semantic[0]
            cur.execute("UPDATE semantic_query_cache SET hit_count=hit_count+1, updated_at=now() WHERE query_hash=%s AND source_scope='knia_json'", (qh,))
            conn.commit()
            if r:
                try:
                    r.setex(key, 3600, json.dumps(refs, ensure_ascii=False))
                except Exception:
                    pass
            return {"items": _public_items_from_refs(refs), "cache": {"exact_hit": False, "semantic_hit": True, "key": key}}

        params: list[Any] = [normalized, vec_literal]
        where = "kc.source_url IS NOT NULL"
        if accident_party_type and accident_party_type != "unknown":
            params.append(accident_party_type)
            where += f" AND kc.accident_party_type=%s"
        params.append(limit)
        cur.execute(
            f"""
            WITH q AS (SELECT plainto_tsquery('simple', %s) AS tsq, %s::vector AS qvec)
            SELECT kc.id, kd.title, kc.plain_summary, kc.source_url, kc.accident_party_type, kc.accident_party_label,
                   kc.display_tags, kc.keywords, kd.source,
                   (CASE WHEN kc.tsv @@ q.tsq THEN ts_rank(kc.tsv, q.tsq) ELSE 0 END) AS fts_rank,
                   (CASE WHEN kc.embedding IS NOT NULL THEN 1 - (kc.embedding <=> q.qvec) ELSE 0 END) AS vector_score,
                   kc.evidence_quality_score
            FROM knia_reference_chunks kc
            JOIN knia_reference_documents kd ON kd.id=kc.document_id
            CROSS JOIN q
            WHERE {where}
            ORDER BY ((CASE WHEN kc.tsv @@ q.tsq THEN ts_rank(kc.tsv, q.tsq) ELSE 0 END) * 0.55
                    + (CASE WHEN kc.embedding IS NOT NULL THEN 1 - (kc.embedding <=> q.qvec) ELSE 0 END) * 0.35
                    + kc.evidence_quality_score * 0.10) DESC
            LIMIT %s
            """,
            params,
        )
        rows = cur.fetchall()
        if not rows and accident_party_type:
            return search_knia_json_cached(query, accident_party_type=None, scenario_type=scenario_type, limit=limit)
        refs = [{"chunk_id": str(row[0])} for row in rows]
        items = [
            {
                "title": row[1], "summary": row[2], "source_url": row[3], "accident_party_type": row[4],
                "accident_party_label": row[5], "display_tags": row[6] or [], "keywords": row[7] or [],
                "source": row[8] or "KNIA 자동차사고 과실비율 정보포털",
                "attribution": "자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털",
            }
            for row in rows
        ]
        cur.execute(
            """
            INSERT INTO semantic_query_cache(source_scope, accident_party_type, scenario_type, normalized_query, query_hash, query_embedding, result_refs, kb_version, expires_at)
            VALUES ('knia_json', %s, %s, %s, %s, %s::vector, %s::jsonb, %s, now() + interval '7 days')
            """,
            (party, scenario_type, normalized, qh, vec_literal, json.dumps(refs, ensure_ascii=False), version),
        )
        conn.commit()
        if r:
            try:
                r.setex(key, 3600, json.dumps(refs, ensure_ascii=False))
            except Exception:
                pass
        return {"items": items, "cache": {"exact_hit": False, "semantic_hit": False, "key": key}}

