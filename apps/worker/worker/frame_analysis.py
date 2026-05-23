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
FRAME_SELECTION_STRATEGY = "start-end-context-plus-midpoint-sequence"
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
        return {
            "version": FRAME_ANALYSIS_CONTRACT_VERSION,
            "enabled": False,
            "reason": "ENABLE_OPENAI_FRAME_ANALYSIS is not 1",
            **_frame_selection_metadata(frame_details, []),
        }
    selected_frames = _select_openai_frames(frame_details, OPENAI_FRAME_ANALYSIS_MAX_FRAMES)
    selection_metadata = _frame_selection_metadata(frame_details, selected_frames)
    if not selected_frames:
        return {"version": FRAME_ANALYSIS_CONTRACT_VERSION, "enabled": False, "reason": "no frames extracted", **selection_metadata}
    if FRAME_ANALYSIS_FIXTURE_MODE:
        return _fixture_frame_analysis(selected_frames, context, FRAME_ANALYSIS_FIXTURE_MODE, selection_metadata)
    if not OPENAI_API_KEY:
        return {"version": FRAME_ANALYSIS_CONTRACT_VERSION, "enabled": False, "reason": "OPENAI_API_KEY is empty", **selection_metadata}
    content: list[dict[str, Any]] = [{
        "type": "input_text",
        "text": (
            "You are extracting observable traffic accident facts from dashcam frame sequence images. "
            "Return JSON only. Do not decide legal liability, insurance responsibility, or fault ratio. "
            "Use unknown and low confidence when a fact is not clearly visible. "
            "The Context JSON may contain user-supplied accident type or structured facts. "
            "Use it only to prioritize which visual facts to inspect; never use it as visual evidence and never copy it into observations unless the frames support it. "
            "Allowed observation fields: stopped, sudden_brake, impact_direction, collision_direction, "
            "opponent_behavior, lane_change_actor, turn_signal, user_signal, opponent_signal, "
            "opponent_signal_violation, crosswalk_nearby, school_zone, damage_level. "
            "For stopped, judge whether the ego/user vehicle was stationary at or immediately before the collision. "
            "Do not mark stopped=false merely because the dashcam image changes, the camera shakes, or surrounding vehicles move. "
            "Return stopped=false only when multiple frame_refs clearly show ego/user vehicle forward movement at the relevant moment; otherwise omit stopped or use unknown. "
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
            **selection_metadata,
            "analyzed_frames": [_public_frame_ref(frame) for frame in selected_frames],
            "summary": parsed.get("summary") or parsed.get("scene_summary"),
            "observations": observations,
            "observation_quality_summary": _observation_quality_summary(observations),
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
            **selection_metadata,
            "analyzed_frames": [_public_frame_ref(frame) for frame in selected_frames],
            "observations": [],
            "observation_quality_summary": _observation_quality_summary([]),
            "created_at": _now_iso(),
        }


def _select_openai_frames(frame_details: list[dict[str, Any]], max_frames: int) -> list[dict[str, Any]]:
    frames = [frame for frame in frame_details if frame.get("path") and Path(frame["path"]).exists()]
    if len(frames) <= max_frames:
        return frames
    if max_frames == 1:
        return [frames[len(frames) // 2]]
    return [frames[index] for index in _event_focused_frame_indexes(len(frames), max_frames)]


def _event_focused_frame_indexes(frame_count: int, max_frames: int) -> list[int]:
    if frame_count <= max_frames:
        return list(range(frame_count))
    if max_frames <= 1:
        return [frame_count // 2]

    midpoint = frame_count // 2
    anchors = [
        0,
        frame_count - 1,
        midpoint,
        midpoint - 1,
        midpoint + 1,
        round((frame_count - 1) * 0.35),
        round((frame_count - 1) * 0.65),
    ]
    selected: list[int] = []
    for index in anchors:
        clamped = max(0, min(frame_count - 1, index))
        if clamped not in selected:
            selected.append(clamped)
        if len(selected) >= max_frames:
            return sorted(selected)

    for step in range(max_frames):
        index = round(step * (frame_count - 1) / (max_frames - 1))
        if index not in selected:
            selected.append(index)
        if len(selected) >= max_frames:
            break
    return sorted(selected)


def _frame_selection_metadata(frame_details: list[dict[str, Any]], selected_frames: list[dict[str, Any]]) -> dict[str, Any]:
    available_frame_count = len([frame for frame in frame_details if frame.get("path") and Path(frame["path"]).exists()])
    return {
        "frame_selection_strategy": FRAME_SELECTION_STRATEGY,
        "available_frame_count": available_frame_count,
        "selected_frame_count": len(selected_frames),
        "frame_selection_max_frames": OPENAI_FRAME_ANALYSIS_MAX_FRAMES,
    }


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


def _fixture_frame_analysis(
    selected_frames: list[dict[str, Any]],
    context: dict[str, Any],
    mode: str,
    selection_metadata: dict[str, Any],
) -> dict[str, Any]:
    frame_refs = [Path(str(frame.get("path", ""))).name for frame in selected_frames if frame.get("path")]
    primary_ref = frame_refs[:2] or ["fixture-frame.jpg"]
    observations = _fixture_observations(mode, primary_ref)
    for observation in observations:
        observation.setdefault(
            "observation_quality",
            _observation_quality(str(observation.get("field") or ""), _as_float(observation.get("confidence"), 0.0), observation.get("frame_refs") or []),
        )
    return {
        "version": FRAME_ANALYSIS_CONTRACT_VERSION,
        "enabled": True,
        "provider": "fixture",
        "model": f"fixture:{mode}",
        "detail": "fixture",
        **selection_metadata,
        "analyzed_frames": [_public_frame_ref(frame) for frame in selected_frames],
        "summary": _fixture_summary(mode, context),
        "observations": observations,
        "observation_quality_summary": _observation_quality_summary(observations),
        "uncertainties": [],
        "created_at": _now_iso(),
    }


def _fixture_observations(mode: str, frame_refs: list[str]) -> list[dict[str, Any]]:
    if mode == "rear_end":
        return [
            {
                "field": "stopped",
                "value": True,
                "confidence": 0.96,
                "source": "frame_analysis:fixture",
                "detector": "fixture:rear_end",
                "frame_refs": frame_refs,
                "reason": "Fixture validates that stationary front-vehicle facts can pass the video contract.",
            },
            {
                "field": "impact_direction",
                "value": "rear",
                "confidence": 0.96,
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
                "confidence": 0.94,
                "source": "frame_analysis:fixture",
                "detector": "fixture:lane_change",
                "frame_refs": frame_refs,
                "reason": "Fixture validates lane-change actor observations.",
            }
        ]
    if mode == "held_quality":
        return [
            {
                "field": "turn_signal",
                "value": True,
                "confidence": 0.42,
                "source": "frame_analysis:fixture",
                "detector": "fixture:held_quality",
                "frame_refs": frame_refs,
                "reason": "Fixture validates that low-confidence frame observations become user followup questions.",
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
        confidence = _normalize_observation_confidence(field, value, item.get("confidence"), frame_refs)
        observations.append({
            "field": field,
            "value": value,
            "confidence": confidence,
            "source": "frame_analysis:openai",
            "detector": OPENAI_VISION_MODEL,
            "frame_refs": frame_refs,
            "reason": str(item.get("reason") or item.get("evidence") or ""),
            "observation_quality": _observation_quality(field, confidence, frame_refs),
        })
    return observations


def _normalize_observation_confidence(field: str, value: Any, confidence_value: Any, frame_refs: list[str]) -> float:
    confidence = _as_float(confidence_value, 0.0)
    if field == "stopped" and value is False:
        # Moving dashcam pixels are easy to overread as "not stopped".
        # Keep negative stopped observations below Agent fact threshold unless
        # a later provider adds stronger motion evidence in the contract.
        if len(frame_refs) < 3:
            return min(confidence, 0.74)
        return min(confidence, 0.81)
    return confidence


def _observation_quality_summary(observations: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {"high": 0, "medium": 0, "low": 0, "none": 0}
    no_frame_ref = 0
    single_frame = 0
    multi_frame = 0
    for item in observations:
        quality = item.get("observation_quality") if isinstance(item.get("observation_quality"), dict) else {}
        level = str(quality.get("level") or "none")
        counts[level if level in counts else "none"] += 1
        frame_count = len(item.get("frame_refs") or []) if isinstance(item.get("frame_refs"), list) else 0
        if frame_count == 0:
            no_frame_ref += 1
        elif frame_count == 1:
            single_frame += 1
        else:
            multi_frame += 1
    return {
        "observation_count": len(observations),
        "quality_counts": counts,
        "no_frame_reference_count": no_frame_ref,
        "single_frame_observation_count": single_frame,
        "multi_frame_observation_count": multi_frame,
    }


def _observation_quality(field: str, confidence: float, frame_refs: list[str]) -> dict[str, Any]:
    frame_count = len(frame_refs)
    flags: list[str] = []
    if frame_count == 0:
        flags.append("missing_frame_reference")
    elif frame_count == 1:
        flags.append("single_frame_observation")
    if confidence < 0.75:
        flags.append("low_confidence")
    if confidence >= 0.9 and frame_count >= 2:
        level = "high"
    elif confidence >= 0.82 and frame_count >= 1:
        level = "medium"
    elif confidence >= 0.75:
        level = "low"
    else:
        level = "none"
    return {
        "level": level,
        "frame_ref_count": frame_count,
        "confidence": confidence,
        "field": field,
        "risk_flags": flags,
    }


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
