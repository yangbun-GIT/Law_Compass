from __future__ import annotations

from typing import Any


def summarize_video_context(video_metadata: dict[str, Any] | None) -> dict[str, Any]:
    meta = video_metadata or {}
    nested = meta.get("metadata") if isinstance(meta.get("metadata"), dict) else meta
    frames = nested.get("representative_frames") or []
    frame_cards = _displayable_frame_cards(nested.get("frame_interpretation_cards"))
    summary = nested.get("preprocess_summary") or ""
    if not summary and nested:
        summary = (
            f"영상 메타데이터: duration={nested.get('duration_sec')}초, "
            f"resolution={nested.get('width')}x{nested.get('height')}, frames={len(frames)}개"
        )

    limitations: list[str] = []
    if frame_cards:
        limitations.append(
            "선별 프레임에서 확인 가능한 시각 단서를 함께 사용했습니다. 보이지 않는 사실은 추가 확인으로 남깁니다."
        )
    elif _frame_analysis_disabled(nested):
        limitations.append(
            "영상 시각 분석이 꺼져 있거나 OpenAI 프레임 분석 설정이 없어 사고 장면을 자동 판독하지 못했습니다."
        )
    else:
        limitations.append(
            "현재 영상 분석은 메타데이터와 선별 프레임 기준의 참고 정보이며, 불명확한 장면은 사용자 확인이 필요합니다."
        )

    return {
        "summary": summary,
        "duration_sec": nested.get("duration_sec"),
        "width": nested.get("width"),
        "height": nested.get("height"),
        "fps": nested.get("fps"),
        "codec": nested.get("codec"),
        "frame_count": len(frames),
        "representative_frames": frames,
        "frame_interpretation_cards": frame_cards,
        "limitations": limitations,
    }


def _frame_analysis_disabled(nested: dict[str, Any]) -> bool:
    frame_analysis = nested.get("openai_frame_analysis")
    if not isinstance(frame_analysis, dict):
        return False
    reason = str(frame_analysis.get("reason") or "")
    return (
        frame_analysis.get("enabled") is False
        or "OPENAI_API_KEY" in reason
        or "ENABLE_OPENAI_FRAME_ANALYSIS" in reason
    )


def _displayable_frame_cards(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    cards: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict) and item.get("display_allowed") is True:
            cards.append(item)
    return cards[:6]
