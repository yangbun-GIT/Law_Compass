import json
import os
import random
import shutil
import time
from pathlib import Path
from typing import Any

try:
    from tenacity import retry, stop_after_attempt, wait_exponential_jitter
except ModuleNotFoundError:
    def retry(*_args: Any, **_kwargs: Any):
        def decorator(fn: Any) -> Any:
            return fn

        return decorator

    def stop_after_attempt(_attempts: int) -> None:
        return None

    def wait_exponential_jitter(*_args: Any, **_kwargs: Any) -> None:
        return None

from worker.frame_analysis import analyze_frames_with_openai
from worker.storage.base import frame_key
from worker.storage.factory import create_storage_adapter
from worker.video_preprocess import VIDEO_PREPROCESS_CONTRACT_VERSION, extract_event_frames, probe_video, summarize_frame_selection
from worker.yolo_frame_analysis import analyze_frames_with_yolo, rank_frame_details_by_yolo

STREAM_KEY = os.getenv("REDIS_STREAM_KEY", "jobs:v1:stream")
DB_URL = os.getenv("DATABASE_URL", "")
INTERNAL_AGENT_URL = os.getenv("INTERNAL_AGENT_URL", "http://agent:8000")
INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "")
LOCAL_VIDEO_CACHE_DIR = Path(os.getenv("LOCAL_VIDEO_CACHE_DIR", "/app/storage/cache"))
NON_VEHICLE_TARGETS = {"pedestrian", "bicycle", "motorcycle", "object"}
DIRECT_TARGET_FIELDS = {"direct_collision_partner_type", "collision_partner_type"}
USER_JOB_LABELS = {
    "video_preprocess": "영상 확인 중",
    "video_analyze": "사고 장면 분석 중",
}
USER_STATUS_LABELS = {
    "queued": "대기 중",
    "running": "분석 중",
    "retrying": "다시 확인 중",
    "succeeded": "완료",
    "failed": "분석 실패. 다시 시도해 주세요.",
}


def user_facing_job_status(job_type: str, status: str) -> dict[str, str]:
    return {
        "job_label": USER_JOB_LABELS.get(job_type, "분석 준비 중"),
        "status_label": USER_STATUS_LABELS.get(status, "상태를 확인하고 있습니다."),
    }


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
def process_job(job_id: str, job_type: str, redis_client: Any) -> None:
    import psycopg

    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE jobs SET status='running', attempts=attempts+1, attempt=attempts+1, started_at=now() WHERE id=%s", (job_id,))
            cur.execute("SELECT id, case_id, upload_id, owner_user_id, payload FROM jobs WHERE id=%s", (job_id,))
            row = cur.fetchone()
            if not row:
                return
            payload = row[4] or {}

            if job_type == "video_preprocess":
                _process_video_preprocess(cur, row, payload, redis_client)
            elif job_type == "video_analyze":
                _process_video_analyze(cur, row, payload, job_id)

            conn.commit()


