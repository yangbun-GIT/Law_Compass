from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def run_json(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, capture_output=True, text=True, check=True)
    return json.loads(completed.stdout or "{}")


def write_summary(out_dir: Path, payload: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract local video metadata and review frames for a LawCompass case.")
    parser.add_argument("video", help="Absolute path to the local video file.")
    parser.add_argument("--case-name", default="", help="Human-friendly case name for the summary.")
    parser.add_argument("--out", default="logs/video_debug", help="Output directory for metadata and extracted frames.")
    parser.add_argument("--every-sec", type=float, default=1.0, help="Frame extraction interval in seconds.")
    args = parser.parse_args()

    video_path = Path(args.video)
    out_root = Path(args.out)
    case_slug = args.case_name or video_path.stem
    out_dir = out_root / "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in case_slug)

    if not video_path.exists():
        write_summary(out_dir, {"status": "missing_video", "video": str(video_path)})
        return 2

    ffprobe = shutil.which("ffprobe")
    ffmpeg = shutil.which("ffmpeg")
    if not ffprobe or not ffmpeg:
        write_summary(
            out_dir,
            {
                "status": "missing_ffmpeg",
                "video": str(video_path),
                "case_name": case_slug,
                "message": "ffmpeg and ffprobe must be available on PATH to extract frames.",
                "ffmpeg": ffmpeg,
                "ffprobe": ffprobe,
            },
        )
        return 2

    metadata = run_json(
        [
            ffprobe,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(video_path),
        ]
    )
    frame_dir = out_dir / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-vf",
            f"fps=1/{max(args.every_sec, 0.1)}",
            str(frame_dir / "frame_%05d.jpg"),
        ],
        check=True,
    )
    frames = sorted(frame_dir.glob("*.jpg"))
    write_summary(
        out_dir,
        {
            "status": "ok",
            "video": str(video_path),
            "case_name": case_slug,
            "metadata": metadata,
            "frame_count": len(frames),
            "frame_dir": str(frame_dir),
            "review_contract": {
                "must_confirm": [
                    "direct_contact_with_ego",
                    "ego_collision_confirmed",
                    "opponent_single_fall",
                    "ego_kept_right",
                    "opponent_failed_keep_right",
                    "road_width_m",
                ],
                "must_not_infer_from_filename": True,
            },
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
