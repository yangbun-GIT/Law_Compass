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
from app.services.knia.party_guard import (
    canonicalize_party_type,
    filter_tags_by_party,
    filter_terms_by_party,
    reject_mismatched_knia_items,
)
from app.services.knia.knia_fault_adjuster import (
    select_structured_base_fault_candidate,
    structured_chart_final_fault_eligible,
)
from app.services.knia.knia_json_repository import get_knia_fault_chart, list_knia_fault_charts_by_party, search_knia_fault_charts
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
    "stealth_illegal_parked_vehicle_collision": ["parking", "stopped_vehicle", "unlit_stopped_vehicle", "visibility", "night", "road_obstruction", "avoidability"],
}

PARTY_FALLBACK_TERMS = {
    "car_vs_car": ("차대차", "차량 사고", "과실비율", "후미추돌", "차선변경", "교차로"),
    "car_vs_person": ("차대사람", "보행자", "횡단보도", "보행자 보호의무"),
    "car_vs_bicycle": ("차대자전거", "자전거", "자전거도로", "자전거 통행 위치"),
    "car_vs_motorcycle": ("차대오토바이", "차대이륜차", "오토바이", "이륜차", "원동기장치자전거"),
    "car_vs_object": ("차대기물", "시설물", "가드레일", "전봇대", "중앙분리대"),
    "single_vehicle": ("차량단독", "단독사고", "도로이탈", "전복"),
}

