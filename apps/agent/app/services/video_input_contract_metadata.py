from __future__ import annotations

from typing import Any

from app.services.video_input_contract_rules import (
    FRAME_RICH_RECOVERY_MIN_FRAMES,
    TECHNICAL_FIELDS,
)


def technical_metadata(meta: dict[str, Any], nested: dict[str, Any]) -> dict[str, Any]:
    technical: dict[str, Any] = {}
    for source in (nested, meta):
        for field in TECHNICAL_FIELDS:
            if field in technical:
                continue
            value = source.get(field) if isinstance(source, dict) else None
            if value not in (None, "", [], {}):
                technical[field] = value
    event_summary = accident_event_summary(meta, nested)
    if event_summary:
        technical["accident_event_summary"] = event_summary
    frames = frame_list(nested) or frame_list(meta)
    if frames:
        technical["representative_frame_count"] = len(frames)
    return technical


def accident_event_summary(meta: dict[str, Any], nested: dict[str, Any]) -> dict[str, Any]:
    for source in (nested, meta):
        if not isinstance(source, dict):
            continue
        frame_analysis = source.get("openai_frame_analysis")
        if not isinstance(frame_analysis, dict):
            continue
        event_summary = frame_analysis.get("accident_event_summary")
        if not isinstance(event_summary, dict):
            continue
        output = {
            "impact_visible": event_summary.get("impact_visible"),
            "event_frame_count": safe_len(event_summary.get("event_frame_refs")),
            "pre_impact_frame_count": safe_len(event_summary.get("pre_impact_frame_refs")),
            "post_impact_frame_count": safe_len(event_summary.get("post_impact_frame_refs")),
        }
        return {key: value for key, value in output.items() if value not in (None, "", [], {})}
    return {}


def frame_rich_zero_observation_fallback(
    meta: dict[str, Any],
    nested: dict[str, Any],
    technical: dict[str, Any],
    observations: list[Any],
) -> dict[str, Any] | None:
    for item in frame_rich_zero_observation_fallbacks(meta, nested, technical, observations):
        if item.get("field") == "visual_evidence_limited":
            return item
    return None


def frame_rich_zero_observation_fallbacks(
    meta: dict[str, Any],
    nested: dict[str, Any],
    technical: dict[str, Any],
    observations: list[Any],
) -> list[dict[str, Any]]:
    if observations:
        return []
    frame_count = int(technical.get("representative_frame_count") or 0)
    if frame_count < FRAME_RICH_RECOVERY_MIN_FRAMES:
        return []
    if not vision_analysis_attempted(meta, nested):
        return []
    frame_refs = fallback_frame_refs(meta, nested)
    if not frame_refs:
        return []
    fallbacks: list[dict[str, Any]] = []
    event_summary = technical.get("accident_event_summary")
    if isinstance(event_summary, dict) and (
        event_summary.get("impact_visible") is True or int(event_summary.get("event_frame_count") or 0) > 0
    ):
        fallbacks.append({
            "field": "accident_event_candidate",
            "value": True,
            "confidence": 0.82,
            "source": "video_preprocess_observation",
            "frame_refs": frame_refs[:3],
            "reason": (
                "Frame-rich analysis found possible accident event frames, but did not return "
                "reliable collision partner or cause facts."
            ),
        })
    fallbacks.append({
        "field": "visual_evidence_limited",
        "value": True,
        "confidence": 1.0,
        "source": "video_preprocess_observation",
        "frame_refs": frame_refs,
        "reason": (
            "Frame-rich video analysis was attempted, but no reliable physical accident facts "
            "were returned in the observation contract."
        ),
    })
    return fallbacks


def analysis_recovery_plan(
    meta: dict[str, Any],
    nested: dict[str, Any],
    technical: dict[str, Any],
    accepted: list[dict[str, Any]],
    uncertain: list[dict[str, Any]],
    ignored: list[dict[str, Any]],
    supporting: list[dict[str, Any]],
) -> dict[str, Any]:
    frame_count = int(technical.get("representative_frame_count") or 0)
    has_uncertain = bool(uncertain)
    has_limited_visual = any(item.get("field") == "visual_evidence_limited" for item in supporting)
    has_event_candidate = any(item.get("field") == "accident_event_candidate" for item in supporting)
    if frame_count < FRAME_RICH_RECOVERY_MIN_FRAMES or (accepted and not has_limited_visual):
        return {"status": "not_required", "actions": []}

    openai = analysis_payload(meta, nested, "openai_frame_analysis")
    yolo = analysis_payload(meta, nested, "yolo_frame_analysis")
    actions: list[dict[str, str]] = []
    retry_plan: list[dict[str, str]] = []

    if not isinstance(openai, dict) or openai.get("enabled") is not True:
        action = {
            "code": "enable_openai_frame_analysis",
            "label": "OpenAI 프레임 분석 활성화",
            "reason": "대표 프레임은 충분하지만 OpenAI 프레임 관찰값이 생성되지 않았습니다.",
        }
        actions.append(action)
        retry_plan.append(action)
    elif has_limited_visual or not accepted:
        action = {
            "code": "rerun_openai_frame_analysis",
            "label": "프레임 분석 재시도",
            "reason": "영상 분석은 실행됐지만 판단에 바로 반영할 물리 사실이 부족했습니다.",
        }
        actions.append(action)
        retry_plan.append(action)

    if not isinstance(yolo, dict) or yolo.get("enabled") is not True:
        action = {
            "code": "enable_yolo_frame_analysis",
            "label": "YOLO 보조 관찰 활성화",
            "reason": "차량·사람·신호등 위치 후보를 별도 모델로 보강할 수 있습니다.",
        }
        actions.append(action)
        retry_plan.append(action)
    elif not accepted:
        action = {
            "code": "include_yolo_object_candidates",
            "label": "YOLO 객체 후보 함께 검토",
            "reason": "객체 후보는 사고유형 확정값이 아니라 충돌 대상 확인 후보로 함께 검토해야 합니다.",
        }
        actions.append(action)
        retry_plan.append(action)

    frame_refs = fallback_frame_refs(meta, nested)
    if frame_refs:
        action = {
            "code": "select_event_window_frames",
            "label": "사고 시점 후보 프레임 재선택",
            "reason": "사고 전·충돌·사고 후 프레임을 다시 묶어 분석하면 초반 배경 오인을 줄일 수 있습니다.",
        }
        actions.insert(0, action)
        retry_plan.insert(0, action)

    confirm_action = {
        "code": "ask_user_confirmation",
        "label": "사고 시점과 충돌 대상 확인",
        "reason": "영상만으로 확정되지 않은 경우 사용자가 사고 발생 시점, 실제 충돌 대상, 상대 신호를 보완해야 합니다.",
    }
    actions.append(confirm_action)
    retry_plan.append(confirm_action)

    return {
        "status": "frame_rich_uncertain_observations_only" if has_uncertain and not has_limited_visual and not has_event_candidate else "frame_rich_no_actionable_observation",
        "frame_count": frame_count,
        "actions": actions[:4],
        "retry_plan": retry_plan[:5],
        "confirmation_prompts": recovery_confirmation_prompts(uncertain, supporting, technical),
    }


