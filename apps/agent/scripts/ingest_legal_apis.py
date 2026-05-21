#!/usr/bin/env python
import json
import os

import psycopg

from app.services.legal_api_clients import fetch_law_search, fetch_data_go_traffic

DB_URL = os.getenv("DATABASE_URL", "postgresql://law:lawpass@localhost:5432/lawcompass")

QUERIES = [
    "도로교통법",
    "교통사고처리 특례법",
    "과실비율 인정기준",
    "교차로 신호위반",
    "후미추돌",
]


def upsert_source(cur, name: str, source_type: str, uri: str):
    cur.execute(
        """
        INSERT INTO kb_sources(name, source_type, source_uri)
        VALUES(%s,%s,%s)
        ON CONFLICT DO NOTHING
        RETURNING id
        """,
        (name, source_type, uri),
    )
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("SELECT id FROM kb_sources WHERE name=%s ORDER BY created_at DESC LIMIT 1", (name,))
    return cur.fetchone()[0]


def run():
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            law_source_id = upsert_source(cur, "국가법령정보센터 OPEN API", "law_api", "https://open.law.go.kr")
            data_source_id = upsert_source(cur, "공공데이터포털 교통 API", "traffic_api", "https://data.go.kr")

            inserted = 0
            for q in QUERIES:
                for row in fetch_law_search(q, limit=8):
                    title = f"{q} - {row['title']}"
                    body = row.get("snippet", "")
                    cur.execute(
                        """
                        INSERT INTO kb_documents(source_id, title, doc_type, raw_text, metadata, tsv)
                        VALUES(%s,%s,'law_api',%s,%s,to_tsvector('simple', %s))
                        RETURNING id
                        """,
                        (law_source_id, title, body, json.dumps({"query": q, "chunk_id": row["chunk_id"]}), body),
                    )
                    doc_id = cur.fetchone()[0]
                    cur.execute(
                        """
                        INSERT INTO kb_chunks(document_id, chunk_index, chunk_text, chunk_summary, metadata, tsv)
                        VALUES(%s,0,%s,%s,%s,to_tsvector('simple', %s))
                        """,
                        (doc_id, body, body[:120], json.dumps({"source": row.get("source")}), body),
                    )
                    inserted += 1

                for row in fetch_data_go_traffic(q, limit=5):
                    title = f"{q} - {row['title']}"
                    body = row.get("snippet", "")
                    cur.execute(
                        """
                        INSERT INTO kb_documents(source_id, title, doc_type, raw_text, metadata, tsv)
                        VALUES(%s,%s,'traffic_api',%s,%s,to_tsvector('simple', %s))
                        RETURNING id
                        """,
                        (data_source_id, title, body, json.dumps({"query": q, "chunk_id": row["chunk_id"]}), body),
                    )
                    doc_id = cur.fetchone()[0]
                    cur.execute(
                        """
                        INSERT INTO kb_chunks(document_id, chunk_index, chunk_text, chunk_summary, metadata, tsv)
                        VALUES(%s,0,%s,%s,%s,to_tsvector('simple', %s))
                        """,
                        (doc_id, body, body[:120], json.dumps({"source": row.get("source")}), body),
                    )
                    inserted += 1

            conn.commit()
            print(f"inserted_docs={inserted}")


if __name__ == "__main__":
    run()