STATIC_LANE_CHANGE_CHART_NO = "차43-2"


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
    if scenario_type == "stealth_illegal_parked_vehicle_collision":
        facts = {**facts, "accident_party_type": "car_vs_car"}
        accident_party_type = "car_vs_car"
    party = canonicalize_party_type(
        accident_party_type
        or facts.get("knia_major_party_type")
        or facts.get("accident_party_type")
        or infer_party_type_from_text(description_text, {**facts, "accident_type": scenario_type or facts.get("accident_type")})
    )
    if scenario_type == "stealth_illegal_parked_vehicle_collision":
        party = "car_vs_car"
    expansion_terms = scenario_search_terms(
        scenario_type=scenario_type,
        scenario_tags=SCENARIO_TO_TAGS.get(scenario_type or "", []),
        facts=facts,
        selected_keywords=keywords,
        accident_party_type=party,
    )
    expansion_terms = filter_terms_by_party(expansion_terms, party, facts)
    keywords = filter_terms_by_party(keywords, party, facts)
    if scenario_type == "stealth_illegal_parked_vehicle_collision":
        expansion_terms = _strip_bicycle_pollution(expansion_terms)
        keywords = _strip_bicycle_pollution(keywords)
    q = normalize_query(" ".join([description_text or "", json.dumps(facts, ensure_ascii=False), " ".join(keywords), scenario_type or "", party or "", " ".join(expansion_terms)]))
    if scenario_type == "stealth_illegal_parked_vehicle_collision":
        q = " ".join(_strip_bicycle_pollution([q]))
    direct_lookup_text = normalize_query(" ".join([description_text or "", " ".join(keywords)]))
    chart_direct = re.search(r"[차보자기단]\d{1,3}(?:-\d+)?", direct_lookup_text)
    tags = filter_tags_by_party(list(dict.fromkeys([*(SCENARIO_TO_TAGS.get(scenario_type or "", [])), *_tags_from_text(q, party)])), party, facts)
    if scenario_type == "stealth_illegal_parked_vehicle_collision":
        tags = [tag for tag in tags if tag != "bicycle"]
    structured_lookup_error = None
    structured_items: list[dict[str, Any]] = []
    structured_rejected: list[dict[str, Any]] = []
    try:
        structured_items = _structured_chart_lookup(
            party=party,
            scenario_type=scenario_type,
            query_terms=expansion_terms,
            chart_no=chart_direct.group(0) if chart_direct else None,
            limit=limit,
        )
        structured_items, structured_rejected = reject_mismatched_knia_items(structured_items, party)
        if not structured_items and not chart_direct and party != "unknown":
            fallback_rows = list_knia_fault_charts_by_party(party, limit=limit)
            structured_items, fallback_rejected = reject_mismatched_knia_items(
                [_structured_chart_to_match(row, 0.28, "같은 대분류 안에서 참고할 수 있는 구조화 KNIA 기준입니다.", reference_only=True) for row in fallback_rows],
                party,
            )
            structured_rejected.extend(fallback_rejected)
    except Exception as exc:
        structured_lookup_error = _safe_error(exc)
    if structured_items:
        fallback_used = not chart_direct and not any(item.get("scenario_type") == scenario_type for item in structured_items)
        primary = structured_items[0]
        return {
            "items": structured_items,
            "cache_hit": False,
            "cache_key": None,
            "accident_party_type": party,
            "requested_party_type": party,
            "query_expansion_terms": expansion_terms,
            "lookup_error": None,
            "structured_lookup_error": structured_lookup_error,
            "structured_chart_used": True,
            "chart_no": primary.get("chart_no"),
            "aggregate_chart_no": primary.get("aggregate_chart_no"),
            "party_guard_policy": _party_guard_policy(party),
            "rejected_mismatch_count": len(structured_rejected),
            "fallback_used": fallback_used,
            "no_knia_match_reason": None,
            "review_required": bool(primary.get("review_required", False)),
            "parsing_confidence": primary.get("parsing_confidence"),
            "excluded_items": structured_rejected,
        }

    cache_key = "knia:match:v10:" + hashlib.sha256(json.dumps({"q": q, "tags": tags, "party": party, "scenario_type": scenario_type, "limit": limit}, ensure_ascii=False).encode("utf-8")).hexdigest()[:24]
    cache = _redis_client()
    if cache:
        cached = cache.get(cache_key)
        if cached:
            cached_items = json.loads(cached)
            return {
                "items": cached_items,
                "cache_hit": True,
                "cache_key": cache_key,
                "accident_party_type": party,
                "requested_party_type": party,
                "query_expansion_terms": expansion_terms,
                "party_guard_policy": _party_guard_policy(party),
                "rejected_mismatch_count": 0,
                "fallback_used": False,
                "structured_chart_used": False,
                "chart_no": cached_items[0].get("chart_no") if cached_items else None,
                "no_knia_match_reason": None if cached_items else "no_same_party_knia_match",
            }
    lookup_error = None
    fallback_lookup_error = None
    fallback_used = False
    rejected_mismatch_count = 0
    excluded_items: list[dict[str, Any]] = []
    try:
        if chart_direct:
            raw_items = _direct_lookup(chart_direct.group(0), limit)
            items, excluded_items = _filter_scenario_compatible_matches(raw_items, scenario_type)
        else:
            items = _hybrid_lookup(q, tags, party, limit, scenario_type=scenario_type)
        items, party_rejected = reject_mismatched_knia_items(items, party)
        excluded_items.extend(party_rejected)
        rejected_mismatch_count = len(party_rejected)
        if not items and not chart_direct:
            fallback_used = True
            fallback_query = normalize_query(" ".join([party, scenario_type or "", " ".join(PARTY_FALLBACK_TERMS.get(party, ())), " ".join(expansion_terms[:6])]))
            fallback_items = _hybrid_lookup(fallback_query, tags, None if party == "car_vs_motorcycle" else party, limit, scenario_type=scenario_type)
            if party == "car_vs_motorcycle" and not fallback_items:
                fallback_items = _hybrid_lookup(fallback_query, ["motorcycle", "two_wheeler"], None, limit, scenario_type=None)
            items, fallback_rejected = reject_mismatched_knia_items(fallback_items, party)
            excluded_items.extend(fallback_rejected)
            rejected_mismatch_count += len(fallback_rejected)
    except Exception as exc:
        items = []
        fallback_lookup_error = _safe_error(exc)
    if not items and _should_use_static_lane_change_fallback(scenario_type, party):
        fallback_used = True
        items, fallback_rejected = reject_mismatched_knia_items(
            _static_lane_change_matches(limit=limit),
            party,
        )
        excluded_items.extend(fallback_rejected)
        rejected_mismatch_count += len(fallback_rejected)
        if items:
            lookup_error = None
        else:
            lookup_error = fallback_lookup_error
    elif fallback_lookup_error:
        lookup_error = fallback_lookup_error
    if cache:
        cache.setex(cache_key, 900, json.dumps(items, ensure_ascii=False))
    no_match_reason = None
    if not items:
        no_match_reason = "lookup_error" if lookup_error else "no_same_party_knia_match"
    return {
        "items": items,
        "cache_hit": False,
        "cache_key": cache_key,
        "accident_party_type": party,
        "requested_party_type": party,
        "query_expansion_terms": expansion_terms,
        "lookup_error": lookup_error,
        "fallback_lookup_error": fallback_lookup_error,
        "structured_lookup_error": structured_lookup_error,
        "structured_chart_used": False,
        "chart_no": items[0].get("chart_no") if items else None,
        "party_guard_policy": _party_guard_policy(party),
        "rejected_mismatch_count": rejected_mismatch_count + len(structured_rejected),
        "fallback_used": fallback_used,
        "no_knia_match_reason": no_match_reason,
        "review_required": bool(items[0].get("review_required", False)) if items else None,
        "parsing_confidence": items[0].get("parsing_confidence") if items else None,
        "excluded_items": excluded_items,
    }


