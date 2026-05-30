from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

import psycopg
import psycopg.rows
from psycopg.types.json import Jsonb

from app.services.knia.party_guard import canonicalize_party_type
from app.services.knia.knia_json_parser import infer_accident_party_type, infer_myaccident_no, normalize_document, parse_visible_items_to_menu_nodes
from app.services.knia.taxonomy import party_label


BASE_URL = "https://accident.knia.or.kr"
LOCAL_JSON_CANDIDATES = (
    "scripts/knia_fault_ratio/knia_fault_ratio.json",
    "scripts/knia_fault_ratio/knia_fault_ratio_2023_06.review.json",
    "scripts/knia_fault_ratio/knia_fault_ratio_2023_06.codex_review.json",
    "scripts/knia_fault_ratio/knia_fault_ratio_2023_06.codex_catalog.json",
    "../../scripts/knia_fault_ratio/knia_fault_ratio.json",
    "../../scripts/knia_fault_ratio/knia_fault_ratio_2023_06.review.json",
    "../../scripts/knia_fault_ratio/knia_fault_ratio_2023_06.codex_review.json",
    "../../scripts/knia_fault_ratio/knia_fault_ratio_2023_06.codex_catalog.json",
    "/app/scripts/knia_fault_ratio/knia_fault_ratio.json",
    "/app/scripts/knia_fault_ratio/knia_fault_ratio_2023_06.review.json",
    "/app/scripts/knia_fault_ratio/knia_fault_ratio_2023_06.codex_review.json",
    "/app/scripts/knia_fault_ratio/knia_fault_ratio_2023_06.codex_catalog.json",
)


def _db_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL missing")
    return url


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


def _page_value(item: dict[str, Any], key: str) -> Any:
    return item.get(key) if item.get(key) is not None else item.get(f"{key}_pdf")


def _base_fault_pair(base_fault: Any) -> tuple[int | None, int | None]:
    if not isinstance(base_fault, dict):
        return None, None
    for candidate in base_fault.get("candidates") or []:
        if not isinstance(candidate, dict):
            continue
        a = candidate.get("A")
        b = candidate.get("B")
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and 0 <= int(a) <= 100 and 0 <= int(b) <= 100:
            return int(a), int(b)
    a = base_fault.get("A")
    b = base_fault.get("B")
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return int(a), int(b)
    return None, None


def _chart_search_text(chart: dict[str, Any]) -> str:
    return " ".join(
        str(chart.get(key) or "")
        for key in (
            "chart_no",
            "title",
            "scenario_type",
            "scenario_subtype",
            "accident_situation",
            "base_fault_explanation",
            "usage_notes",
            "raw_text",
        )
    ).lower()


def _score_chart(chart: dict[str, Any], scenario_type: str | None, query_terms: list[str]) -> float:
    score = 0.0
    if scenario_type and chart.get("scenario_type") == scenario_type:
        score += 0.45
    text = _chart_search_text(chart)
    for term in query_terms or []:
        normalized = str(term or "").strip().lower()
        if normalized and normalized in text:
            score += 0.08
    if chart.get("review_required"):
        score -= 0.18
    if not chart.get("base_fault"):
        score -= 0.12
    confidence = chart.get("parsing_confidence")
    if isinstance(confidence, (int, float)):
        score += max(0.0, min(float(confidence), 1.0)) * 0.12
    query_text = normalize_text(" ".join(query_terms or []))
    score += _local_special_boost(chart, query_text, canonicalize_party_type(chart.get("major_party_type") or chart.get("accident_party_type")))
    return round(score, 4)


def start_import_run(path: str, file_hash: str, metadata: dict[str, Any]) -> str:
    with psycopg.connect(_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO knia_json_import_runs(source_file_path, source_file_hash, source_site, base_url, collected_at, metadata)
            VALUES (%s,%s,%s,%s,%s,%s::jsonb)
            RETURNING id
            """,
            (path, file_hash, metadata.get("site"), metadata.get("base_url"), metadata.get("collected_at"), _json(metadata)),
        )
        run_id = cur.fetchone()[0]
        conn.commit()
        return str(run_id)


def finish_import_run(run_id: str, stats: dict[str, Any]) -> None:
    with psycopg.connect(_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE knia_json_import_runs
            SET imported_pages=%s, imported_documents=%s, imported_menu_nodes=%s, imported_media_assets=%s,
                imported_chunks=%s, status='success', finished_at=now(), metadata=metadata || %s::jsonb
            WHERE id=%s
            """,
            (
                stats.get("imported_pages", 0), stats.get("imported_documents", 0), stats.get("imported_menu_nodes", 0),
                stats.get("imported_media_assets", 0), stats.get("imported_chunks", 0), _json({"stats": stats}), run_id,
            ),
        )
        conn.commit()


def fail_import_run(run_id: str, error: str) -> None:
    with psycopg.connect(_db_url()) as conn, conn.cursor() as cur:
        cur.execute("UPDATE knia_json_import_runs SET status='failed', error_message=%s, finished_at=now() WHERE id=%s", (error[:2000], run_id))
        conn.commit()


