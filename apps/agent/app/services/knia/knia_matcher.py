from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any

import psycopg
import redis

from app.providers.embedding import get_embedding_provider, vector_literal
from app.services.knia.knia_media_selector import select_media
from app.services.knia.taxonomy import infer_party_type_from_text, party_actions, party_label
from app.services.scenario_search_terms import scenario_search_terms

DB_URL = os.getenv("DATABASE_URL", "postgresql://law:lawpass@postgres:5432/lawcompass")
REDIS_URL = os.getenv("REDIS_URL", "")

SCENARIO_TO_TAGS = {
    "rear_end_collision": ["rear_end", "safe_distance", "fault_ratio"],
    "lane_change_collision": ["lane_change", "fault_ratio"],
    "intersection_signal_violation": ["intersection", "signal_violation", "fault_ratio"],
    "pedestrian_crosswalk_accident": ["pedestrian", "fault_ratio"],
    "school_zone_child_accident": ["pedestrian", "school_zone", "fault_ratio"],
    "bicycle_collision": ["bicycle", "fault_ratio"],
    "object_collision": ["object", "single_vehicle"],
    "single_vehicle_accident": ["single_vehicle"],
    "parking_or_stopped_vehicle_accident": ["parking", "rear_end"],
}


def normalize_query(text: str) -> str:
    return " ".join(re.sub(r"[^0-9A-Za-z가-힣\-\s]", " ", text or "").split()).lower()


def _redis_client():
    if not REDIS_URL:
        return None
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)


