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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


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


def create_case_payload(case_json_path: str = ""):
    if case_json_path:
        loaded = json.loads(Path(case_json_path).expanduser().resolve().read_text(encoding="utf-8-sig"))
        if not isinstance(loaded, dict):
            raise E2EError(f"case json must contain an object: {case_json_path}")
        payload = loaded.get("case") if isinstance(loaded.get("case"), dict) else loaded
        if not isinstance(payload, dict):
            raise E2EError(f"case json must contain a case object: {case_json_path}")
        if not payload.get("title") or not payload.get("description_text"):
            raise E2EError("case json must include title and description_text")
        return payload
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
    event_summary = frame_analysis.get("accident_event_summary") if isinstance(frame_analysis.get("accident_event_summary"), dict) else {}
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
        "frame_selection_strategy": frame_analysis.get("frame_selection_strategy"),
        "available_frame_count": frame_analysis.get("available_frame_count"),
        "selected_frame_count": frame_analysis.get("selected_frame_count"),
        "frame_selection_max_frames": frame_analysis.get("frame_selection_max_frames"),
        "analyzed_frame_count": len(frame_analysis.get("analyzed_frames") or []),
        "observation_count": len(observations),
        "observation_quality_summary": frame_analysis.get("observation_quality_summary"),
        "accident_event_summary": event_summary,
        "zero_observation_retry_used": frame_analysis.get("zero_observation_retry_used"),
        "zero_observation_retry_error": frame_analysis.get("zero_observation_retry_error"),
        "analysis_attempts": frame_analysis.get("analysis_attempts") if isinstance(frame_analysis.get("analysis_attempts"), list) else [],
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


def assert_expert_guidance_card(report: dict):
    card = report.get("expert_guidance_card")
    if not isinstance(card, dict):
        raise E2EError("easy-report is missing expert_guidance_card")
    legal = card.get("legal") if isinstance(card.get("legal"), dict) else {}
    insurance = card.get("insurance") if isinstance(card.get("insurance"), dict) else {}
    if not card.get("status_label"):
        raise E2EError("expert_guidance_card is missing status label")
    if not legal.get("fault_range_label"):
        raise E2EError("expert_guidance_card is missing legal fault range")
    if not insurance.get("summary") and not insurance.get("steps"):
        raise E2EError("expert_guidance_card is missing insurance guidance")

    encoded = json.dumps(card, ensure_ascii=False)
    forbidden_tokens = [
        "expert_guidance_sections",
        "chunk_id",
        "cache_key",
        "model_info",
        "evidence_ids",
        "source_uri",
    ]
    leaked = [token for token in forbidden_tokens if token in encoded]
    if leaked:
        raise E2EError(f"expert_guidance_card leaked internal tokens: {leaked}")
    basis = [
        {
            "family_label": str(item.get("family_label") or ""),
            "title": str(item.get("title") or ""),
            "reason": str(item.get("reason") or ""),
        }
        for item in (card.get("basis") or [])
        if isinstance(item, dict)
    ][:4]
    legal_points = [str(item) for item in (legal.get("points") or []) if item][:6]
    legal_limits = [str(item) for item in (legal.get("limits") or []) if item][:4]
    insurance_steps = [str(item) for item in (insurance.get("steps") or []) if item][:5]
    insurance_documents = [str(item) for item in (insurance.get("documents") or []) if item][:6]
    missing_items = [str(item) for item in (card.get("missing_items") or []) if item][:5]
    return {
        "status_label": card.get("status_label"),
        "summary": card.get("summary"),
        "fault_range_label": legal.get("fault_range_label"),
        "legal_point_count": len(legal_points),
        "legal_limit_count": len(legal_limits),
        "insurance_step_count": len(insurance_steps),
        "insurance_document_count": len(insurance_documents),
        "basis_count": len(basis),
        "missing_item_count": len(missing_items),
        "legal_points": legal_points,
        "legal_limits": legal_limits,
        "insurance_steps": insurance_steps,
        "insurance_documents": insurance_documents,
        "basis": basis,
        "missing_items": missing_items,
    }


