from __future__ import annotations

from fastapi import APIRouter, Header

from app.routers.internal_auth import check_internal_token
from app.schemas import VideoOnlyMlkitDemoRequest, VideoOnlyMlkitDemoResponse
from app.services.video_observation_summarizer import summarize_client_pre_observations

router = APIRouter()


@router.post("/mobile-demo/video-only-analysis", response_model=VideoOnlyMlkitDemoResponse)
async def video_only_analysis(payload: VideoOnlyMlkitDemoRequest, x_internal_token: str | None = Header(default=None)):
    check_internal_token(x_internal_token)
    summary = summarize_client_pre_observations(payload.client_pre_observations)
    return summary
