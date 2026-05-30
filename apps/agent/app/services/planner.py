from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.services.agent_contracts import AgentInputRef, AgentPlan, AgentTask, EvidenceRequirement, PlanInputMode


AGENT_PLAN_VERSION = "agent-plan-v1"


def build_task_plan(
    *,
    description_text: str | None = None,
    structured_facts: dict[str, Any] | None = None,
    selected_keywords: list[str] | None = None,
    video_metadata: dict[str, Any] | None = None,
    analysis_mode: str | None = None,
    input_mode: PlanInputMode | None = None,
    case_id: str | None = None,
    trace_id: str | None = None,
    upload_id: str | None = None,
    created_by: str | None = None,
) -> AgentPlan:
    """Create a safe metadata-only execution plan for the current analysis run."""

    facts = structured_facts if isinstance(structured_facts, dict) else {}
    resolved_mode = input_mode or _resolve_input_mode(
        description_text=description_text,
        structured_facts=facts,
        selected_keywords=selected_keywords,
        video_metadata=video_metadata,
    )
    creator = "admin_diagnostic" if resolved_mode == "admin_diagnostic" else (created_by or "static_stage_adapter")
    refs = _build_input_refs(
        description_text=description_text,
        structured_facts=facts,
        selected_keywords=selected_keywords,
        video_metadata=video_metadata,
        analysis_mode=analysis_mode,
        upload_id=upload_id,
        input_mode=resolved_mode,
    )
    tasks = _build_tasks(resolved_mode, refs)
    return AgentPlan(
        version=AGENT_PLAN_VERSION,
        plan_id=_new_id("agent-plan"),
        case_id=_safe_id(case_id, "case"),
        trace_id=_safe_id(trace_id, "trace"),
        input_mode=resolved_mode,
        plan_status="ready",
        tasks=tasks,
        execution_order=[task.task_id for task in tasks],
        replan_policy="bounded_on_blocker" if resolved_mode == "followup_reanalysis" else "none",
        created_by=creator,  # type: ignore[arg-type]
    )


def build_safe_fallback_plan(
    *,
    error: BaseException | str,
    input_mode: PlanInputMode | None = None,
    case_id: str | None = None,
    trace_id: str | None = None,
) -> AgentPlan:
    """Return a blocked plan when plan creation itself fails."""

    resolved_mode = input_mode or "text_only"
    task = AgentTask(
        task_id="input_normalization",
        task_type="input_normalization",
        goal="입력 안전성 확인 후 기존 분석 흐름을 중단하지 않고 진행한다.",
        input_refs=[AgentInputRef(ref_type="safe_summary", ref_id="planner_failure", visibility="internal", summary="planner_failed=true")],
        required_evidence=[EvidenceRequirement(evidence_type="user_fact", directness="missing", required=True, reason="planner failure")],
        status="blocked",
        blocking_reasons=["agent_plan_creation_failed"],
    )
    return AgentPlan(
        version=AGENT_PLAN_VERSION,
        plan_id=_new_id("agent-plan"),
        case_id=_safe_id(case_id, "case"),
        trace_id=_safe_id(trace_id, "trace"),
        input_mode=resolved_mode,
        plan_status="safe_fallback",
        tasks=[task],
        execution_order=[task.task_id],
        replan_policy="manual_only",
        created_by="static_stage_adapter",
        failure_observations=[
            {
                "section": "planner",
                "type": "agent_plan_creation_failed",
                "recoverable": True,
                "error_type": type(error).__name__ if not isinstance(error, str) else "PlannerError",
            }
        ],
    )


def _resolve_input_mode(
    *,
    description_text: str | None,
    structured_facts: dict[str, Any],
    selected_keywords: list[str] | None,
    video_metadata: dict[str, Any] | None,
) -> PlanInputMode:
    if _has_followup_markers(structured_facts):
        return "followup_reanalysis"
    has_text = bool((description_text or "").strip()) or bool(structured_facts) or bool(selected_keywords)
    has_video = _has_video_metadata(video_metadata)
    if has_text and has_video:
        return "text_and_video"
    if has_video:
        return "video_only"
    return "text_only"


