from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.accident_party_action_guide import build_party_type_action_guide
from app.services.accident_perspective import infer_user_vehicle_role
from app.services.dynamic_questionnaire import build_dynamic_questionnaire
from app.services.input_normalizer import normalize_analysis_input
from app.services.input_requirements import build_followup_loop_state, build_input_requirements
from app.services.scenario_classifier import classify_scenario
from app.services.video_context_analyzer import summarize_video_context
from app.services.video_observation_summarizer import build_video_scene_summary


@dataclass
class CaseContext:
    video_context: dict[str, Any]
    normalized: dict[str, Any]
    scenario: dict[str, Any]
    party_type_action_guide: dict[str, Any]
    input_requirements: dict[str, Any]
    guided_questionnaire: dict[str, Any]
    followup_loop: dict[str, Any]
    decision_blocking_missing_fields: list[str]


def build_case_context(
    *,
    description_text: str,
    structured_facts: dict[str, Any] | None,
    selected_keywords: list[str] | None,
    analysis_mode: str | None,
    video_metadata: dict[str, Any] | None,
    initial_intake: dict[str, Any] | None = None,
) -> CaseContext:
    video_context = summarize_video_context(video_metadata)
    normalized = normalize_analysis_input(
        description_text=description_text,
        structured_facts=structured_facts,
        selected_keywords=selected_keywords,
        video_metadata=video_metadata,
        analysis_mode=analysis_mode,
        initial_intake=initial_intake,
    )
    video_scene_summary = build_video_scene_summary(
        normalized.get("video_input_contract") or {},
        _nested_video_block(video_metadata, "openai_frame_analysis"),
        _nested_video_block(video_metadata, "yolo_analysis") or _nested_video_block(video_metadata, "vision_object_inventory"),
        video_metadata or {},
    )
    video_context = {**video_context, "video_scene_summary": video_scene_summary}
    if video_scene_summary.get("available"):
        normalized["structured_facts"] = {
            **normalized["structured_facts"],
            "video_scene_summary": video_scene_summary,
        }
    scenario = classify_scenario(
        normalized["merged_text"],
        normalized["structured_facts"],
        normalized["selected_keywords"],
    )
    user_vehicle_role = infer_user_vehicle_role(
        normalized["description_text"],
        normalized["structured_facts"],
        scenario.get("scenario_type"),
    )
    if user_vehicle_role != "unknown":
        normalized["structured_facts"] = {**normalized["structured_facts"], "user_vehicle_role": user_vehicle_role}

    party_type_action_guide = build_party_type_action_guide(
        scenario.get("accident_party_type", "unknown"),
        normalized["structured_facts"],
        scenario.get("scenario_type"),
    )
    input_requirements = build_input_requirements(
        facts=normalized["structured_facts"],
        scenario_type=scenario["scenario_type"],
        accident_party_type=scenario.get("accident_party_type"),
        missing_fields=normalized["missing_fields"],
        description_text=normalized["description_text"],
    )
    guided_questionnaire = build_dynamic_questionnaire(
        scenario_type=scenario["scenario_type"],
        accident_party_type=scenario.get("accident_party_type"),
        analysis_mode=normalized.get("analysis_mode"),
        description_text=normalized["description_text"],
        structured_facts=normalized["structured_facts"],
        selected_keywords=normalized["selected_keywords"],
        video_observations=video_context,
    )
    input_requirements = {**input_requirements, "guided_questionnaire": guided_questionnaire}
    followup_loop = build_followup_loop_state(input_requirements, normalized["structured_facts"])
    return CaseContext(
        video_context=video_context,
        normalized=normalized,
        scenario=scenario,
        party_type_action_guide=party_type_action_guide,
        input_requirements=input_requirements,
        guided_questionnaire=guided_questionnaire,
        followup_loop=followup_loop,
        decision_blocking_missing_fields=list(input_requirements.get("blocking_fields") or []),
    )


def _nested_video_block(video_metadata: dict[str, Any] | None, key: str) -> dict[str, Any]:
    if not isinstance(video_metadata, dict):
        return {}
    direct = video_metadata.get(key)
    if isinstance(direct, dict):
        return direct
    metadata = video_metadata.get("metadata")
    if isinstance(metadata, dict) and isinstance(metadata.get(key), dict):
        return metadata[key]
    analysis = video_metadata.get("analysis")
    if isinstance(analysis, dict) and isinstance(analysis.get(key), dict):
        return analysis[key]
    return {}
