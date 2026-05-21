#!/usr/bin/env python
import json
import os
import re

import psycopg

from app.providers.embedding import get_embedding_provider, vector_literal

DB_URL = os.getenv("DATABASE_URL", "postgresql://law:lawpass@localhost:5432/lawcompass")

DOCS = [
    {
        "source_name": "Road Traffic Act",
        "source_type": "law",
        "title": "Road Traffic Act accident notes",
        "doc_type": "statute",
        "text": "Traffic accident obligations, reporting duty, and safe driving duty summary for KR context.",
        "uri": "https://www.law.go.kr",
    },
    {
        "source_name": "Fault Ratio Guide",
        "source_type": "guideline",
        "title": "Rear-end and lane-change ratio examples",
        "doc_type": "guideline",
        "text": "Typical patterns for rear-end, lane-change, and intersection accident fault estimation.",
        "uri": "https://www.kidi.or.kr",
    },
]


def chunk_text(text: str, size: int = 180):
    words = re.split(r"\s+", text.strip())
    chunks = []
    buf = []
    n = 0
    for w in words:
        buf.append(w)
        n += len(w) + 1
        if n >= size:
            chunks.append(" ".join(buf))
            buf = []
            n = 0
    if buf:
        chunks.append(" ".join(buf))
    return chunks or [text]


def run():
    embedder = get_embedding_provider()
    inserted_docs = 0
    inserted_chunks = 0
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            for d in DOCS:
                cur.execute(
                    "INSERT INTO kb_sources(name, source_type, source_uri) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING RETURNING id",
                    (d["source_name"], d["source_type"], d["uri"]),
                )
                row = cur.fetchone()
                if row:
                    source_id = row[0]
                else:
                    cur.execute("SELECT id FROM kb_sources WHERE name=%s ORDER BY created_at DESC LIMIT 1", (d["source_name"],))
                    source_id = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO kb_documents(source_id, title, doc_type, raw_text, metadata, tsv)
                    VALUES(%s,%s,%s,%s,%s,to_tsvector('simple', %s))
                    RETURNING id
                    """,
                    (source_id, d["title"], d["doc_type"], d["text"], json.dumps({"lang": "ko"}), d["text"]),
                )
                document_id = cur.fetchone()[0]
                inserted_docs += 1

                for idx, c in enumerate(chunk_text(d["text"])):
                    cur.execute(
                        """
                        INSERT INTO kb_chunks(document_id, chunk_index, chunk_text, chunk_summary, metadata, tsv)
                        VALUES(%s,%s,%s,%s,%s,to_tsvector('simple', %s))
                        RETURNING id
                        """,
                        (document_id, idx, c, c[:120], json.dumps({"lang": "ko"}), c),
                    )
                    chunk_id = cur.fetchone()[0]
                    cur.execute("INSERT INTO kb_embeddings(chunk_id, embedding) VALUES(%s, %s::vector)", (chunk_id, vector_literal(embedder.embed(c))))
                    inserted_chunks += 1

            conn.commit()
    print(f"inserted_docs={inserted_docs} inserted_chunks={inserted_chunks}")


if __name__ == "__main__":
    run()