def upsert_knia_fault_charts(document_id: str, charts: list[dict[str, Any]]) -> dict[str, int]:
    imported = 0
    review_required = 0
    skipped = 0
    with psycopg.connect(_db_url()) as conn, conn.cursor() as cur:
        for chart in charts or []:
            chart_no = str(chart.get("chart_no") or "").strip()
            title = str(chart.get("title") or "").strip()
            major_party_type = canonicalize_party_type(chart.get("major_party_type"))
            scenario_type = str(chart.get("scenario_type") or "").strip()
            if not chart_no or not title or major_party_type == "unknown" or not scenario_type:
                skipped += 1
                continue
            base_a, base_b = _base_fault_pair(chart.get("base_fault"))
            source_url = chart.get("source_url") or f"{BASE_URL}/"
            cur.execute(
                """
                INSERT INTO knia_fault_charts(
                  document_id, chart_no, chart_type, title, major_party_type, scenario_type, scenario_subtype,
                  page_start, page_end, vehicle_roles, base_fault, adjustments, related_laws,
                  accident_situation, base_fault_explanation, usage_notes, raw_text,
                  parsing_confidence, review_required, accident_party_type, accident_party_label,
                  accident_summary, basic_fault_text, base_fault_a, base_fault_b, adjustment_factors,
                  source_url, source_detail_url, metadata, tsv
                )
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,to_tsvector('simple', %s))
                ON CONFLICT(chart_no, chart_type) DO UPDATE SET
                  document_id=EXCLUDED.document_id,
                  title=EXCLUDED.title,
                  major_party_type=EXCLUDED.major_party_type,
                  scenario_type=EXCLUDED.scenario_type,
                  scenario_subtype=EXCLUDED.scenario_subtype,
                  page_start=EXCLUDED.page_start,
                  page_end=EXCLUDED.page_end,
                  vehicle_roles=EXCLUDED.vehicle_roles,
                  base_fault=EXCLUDED.base_fault,
                  adjustments=EXCLUDED.adjustments,
                  related_laws=EXCLUDED.related_laws,
                  accident_situation=EXCLUDED.accident_situation,
                  base_fault_explanation=EXCLUDED.base_fault_explanation,
                  usage_notes=EXCLUDED.usage_notes,
                  raw_text=EXCLUDED.raw_text,
                  parsing_confidence=EXCLUDED.parsing_confidence,
                  review_required=EXCLUDED.review_required,
                  accident_party_type=EXCLUDED.accident_party_type,
                  accident_party_label=EXCLUDED.accident_party_label,
                  accident_summary=EXCLUDED.accident_summary,
                  basic_fault_text=EXCLUDED.basic_fault_text,
                  base_fault_a=EXCLUDED.base_fault_a,
                  base_fault_b=EXCLUDED.base_fault_b,
                  adjustment_factors=EXCLUDED.adjustment_factors,
                  source_url=EXCLUDED.source_url,
                  source_detail_url=EXCLUDED.source_detail_url,
                  metadata=knia_fault_charts.metadata || EXCLUDED.metadata,
                  tsv=EXCLUDED.tsv,
                  updated_at=now()
                """,
                (
                    document_id,
                    chart_no,
                    str(chart.get("chart_type") or "1"),
                    title,
                    major_party_type,
                    scenario_type,
                    chart.get("scenario_subtype"),
                    _page_value(chart, "page_start"),
                    _page_value(chart, "page_end"),
                    _json(chart.get("vehicle_roles") or {}),
                    _json(chart.get("base_fault") or {}),
                    _json(chart.get("adjustments") or []),
                    _json(chart.get("related_laws") or []),
                    chart.get("accident_situation"),
                    chart.get("base_fault_explanation"),
                    chart.get("usage_notes"),
                    chart.get("raw_text"),
                    chart.get("parsing_confidence"),
                    bool(chart.get("review_required", False)),
                    major_party_type,
                    party_label(major_party_type),
                    chart.get("accident_situation"),
                    chart.get("base_fault_explanation"),
                    base_a,
                    base_b,
                    _json(chart.get("adjustments") or []),
                    source_url,
                    chart.get("source_detail_url") or source_url,
                    _json({
                        "chart_prefix": chart.get("chart_prefix"),
                        "scenario_tags": chart.get("scenario_tags") or [],
                        "subcharts": chart.get("subcharts") or [],
                        "codex_notes": chart.get("codex_notes"),
                        "source": "codex_review_json",
                    }),
                    _chart_search_text(chart),
                ),
            )
            imported += 1
            if chart.get("review_required"):
                review_required += 1
        conn.commit()
    return {"charts_imported": imported, "charts_review_required": review_required, "charts_skipped": skipped}


def get_knia_fault_chart(chart_no: str) -> dict[str, Any] | None:
    if not chart_no:
        return None
    try:
        with psycopg.connect(_db_url()) as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT * FROM knia_fault_charts WHERE chart_no=%s ORDER BY updated_at DESC LIMIT 1", (chart_no,))
            row = cur.fetchone()
            return _normalize_chart_row(dict(row)) if row else None
    except Exception:
        return _local_chart_by_no(chart_no)