def agent_video_fact_summary(debug_report: dict, require_agent_video_facts: bool):
    technical = debug_report.get("technical") if isinstance(debug_report.get("technical"), dict) else {}
    video_contract = technical.get("video_input_contract") if isinstance(technical.get("video_input_contract"), dict) else {}
    arbitration = technical.get("fact_arbitration") if isinstance(technical.get("fact_arbitration"), dict) else {}
    fact_patch = video_contract.get("fact_patch") if isinstance(video_contract.get("fact_patch"), dict) else {}
    accepted = video_contract.get("accepted_observations") if isinstance(video_contract.get("accepted_observations"), list) else []
    uncertain = video_contract.get("uncertain_observations") if isinstance(video_contract.get("uncertain_observations"), list) else []
    supporting = video_contract.get("supporting_observations") if isinstance(video_contract.get("supporting_observations"), list) else []
    confirmation_candidates = video_contract.get("confirmation_candidates") if isinstance(video_contract.get("confirmation_candidates"), list) else []
    confirmation_groups = video_contract.get("confirmation_groups") if isinstance(video_contract.get("confirmation_groups"), list) else []
    applied_video_fields = arbitration.get("applied_video_fields") if isinstance(arbitration.get("applied_video_fields"), list) else []
    confirmed_fields = arbitration.get("confirmed_fields") if isinstance(arbitration.get("confirmed_fields"), list) else []
    conflicts = arbitration.get("conflicts") if isinstance(arbitration.get("conflicts"), list) else []
    if require_agent_video_facts:
        if not accepted:
            raise E2EError("Agent video_input_contract accepted no frame observations")
        if not fact_patch:
            raise E2EError("Agent video_input_contract produced no fact_patch")
        if not applied_video_fields and not confirmed_fields:
            raise E2EError("Agent fact_arbitration neither applied nor confirmed video-derived fields")
    return {
        "video_contract_version": video_contract.get("version"),
        "accepted_observation_count": len(accepted),
        "uncertain_observation_count": len(uncertain),
        "supporting_observation_count": len(supporting),
        "supporting_observations": [
            {
                "field": item.get("field"),
                "value": item.get("value"),
                "confidence": item.get("confidence"),
            }
            for item in supporting[:8]
            if isinstance(item, dict)
        ],
        "confirmation_candidate_count": len(confirmation_candidates),
        "confirmation_groups": [
            {
                "type": item.get("type"),
                "status": item.get("status"),
                "fields": item.get("fields"),
            }
            for item in confirmation_groups[:5]
            if isinstance(item, dict)
        ],
        "observation_quality_summary": video_contract.get("observation_quality_summary"),
        "fact_patch": fact_patch,
        "applied_video_fields": applied_video_fields,
        "confirmed_fields": confirmed_fields,
        "conflict_count": len(conflicts),
        "conflicts": [
            {
                "field": item.get("field"),
                "winner": item.get("winner"),
                "authority": item.get("authority"),
                "user_value": item.get("user_value"),
                "video_value": item.get("video_value"),
                "video_confidence": item.get("video_confidence"),
            }
            for item in conflicts[:5]
            if isinstance(item, dict)
        ],
    }


def _parse_expected_items(raw_items: list[str] | None) -> dict[str, object]:
    expected: dict[str, object] = {}
    for raw in raw_items or []:
        if "=" not in raw:
            raise E2EError(f"expected item must use field=value format: {raw}")
        field, value = raw.split("=", 1)
        field = field.strip()
        if not field:
            raise E2EError(f"expected item has empty field: {raw}")
        expected[field] = _parse_expected_value(value.strip())
    return expected


def _parse_expected_value(value: str) -> object:
    lowered = value.lower()
    if lowered in {"true", "yes", "1"}:
        return True
    if lowered in {"false", "no", "0"}:
        return False
    try:
        return int(value)
    except ValueError:
        return value


