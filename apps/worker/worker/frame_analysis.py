import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from worker.frame_analysis_usage import aggregate_attempt_usage, openai_usage, with_openai_usage_event
from worker.frame_observations import (
    as_float,
    derive_accident_event_summary_from_observations,
    normalize_accident_event_summary,
    normalize_openai_observations,
    normalize_observation_confidence,
    observation_quality,
    observation_quality_summary,
    should_drop_openai_observation,
)
from worker.frame_selection import frame_selection_metadata, select_openai_frames


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


FRAME_ANALYSIS_CONTRACT_VERSION = "openai-frame-analysis-v1"
AI_USAGE_EVENT_VERSION = "ai-usage-event-v1"
FRAME_SELECTION_STRATEGY = "full-sequence-event-spread-plus-impact-context"
ENABLE_OPENAI_FRAME_ANALYSIS = os.getenv("ENABLE_OPENAI_FRAME_ANALYSIS", "0") == "1"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
OPENAI_TIMEOUT_SEC = float(os.getenv("OPENAI_TIMEOUT_SEC", "45"))
OPENAI_FRAME_ANALYSIS_MAX_FRAMES = max(1, min(18, _int_env("OPENAI_FRAME_ANALYSIS_MAX_FRAMES", 18)))
OPENAI_FRAME_ANALYSIS_MAX_OUTPUT_TOKENS = max(600, min(3000, _int_env("OPENAI_FRAME_ANALYSIS_MAX_OUTPUT_TOKENS", 2200)))
OPENAI_FRAME_ANALYSIS_ZERO_OBSERVATION_RETRY = os.getenv("OPENAI_FRAME_ANALYSIS_ZERO_OBSERVATION_RETRY", "1") == "1"
OPENAI_FRAME_ANALYSIS_RETRY_MIN_FRAMES = max(1, min(18, _int_env("OPENAI_FRAME_ANALYSIS_RETRY_MIN_FRAMES", 6)))
OPENAI_FRAME_ANALYSIS_ERROR_RETRY = os.getenv("OPENAI_FRAME_ANALYSIS_ERROR_RETRY", "1") == "1"
OPENAI_FRAME_ANALYSIS_DETAIL = os.getenv("OPENAI_FRAME_ANALYSIS_DETAIL", "high").strip().lower()
if OPENAI_FRAME_ANALYSIS_DETAIL not in {"low", "high", "auto"}:
    OPENAI_FRAME_ANALYSIS_DETAIL = "high"
OPENAI_FRAME_ANALYSIS_REASONING_EFFORT = os.getenv("OPENAI_FRAME_ANALYSIS_REASONING_EFFORT", "minimal").strip().lower()
FRAME_ANALYSIS_FIXTURE_MODE = os.getenv("FRAME_ANALYSIS_FIXTURE_MODE", "").strip().lower()