def search_knia_fault_charts(
        party_type: str | None,
        scenario_type: str | None,
        query_terms: list[str] | None,
        limit: int = 5,
) -> list[dict[str, Any]]:
    party = canonicalize_party_type(party_type)
    capped = max(1, min(int(limit or 5), 20))
    try:
        where = ["chart_no IS NOT NULL"]
        params: list[Any] = []
        if party != "unknown":
            prefixes = _party_prefix_patterns(party)
            prefix_clause = " OR ".join(["chart_no LIKE %s"] * len(prefixes))
            prefix_sql = f" OR {prefix_clause}" if prefix_clause else ""
            where.append(f"(major_party_type=%s OR accident_party_type=%s{prefix_sql})")
            params.extend([party, party, *prefixes])
        if scenario_type:
            where.append("(scenario_type=%s OR %s='')")
            params.extend([scenario_type, scenario_type])
        with psycopg.connect(_db_url()) as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                f"""
                SELECT *
                FROM knia_fault_charts
                WHERE {' AND '.join(where)}
                ORDER BY
                  CASE WHEN scenario_type=%s THEN 0 ELSE 1 END,
                  review_required ASC NULLS LAST,
                  parsing_confidence DESC NULLS LAST,
                  chart_no ASC
                LIMIT 200
                """,
                [*params, scenario_type or ""],
            )
            rows = [_normalize_chart_row(dict(row)) for row in cur.fetchall()]
    except Exception:
        rows = _local_charts(party, scenario_type)
    ranked = sorted(
        rows,
        key=lambda item: (_score_chart(item, scenario_type, query_terms or []), str(item.get("chart_no") or "")),
        reverse=True,
    )
    if ranked:
        return ranked[:capped]
    local_hits = search_local_charts(
        " ".join(query_terms or []),
        major_party_type=party if party != "unknown" else None,
        scenario_type=scenario_type,
        limit=capped,
    )
    return [_normalize_chart_row(_local_chart_to_row(hit["chart"], hit)) for hit in local_hits[:capped]]


def list_knia_fault_charts_by_party(party_type: str | None, limit: int = 20) -> list[dict[str, Any]]:
    party = canonicalize_party_type(party_type)
    capped = max(1, min(int(limit or 20), 200))
    try:
        prefixes = _party_prefix_patterns(party)
        prefix_clause = " OR ".join(["chart_no LIKE %s"] * len(prefixes))
        prefix_sql = f" OR {prefix_clause}" if prefix_clause else ""
        party_clause = f"(%s='unknown' OR major_party_type=%s OR accident_party_type=%s{prefix_sql})"
        with psycopg.connect(_db_url()) as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                f"""
                SELECT *
                FROM knia_fault_charts
                WHERE {party_clause}
                ORDER BY review_required ASC NULLS LAST, parsing_confidence DESC NULLS LAST, chart_no ASC
                LIMIT %s
                """,
                (party, party, party, *prefixes, capped),
            )
            return [_normalize_chart_row(dict(row)) for row in cur.fetchall()]
    except Exception:
        return _local_charts(party, None)[:capped]


def get_rag_documents_by_chart_no(chart_no: str) -> list[dict[str, Any]]:
    if not chart_no:
        return []
    try:
        with psycopg.connect(_db_url()) as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                """
                SELECT kd.id AS doc_id, kd.title, kd.content AS body, kd.source_url, kd.chart_no,
                       kd.major_party_type, kd.scenario_type, kd.scenario_subtype, kd.chunk_type,
                       kd.page_start, kd.page_end, kd.review_required, kd.metadata
                FROM knia_reference_documents kd
                WHERE kd.chart_no=%s
                ORDER BY kd.chunk_type ASC, kd.id ASC
                """,
                (chart_no,),
            )
            return [dict(row) for row in cur.fetchall()]
    except Exception:
        return [doc for doc in _local_rag_documents() if doc.get("chart_no") == chart_no]