def evaluate_accuracy_expectations(frame_summary: dict, agent_video_summary: dict, args: argparse.Namespace) -> dict:
    expected_agent = _parse_expected_items(args.expect_agent_fact)
    expected_frame = _parse_expected_items(args.expect_frame_observation)
    frame_observations = frame_summary.get("observations") if isinstance(frame_summary.get("observations"), list) else []
    fact_patch = agent_video_summary.get("fact_patch") if isinstance(agent_video_summary.get("fact_patch"), dict) else {}
    checks: list[dict] = []

    for field, expected_value in expected_frame.items():
        matched = any(item.get("field") == field and item.get("value") == expected_value for item in frame_observations if isinstance(item, dict))
        checks.append({"scope": "frame_observation", "field": field, "expected": expected_value, "passed": matched})
    for field, expected_value in expected_agent.items():
        actual = fact_patch.get(field)
        checks.append({"scope": "agent_fact_patch", "field": field, "expected": expected_value, "actual": actual, "passed": actual == expected_value})

    failed = [item for item in checks if not item.get("passed")]
    if failed and not args.allow_accuracy_mismatch:
        raise E2EError(f"accuracy expectations failed: {failed}")
    return {
        "checked_count": len(checks),
        "passed_count": len(checks) - len(failed),
        "failed_count": len(failed),
        "mismatch_allowed": bool(args.allow_accuracy_mismatch),
        "checks": checks,
    }


def assert_video_fact_card(report: dict):
    card = report.get("video_fact_explanation_card")
    if not isinstance(card, dict):
        raise E2EError("easy-report is missing video_fact_explanation_card")
    quality = card.get("quality_summary") if isinstance(card.get("quality_summary"), dict) else {}
    stats = card.get("stats") if isinstance(card.get("stats"), list) else []
    if not quality.get("status_label"):
        raise E2EError("video_fact_explanation_card is missing quality status")
    if not stats:
        raise E2EError("video_fact_explanation_card is missing stats")
    return {
        "summary": card.get("summary"),
        "status_label": quality.get("status_label"),
        "representative_frame_count": quality.get("representative_frame_count"),
        "quality_notes": quality.get("notes") if isinstance(quality.get("notes"), list) else [],
        "recovery_actions": quality.get("recovery_actions") if isinstance(quality.get("recovery_actions"), list) else [],
        "stats": stats,
        "event_candidate": card.get("event_candidate") if isinstance(card.get("event_candidate"), dict) else None,
    }


def video_accuracy_metrics(frame_summary: dict, agent_video_summary: dict, video_card: dict, accuracy_summary: dict) -> dict:
    accepted = int(agent_video_summary.get("accepted_observation_count") or 0)
    uncertain = int(agent_video_summary.get("uncertain_observation_count") or 0)
    supporting = int(agent_video_summary.get("supporting_observation_count") or 0)
    confirmed = len(agent_video_summary.get("confirmed_fields") or [])
    applied = len(agent_video_summary.get("applied_video_fields") or [])
    conflicts = int(agent_video_summary.get("conflict_count") or 0)
    observed = int(frame_summary.get("observation_count") or 0)
    actionable = applied + confirmed
    checked = int(accuracy_summary.get("checked_count") or 0)
    passed = int(accuracy_summary.get("passed_count") or 0)
    stats = video_card.get("stats") if isinstance(video_card.get("stats"), list) else []
    return {
        "provider": frame_summary.get("provider"),
        "model": frame_summary.get("model"),
        "detail": frame_summary.get("detail"),
        "selected_frame_count": frame_summary.get("selected_frame_count"),
        "frame_observation_count": observed,
        "agent_accepted_count": accepted,
        "agent_uncertain_count": uncertain,
        "agent_supporting_count": supporting,
        "applied_count": applied,
        "confirmed_count": confirmed,
        "actionable_count": actionable,
        "conflict_count": conflicts,
        "accuracy_checked_count": checked,
        "accuracy_passed_count": passed,
        "accuracy_failed_count": max(0, checked - passed),
        "actionable_rate": round(actionable / accepted, 3) if accepted else 0,
        "uncertain_rate": round(uncertain / observed, 3) if observed else 0,
        "supporting_rate": round(supporting / observed, 3) if observed else 0,
        "conflict_rate": round(conflicts / accepted, 3) if accepted else 0,
        "recovery_action_count": len(video_card.get("recovery_actions") or []),
        "display_stats": stats,
    }


