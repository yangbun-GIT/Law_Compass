from __future__ import annotations

from typing import Any


def summarize_video_context(video_metadata: dict[str, Any] | None) -> dict[str, Any]:
    meta = video_metadata or {}
    nested = meta.get("metadata") if isinstance(meta.get("metadata"), dict) else meta
    frames = nested.get("representative_frames") or []
    summary = nested.get("preprocess_summary") or ""
    if not summary and nested:
        summary = (
            f"영상 메타데이터: duration={nested.get('duration_sec')}초, "
            f"resolution={nested.get('width')}x{nested.get('height')}, frames={len(frames)}장"
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
        "limitations": ["현재 MVP는 영상의 실제 객체 인식이 아니라 메타데이터와 사용자가 입력한 사고 사실을 함께 사용합니다."],
    }
