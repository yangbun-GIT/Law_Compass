import json
import os
import random
import subprocess
import time
import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
import redis
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
STREAM_KEY = os.getenv("REDIS_STREAM_KEY", "jobs:v1:stream")
GROUP = os.getenv("REDIS_STREAM_GROUP", "worker-group")
CONSUMER = f"worker-{os.getpid()}"
DB_URL = os.getenv("DATABASE_URL", "")
INTERNAL_AGENT_URL = os.getenv("INTERNAL_AGENT_URL", "http://agent:8000")
INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "")
STORAGE_ROOT = Path(os.getenv("LOCAL_STORAGE_ROOT", "/app/storage"))
VIDEO_PREPROCESS_CONTRACT_VERSION = "worker-video-preprocess-v1"
FRAME_ANALYSIS_CONTRACT_VERSION = "openai-frame-analysis-v1"
ENABLE_OPENAI_FRAME_ANALYSIS = os.getenv("ENABLE_OPENAI_FRAME_ANALYSIS", "0") == "1"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
OPENAI_TIMEOUT_SEC = float(os.getenv("OPENAI_TIMEOUT_SEC", "18"))
OPENAI_FRAME_ANALYSIS_MAX_FRAMES = max(1, int(os.getenv("OPENAI_FRAME_ANALYSIS_MAX_FRAMES", "8")))
OPENAI_FRAME_ANALYSIS_DETAIL = os.getenv("OPENAI_FRAME_ANALYSIS_DETAIL", "low")

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def init_group():
    try:
        r.xgroup_create(STREAM_KEY, GROUP, id="0", mkstream=True)
    except redis.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def now_iso():
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


def frame_times_for_duration(duration_sec: float | None, max_frames: int = 12) -> list[float]:
    duration = max(0.5, float(duration_sec or 8.0))
    if duration <= 5:
        interval = 0.5
    elif duration <= 10:
        interval = 0.75
    elif duration <= 30:
        interval = 1.0
    else:
        interval = max(1.5, duration / 24)
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


def extract_event_frames(storage_path: str, case_id: str, upload_id: str, duration_sec: float | None) -> list[dict[str, Any]]:
    out_dir = STORAGE_ROOT / "frames" / str(case_id) / str(upload_id)
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


def extract_frames(storage_path: str, case_id: str, upload_id: str, duration_sec: float | None) -> list[str]:
    return [item["path"] for item in extract_event_frames(storage_path, case_id, upload_id, duration_sec)]


def _frame_role(index: int, count: int) -> str:
    if index == 1:
        return "start_context"
    if index == count:
        return "end_context"
    return "time_sequence"


