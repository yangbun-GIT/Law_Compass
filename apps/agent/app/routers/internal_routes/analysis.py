from __future__ import annotations

from fastapi import APIRouter, Header

from app.routers.internal_auth import check_internal_token
from app.schemas import AnalysisOutput, AnalyzeTextRequest, AnalyzeVideoRequest
from app.services.orchestrator import analyze_case, analyze_scenario, analyze_video_case

router = APIRouter()


@router.post("/analyze/text", response_model=AnalysisOutput)
async def analyze_text(payload: AnalyzeTextRequest, x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
    return AnalysisOutput(
        **analyze_case(
            payload.description_text,
            structured_facts=payload.structured_facts,
            selected_keywords=payload.selected_keywords,
            video_metadata=payload.video_metadata,
            analysis_mode=payload.analysis_mode,
            ai_profile=payload.ai_profile,
            specialist_roles=payload.specialist_roles,
        )
    )


@router.post("/analyze/video", response_model=AnalysisOutput)
async def analyze_video(payload: AnalyzeVideoRequest, x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
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
    check_internal_token(x_internal_token)
    return AnalysisOutput(**analyze_scenario(payload))