def _process_video_preprocess(cur: Any, row: tuple[Any, ...], payload: dict[str, Any], redis_client: Any) -> None:
    storage_path = payload.get("storage_path")
    storage_key = payload.get("storage_key")
    storage_driver = payload.get("storage_driver") or payload.get("storage_provider")
    cur.execute("SELECT storage_provider, storage_driver, storage_key, storage_path FROM uploads WHERE id=%s", (row[2],))
    up = cur.fetchone()
    if up:
        storage_driver = storage_driver or up[1] or up[0]
        storage_key = storage_key or up[2]
        storage_path = storage_path or up[3]
    storage_driver = storage_driver or "local"
    storage_adapter = create_storage_adapter(storage_driver)
    local_video_path: Path | None = None
    local_frame_dir = str(LOCAL_VIDEO_CACHE_DIR / "frames" / str(row[1]) / str(row[2]))
    cleanup_video = False
    try:
        local_video_path, cleanup_video = _materialize_video_for_processing(storage_adapter, storage_driver, storage_key, storage_path, str(row[1]), str(row[2]))

        metadata = probe_video(str(local_video_path))
        frame_details = extract_event_frames(str(local_video_path), str(row[1]), str(row[2]), metadata.get("duration_sec"), LOCAL_VIDEO_CACHE_DIR)
        cur.execute(
            """
            SELECT c.structured_facts, c.selected_keywords, c.analysis_mode
            FROM cases c WHERE c.id=%s
            """,
            (row[1],),
        )
        case_inputs = cur.fetchone()
        frame_analysis_context = build_frame_analysis_context(row, metadata, case_inputs)
        yolo_frame_analysis = analyze_frames_with_yolo(frame_details, frame_analysis_context)
        frame_analysis_context["vision_object_inventory"] = _compact_yolo_context(yolo_frame_analysis)
        frame_details = rank_frame_details_by_yolo(frame_details, yolo_frame_analysis)
        frame_selection_summary = summarize_frame_selection(frame_details)
        openai_frame_analysis = analyze_frames_with_openai(frame_details, frame_analysis_context)
        frame_observations = _merge_frame_observations(openai_frame_analysis, yolo_frame_analysis)
        frame_details = _persist_processed_frames(storage_adapter, frame_details, str(row[1]), str(row[2]))
        frames = [item.get("storage_key") or item["path"] for item in frame_details]
        metadata["representative_frames"] = frames
        metadata["representative_frame_details"] = frame_details
        metadata["frame_selection_summary"] = frame_selection_summary
        metadata["openai_frame_analysis"] = openai_frame_analysis
        metadata["yolo_frame_analysis"] = yolo_frame_analysis
        metadata["observations"] = frame_observations
        metadata["preprocess_summary"] = (
            f"Local video verified. duration={metadata.get('duration_sec')}s, "
            f"resolution={metadata.get('width')}x{metadata.get('height')}, frames={len(frames)}, "
            f"frame_observations={len(frame_observations)}, "
            f"openai_observations={len(openai_frame_analysis.get('observations') or [])}, "
            f"yolo_observations={len(yolo_frame_analysis.get('observations') or [])}."
        )
        frame_dir = f"processed/frames/{row[1]}/{row[2]}"
        artifacts = {
            "user_facing_status": user_facing_job_status("video_preprocess", "succeeded"),
            "video_preprocess_contract_version": VIDEO_PREPROCESS_CONTRACT_VERSION,
            "storage_driver": storage_driver,
            "source_storage_key": storage_key,
            "processed_frames_key": frame_dir,
            "duration_sec": metadata.get("duration_sec"),
            "width": metadata.get("width"),
            "height": metadata.get("height"),
            "fps": metadata.get("fps"),
            "codec": metadata.get("codec"),
            "extracted_frame_paths": frames,
            "representative_frame_details": frame_details,
            "frame_selection_summary": frame_selection_summary,
            "openai_frame_analysis": openai_frame_analysis,
            "yolo_frame_analysis": yolo_frame_analysis,
            "observations": frame_observations,
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
        cur.execute("UPDATE jobs SET status='succeeded', artifacts=%s, finished_at=now() WHERE id=%s", (json.dumps(artifacts), row[0]))
        if payload.get("auto_analyze_after_preprocess", True) is not False:
            _enqueue_video_analyze_job(cur, row, payload, redis_client, case_inputs)
    finally:
        if local_video_path is not None:
            _cleanup_processing_cache(cleanup_video, local_video_path, local_frame_dir)


def _materialize_video_for_processing(
    storage_adapter: Any,
    storage_driver: str,
    storage_key: str | None,
    storage_path: str | None,
    case_id: str,
    upload_id: str,
) -> tuple[Path, bool]:
    if storage_driver == "local" and storage_path and Path(storage_path).exists():
        return Path(storage_path), False
    if not storage_key:
        raise FileNotFoundError("stored video reference missing")
    local_target = LOCAL_VIDEO_CACHE_DIR / "uploads" / case_id / upload_id / Path(storage_key).name
    storage_adapter.get_file(storage_key, local_target)
    return local_target, True


def _persist_processed_frames(storage_adapter: Any, frame_details: list[dict[str, Any]], case_id: str, upload_id: str) -> list[dict[str, Any]]:
    persisted: list[dict[str, Any]] = []
    for item in frame_details:
        local_path = Path(str(item.get("path") or ""))
        if not local_path.exists():
            continue
        key = frame_key(case_id, upload_id, local_path.name)
        stored = storage_adapter.put_file(local_path, key, {"mime_type": "image/jpeg"})
        persisted.append({
            **item,
            "local_cache_path": str(local_path),
            "path": stored.get("storage_key") or key,
            "storage_driver": stored.get("storage_driver"),
            "storage_key": stored.get("storage_key") or key,
            "storage_path": stored.get("storage_path"),
        })
    return persisted


def _cleanup_processing_cache(cleanup_video: bool, local_video_path: Path, local_frame_dir: str) -> None:
    if cleanup_video:
        local_video_path.unlink(missing_ok=True)
    shutil.rmtree(local_frame_dir, ignore_errors=True)


def _merge_frame_observations(*analysis_payloads: dict[str, Any]) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for payload in analysis_payloads:
        if not isinstance(payload, dict):
            continue
        for item in payload.get("observations") or []:
            if isinstance(item, dict):
                observations.append(item)
    return _sanitize_merged_frame_observations(observations)


def _sanitize_merged_frame_observations(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    observations = _augment_pedestrian_visibility_target_candidates(observations)
    non_vehicle_candidate_targets = {
        _canonical_target(item.get("value"))
        for item in observations
        if str(item.get("field") or "") == "primary_collision_target"
        and str(item.get("value") or "").strip().lower().replace("-", "_").endswith("_candidate")
        and _canonical_target(item.get("value")) in NON_VEHICLE_TARGETS
        and _as_float(item.get("confidence")) >= 0.3
    }
    yolo_sequence_direct_targets = {
        _canonical_target(item.get("value"))
        for item in observations
        if str(item.get("source") or "").strip().lower() == "vision_model:yolo_sequence"
        and str(item.get("field") or "") in DIRECT_TARGET_FIELDS
        and _canonical_target(item.get("value")) in NON_VEHICLE_TARGETS
        and _frame_ref_count(item) >= 2
        and _as_float(item.get("confidence")) >= 0.76
    }
    sanitized: list[dict[str, Any]] = []
    for item in observations:
        field = str(item.get("field") or "")
        source = str(item.get("source") or "").strip().lower()
        target = _canonical_target(item.get("value"))
        raw_value = str(item.get("value") or "").strip().lower().replace("-", "_")
        if (
            source.startswith("frame_analysis")
            and target == "vehicle"
            and non_vehicle_candidate_targets
            and (field in DIRECT_TARGET_FIELDS or (field == "primary_collision_target" and not raw_value.endswith("_candidate")))
        ):
            sanitized.append(_demote_to_target_candidate(item, target, "openai_vehicle_direct_demoted_due_non_vehicle_target_candidate"))
            continue
        if source.startswith("frame_analysis") and target in NON_VEHICLE_TARGETS and target not in yolo_sequence_direct_targets:
            if field in DIRECT_TARGET_FIELDS:
                sanitized.append(_demote_to_target_candidate(item, target, "openai_direct_non_vehicle_requires_yolo_sequence_support"))
                continue
            if field == "primary_collision_target" and not str(item.get("value") or "").strip().lower().endswith("_candidate"):
                sanitized.append(_demote_to_target_candidate(item, target, "openai_non_vehicle_primary_requires_yolo_sequence_support"))
                continue
        sanitized.append(item)
    return _dedupe_observations(sanitized)


def _augment_pedestrian_visibility_target_candidates(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    has_pedestrian_target_candidate = any(
        str(item.get("field") or "") == "primary_collision_target"
        and _canonical_target(item.get("value")) == "pedestrian"
        for item in observations
    )
    if has_pedestrian_target_candidate:
        return observations
    augmented = list(observations)
    for item in observations:
        if str(item.get("field") or "") != "pedestrian_visible" or item.get("value") is not True:
            continue
        if _as_float(item.get("confidence")) < 0.85 or _frame_ref_count(item) < 3:
            continue
        augmented.append(_pedestrian_visibility_target_candidate(item))
        break
    return augmented


def _pedestrian_visibility_target_candidate(item: dict[str, Any]) -> dict[str, Any]:
    reason = str(item.get("reason") or "")
    reason_code = "pedestrian_visible_requires_collision_target_verification"
    next_reason = f"{reason}; {reason_code}" if reason else reason_code
    return {
        **item,
        "field": "primary_collision_target",
        "value": "pedestrian_candidate",
        "confidence": round(min(_as_float(item.get("confidence")), 0.68), 4),
        "reason": next_reason,
    }


def _demote_to_target_candidate(item: dict[str, Any], target: str, reason_code: str) -> dict[str, Any]:
    reason = str(item.get("reason") or "")
    next_reason = f"{reason}; {reason_code}" if reason else reason_code
    return {
        **item,
        "field": "primary_collision_target",
        "value": f"{target}_candidate",
        "confidence": round(min(_as_float(item.get("confidence")), 0.69), 4),
        "reason": next_reason,
    }


def _dedupe_observations(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str, tuple[str, ...], str]] = set()
    for item in observations:
        refs = tuple(str(ref) for ref in item.get("frame_refs") or [] if ref)
        key = (
            str(item.get("field") or ""),
            str(item.get("value") or ""),
            refs,
            str(item.get("source") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _canonical_target(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if text.endswith("_candidate"):
        text = text[: -len("_candidate")]
    if any(token in text for token in ("pedestrian", "person")):
        return "pedestrian"
    if any(token in text for token in ("bicycle", "bike", "cyclist")):
        return "bicycle"
    if any(token in text for token in ("motorcycle", "motorbike", "scooter", "moped", "two_wheeler")):
        return "motorcycle"
    if any(token in text for token in ("object", "obstacle", "barrier", "debris")):
        return "object"
    if any(token in text for token in ("vehicle", "truck", "trailer", "bus", "van", "car", "motor_vehicle")):
        return "vehicle"
    return text


def _frame_ref_count(item: dict[str, Any]) -> int:
    refs = item.get("frame_refs")
    return len(refs) if isinstance(refs, list) else 0


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _enqueue_video_analyze_job(
    cur: Any,
    row: tuple[Any, ...],
    payload: dict[str, Any],
    redis_client: Any,
    case_inputs: tuple[Any, ...] | None = None,
) -> None:
    if case_inputs is None:
        cur.execute(
            """
            SELECT c.structured_facts, c.selected_keywords, c.analysis_mode
            FROM cases c WHERE c.id=%s
            """,
            (row[1],),
        )
        case_inputs = cur.fetchone()
    analyze_payload = build_video_analyze_payload(row, payload, case_inputs)
    cur.execute(
        """
        INSERT INTO jobs(case_id, upload_id, owner_user_id, type, status, payload)
        VALUES(%s,%s,%s,'video_analyze','queued',%s)
        RETURNING id
        """,
        (row[1], row[2], row[3], json.dumps(analyze_payload)),
    )
    analyze_job_id = str(cur.fetchone()[0])
    redis_client.xadd(STREAM_KEY, {"job_id": analyze_job_id, "job_type": "video_analyze"}, maxlen=10000, approximate=True)


def build_frame_analysis_context(row: tuple[Any, ...], metadata: dict[str, Any], case_inputs: tuple[Any, ...] | None) -> dict[str, Any]:
    structured_facts = case_inputs[0] if case_inputs and isinstance(case_inputs[0], dict) else {}
    selected_keywords = list(case_inputs[1] if case_inputs and case_inputs[1] else [])
    safe_fact_keys = {
        "accident_type",
        "accident_party_type",
        "stopped",
        "sudden_brake",
        "lane_change",
        "intersection",
        "signal_state",
        "user_signal",
        "opponent_signal",
        "opponent_signal_visible",
        "signal_transition",
        "crosswalk_nearby",
        "pedestrian_visible",
        "pedestrian_signal",
        "collision_partner_type",
        "primary_collision_target",
        "front_vehicle_stopped",
        "ego_turn_direction",
        "centerline_crossed",
        "centerline_cross_reason",
        "stopped_vehicle_without_lights",
        "non_contact_trigger",
        "trigger_actor_type",
        "trigger_actor_behavior",
        "direct_collision_partner_type",
        "rear_vehicle_collision",
        "highway_or_expressway",
        "opponent_behavior",
        "injury",
        "damage_level",
    }
    visual_focus = {key: structured_facts.get(key) for key in safe_fact_keys if structured_facts.get(key) not in (None, "", [], {})}
    return {
        "case_id": str(row[1]),
        "upload_id": str(row[2]),
        "duration_sec": metadata.get("duration_sec"),
        "width": metadata.get("width"),
        "height": metadata.get("height"),
        "fps": metadata.get("fps"),
        "user_context_is_visual_focus_only": True,
        "visual_focus": visual_focus,
        "selected_keywords": selected_keywords[:8],
    }


def _compact_yolo_context(yolo_payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(yolo_payload, dict) or yolo_payload.get("enabled") is not True:
        return {}
    summary = yolo_payload.get("summary") if isinstance(yolo_payload.get("summary"), dict) else {}
    top_events = []
    for item in (yolo_payload.get("event_candidate_summary") or [])[:3]:
        if not isinstance(item, dict):
            continue
        top_events.append({
            "event_candidate_id": item.get("event_candidate_id"),
            "score": item.get("score"),
            "frame_refs": item.get("frame_refs"),
            "target_type_counts": item.get("target_detection_counts"),
            "dominant_target_type": item.get("dominant_target_type"),
            "event_phase_counts": item.get("event_phase_counts"),
        })
    sequences = []
    for item in (yolo_payload.get("temporal_sequence_summary") or [])[:3]:
        if not isinstance(item, dict):
            continue
        sequences.append({
            "event_candidate_id": item.get("event_candidate_id"),
            "rank": item.get("rank"),
            "sequence_quality": item.get("sequence_quality"),
            "dominant_target_type": item.get("dominant_target_type"),
            "target_detection_counts": item.get("target_detection_counts"),
            "target_frame_counts": item.get("target_frame_counts"),
            "target_phase_counts": item.get("target_phase_counts"),
            "frame_refs": item.get("frame_refs"),
        })
    return {
        "source": yolo_payload.get("source"),
        "model": yolo_payload.get("model"),
        "target_type_counts": summary.get("target_type_counts"),
        "ignored_class_counts": summary.get("ignored_class_counts"),
        "top_event_candidates": top_events,
        "temporal_sequences": sequences,
        "interpretation": "YOLO is an object inventory and frame-selection hint only; OpenAI must verify visible contact from frames.",
    }


def _process_video_analyze(cur: Any, row: tuple[Any, ...], payload: dict[str, Any], job_id: str) -> None:
    cur.execute("SELECT title, description_text FROM cases WHERE id=%s", (row[1],))
    case_row = cur.fetchone()

    cur.execute("SELECT metadata, file_name, status FROM uploads WHERE id=%s", (row[2],))
    upload_row = cur.fetchone()
    agent_payload = build_agent_video_request(row, payload, case_row, upload_row)
    response = requests_post_json(
        f"{INTERNAL_AGENT_URL}/internal/v1/analyze/video",
        agent_payload,
    )
    _insert_analysis_result(cur, row, response)
    cur.execute(
        "UPDATE jobs SET status='succeeded', artifacts=%s, finished_at=now() WHERE id=%s",
        (json.dumps({"user_facing_status": user_facing_job_status("video_analyze", "succeeded")}), job_id),
    )


def build_video_analyze_payload(row: tuple[Any, ...], payload: dict[str, Any], case_inputs: tuple[Any, ...] | None) -> dict[str, Any]:
    return {
        "case_id": str(row[1]),
        "upload_id": str(row[2]),
        "ai_profile": payload.get("ai_profile", "default_vehicle_collision"),
        "specialist_roles": payload.get("specialist_roles", []),
        "routing_reason": "auto_after_local_preprocess",
        "structured_facts": (case_inputs[0] if case_inputs else {}) or {},
        "selected_keywords": list(case_inputs[1] if case_inputs and case_inputs[1] else []),
        "analysis_mode": (case_inputs[2] if case_inputs else None) or "quick_summary",
    }


def build_agent_video_request(
    row: tuple[Any, ...],
    payload: dict[str, Any],
    case_row: tuple[Any, ...] | None,
    upload_row: tuple[Any, ...] | None,
) -> dict[str, Any]:
    structured_facts = payload.get("structured_facts") or {}
    selected_keywords = payload.get("selected_keywords") or []
    routing_reason = payload.get("routing_reason")
    case_text = f"{case_row[0] or ''} {case_row[1] or ''}".strip() if case_row else ""
    metadata = upload_row[0] if upload_row and isinstance(upload_row[0], dict) else {}
    payload_video_metadata = payload.get("video_metadata") if isinstance(payload.get("video_metadata"), dict) else {}
    preprocessed_summary = metadata.get("preprocess_summary") or "Local video metadata is available for analysis."
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
    return {
        "case_id": str(row[1]),
        "user_id": str(row[3]),
        "upload_id": str(row[2]),
        "preprocessed_summary": merged_summary,
        "ai_profile": payload.get("ai_profile", "default_vehicle_collision"),
        "specialist_roles": payload.get("specialist_roles", []),
        "video_metadata": {
            "preprocess_contract_version": VIDEO_PREPROCESS_CONTRACT_VERSION,
            "upload_status": upload_row[2] if upload_row else None,
            "file_name": upload_row[1] if upload_row else None,
            "metadata": metadata,
            "preprocess_payload": payload_video_metadata,
        },
        "structured_facts": structured_facts,
        "selected_keywords": selected_keywords,
        "analysis_mode": payload.get("analysis_mode") or "quick_summary",
    }


def build_analysis_result_values(row: tuple[Any, ...], response: dict[str, Any], version: int) -> dict[str, Any]:
    evidence = response.get("evidence", [])
    legal_liability = response.get("legal_liability", {}) or {}
    legal_analysis = response.get("legal_analysis", {}) or {}
    return {
        "case_id": row[1],
        "owner_user_id": row[3],
        "version": version,
        "result": response,
        "evidence": evidence,
        "uncertainty": response.get("uncertainty", {}),
        "model_info": response.get("model_info", {}),
        "structured_facts": response.get("structured_facts", {}),
        "recommended_keywords": response.get("recommended_keywords", []),
        "suggested_next_inputs": response.get("suggested_next_inputs", []),
        "report_payload": {},
        "elderly_friendly_report": response.get("elderly_friendly_report", {}),
        "legal_analysis": legal_analysis,
        "scenario_type": response.get("scenario_type"),
        "used_evidence_ids": [x.get("chunk_id") for x in evidence if x.get("chunk_id")],
        "legal_risk_flags": legal_liability.get("risk_flags", []) or legal_analysis.get("risk_flags", []),
        "persona_outputs": {"analysts": response.get("recommended_specialists", [])},
        "evidence_audit": response.get("evidence_audit", {}),
    }


def _insert_analysis_result(cur: Any, row: tuple[Any, ...], response: dict[str, Any]) -> None:
    cur.execute("SELECT COALESCE(MAX(version),0)+1 FROM analysis_results WHERE case_id=%s", (row[1],))
    version = cur.fetchone()[0]
    values = build_analysis_result_values(row, response, version)
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
            values["case_id"],
            values["owner_user_id"],
            values["version"],
            json.dumps(values["result"]),
            json.dumps(values["evidence"]),
            json.dumps(values["uncertainty"]),
            json.dumps(values["model_info"]),
            json.dumps(values["structured_facts"]),
            json.dumps(values["recommended_keywords"]),
            json.dumps(values["suggested_next_inputs"]),
            json.dumps(values["report_payload"]),
            json.dumps(values["elderly_friendly_report"]),
            json.dumps(values["legal_analysis"]),
            values["scenario_type"],
            json.dumps(values["used_evidence_ids"]),
            json.dumps(values["legal_risk_flags"]),
            json.dumps(values["persona_outputs"]),
            json.dumps(values["evidence_audit"]),
        ),
    )
    result_id = cur.fetchone()[0]
    cur.execute("UPDATE cases SET status='completed', latest_result_id=%s WHERE id=%s", (result_id, row[1]))


def mark_failed(job_id: str, err: Exception) -> None:
    try:
        import psycopg

        with psycopg.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE jobs
                    SET status = (CASE WHEN attempts >= max_attempts THEN 'dead' ELSE 'failed' END)::job_status,
                        error_info = jsonb_build_object('message', %s::text, 'at', now()),
                        last_error = %s,
                        next_run_at = now() + interval '5 minutes',
                        updated_at = now()
                    WHERE id=%s
                    """,
                    (_safe_worker_error_message(err), _safe_worker_error_message(err), job_id),
                )
                conn.commit()
    except Exception as update_err:
        print(json.dumps({
            "event": "worker_mark_failed_update_failed",
            "job_id": job_id,
            "error": _safe_worker_error_message(update_err),
        }))


def _safe_worker_error_message(err: Exception) -> str:
    message = str(err)
    lowered = message.lower()
    if isinstance(err, FileNotFoundError) or "not found" in lowered or "no such file" in lowered:
        return "저장된 영상을 찾지 못했습니다. 다시 업로드해 주세요."
    if "permission" in lowered or "denied" in lowered:
        return "영상 저장 권한을 확인해야 합니다. 관리자에게 문의해 주세요."
    if "space" in lowered or "enospc" in lowered:
        return "저장 공간이 부족하여 영상을 저장하지 못했습니다. 관리자에게 문의해 주세요."
    if "connect" in lowered or "timeout" in lowered or "timed out" in lowered:
        return "영상 저장소에 일시적으로 연결하지 못했습니다. 잠시 후 다시 시도해 주세요."
    return "영상 처리 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요."