def _build_input_refs(
    *,
    description_text: str | None,
    structured_facts: dict[str, Any],
    selected_keywords: list[str] | None,
    video_metadata: dict[str, Any] | None,
    analysis_mode: str | None,
    upload_id: str | None,
    input_mode: PlanInputMode,
) -> list[AgentInputRef]:
    refs = [
        AgentInputRef(
            ref_type="safe_summary",
            ref_id="analysis_input_summary",
            visibility="internal",
            summary=(
                f"description_present={bool((description_text or '').strip())};"
                f"structured_fact_count={len([key for key in structured_facts if not str(key).startswith('_')])};"
                f"selected_keyword_count={len(selected_keywords or [])};"
                f"analysis_mode_present={bool(analysis_mode)}"
            ),
        )
    ]
    if structured_facts:
        refs.append(
            AgentInputRef(
                ref_type="structured_fact",
                ref_id="structured_facts",
                visibility="internal",
                summary=f"field_count={len([key for key in structured_facts if not str(key).startswith('_')])}",
            )
        )
    if input_mode == "followup_reanalysis":
        refs.append(
            AgentInputRef(
                ref_type="questionnaire_answer",
                ref_id="followup_answers",
                visibility="internal",
                summary=(
                    f"iteration={structured_facts.get('_followup_iteration', 0)};"
                    f"answered_count={len(structured_facts.get('_followup_answered_fields') or [])};"
                    f"unresolved_count={len(structured_facts.get('_followup_unresolved_fields') or [])}"
                ),
            )
        )
    if _has_video_metadata(video_metadata):
        metadata = _metadata_dict(video_metadata)
        observation_count = len(metadata.get("observations") or [])
        frame_count = len(metadata.get("representative_frames") or [])
        refs.append(
            AgentInputRef(
                ref_type="upload",
                ref_id=_safe_id(upload_id, "upload"),
                visibility="internal",
                summary=f"video_metadata_present=true;representative_frame_count={frame_count};observation_count={observation_count}",
            )
        )
        refs.append(
            AgentInputRef(
                ref_type="video_observation",
                ref_id="video_observations",
                visibility="internal",
                summary=f"candidate_observation_count={observation_count}",
            )
        )
    return refs


def _build_tasks(input_mode: PlanInputMode, input_refs: list[AgentInputRef]) -> list[AgentTask]:
    tasks: list[AgentTask] = [
        _task(
            "input_normalization",
            "input_normalization",
            "사용자 입력과 구조화 fact를 안전한 분석 입력으로 정규화한다.",
            input_refs,
            required_evidence=[_evidence("user_fact", "partial", "입력 사실 정규화")],
        )
    ]
    if input_mode in {"video_only", "text_and_video", "followup_reanalysis", "admin_diagnostic"} and any(
        ref.ref_type in {"upload", "video_observation"} for ref in input_refs
    ):
        tasks.extend(
            [
                _task(
                    "video_observation",
                    "video_observation",
                    "영상 후보 관찰값을 확정 사실과 후보 사실로 분리한다.",
                    _refs(input_refs, {"upload", "video_observation"}),
                    required_tools=["video_frame_analysis_adapter"],
                    required_evidence=[_evidence("video", "partial", "영상 관찰 후보")],
                ),
                _task(
                    "fact_arbitration",
                    "fact_arbitration",
                    "사용자 입력과 영상 관찰값의 충돌, 보류, 반영 대상을 판정한다.",
                    input_refs,
                    required_tools=["evidence_guard_tool"],
                    required_evidence=[
                        _evidence("user_fact", "partial", "사용자 입력"),
                        _evidence("video", "partial", "영상 관찰값"),
                    ],
                ),
            ]
        )
    tasks.extend(
        [
            _task(
                "scenario_classification",
                "scenario_classification",
                "사고 대분류, 직접 충돌 대상, 핵심 사고축을 분류한다.",
                input_refs,
                required_evidence=[_evidence("user_fact", "partial", "사고 분류 입력")],
            ),
            _task(
                "evidence_retrieval",
                "evidence_retrieval",
                "분류된 사고축에 맞는 법령, 판례, 설명 근거를 검색한다.",
                input_refs,
                required_tools=["legal_rag_search_tool", "evidence_guard_tool"],
                required_evidence=[
                    _evidence("law", "partial", "법령 근거"),
                    _evidence("precedent", "partial", "유사 사례 또는 판례 근거"),
                ],
            ),
            _task(
                "knia_matching",
                "knia_matching",
                "사고 대분류와 핵심 fact에 맞는 KNIA 과실비율 기준을 매칭한다.",
                input_refs,
                required_tools=["search_knia_json_rag_tool", "get_knia_media_by_query_tool"],
                required_evidence=[_evidence("knia", "partial", "KNIA 기준")],
            ),
            _task(
                "fault_ratio",
                "fault_ratio",
                "법령, KNIA 기준, 구조화 fact를 기반으로 참고 과실 범위를 산정한다.",
                input_refs,
                required_tools=["evidence_guard_tool"],
                required_evidence=[
                    _evidence("knia", "partial", "과실비율 기준"),
                    _evidence("law", "partial", "주의의무 기준"),
                    _evidence("user_fact", "partial", "핵심 사고 사실"),
                ],
            ),
            _task(
                "criminal_liability",
                "criminal_liability",
                "형사 쟁점 가능성과 신고, 진단, 인명피해 확인 필요성을 정리한다.",
                input_refs,
                required_evidence=[
                    _evidence("law", "partial", "형사책임 기준"),
                    _evidence("user_fact", "partial", "피해 및 사고 사실"),
                ],
            ),
            _task(
                "insurance_guidance",
                "insurance_guidance",
                "보험 접수, 증거 보존, 후속 대응에 필요한 자료를 정리한다.",
                input_refs,
                required_evidence=[
                    _evidence("insurance", "partial", "보험 처리 기준"),
                    _evidence("user_fact", "partial", "사고 처리 입력"),
                ],
            ),
            _task(
                "action_guidance",
                "action_guidance",
                "사용자가 다음에 확인하거나 준비해야 하는 행동 지침을 제시한다.",
                input_refs,
                required_evidence=[
                    _evidence("police", "context", "신고 또는 조사 필요성"),
                    _evidence("medical", "context", "부상 확인 필요성"),
                ],
            ),
            _task(
                "presentation_policy",
                "presentation_policy",
                "확정 판결처럼 말하지 않고 참고 추정, 조건부 결과, 추가 확인 필요성을 구분해 표시한다.",
                input_refs,
                required_tools=["evidence_guard_tool"],
                required_evidence=[_evidence("any", "partial", "최종 표시 안전성")],
            ),
        ]
    )
    return tasks


