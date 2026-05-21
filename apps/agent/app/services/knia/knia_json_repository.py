from __future__ import annotations

import json
import os
from typing import Any

import psycopg

from app.services.knia.knia_json_parser import infer_accident_party_type, infer_myaccident_no, normalize_document, parse_visible_items_to_menu_nodes


def _db_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL missing")
    return url


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


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
              accident_party_type,accident_party_label,source_file_hash,metadata,tsv)
            VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s::jsonb,to_tsvector('simple', %s))
            ON CONFLICT(id) DO UPDATE SET
              source=EXCLUDED.source, source_url=EXCLUDED.source_url, title=EXCLUDED.title, label=EXCLUDED.label,
              headings=EXCLUDED.headings, content=EXCLUDED.content, content_hash=EXCLUDED.content_hash,
              myaccident_no=EXCLUDED.myaccident_no, accident_party_type=EXCLUDED.accident_party_type,
              accident_party_label=EXCLUDED.accident_party_label, source_file_hash=EXCLUDED.source_file_hash,
              metadata=EXCLUDED.metadata, tsv=EXCLUDED.tsv, updated_at=now()
            """,
            (normalized["id"], normalized["source"], normalized["source_url"], normalized["title"], normalized["label"], _json(normalized["headings"]), normalized["content"], normalized["content_hash"], normalized["myaccident_no"], normalized["accident_party_type"], normalized["accident_party_label"], file_hash, _json(normalized["metadata"]), normalized["content"]),
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
                  accident_party_type,accident_party_label,scenario_tags,keywords,display_tags,content_hash,evidence_quality_score,tsv)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,to_tsvector('simple', %s))
                """,
                (document_id, chunk.get("chunk_index", 0), chunk.get("chunk_type", "rag"), chunk["chunk_text"], chunk.get("plain_summary"), chunk.get("source_url"), chunk.get("myaccident_no"), chunk.get("accident_party_type", "unknown"), chunk.get("accident_party_label"), chunk.get("scenario_tags") or [], chunk.get("keywords") or [], chunk.get("display_tags") or [], chunk.get("content_hash"), chunk.get("evidence_quality_score", 0.5), chunk["chunk_text"]),
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
