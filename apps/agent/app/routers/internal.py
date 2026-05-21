from __future__ import annotations

import os

import psycopg
from fastapi import APIRouter, Header, HTTPException

from app.schemas import AnalysisOutput, AnalyzeTextRequest, AnalyzeVideoRequest
from app.services.chat.chat_orchestrator import handle_chat_message
from app.services.knia.knia_collector import KniaCollector
from app.services.knia.knia_fault_adjuster import estimate_knia_fault
from app.services.knia.knia_matcher import match_knia_charts
from app.services.knia.knia_repository import KniaRepository
from app.services.knia.knia_json_loader import import_knia_json
from app.services.knia.knia_json_menu_builder import get_myaccident_pages, get_myaccident_tree
from app.services.knia.knia_json_vectorizer import rebuild_knia_json_embeddings
from app.services.rag.two_stage_cache import invalidate_scope, search_knia_json_cached
from app.mcp.tool_executor import execute_tool
from app.services.knia.knia_vectorizer import rebuild_knia_embeddings
from app.services.legal.legal_evidence_retriever import retrieve_legal_evidence
from app.services.legal.legal_ingestion_service import ingest_traffic_law_documents
from app.services.legal.legal_vectorizer import embedding_model_name, vectorize_text
from app.services.orchestrator import analyze_case, analyze_scenario, analyze_video_case

router = APIRouter(prefix="/internal/v1", tags=["internal"])


def _check_internal_token(token: str | None):
    expected = os.getenv("INTERNAL_SERVICE_TOKEN", "")
    if not token or token != expected:
        raise HTTPException(status_code=401, detail="invalid internal token")


@router.get("/health")
async def health():
    return {"ok": True}


