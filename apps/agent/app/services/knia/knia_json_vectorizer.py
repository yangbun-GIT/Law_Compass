from __future__ import annotations

import os
from typing import Any

import psycopg

from app.providers.embedding import get_embedding_provider, vector_literal


def _db_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL missing")
    return url


def rebuild_knia_json_embeddings(limit: int | None = None, force: bool = False) -> dict[str, Any]:
    provider = get_embedding_provider()
    sql = "SELECT id, chunk_text FROM knia_reference_chunks"
    params: list[Any] = []
    if not force:
        sql += " WHERE embedding IS NULL"
    sql += " ORDER BY created_at ASC"
    if limit:
        sql += " LIMIT %s"
        params.append(limit)
    processed = 0
    with psycopg.connect(_db_url()) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        for chunk_id, text in rows:
            vec = vector_literal(provider.embed(text[:4000]))
            cur.execute("UPDATE knia_reference_chunks SET embedding=%s::vector WHERE id=%s", (vec, chunk_id))
            processed += 1
            if processed % 50 == 0:
                conn.commit()
        conn.commit()
    return {"processed": processed, "force": force, "embedding_provider": provider.__class__.__name__}