def upsert_myaccident_page(page: dict[str, Any], file_hash: str) -> dict[str, Any]:
    start_url = page.get("start_url") or ""
    my_no = infer_myaccident_no(start_url)
    if not my_no:
        return {"page_id": None, "upsert_nodes": lambda *_: 0}
    title_map = {
        1: "자동차와 보행자의 사고",
        2: "자동차와 자동차의 사고",
        3: "자동차와 자전거의 사고",
        4: "자동차와 이륜차의 사고",
        5: "기타 사고와 차량단독 사고",
    }
    party = infer_accident_party_type(title_map.get(my_no, ""), start_url)
    nodes = parse_visible_items_to_menu_nodes(page)
    with psycopg.connect(_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO knia_myaccident_pages(myaccident_no, page_url, page_title, page_description, accident_party_type, accident_party_label, raw_menu_count, source_file_hash, metadata)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
            ON CONFLICT(myaccident_no) DO UPDATE SET
              page_url=EXCLUDED.page_url, page_title=EXCLUDED.page_title, page_description=EXCLUDED.page_description,
              accident_party_type=EXCLUDED.accident_party_type, accident_party_label=EXCLUDED.accident_party_label,
              raw_menu_count=EXCLUDED.raw_menu_count, source_file_hash=EXCLUDED.source_file_hash, updated_at=now(), metadata=EXCLUDED.metadata
            RETURNING id
            """,
            (my_no, start_url, title_map.get(my_no, f"나의 과실비율 알아보기 {my_no}"), "KNIA JSON에서 가져온 사고유형 메뉴입니다.", party["accident_party_type"], party["accident_party_label"], len(nodes), file_hash, _json({"start_url": start_url})),
        )
        page_id = str(cur.fetchone()[0])
        conn.commit()

    def _upsert_nodes(nodes_arg: list[dict[str, Any]], source_hash: str) -> int:
        return upsert_menu_nodes(page_id, nodes_arg, source_hash)

    return {"page_id": page_id, "upsert_nodes": _upsert_nodes}


def upsert_menu_nodes(page_id: str, nodes: list[dict[str, Any]], file_hash: str) -> int:
    with psycopg.connect(_db_url()) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM knia_menu_nodes WHERE page_id=%s", (page_id,))
        id_map: dict[str, str] = {}
        count = 0
        for node in nodes:
            parent_id = id_map.get(node.get("parent_client_id"))
            cur.execute(
                """
                INSERT INTO knia_menu_nodes(page_id,parent_id,depth,display_order,label,normalized_label,category_path,
                  accident_party_type,accident_party_label,chart_no,chart_type,source_url,source_snapshot_label,source_file_hash,metadata)
                VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                RETURNING id
                """,
                (page_id, parent_id, node.get("depth", 0), node.get("display_order", 0), node["label"], node.get("normalized_label"), _json(node.get("category_path") or []), node.get("accident_party_type", "unknown"), node.get("accident_party_label"), node.get("chart_no"), node.get("chart_type"), node.get("source_url"), node.get("source_snapshot_label"), file_hash, _json(node.get("metadata") or {})),
            )
            node_id = str(cur.fetchone()[0])
            id_map[node.get("client_id")] = node_id
            count += 1
        conn.commit()
        return count


def upsert_reference_document(doc: dict[str, Any], file_hash: str) -> dict[str, Any]:
    normalized = normalize_document(doc)
    if not normalized["content"] or len(normalized["content"]) < 50:
        normalized["content"] = normalized["title"] + "\n" + (doc.get("text") or "")
    with psycopg.connect(_db_url()) as conn, conn.cursor() as cur:
        cur.execute("SELECT content_hash FROM knia_reference_documents WHERE id=%s", (normalized["id"],))
        prev = cur.fetchone()
        changed = not prev or prev[0] != normalized["content_hash"]
        cur.execute(
            """
            INSERT INTO knia_reference_documents(id,source,source_url,title,label,headings,content,content_hash,myaccident_no,
              accident_party_type,accident_party_label,source_file_hash,metadata,chart_no,major_party_type,scenario_type,
              scenario_subtype,chunk_type,page_start,page_end,review_required,tsv)
            VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s,%s,to_tsvector('simple', %s))
            ON CONFLICT(id) DO UPDATE SET
              source=EXCLUDED.source, source_url=EXCLUDED.source_url, title=EXCLUDED.title, label=EXCLUDED.label,
              headings=EXCLUDED.headings, content=EXCLUDED.content, content_hash=EXCLUDED.content_hash,
              myaccident_no=EXCLUDED.myaccident_no, accident_party_type=EXCLUDED.accident_party_type,
              accident_party_label=EXCLUDED.accident_party_label, source_file_hash=EXCLUDED.source_file_hash,
              metadata=EXCLUDED.metadata, chart_no=EXCLUDED.chart_no, major_party_type=EXCLUDED.major_party_type,
              scenario_type=EXCLUDED.scenario_type, scenario_subtype=EXCLUDED.scenario_subtype,
              chunk_type=EXCLUDED.chunk_type, page_start=EXCLUDED.page_start, page_end=EXCLUDED.page_end,
              review_required=EXCLUDED.review_required, tsv=EXCLUDED.tsv, updated_at=now()
            """,
            (
                normalized["id"], normalized["source"], normalized["source_url"], normalized["title"], normalized["label"],
                _json(normalized["headings"]), normalized["content"], normalized["content_hash"], normalized["myaccident_no"],
                normalized["accident_party_type"], normalized["accident_party_label"], file_hash, _json(normalized["metadata"]),
                normalized.get("chart_no"), normalized.get("major_party_type"), normalized.get("scenario_type"),
                normalized.get("scenario_subtype"), normalized.get("chunk_type"), normalized.get("page_start"),
                normalized.get("page_end"), normalized.get("review_required", False), normalized["content"],
            ),
        )
        conn.commit()
        return {"document_id": normalized["id"], "changed": changed}


def replace_reference_chunks(document_id: str, chunks: list[dict[str, Any]]) -> int:
    with psycopg.connect(_db_url()) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM knia_reference_chunks WHERE document_id=%s", (document_id,))
        for chunk in chunks:
            cur.execute(
                """
                INSERT INTO knia_reference_chunks(document_id,chunk_index,chunk_type,chunk_text,plain_summary,source_url,myaccident_no,
                  accident_party_type,accident_party_label,scenario_tags,keywords,display_tags,content_hash,evidence_quality_score,
                  chart_no,major_party_type,scenario_type,review_required,metadata,tsv)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,to_tsvector('simple', %s))
                """,
                (
                    document_id, chunk.get("chunk_index", 0), chunk.get("chunk_type", "rag"), chunk["chunk_text"],
                    chunk.get("plain_summary"), chunk.get("source_url"), chunk.get("myaccident_no"),
                    chunk.get("accident_party_type", "unknown"), chunk.get("accident_party_label"),
                    chunk.get("scenario_tags") or [], chunk.get("keywords") or [], chunk.get("display_tags") or [],
                    chunk.get("content_hash"), chunk.get("evidence_quality_score", 0.5), chunk.get("chart_no"),
                    chunk.get("major_party_type"), chunk.get("scenario_type"), chunk.get("review_required", False),
                    _json(chunk.get("metadata") or {}), chunk["chunk_text"],
                ),
            )
        conn.commit()
        return len(chunks)


def upsert_media_assets(assets: list[dict[str, Any]], file_hash: str) -> int:
    count = 0
    with psycopg.connect(_db_url()) as conn, conn.cursor() as cur:
        for asset in assets:
            source_url = asset.get("source_url")
            if not source_url:
                continue
            cur.execute(
                """
                INSERT INTO knia_json_media_assets(document_id,asset_type,source_url,embed_url,title,alt,storage_provider,storage_key,mime_type,
                  accident_party_type,attribution,license_status,source_file_hash,metadata)
                VALUES (%s,%s,%s,%s,%s,%s,'external_url',NULL,%s,%s,%s,'source_link_only',%s,%s::jsonb)
                ON CONFLICT(source_url) DO UPDATE SET
                  document_id=COALESCE(EXCLUDED.document_id, knia_json_media_assets.document_id), asset_type=EXCLUDED.asset_type,
                  embed_url=EXCLUDED.embed_url, title=EXCLUDED.title, alt=EXCLUDED.alt, mime_type=EXCLUDED.mime_type,
                  accident_party_type=EXCLUDED.accident_party_type, source_file_hash=EXCLUDED.source_file_hash,
                  metadata=knia_json_media_assets.metadata || EXCLUDED.metadata
                """,
                (asset.get("document_id"), asset.get("asset_type", "link"), source_url, asset.get("embed_url"), asset.get("title"), asset.get("alt"), asset.get("mime_type"), asset.get("accident_party_type", "unknown"), asset.get("attribution") or "출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털", file_hash, _json(asset.get("metadata") or {})),
            )
            count += 1
        conn.commit()
        return count


def get_import_stats() -> dict[str, Any]:
    with psycopg.connect(_db_url()) as conn, conn.cursor() as cur:
        def one(sql: str):
            cur.execute(sql)
            return cur.fetchone()[0]
        return {
            "runs": one("SELECT count(*) FROM knia_json_import_runs"),
            "successful_runs": one("SELECT count(*) FROM knia_json_import_runs WHERE status='success'"),
            "pages": one("SELECT count(*) FROM knia_myaccident_pages"),
            "menu_nodes": one("SELECT count(*) FROM knia_menu_nodes"),
            "documents": one("SELECT count(*) FROM knia_reference_documents"),
            "chunks": one("SELECT count(*) FROM knia_reference_chunks"),
            "embedded_chunks": one("SELECT count(*) FROM knia_reference_chunks WHERE embedding IS NOT NULL"),
            "media_assets": one("SELECT count(*) FROM knia_json_media_assets"),
        }


def _normalize_chart_row(row: dict[str, Any]) -> dict[str, Any]:
    if not row:
        return row
    major = canonicalize_party_type(row.get("major_party_type") or row.get("accident_party_type"))
    base_fault = row.get("base_fault") or {}
    adjustments = row.get("adjustments") or row.get("adjustment_factors") or []
    base_a = row.get("base_fault_a")
    base_b = row.get("base_fault_b")
    if base_a is None or base_b is None:
        base_a, base_b = _base_fault_pair(base_fault)
    source_url = str(row.get("source_url") or "").strip()
    source_is_fallback = bool(row.get("source_url_is_fallback"))
    if not source_url or source_url.rstrip("/") == BASE_URL:
        source_url, source_is_fallback = build_knia_source_url(row)
    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    menu_path = row.get("menu_path") or metadata.get("menu_path")
    if not menu_path:
        menu_path = build_menu_path_for_chart(row)
    return {
        **row,
        "major_party_type": major,
        "accident_party_type": major,
        "accident_party_label": row.get("accident_party_label") or party_label(major),
        "base_fault": base_fault,
        "adjustments": adjustments,
        "base_fault_a": base_a,
        "base_fault_b": base_b,
        "review_required": bool(row.get("review_required", False)),
        "source_url": source_url,
        "source_detail_url": row.get("source_detail_url") or source_url,
        "source_url_is_fallback": source_is_fallback,
        "menu_path": menu_path,
        "source_type": row.get("source_type") or "knia_structured_chart",
        "source_family": "knia",
    }


def normalize_text(value: Any) -> str:
    return " ".join(re.sub(r"[^0-9A-Za-z가-힣\-\s]", " ", str(value or "")).split()).lower()


def _party_prefix_patterns(party: str | None) -> list[str]:
    return {
        "car_vs_car": ["차%"],
        "car_vs_person": ["보%"],
        "car_vs_bicycle": ["자%", "거%"],
        "car_vs_object": ["기%"],
        "single_vehicle": ["단%"],
    }.get(canonicalize_party_type(party), [])


def tokenize(value: Any) -> list[str]:
    text = normalize_text(value)
    return [token for token in text.split() if token]


def chart_search_text(chart: dict[str, Any]) -> str:
    values: list[Any] = [
        chart.get("chart_no"),
        chart.get("title"),
        chart.get("major_party_type"),
        chart.get("scenario_type"),
        chart.get("scenario_subtype"),
        chart.get("accident_situation"),
        chart.get("base_fault_explanation"),
        chart.get("usage_notes"),
        chart.get("raw_text"),
        chart.get("scenario_tags"),
        chart.get("vehicle_roles"),
    ]
    for subchart in chart.get("subcharts_summary") or []:
        if isinstance(subchart, dict):
            values.extend([subchart.get("subchart_no"), subchart.get("title"), subchart.get("source_text"), subchart.get("type")])
    return normalize_text(" ".join(json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v or "") for v in values))


def subchart_search_text(subchart: dict[str, Any]) -> str:
    return normalize_text(
        " ".join(
            str(subchart.get(key) or "")
            for key in ("subchart_no", "title", "source_text", "type", "label", "description")
        )
    )


def rag_docs_for_chart(chart_no: str, major_party_type: str | None = None) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    party = canonicalize_party_type(major_party_type)
    for doc in _local_rag_documents():
        if str(doc.get("chart_no") or "") != str(chart_no or ""):
            continue
        doc_party = canonicalize_party_type(doc.get("major_party_type") or doc.get("accident_party_type"))
        if party != "unknown" and doc_party != party:
            continue
        docs.append(doc)
    return docs


def search_local_charts(
    query: str,
    *,
    major_party_type: str | None = None,
    scenario_type: str | None = None,
    scenario_subtype: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    data = _load_local_json() or {}
    party = canonicalize_party_type(major_party_type)
    query_text = normalize_text(query)
    query_tokens = set(tokenize(query_text))
    results: list[dict[str, Any]] = []
    for chart in data.get("charts") or []:
        if not isinstance(chart, dict):
            continue
        chart_party = canonicalize_party_type(chart.get("major_party_type") or _party_from_chart_no_local(chart.get("chart_no")))
        if party != "unknown" and chart_party != party:
            continue
        text = chart_search_text(chart)
        score = 0.0
        if scenario_type and chart.get("scenario_type") == scenario_type:
            score += 3.0
        elif scenario_type and _scenario_family_compatible(scenario_type, chart.get("scenario_type"), chart.get("scenario_subtype")):
            score += 1.6
        if scenario_subtype and chart.get("scenario_subtype") == scenario_subtype:
            score += 1.2
        for token in query_tokens:
            if token and token in text:
                score += 0.25
        score += _local_special_boost(chart, query_text, chart_party)
        best_subchart = _best_local_subchart(chart, query_text)
        if best_subchart:
            score += float(best_subchart.get("_score") or 0.0)
        if score <= 0 and party != "unknown":
            score = 0.05
        if score <= 0:
            continue
        source_url, is_fallback = build_knia_source_url(chart, best_subchart)
        menu_path = build_menu_path_for_chart(chart, best_subchart)
        chart_copy = {
            **chart,
            "major_party_type": chart_party,
            "source_url": source_url,
            "source_detail_url": chart.get("source_detail_url") or source_url,
            "source_url_is_fallback": is_fallback,
            "menu_path": menu_path,
        }
        results.append(
            {
                "chart": chart_copy,
                "subchart": best_subchart,
                "score": round(score, 4),
                "rag_documents": rag_docs_for_chart(str(chart.get("chart_no") or ""), chart_party),
                "menu_path": menu_path,
                "source_url": source_url,
                "source_url_is_fallback": is_fallback,
            }
        )
    return sorted(results, key=lambda item: (float(item.get("score") or 0.0), str((item.get("chart") or {}).get("chart_no") or "")), reverse=True)[: max(1, int(limit or 5))]


def search_local_subcharts(
    query: str,
    *,
    major_party_type: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for result in search_local_charts(query, major_party_type=major_party_type, limit=50):
        chart = result.get("chart") or {}
        for subchart in chart.get("subcharts_summary") or []:
            if not isinstance(subchart, dict):
                continue
            score = _score_subchart(subchart, normalize_text(query))
            if score <= 0:
                continue
            source_url, is_fallback = build_knia_source_url(chart, subchart)
            hits.append({**result, "subchart": subchart, "score": round(float(result.get("score") or 0) + score, 4), "source_url": source_url, "source_url_is_fallback": is_fallback})
    return sorted(hits, key=lambda item: float(item.get("score") or 0.0), reverse=True)[: max(1, int(limit or 5))]


def build_knia_source_url(chart: dict[str, Any], subchart: dict[str, Any] | None = None) -> tuple[str, bool]:
    for item in (subchart, chart):
        if isinstance(item, dict):
            for key in ("source_detail_url", "source_url", "href"):
                url = str(item.get(key) or "").strip()
                if url:
                    return url, False
    chart_no = str((subchart or {}).get("subchart_no") or chart.get("chart_no") or "").strip()
    encoded = quote(chart_no, safe="")
    return f"{BASE_URL}/myaccident-content?chartNo={encoded}&chartType=1", True


def build_menu_path_for_chart(chart: dict[str, Any], subchart: dict[str, Any] | None = None) -> list[str]:
    existing = chart.get("menu_path") or chart.get("category_path")
    if isinstance(existing, list) and existing:
        path = [str(item) for item in existing if item]
    else:
        major = {
            "car_vs_person": "자동차와 보행자의 사고",
            "car_vs_car": "자동차와 자동차의 사고",
            "car_vs_bicycle": "자동차와 자전거의 사고",
            "car_vs_motorcycle": "자동차와 이륜차의 사고",
            "car_vs_object": "자동차와 기물의 사고",
            "single_vehicle": "차량 단독 사고",
        }.get(canonicalize_party_type(chart.get("major_party_type")), "KNIA 과실비율 인정기준")
        path = [major]
        chart_no = str(chart.get("chart_no") or "")
        subtype = str(chart.get("scenario_subtype") or "")
        title = str(chart.get("title") or "")
        if chart_no.startswith("보25"):
            path.extend(["횡단보도 없음 또는 기타 사고유형", "보도와 차도 구분 있음", "보행자의 차도보행중 사고(보도 공사중)"])
        elif chart_no.startswith(("보27", "보28")):
            path.extend(["횡단보도 없음 또는 기타 사고유형", "보도와 차도 구분 없음", title])
        elif chart_no.startswith("보30"):
            path.extend(["기타 사고유형", "보행자 위험행위 사고"])
        elif chart_no.startswith(("보22", "보23")):
            path.extend(["도로 유형별 횡단 중 사고", title])
        elif chart_no.startswith("차7"):
            path.extend(["교차로(+자로, T자로 등) 사고", "한쪽 지시표지 있는 교차로", "직진 대 직진"])
        elif chart_no.startswith("차43"):
            path.extend(["같은 방향 진행차량 상호 간의 사고", "진로변경 사고"])
        elif chart_no.startswith("차41"):
            path.extend(["같은 방향 진행차량 상호 간의 사고", "안전거리미확보로 인한 추돌사고"])
        elif chart_no.startswith("차42"):
            path.extend(["같은 방향 진행차량 상호 간의 사고", "주정차 차량 추돌사고"])
        elif subtype:
            path.append(subtype)
        elif title:
            path.append(title)
    subchart_no = str((subchart or {}).get("subchart_no") or "")
    if subchart_no and subchart_no not in path[-1:]:
        path.append(f"{subchart_no} {str((subchart or {}).get('title') or '').strip()}".strip())
    return path


def _scenario_family_compatible(requested: str | None, chart_scenario: Any, chart_subtype: Any) -> bool:
    requested_text = str(requested or "")
    chart_text = " ".join([str(chart_scenario or ""), str(chart_subtype or "")])
    if requested_text in {"pedestrian_roadway_worker_accident", "pedestrian_road_work_worker_accident", "pedestrian_accident"}:
        return "pedestrian" in chart_text
    if requested_text == "intersection_collision":
        return "intersection" in chart_text
    if requested_text == "stealth_illegal_parked_vehicle_collision":
        return "parking" in chart_text or "stopped" in chart_text
    return requested_text and requested_text.split("_")[0] in chart_text


def _local_special_boost(chart: dict[str, Any], query_text: str, party: str) -> float:
    chart_no = str(chart.get("chart_no") or "")
    boost = 0.0
    if party == "car_vs_person" and any(token in query_text for token in ("공사", "작업자", "도로 폭", "차도", "튀어나", "뛰어나", "차량을 보지 않고")):
        if chart_no == "보25":
            boost += 4.0
        elif chart_no == "보27":
            boost += 3.5
        elif chart_no == "보28":
            boost += 3.0
        elif chart_no == "보30":
            boost += 2.5
        elif chart_no == "보34":
            boost += 1.5
        elif chart_no in {"보22", "보23"}:
            boost += 1.2
    if any(token in query_text for token in ("한쪽 지시표지", "지시표지", "직진 대 직진", "측면 진입", "차7", "차7-1")) and chart_no == "차7":
        boost += 5.0
    if any(token in query_text for token in ("차선변경", "차로변경", "진로변경", "끼어들기")) and chart_no == "차43":
        boost += 5.0
    if any(token in query_text for token in ("앞차를 들이받", "앞차 추돌", "안전거리", "후미추돌")) and chart_no == "차41":
        boost += 5.0
    if any(token in query_text for token in ("주차차량", "정차차량", "스텔스", "무등화", "주정차")) and chart_no == "차42":
        boost += 5.0
    return boost


def _best_local_subchart(chart: dict[str, Any], query_text: str) -> dict[str, Any] | None:
    scored: list[tuple[float, dict[str, Any]]] = []
    for subchart in chart.get("subcharts_summary") or []:
        if isinstance(subchart, dict):
            score = _score_subchart(subchart, query_text)
            if score > 0:
                scored.append((score, {**subchart, "_score": score}))
    if not scored:
        return None
    return sorted(scored, key=lambda item: item[0], reverse=True)[0][1]


def _score_subchart(subchart: dict[str, Any], query_text: str) -> float:
    sub_no = str(subchart.get("subchart_no") or "")
    text = subchart_search_text(subchart)
    score = 0.0
    if sub_no and sub_no.lower() in query_text:
        score += 3.0
    if sub_no == "차7-1" and any(token in query_text for token in ("한쪽 지시표지", "지시표지", "녹색", "적색", "직진")):
        score += 6.0
    for token in tokenize(query_text):
        if token in text:
            score += 0.15
    return score


def _party_from_chart_no_local(chart_no: Any) -> str:
    value = str(chart_no or "")
    if value.startswith("보"):
        return "car_vs_person"
    if value.startswith("차"):
        return "car_vs_car"
    if value.startswith(("거", "자")):
        return "car_vs_bicycle"
    if value.startswith("기"):
        return "car_vs_object"
    if value.startswith("단"):
        return "single_vehicle"
    return "unknown"


def _load_local_json() -> dict[str, Any] | None:
    for candidate in LOCAL_JSON_CANDIDATES:
        path = Path(candidate)
        if path.exists() and path.is_file():
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data.get("charts"), list) and data.get("charts"):
                return data
    return None


def _local_charts(party_type: str | None, scenario_type: str | None) -> list[dict[str, Any]]:
    data = _load_local_json() or {}
    party = canonicalize_party_type(party_type)
    rows: list[dict[str, Any]] = []
    for chart in data.get("charts") or []:
        major = canonicalize_party_type(chart.get("major_party_type"))
        if party != "unknown" and major != party:
            continue
        if scenario_type and chart.get("scenario_type") != scenario_type:
            continue
        rows.append(_normalize_chart_row(_local_chart_to_row(chart)))
    return rows


def _local_chart_by_no(chart_no: str) -> dict[str, Any] | None:
    data = _load_local_json() or {}
    for chart in data.get("charts") or []:
        if chart.get("chart_no") == chart_no:
            return _normalize_chart_row(_local_chart_to_row(chart))
    return None


def _local_rag_documents() -> list[dict[str, Any]]:
    data = _load_local_json() or {}
    return list(data.get("rag_documents") or [])


def _local_chart_to_row(chart: dict[str, Any], search_result: dict[str, Any] | None = None) -> dict[str, Any]:
    base_a, base_b = _base_fault_pair(chart.get("base_fault"))
    major = canonicalize_party_type(chart.get("major_party_type"))
    source_url, source_url_is_fallback = (
        (search_result or {}).get("source_url"),
        bool((search_result or {}).get("source_url_is_fallback")),
    )
    if not source_url:
        source_url, source_url_is_fallback = build_knia_source_url(chart)
    menu_path = (search_result or {}).get("menu_path") or build_menu_path_for_chart(chart)
    selected_subchart = (search_result or {}).get("subchart") or {}
    return {
        "id": f"local-json:{chart.get('chart_no')}",
        "document_id": "local-codex-review-json",
        "chart_no": chart.get("chart_no"),
        "subchart_no": selected_subchart.get("subchart_no"),
        "chart_type": chart.get("chart_type") or "1",
        "title": chart.get("title"),
        "major_party_type": major,
        "scenario_type": chart.get("scenario_type"),
        "scenario_subtype": chart.get("scenario_subtype"),
        "page_start": _page_value(chart, "page_start"),
        "page_end": _page_value(chart, "page_end"),
        "vehicle_roles": chart.get("vehicle_roles") or {},
        "base_fault": chart.get("base_fault") or {},
        "adjustments": chart.get("adjustments") or [],
        "related_laws": chart.get("related_laws") or [],
        "accident_situation": chart.get("accident_situation"),
        "base_fault_explanation": chart.get("base_fault_explanation"),
        "usage_notes": chart.get("usage_notes"),
        "raw_text": chart.get("raw_text"),
        "parsing_confidence": chart.get("parsing_confidence"),
        "review_required": bool(chart.get("review_required", False)),
        "accident_party_type": major,
        "accident_party_label": party_label(major),
        "accident_summary": chart.get("accident_situation"),
        "basic_fault_text": chart.get("base_fault_explanation"),
        "base_fault_a": base_a,
        "base_fault_b": base_b,
        "adjustment_factors": chart.get("adjustments") or [],
        "source_url": source_url,
        "source_detail_url": chart.get("source_detail_url") or source_url,
        "source_url_is_fallback": source_url_is_fallback,
        "menu_path": menu_path,
        "rag_documents": (search_result or {}).get("rag_documents") or [],
        "metadata": {
            "scenario_tags": chart.get("scenario_tags") or [],
            "chart_prefix": chart.get("chart_prefix"),
            "source": "local_codex_review_json",
            "menu_path": menu_path,
            "source_url_is_fallback": source_url_is_fallback,
            "subchart": selected_subchart,
        },
    }
