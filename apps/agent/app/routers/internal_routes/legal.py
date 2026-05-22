from __future__ import annotations

import os

import psycopg
from fastapi import APIRouter, Header, HTTPException

from app.routers.internal_auth import check_internal_token
from app.services.legal.legal_evidence_retriever import retrieve_legal_evidence
from app.services.legal.legal_ingestion_service import ingest_traffic_law_documents
from app.services.legal.legal_vectorizer import embedding_model_name, vectorize_text

router = APIRouter()


@router.post("/legal/ingest")
async def legal_ingest(x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
    return ingest_traffic_law_documents()


@router.post("/legal/rebuild-embeddings")
async def legal_rebuild_embeddings(x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL missing")
    processed = 0
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT kc.id, kc.chunk_text
                FROM kb_chunks kc
                LEFT JOIN kb_embeddings ke ON ke.chunk_id = kc.id
                WHERE ke.chunk_id IS NULL
                ORDER BY kc.created_at ASC
                LIMIT 500
                """
            )
            for chunk_id, text in cur.fetchall():
                vec, model = vectorize_text(text)
                cur.execute(
                    "INSERT INTO kb_embeddings(chunk_id, embedding, embedding_model) VALUES(%s,%s::vector,%s) ON CONFLICT(chunk_id) DO NOTHING",
                    (chunk_id, vec, model),
                )
                processed += 1
            conn.commit()
    return {"processed": processed, "embedding_model": embedding_model_name()}


@router.get("/legal/retrieval-test")
async def legal_retrieval_test(q: str = "후미추돌 안전거리 과실비율", x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
    result = retrieve_legal_evidence(scenario_type="general_collision", scenario_tags=[], query=q, limit=5)
    return {"query": q, "cache_hit": result["cache_hit"], "items": result["items"]}