def analyze_frames_with_openai(frame_details: list[dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    if not ENABLE_OPENAI_FRAME_ANALYSIS:
        return _with_openai_usage_event({
            "version": FRAME_ANALYSIS_CONTRACT_VERSION,
            "enabled": False,
            "reason": "ENABLE_OPENAI_FRAME_ANALYSIS is not 1",
            **_frame_selection_metadata(frame_details, []),
        }, enabled=False, success=False, frame_details=frame_details, selected_frames=[], fallback_reason="disabled")
    selected_frames = _select_openai_frames(frame_details, OPENAI_FRAME_ANALYSIS_MAX_FRAMES)
    selection_metadata = _frame_selection_metadata(frame_details, selected_frames)
    if not selected_frames:
        return _with_openai_usage_event(
            {"version": FRAME_ANALYSIS_CONTRACT_VERSION, "enabled": False, "reason": "no frames extracted", **selection_metadata},
            enabled=False,
            success=False,
            frame_details=frame_details,
            selected_frames=[],
            fallback_reason="no_frames_extracted",
        )
    if FRAME_ANALYSIS_FIXTURE_MODE:
        return _fixture_frame_analysis(selected_frames, context, FRAME_ANALYSIS_FIXTURE_MODE, selection_metadata)
    if not OPENAI_API_KEY:
        return _with_openai_usage_event(
            {"version": FRAME_ANALYSIS_CONTRACT_VERSION, "enabled": False, "reason": "OPENAI_API_KEY is empty", **selection_metadata},
            enabled=False,
            success=False,
            frame_details=frame_details,
            selected_frames=selected_frames,
            fallback_reason="api_key_missing",
        )
    payload = _openai_frame_analysis_payload(selected_frames, context)
    attempts: list[dict[str, Any]] = []
    error_retry_used = False
    error_retry_error = ""
    try:
        attempt = _run_openai_analysis_attempt("primary", payload, selected_frames)
        data = attempt["data"]
        parsed = attempt["parsed"]
        observations = attempt["observations"]
        event_summary = attempt["event_summary"]
        attempts.append(attempt["summary"])
        retry_error = ""
        retry_used = False
        if _should_retry_zero_observation(observations, selected_frames):
            retry_used = True
            try:
                retry_payload = _openai_frame_analysis_payload(selected_frames, context, fallback=True, prior_event_summary=event_summary)
                retry_attempt = _run_openai_analysis_attempt("zero_observation_retry", retry_payload, selected_frames)
                retry_data = retry_attempt["data"]
                retry_parsed = retry_attempt["parsed"]
                retry_observations = retry_attempt["observations"]
                retry_event_summary = retry_attempt["event_summary"]
                attempts.append(retry_attempt["summary"])
                if retry_observations:
                    data = retry_data
                    parsed = retry_parsed
                    observations = retry_observations
                    event_summary = retry_event_summary or event_summary
                elif retry_event_summary and not event_summary:
                    event_summary = retry_event_summary
            except Exception as exc:
                retry_error = str(exc)
        if not observations:
            observations = _fallback_limited_visual_observations(selected_frames, event_summary)
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
            "error_retry_used": error_retry_used,
            "error_retry_error": error_retry_error,
            "analysis_attempts": attempts,
            "usage": _aggregate_attempt_usage(attempts),
            **selection_metadata,
            "analyzed_frames": [_public_frame_ref(frame) for frame in selected_frames],
            "summary": parsed.get("summary") or parsed.get("scene_summary"),
            "accident_event_summary": event_summary,
            "observations": observations,
            "observation_quality_summary": _observation_quality_summary(observations),
            "uncertainties": parsed.get("uncertainties") or _empty_output_uncertainty(data, observations),
            "created_at": _now_iso(),
        }
        result = _with_openai_usage_event(
            result,
            enabled=True,
            success=True,
            frame_details=frame_details,
            selected_frames=selected_frames,
            usage=result.get("usage"),
            response_status=result.get("response_status"),
            fallback_reason="zero_observation_retry" if retry_used else "",
            retry_count=len(attempts) - 1,
        )
        print(json.dumps({
            "event": "openai_frame_analysis",
            "model": result["model"],
            "frames": len(selected_frames),
            "usage": result.get("usage") or {},
            "observations": observations,
            "summary": result["summary"],
        }, ensure_ascii=False))
        return result
    except Exception as exc:
        primary_error = str(exc)
        attempts.append(_analysis_error_attempt_summary("primary", primary_error))
        if _should_retry_openai_error(primary_error, selected_frames):
            error_retry_used = True
            try:
                retry_payload = _openai_frame_analysis_payload(selected_frames, context, fallback=True, prior_event_summary={})
                retry_attempt = _run_openai_analysis_attempt("error_retry", retry_payload, selected_frames)
                data = retry_attempt["data"]
                parsed = retry_attempt["parsed"]
                observations = retry_attempt["observations"]
                event_summary = retry_attempt["event_summary"]
                attempts.append(retry_attempt["summary"])
                if not observations:
                    observations = _fallback_limited_visual_observations(selected_frames, event_summary)
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
                    "zero_observation_retry_used": False,
                    "zero_observation_retry_error": "",
                    "error_retry_used": True,
                    "error_retry_error": "",
                    "analysis_attempts": attempts,
                    "usage": _aggregate_attempt_usage(attempts),
                    **selection_metadata,
                    "analyzed_frames": [_public_frame_ref(frame) for frame in selected_frames],
                    "summary": parsed.get("summary") or parsed.get("scene_summary"),
                    "accident_event_summary": event_summary,
                    "observations": observations,
                    "observation_quality_summary": _observation_quality_summary(observations),
                    "uncertainties": parsed.get("uncertainties") or _empty_output_uncertainty(data, observations),
                    "created_at": _now_iso(),
                }
                return _with_openai_usage_event(
                    result,
                    enabled=True,
                    success=True,
                    frame_details=frame_details,
                    selected_frames=selected_frames,
                    usage=result.get("usage"),
                    response_status=result.get("response_status"),
                    fallback_reason="error_retry",
                    retry_count=len(attempts) - 1,
                )
            except Exception as retry_exc:
                error_retry_error = str(retry_exc)
                attempts.append(_analysis_error_attempt_summary("error_retry", error_retry_error))
        result = {
            "version": FRAME_ANALYSIS_CONTRACT_VERSION,
            "enabled": True,
            "provider": "openai",
            "model": OPENAI_VISION_MODEL,
            "detail": OPENAI_FRAME_ANALYSIS_DETAIL,
            "error": primary_error,
            "error_retry_used": error_retry_used,
            "error_retry_error": error_retry_error,
            "analysis_attempts": attempts,
            "usage": _aggregate_attempt_usage(attempts),
            **selection_metadata,
            "analyzed_frames": [_public_frame_ref(frame) for frame in selected_frames],
            "observations": [],
            "observation_quality_summary": _observation_quality_summary([]),
            "created_at": _now_iso(),
        }
        return _with_openai_usage_event(
            result,
            enabled=True,
            success=False,
            frame_details=frame_details,
            selected_frames=selected_frames,
            usage=result.get("usage"),
            response_status="error",
            fallback_reason="openai_error",
            retry_count=len(attempts) - 1,
            error=primary_error,
        )