def missing_questions(report: dict) -> list[dict]:
    missing = report.get("missing_info") if isinstance(report.get("missing_info"), dict) else {}
    questions = missing.get("questions") if isinstance(missing.get("questions"), list) else []
    return [item for item in questions if isinstance(item, dict) and item.get("field")]


def assert_missing_info_priority(report: dict):
    questions = missing_questions(report)
    if not questions:
        return None
    missing = report.get("missing_info") if isinstance(report.get("missing_info"), dict) else {}
    priority_items = missing.get("priority_items") if isinstance(missing.get("priority_items"), list) else []
    if not priority_items:
        raise E2EError("missing_info has questions but no priority_items")
    top = priority_items[0] if isinstance(priority_items[0], dict) else {}
    if not top.get("label") and not top.get("question"):
        raise E2EError("missing_info priority item has no user-safe label or question")
    text = json.dumps(priority_items, ensure_ascii=False)
    for question in questions:
        raw_field = str(question.get("field") or "")
        if raw_field and raw_field in text:
            raise E2EError("missing_info priority item exposed raw field names")
    return {
        "top_label": top.get("label"),
        "top_priority": top.get("priority_label"),
        "priority_count": len(priority_items),
    }


def choose_quality_followup_question(report: dict) -> dict | None:
    video_followup_fields = {
        "stopped",
        "sudden_brake",
        "opponent_behavior",
        "lane_change_actor",
        "turn_signal",
        "user_signal",
        "opponent_signal",
        "opponent_signal_violation",
        "crosswalk_nearby",
        "school_zone",
        "damage_level",
    }
    for question in missing_questions(report):
        field = str(question.get("field") or "")
        encoded = json.dumps(question, ensure_ascii=False).lower()
        if field in video_followup_fields and "front" not in encoded:
            return question
    for question in missing_questions(report):
        text = f"{question.get('question') or ''} {question.get('label') or ''}"
        if any(marker in text for marker in ("품질 기준", "바로 반영하지 않았습니다", "충분히 확인하지 못했습니다")):
            return question
    return None


def choose_conflict_followup_question(report: dict, agent_video_summary: dict) -> tuple[dict | None, dict | None]:
    conflicts = agent_video_summary.get("conflicts") if isinstance(agent_video_summary.get("conflicts"), list) else []
    questions = missing_questions(report)
    for conflict in conflicts:
        field = str(conflict.get("field") or "")
        if not field:
            continue
        for question in questions:
            if str(question.get("field") or "") == field:
                return question, conflict
    return None, None


def answer_for_question(question: dict) -> str:
    field = str(question.get("field") or "")
    preferred = {
        "stopped": "정차 중",
        "sudden_brake": "급정거 아님",
        "opponent_behavior": "뒤에서 추돌",
        "lane_change_actor": "상대 차량",
        "turn_signal": "켜지 않음",
        "user_signal": "적색",
        "opponent_signal": "적색",
        "opponent_signal_violation": "예",
        "crosswalk_nearby": "횡단보도 아님",
        "school_zone": "어린이보호구역 아님",
        "injury": "다친 사람 없음",
        "damage_level": "경미",
    }
    options = [str(item) for item in (question.get("options") or []) if str(item).strip()]
    if field in preferred and (not options or preferred[field] in options):
        return preferred[field]
    for option in options:
        if "확인" not in option:
            return option
    if options:
        return options[0]
    return preferred.get(field, "확인 필요")


