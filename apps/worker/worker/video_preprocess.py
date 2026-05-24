import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VIDEO_PREPROCESS_CONTRACT_VERSION = "worker-video-preprocess-v1"
SCENE_DETECTION_THRESHOLD = float(os.getenv("VIDEO_SCENE_DETECTION_THRESHOLD", "0.28"))
SCENE_DETECTION_TIMEOUT_SEC = float(os.getenv("VIDEO_SCENE_DETECTION_TIMEOUT_SEC", "20"))
SCENE_DETECTION_MAX_EVENTS = int(os.getenv("VIDEO_SCENE_DETECTION_MAX_EVENTS", "24"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def probe_video(storage_path: str) -> dict:
    path = Path(storage_path)
    if not path.exists():
        raise FileNotFoundError(f"video file not found: {storage_path}")
    cmd = ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)]
    raw = subprocess.check_output(cmd, text=True)
    data = json.loads(raw or "{}")
    video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    duration = data.get("format", {}).get("duration") or video_stream.get("duration")
    fps = None
    rate = video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate")
    if rate and "/" in rate:
        n, d = rate.split("/", 1)
        if float(d or 0) != 0:
            fps = round(float(n) / float(d), 3)
    return {
        "extension": path.suffix.lower().lstrip("."),
        "codec": video_stream.get("codec_name"),
        "duration_sec": round(float(duration), 3) if duration else None,
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "fps": fps,
        "file_size_bytes": path.stat().st_size,
        "checked_at": now_iso(),
    }


def frame_times_for_duration(duration_sec: float | None, max_frames: int = 18, event_times: list[float] | None = None) -> list[float]:
    duration = max(0.5, float(duration_sec or 8.0))
    event_times = sorted(set(round(float(time), 2) for time in (event_times or []) if 0 <= float(time) <= duration))
    if event_times:
        return event_focused_frame_times(duration, event_times, max_frames=max_frames)
    if duration <= 5:
        interval = 0.35
    elif duration <= 10:
        interval = 0.5
    elif duration <= 15:
        interval = 0.75
    elif duration <= 30:
        interval = 1.0
    else:
        interval = max(1.25, duration / 30)
    candidates = {0.0, max(0.0, duration - 0.1)}
    t = 0.2 if duration > 0.5 else 0.0
    while t < duration:
        candidates.add(min(duration, t))
        t += interval
    for pct in [0.1, 0.35, 0.65, 0.9]:
        candidates.add(max(0.0, min(duration, duration * pct)))
    times = sorted(round(value, 2) for value in candidates if 0 <= value <= duration)
    if len(times) <= max_frames:
        return times
    if max_frames == 1:
        return [times[len(times) // 2]]
    return [times[round(idx * (len(times) - 1) / (max_frames - 1))] for idx in range(max_frames)]


def event_focused_frame_times(duration_sec: float, event_times: list[float], max_frames: int = 18) -> list[float]:
    duration = max(0.5, float(duration_sec))
    candidates = {0.0, max(0.0, duration - 0.1)}
    for event_time in event_times[:SCENE_DETECTION_MAX_EVENTS]:
        for offset in (-4.0, -2.0, -1.0, -0.35, 0.0, 0.35, 1.0, 2.0, 4.0):
            candidates.add(max(0.0, min(duration, event_time + offset)))
    for pct in (0.1, 0.5, 0.9):
        candidates.add(max(0.0, min(duration, duration * pct)))
    times = sorted(round(value, 2) for value in candidates if 0 <= value <= duration)
    if len(times) <= max_frames:
        return times
    priority = sorted(
        times,
        key=lambda value: (
            0 if _near_any_event(value, event_times, tolerance=4.0) else 1,
            min(abs(value - event_time) for event_time in event_times) if event_times else duration,
            value,
        ),
    )
    selected = sorted(set([0.0, max(0.0, round(duration - 0.1, 2)), *priority[: max(0, max_frames - 2)]]))
    while len(selected) > max_frames:
        removable = [value for value in selected if value not in {0.0, max(0.0, round(duration - 0.1, 2))}]
        if not removable:
            break
        selected.remove(removable[-1])
    return selected


def detect_scene_change_times(storage_path: str, duration_sec: float | None) -> dict[str, Any]:
    duration = float(duration_sec or 0)
    if duration <= 0.5:
        return {"enabled": False, "reason": "duration_too_short", "event_times": []}
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-i",
        storage_path,
        "-vf",
        f"select='gt(scene,{SCENE_DETECTION_THRESHOLD})',showinfo",
        "-an",
        "-f",
        "null",
        "-",
    ]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, timeout=SCENE_DETECTION_TIMEOUT_SEC)
    except subprocess.TimeoutExpired:
        return {"enabled": True, "reason": "scene_detection_timeout", "event_times": [], "threshold": SCENE_DETECTION_THRESHOLD}
    if proc.returncode not in (0, 1):
        return {"enabled": True, "reason": "scene_detection_failed", "event_times": [], "threshold": SCENE_DETECTION_THRESHOLD}
    matches = re.findall(r"pts_time:([0-9]+(?:\.[0-9]+)?)", proc.stderr or "")
    event_times = []
    for raw in matches:
        value = round(float(raw), 2)
        if 0 <= value <= duration and all(abs(value - existing) > 0.5 for existing in event_times):
            event_times.append(value)
        if len(event_times) >= SCENE_DETECTION_MAX_EVENTS:
            break
    return {
        "enabled": True,
        "reason": "scene_detection_completed",
        "threshold": SCENE_DETECTION_THRESHOLD,
        "event_times": event_times,
        "event_count": len(event_times),
    }


