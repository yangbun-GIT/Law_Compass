import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VIDEO_PREPROCESS_CONTRACT_VERSION = "worker-video-preprocess-v1"


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


def frame_times_for_duration(duration_sec: float | None, max_frames: int = 18) -> list[float]:
    duration = max(0.5, float(duration_sec or 8.0))
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


def extract_event_frames(
    storage_path: str,
    case_id: str,
    upload_id: str,
    duration_sec: float | None,
    storage_root: Path,
) -> list[dict[str, Any]]:
    out_dir = storage_root / "frames" / str(case_id) / str(upload_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    times = frame_times_for_duration(duration_sec)
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
                "role": _frame_role(idx, len(times)),
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


def _frame_role(index: int, count: int) -> str:
    if index == 1:
        return "start_context"
    if index == count:
        return "end_context"
    return "time_sequence"