@router.post("/analyze/text", response_model=AnalysisOutput)
async def analyze_text(payload: AnalyzeTextRequest, x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
    return AnalysisOutput(
        **analyze_case(
            payload.description_text,
            structured_facts=payload.structured_facts,
            selected_keywords=payload.selected_keywords,
            analysis_mode=payload.analysis_mode,
            ai_profile=payload.ai_profile,
            specialist_roles=payload.specialist_roles,
        )
    )


@router.post("/analyze/video", response_model=AnalysisOutput)
async def analyze_video(payload: AnalyzeVideoRequest, x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
    base_text = payload.preprocessed_summary or "영상 분석 정보가 충분하지 않습니다. 사고 상황을 글로 조금 더 입력해 주세요."
    return AnalysisOutput(
        **analyze_video_case(
            preprocessed_summary=base_text,
            ai_profile=payload.ai_profile or "default_vehicle_collision",
            specialist_roles=payload.specialist_roles,
            video_metadata=payload.video_metadata,
            structured_facts=payload.structured_facts,
            selected_keywords=payload.selected_keywords,
            analysis_mode=payload.analysis_mode,
        )
    )


@router.post("/analyze/scenario", response_model=AnalysisOutput)
async def analyze_scenario_endpoint(payload: dict, x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
    return AnalysisOutput(**analyze_scenario(payload))


@router.post("/jobs/process")
async def process_job(payload: dict, x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
    return {"ok": True, "received": payload}


@router.post("/legal/ingest")
async def legal_ingest(x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
    return ingest_traffic_law_documents()


@router.post("/legal/rebuild-embeddings")
async def legal_rebuild_embeddings(x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
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
    _check_internal_token(x_internal_token)
    result = retrieve_legal_evidence(scenario_type="general_collision", scenario_tags=[], query=q, limit=5)
    return {"query": q, "cache_hit": result["cache_hit"], "items": result["items"]}


@router.post("/chat/message")
async def chat_message(payload: dict, x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
    return handle_chat_message(payload)


@router.post("/knia/collect/menu-pages")
async def knia_collect_menu_pages(x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
    return KniaCollector().collect_menu_pages()


@router.post("/knia/collect/ranking")
async def knia_collect_ranking(x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
    return KniaCollector().collect_ranking()


@router.post("/knia/collect/charts")
async def knia_collect_charts(payload: dict | None = None, x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
    payload = payload or {}
    return KniaCollector().collect_fault_charts(chart_nos=payload.get("chart_nos"), max_charts=payload.get("max_charts"))


@router.post("/knia/collect/ranking-details")
async def knia_collect_ranking_details(payload: dict | None = None, x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
    payload = payload or {}
    return KniaCollector().collect_ranking_chart_details(limit=payload.get("limit"), force=bool(payload.get("force", False)))


@router.post("/knia/fault/estimate")
async def knia_fault_estimate(payload: dict, x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
    return estimate_knia_fault(
        chart_no=payload.get("chart_no"),
        chart_type=payload.get("chart_type") or "1",
        description_text=payload.get("description_text") or "",
        selected_keywords=payload.get("selected_keywords") or [],
        structured_facts=payload.get("structured_facts") or {},
        video_metadata=payload.get("video_metadata") or {},
        scenario_type=payload.get("scenario_type"),
        accident_party_type=payload.get("accident_party_type"),
    )


@router.get("/knia/charts/{chart_no}/adjustments")
async def knia_chart_adjustments(chart_no: str, chartType: str = "1", x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
    return {"chart_no": chart_no, "chart_type": chartType, "items": KniaRepository().get_chart_adjustments(chart_no, chartType)}


@router.get("/knia/charts/{chart_no}/references")
async def knia_chart_references(chart_no: str, chartType: str = "1", x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
    refs = KniaRepository().get_chart_references(chart_no, chartType)
    return {"chart_no": chart_no, "chart_type": chartType, **refs}


@router.post("/knia/rebuild-embeddings")
async def knia_rebuild_embeddings(payload: dict | None = None, x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
    payload = payload or {}
    return rebuild_knia_embeddings(limit=int(payload.get("limit") or 1000))


@router.post("/knia/match")
async def knia_match(payload: dict, x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
    return match_knia_charts(
        description_text=payload.get("description_text") or "",
        structured_facts=payload.get("structured_facts") or {},
        selected_keywords=payload.get("selected_keywords") or [],
        scenario_type=payload.get("scenario_type"),
        accident_party_type=payload.get("accident_party_type"),
        limit=int(payload.get("limit") or 5),
    )


@router.get("/knia/retrieval-test")
async def knia_retrieval_test(q: str = "후미추돌 정차 뒤차 추돌", x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
    return match_knia_charts(description_text=q, structured_facts={}, selected_keywords=[], scenario_type=None, limit=5)


@router.post("/knia/import-json")
async def knia_import_json(payload: dict | None = None, x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
    payload = payload or {}
    return import_knia_json(
        payload.get("path"),
        force=bool(payload.get("force", False)),
        rebuild_embeddings=bool(payload.get("rebuild_embeddings", False)),
    )


@router.post("/knia/json/rebuild-embeddings")
async def knia_json_rebuild_embeddings(payload: dict | None = None, x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
    payload = payload or {}
    return rebuild_knia_json_embeddings(limit=payload.get("limit"), force=bool(payload.get("force", False)))


@router.get("/knia/myaccident-pages")
async def knia_myaccident_pages(x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
    return {"items": get_myaccident_pages()}


@router.get("/knia/myaccident/{myaccident_no}/tree")
async def knia_myaccident_tree(myaccident_no: int, x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
    return get_myaccident_tree(myaccident_no)


@router.get("/knia/json/search")
async def knia_json_search(q: str, accidentPartyType: str | None = None, limit: int = 5, x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
    return search_knia_json_cached(q, accident_party_type=accidentPartyType, limit=limit)


@router.get("/knia/media/search")
async def knia_media_search(q: str, accidentPartyType: str | None = None, x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
    return execute_tool("get_knia_media_by_query_tool", {"query": q, "accident_party_type": accidentPartyType, "limit": 8})


@router.post("/cache/invalidate")
async def cache_invalidate(payload: dict | None = None, x_internal_token: str | None = Header(default=None)):
    _check_internal_token(x_internal_token)
    payload = payload or {}
    return invalidate_scope(payload.get("scope") or "knia_json")
