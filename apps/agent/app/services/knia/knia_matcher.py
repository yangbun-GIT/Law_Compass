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
    "parking_or_stopped_vehicle_accident": ["parking", "stopped_vehicle"],
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
    cache_key = "knia:match:v7:" + hashlib.sha256(json.dumps({"q": q, "tags": tags, "party": party, "scenario_type": scenario_type, "limit": limit}, ensure_ascii=False).encode("utf-8")).hexdigest()[:24]
    cache = _redis_client()
    if cache:
        cached = cache.get(cache_key)
        if cached:
            return {"items": json.loads(cached), "cache_hit": True, "cache_key": cache_key, "accident_party_type": party, "query_expansion_terms": expansion_terms}
    lookup_error = None
    try:
        excluded_items: list[dict[str, Any]] = []
        if chart_direct:
            raw_items = _direct_lookup(chart_direct.group(0), limit)
            items, excluded_items = _filter_scenario_compatible_matches(raw_items, scenario_type)
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
        "excluded_items": excluded_items if "excluded_items" in locals() else [],
    }


def _tags_from_text(text: str, party: str | None = None) -> list[str]:
    tags: list[str] = []
    checks = [
        ("rear_end", ["후미", "뒤차", "추돌", "정차", "안전거리"]),
        ("front_vehicle_stop_reason", ["앞차", "선행 차량", "정지 사유", "정차 사유", "횡단보도 앞", "front vehicle", "stop reason"]),
        ("lane_change", ["차선", "진로", "끼어", "방향지시등"]),
        ("centerline", ["중앙선", "황색 실선", "중앙선을", "centerline"]),
        ("oncoming_vehicle", ["마주오", "대향", "반대편", "oncoming"]),
        ("road_obstruction", ["장애물", "불법 주정차", "주차 차량", "가구", "사물", "obstacle"]),
        ("intersection", ["교차로", "좌회전", "우회전"]),
        ("signal_violation", ["신호", "빨간불", "적색"]),
        ("pedestrian", ["보행자", "횡단보도", "아이", "사람"]),
        ("bicycle", ["자전거"]),
        ("non_contact_trigger", ["비접촉", "유발", "non contact", "non-contact", "trigger"]),
        ("time_gap", ["시간적 여유", "4초", "반응 시간", "reaction time", "time gap", "급제동", "급정거"]),
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
    party_prefixes = _party_chart_prefixes(party_filter)
    sql = """
    WITH fts AS (
      SELECT c.id AS chart_id, ch.id AS chunk_id, ts_rank_cd(ch.tsv, plainto_tsquery('simple', %(q)s)) AS fts_score
      FROM knia_fault_chart_chunks ch
      JOIN knia_fault_charts c ON c.id = ch.chart_id
      WHERE ch.tsv @@ plainto_tsquery('simple', %(q)s)
        AND (%(party)s::text IS NULL OR ch.accident_party_type=%(party)s OR c.accident_party_type=%(party)s OR c.chart_no LIKE ANY(%(party_prefixes)s::text[]))
      LIMIT 100
    ), vec AS (
      SELECT c.id AS chart_id, ch.id AS chunk_id, CASE WHEN ch.embedding IS NULL THEN 0 ELSE 1 - (ch.embedding <=> %(vec)s::vector) END AS vec_score
      FROM knia_fault_chart_chunks ch
      JOIN knia_fault_charts c ON c.id = ch.chart_id
      WHERE ch.embedding IS NOT NULL
        AND (%(party)s::text IS NULL OR ch.accident_party_type=%(party)s OR c.accident_party_type=%(party)s OR c.chart_no LIKE ANY(%(party_prefixes)s::text[]))
      ORDER BY ch.embedding <=> %(vec)s::vector
      LIMIT 100
    ), tag AS (
      SELECT c.id AS chart_id, ch.id AS chunk_id, CASE WHEN ch.scenario_tags && %(tags)s::text[] OR ch.display_tags && %(tags)s::text[] THEN 0.30 ELSE 0 END AS tag_score
      FROM knia_fault_chart_chunks ch
      JOIN knia_fault_charts c ON c.id = ch.chart_id
      WHERE (%(tags)s::text[] = '{}'::text[] OR ch.scenario_tags && %(tags)s::text[] OR ch.display_tags && %(tags)s::text[])
        AND (%(party)s::text IS NULL OR ch.accident_party_type=%(party)s OR c.accident_party_type=%(party)s OR c.chart_no LIKE ANY(%(party_prefixes)s::text[]))
      LIMIT 100
    ), party_rank AS (
      SELECT c.id AS chart_id, 0.22 AS party_score
      FROM knia_fault_charts c
      WHERE %(party)s::text IS NOT NULL AND (c.accident_party_type=%(party)s OR c.chart_no LIKE ANY(%(party_prefixes)s::text[]))
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
        cur.execute(sql, {"q": query, "vec": vec, "tags": tags, "party": party_filter, "party_prefixes": party_prefixes, "limit": limit})
        rows = [dict(r) for r in cur.fetchall()]
    matches = []
    for row in rows:
        score = float(row.get("match_score") or 0.0)
        joined = " ".join([str(row.get("chart_no") or ""), str(row.get("title") or ""), str(row.get("accident_summary") or ""), str(row.get("basic_fault_text") or "")])
        if _is_strict_scenario_mismatch(scenario_type, row, joined):
            continue
        if _is_centerline_primary_mismatch(tags, row):
            continue
        if "rear_end" in tags:
            if row.get("chart_no") == "차41-1" or any(w in joined for w in ["후방 추돌", "뒤차", "안전거리"]):
                score += 0.18
            if any(w in joined for w in ["진로 변경", "진로변경", "차로를 변경"]):
                score -= 0.12
        if "centerline" in tags or "oncoming_vehicle" in tags or "road_obstruction" in tags:
            if row.get("chart_no") and str(row.get("chart_no")).startswith("차43"):
                score += 0.34
            if any(w in joined for w in ["진로 변경", "진로변경", "차로를 변경", "중앙선", "대향"]):
                score += 0.22
            if row.get("chart_no") and str(row.get("chart_no")).startswith(("차41", "차42")):
                score -= 0.24
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
        "intersection_signal_violation": {"car_vs_car"},
        "lane_change_collision": {"car_vs_car"},
        "rear_end_collision": {"car_vs_car"},
    }.get(scenario_type or "")
    if expected_parties and party not in expected_parties:
        return True

    has_signal_terms = any(w in joined_text for w in ["신호위반", "적색", "빨간불", "교차로 신호", "녹색신호"])
    has_lane_terms = any(w in joined_text for w in ["진로 변경", "진로변경", "차로를 변경", "차선변경", "끼어들", "방향지시"])
    if scenario_type == "intersection_signal_violation":
        # Vehicle-vs-vehicle signal violation standards should stay in the 차12 family.
        # Do not let pedestrian/bicycle signal charts win only because they contain
        # generic "신호위반" terms.
        return not chart_no.startswith("차12")
    if scenario_type == "lane_change_collision":
        return not (chart_no.startswith("차43") or has_lane_terms)
    if scenario_type == "rear_end_collision":
        return _rear_end_primary_exclusion_reason(row, joined_text) is not None
    return False


def _filter_scenario_compatible_matches(
    items: list[dict[str, Any]],
    scenario_type: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    kept: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for item in items:
        joined = _match_joined_text(item)
        reason = None
        if scenario_type == "rear_end_collision":
            reason = _rear_end_primary_exclusion_reason(item, joined)
        elif _is_strict_scenario_mismatch(scenario_type, item, joined):
            reason = "scenario_party_or_structure_mismatch"
        if reason:
            excluded.append({**item, "exclusion_reason": reason})
        else:
            kept.append(item)
    return kept, excluded


def _rear_end_primary_exclusion_reason(row: dict[str, Any], joined_text: str | None = None) -> str | None:
    text = joined_text or _match_joined_text(row)
    chart_no = str(row.get("chart_no") or "")
    party = _row_party_type(row)
    if party in {"car_vs_person", "car_vs_bicycle", "car_vs_object", "single_vehicle"}:
        return f"incompatible_party_type:{party}"
    strong_rear_end = chart_no.startswith(("차41", "차42")) or any(
        token in text
        for token in (
            "후미추돌",
            "후방추돌",
            "후방 추돌",
            "뒤차",
            "뒷차",
            "안전거리",
            "정차 차량",
            "선행 차량",
            "앞차",
            "rear-end",
            "safe distance",
        )
    )
    structural_mismatch = any(
        token in text
        for token in (
            "좌회전",
            "직진 대 좌회전",
            "교차로 직진",
            "신호등 없는 교차로",
            "진로변경",
            "진로 변경",
            "차선변경",
            "차로를 변경",
            "자전거",
            "보행자",
            "기물",
            "시설물",
            "중앙선 침범",
            "중앙선",
            "left turn",
            "lane change",
            "bicycle",
            "pedestrian",
        )
    )
    if chart_no.startswith("차16") or (structural_mismatch and not strong_rear_end):
        return "rear_end_structure_mismatch"
    if not strong_rear_end:
        return "rear_end_signal_missing"
    return None


def is_knia_match_compatible_with_scenario(match: dict[str, Any] | None, scenario_type: str | None) -> bool:
    if not match:
        return False
    return _rear_end_primary_exclusion_reason(match) is None if scenario_type == "rear_end_collision" else not _is_strict_scenario_mismatch(scenario_type, match, _match_joined_text(match))


def _match_joined_text(row: dict[str, Any]) -> str:
    return " ".join(
        str(row.get(key) or "")
        for key in (
            "chart_no",
            "title",
            "accident_summary",
            "scenario_summary_easy",
            "basic_fault_text",
            "plain_summary",
            "summary",
            "related_reason",
            "source_url",
            "source_detail_url",
            "display_tags",
            "keywords",
        )
    ).lower()


def _is_centerline_primary_mismatch(tags: list[str], row: dict[str, Any]) -> bool:
    if not ("centerline" in tags or "oncoming_vehicle" in tags or "road_obstruction" in tags):
        return False
    chart_text = " ".join(
        str(row.get(key) or "")
        for key in ("chart_no", "title", "source_url", "source_detail_url")
    )
    party = _row_party_type(row)
    if party == "car_vs_person":
        return True
    if re.search(r"(?:^|\s|/)보\d", chart_text):
        return True
    if any(token in chart_text for token in ("무등화", "스텔스", "후미추돌", "후방추돌", "횡단보도", "앞차 정차", "보행자")):
        return True
    return "차41" in chart_text or "차42" in chart_text


def _scenario_chart_score_adjustment(row: dict[str, Any], tags: list[str], joined_text: str) -> float:
    chart_no = str(row.get("chart_no") or "")
    adjustment = 0.0
    has_lane_terms = any(w in joined_text for w in ["진로 변경", "진로변경", "차로를 변경", "차선변경", "끼어들", "방향지시"])
    has_signal_terms = any(w in joined_text for w in ["신호위반", "적색", "빨간불", "교차로 신호", "녹색신호"])

    if "rear_end" in tags:
        if chart_no.startswith(("차41", "차42")):
            adjustment += 0.55
        if chart_no.startswith(("차12", "차16", "차43")):
            adjustment -= 0.35

    if "signal_violation" in tags:
        if chart_no.startswith("차12"):
            adjustment += 0.70
        elif has_signal_terms:
            adjustment += 0.06
        if not chart_no.startswith("차12"):
            adjustment -= 0.22
        if has_lane_terms and not has_signal_terms:
            adjustment -= 0.22

    if "lane_change" in tags:
        if chart_no.startswith("차43"):
            adjustment += 0.70
        elif has_lane_terms:
            adjustment += 0.12
        if chart_no.startswith(("차12", "차16", "차41", "차42")):
            adjustment -= 0.35
        if has_signal_terms and not has_lane_terms:
            adjustment -= 0.12

    if "bicycle" in tags:
        if chart_no.startswith(("자", "거")):
            adjustment += 0.32
        if chart_no.startswith(("차", "보")):
            adjustment -= 0.12

    if "centerline" in tags or "oncoming_vehicle" in tags or "road_obstruction" in tags:
        if chart_no.startswith("차43") or has_lane_terms:
            adjustment += 0.24
        if chart_no.startswith(("차41", "차42")):
            adjustment -= 0.18

    return adjustment


def _reason(row: dict[str, Any], tags: list[str], party: str | None = None) -> str:
    if "centerline" in tags or "oncoming_vehicle" in tags or "road_obstruction" in tags:
        return "중앙선 침범 사유, 도로 장애물, 대향 차량과의 충돌 구조를 함께 볼 수 있는 기준입니다."
    if "rear_end" in tags and "non_contact_trigger" in tags:
        return "자전거 비접촉 유발, 트럭·앞차 정지 사유, 후방 버스 추돌, 급제동 또는 반응 시간, 안전거리 책임을 함께 볼 수 있는 기준입니다."
    if "rear_end" in tags and "front_vehicle_stop_reason" in tags:
        return "앞차 정지 사유, 횡단보도·교차로 앞 정지, 급정거 여부, 뒤차 안전거리와 직접 관련된 기준입니다."
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


def _party_chart_prefixes(party: str | None) -> list[str]:
    prefixes = {
        "car_vs_car": ["차%"],
        "vehicle_vs_vehicle": ["차%"],
        "car_vs_person": ["보%"],
        "vehicle_vs_pedestrian": ["보%"],
        "pedestrian": ["보%"],
        "car_vs_bicycle": ["자%", "거%"],
        "vehicle_vs_bicycle": ["자%", "거%"],
        "bicycle": ["자%", "거%"],
        "two_wheeler": ["자%", "거%"],
        "car_vs_object": ["기%"],
        "single_vehicle": ["단%"],
        "vehicle_single": ["단%"],
    }
    return prefixes.get(party or "", [])


def _party_from_chart_no(chart_no: Any) -> str | None:
    text = str(chart_no or "")
    if text.startswith("차"):
        return "car_vs_car"
    if text.startswith("보"):
        return "car_vs_person"
    if text.startswith(("자", "거")):
        return "car_vs_bicycle"
    if text.startswith("기"):
        return "car_vs_object"
    if text.startswith("단"):
        return "single_vehicle"
    return None
