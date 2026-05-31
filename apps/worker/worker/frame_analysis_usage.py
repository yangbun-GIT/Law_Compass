from typing import Any, Callable


FAILURE_OBSERVATION_VERSION = "failure-observation-v1"


def safe_failure_observation(
    *,
    code: str,
    source: str,
    stage: str,
    safe_message: str,
    severity: str = "warning",
    recoverable: bool = True,
    retryable: bool = False,
    fallback_reason: str = "",
    error_type: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    observation: dict[str, Any] = {
        "version": FAILURE_OBSERVATION_VERSION,
        "code": safe_token(code, "unknown_failure"),
        "source": safe_token(source, "unknown"),
        "stage": safe_token(stage, "unknown"),
        "severity": safe_token(severity, "warning"),
        "recoverable": bool(recoverable),
        "retryable": bool(retryable),
        "safe_message": safe_message.strip() or "분석 과정에서 확인 가능한 오류가 발생했습니다.",
    }
    if fallback_reason:
        observation["fallback_reason"] = safe_token(fallback_reason, "fallback")
    if error_type:
        observation["error_type"] = safe_token(error_type, "error")
    safe_metadata = sanitize_metadata(metadata or {})
    if safe_metadata:
        observation["metadata"] = safe_metadata
    return observation


def extend_failure_observations(result: dict[str, Any], observations: list[dict[str, Any]]) -> dict[str, Any]:
    if not observations:
        return result
    existing = result.get("failure_observations")
    merged = [item for item in existing if isinstance(item, dict)] if isinstance(existing, list) else []
    merged.extend(observations)
    updated = dict(result)
    updated["failure_observations"] = merged
    return updated


def openai_usage(data: dict[str, Any]) -> dict[str, Any]:
    raw = data.get("usage")
    if not isinstance(raw, dict):
        return {}
    input_tokens = usage_int(raw.get("input_tokens") or raw.get("prompt_tokens"))
    output_tokens = usage_int(raw.get("output_tokens") or raw.get("completion_tokens"))
    total_tokens = usage_int(raw.get("total_tokens"))
    if not total_tokens:
        total_tokens = input_tokens + output_tokens
    output: dict[str, Any] = {}
    if input_tokens:
        output["input_tokens"] = input_tokens
    if output_tokens:
        output["output_tokens"] = output_tokens
    if total_tokens:
        output["total_tokens"] = total_tokens
    return output


def aggregate_attempt_usage(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    for attempt in attempts:
        usage = attempt.get("usage") if isinstance(attempt, dict) else {}
        if not isinstance(usage, dict):
            continue
        for key in totals:
            totals[key] += usage_int(usage.get(key))
    return {key: value for key, value in totals.items() if value > 0}


def with_openai_usage_event(
    result: dict[str, Any],
    *,
    event_version: str,
    model: str,
    max_output_tokens: int,
    now: Callable[[], str],
    enabled: bool,
    success: bool,
    frame_details: list[dict[str, Any]],
    selected_frames: list[dict[str, Any]],
    usage: dict[str, Any] | None = None,
    response_status: str | None = None,
    fallback_reason: str = "",
    retry_count: int = 0,
    error: str = "",
    timeout_sec: float | int | None = None,
) -> dict[str, Any]:
    updated = dict(result)
    attempts = result.get("analysis_attempts") if isinstance(result.get("analysis_attempts"), list) else []
    attempt_count = len(attempts)
    latency_ms = sum(usage_int(attempt.get("latency_ms")) for attempt in attempts if isinstance(attempt, dict))
    updated["ai_usage_event"] = openai_usage_event(
        event_version=event_version,
        model=model,
        max_output_tokens=max_output_tokens,
        now=now,
        enabled=enabled,
        success=success,
        frame_details=frame_details,
        selected_frames=selected_frames,
        usage=usage or {},
        response_status=response_status,
        fallback_reason=fallback_reason,
        retry_count=retry_count,
        error=error,
        attempt_count=attempt_count,
        latency_ms=latency_ms,
        timeout_sec=timeout_sec,
    )
    return updated


def openai_usage_event(
    *,
    event_version: str,
    model: str,
    max_output_tokens: int,
    now: Callable[[], str],
    enabled: bool,
    success: bool,
    frame_details: list[dict[str, Any]],
    selected_frames: list[dict[str, Any]],
    usage: dict[str, Any],
    response_status: str | None,
    fallback_reason: str,
    retry_count: int,
    error: str,
    attempt_count: int = 0,
    latency_ms: int = 0,
    timeout_sec: float | int | None = None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "version": event_version,
        "provider": "openai",
        "endpoint": "responses",
        "model": model,
        "enabled": bool(enabled),
        "success": bool(success),
        "frame_count": len(frame_details),
        "selected_frame_count": len(selected_frames),
        "max_output_tokens": max_output_tokens,
        "retry_count": max(0, int(retry_count or 0)),
        "attempt_count": max(0, int(attempt_count or 0)),
        "created_at": now(),
    }
    event["latency_ms"] = usage_int(latency_ms)
    if timeout_sec is not None:
        try:
            event["timeout_sec"] = float(timeout_sec)
        except (TypeError, ValueError):
            pass
    if response_status:
        event["response_status"] = str(response_status)
    safe_usage = {key: usage_int(usage.get(key)) for key in ("input_tokens", "output_tokens", "total_tokens") if usage_int(usage.get(key))}
    if safe_usage:
        event["usage"] = safe_usage
    if fallback_reason:
        event["fallback_reason"] = fallback_reason
    if error:
        event["error_type"] = "openai_frame_analysis_error"
    return event


def usage_int(value: Any) -> int:
    try:
        number = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return max(0, number)


def safe_token(value: Any, fallback: str) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return fallback
    allowed = []
    for char in text[:80]:
        if char.isalnum() or char in {"_", "-", ".", ":"}:
            allowed.append(char)
        elif char.isspace():
            allowed.append("_")
    cleaned = "".join(allowed).strip("_")
    return cleaned or fallback


def sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        safe_key = safe_token(key, "")
        if not safe_key:
            continue
        if isinstance(value, bool) or value is None:
            safe[safe_key] = value
        elif isinstance(value, (int, float)):
            safe[safe_key] = value
        elif isinstance(value, str):
            safe[safe_key] = safe_token(value, "value")[:80]
    return safe
