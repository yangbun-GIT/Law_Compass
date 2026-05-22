import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import redis
from tenacity import retry, stop_after_attempt, wait_exponential_jitter
from worker.frame_analysis import analyze_frames_with_openai
from worker.video_preprocess import VIDEO_PREPROCESS_CONTRACT_VERSION, extract_event_frames, probe_video

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
STREAM_KEY = os.getenv("REDIS_STREAM_KEY", "jobs:v1:stream")
GROUP = os.getenv("REDIS_STREAM_GROUP", "worker-group")
CONSUMER = f"worker-{os.getpid()}"
DB_URL = os.getenv("DATABASE_URL", "")
INTERNAL_AGENT_URL = os.getenv("INTERNAL_AGENT_URL", "http://agent:8000")
INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "")
STORAGE_ROOT = Path(os.getenv("LOCAL_STORAGE_ROOT", "/app/storage"))

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def init_group():
    try:
        r.xgroup_create(STREAM_KEY, GROUP, id="0", mkstream=True)
    except redis.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def now_iso():
    return datetime.now(timezone.utc).isoformat()


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
                frame_details = extract_event_frames(storage_path, str(row[1]), str(row[2]), metadata.get("duration_sec"), STORAGE_ROOT)
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