def answer_for_conflict_resolution(question: dict, conflict: dict) -> str:
    value = conflict.get("video_value")
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is not None and str(value).strip():
        return str(value).strip()
    return answer_for_question(question)


def equivalent_fact_value(left, right) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return str(left).lower() == str(right).lower()
    return str(left).strip().lower() == str(right).strip().lower()


def run_held_observation_followup(base_url: str, case_id: str, token: str, report: dict):
    question = choose_quality_followup_question(report)
    if not question:
        raise E2EError("easy-report has no held video-observation quality followup question")
    before_questions = missing_questions(report)
    before_question_count = len(before_questions)
    field = str(question["field"])
    answer = answer_for_question(question)
    payload = {
        "followup_answers": {
            field: answer,
        }
    }
    reanalyzed = http_json("POST", base_url, f"/api/v1/cases/{case_id}/reanalyze", payload, token=token)
    next_version = int(reanalyzed.get("version") or 0)
    if next_version < 2:
        raise E2EError("reanalyze did not create a new analysis version")
    next_report = reanalyzed.get("report") if isinstance(reanalyzed.get("report"), dict) else reanalyzed.get("result", {})
    if not isinstance(next_report, dict):
        raise E2EError("reanalyze response did not include a report")
    change_card = next_report.get("analysis_change_card")
    if not isinstance(change_card, dict):
        raise E2EError("reanalyze response is missing analysis_change_card")
    answer_items = change_card.get("answer_items") if isinstance(change_card.get("answer_items"), list) else []
    if not answer_items:
        raise E2EError("analysis_change_card is missing followup answer_items")
    question_flow = change_card.get("question_flow") if isinstance(change_card.get("question_flow"), dict) else {}
    if not question_flow:
        raise E2EError("analysis_change_card is missing question_flow")
    if int(question_flow.get("answered_count") or 0) < 1:
        raise E2EError("analysis_change_card question_flow did not record the answered field")
    answer_text = json.dumps(answer_items, ensure_ascii=False)
    if field in answer_text:
        raise E2EError("analysis_change_card exposed raw followup field names")
    latest_report = http_json("GET", base_url, f"/api/v1/cases/{case_id}/easy-report", token=token)
    latest_questions = missing_questions(latest_report)
    latest_card = latest_report.get("analysis_change_card") if isinstance(latest_report.get("analysis_change_card"), dict) else {}
    if not latest_card:
        raise E2EError("latest easy-report did not persist analysis_change_card")
    latest_flow = latest_card.get("question_flow") if isinstance(latest_card.get("question_flow"), dict) else {}
    if not latest_flow:
        raise E2EError("latest easy-report did not persist analysis_change_card.question_flow")
    if int(latest_flow.get("before_count") or -1) != before_question_count:
        raise E2EError("latest easy-report question_flow does not preserve original question count")
    if int(latest_flow.get("after_count") or -1) != len(latest_questions):
        raise E2EError("latest easy-report question_flow does not match current question count")
    if int(latest_flow.get("answered_count") or 0) < 1:
        raise E2EError("latest easy-report question_flow did not preserve answered field count")
    updated_case = http_json("GET", base_url, f"/api/v1/cases/{case_id}", token=token).get("case", {})
    latest_facts = updated_case.get("structured_facts") if isinstance(updated_case.get("structured_facts"), dict) else {}
    answered_fields = latest_facts.get("_followup_answered_fields") if isinstance(latest_facts.get("_followup_answered_fields"), list) else []
    unresolved_fields = latest_facts.get("_followup_unresolved_fields") if isinstance(latest_facts.get("_followup_unresolved_fields"), list) else []
    if field not in answered_fields and field not in unresolved_fields:
        raise E2EError("reanalyze did not persist followup field status into case facts")
    after_question_fields = [str(item.get("field") or "") for item in latest_questions if isinstance(item, dict)]
    return {
        "field": field,
        "question": question.get("question"),
        "answer": answer,
        "next_version": next_version,
        "change_summary": change_card.get("summary"),
        "question_flow": {
            "before_count": before_question_count,
            "after_count": len(latest_questions),
            "answered_count": question_flow.get("answered_count"),
            "unresolved_count": question_flow.get("unresolved_count"),
            "status_label": question_flow.get("status_label"),
            "field_removed_from_questions": field not in after_question_fields,
        },
        "persisted_question_flow": {
            "before_count": latest_flow.get("before_count"),
            "after_count": latest_flow.get("after_count"),
            "answered_count": latest_flow.get("answered_count"),
            "unresolved_count": latest_flow.get("unresolved_count"),
            "status_label": latest_flow.get("status_label"),
        },
        "answer_statuses": [
            {
                "label": item.get("label"),
                "status_label": item.get("status_label"),
            }
            for item in answer_items[:5]
            if isinstance(item, dict)
        ],
        "remaining_question_count": len(latest_questions),
        "remaining_question_fields": after_question_fields[:8],
    }