def _select_openai_frames(frame_details: list[dict[str, Any]], max_frames: int) -> list[dict[str, Any]]:
    return select_openai_frames(frame_details, max_frames)


def _frame_selection_metadata(frame_details: list[dict[str, Any]], selected_frames: list[dict[str, Any]]) -> dict[str, Any]:
    return frame_selection_metadata(
        frame_details,
        selected_frames,
        strategy=FRAME_SELECTION_STRATEGY,
        max_frames=OPENAI_FRAME_ANALYSIS_MAX_FRAMES,
    )


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
        "non_contact_trigger, trigger_actor_type, trigger_actor_behavior, direct_collision_partner_type, rear_vehicle_collision, "
        "collision_partner_type, primary_collision_target, collision_point_visible, collision_point_location, "
        "front_vehicle_stopped, ego_turn_direction, stopped_vehicle_without_lights, highway_or_expressway, "
        "recaptured_screen, dashcam_screen_visible, screen_glare_or_reflection. "
        "Use collision_partner_type as one of vehicle, pedestrian, bicycle, motorcycle, object, unknown. "
        "Use ego_turn_direction as one of right, left, straight, u_turn, unknown. "
        "Use primary_collision_target to describe the object actually struck or striking the ego vehicle; do not use road environment as the target unless the collision is with that object. "
        "For non-contact trigger crashes, separate trigger_actor_type/trigger_actor_behavior from direct_collision_partner_type. For example, a bicycle that caused braking is a trigger actor, while a rear bus or following vehicle that physically hit the ego vehicle is the direct collision partner. "
        "Do not set collision_partner_type=bicycle merely because a bicycle appears when the visible contact is vehicle-to-vehicle or rear-end. "
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


def _should_retry_openai_error(error: str, selected_frames: list[dict[str, Any]]) -> bool:
    if not OPENAI_FRAME_ANALYSIS_ERROR_RETRY or len(selected_frames) < OPENAI_FRAME_ANALYSIS_RETRY_MIN_FRAMES:
        return False
    text = error.lower()
    transient_markers = (
        "timed out",
        "timeout",
        "temporarily unavailable",
        "connection reset",
        "remote end closed",
        "server disconnected",
    )
    return any(marker in text for marker in transient_markers)