def _should_use_static_lane_change_fallback(scenario_type: str | None, party: str | None) -> bool:
    return scenario_type == "lane_change_collision" and canonicalize_party_type(party) in {"car_vs_car", "unknown"}


def _structured_chart_lookup(
        *,
        party: str | None,
        scenario_type: str | None,
        query_terms: list[str],
        chart_no: str | None,
        limit: int,
) -> list[dict[str, Any]]:
    if chart_no:
        chart = get_knia_fault_chart(chart_no)
        if not chart:
            return []
        return [_structured_chart_to_match(chart, 0.95, "입력 내용에 구조화 KNIA 기준번호가 직접 포함되어 있습니다.")]
    rows = search_knia_fault_charts(party, scenario_type, query_terms, limit=limit)
    matches: list[dict[str, Any]] = []
    for row in rows:
        score = float(row.get("match_score") or 0.55)
        if row.get("scenario_type") == scenario_type:
            score = max(score, 0.72)
        reason = "구조화된 2023.6 KNIA JSON chart가 사고 대분류와 사고유형에 맞습니다."
        if not structured_chart_final_fault_eligible(row):
            reason += " 다만 기본과실 또는 원문 근거가 불완전해 참고 기준으로 표시합니다."
        matches.append(_structured_chart_to_match(row, score, reason))
    return matches


def _structured_chart_to_match(
        row: dict[str, Any],
        score: float,
        reason: str,
        *,
        reference_only: bool | None = None,
) -> dict[str, Any]:
    match = _to_match(row, score, reason)
    review_required = bool(row.get("review_required", False))
    selected_candidate = select_structured_base_fault_candidate(row)
    selected_fault = _base_fault_pair_from_candidate(selected_candidate)
    aggregate_chart_no = row.get("aggregate_chart_no") or row.get("chart_no")
    display_chart_no = (selected_candidate or {}).get("subchart_no") or row.get("chart_no")
    forced_reference_only = bool(reference_only)
    final_fault_eligible = (not forced_reference_only) and structured_chart_final_fault_eligible(row, selected_candidate)
    no_base_fault = not bool(selected_fault)
    if selected_fault:
        match["base_fault_a"] = selected_fault["A"]
        match["base_fault_b"] = selected_fault["B"]
    if display_chart_no:
        match["chart_no"] = display_chart_no
    match.update(
        {
            "structured_chart_used": True,
            "source_type": "knia_structured_chart",
            "source_family": "knia",
            "evidence_family": "knia",
            "aggregate_chart_no": aggregate_chart_no if aggregate_chart_no != display_chart_no else None,
            "major_party_type": row.get("major_party_type") or row.get("accident_party_type"),
            "scenario_type": row.get("scenario_type"),
            "scenario_subtype": row.get("scenario_subtype"),
            "vehicle_roles": row.get("vehicle_roles") or {},
            "base_fault": row.get("base_fault") or {},
            "selected_base_fault_candidate": selected_candidate or {},
            "adjustments": row.get("adjustments") or row.get("adjustment_factors") or [],
            "related_laws": row.get("related_laws") or [],
            "accident_situation": row.get("accident_situation") or row.get("accident_summary"),
            "base_fault_explanation": row.get("base_fault_explanation") or row.get("basic_fault_text"),
            "usage_notes": row.get("usage_notes"),
            "raw_text": row.get("raw_text"),
            "parsing_confidence": row.get("parsing_confidence"),
            "review_required": review_required,
            "reference_only": not final_fault_eligible,
            "reference_only_forced": forced_reference_only,
            "final_fault_eligible": final_fault_eligible,
            "page_start": row.get("page_start"),
            "page_end": row.get("page_end"),
            "display_tags": _structured_display_tags(row),
            "scenario_tags": SCENARIO_TO_TAGS.get(str(row.get("scenario_type") or ""), []),
            "keywords": _structured_keywords(row, selected_candidate),
        }
    )
    if match["reference_only"]:
        match["match_label"] = "검수 필요 구조화 KNIA 참고 기준입니다." if review_required else "구조화 KNIA 참고 기준입니다."
    elif review_required:
        match["match_label"] = "검수 표시가 있지만 기본과실과 원문 근거가 확인된 구조화 KNIA 기준입니다."
    return match


