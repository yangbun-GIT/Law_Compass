from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import psycopg
import psycopg.rows
from psycopg.types.json import Jsonb

from app.services.knia.party_guard import canonicalize_party_type
from app.services.knia.knia_json_parser import infer_accident_party_type, infer_myaccident_no, normalize_document, parse_visible_items_to_menu_nodes
from app.services.knia.taxonomy import party_label


BASE_URL = "https://accident.knia.or.kr"
LOCAL_JSON_CANDIDATES = (
    "scripts/knia_fault_ratio/knia_fault_ratio_2023_06.codex_review.json",
    "../../scripts/knia_fault_ratio/knia_fault_ratio_2023_06.codex_review.json",
    "/app/scripts/knia_fault_ratio/knia_fault_ratio_2023_06.codex_review.json",
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
            where.append("(major_party_type=%s OR accident_party_type=%s)")
            params.extend([party, party])
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
    return ranked[:capped]


def list_knia_fault_charts_by_party(party_type: str | None, limit: int = 20) -> list[dict[str, Any]]:
    party = canonicalize_party_type(party_type)
    capped = max(1, min(int(limit or 20), 200))
    try:
        with psycopg.connect(_db_url()) as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                """
                SELECT *
                FROM knia_fault_charts
                WHERE (%s='unknown' OR major_party_type=%s OR accident_party_type=%s)
                ORDER BY review_required ASC NULLS LAST, parsing_confidence DESC NULLS LAST, chart_no ASC
                LIMIT %s
                """,
                (party, party, party, capped),
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
        "source_type": row.get("source_type") or "knia_structured_chart",
        "source_family": "knia",
    }


def _load_local_json() -> dict[str, Any] | None:
    for candidate in LOCAL_JSON_CANDIDATES:
        path = Path(candidate)
        if path.exists() and path.is_file():
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
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


def _local_chart_to_row(chart: dict[str, Any]) -> dict[str, Any]:
    base_a, base_b = _base_fault_pair(chart.get("base_fault"))
    major = canonicalize_party_type(chart.get("major_party_type"))
    return {
        "id": f"local-json:{chart.get('chart_no')}",
        "document_id": "local-codex-review-json",
        "chart_no": chart.get("chart_no"),
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
        "source_url": chart.get("source_url") or BASE_URL,
        "source_detail_url": chart.get("source_detail_url") or BASE_URL,
        "metadata": {
            "scenario_tags": chart.get("scenario_tags") or [],
            "chart_prefix": chart.get("chart_prefix"),
            "source": "local_codex_review_json",
        },
    }
