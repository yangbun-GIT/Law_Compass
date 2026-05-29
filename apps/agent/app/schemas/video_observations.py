from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class VideoOnlyMlkitDemoRequest(BaseModel):
    mode: str = "video_only_mlkit_demo"
    upload_id: str | None = None
    video_metadata: dict[str, Any] = Field(default_factory=dict)
    client_pre_observations: dict[str, Any] = Field(default_factory=dict)
    user_text: str | None = None


class VideoOnlyMlkitDemoResponse(BaseModel):
    mode: str
    status: str
    analysis_readiness: dict[str, Any]
    observation_summary: dict[str, Any]
    video_observation_summary: dict[str, Any]
    candidate_accident_context: dict[str, Any]
    fault_ratio_result: dict[str, Any]
    forbidden_field_paths: list[str] = Field(default_factory=list)