def extract_event_frames(
    storage_path: str,
    case_id: str,
    upload_id: str,
    duration_sec: float | None,
    storage_root: Path,
) -> list[dict[str, Any]]:
    out_dir = storage_root / "frames" / str(case_id) / str(upload_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene_signals = detect_scene_change_times(storage_path, duration_sec)
    scene_times = scene_signals.get("event_times") if isinstance(scene_signals.get("event_times"), list) else []
    times = frame_times_for_duration(duration_sec, event_times=scene_times)
    frames: list[dict[str, Any]] = []
    for idx, time_sec in enumerate(times, start=1):
        output = out_dir / f"frame_{idx}.jpg"
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            str(max(0.0, time_sec)),
            "-i",
            storage_path,
            "-frames:v",
            "1",
            "-vf",
            "scale=960:-2",
            "-q:v",
            "4",
            str(output),
        ]
        proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if proc.returncode == 0 and output.exists():
            frames.append({
                "path": str(output),
                "time_sec": time_sec,
                "role": _frame_role(idx, len(times), time_sec, scene_times),
                "selection_reason": _selection_reason(time_sec, scene_times),
            })
    return frames


def extract_frames(
    storage_path: str,
    case_id: str,
    upload_id: str,
    duration_sec: float | None,
    storage_root: Path,
) -> list[str]:
    return [item["path"] for item in extract_event_frames(storage_path, case_id, upload_id, duration_sec, storage_root)]


def summarize_frame_selection(frame_details: list[dict[str, Any]]) -> dict[str, Any]:
    role_counts: dict[str, int] = {}
    reason_counts: dict[str, int] = {}
    for frame in frame_details:
        role = str(frame.get("role") or "unknown")
        reason = str(frame.get("selection_reason") or "unknown")
        role_counts[role] = role_counts.get(role, 0) + 1
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
    return {
        "strategy": "scene-change-prioritized-object-first-frame-selection",
        "frame_count": len(frame_details),
        "role_counts": role_counts,
        "reason_counts": reason_counts,
        "accident_candidate_count": role_counts.get("accident_candidate", 0),
        "event_context_count": role_counts.get("event_context", 0),
    }


def _frame_role(index: int, count: int, time_sec: float | None = None, event_times: list[float] | None = None) -> str:
    if index == 1:
        return "start_context"
    if index == count:
        return "end_context"
    if time_sec is not None and _near_any_event(float(time_sec), event_times or [], tolerance=1.25):
        return "accident_candidate"
    if time_sec is not None and _near_any_event(float(time_sec), event_times or [], tolerance=4.0):
        return "event_context"
    return "time_sequence"


def _selection_reason(time_sec: float, event_times: list[float]) -> str:
    if _near_any_event(time_sec, event_times, tolerance=1.25):
        return "near_scene_change_accident_candidate"
    if _near_any_event(time_sec, event_times, tolerance=4.0):
        return "near_scene_change_context"
    return "representative_time_context"


def _near_any_event(time_sec: float, event_times: list[float], *, tolerance: float) -> bool:
    return any(abs(time_sec - event_time) <= tolerance for event_time in event_times)