def _fallback_limited_visual_observations(selected_frames: list[dict[str, Any]], event_summary: dict[str, Any]) -> list[dict[str, Any]]:
    if len(selected_frames) < OPENAI_FRAME_ANALYSIS_RETRY_MIN_FRAMES:
        return []
    frame_refs = [
        Path(str(frame.get("path", ""))).name
        for frame in selected_frames
        if frame.get("path")
    ]
    event_refs = [
        str(ref)
        for ref in (event_summary.get("event_frame_refs") if isinstance(event_summary, dict) else []) or []
        if str(ref) in frame_refs
    ]
    refs = event_refs or frame_refs[: min(len(frame_refs), 6)]
    if not refs:
        return []
    observations: list[dict[str, Any]] = []
    if event_refs:
        observations.append({
            "field": "accident_event_candidate",
            "value": True,
            "confidence": 0.82,
            "source": "frame_analysis:openai",
            "detector": OPENAI_VISION_MODEL,
            "frame_refs": event_refs,
            "reason": (
                "OpenAI localized a likely impact/contact window, but did not return enough reliable "
                "physical facts to apply directly."
            ),
            "observation_quality": _observation_quality("accident_event_candidate", 0.82, event_refs),
        })
    observations.append({
        "field": "visual_evidence_limited",
        "value": True,
        "confidence": 1.0,
        "source": "frame_analysis:openai",
        "detector": OPENAI_VISION_MODEL,
        "frame_refs": refs,
        "reason": (
            "OpenAI completed the frame analysis and bounded retries, but no reliable physical accident facts "
            "met the observation contract. Treat the video as available but visually insufficient for direct fact application."
        ),
        "observation_quality": _observation_quality("visual_evidence_limited", 1.0, refs),
    })
    return observations


def _run_openai_analysis_attempt(label: str, payload: dict[str, Any], selected_frames: list[dict[str, Any]]) -> dict[str, Any]:
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
    return {
        "data": data,
        "parsed": parsed,
        "observations": observations,
        "event_summary": event_summary,
        "summary": _analysis_attempt_summary(label, data, observations, event_summary),
    }


def _analysis_attempt_summary(label: str, data: dict[str, Any], observations: list[dict[str, Any]], event_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": label,
        "response_id": data.get("id"),
        "response_status": data.get("status"),
        "incomplete_details": data.get("incomplete_details"),
        "usage": _openai_usage(data),
        "observation_count": len(observations),
        "event_frame_count": len(event_summary.get("event_frame_refs") or []) if isinstance(event_summary, dict) else 0,
        "impact_visible": event_summary.get("impact_visible") if isinstance(event_summary, dict) else None,
    }


def _openai_usage(data: dict[str, Any]) -> dict[str, Any]:
    return openai_usage(data)


def _aggregate_attempt_usage(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    return aggregate_attempt_usage(attempts)


def _with_openai_usage_event(
    result: dict[str, Any],
    *,
    enabled: bool,
    success: bool,
    frame_details: list[dict[str, Any]],
    selected_frames: list[dict[str, Any]],
    usage: dict[str, Any] | None = None,
    response_status: str | None = None,
    fallback_reason: str = "",
    retry_count: int = 0,
    error: str = "",
) -> dict[str, Any]:
    return with_openai_usage_event(
        result,
        event_version=AI_USAGE_EVENT_VERSION,
        model=OPENAI_VISION_MODEL,
        max_output_tokens=OPENAI_FRAME_ANALYSIS_MAX_OUTPUT_TOKENS,
        now=_now_iso,
        enabled=enabled,
        success=success,
        frame_details=frame_details,
        selected_frames=selected_frames,
        usage=usage or {},
        response_status=response_status,
        fallback_reason=fallback_reason,
        retry_count=retry_count,
        error=error,
    )


def _analysis_error_attempt_summary(label: str, error: str) -> dict[str, Any]:
    return {
        "label": label,
        "response_status": "error",
        "error": error[:200],
        "observation_count": 0,
        "event_frame_count": 0,
        "impact_visible": None,
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
    return normalize_openai_observations(raw_observations, selected_frames, detector=OPENAI_VISION_MODEL)


def _normalize_accident_event_summary(value: Any, selected_frames: list[dict[str, Any]]) -> dict[str, Any]:
    return normalize_accident_event_summary(value, selected_frames)


def _derive_accident_event_summary_from_observations(observations: list[dict[str, Any]], selected_frames: list[dict[str, Any]]) -> dict[str, Any]:
    return derive_accident_event_summary_from_observations(observations, selected_frames)


def _normalize_observation_confidence(field: str, value: Any, confidence_value: Any, frame_refs: list[str]) -> float:
    return normalize_observation_confidence(field, value, confidence_value, frame_refs)


def _observation_quality_summary(observations: list[dict[str, Any]]) -> dict[str, Any]:
    return observation_quality_summary(observations)


def _observation_quality(field: str, confidence: float, frame_refs: list[str]) -> dict[str, Any]:
    return observation_quality(field, confidence, frame_refs)


def _should_drop_openai_observation(field: str, value: Any) -> bool:
    return should_drop_openai_observation(field, value)


def _as_float(value: Any, default: float) -> float:
    return as_float(value, default)


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
