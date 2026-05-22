import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


FRAME_ANALYSIS_CONTRACT_VERSION = "openai-frame-analysis-v1"
ENABLE_OPENAI_FRAME_ANALYSIS = os.getenv("ENABLE_OPENAI_FRAME_ANALYSIS", "0") == "1"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
OPENAI_TIMEOUT_SEC = float(os.getenv("OPENAI_TIMEOUT_SEC", "18"))
OPENAI_FRAME_ANALYSIS_MAX_FRAMES = max(1, min(8, _int_env("OPENAI_FRAME_ANALYSIS_MAX_FRAMES", 6)))
OPENAI_FRAME_ANALYSIS_MAX_OUTPUT_TOKENS = max(300, min(1400, _int_env("OPENAI_FRAME_ANALYSIS_MAX_OUTPUT_TOKENS", 900)))
OPENAI_FRAME_ANALYSIS_DETAIL = os.getenv("OPENAI_FRAME_ANALYSIS_DETAIL", "low").strip().lower()
if OPENAI_FRAME_ANALYSIS_DETAIL not in {"low", "high", "auto"}:
    OPENAI_FRAME_ANALYSIS_DETAIL = "low"
OPENAI_FRAME_ANALYSIS_REASONING_EFFORT = os.getenv("OPENAI_FRAME_ANALYSIS_REASONING_EFFORT", "minimal").strip().lower()
FRAME_ANALYSIS_FIXTURE_MODE = os.getenv("FRAME_ANALYSIS_FIXTURE_MODE", "").strip().lower()


