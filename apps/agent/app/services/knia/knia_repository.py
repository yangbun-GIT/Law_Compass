from __future__ import annotations

import os
from typing import Any

import psycopg
import psycopg.rows
from psycopg.types.json import Jsonb

DB_URL = os.getenv("DATABASE_URL", "postgresql://law:lawpass@postgres:5432/lawcompass")


class KniaRepository:
    def __init__(self, db_url: str | None = None):
        self.db_url = db_url or DB_URL

    def ensure_source(self) -> str:
        with psycopg.connect(self.db_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO knia_sources(name, base_url, terms_note)
                VALUES(%s,%s,%s)
                RETURNING id
                """,
                (
                    "과실비율정보포털",
                    "https://accident.knia.or.kr",
                    "관리자 수집 스크립트로 텍스트와 외부 URL만 저장합니다. 영상 파일은 다운로드하지 않습니다.",
                ),
            )
            source_id = str(cur.fetchone()[0])
            conn.commit()
            return source_id

    def upsert_menu_page(self, item: dict[str, Any]) -> str:
        with psycopg.connect(self.db_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO knia_menu_pages(menu_group, menu_name, page_url, title, content_text, plain_summary, source_url, metadata, tsv)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,to_tsvector('simple', %s))
                ON CONFLICT(page_url) DO UPDATE SET
                  menu_group=EXCLUDED.menu_group,
                  menu_name=EXCLUDED.menu_name,
                  title=EXCLUDED.title,
                  content_text=EXCLUDED.content_text,
                  plain_summary=EXCLUDED.plain_summary,
                  source_url=EXCLUDED.source_url,
                  metadata=EXCLUDED.metadata,
                  tsv=EXCLUDED.tsv,
                  updated_at=now()
                RETURNING id
                """,
                (
                    item["menu_group"],
                    item["menu_name"],
                    item["page_url"],
                    item.get("title"),
                    item.get("content_text"),
                    item.get("plain_summary"),
                    item["source_url"],
                    Jsonb(item.get("metadata") or {}),
                    " ".join([item.get("title") or "", item.get("content_text") or "", item.get("plain_summary") or ""]),
                ),
            )
            item_id = str(cur.fetchone()[0])
            conn.commit()
            return item_id

    def insert_rankings(self, rows: list[dict[str, Any]], rank_period: str = "last_30_days") -> int:
        inserted = 0
        with psycopg.connect(self.db_url) as conn, conn.cursor() as cur:
            for row in rows:
                cur.execute(
                    """
                    INSERT INTO knia_fault_rankings(
                      rank_period, rank_no, chart_no, chart_type, title, search_count, percentage,
                      source_url, thumbnail_url, accident_party_type, accident_party_label, display_tags
                    )
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        rank_period,
                        row["rank_no"],
                        row["chart_no"],
                        row.get("chart_type") or "1",
                        row["title"],
                        row.get("search_count"),
                        row.get("percentage"),
                        row.get("source_url"),
                        row.get("thumbnail_url"),
                        row.get("accident_party_type") or "unknown",
                        row.get("accident_party_label") or "사고유형 확인 필요",
                        row.get("display_tags") or [],
                    ),
                )
                inserted += cur.rowcount
            conn.commit()
        return inserted

    def upsert_chart(self, chart: dict[str, Any]) -> str:
        with psycopg.connect(self.db_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO knia_fault_charts(
                  chart_no, chart_type, title, vehicle_a_label, vehicle_b_label, category_path,
                  accident_summary, applicable_text, non_applicable_text, basic_fault_text,
                  base_fault_a, base_fault_b, adjustment_factors, related_laws, precedents,
                  source_url, thumbnail_url, video_url, media_embed_url, media_provider, license_status,
                  attribution, metadata, accident_party_type, accident_party_label, vehicle_a_role, vehicle_b_role,
                  vulnerable_road_user_type, object_type, scenario_summary_easy, recommended_user_actions, display_tags, tsv
                ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,to_tsvector('simple', %s))
                ON CONFLICT(chart_no, chart_type) DO UPDATE SET
                  title=EXCLUDED.title,
                  vehicle_a_label=EXCLUDED.vehicle_a_label,
                  vehicle_b_label=EXCLUDED.vehicle_b_label,
                  category_path=EXCLUDED.category_path,
                  accident_summary=EXCLUDED.accident_summary,
                  applicable_text=EXCLUDED.applicable_text,
                  non_applicable_text=EXCLUDED.non_applicable_text,
                  basic_fault_text=EXCLUDED.basic_fault_text,
                  base_fault_a=EXCLUDED.base_fault_a,
                  base_fault_b=EXCLUDED.base_fault_b,
                  adjustment_factors=EXCLUDED.adjustment_factors,
                  related_laws=EXCLUDED.related_laws,
                  precedents=EXCLUDED.precedents,
                  source_url=EXCLUDED.source_url,
                  thumbnail_url=EXCLUDED.thumbnail_url,
                  video_url=EXCLUDED.video_url,
                  media_embed_url=EXCLUDED.media_embed_url,
                  media_provider='external_url',
                  license_status='source_link_only',
                  attribution=EXCLUDED.attribution,
                  metadata=EXCLUDED.metadata,
                  accident_party_type=EXCLUDED.accident_party_type,
                  accident_party_label=EXCLUDED.accident_party_label,
                  vehicle_a_role=EXCLUDED.vehicle_a_role,
                  vehicle_b_role=EXCLUDED.vehicle_b_role,
                  vulnerable_road_user_type=EXCLUDED.vulnerable_road_user_type,
                  object_type=EXCLUDED.object_type,
                  scenario_summary_easy=EXCLUDED.scenario_summary_easy,
                  recommended_user_actions=EXCLUDED.recommended_user_actions,
                  display_tags=EXCLUDED.display_tags,
                  tsv=EXCLUDED.tsv,
                  updated_at=now()
                RETURNING id
                """,
                (
                    chart["chart_no"], chart.get("chart_type") or "1", chart["title"],
                    chart.get("vehicle_a_label"), chart.get("vehicle_b_label"), Jsonb(chart.get("category_path") or []),
                    chart.get("accident_summary"), chart.get("applicable_text"), chart.get("non_applicable_text"), chart.get("basic_fault_text"),
                    chart.get("base_fault_a"), chart.get("base_fault_b"), Jsonb(chart.get("adjustment_factors") or []), Jsonb(chart.get("related_laws") or []), Jsonb(chart.get("precedents") or []),
                    chart["source_url"], chart.get("thumbnail_url"), chart.get("video_url"), chart.get("media_embed_url"), "external_url", "source_link_only",
                    chart.get("attribution") or "출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털", Jsonb(chart.get("metadata") or {}),
                    chart.get("accident_party_type") or "unknown",
                    chart.get("accident_party_label") or "사고유형 확인 필요",
                    chart.get("vehicle_a_role"), chart.get("vehicle_b_role"), chart.get("vulnerable_road_user_type"), chart.get("object_type"),
                    chart.get("scenario_summary_easy"), Jsonb(chart.get("recommended_user_actions") or []), chart.get("display_tags") or [],
                    " ".join([chart.get("chart_no") or "", chart.get("title") or "", chart.get("accident_summary") or "", chart.get("applicable_text") or "", chart.get("basic_fault_text") or "", chart.get("accident_party_label") or "", " ".join(chart.get("display_tags") or [])]),
                ),
            )
            chart_id = str(cur.fetchone()[0])
            cur.execute(
                """
                UPDATE knia_fault_charts SET
                  source_detail_url=%s,
                  accident_explanation=%s,
                  accident_situation_lines=%s,
                  applied_fault_a=%s,
                  applied_fault_b=%s,
                  adjustment_explanations=%s,
                  related_laws=%s,
                  case_references=%s,
                  raw_detail=%s,
                  raw_html_hash=%s,
                  detail_collected_at=now(),
                  updated_at=now()
                WHERE chart_no=%s AND chart_type=%s
                """,
                (
                    chart.get("source_detail_url") or chart.get("source_url"),
                    chart.get("accident_explanation"),
                    Jsonb(chart.get("accident_situation_lines") or []),
                    chart.get("applied_fault_a"),
                    chart.get("applied_fault_b"),
                    Jsonb(chart.get("adjustment_explanations") or []),
                    Jsonb(chart.get("related_laws") or []),
                    Jsonb(chart.get("case_references") or []),
                    Jsonb(chart.get("raw_detail") or {}),
                    chart.get("raw_html_hash"),
                    chart["chart_no"],
                    chart.get("chart_type") or "1",
                ),
            )
            self.replace_chart_chunks(cur, chart_id, chart)
            self.replace_adjustment_factors(cur, chart)
            self.replace_reference_sections(cur, chart)
            self.upsert_media_assets(cur, chart_id, chart)
            conn.commit()
            return chart_id

    def replace_chart_chunks(self, cur: Any, chart_id: str, chart: dict[str, Any]) -> None:
        cur.execute("DELETE FROM knia_fault_chart_chunks WHERE chart_id=%s", (chart_id,))
        tags = chart.get("scenario_tags") or []
        keywords = chart.get("keywords") or []
        chunks: list[tuple[str, str, str, int]] = []
        prefix = " ".join([
            " > ".join(chart.get("category_path") or []),
            chart.get("accident_party_label") or "",
            " ".join(chart.get("display_tags") or []),
        ]).strip()
        chunks.append(("summary", " ".join([prefix, chart.get("title") or "", chart.get("accident_summary") or ""]), _summary_for(chart), 10))
        if chart.get("basic_fault_text"):
            chunks.append(("basic_fault", chart["basic_fault_text"], "기본 과실비율과 판단 기준입니다.", 20))
        if chart.get("applicable_text"):
            chunks.append(("applicable", chart["applicable_text"], "이 기준이 적용될 수 있는 사고 조건입니다.", 30))
        if chart.get("non_applicable_text"):
            chunks.append(("non_applicable", chart["non_applicable_text"], "이 기준이 맞지 않을 수 있는 조건입니다.", 40))
        for factor in chart.get("adjustment_factors") or []:
            label = factor.get("label") or ""
            delta_a = factor.get("delta_a") or 0
            delta_b = factor.get("delta_b") or 0
            if label:
                chunks.append((
                    "knia_adjustment_factor",
                    f"가감요소: {label}. A {delta_a:+d}, B {delta_b:+d}",
                    "KNIA 원문 가감요소입니다.",
                    50,
                ))
        for item in chart.get("adjustment_explanations") or []:
            body = " ".join([item.get("title") or "", item.get("body") or ""]).strip()
            if body:
                chunks.append(("knia_adjustment_explanation", body, "KNIA 원문 수정요소해설입니다.", 55))
        for item in chart.get("related_laws") or []:
            body = " ".join([item.get("law_title") or "", item.get("law_text") or ""]).strip()
            if body:
                chunks.append(("knia_related_law", body, "KNIA 원문 관련법규입니다.", 60))
        for item in chart.get("case_references") or []:
            body = " ".join([item.get("case_title") or "", item.get("case_body") or "", item.get("decision_summary") or ""]).strip()
            if body:
                chunks.append(("knia_case_reference", body, "KNIA 원문 판례·조정사례입니다.", 65))
        for chunk_type, text, summary, priority in chunks:
            safe_text = (text or "").strip()
            if not safe_text:
                continue
            cur.execute(
                """
                INSERT INTO knia_fault_chart_chunks(
                  chart_id, chunk_type, chunk_text, plain_summary, scenario_tags, keywords,
                  source_url, video_url, display_priority, accident_party_type, display_tags, recommended_user_actions, tsv
                )
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,to_tsvector('simple', %s))
                """,
                (
                    chart_id, chunk_type, safe_text[:5000], summary, tags, keywords,
                    chart.get("source_url"), chart.get("video_url"), priority,
                    chart.get("accident_party_type") or "unknown",
                    chart.get("display_tags") or [],
                    Jsonb(chart.get("recommended_user_actions") or []),
                    " ".join([safe_text, summary, " ".join(tags), " ".join(keywords), chart.get("accident_party_label") or "", " ".join(chart.get("display_tags") or [])]),
                ),
            )

    def replace_adjustment_factors(self, cur: Any, chart: dict[str, Any]) -> None:
        chart_no = chart["chart_no"]
        chart_type = chart.get("chart_type") or "1"
        cur.execute("DELETE FROM knia_adjustment_factors WHERE chart_no=%s AND chart_type=%s", (chart_no, chart_type))
        for idx, factor in enumerate(chart.get("adjustment_factors") or [], start=1):
            label = (factor.get("label") or "").strip()
            if not label:
                continue
            cur.execute(
                """
                INSERT INTO knia_adjustment_factors(
                  chart_no, chart_type, source_case_id, factor_order, label, condition_code,
                  checkbox_value, delta_a, delta_b, raw, source_detail_url, updated_at
                )
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                ON CONFLICT(chart_no, chart_type, source_case_id, factor_order, label) DO UPDATE SET
                  condition_code=EXCLUDED.condition_code,
                  checkbox_value=EXCLUDED.checkbox_value,
                  delta_a=EXCLUDED.delta_a,
                  delta_b=EXCLUDED.delta_b,
                  raw=EXCLUDED.raw,
                  source_detail_url=EXCLUDED.source_detail_url,
                  updated_at=now()
                """,
                (
                    chart_no,
                    chart_type,
                    factor.get("source_case_id") or "case1",
                    int(factor.get("factor_order") or idx),
                    label,
                    factor.get("condition_code"),
                    factor.get("checkbox_value"),
                    int(factor.get("delta_a") or 0),
                    int(factor.get("delta_b") or 0),
                    Jsonb(factor.get("raw") or {}),
                    factor.get("source_detail_url") or chart.get("source_detail_url") or chart.get("source_url"),
                ),
            )

    def replace_reference_sections(self, cur: Any, chart: dict[str, Any]) -> None:
        chart_no = chart["chart_no"]
        chart_type = chart.get("chart_type") or "1"
        cur.execute("DELETE FROM knia_chart_reference_sections WHERE chart_no=%s AND chart_type=%s", (chart_no, chart_type))

        def insert_section(section_type: str, item: dict[str, Any], order: int) -> None:
            cur.execute(
                """
                INSERT INTO knia_chart_reference_sections(
                  chart_no, chart_type, section_type, title, body, law_title, law_text,
                  case_title, case_body, decision_summary, item_order, source_detail_url, raw, updated_at
                )
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                ON CONFLICT DO NOTHING
                """,
                (
                    chart_no,
                    chart_type,
                    section_type,
                    item.get("title"),
                    item.get("body"),
                    item.get("law_title"),
                    item.get("law_text"),
                    item.get("case_title"),
                    item.get("case_body"),
                    item.get("decision_summary"),
                    int(item.get("item_order") or order),
                    item.get("source_detail_url") or chart.get("source_detail_url") or chart.get("source_url"),
                    Jsonb(item.get("raw") or {}),
                ),
            )

        for idx, item in enumerate(chart.get("adjustment_explanations") or [], start=1):
            insert_section("adjustment_explanation", item, idx)
        for idx, item in enumerate(chart.get("related_laws") or [], start=1):
            insert_section("related_law", item, idx)
        for idx, item in enumerate(chart.get("case_references") or [], start=1):
            insert_section("case_reference", item, idx)

    def upsert_media_assets(self, cur: Any, chart_id: str, chart: dict[str, Any]) -> None:
        cur.execute("DELETE FROM knia_media_assets WHERE chart_id=%s", (chart_id,))
        for asset_type, source_url, embed_url, title in [
            ("thumbnail", chart.get("thumbnail_url"), None, "과실비율 기준 썸네일"),
            ("video", chart.get("video_url"), chart.get("media_embed_url"), "과실비율정보포털 관련 영상"),
        ]:
            if not source_url:
                continue
            cur.execute(
                """
                INSERT INTO knia_media_assets(chart_id, asset_type, source_url, embed_url, storage_provider, title, attribution, license_status, metadata)
                VALUES(%s,%s,%s,%s,'external_url',%s,'출처: 과실비율정보포털','source_link_only',%s)
                """,
                (chart_id, asset_type, source_url, embed_url, title, Jsonb({"downloaded": False, "mirrored_to_s3": False})),
            )

    def latest_ranking(self, limit: int = 20) -> list[dict[str, Any]]:
        with psycopg.connect(self.db_url) as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                """
                SELECT rank_no, chart_no, chart_type, title, search_count, percentage, source_url, thumbnail_url, collected_at
                FROM knia_fault_rankings
                WHERE collected_at = (SELECT max(collected_at) FROM knia_fault_rankings)
                ORDER BY rank_no ASC
                LIMIT %s
                """,
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]

    def ranking_chart_targets(self, limit: int | None = None, force: bool = False) -> list[dict[str, Any]]:
        params: list[Any] = []
        where = "r.chart_no IS NOT NULL"
        if not force:
            where += " AND (c.detail_collected_at IS NULL OR c.raw_html_hash IS NULL)"
        limit_sql = ""
        if limit:
            params.append(limit)
            limit_sql = "LIMIT %s"
        with psycopg.connect(self.db_url) as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                f"""
                SELECT DISTINCT r.chart_no, COALESCE(r.chart_type, '1') AS chart_type,
                       r.source_detail_url, r.local_chart_url
                FROM knia_ranking_items r
                LEFT JOIN knia_fault_charts c
                  ON c.chart_no = r.chart_no AND c.chart_type = COALESCE(r.chart_type, '1')
                WHERE {where}
                ORDER BY r.chart_no, COALESCE(r.chart_type, '1')
                {limit_sql}
                """,
                params,
            )
            return [dict(r) for r in cur.fetchall()]

    def get_chart_adjustments(self, chart_no: str, chart_type: str = "1") -> list[dict[str, Any]]:
        with psycopg.connect(self.db_url) as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                """
                SELECT label, condition_code, checkbox_value, delta_a, delta_b, source_case_id,
                       factor_order, source_detail_url
                FROM knia_adjustment_factors
                WHERE chart_no=%s AND chart_type=%s
                ORDER BY factor_order ASC, id ASC
                """,
                (chart_no, chart_type),
            )
            return [dict(r) for r in cur.fetchall()]

    def get_chart_references(self, chart_no: str, chart_type: str = "1") -> dict[str, list[dict[str, Any]]]:
        buckets = {"adjustment_explanations": [], "related_laws": [], "case_references": []}
        with psycopg.connect(self.db_url) as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                """
                SELECT section_type, title, body, law_title, law_text, case_title, case_body,
                       decision_summary, item_order, source_detail_url
                FROM knia_chart_reference_sections
                WHERE chart_no=%s AND chart_type=%s
                ORDER BY section_type ASC, item_order ASC, id ASC
                """,
                (chart_no, chart_type),
            )
            for row in cur.fetchall():
                item = dict(row)
                section_type = item.pop("section_type")
                if section_type == "adjustment_explanation":
                    buckets["adjustment_explanations"].append(item)
                elif section_type == "related_law":
                    buckets["related_laws"].append(item)
                elif section_type == "case_reference":
                    buckets["case_references"].append(item)
        return buckets



    def upsert_ranking_items(self, rows: list[dict[str, Any]]) -> int:
        changed = 0
        with psycopg.connect(self.db_url) as conn, conn.cursor() as cur:
            for row in rows:
                chart_type = str(row.get("chart_type") or "1")
                local_chart_url = row.get("local_chart_url") or row.get("chart_url") or f"/knia/charts/{row['chart_no']}?chartType={chart_type}"
                cur.execute(
                    """
                    INSERT INTO knia_ranking_items(
                      source_category, accident_party_type, rank, chart_no, chart_type, title, search_count, percentage,
                      source_url, source_detail_url, local_chart_url, source_onclick, chart_url, raw, collected_at, updated_at
                    ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),now())
                    ON CONFLICT(source_category, rank, chart_no) DO UPDATE SET
                      accident_party_type=EXCLUDED.accident_party_type,
                      chart_type=EXCLUDED.chart_type,
                      title=EXCLUDED.title,
                      search_count=EXCLUDED.search_count,
                      percentage=EXCLUDED.percentage,
                      source_url=EXCLUDED.source_url,
                      source_detail_url=EXCLUDED.source_detail_url,
                      local_chart_url=EXCLUDED.local_chart_url,
                      source_onclick=EXCLUDED.source_onclick,
                      chart_url=EXCLUDED.chart_url,
                      raw=EXCLUDED.raw,
                      collected_at=EXCLUDED.collected_at,
                      updated_at=now()
                    """,
                    (
                        row["source_category"],
                        row["accident_party_type"],
                        row["rank"],
                        row["chart_no"],
                        chart_type,
                        row["title"],
                        row.get("search_count"),
                        row.get("percentage"),
                        row.get("source_url") or "https://accident.knia.or.kr/ranking",
                        row.get("source_detail_url"),
                        local_chart_url,
                        row.get("source_onclick"),
                        row.get("chart_url") or local_chart_url,
                        Jsonb(row.get("raw") or {}),
                    ),
                )
                changed += 1
            conn.commit()
        return changed

    def latest_ranking_items(self, accident_party_type: str = "all", q: str = "", limit: int = 20) -> list[dict[str, Any]]:
        category_map = {
            "all": "\uc804\uccb4", "\uc804\uccb4": "\uc804\uccb4",
            "car_vs_car": "\ucc28\ub300\ucc28", "\ucc28\ub300\ucc28": "\ucc28\ub300\ucc28",
            "car_vs_person": "\ucc28\ub300\uc0ac\ub78c", "\ucc28\ub300\uc0ac\ub78c": "\ucc28\ub300\uc0ac\ub78c",
            "car_vs_bicycle": "\ucc28\ub300\uc790\uc804\uac70", "\ucc28\ub300\uc790\uc804\uac70": "\ucc28\ub300\uc790\uc804\uac70",
        }
        source_category = category_map.get(accident_party_type or "all", "\uc804\uccb4")
        params: list[Any] = [source_category]
        where = "source_category=%s AND collected_at >= (SELECT max(collected_at) - interval '10 minutes' FROM knia_ranking_items WHERE source_category=%s)"
        params.append(source_category)
        if q:
            where += " AND (title ILIKE %s OR chart_no ILIKE %s)"
            params.extend([f"%{q}%", f"%{q}%"])
        params.append(limit)
        with psycopg.connect(self.db_url) as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                f"""
                SELECT rank, chart_no, chart_type, title, search_count, percentage, source_category, accident_party_type,
                       source_url, source_detail_url, local_chart_url, source_onclick, chart_url, collected_at
                FROM knia_ranking_items
                WHERE {where}
                ORDER BY rank ASC
                LIMIT %s
                """,
                params,
            )
            return [dict(r) for r in cur.fetchall()]


    def get_chart(self, chart_no: str, chart_type: str = "1") -> dict[str, Any] | None:
        with psycopg.connect(self.db_url) as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT * FROM knia_fault_charts WHERE chart_no=%s AND chart_type=%s", (chart_no, chart_type))
            row = cur.fetchone()
            return dict(row) if row else None


def _summary_for(chart: dict[str, Any]) -> str:
    if chart.get("base_fault_a") is not None and chart.get("base_fault_b") is not None:
        return f"기본 과실은 A차량 {chart['base_fault_a']}%, B차량 {chart['base_fault_b']}%로 표시된 KNIA 참고 기준입니다."
    return "사고 상황과 유사한 과실비율 인정기준입니다."
