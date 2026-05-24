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
FRAME_SELECTION_STRATEGY = "full-sequence-event-spread-plus-impact-context"
ENABLE_OPENAI_FRAME_ANALYSIS = os.getenv("ENABLE_OPENAI_FRAME_ANALYSIS", "0") == "1"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
OPENAI_TIMEOUT_SEC = float(os.getenv("OPENAI_TIMEOUT_SEC", "45"))
OPENAI_FRAME_ANALYSIS_MAX_FRAMES = max(1, min(18, _int_env("OPENAI_FRAME_ANALYSIS_MAX_FRAMES", 18)))
OPENAI_FRAME_ANALYSIS_MAX_OUTPUT_TOKENS = max(600, min(3000, _int_env("OPENAI_FRAME_ANALYSIS_MAX_OUTPUT_TOKENS", 2200)))
OPENAI_FRAME_ANALYSIS_ZERO_OBSERVATION_RETRY = os.getenv("OPENAI_FRAME_ANALYSIS_ZERO_OBSERVATION_RETRY", "1") == "1"
OPENAI_FRAME_ANALYSIS_RETRY_MIN_FRAMES = max(1, min(18, _int_env("OPENAI_FRAME_ANALYSIS_RETRY_MIN_FRAMES", 6)))
OPENAI_FRAME_ANALYSIS_DETAIL = os.getenv("OPENAI_FRAME_ANALYSIS_DETAIL", "high").strip().lower()
if OPENAI_FRAME_ANALYSIS_DETAIL not in {"low", "high", "auto"}:
    OPENAI_FRAME_ANALYSIS_DETAIL = "high"
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
    payload = _openai_frame_analysis_payload(selected_frames, context)
    try:
        data = _post_json(
            "https://api.openai.com/v1/responses",
            payload,
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            timeout=OPENAI_TIMEOUT_SEC,
        )
        parsed = _safe_json_loads(_openai_output_text(data)) or {}
        observations = _normalize_openai_observations(parsed.get("observations") or parsed.get("detected_events") or [], selected_frames)
        event_summary = _normalize_accident_event_summary(parsed.get("accident_event_summary"), selected_frames)
        event_summary = event_summary or _derive_accident_event_summary_from_observations(observations, selected_frames)
        attempts = [_analysis_attempt_summary("primary", data, observations, event_summary)]
        retry_error = ""
        retry_used = False
        if _should_retry_zero_observation(observations, selected_frames):
            retry_used = True
            try:
                retry_payload = _openai_frame_analysis_payload(selected_frames, context, fallback=True, prior_event_summary=event_summary)
                retry_data = _post_json(
                    "https://api.openai.com/v1/responses",
                    retry_payload,
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                    timeout=OPENAI_TIMEOUT_SEC,
                )
                retry_parsed = _safe_json_loads(_openai_output_text(retry_data)) or {}
                retry_observations = _normalize_openai_observations(
                    retry_parsed.get("observations") or retry_parsed.get("detected_events") or [],
                    selected_frames,
                )
                retry_event_summary = _normalize_accident_event_summary(retry_parsed.get("accident_event_summary"), selected_frames)
                retry_event_summary = retry_event_summary or _derive_accident_event_summary_from_observations(retry_observations, selected_frames)
                attempts.append(_analysis_attempt_summary("zero_observation_retry", retry_data, retry_observations, retry_event_summary))
                if retry_observations:
                    data = retry_data
                    parsed = retry_parsed
                    observations = retry_observations
                    event_summary = retry_event_summary or event_summary
                elif retry_event_summary and not event_summary:
                    event_summary = retry_event_summary
            except Exception as exc:
                retry_error = str(exc)
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
            "zero_observation_retry_used": retry_used,
            "zero_observation_retry_error": retry_error,
            "analysis_attempts": attempts,
            **selection_metadata,
            "analyzed_frames": [_public_frame_ref(frame) for frame in selected_frames],
            "summary": parsed.get("summary") or parsed.get("scene_summary"),
            "accident_event_summary": event_summary,
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
    object_first = _object_first_frame_indexes(frames, max_frames)
    if object_first:
        return [frames[index] for index in object_first]
    return [frames[index] for index in _event_focused_frame_indexes(len(frames), max_frames)]


