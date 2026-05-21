from __future__ import annotations

import os

import psycopg

from app.providers.embedding import get_embedding_provider, vector_literal

DB_URL = os.getenv("DATABASE_URL", "postgresql://law:lawpass@postgres:5432/lawcompass")


def rebuild_knia_embeddings(limit: int = 1000) -> dict[str, int | str]:
    provider = get_embedding_provider()
    model = os.getenv("OPENAI_EMBEDDING_MODEL", "deterministic-1024") if os.getenv("OPENAI_API_KEY") else "deterministic-1024"
    processed = 0
    with psycopg.connect(DB_URL) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, chunk_text, COALESCE(plain_summary, '')
            FROM knia_fault_chart_chunks
            WHERE embedding IS NULL
            ORDER BY display_priority ASC, created_at ASC
            LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()
        for chunk_id, chunk_text, plain_summary in rows:
            vec = vector_literal(provider.embed(f"{plain_summary}\n{chunk_text}"))
            cur.execute("UPDATE knia_fault_chart_chunks SET embedding=%s::vector WHERE id=%s", (vec, chunk_id))
            processed += 1
        conn.commit()
    return {"processed": processed, "embedding_model": model}
