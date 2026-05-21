from __future__ import annotations

import os

import psycopg

from app.services.legal.legal_vectorizer import embedding_model_name, vectorize_text

DB_URL = os.getenv("DATABASE_URL", "postgresql://law:lawpass@postgres:5432/lawcompass")


def main():
    processed = 0
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT kc.id, kc.chunk_text
                FROM kb_chunks kc
                LEFT JOIN kb_embeddings ke ON ke.chunk_id = kc.id
                WHERE ke.chunk_id IS NULL
                ORDER BY kc.created_at ASC
                """
            )
            for chunk_id, text in cur.fetchall():
                vec, model = vectorize_text(text)
                cur.execute(
                    """
                    INSERT INTO kb_embeddings(chunk_id, embedding, embedding_model)
                    VALUES(%s,%s::vector,%s)
                    ON CONFLICT(chunk_id) DO UPDATE
                    SET embedding=EXCLUDED.embedding,
                        embedding_model=EXCLUDED.embedding_model,
                        created_at=now()
                    """,
                    (chunk_id, vec, model),
                )
                processed += 1
            conn.commit()
    print(f"processed_embeddings={processed} embedding_model={embedding_model_name()}")


if __name__ == "__main__":
    main()
