from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any

import psycopg
import redis

from app.providers.embedding import get_embedding_provider, vector_literal


KNIA_JSON_EXACT_CACHE_VERSION = "v4"
KNIA_JSON_SEMANTIC_DISTANCE_THRESHOLD = 0.20
logger = logging.getLogger(__name__)

CHART_NO_SQL = "COALESCE(kd.metadata->>'chart_no', kd.metadata->>'subchart_no')"
MAJOR_PARTY_SQL = "COALESCE(kd.metadata->>'major_party_type', kc.accident_party_type)"
SCENARIO_TYPE_SQL = "COALESCE(kd.metadata->>'scenario_type', kd.metadata->>'scenario_subtype')"
REVIEW_REQUIRED_SQL = (
    "CASE WHEN lower(COALESCE(kd.metadata->>'review_required', 'false')) "
    "IN ('true', '1', 'yes') THEN true ELSE false END"
)


def _chart_prefix_patterns(party_type: str | None) -> list[str]:
    return {
        "car_vs_car": ["차%", "李%"],
        "car_vs_person": ["보%", "蹂%"],
        "car_vs_bicycle": ["거%", "자%", "嫄%"],
        "car_vs_object": ["기%", "湲%"],
        "single_vehicle": ["단%"],
    }.get(str(party_type or ""), [])


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
            for key in r.scan_iter("knia_json:exact:*"):
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
                   kc.display_tags, kc.keywords, kd.source,
                   {CHART_NO_SQL} AS chart_no,
                   {MAJOR_PARTY_SQL} AS major_party_type,
                   {SCENARIO_TYPE_SQL} AS scenario_type,
                   kc.chunk_type,
                   {REVIEW_REQUIRED_SQL} AS review_required,
                   kd.metadata AS metadata
            FROM knia_reference_chunks kc JOIN knia_reference_documents kd ON kd.id=kc.document_id
            WHERE kc.id::text = ANY(%s)
            """.format(
                CHART_NO_SQL=CHART_NO_SQL,
                MAJOR_PARTY_SQL=MAJOR_PARTY_SQL,
                SCENARIO_TYPE_SQL=SCENARIO_TYPE_SQL,
                REVIEW_REQUIRED_SQL=REVIEW_REQUIRED_SQL,
            ),
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
            "chart_no": r[9],
            "major_party_type": r[10],
            "scenario_type": r[11],
            "chunk_type": r[12],
            "review_required": bool(r[13]),
            "metadata": r[14] or {},
            "attribution": "자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털",
        })
    return out


def _rows_to_public_items(rows: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "title": row[1],
            "summary": row[2],
            "source_url": row[3],
            "accident_party_type": row[4],
            "accident_party_label": row[5],
            "display_tags": row[6] or [],
            "keywords": row[7] or [],
            "source": row[8] or "KNIA 자동차사고 과실비율 정보포털",
            "chart_no": row[9] if len(row) > 9 else None,
            "major_party_type": row[10] if len(row) > 10 else None,
            "scenario_type": row[11] if len(row) > 11 else None,
            "chunk_type": row[12] if len(row) > 12 else None,
            "review_required": bool(row[13]) if len(row) > 13 else False,
            "metadata": row[14] if len(row) > 14 else {},
            "attribution": "자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털",
        }
        for row in rows
    ]


def _keyword_fallback_search(
    *,
    query: str,
    accident_party_type: str | None,
    scenario_type: str | None,
    chart_no: str | None,
    limit: int,
    cache_key: str,
    lookup_error: str,
) -> dict[str, Any]:
    db_url = _db_url()
    scenario = scenario_type or "unknown"
    if not db_url:
        return {
            "items": [],
            "cache": {
                "exact_hit": False,
                "semantic_hit": False,
                "key": cache_key,
                "scenario_type": scenario,
                "disabled_reason": "embedding_unavailable",
                "lookup_error": lookup_error,
            },
        }
    try:
        with psycopg.connect(db_url) as conn, conn.cursor() as cur:
            params: list[Any] = [query]
            where = "kc.source_url IS NOT NULL"
            if chart_no:
                params.append(chart_no)
                where += f" AND {CHART_NO_SQL}=%s"
            if accident_party_type and accident_party_type != "unknown":
                params.append(accident_party_type)
                prefixes = _chart_prefix_patterns(accident_party_type)
                where += f" AND ({MAJOR_PARTY_SQL}=%s OR kc.accident_party_type=%s"
                params.append(accident_party_type)
                if prefixes:
                    params.append(prefixes)
                    where += f" OR {CHART_NO_SQL} LIKE ANY(%s::text[])"
                where += ")"
            params.append(limit)
            cur.execute(
                f"""
                WITH q AS (SELECT plainto_tsquery('simple', %s) AS tsq)
                SELECT kc.id, kd.title, kc.plain_summary, kc.source_url, kc.accident_party_type, kc.accident_party_label,
                       kc.display_tags, kc.keywords, kd.source,
                       {CHART_NO_SQL} AS chart_no,
                       {MAJOR_PARTY_SQL} AS major_party_type,
                       {SCENARIO_TYPE_SQL} AS scenario_type,
                       kc.chunk_type,
                       {REVIEW_REQUIRED_SQL} AS review_required,
                       kd.metadata AS metadata,
                       (CASE WHEN kc.tsv @@ q.tsq THEN ts_rank(kc.tsv, q.tsq) ELSE 0 END) AS fts_rank,
                       kc.evidence_quality_score
                FROM knia_reference_chunks kc
                JOIN knia_reference_documents kd ON kd.id=kc.document_id
                CROSS JOIN q
                WHERE {where}
                ORDER BY ((CASE WHEN kc.tsv @@ q.tsq THEN ts_rank(kc.tsv, q.tsq) ELSE 0 END) * 0.80
                        + kc.evidence_quality_score * 0.20) DESC
                LIMIT %s
                """.format(
                    where=where,
                    CHART_NO_SQL=CHART_NO_SQL,
                    MAJOR_PARTY_SQL=MAJOR_PARTY_SQL,
                    SCENARIO_TYPE_SQL=SCENARIO_TYPE_SQL,
                    REVIEW_REQUIRED_SQL=REVIEW_REQUIRED_SQL,
                ),
                params,
            )
            rows = cur.fetchall()
            return {
                "items": _rows_to_public_items(rows),
                "cache": {
                    "exact_hit": False,
                    "semantic_hit": False,
                    "key": cache_key,
                    "scenario_type": scenario,
                    "disabled_reason": "embedding_unavailable",
                    "lookup_error": lookup_error,
                },
            }
    except Exception as exc:
        logger.warning("KNIA keyword fallback search failed", extra={"error_type": exc.__class__.__name__})
        return {
            "items": [],
            "cache": {
                "exact_hit": False,
                "semantic_hit": False,
                "key": cache_key,
                "scenario_type": scenario,
                "disabled_reason": "embedding_unavailable",
                "lookup_error": lookup_error,
            },
        }


def search_knia_json_cached(query: str, accident_party_type: str | None = None, scenario_type: str | None = None, limit: int = 5, chart_no: str | None = None) -> dict[str, Any]:
    normalized = normalize_query(query)
    qh = query_hash(normalized)
    version = get_knia_json_version()
    party = accident_party_type or "unknown"
    scenario = scenario_type or "unknown"
    chart_scope = chart_no or "any"
    key = f"knia_json:exact:{KNIA_JSON_EXACT_CACHE_VERSION}:{version}:{party}:{scenario}:{chart_scope}:{qh}"
    db_url = _db_url()
    if not db_url:
        return {"items": [], "cache": {"exact_hit": False, "semantic_hit": False, "key": key, "scenario_type": scenario, "disabled_reason": "DATABASE_URL missing"}}
    r = _redis()
    if r:
        try:
            cached = r.get(key)
            if cached:
                refs = json.loads(cached)
                return {"items": _public_items_from_refs(refs), "cache": {"exact_hit": True, "semantic_hit": False, "key": key, "scenario_type": scenario}}
        except Exception:
            r = None

    try:
        provider = get_embedding_provider()
        vec_literal = vector_literal(provider.embed(normalized[:4000]))
    except Exception as exc:
        logger.warning("KNIA semantic lookup disabled because embedding is unavailable", extra={"error_type": exc.__class__.__name__})
        return _keyword_fallback_search(
            query=normalized,
            accident_party_type=accident_party_type,
            scenario_type=scenario_type,
            chart_no=chart_no,
            limit=limit,
            cache_key=key,
            lookup_error=f"embedding_unavailable:{exc.__class__.__name__}",
        )
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        semantic = None
        if not chart_no:
            cur.execute(
                """
                SELECT result_refs, query_hash, query_embedding <=> %s::vector AS distance
                FROM semantic_query_cache
                WHERE source_scope='knia_json'
                  AND coalesce(accident_party_type,'unknown')=%s
                  AND coalesce(scenario_type,'unknown')=%s
                  AND (expires_at IS NULL OR expires_at > now())
                ORDER BY query_embedding <=> %s::vector ASC
                LIMIT 1
                """,
                (vec_literal, party, scenario, vec_literal),
            )
            semantic = cur.fetchone()
        if semantic and float(semantic[2] or 1.0) <= KNIA_JSON_SEMANTIC_DISTANCE_THRESHOLD:
            refs = semantic[0]
            cur.execute("UPDATE semantic_query_cache SET hit_count=hit_count+1, updated_at=now() WHERE query_hash=%s AND source_scope='knia_json'", (semantic[1],))
            conn.commit()
            if r:
                try:
                    r.setex(key, 3600, json.dumps(refs, ensure_ascii=False))
                except Exception:
                    pass
            return {
                "items": _public_items_from_refs(refs),
                "cache": {
                    "exact_hit": False,
                    "semantic_hit": True,
                    "key": key,
                    "scenario_type": scenario,
                    "semantic_distance": float(semantic[2] or 0.0),
                    "semantic_distance_threshold": KNIA_JSON_SEMANTIC_DISTANCE_THRESHOLD,
                },
            }

        params: list[Any] = [normalized, vec_literal]
        where = "kc.source_url IS NOT NULL"
        if chart_no:
            params.append(chart_no)
            where += f" AND {CHART_NO_SQL}=%s"
        if accident_party_type and accident_party_type != "unknown":
            params.append(accident_party_type)
            prefixes = _chart_prefix_patterns(accident_party_type)
            where += f" AND ({MAJOR_PARTY_SQL}=%s OR kc.accident_party_type=%s"
            params.append(accident_party_type)
            if prefixes:
                params.append(prefixes)
                where += f" OR {CHART_NO_SQL} LIKE ANY(%s::text[])"
            where += ")"
        params.append(limit)
        cur.execute(
            f"""
            WITH q AS (SELECT plainto_tsquery('simple', %s) AS tsq, %s::vector AS qvec)
            SELECT kc.id, kd.title, kc.plain_summary, kc.source_url, kc.accident_party_type, kc.accident_party_label,
                   kc.display_tags, kc.keywords, kd.source,
                   {CHART_NO_SQL} AS chart_no,
                   {MAJOR_PARTY_SQL} AS major_party_type,
                   {SCENARIO_TYPE_SQL} AS scenario_type,
                   kc.chunk_type,
                   {REVIEW_REQUIRED_SQL} AS review_required,
                   kd.metadata AS metadata,
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
        refs = [{"chunk_id": str(row[0])} for row in rows]
        items = _rows_to_public_items(rows)
        if not chart_no:
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
        return {
            "items": items,
            "cache": {
                "exact_hit": False,
                "semantic_hit": False,
                "key": key,
                "scenario_type": scenario,
                "semantic_distance_threshold": KNIA_JSON_SEMANTIC_DISTANCE_THRESHOLD,
            },
        }