def match_knia_charts(
    *,
    description_text: str,
    structured_facts: dict[str, Any] | None = None,
    selected_keywords: list[str] | None = None,
    scenario_type: str | None = None,
    accident_party_type: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    facts = structured_facts or {}
    keywords = selected_keywords or []
    party = accident_party_type or facts.get("accident_party_type") or infer_party_type_from_text(description_text, {**facts, "accident_type": scenario_type or facts.get("accident_type")})
    expansion_terms = scenario_search_terms(
        scenario_type=scenario_type,
        scenario_tags=SCENARIO_TO_TAGS.get(scenario_type or "", []),
        facts=facts,
        selected_keywords=keywords,
        accident_party_type=party,
    )
    q = normalize_query(" ".join([description_text or "", json.dumps(facts, ensure_ascii=False), " ".join(keywords), scenario_type or "", party or "", " ".join(expansion_terms)]))
    chart_direct = re.search(r"[차보자기단]\d{1,3}(?:-\d+)?", q)
    tags = list(dict.fromkeys([*(SCENARIO_TO_TAGS.get(scenario_type or "", [])), *_tags_from_text(q, party)]))
    cache_key = "knia:match:v5:" + hashlib.sha256(json.dumps({"q": q, "tags": tags, "party": party, "limit": limit}, ensure_ascii=False).encode("utf-8")).hexdigest()[:24]
    cache = _redis_client()
    if cache:
        cached = cache.get(cache_key)
        if cached:
            return {"items": json.loads(cached), "cache_hit": True, "cache_key": cache_key, "accident_party_type": party, "query_expansion_terms": expansion_terms}
    lookup_error = None
    try:
        if chart_direct:
            items = _direct_lookup(chart_direct.group(0), limit)
        else:
            items = _hybrid_lookup(q, tags, party, limit, scenario_type=scenario_type)
            if not items and party != "unknown":
                items = _hybrid_lookup(q, tags, None, limit, scenario_type=scenario_type)
    except Exception as exc:
        items = []
        lookup_error = _safe_error(exc)
    if cache:
        cache.setex(cache_key, 900, json.dumps(items, ensure_ascii=False))
    return {
        "items": items,
        "cache_hit": False,
        "cache_key": cache_key,
        "accident_party_type": party,
        "query_expansion_terms": expansion_terms,
        "lookup_error": lookup_error,
    }


def _tags_from_text(text: str, party: str | None = None) -> list[str]:
    tags: list[str] = []
    checks = [
        ("rear_end", ["후미", "뒤차", "추돌", "정차", "안전거리"]),
        ("lane_change", ["차선", "진로", "끼어", "방향지시등"]),
        ("intersection", ["교차로", "좌회전", "우회전"]),
        ("signal_violation", ["신호", "빨간불", "적색"]),
        ("pedestrian", ["보행자", "횡단보도", "아이", "사람"]),
        ("bicycle", ["자전거"]),
        ("object", ["기물", "시설물", "가드레일", "전봇대", "중앙분리대", "기둥", "벽"]),
        ("single_vehicle", ["혼자", "단독", "미끄러", "전복", "빗길", "눈길"]),
        ("parking", ["주차", "정차"]),
    ]
    for tag, words in checks:
        if any(w in text for w in words):
            tags.append(tag)
    party_tag = {"car_vs_person": "pedestrian", "car_vs_bicycle": "bicycle", "car_vs_object": "object", "single_vehicle": "single_vehicle", "car_vs_car": "vehicle"}.get(party or "")
    if party_tag:
        tags.append(party_tag)
    return list(dict.fromkeys(tags or ["general_collision"]))


def _direct_lookup(chart_no: str, limit: int) -> list[dict[str, Any]]:
    with psycopg.connect(DB_URL) as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute("SELECT * FROM knia_fault_charts WHERE chart_no=%s ORDER BY updated_at DESC LIMIT %s", (chart_no, limit))
        rows = [dict(r) for r in cur.fetchall()]
    return [_to_match(row, 0.95, "입력 내용에 기준번호가 직접 포함되어 있습니다.") for row in rows]


def _hybrid_lookup(
    query: str,
    tags: list[str],
    party: str | None,
    limit: int,
    *,
    scenario_type: str | None = None,
) -> list[dict[str, Any]]:
    provider = get_embedding_provider()
    vec = vector_literal(provider.embed(query))
    party_filter = party if party and party != "unknown" else None
    sql = """
    WITH fts AS (
      SELECT c.id AS chart_id, ch.id AS chunk_id, ts_rank_cd(ch.tsv, plainto_tsquery('simple', %(q)s)) AS fts_score
      FROM knia_fault_chart_chunks ch
      JOIN knia_fault_charts c ON c.id = ch.chart_id
      WHERE ch.tsv @@ plainto_tsquery('simple', %(q)s)
        AND (%(party)s::text IS NULL OR ch.accident_party_type=%(party)s OR c.accident_party_type=%(party)s)
      LIMIT 100
    ), vec AS (
      SELECT c.id AS chart_id, ch.id AS chunk_id, CASE WHEN ch.embedding IS NULL THEN 0 ELSE 1 - (ch.embedding <=> %(vec)s::vector) END AS vec_score
      FROM knia_fault_chart_chunks ch
      JOIN knia_fault_charts c ON c.id = ch.chart_id
      WHERE ch.embedding IS NOT NULL
        AND (%(party)s::text IS NULL OR ch.accident_party_type=%(party)s OR c.accident_party_type=%(party)s)
      ORDER BY ch.embedding <=> %(vec)s::vector
      LIMIT 100
    ), tag AS (
      SELECT c.id AS chart_id, ch.id AS chunk_id, CASE WHEN ch.scenario_tags && %(tags)s::text[] OR ch.display_tags && %(tags)s::text[] THEN 0.30 ELSE 0 END AS tag_score
      FROM knia_fault_chart_chunks ch
      JOIN knia_fault_charts c ON c.id = ch.chart_id
      WHERE (%(tags)s::text[] = '{}'::text[] OR ch.scenario_tags && %(tags)s::text[] OR ch.display_tags && %(tags)s::text[])
        AND (%(party)s::text IS NULL OR ch.accident_party_type=%(party)s OR c.accident_party_type=%(party)s)
      LIMIT 100
    ), party_rank AS (
      SELECT c.id AS chart_id, 0.22 AS party_score
      FROM knia_fault_charts c
      WHERE %(party)s::text IS NOT NULL AND c.accident_party_type=%(party)s
      LIMIT 100
    ), merged AS (
      SELECT COALESCE(f.chart_id, v.chart_id, t.chart_id, p.chart_id) AS chart_id,
             max(COALESCE(f.fts_score,0)) AS fts_score,
             max(COALESCE(v.vec_score,0)) AS vec_score,
             max(COALESCE(t.tag_score,0)) AS tag_score,
             max(COALESCE(p.party_score,0)) AS party_score
      FROM fts f
      FULL OUTER JOIN vec v ON v.chart_id=f.chart_id
      FULL OUTER JOIN tag t ON t.chart_id=COALESCE(f.chart_id, v.chart_id)
      FULL OUTER JOIN party_rank p ON p.chart_id=COALESCE(f.chart_id, v.chart_id, t.chart_id)
      GROUP BY COALESCE(f.chart_id, v.chart_id, t.chart_id, p.chart_id)
    ), ranked AS (
      SELECT c.*, (m.party_score + m.tag_score + m.fts_score * 0.44 + m.vec_score * 0.36 + COALESCE((SELECT max(100-r.rank_no) FROM knia_fault_rankings r WHERE r.chart_no=c.chart_no), 0) * 0.001) AS match_score
      FROM merged m
      JOIN knia_fault_charts c ON c.id=m.chart_id
    )
    SELECT * FROM ranked ORDER BY match_score DESC LIMIT %(limit)s
    """
    with psycopg.connect(DB_URL) as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(sql, {"q": query, "vec": vec, "tags": tags, "party": party_filter, "limit": limit})
        rows = [dict(r) for r in cur.fetchall()]
    matches = []
    for row in rows:
        score = float(row.get("match_score") or 0.0)
        joined = " ".join([str(row.get("chart_no") or ""), str(row.get("title") or ""), str(row.get("accident_summary") or ""), str(row.get("basic_fault_text") or "")])
        if _is_strict_scenario_mismatch(scenario_type, row, joined):
            continue
        if "rear_end" in tags:
            if row.get("chart_no") == "차41-1" or any(w in joined for w in ["후방 추돌", "뒤차", "안전거리"]):
                score += 0.18
            if any(w in joined for w in ["진로 변경", "진로변경", "차로를 변경"]):
                score -= 0.12
        if "bicycle" in tags and row.get("accident_party_type") == "car_vs_bicycle":
            score += 0.18
        if "pedestrian" in tags and row.get("accident_party_type") == "car_vs_person":
            score += 0.18
        if "object" in tags and row.get("accident_party_type") == "car_vs_object":
            score += 0.18
        if "single_vehicle" in tags and row.get("accident_party_type") == "single_vehicle":
            score += 0.18
        if "lane_change" in tags and any(w in joined for w in ["진로 변경", "진로변경", "차로를 변경"]):
            score += 0.16
        score += _scenario_chart_score_adjustment(row, tags, joined)
        matches.append(_to_match(row, score, _reason(row, tags, party)))
    return sorted(matches, key=lambda x: x.get("match_score") or 0, reverse=True)[:limit]


def _is_strict_scenario_mismatch(scenario_type: str | None, row: dict[str, Any], joined_text: str) -> bool:
    chart_no = str(row.get("chart_no") or "")
    party = _row_party_type(row)
    expected_parties = {
        "pedestrian_crosswalk_accident": {"car_vs_person"},
        "school_zone_child_accident": {"car_vs_person"},
        "bicycle_collision": {"car_vs_bicycle"},
        "object_collision": {"car_vs_object"},
        "single_vehicle_accident": {"single_vehicle"},
    }.get(scenario_type or "")
    if expected_parties and party not in expected_parties:
        return True

    has_signal_terms = any(w in joined_text for w in ["신호위반", "적색", "빨간불", "교차로 신호"])
    if scenario_type == "intersection_signal_violation":
        return not (chart_no.startswith("차12") or has_signal_terms)
    return False


def _scenario_chart_score_adjustment(row: dict[str, Any], tags: list[str], joined_text: str) -> float:
    chart_no = str(row.get("chart_no") or "")
    adjustment = 0.0
    has_lane_terms = any(w in joined_text for w in ["진로 변경", "진로변경", "차로를 변경", "차선변경"])
    has_signal_terms = any(w in joined_text for w in ["신호위반", "적색", "빨간불", "교차로 신호"])

    if "signal_violation" in tags:
        if chart_no.startswith("차12") or has_signal_terms:
            adjustment += 0.32
        if has_lane_terms and not has_signal_terms:
            adjustment -= 0.22

    if "lane_change" in tags:
        if chart_no.startswith("차43") or has_lane_terms:
            adjustment += 0.18
        if has_signal_terms and not has_lane_terms:
            adjustment -= 0.12

    return adjustment


def _reason(row: dict[str, Any], tags: list[str], party: str | None = None) -> str:
    if "rear_end" in tags:
        return "정차 또는 감속 중 뒤차가 추돌한 상황과 유사합니다."
    if "lane_change" in tags:
        return "차선변경이나 방향지시등 관련 사고 내용이 기준과 가깝습니다."
    if "signal_violation" in tags:
        return "교차로 신호위반 여부가 기준과 가깝습니다."
    if party == "car_vs_person" or "pedestrian" in tags:
        return "보행자와 접촉한 사고라는 점이 유사합니다."
    if party == "car_vs_bicycle" or "bicycle" in tags:
        return "자전거와 충돌한 사고라는 점이 유사합니다."
    if party == "car_vs_object" or "object" in tags:
        return "시설물이나 기물과 충돌한 사고라는 점이 유사합니다."
    if party == "single_vehicle" or "single_vehicle" in tags:
        return "다른 차량 없이 혼자 발생한 사고라는 점이 유사합니다."
    return "입력하신 사고 내용과 비슷한 과실비율 기준입니다."


def _to_match(row: dict[str, Any], score: float, reason: str) -> dict[str, Any]:
    media = select_media(row)
    party = _row_party_type(row)
    return {
        "chart_id": str(row.get("id")),
        "chart_no": row.get("chart_no"),
        "chart_type": row.get("chart_type") or "1",
        "title": row.get("title"),
        "match_score": round(score, 4),
        "match_label": "관련성이 높은 기준입니다." if score >= 0.35 else "참고할 수 있는 기준입니다.",
        "match_reason": reason,
        "accident_party_type": party,
        "accident_party_label": party_label(party),
        "base_fault_a": row.get("base_fault_a"),
        "base_fault_b": row.get("base_fault_b"),
        "accident_summary": row.get("accident_summary"),
        "scenario_summary_easy": row.get("scenario_summary_easy"),
        "basic_fault_text": row.get("basic_fault_text"),
        "recommended_user_actions": row.get("recommended_user_actions") or party_actions(party),
        "display_tags": row.get("display_tags") or [],
        "source_url": row.get("source_url"),
        "thumbnail_url": row.get("thumbnail_url"),
        "video_url": row.get("video_url"),
        "media": media,
        "attribution": row.get("attribution") or "자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털",
    }


def _row_party_type(row: dict[str, Any]) -> str:
    return _party_from_chart_no(row.get("chart_no")) or row.get("accident_party_type") or "unknown"


def _safe_error(exc: Exception) -> dict[str, str]:
    return {"type": exc.__class__.__name__, "message": "KNIA chart lookup failed"}


def _party_from_chart_no(chart_no: Any) -> str | None:
    text = str(chart_no or "")
    if text.startswith("차"):
        return "car_vs_car"
    if text.startswith("보"):
        return "car_vs_person"
    if text.startswith("자"):
        return "car_vs_bicycle"
    if text.startswith("기"):
        return "car_vs_object"
    if text.startswith("단"):
        return "single_vehicle"
    return None