def analyze_frames_with_openai(frame_details: list[dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    if not ENABLE_OPENAI_FRAME_ANALYSIS:
        return {"version": FRAME_ANALYSIS_CONTRACT_VERSION, "enabled": False, "reason": "ENABLE_OPENAI_FRAME_ANALYSIS is not 1"}
    if not OPENAI_API_KEY:
        return {"version": FRAME_ANALYSIS_CONTRACT_VERSION, "enabled": False, "reason": "OPENAI_API_KEY is empty"}
    selected_frames = _select_openai_frames(frame_details, OPENAI_FRAME_ANALYSIS_MAX_FRAMES)
    if not selected_frames:
        return {"version": FRAME_ANALYSIS_CONTRACT_VERSION, "enabled": False, "reason": "no frames extracted"}
    content: list[dict[str, Any]] = [{
        "type": "input_text",
        "text": (
            "You are extracting observable traffic accident facts from dashcam frame sequence images. "
            "Return JSON only. Do not decide legal liability, insurance responsibility, or fault ratio. "
            "Use unknown and low confidence when a fact is not clearly visible. "
            "Allowed observation fields: stopped, sudden_brake, impact_direction, collision_direction, "
            "opponent_behavior, lane_change_actor, turn_signal, user_signal, opponent_signal, "
            "opponent_signal_violation, crosswalk_nearby, school_zone, damage_level. "
            "Do not infer injury status from frames. Do not infer absence facts such as no damage, no school zone, "
            "or no signal violation just because they are not visible. Omit fields that are not observable. "
            "Each observation must include field, value, confidence between 0 and 1, frame_refs, and reason. "
            f"Context JSON: {json.dumps(_compact_context(context), ensure_ascii=False)}"
        ),
    }]
    for frame in selected_frames:
        content.append({
            "type": "input_text",
            "text": f"frame_ref={Path(frame['path']).name}, time_sec={frame.get('time_sec')}, role={frame.get('role')}",
        })
        content.append({
            "type": "input_image",
            "image_url": _image_data_url(Path(frame["path"])),
            "detail": OPENAI_FRAME_ANALYSIS_DETAIL,
        })
    payload = {
        "model": OPENAI_VISION_MODEL,
        "temperature": 0,
        "max_output_tokens": 1400,
        "text": {"format": {"type": "json_object"}},
        "input": [{"role": "user", "content": content}],
    }
    try:
        data = requests_post_json(
            "https://api.openai.com/v1/responses",
            payload,
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            timeout=OPENAI_TIMEOUT_SEC,
        )
        parsed = _safe_json_loads(_openai_output_text(data)) or {}
        observations = _normalize_openai_observations(parsed.get("observations") or parsed.get("detected_events") or [], selected_frames)
        result = {
            "version": FRAME_ANALYSIS_CONTRACT_VERSION,
            "enabled": True,
            "provider": "openai",
            "model": OPENAI_VISION_MODEL,
            "detail": OPENAI_FRAME_ANALYSIS_DETAIL,
            "response_id": data.get("id"),
            "analyzed_frames": [_public_frame_ref(frame) for frame in selected_frames],
            "summary": parsed.get("summary") or parsed.get("scene_summary"),
            "observations": observations,
            "uncertainties": parsed.get("uncertainties") or [],
            "created_at": now_iso(),
        }
        print(json.dumps({
            "event": "openai_frame_analysis",
            "model": result["model"],
            "frames": len(selected_frames),
            "observations": observations,
            "summary": result["summary"],
        }, ensure_ascii=False))
        return result
    except Exception as exc:
        return {
            "version": FRAME_ANALYSIS_CONTRACT_VERSION,
            "enabled": True,
            "provider": "openai",
            "model": OPENAI_VISION_MODEL,
            "error": str(exc),
            "analyzed_frames": [_public_frame_ref(frame) for frame in selected_frames],
            "observations": [],
            "created_at": now_iso(),
        }


def _select_openai_frames(frame_details: list[dict[str, Any]], max_frames: int) -> list[dict[str, Any]]:
    frames = [frame for frame in frame_details if frame.get("path") and Path(frame["path"]).exists()]
    if len(frames) <= max_frames:
        return frames
    if max_frames == 1:
        return [frames[len(frames) // 2]]
    return [frames[round(idx * (len(frames) - 1) / (max_frames - 1))] for idx in range(max_frames)]


def _image_data_url(path: Path) -> str:
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{data}"


def _compact_context(context: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in context.items() if value not in (None, "", [], {})}


def _public_frame_ref(frame: dict[str, Any]) -> dict[str, Any]:
    return {
        "frame_ref": Path(str(frame.get("path", ""))).name,
        "time_sec": frame.get("time_sec"),
        "role": frame.get("role"),
    }


def _openai_output_text(data: dict[str, Any]) -> str:
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    parts: list[str] = []
    for item in data.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if isinstance(content, dict) and content.get("type") == "output_text":
                parts.append(str(content.get("text") or ""))
    return "\n".join(parts)


def _safe_json_loads(raw: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(raw or "{}")
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _normalize_openai_observations(raw_observations: Any, selected_frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(raw_observations, list):
        return []
    allowed_frame_refs = {Path(frame["path"]).name for frame in selected_frames}
    observations: list[dict[str, Any]] = []
    for item in raw_observations:
        if not isinstance(item, dict):
            continue
        field = str(item.get("field") or item.get("name") or item.get("type") or "").strip()
        if not field:
            continue
        value = item.get("value", "unknown")
        if _should_drop_openai_observation(field, value):
            continue
        frame_refs = [str(ref) for ref in item.get("frame_refs") or item.get("frames") or [] if str(ref) in allowed_frame_refs]
        observations.append({
            "field": field,
            "value": value,
            "confidence": _as_float(item.get("confidence"), 0.0),
            "source": "frame_analysis:openai",
            "detector": OPENAI_VISION_MODEL,
            "frame_refs": frame_refs,
            "reason": str(item.get("reason") or item.get("evidence") or ""),
        })
    return observations


def _should_drop_openai_observation(field: str, value: Any) -> bool:
    text = str(value).strip().lower()
    if text in {"", "unknown", "unclear", "not_visible", "not visible", "none"}:
        return True
    if field == "injury":
        return True
    if field == "damage_level" and text in {"none", "no_damage", "no damage"}:
        return True
    if value is False and field in {
        "opponent_signal_violation",
        "crosswalk_nearby",
        "school_zone",
        "turn_signal",
        "user_signal",
        "opponent_signal",
    }:
        return True
    return False


def _as_float(value: Any, default: float) -> float:
    try:
        number = float(value)
        return max(0.0, min(1.0, number))
    except (TypeError, ValueError):
        return default


def requests_post_json(url: str, payload: dict, headers: dict[str, str] | None = None, timeout: float = 25):
    import urllib.request

    request_headers = {"Content-Type": "application/json", **(headers or {})}
    if url.startswith(INTERNAL_AGENT_URL):
        request_headers = {**request_headers, "x-internal-token": INTERNAL_SERVICE_TOKEN}
    req = urllib.request.Request(
        url,
        method="POST",
        headers=request_headers,
        data=json.dumps(payload).encode("utf-8"),
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


@retry(stop=stop_after_attempt(5), wait=wait_exponential_jitter(initial=1, max=30))
def process_job(job_id: str, job_type: str):
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE jobs SET status='running', attempts=attempts+1, attempt=attempts+1, started_at=now() WHERE id=%s", (job_id,))
            cur.execute("SELECT id, case_id, upload_id, owner_user_id, payload FROM jobs WHERE id=%s", (job_id,))
            row = cur.fetchone()
            if not row:
                return
            payload = row[4] or {}

            if job_type == "video_preprocess":
                storage_path = payload.get("storage_path")
                cur.execute("SELECT storage_path FROM uploads WHERE id=%s", (row[2],))
                up = cur.fetchone()
                storage_path = storage_path or (up[0] if up else None)
                if not storage_path:
                    raise RuntimeError("storage_path missing")

                metadata = probe_video(storage_path)
                frame_details = extract_event_frames(storage_path, str(row[1]), str(row[2]), metadata.get("duration_sec"))
                frames = [item["path"] for item in frame_details]
                openai_frame_analysis = analyze_frames_with_openai(
                    frame_details,
                    {
                        "case_id": str(row[1]),
                        "upload_id": str(row[2]),
                        "duration_sec": metadata.get("duration_sec"),
                        "width": metadata.get("width"),
                        "height": metadata.get("height"),
                        "fps": metadata.get("fps"),
                    },
                )
                metadata["representative_frames"] = frames
                metadata["representative_frame_details"] = frame_details
                metadata["openai_frame_analysis"] = openai_frame_analysis
                metadata["observations"] = openai_frame_analysis.get("observations") or []
                metadata["preprocess_summary"] = (
                    f"Local video verified. duration={metadata.get('duration_sec')}s, "
                    f"resolution={metadata.get('width')}x{metadata.get('height')}, frames={len(frames)}, "
                    f"frame_observations={len(metadata['observations'])}."
                )
                frame_dir = str(STORAGE_ROOT / "frames" / str(row[1]) / str(row[2]))
                artifacts = {
                    "video_preprocess_contract_version": VIDEO_PREPROCESS_CONTRACT_VERSION,
                    "duration_sec": metadata.get("duration_sec"),
                    "width": metadata.get("width"),
                    "height": metadata.get("height"),
                    "fps": metadata.get("fps"),
                    "codec": metadata.get("codec"),
                    "extracted_frame_paths": frames,
                    "representative_frame_details": frame_details,
                    "openai_frame_analysis": openai_frame_analysis,
                    "preprocess_summary": metadata["preprocess_summary"],
                }
                cur.execute(
                    """
                    UPDATE uploads
                    SET status='processing',
                        metadata = metadata || %s::jsonb,
                        frame_dir=%s,
                        preprocess_summary=%s
                    WHERE id=%s
                    """,
                    (json.dumps(metadata), frame_dir, metadata["preprocess_summary"], row[2]),
                )
                time.sleep(random.uniform(0.1, 0.4))
                cur.execute("UPDATE uploads SET status='ready', derived_path=%s WHERE id=%s", (frame_dir, row[2]))
                cur.execute("UPDATE jobs SET status='succeeded', artifacts=%s, finished_at=now() WHERE id=%s", (json.dumps(artifacts), job_id))

                cur.execute(
                    """
                    SELECT c.structured_facts, c.selected_keywords, c.analysis_mode
                    FROM cases c WHERE c.id=%s
                    """,
                    (row[1],),
                )
                case_inputs = cur.fetchone()
                analyze_payload = {
                    "case_id": str(row[1]),
                    "upload_id": str(row[2]),
                    "ai_profile": payload.get("ai_profile", "default_vehicle_collision"),
                    "specialist_roles": payload.get("specialist_roles", []),
                    "routing_reason": "auto_after_local_preprocess",
                    "structured_facts": (case_inputs[0] if case_inputs else {}) or {},
                    "selected_keywords": list(case_inputs[1] if case_inputs and case_inputs[1] else []),
                    "analysis_mode": (case_inputs[2] if case_inputs else None) or "quick_summary",
                }
                cur.execute(
                    """
                    INSERT INTO jobs(case_id, upload_id, owner_user_id, type, status, payload)
                    VALUES(%s,%s,%s,'video_analyze','queued',%s)
                    RETURNING id
                    """,
                    (row[1], row[2], row[3], json.dumps(analyze_payload)),
                )
                analyze_job_id = str(cur.fetchone()[0])
                r.xadd(STREAM_KEY, {"job_id": analyze_job_id, "job_type": "video_analyze"}, maxlen=10000, approximate=True)

            elif job_type == "video_analyze":
                ai_profile = payload.get("ai_profile", "default_vehicle_collision")
                specialist_roles = payload.get("specialist_roles", [])
                structured_facts = payload.get("structured_facts") or {}
                selected_keywords = payload.get("selected_keywords") or []
                analysis_mode = payload.get("analysis_mode") or "quick_summary"
                routing_reason = payload.get("routing_reason")

                cur.execute("SELECT title, description_text FROM cases WHERE id=%s", (row[1],))
                case_row = cur.fetchone()
                case_text = f"{case_row[0] or ''} {case_row[1] or ''}".strip() if case_row else ""

                cur.execute("SELECT metadata, file_name, status FROM uploads WHERE id=%s", (row[2],))
                up = cur.fetchone()
                metadata = up[0] if up and isinstance(up[0], dict) else {}
                payload_video_metadata = payload.get("video_metadata") if isinstance(payload.get("video_metadata"), dict) else {}
                preprocessed_summary = metadata.get("preprocess_summary") or "Local video metadata is available for analysis."
                video_metadata = {
                    "preprocess_contract_version": VIDEO_PREPROCESS_CONTRACT_VERSION,
                    "upload_status": up[2] if up else None,
                    "file_name": up[1] if up else None,
                    "metadata": metadata,
                    "preprocess_payload": payload_video_metadata,
                }
                merged_summary = " ".join(
                    x
                    for x in [
                        preprocessed_summary,
                        case_text,
                        " ".join(selected_keywords),
                        json.dumps(structured_facts, ensure_ascii=False),
                        f"routing_reason:{routing_reason}" if routing_reason else "",
                    ]
                    if x
                )
                response = requests_post_json(
                    f"{INTERNAL_AGENT_URL}/internal/v1/analyze/video",
                    {
                        "case_id": str(row[1]),
                        "user_id": str(row[3]),
                        "upload_id": str(row[2]),
                        "preprocessed_summary": merged_summary,
                        "ai_profile": ai_profile,
                        "specialist_roles": specialist_roles,
                        "video_metadata": video_metadata,
                        "structured_facts": structured_facts,
                        "selected_keywords": selected_keywords,
                        "analysis_mode": analysis_mode,
                    },
                )
                cur.execute("SELECT COALESCE(MAX(version),0)+1 FROM analysis_results WHERE case_id=%s", (row[1],))
                version = cur.fetchone()[0]
                cur.execute(
                    """
                    INSERT INTO analysis_results(
                        case_id, owner_user_id, version, source_type, result, evidence, uncertainty, model_info,
                        structured_facts, recommended_keywords, suggested_next_inputs, report_payload, elderly_friendly_report,
                        legal_analysis, scenario_type, used_evidence_ids, legal_risk_flags, persona_outputs, evidence_audit
                    )
                    VALUES(%s,%s,%s,'video',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id
                    """,
                    (
                        row[1],
                        row[3],
                        version,
                        json.dumps(response),
                        json.dumps(response.get("evidence", [])),
                        json.dumps(response.get("uncertainty", {})),
                        json.dumps(response.get("model_info", {})),
                        json.dumps(response.get("structured_facts", {})),
                        json.dumps(response.get("recommended_keywords", [])),
                        json.dumps(response.get("suggested_next_inputs", [])),
                        json.dumps({}),
                        json.dumps(response.get("elderly_friendly_report", {})),
                        json.dumps(response.get("legal_analysis", {})),
                        response.get("scenario_type"),
                        json.dumps([x.get("chunk_id") for x in response.get("evidence", []) if x.get("chunk_id")]),
                        json.dumps((response.get("legal_liability", {}) or {}).get("risk_flags", []) or (response.get("legal_analysis", {}) or {}).get("risk_flags", [])),
                        json.dumps({"analysts": response.get("recommended_specialists", [])}),
                        json.dumps(response.get("evidence_audit", {})),
                    ),
                )
                result_id = cur.fetchone()[0]
                cur.execute("UPDATE cases SET status='completed', latest_result_id=%s WHERE id=%s", (result_id, row[1]))
                cur.execute("UPDATE jobs SET status='succeeded', finished_at=now() WHERE id=%s", (job_id,))

            conn.commit()


def mark_failed(job_id: str, err: Exception):
    try:
        with psycopg.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE jobs
                    SET status = (CASE WHEN attempts >= max_attempts THEN 'dead' ELSE 'failed' END)::job_status,
                        error_info = jsonb_build_object('message', %s, 'at', now()),
                        last_error = %s,
                        next_run_at = now() + interval '5 minutes',
                        updated_at = now()
                    WHERE id=%s
                    """,
                    (str(err), str(err), job_id),
                )
                conn.commit()
    except Exception:
        pass


def main_loop():
    init_group()
    while True:
        entries = r.xreadgroup(groupname=GROUP, consumername=CONSUMER, streams={STREAM_KEY: ">"}, count=1, block=5000)
        if not entries:
            continue

        for _, messages in entries:
            for msg_id, fields in messages:
                job_id = fields.get("job_id")
                job_type = fields.get("job_type")
                try:
                    process_job(job_id, job_type)
                    r.xack(STREAM_KEY, GROUP, msg_id)
                    r.setex(f"job:v1:{job_id}:status", 300, json.dumps({"status": "succeeded", "at": now_iso()}))
                except Exception as exc:
                    mark_failed(job_id, exc)
                    time.sleep(min(8.0, 2 ** random.randint(0, 3) + random.random()))
                    r.xack(STREAM_KEY, GROUP, msg_id)
                    r.setex(f"job:v1:{job_id}:status", 300, json.dumps({"status": "failed", "error": str(exc), "at": now_iso()}))


if __name__ == "__main__":
    main_loop()