def _task(
    task_id: str,
    task_type: str,
    goal: str,
    input_refs: list[AgentInputRef],
    *,
    required_tools: list[str] | None = None,
    required_evidence: list[EvidenceRequirement] | None = None,
) -> AgentTask:
    return AgentTask(
        task_id=task_id,
        task_type=task_type,  # type: ignore[arg-type]
        goal=goal,
        input_refs=input_refs,
        required_tools=required_tools or [],
        required_evidence=required_evidence or [],
        status="pending",
    )


def _evidence(evidence_type: str, directness: str, reason: str) -> EvidenceRequirement:
    return EvidenceRequirement(evidence_type=evidence_type, directness=directness, required=True, reason=reason)  # type: ignore[arg-type]


def _refs(input_refs: list[AgentInputRef], ref_types: set[str]) -> list[AgentInputRef]:
    return [ref for ref in input_refs if ref.ref_type in ref_types]


def _has_video_metadata(video_metadata: dict[str, Any] | None) -> bool:
    if not isinstance(video_metadata, dict) or not video_metadata:
        return False
    metadata = _metadata_dict(video_metadata)
    return bool(
        metadata.get("representative_frames")
        or metadata.get("observations")
        or metadata.get("duration_sec")
        or metadata.get("file_name")
        or video_metadata.get("upload_id")
    )


def _metadata_dict(video_metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(video_metadata, dict):
        return {}
    nested = video_metadata.get("metadata")
    return nested if isinstance(nested, dict) else video_metadata


def _has_followup_markers(structured_facts: dict[str, Any]) -> bool:
    if any(str(key).startswith("_followup_") for key in structured_facts):
        return True
    return any(key in structured_facts for key in {"followup_answers", "followupAnswers", "reanalyze_reason"})


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def _safe_id(value: str | None, prefix: str) -> str:
    cleaned = str(value or "").strip()
    if cleaned and not any(marker in cleaned.lower() for marker in ("password", "secret", "token", "api_key", ".env")):
        return cleaned[:96]
    return _new_id(prefix)