def recovery_confirmation_prompts(
    uncertain: list[dict[str, Any]],
    supporting: list[dict[str, Any]],
    technical: dict[str, Any],
) -> list[dict[str, str]]:
    fields = {str(item.get("field") or "") for item in uncertain if item.get("field")}
    supporting_fields = {str(item.get("field") or "") for item in supporting if item.get("field")}
    prompts: list[dict[str, str]] = []
    if "accident_event_candidate" in supporting_fields or technical.get("accident_event_summary"):
        prompts.append({
            "code": "confirm_accident_event_window",
            "field": "accident_event_window",
            "label": "사고 시점",
            "question": "영상에서 실제 충돌이 일어난 구간이 맞나요?",
        })
    if fields.intersection({"collision_partner_type", "direct_collision_partner_type", "primary_collision_target"}):
        prompts.append({
            "code": "confirm_collision_partner",
            "field": "collision_partner_type",
            "label": "실제 충돌 대상",
            "question": "실제로 부딪힌 대상이 차량, 사람, 자전거, 장애물 중 무엇인가요?",
        })
    if fields.intersection({"collision_point_visible", "primary_collision_target"}):
        prompts.append({
            "code": "confirm_collision_point",
            "field": "collision_point_visible",
            "label": "충돌 지점",
            "question": "충돌 지점이 영상에서 명확히 보이나요?",
        })
    if fields.intersection({"opponent_signal_violation", "opponent_signal_status", "opponent_signal_visible", "signal_transition"}):
        prompts.append({
            "code": "confirm_signal_state",
            "field": "signal_state",
            "label": "신호 상태",
            "question": "내 신호와 상대 차량 신호가 각각 어떤 상태였나요?",
        })
    if not prompts:
        prompts.append({
            "code": "confirm_collision_summary",
            "field": "collision_summary",
            "label": "사고 핵심 사실",
            "question": "실제 충돌 대상, 사고 시점, 충돌 직전 행동을 확인해 주세요.",
        })
    return prompts[:4]


def frame_list(value: dict[str, Any]) -> list[Any]:
    for key in ("representative_frames", "extracted_frame_paths", "frames", "frame_paths"):
        frames = value.get(key)
        if isinstance(frames, list):
            return frames
    return []


def fallback_frame_refs(meta: dict[str, Any], nested: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for source in (nested, meta):
        if not isinstance(source, dict):
            continue
        openai = source.get("openai_frame_analysis")
        if isinstance(openai, dict):
            event_summary = openai.get("accident_event_summary")
            if isinstance(event_summary, dict):
                for key in ("event_frame_refs", "pre_impact_frame_refs", "post_impact_frame_refs"):
                    values = event_summary.get(key)
                    if isinstance(values, list):
                        refs.extend(str(item) for item in values if item)
    if not refs:
        refs = [str(item).rsplit("/", 1)[-1].rsplit("\\", 1)[-1] for item in (frame_list(nested) or frame_list(meta)) if item]
    unique_refs = list(dict.fromkeys(refs))
    return unique_refs[:6]


def vision_analysis_attempted(meta: dict[str, Any], nested: dict[str, Any]) -> bool:
    for source in (nested, meta):
        if not isinstance(source, dict):
            continue
        for key in ("openai_frame_analysis", "yolo_frame_analysis"):
            payload = source.get(key)
            if isinstance(payload, dict) and payload.get("enabled") is True:
                return True
    return False


def analysis_payload(meta: dict[str, Any], nested: dict[str, Any], key: str) -> dict[str, Any] | None:
    for source in (nested, meta):
        if not isinstance(source, dict):
            continue
        payload = source.get(key)
        if isinstance(payload, dict):
            return payload
    return None


def safe_len(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0