def analyze_frames_with_openai(frame_details: list[dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    if not ENABLE_OPENAI_FRAME_ANALYSIS:
        return {"version": FRAME_ANALYSIS_CONTRACT_VERSION, "enabled": False, "reason": "ENABLE_OPENAI_FRAME_ANALYSIS is not 1"}
    selected_frames = _select_openai_frames(frame_details, OPENAI_FRAME_ANALYSIS_MAX_FRAMES)
    if not selected_frames:
        return {"version": FRAME_ANALYSIS_CONTRACT_VERSION, "enabled": False, "reason": "no frames extracted"}
    if FRAME_ANALYSIS_FIXTURE_MODE:
        return _fixture_frame_analysis(selected_frames, context, FRAME_ANALYSIS_FIXTURE_MODE)
    if not OPENAI_API_KEY:
        return {"version": FRAME_ANALYSIS_CONTRACT_VERSION, "enabled": False, "reason": "OPENAI_API_KEY is empty"}
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
        "max_output_tokens": OPENAI_FRAME_ANALYSIS_MAX_OUTPUT_TOKENS,
        "store": False,
        "text": _text_options_for_model(OPENAI_VISION_MODEL),
        "input": [{"role": "user", "content": content}],
    }
    payload.update(_generation_controls_for_model(OPENAI_VISION_MODEL))
    try:
        data = _post_json(
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
            "max_output_tokens": OPENAI_FRAME_ANALYSIS_MAX_OUTPUT_TOKENS,
            "response_id": data.get("id"),
            "response_status": data.get("status"),
            "incomplete_details": data.get("incomplete_details"),
            "analyzed_frames": [_public_frame_ref(frame) for frame in selected_frames],
            "summary": parsed.get("summary") or parsed.get("scene_summary"),
            "observations": observations,
            "uncertainties": parsed.get("uncertainties") or _empty_output_uncertainty(data, observations),
            "created_at": _now_iso(),
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
            "detail": OPENAI_FRAME_ANALYSIS_DETAIL,
            "error": str(exc),
            "analyzed_frames": [_public_frame_ref(frame) for frame in selected_frames],
            "observations": [],
            "created_at": _now_iso(),
        }


def _select_openai_frames(frame_details: list[dict[str, Any]], max_frames: int) -> list[dict[str, Any]]:
    frames = [frame for frame in frame_details if frame.get("path") and Path(frame["path"]).exists()]
    if len(frames) <= max_frames:
        return frames
    if max_frames == 1:
        return [frames[len(frames) // 2]]
    return [frames[round(idx * (len(frames) - 1) / (max_frames - 1))] for idx in range(max_frames)]


def _text_options_for_model(model: str) -> dict[str, Any]:
    options: dict[str, Any] = {"format": {"type": "json_object"}}
    if _is_gpt5_family(model):
        options["verbosity"] = "low"
    return options


def _generation_controls_for_model(model: str) -> dict[str, Any]:
    if _is_gpt5_family(model):
        return {"reasoning": {"effort": _normalized_reasoning_effort(model)}}
    return {"temperature": 0}


def _is_gpt5_family(model: str) -> bool:
    return model.strip().lower().startswith("gpt-5")


def _normalized_reasoning_effort(model: str) -> str:
    requested = OPENAI_FRAME_ANALYSIS_REASONING_EFFORT
    if model.strip().lower().startswith(("gpt-5.1", "gpt-5.2")):
        allowed = {"none", "low", "medium", "high"}
        return requested if requested in allowed else "none"
    allowed = {"minimal", "low", "medium", "high"}
    return requested if requested in allowed else "minimal"


def _fixture_frame_analysis(selected_frames: list[dict[str, Any]], context: dict[str, Any], mode: str) -> dict[str, Any]:
    frame_refs = [Path(str(frame.get("path", ""))).name for frame in selected_frames if frame.get("path")]
    primary_ref = frame_refs[:2] or ["fixture-frame.jpg"]
    observations = _fixture_observations(mode, primary_ref)
    return {
        "version": FRAME_ANALYSIS_CONTRACT_VERSION,
        "enabled": True,
        "provider": "fixture",
        "model": f"fixture:{mode}",
        "detail": "fixture",
        "analyzed_frames": [_public_frame_ref(frame) for frame in selected_frames],
        "summary": _fixture_summary(mode, context),
        "observations": observations,
        "uncertainties": [],
        "created_at": _now_iso(),
    }


def _fixture_observations(mode: str, frame_refs: list[str]) -> list[dict[str, Any]]:
    if mode == "rear_end":
        return [
            {
                "field": "stopped",
                "value": True,
                "confidence": 0.91,
                "source": "frame_analysis:fixture",
                "detector": "fixture:rear_end",
                "frame_refs": frame_refs,
                "reason": "Fixture validates that stationary front-vehicle facts can pass the video contract.",
            },
            {
                "field": "impact_direction",
                "value": "rear",
                "confidence": 0.9,
                "source": "frame_analysis:fixture",
                "detector": "fixture:rear_end",
                "frame_refs": frame_refs,
                "reason": "Fixture validates rear-impact mapping to opponent rear collision behavior.",
            },
        ]
    if mode == "lane_change":
        return [
            {
                "field": "lane_change_actor",
                "value": "opponent",
                "confidence": 0.88,
                "source": "frame_analysis:fixture",
                "detector": "fixture:lane_change",
                "frame_refs": frame_refs,
                "reason": "Fixture validates lane-change actor observations.",
            }
        ]
    return []


def _fixture_summary(mode: str, context: dict[str, Any]) -> str:
    return f"Local frame-analysis fixture '{mode}' generated observations for upload {context.get('upload_id') or 'unknown'}."


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


def _empty_output_uncertainty(data: dict[str, Any], observations: list[dict[str, Any]]) -> list[str]:
    if observations or _openai_output_text(data).strip():
        return []
    status = data.get("status") or "unknown"
    incomplete = data.get("incomplete_details")
    return [f"OpenAI response returned no output_text; status={status}; incomplete_details={incomplete}"]


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


def _post_json(url: str, payload: dict, headers: dict[str, str] | None = None, timeout: float = 25):
    import urllib.request

    req = urllib.request.Request(
        url,
        method="POST",
        headers={"Content-Type": "application/json", **(headers or {})},
        data=json.dumps(payload).encode("utf-8"),
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