def _object_first_frame_indexes(frames: list[dict[str, Any]], max_frames: int) -> list[int]:
    event_indexes = [
        index for index, frame in enumerate(frames)
        if frame.get("role") in {"accident_candidate", "event_context"}
    ]
    if not event_indexes:
        return []
    selected: list[int] = []

    def add(index: int) -> None:
        if len(selected) >= max_frames:
            return
        clamped = max(0, min(len(frames) - 1, index))
        if clamped not in selected:
            selected.append(clamped)

    add(0)
    add(len(frames) - 1)
    event_budget = max(1, max_frames - len(selected))
    distributed_events = _spread_indexes(event_indexes, min(len(event_indexes), event_budget))
    for index in distributed_events:
        add(index)
    for offset in (-1, 1, -2, 2):
        for index in distributed_events:
            add(index + offset)
            if len(selected) >= max_frames:
                return sorted(selected)
    for index in _event_focused_frame_indexes(len(frames), max_frames):
        add(index)
        if len(selected) >= max_frames:
            break
    return sorted(selected)


def _spread_indexes(indexes: list[int], count: int) -> list[int]:
    if count <= 0:
        return []
    values = sorted(dict.fromkeys(indexes))
    if count >= len(values):
        return values
    if count == 1:
        return [values[len(values) // 2]]
    selected: list[int] = []
    for step in range(count):
        pos = round(step * (len(values) - 1) / (count - 1))
        value = values[pos]
        if value not in selected:
            selected.append(value)
    return selected


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


def _openai_frame_analysis_payload(
    selected_frames: list[dict[str, Any]],
    context: dict[str, Any],
    fallback: bool = False,
    prior_event_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    content: list[dict[str, Any]] = [{
        "type": "input_text",
        "text": _openai_frame_analysis_prompt(context, fallback=fallback, prior_event_summary=prior_event_summary or {}),
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
    return payload


def _openai_frame_analysis_prompt(context: dict[str, Any], fallback: bool = False, prior_event_summary: dict[str, Any] | None = None) -> str:
    retry_intro = ""
    if fallback:
        retry_intro = (
            "This is a bounded retry because the prior pass returned zero usable observations. "
            "Focus on a small set of high-value facts that are visually supportable across the frame sequence. "
            "Do not force a fact when it is not visible, but avoid returning zero observations if any accident target, collision partner, signal, centerline, stopped vehicle, road obstruction, crosswalk context, or visible absence of pedestrian-in-path can be supported. "
            f"Prior accident_event_summary JSON: {json.dumps(prior_event_summary or {}, ensure_ascii=False)} "
        )
    return (
        f"{retry_intro}"
        "You are extracting observable traffic accident facts from dashcam frame sequence images. "
        "Return JSON only. Do not decide legal liability, insurance responsibility, or fault ratio. "
        "Use unknown and low confidence when a fact is not clearly visible. "
        "Primary task: identify the accident target/object, collision point, and collision partner first. "
        "Before writing observations, inspect every provided frame_ref in chronological order and identify the most likely actual impact/contact moment or immediate pre/post-impact window. "
        "Do not treat the first risky scene, visible pedestrian, crosswalk, parked vehicle, signal, near miss, or lane conflict as the accident merely because it appears first. "
        "If the selected sequence shows multiple possible event candidates, compare all candidates and base collision_partner_type, primary_collision_target, collision_point_visible, impact_direction, and opponent_behavior on the candidate with visible contact, abrupt impact evidence, or immediate aftermath. "
        "If no contact, impact evidence, or immediate aftermath is visible in the selected frames, say so in uncertainties and do not confirm collision-target facts. "
        "Road environment facts such as crosswalks, centerline, parked vehicles, obstacles, and signals are secondary context and must not replace collision-target identification. "
        "The Context JSON may contain user-supplied accident type or structured facts. "
        "Use it only to prioritize which visual facts to inspect; never use it as visual evidence and never copy it into observations unless the frames support it. "
        "Allowed observation fields: stopped, sudden_brake, impact_direction, collision_direction, "
        "opponent_behavior, lane_change_actor, turn_signal, user_signal, opponent_signal, "
        "opponent_signal_visible, opponent_signal_violation, signal_transition, intersection, "
        "crosswalk_nearby, pedestrian_visible, pedestrian_signal, school_zone, damage_level, "
        "centerline_crossed, centerline_cross_reason, road_obstruction, illegal_parking_obstruction, "
        "opposing_vehicle_present, opposing_vehicle_did_not_stop, secondary_collision, "
        "collision_partner_type, primary_collision_target, collision_point_visible, collision_point_location, "
        "front_vehicle_stopped, ego_turn_direction, stopped_vehicle_without_lights, highway_or_expressway, "
        "recaptured_screen, dashcam_screen_visible, screen_glare_or_reflection. "
        "Use collision_partner_type as one of vehicle, pedestrian, bicycle, motorcycle, object, unknown. "
        "Use ego_turn_direction as one of right, left, straight, u_turn, unknown. "
        "Use primary_collision_target to describe the object actually struck or striking the ego vehicle; do not use road environment as the target unless the collision is with that object. "
        "For stopped, judge whether the ego/user vehicle was stationary at or immediately before the collision. "
        "Do not mark stopped=false merely because the dashcam image changes, the camera shakes, or surrounding vehicles move. "
        "Return stopped=false only when multiple frame_refs clearly show ego/user vehicle forward movement at the relevant moment; otherwise omit stopped or use unknown. "
        "crosswalk_nearby only means a crosswalk is visible or close to the conflict area; never infer a pedestrian accident from crosswalk_nearby alone. "
        "Use pedestrian_visible=true only when a pedestrian is actually visible in or near the collision path. "
        "If a crosswalk or pedestrian signal is visible but the collision partner is a vehicle, keep collision_partner_type=vehicle and treat crosswalk_nearby/pedestrian_signal as road context only. "
        "Use pedestrian_visible=false only when the selected frames clearly show no pedestrian in the collision path; this negative fact is allowed to prevent crosswalk-only car-vs-person mistakes. "
        "For right-turn cases where a front/lead vehicle stops near a crosswalk and the ego vehicle hits that vehicle, set collision_partner_type=vehicle, front_vehicle_stopped=true, ego_turn_direction=right, and crosswalk_nearby=true when visible. "
        "Use ego_turn_direction only for an intentional left/right/U-turn at an intersection, driveway, branch, or marked turn path; do not mark right or left only because the road curves or the camera yaws. "
        "Use front_vehicle_stopped only for a lead vehicle in the same traffic stream that was stopped before impact, not for an oncoming or side vehicle after impact. "
        "For signalized intersection crashes, distinguish visible ego signal from opponent signal. If the opponent signal head is not visible, set opponent_signal_visible=false instead of guessing opponent_signal or opponent_signal_violation. "
        "If a signal changes across frames, use signal_transition to describe the observed sequence, for example green_to_yellow, yellow_to_red, red_to_green, or unknown. "
        "For high-speed roads with a stopped dark/unlit vehicle, set stopped_vehicle_without_lights=true and highway_or_expressway=true only when visually supported; do not estimate speed from frames. "
        "For narrow two-way roads, yellow centerline encroachment, parked vehicles, roadside objects, lane-blocking obstacles, oncoming vehicles, failure of an oncoming vehicle to stop, and secondary impacts, return the corresponding road-context fields when visible. "
        "If centerline crossing appears caused by a parked vehicle or obstacle, set centerline_cross_reason to parked_vehicle_obstruction or road_obstruction with frame_refs. "
        "When a vehicle crosses or straddles the centerline to pass an obstacle or parked vehicle, prefer centerline_crossed, centerline_cross_reason, road_obstruction, illegal_parking_obstruction, and opposing_vehicle_present over turn-direction labels. "
        "Do not infer injury status from frames. Do not infer absence facts such as no damage, no school zone, "
        "or no signal violation just because they are not visible. Omit fields that are not observable. "
        "Each observation must include field, value, confidence between 0 and 1, frame_refs, and reason. "
        "You may also include accident_event_summary with impact_visible, event_frame_refs, pre_impact_frame_refs, post_impact_frame_refs, and rationale; this metadata is for quality review and must not include legal conclusions. "
        f"Context JSON: {json.dumps(_compact_context(context), ensure_ascii=False)}"
    )


def _should_retry_zero_observation(observations: list[dict[str, Any]], selected_frames: list[dict[str, Any]]) -> bool:
    return (
        OPENAI_FRAME_ANALYSIS_ZERO_OBSERVATION_RETRY
        and not observations
        and len(selected_frames) >= OPENAI_FRAME_ANALYSIS_RETRY_MIN_FRAMES
    )


def _analysis_attempt_summary(label: str, data: dict[str, Any], observations: list[dict[str, Any]], event_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": label,
        "response_id": data.get("id"),
        "response_status": data.get("status"),
        "incomplete_details": data.get("incomplete_details"),
        "observation_count": len(observations),
        "event_frame_count": len(event_summary.get("event_frame_refs") or []) if isinstance(event_summary, dict) else 0,
        "impact_visible": event_summary.get("impact_visible") if isinstance(event_summary, dict) else None,
    }


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
    if mode == "conflict_stopped":
        return [
            {
                "field": "stopped",
                "value": False,
                "confidence": 0.93,
                "source": "frame_analysis:fixture",
                "detector": "fixture:conflict_stopped",
                "frame_refs": frame_refs,
                "reason": "Fixture validates video/user stopped-state conflict followup and reanalysis.",
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


def _normalize_accident_event_summary(value: Any, selected_frames: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    allowed_frame_refs = {Path(frame["path"]).name for frame in selected_frames}

    def refs(name: str) -> list[str]:
        return [str(ref) for ref in value.get(name) or [] if str(ref) in allowed_frame_refs]

    output: dict[str, Any] = {
        "impact_visible": bool(value.get("impact_visible")) if value.get("impact_visible") is not None else None,
        "event_frame_refs": refs("event_frame_refs"),
        "pre_impact_frame_refs": refs("pre_impact_frame_refs"),
        "post_impact_frame_refs": refs("post_impact_frame_refs"),
        "rationale": str(value.get("rationale") or "")[:500],
    }
    return {key: item for key, item in output.items() if item not in (None, "", [])}


def _derive_accident_event_summary_from_observations(observations: list[dict[str, Any]], selected_frames: list[dict[str, Any]]) -> dict[str, Any]:
    event_fields = {
        "collision_partner_type",
        "primary_collision_target",
        "collision_point_visible",
        "collision_point_location",
        "impact_direction",
        "collision_direction",
        "secondary_collision",
    }
    event_refs: list[str] = []
    for item in observations:
        if not isinstance(item, dict) or item.get("field") not in event_fields:
            continue
        confidence = _as_float(item.get("confidence"), 0.0)
        if confidence < 0.75:
            continue
        for ref in item.get("frame_refs") or []:
            text = str(ref)
            if text not in event_refs:
                event_refs.append(text)
    if not event_refs:
        return {}
    frame_names = [Path(frame["path"]).name for frame in selected_frames]
    event_refs = [ref for ref in event_refs if ref in frame_names]
    if not event_refs:
        return {}
    first_index = min(frame_names.index(ref) for ref in event_refs)
    last_index = max(frame_names.index(ref) for ref in event_refs)
    pre_refs = frame_names[max(0, first_index - 2):first_index]
    post_refs = frame_names[last_index + 1:last_index + 3]
    return {
        "impact_visible": True,
        "event_frame_refs": event_refs,
        "pre_impact_frame_refs": pre_refs,
        "post_impact_frame_refs": post_refs,
        "rationale": "Derived from high-confidence collision-related observations because the model omitted accident_event_summary.",
    }


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
        "centerline_crossed",
        "road_obstruction",
        "illegal_parking_obstruction",
        "opposing_vehicle_present",
        "opposing_vehicle_did_not_stop",
        "secondary_collision",
        "collision_point_visible",
        "front_vehicle_stopped",
        "intersection",
        "opponent_signal_visible",
        "stopped_vehicle_without_lights",
        "highway_or_expressway",
        "recaptured_screen",
        "dashcam_screen_visible",
        "screen_glare_or_reflection",
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