def run_conflict_followup(base_url: str, case_id: str, token: str, report: dict, agent_video_summary: dict):
    question, conflict = choose_conflict_followup_question(report, agent_video_summary)
    if not question or not conflict:
        raise E2EError("easy-report has no video/user conflict followup question")
    before_questions = missing_questions(report)
    before_question_count = len(before_questions)
    field = str(question["field"])
    expected_value = conflict.get("video_value")
    answer = answer_for_conflict_resolution(question, conflict)
    payload = {"followup_answers": {field: answer}}
    reanalyzed = http_json("POST", base_url, f"/api/v1/cases/{case_id}/reanalyze", payload, token=token)
    next_version = int(reanalyzed.get("version") or 0)
    if next_version < 2:
        raise E2EError("conflict reanalyze did not create a new analysis version")
    next_report = reanalyzed.get("report") if isinstance(reanalyzed.get("report"), dict) else reanalyzed.get("result", {})
    if not isinstance(next_report, dict):
        raise E2EError("conflict reanalyze response did not include a report")
    change_card = next_report.get("analysis_change_card")
    if not isinstance(change_card, dict):
        raise E2EError("conflict reanalyze response is missing analysis_change_card")

    latest_report = http_json("GET", base_url, f"/api/v1/cases/{case_id}/easy-report", token=token)
    latest_questions = missing_questions(latest_report)
    latest_debug = http_json("GET", base_url, f"/api/v1/cases/{case_id}/report?debug=1", token=token).get("debug", {})
    latest_video_summary = agent_video_fact_summary(latest_debug, False)
    remaining_conflict_fields = [
        str(item.get("field") or "")
        for item in latest_video_summary.get("conflicts", [])
        if isinstance(item, dict)
    ]
    if field in remaining_conflict_fields:
        raise E2EError("conflict followup did not resolve the answered video/user conflict")

    updated_case = http_json("GET", base_url, f"/api/v1/cases/{case_id}", token=token).get("case", {})
    latest_facts = updated_case.get("structured_facts") if isinstance(updated_case.get("structured_facts"), dict) else {}
    if expected_value is not None and not equivalent_fact_value(latest_facts.get(field), expected_value):
        raise E2EError("conflict followup answer was not persisted as the selected case fact")

    after_question_fields = [str(item.get("field") or "") for item in latest_questions if isinstance(item, dict)]
    return {
        "field": field,
        "answer": answer,
        "expected_value": expected_value,
        "next_version": next_version,
        "question_flow": {
            "before_count": before_question_count,
            "after_count": len(latest_questions),
            "field_removed_from_questions": field not in after_question_fields,
        },
        "latest_conflict_count": latest_video_summary.get("conflict_count"),
        "latest_applied_video_fields": latest_video_summary.get("applied_video_fields"),
        "latest_confirmed_fields": latest_video_summary.get("confirmed_fields"),
        "remaining_question_fields": after_question_fields[:8],
    }