def _base_fault_pair_from_candidate(candidate: dict[str, Any] | None) -> dict[str, int] | None:
    if not candidate:
        return None
    a = candidate.get("A")
    b = candidate.get("B")
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        a_i = max(0, min(100, int(a)))
        b_i = max(0, min(100, int(b)))
        if a_i + b_i != 100:
            b_i = 100 - a_i
        return {"A": a_i, "B": b_i}
    return None


def _structured_display_tags(row: dict[str, Any]) -> list[str]:
    tags = list(row.get("display_tags") or [])
    scenario_type = str(row.get("scenario_type") or "")
    tags.extend(SCENARIO_TO_TAGS.get(scenario_type, []))
    party = row.get("major_party_type") or row.get("accident_party_type")
    if party:
        tags.append(str(party))
    return list(dict.fromkeys(str(tag) for tag in tags if tag))


def _structured_keywords(row: dict[str, Any], selected_candidate: dict[str, Any] | None) -> list[str]:
    keywords = list(row.get("keywords") or [])
    scenario_type = str(row.get("scenario_type") or "")
    if scenario_type == "lane_change_collision":
        keywords.extend(["lane_change", "진로변경", "차로변경", "차선변경", "끼어들기"])
    if scenario_type == "rear_end_collision":
        keywords.extend(["rear_end", "후미추돌", "후방추돌", "안전거리"])
    for key in ("subchart_no", "source_text", "vehicle_roles"):
        value = (selected_candidate or {}).get(key)
        if value:
            keywords.append(str(value))
    return list(dict.fromkeys(str(keyword) for keyword in keywords if keyword))


