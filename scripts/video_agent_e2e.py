import argparse
import json
import mimetypes
import sys
import time
import uuid
from pathlib import Path
from urllib import error, request


DEFAULT_BASE_URL = "http://localhost"
DEFAULT_TIMEOUT_SEC = 180


class E2EError(RuntimeError):
    pass


def http_json(method: str, base_url: str, path: str, payload: dict | None = None, token: str | None = None):
    data = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
    headers = {
        "Accept": "application/json",
        "Idempotency-Key": str(uuid.uuid4()),
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = request.Request(f"{base_url}{path}", data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise E2EError(f"{method} {path} failed: {exc.code} {body}") from exc


def multipart_upload(base_url: str, path: str, case_id: str, file_path: Path, token: str):
    boundary = f"----lawcompass{uuid.uuid4().hex}"
    mime = mimetypes.guess_type(file_path.name)[0] or "video/mp4"
    fields = f"--{boundary}\r\nContent-Disposition: form-data; name=\"case_id\"\r\n\r\n{case_id}\r\n".encode()
    file_header = (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"file\"; filename=\"{file_path.name}\"\r\n"
        f"Content-Type: {mime}\r\n\r\n"
    ).encode()
    footer = f"\r\n--{boundary}--\r\n".encode()
    body = fields + file_header + file_path.read_bytes() + footer
    req = request.Request(
        f"{base_url}{path}",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Idempotency-Key": str(uuid.uuid4()),
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise E2EError(f"POST {path} failed: {exc.code} {body}") from exc


def create_case_payload():
    return {
        "title": "영상 E2E 후미추돌 검증",
        "description_text": "신호대기 또는 정차 중 뒤 차량이 추돌한 사고로 보입니다. 영상 전처리 결과와 사용자 입력을 함께 검증합니다.",
        "structured_facts": {
            "accident_type": "rear_end_collision",
            "signal_state": "red",
            "stopped": True,
            "sudden_brake": False,
            "lane_change": False,
            "intersection": False,
            "pedestrian": False,
            "weather": "clear",
            "light_condition": "day",
            "opponent_behavior": "rear_vehicle_collision",
            "injury": False,
            "damage_level": "minor_rear_bumper_damage",
        },
        "selected_keywords": ["후미추돌", "정차 중", "안전거리", "블랙박스", "보험 접수"],
        "analysis_mode": "fault_ratio",
    }


def summarize_jobs(jobs: list[dict]) -> list[dict]:
    return [
        {
            "type": item.get("type"),
            "status": item.get("status"),
            "id": item.get("id"),
        }
        for item in jobs
    ]


def wait_for_video_pipeline(base_url: str, case_id: str, token: str, timeout_sec: int):
    deadline = time.time() + timeout_sec
    last_jobs: list[dict] = []
    while time.time() < deadline:
        jobs = http_json("GET", base_url, f"/api/v1/cases/{case_id}/jobs", token=token).get("items", [])
        last_jobs = jobs
        statuses = {(job.get("type"), job.get("status")) for job in jobs}
        if any(status in {"failed", "dead"} for _, status in statuses):
            raise E2EError(f"video pipeline job failed: {summarize_jobs(jobs)}")
        has_preprocess = any(job_type == "video_preprocess" and status == "succeeded" for job_type, status in statuses)
        has_analyze = any(job_type == "video_analyze" and status == "succeeded" for job_type, status in statuses)
        if has_preprocess and has_analyze:
            return jobs
        time.sleep(2)
    raise E2EError(f"video pipeline timed out: {summarize_jobs(last_jobs)}")


def frame_analysis_summary(upload: dict, require_observations: bool):
    metadata = upload.get("metadata") if isinstance(upload.get("metadata"), dict) else {}
    frame_analysis = metadata.get("openai_frame_analysis") if isinstance(metadata.get("openai_frame_analysis"), dict) else {}
    observations = frame_analysis.get("observations") if isinstance(frame_analysis.get("observations"), list) else []
    error_text = str(frame_analysis.get("error") or "")
    if require_observations:
        if frame_analysis.get("enabled") is not True:
            raise E2EError(f"OpenAI frame analysis was not enabled: {frame_analysis.get('reason') or 'unknown reason'}")
        if error_text:
            raise E2EError(f"OpenAI frame analysis returned an error: {error_text}")
        if not observations:
            raise E2EError("OpenAI frame analysis completed but returned no observations")
    return {
        "enabled": frame_analysis.get("enabled"),
        "provider": frame_analysis.get("provider"),
        "model": frame_analysis.get("model"),
        "detail": frame_analysis.get("detail"),
        "analyzed_frame_count": len(frame_analysis.get("analyzed_frames") or []),
        "observation_count": len(observations),
        "observation_quality_summary": frame_analysis.get("observation_quality_summary"),
        "summary": frame_analysis.get("summary"),
        "observations": [
            {
                "field": item.get("field"),
                "value": item.get("value"),
                "confidence": item.get("confidence"),
                "frame_refs": item.get("frame_refs") or [],
            }
            for item in observations[:5]
            if isinstance(item, dict)
        ],
        "has_error": bool(error_text),
    }


def assert_agent_process_card(report: dict):
    card = report.get("agent_process_card")
    if not isinstance(card, dict):
        raise E2EError("easy-report is missing agent_process_card")
    if not card.get("stats") or not card.get("steps"):
        raise E2EError("agent_process_card is missing stats or steps")

    encoded = json.dumps(card, ensure_ascii=False)
    forbidden_tokens = [
        "agent_trace",
        "reflection_loop",
        "packet",
        "input_normalization",
        "next_action",
    ]
    leaked = [token for token in forbidden_tokens if token in encoded]
    if leaked:
        raise E2EError(f"agent_process_card leaked internal tokens: {leaked}")
    return card


def agent_video_fact_summary(debug_report: dict, require_agent_video_facts: bool):
    technical = debug_report.get("technical") if isinstance(debug_report.get("technical"), dict) else {}
    video_contract = technical.get("video_input_contract") if isinstance(technical.get("video_input_contract"), dict) else {}
    arbitration = technical.get("fact_arbitration") if isinstance(technical.get("fact_arbitration"), dict) else {}
    fact_patch = video_contract.get("fact_patch") if isinstance(video_contract.get("fact_patch"), dict) else {}
    accepted = video_contract.get("accepted_observations") if isinstance(video_contract.get("accepted_observations"), list) else []
    uncertain = video_contract.get("uncertain_observations") if isinstance(video_contract.get("uncertain_observations"), list) else []
    applied_video_fields = arbitration.get("applied_video_fields") if isinstance(arbitration.get("applied_video_fields"), list) else []
    conflicts = arbitration.get("conflicts") if isinstance(arbitration.get("conflicts"), list) else []
    if require_agent_video_facts:
        if not accepted:
            raise E2EError("Agent video_input_contract accepted no frame observations")
        if not fact_patch:
            raise E2EError("Agent video_input_contract produced no fact_patch")
        if not applied_video_fields:
            raise E2EError("Agent fact_arbitration applied no video-derived fields")
    return {
        "video_contract_version": video_contract.get("version"),
        "accepted_observation_count": len(accepted),
        "uncertain_observation_count": len(uncertain),
        "observation_quality_summary": video_contract.get("observation_quality_summary"),
        "fact_patch": fact_patch,
        "applied_video_fields": applied_video_fields,
        "conflict_count": len(conflicts),
        "conflicts": [
            {
                "field": item.get("field"),
                "winner": item.get("winner"),
                "authority": item.get("authority"),
                "video_confidence": item.get("video_confidence"),
            }
            for item in conflicts[:5]
            if isinstance(item, dict)
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Run a local video upload -> preprocess -> Agent report E2E check.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--video-path", required=True)
    parser.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC)
    parser.add_argument(
        "--require-frame-observations",
        action="store_true",
        help="Fail if OpenAI frame analysis is disabled, errored, or returned no observations.",
    )
    parser.add_argument(
        "--require-agent-video-facts",
        action="store_true",
        help="Fail if Agent video input contract/fact arbitration did not accept and apply video-derived facts.",
    )
    args = parser.parse_args()

    video_path = Path(args.video_path).expanduser().resolve()
    if not video_path.exists():
        raise E2EError(f"video file not found: {video_path}")

    unique = uuid.uuid4().hex[:10]
    email = f"video-e2e-{unique}@example.com"
    password = f"LocalE2E-{uuid.uuid4().hex[:12]}!"

    http_json("POST", args.base_url, "/api/v1/auth/signup", {
        "email": email,
        "password": password,
        "display_name": "영상 E2E",
    })
    login = http_json("POST", args.base_url, "/api/v1/auth/login", {"email": email, "password": password})
    token = login["access_token"]

    created = http_json("POST", args.base_url, "/api/v1/cases", create_case_payload(), token)
    case_id = created["case"]["id"]

    uploaded = multipart_upload(args.base_url, "/api/v1/uploads/local", case_id, video_path, token)
    upload_id = uploaded["upload_id"]
    completed = http_json("POST", args.base_url, "/api/v1/uploads/complete", {"upload_id": upload_id}, token)

    jobs = wait_for_video_pipeline(args.base_url, case_id, token, args.timeout_sec)
    report = http_json("GET", args.base_url, f"/api/v1/cases/{case_id}/easy-report", token=token)
    card = assert_agent_process_card(report)
    debug_report = http_json("GET", args.base_url, f"/api/v1/cases/{case_id}/report?debug=1", token=token).get("debug", {})
    uploads = http_json("GET", args.base_url, f"/api/v1/cases/{case_id}/uploads", token=token).get("items", [])
    upload = next((item for item in uploads if item.get("id") == upload_id), {})
    frame_summary = frame_analysis_summary(upload, args.require_frame_observations)
    agent_video_summary = agent_video_fact_summary(debug_report, args.require_agent_video_facts)

    output = {
        "video_agent_e2e": "passed",
        "case_id": case_id,
        "upload_id": upload_id,
        "preprocess_job_id": completed.get("job_id"),
        "jobs": summarize_jobs(jobs),
        "upload_status": upload.get("status"),
        "preprocess_summary": upload.get("preprocess_summary"),
        "frame_analysis": frame_summary,
        "agent_video_input": agent_video_summary,
        "agent_process_status": card.get("status_label"),
        "agent_process_stats": card.get("stats", []),
        "agent_process_steps": [step.get("label") for step in card.get("steps", [])],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except E2EError as exc:
        print(f"video_agent_e2e=failed: {exc}", file=sys.stderr)
        sys.exit(1)
