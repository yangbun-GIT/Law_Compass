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
    if observations:
        return None
    frame_count = int(technical.get("representative_frame_count") or 0)
    if frame_count < FRAME_RICH_RECOVERY_MIN_FRAMES:
        return None
    if not vision_analysis_attempted(meta, nested):
        return None
    frame_refs = fallback_frame_refs(meta, nested)
    if not frame_refs:
        return None
    return {
        "field": "visual_evidence_limited",
        "value": True,
        "confidence": 1.0,
        "source": "video_preprocess_observation",
        "frame_refs": frame_refs,
        "reason": (
            "Frame-rich video analysis was attempted, but no reliable physical accident facts "
            "were returned in the observation contract."
        ),
    }


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
    has_actionable = bool(accepted or uncertain or ignored)
    has_limited_visual = any(item.get("field") == "visual_evidence_limited" for item in supporting)
    if frame_count < FRAME_RICH_RECOVERY_MIN_FRAMES or (has_actionable and not has_limited_visual):
        return {"status": "not_required", "actions": []}

    openai = analysis_payload(meta, nested, "openai_frame_analysis")
    yolo = analysis_payload(meta, nested, "yolo_frame_analysis")
    actions: list[dict[str, str]] = []

    if not isinstance(openai, dict) or openai.get("enabled") is not True:
        actions.append({
            "label": "OpenAI 프레임 분석 활성화",
            "reason": "대표 프레임은 충분하지만 OpenAI 프레임 관찰값이 생성되지 않았습니다.",
        })
    elif has_limited_visual or not accepted:
        actions.append({
            "label": "프레임 분석 재시도",
            "reason": "영상 분석은 실행됐지만 판단에 바로 반영할 물리 사실이 부족했습니다.",
        })

    if not isinstance(yolo, dict) or yolo.get("enabled") is not True:
        actions.append({
            "label": "YOLO 보조 관찰 활성화",
            "reason": "차량·사람·신호등 위치 후보를 별도 모델로 보강할 수 있습니다.",
        })

    actions.append({
        "label": "사고 시점과 충돌 대상 확인",
        "reason": "영상만으로 확정되지 않은 경우 사용자가 사고 발생 시점, 실제 충돌 대상, 상대 신호를 보완해야 합니다.",
    })

    return {
        "status": "frame_rich_no_actionable_observation",
        "frame_count": frame_count,
        "actions": actions[:4],
    }


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