def _static_lane_change_matches(*, limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    return [
        {
            "chart_id": "static-knia-lane-change-43-2",
            "chart_no": STATIC_LANE_CHANGE_CHART_NO,
            "chart_type": "1",
            "title": "동일방향 후행 직진차와 선행 진로변경차 사고",
            "match_score": 0.52,
            "match_label": "대분류는 맞지만 세부유형 일치도가 낮은 참고 기준입니다.",
            "match_reason": "KNIA 조회가 비어 있거나 실패하여 차대차 차선변경 사고의 정적 참고 기준을 사용했습니다.",
            "accident_party_type": "car_vs_car",
            "accident_party_label": party_label("car_vs_car"),
            "base_fault_a": 30,
            "base_fault_b": 70,
            "accident_summary": "같은 방향으로 진행하던 후행 직진차와 선행 진로변경차의 충돌 구조입니다.",
            "scenario_summary_easy": "직진 차량보다 차로를 바꾸는 차량의 주의의무가 더 크게 반영되는 차대차 차선변경 기준입니다.",
            "basic_fault_text": "기본 참고 과실: A 후행 직진차 30%, B 선행 진로변경차 70%",
            "recommended_user_actions": party_actions("car_vs_car"),
            "display_tags": ["vehicle", "lane_change", "fault_ratio", "차43-2"],
            "scenario_tags": ["lane_change", "fault_ratio"],
            "keywords": ["진로변경", "차로변경", "차선변경", "끼어들기", "후행 직진차", "진로변경차"],
            "source_type": "knia_fault_standard_static_fallback",
            "source_family": "knia",
            "evidence_family": "knia",
            "source": "과실비율정보포털 KNIA 차선변경 기준 fallback",
            "used_for": "KNIA 차선변경 기본과실 참고",
            "is_static_fallback": True,
            "fallback_used": True,
            "attribution": "자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털",
        }
    ][:limit]


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
        ("motorcycle", ["오토바이", "이륜차", "원동기장치자전거", "motorcycle"]),
        ("two_wheeler", ["오토바이", "이륜차", "two wheeler", "two_wheeler"]),
        ("non_contact_trigger", ["비접촉", "유발", "non contact", "non-contact", "trigger"]),
        ("time_gap", ["시간적 여유", "4초", "반응 시간", "reaction time", "time gap", "급제동", "급정거"]),
        ("object", ["기물", "시설물", "가드레일", "전봇대", "중앙분리대", "기둥", "벽"]),
        ("single_vehicle", ["혼자", "단독", "미끄러", "전복", "빗길", "눈길"]),
        ("parking", ["주차", "정차"]),
    ]
    for tag, words in checks:
        if any(w in text for w in words):
            tags.append(tag)
    party_tag = {"car_vs_person": "pedestrian", "car_vs_bicycle": "bicycle", "car_vs_motorcycle": "motorcycle", "car_vs_object": "object", "single_vehicle": "single_vehicle", "car_vs_car": "vehicle"}.get(party or "")
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
        "motorcycle_collision": {"car_vs_motorcycle"},
        "object_collision": {"car_vs_object"},
        "single_vehicle_accident": {"single_vehicle"},
        "intersection_signal_violation": {"car_vs_car"},
        "lane_change_collision": {"car_vs_car"},
        "rear_end_collision": {"car_vs_car"},
        "stealth_illegal_parked_vehicle_collision": {"car_vs_car"},
    }.get(scenario_type or "")
    if expected_parties and party not in expected_parties:
        return True

    has_signal_terms = any(w in joined_text for w in ["신호위반", "적색", "빨간불", "교차로 신호", "녹색신호"])
    has_lane_terms = any(w in joined_text for w in ["진로 변경", "진로변경", "차로를 변경", "차선변경", "끼어들", "방향지시"])
    if scenario_type == "motorcycle_collision":
        return party != "car_vs_motorcycle" and not any(token in joined_text for token in ("오토바이", "이륜", "motorcycle"))
    if scenario_type == "intersection_signal_violation":
        # Vehicle-vs-vehicle signal violation standards should stay in the 차12 family.
        # Do not let pedestrian/bicycle signal charts win only because they contain
        # generic "신호위반" terms.
        return not chart_no.startswith("차12")
    if scenario_type == "lane_change_collision":
        return not (chart_no.startswith("차43") or has_lane_terms)
    if scenario_type == "rear_end_collision":
        return _rear_end_primary_exclusion_reason(row, joined_text) is not None
    if scenario_type == "stealth_illegal_parked_vehicle_collision":
        return chart_no.startswith(("자", "거", "보")) or any(token in joined_text for token in ("자전거", "bicycle", "cyclist", "보행자"))
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
            "accident_situation",
            "scenario_summary_easy",
            "scenario_type",
            "scenario_subtype",
            "basic_fault_text",
            "base_fault_explanation",
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
    if "motorcycle" in tags or "two_wheeler" in tags:
        if any(token in joined_text for token in ["오토바이", "이륜", "원동기", "motorcycle"]):
            adjustment += 0.32
        if chart_no.startswith(("보", "자", "거", "기", "단")):
            adjustment -= 0.32

    if "centerline" in tags or "oncoming_vehicle" in tags or "road_obstruction" in tags:
        if chart_no.startswith("차43") or has_lane_terms:
            adjustment += 0.24
        if chart_no.startswith(("차41", "차42")):
            adjustment -= 0.18
    if "parking" in tags or "stopped_vehicle" in tags or "unlit_stopped_vehicle" in tags:
        if chart_no.startswith(("차41", "차42")):
            adjustment += 0.18
        if chart_no.startswith(("자", "거", "보")):
            adjustment -= 0.45

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
    if party == "car_vs_motorcycle" or "motorcycle" in tags or "two_wheeler" in tags:
        return "오토바이 또는 이륜차와 충돌한 사고라는 점이 유사합니다."
    if party == "car_vs_object" or "object" in tags:
        return "시설물이나 기물과 충돌한 사고라는 점이 유사합니다."
    if party == "single_vehicle" or "single_vehicle" in tags:
        return "다른 차량 없이 혼자 발생한 사고라는 점이 유사합니다."
    return "입력하신 사고 내용과 비슷한 과실비율 기준입니다."