def main():
    parser = argparse.ArgumentParser(description="Run a local video upload -> preprocess -> Agent report E2E check.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--video-path", required=True)
    parser.add_argument(
        "--case-json",
        default="",
        help="Optional JSON file containing a case payload or an object with a case property.",
    )
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
    parser.add_argument(
        "--exercise-held-observation-followup",
        action="store_true",
        help="Submit one held video-observation quality followup answer and fail unless reanalysis records a change card.",
    )
    parser.add_argument(
        "--exercise-conflict-followup",
        action="store_true",
        help="Submit one video/user conflict followup answer and fail unless reanalysis resolves that conflict.",
    )
    parser.add_argument(
        "--expect-frame-observation",
        action="append",
        default=[],
        help="Expected frame observation in field=value format. Can be repeated.",
    )
    parser.add_argument(
        "--expect-agent-fact",
        action="append",
        default=[],
        help="Expected Agent video fact_patch value in field=value format. Can be repeated.",
    )
    parser.add_argument(
        "--allow-accuracy-mismatch",
        action="store_true",
        help="Record failed expectation checks without failing the E2E run. Useful for actual model calibration.",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="Optional path to write the full JSON result for accuracy calibration records.",
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

    created = http_json("POST", args.base_url, "/api/v1/cases", create_case_payload(args.case_json), token)
    case_id = created["case"]["id"]

    uploaded = multipart_upload(args.base_url, "/api/v1/uploads/local", case_id, video_path, token)
    upload_id = uploaded["upload_id"]
    completed = http_json("POST", args.base_url, "/api/v1/uploads/complete", {"upload_id": upload_id}, token)

    jobs = wait_for_video_pipeline(args.base_url, case_id, token, args.timeout_sec)
    report = http_json("GET", args.base_url, f"/api/v1/cases/{case_id}/easy-report", token=token)
    card = assert_agent_process_card(report)
    expert_card = assert_expert_guidance_card(report)
    video_card = assert_video_fact_card(report)
    priority_summary = assert_missing_info_priority(report)
    debug_report = http_json("GET", args.base_url, f"/api/v1/cases/{case_id}/report?debug=1", token=token).get("debug", {})
    uploads = http_json("GET", args.base_url, f"/api/v1/cases/{case_id}/uploads", token=token).get("items", [])
    upload = next((item for item in uploads if item.get("id") == upload_id), {})
    frame_summary = frame_analysis_summary(upload, args.require_frame_observations)
    agent_video_summary = agent_video_fact_summary(debug_report, args.require_agent_video_facts)
    accuracy_summary = evaluate_accuracy_expectations(frame_summary, agent_video_summary, args)
    followup_summary = (
        run_held_observation_followup(args.base_url, case_id, token, report)
        if args.exercise_held_observation_followup
        else None
    )
    conflict_followup_summary = (
        run_conflict_followup(args.base_url, case_id, token, report, agent_video_summary)
        if args.exercise_conflict_followup
        else None
    )

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
        "accuracy_expectations": accuracy_summary,
        "video_accuracy_metrics": video_accuracy_metrics(frame_summary, agent_video_summary, video_card, accuracy_summary),
        "expert_guidance_card": expert_card,
        "video_fact_card": video_card,
        "agent_process_status": card.get("status_label"),
        "agent_process_stats": card.get("stats", []),
        "agent_process_steps": [step.get("label") for step in card.get("steps", [])],
    }
    if followup_summary:
        output["held_observation_followup"] = followup_summary
    if conflict_followup_summary:
        output["conflict_followup"] = conflict_followup_summary
    if priority_summary:
        output["missing_info_priority"] = priority_summary
    if args.output_json:
        output_path = Path(args.output_json).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except E2EError as exc:
        print(f"video_agent_e2e=failed: {exc}", file=sys.stderr)
        sys.exit(1)
