from __future__ import annotations

import os
from typing import Any

import psycopg


def _db_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL missing")
    return url


def get_myaccident_pages() -> list[dict[str, Any]]:
    with psycopg.connect(_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT myaccident_no, page_url, page_title, page_description, accident_party_type, accident_party_label, raw_menu_count
            FROM knia_myaccident_pages
            ORDER BY myaccident_no ASC
            """
        )
        return [
            {
                "myaccident_no": r[0], "page_url": r[1], "page_title": r[2], "page_description": r[3],
                "accident_party_type": r[4], "accident_party_label": r[5], "raw_menu_count": r[6],
            }
            for r in cur.fetchall()
        ]


def get_myaccident_tree(myaccident_no: int) -> dict[str, Any]:
    with psycopg.connect(_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id,myaccident_no,page_url,page_title,page_description,accident_party_type,accident_party_label FROM knia_myaccident_pages WHERE myaccident_no=%s",
            (myaccident_no,),
        )
        page_row = cur.fetchone()
        if not page_row:
            return {"page": None, "tree": []}
        page_id = str(page_row[0])
        cur.execute(
            """
            SELECT id,parent_id,depth,display_order,label,category_path,accident_party_type,accident_party_label,chart_no,chart_type,source_url
            FROM knia_menu_nodes WHERE page_id=%s ORDER BY display_order ASC
            """,
            (page_id,),
        )
        nodes = []
        by_id = {}
        for r in cur.fetchall():
            node = {
                "id": str(r[0]), "parent_id": str(r[1]) if r[1] else None, "depth": r[2], "display_order": r[3],
                "label": r[4], "category_path": r[5] or [], "accident_party_type": r[6], "accident_party_label": r[7],
                "chart_no": r[8], "chart_type": r[9], "source_url": r[10], "children": [],
            }
            nodes.append(node); by_id[node["id"]] = node
        tree = []
        for node in nodes:
            parent = by_id.get(node["parent_id"])
            if parent:
                parent["children"].append(node)
            else:
                tree.append(node)
        page = {
            "id": page_id, "myaccident_no": page_row[1], "page_url": page_row[2], "page_title": page_row[3],
            "page_description": page_row[4], "accident_party_type": page_row[5], "accident_party_label": page_row[6],
        }
        return {"page": page, "tree": tree}


def search_menu_nodes(q: str, accident_party_type: str | None = None, limit: int = 30) -> list[dict[str, Any]]:
    params: list[Any] = [f"%{q}%"]
    where = "label ILIKE %s"
    if accident_party_type and accident_party_type != "all":
        params.append(accident_party_type)
        where += f" AND accident_party_type=%s"
    params.append(limit)
    with psycopg.connect(_db_url()) as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT label, category_path, accident_party_type, accident_party_label, chart_no, chart_type, source_url
            FROM knia_menu_nodes WHERE {where} ORDER BY display_order ASC LIMIT %s
            """,
            params,
        )
        return [
            {"label": r[0], "category_path": r[1] or [], "accident_party_type": r[2], "accident_party_label": r[3], "chart_no": r[4], "chart_type": r[5], "source_url": r[6]}
            for r in cur.fetchall()
        ]