def _to_match(row: dict[str, Any], score: float, reason: str) -> dict[str, Any]:
    media = select_media(row)
    party = _row_party_type(row)
    base_a = row.get("base_fault_a")
    base_b = row.get("base_fault_b")
    if (base_a is None or base_b is None) and isinstance(row.get("base_fault"), dict):
        base_a, base_b = _base_fault_pair(row.get("base_fault"))
    return {
        "chart_id": str(row.get("id")),
        "chart_no": row.get("chart_no"),
        "chart_type": row.get("chart_type") or "1",
        "title": row.get("title"),
        "match_score": round(score, 4),
        "match_label": "관련성이 높은 기준입니다." if score >= 0.35 else "참고할 수 있는 기준입니다.",
        "match_reason": reason,
        "accident_party_type": party,
        "major_party_type": row.get("major_party_type") or party,
        "accident_party_label": party_label(party),
        "base_fault_a": base_a,
        "base_fault_b": base_b,
        "accident_summary": row.get("accident_summary") or row.get("accident_situation"),
        "scenario_summary_easy": row.get("scenario_summary_easy"),
        "basic_fault_text": row.get("basic_fault_text") or row.get("base_fault_explanation"),
        "recommended_user_actions": row.get("recommended_user_actions") or party_actions(party),
        "display_tags": row.get("display_tags") or [],
        "source_url": row.get("source_url"),
        "thumbnail_url": row.get("thumbnail_url"),
        "video_url": row.get("video_url"),
        "media": media,
        "attribution": row.get("attribution") or "자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털",
    }


def _row_party_type(row: dict[str, Any]) -> str:
    return row.get("major_party_type") or _party_from_chart_no(row.get("chart_no")) or row.get("accident_party_type") or "unknown"


def _base_fault_pair(base_fault: dict[str, Any]) -> tuple[int | None, int | None]:
    for candidate in base_fault.get("candidates") or []:
        if not isinstance(candidate, dict):
            continue
        a = candidate.get("A")
        b = candidate.get("B")
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return int(a), int(b)
    a = base_fault.get("A")
    b = base_fault.get("B")
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return int(a), int(b)
    return None, None


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
        "car_vs_motorcycle": [],
        "motorcycle": [],
        "car_vs_object": ["기%"],
        "single_vehicle": ["단%"],
        "vehicle_single": ["단%"],
    }
    return prefixes.get(party or "", [])


def _party_guard_policy(party: str) -> dict[str, Any]:
    return {
        "requested_party_type": party or "unknown",
        "policy": "final_knia_candidates_must_match_major_party_type",
        "fallback_scope": "same_party_only",
        "mismatched_party_display": "rejected",
    }


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


def _strip_bicycle_pollution(values: list[str]) -> list[str]:
    blocked = (
        "자전거",
        "차대자전거",
        "bicycle",
        "cyclist",
        "non-contact bicycle trigger",
        "자전거 비접촉 유발",
        "자전거 회피 정지",
    )
    out: list[str] = []
    for value in values:
        text = str(value or "")
        lower = text.lower()
        if any(token in text for token in blocked) or any(token in lower for token in blocked):
            continue
        out.append(text)
    return out
