from __future__ import annotations

from fastapi import APIRouter, Header

from app.mcp.tool_executor import execute_tool
from app.routers.internal_auth import check_internal_token
from app.services.knia.knia_collector import KniaCollector
from app.services.knia.knia_fault_adjuster import estimate_knia_fault
from app.services.knia.knia_json_loader import import_knia_json
from app.services.knia.knia_json_menu_builder import get_myaccident_pages, get_myaccident_tree
from app.services.knia.knia_json_vectorizer import rebuild_knia_json_embeddings
from app.services.knia.knia_matcher import match_knia_charts
from app.services.knia.knia_repository import KniaRepository
from app.services.knia.knia_vectorizer import rebuild_knia_embeddings
from app.services.rag.two_stage_cache import search_knia_json_cached

router = APIRouter()


@router.post("/knia/collect/menu-pages")
async def knia_collect_menu_pages(x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
    return KniaCollector().collect_menu_pages()


@router.post("/knia/collect/ranking")
async def knia_collect_ranking(x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
    return KniaCollector().collect_ranking()


@router.post("/knia/collect/charts")
async def knia_collect_charts(payload: dict | None = None, x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
    payload = payload or {}
    return KniaCollector().collect_fault_charts(chart_nos=payload.get("chart_nos"), max_charts=payload.get("max_charts"))


@router.post("/knia/collect/ranking-details")
async def knia_collect_ranking_details(payload: dict | None = None, x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
    payload = payload or {}
    return KniaCollector().collect_ranking_chart_details(limit=payload.get("limit"), force=bool(payload.get("force", False)))


@router.post("/knia/fault/estimate")
async def knia_fault_estimate(payload: dict, x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
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
    check_internal_token(x_internal_token)
    return {"chart_no": chart_no, "chart_type": chartType, "items": KniaRepository().get_chart_adjustments(chart_no, chartType)}


@router.get("/knia/charts/{chart_no}/references")
async def knia_chart_references(chart_no: str, chartType: str = "1", x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
    refs = KniaRepository().get_chart_references(chart_no, chartType)
    return {"chart_no": chart_no, "chart_type": chartType, **refs}


@router.post("/knia/rebuild-embeddings")
async def knia_rebuild_embeddings(payload: dict | None = None, x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
    payload = payload or {}
    return rebuild_knia_embeddings(limit=int(payload.get("limit") or 1000))


@router.post("/knia/match")
async def knia_match(payload: dict, x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
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
    check_internal_token(x_internal_token)
    return match_knia_charts(description_text=q, structured_facts={}, selected_keywords=[], scenario_type=None, limit=5)


@router.post("/knia/import-json")
async def knia_import_json(payload: dict | None = None, x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
    payload = payload or {}
    return import_knia_json(
        payload.get("path"),
        force=bool(payload.get("force", False)),
        rebuild_embeddings=bool(payload.get("rebuild_embeddings", False)),
    )


@router.post("/knia/json/rebuild-embeddings")
async def knia_json_rebuild_embeddings(payload: dict | None = None, x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
    payload = payload or {}
    return rebuild_knia_json_embeddings(limit=payload.get("limit"), force=bool(payload.get("force", False)))


@router.get("/knia/myaccident-pages")
async def knia_myaccident_pages(x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
    return {"items": get_myaccident_pages()}


@router.get("/knia/myaccident/{myaccident_no}/tree")
async def knia_myaccident_tree(myaccident_no: int, x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
    return get_myaccident_tree(myaccident_no)


@router.get("/knia/json/search")
async def knia_json_search(q: str, accidentPartyType: str | None = None, limit: int = 5, x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
    return search_knia_json_cached(q, accident_party_type=accidentPartyType, limit=limit)


@router.get("/knia/media/search")
async def knia_media_search(q: str, accidentPartyType: str | None = None, x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
    return execute_tool("get_knia_media_by_query_tool", {"query": q, "accident_party_type": accidentPartyType, "limit": 8})
