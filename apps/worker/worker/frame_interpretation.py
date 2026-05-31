from __future__ import annotations

from pathlib import Path
from typing import Any

DISPLAY_CONFIDENCE_MIN = 0.65
UNCERTAIN_TOKENS = {
    "unclear",
    "unknown",
    "uncertain",
    "maybe",
    "추정",
    "불명확",
    "확인 필요",
    "모름",
}
INTERNAL_CARD_KEYS = {"path", "storage_path", "local_cache_path", "raw_prompt", "prompt", "system_prompt"}


def build_frame_interpretation_cards(
    vision_result: dict[str, Any] | None,
    selected_frames: list[dict[str, Any]] | None,
    observations: list[dict[str, Any]] | None,
    event_summary: dict[str, Any] | None = None,
    *,
    case_id: str = "",
    upload_id: str = "",
) -> list[dict[str, Any]]:
    """Build display-gated frame cards from processed frame observations.

    Cards intentionally expose only stable frame refs and compact observations. Local paths,
    storage paths, raw prompts, and low-confidence guesses are not copied into the payload.
    """

    if not _analysis_succeeded(vision_result) and not observations:
        return []

    frame_by_ref = _frame_lookup(selected_frames or [])
    if not frame_by_ref:
        return []

    clean_observations = [_sanitize_observation(item) for item in observations or [] if isinstance(item, dict)]
    clean_observations = [item for item in clean_observations if item]
    event_refs = {_basename(ref) for ref in _as_list((event_summary or {}).get("event_frame_refs"))}
    impact_visible = (event_summary or {}).get("impact_visible") is True
    cards: list[dict[str, Any]] = []

    for frame_ref, frame in frame_by_ref.items():
        frame_observations = [
            item for item in clean_observations
            if frame_ref in {_basename(ref) for ref in _as_list(item.get("frame_refs") or item.get("frame_ref"))}
        ]
        strong_facts = [item for item in frame_observations if _displayable_observation(item)]
        is_event_frame = frame_ref in event_refs or _event_phase(frame, event_summary) != "context"
        repeated = any(len(_as_list(item.get("frame_refs"))) >= 2 for item in strong_facts)
        display_allowed = bool(strong_facts) and (is_event_frame or repeated or impact_visible)
        confidence = max([_to_float(item.get("confidence")) for item in strong_facts] or [0.0])

        card = {
            "frame_ref": frame_ref,
            "time_sec": _to_float(frame.get("time_sec") or frame.get("timestamp_sec")),
            "event_phase": _event_phase(frame, event_summary),
            "interpretation_summary": _summary_for(strong_facts, display_allowed),
            "judgment_reason": _reason_for(strong_facts, event_summary, display_allowed),
            "observed_facts": strong_facts[:4],
            "confidence": round(confidence, 3),
            "event_probability": round(confidence, 3),
            "visibility": "clear" if confidence >= 0.8 else "medium" if confidence >= DISPLAY_CONFIDENCE_MIN else "limited",
            "display_allowed": display_allowed,
            "image_ref": _image_ref(frame, frame_ref, case_id=case_id, upload_id=upload_id),
        }
        cards.append(_without_internal_keys(card))

    return cards


def _analysis_succeeded(result: dict[str, Any] | None) -> bool:
    if not isinstance(result, dict):
        return False
    usage = result.get("ai_usage_event") if isinstance(result.get("ai_usage_event"), dict) else {}
    if usage.get("success") is False:
        return False
    if result.get("enabled") is False:
        return False
    return True


def _frame_lookup(frames: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for frame in frames:
        if not isinstance(frame, dict):
            continue
        ref = _basename(frame.get("frame_ref") or frame.get("storage_key") or frame.get("path") or frame.get("filename"))
        if ref:
            out[ref] = frame
    return out


def _sanitize_observation(item: dict[str, Any]) -> dict[str, Any]:
    field = _safe_text(item.get("field") or item.get("label"))
    value = _safe_text(item.get("value") or item.get("description"))
    source = _safe_text(item.get("source") or "vision")
    confidence = _to_float(item.get("confidence"))
    if not field or not value:
        return {}
    return {
        "field": field,
        "value": value,
        "source": source,
        "confidence": round(confidence, 3),
        "reason": _safe_text(item.get("reason") or item.get("rationale") or item.get("explanation")),
        "frame_refs": [_basename(ref) for ref in _as_list(item.get("frame_refs") or item.get("frame_ref")) if _basename(ref)],
    }


def _displayable_observation(item: dict[str, Any]) -> bool:
    confidence = _to_float(item.get("confidence"))
    joined = f"{item.get('field', '')} {item.get('value', '')} {item.get('source', '')}".lower()
    if confidence < DISPLAY_CONFIDENCE_MIN:
        return False
    if any(token in joined for token in UNCERTAIN_TOKENS):
        return False
    source = str(item.get("source") or "").lower()
    return source.startswith(("vision", "openai", "yolo", "frame"))


def _summary_for(facts: list[dict[str, Any]], display_allowed: bool) -> str:
    if not display_allowed:
        return "프레임상 확정적으로 표시할 수 있는 영상 단서가 부족합니다."
    labels = [_safe_text(item.get("value")) for item in facts[:2]]
    labels = [item for item in labels if item]
    if labels:
        return "선별 프레임에서 " + ", ".join(labels) + " 단서를 확인했습니다."
    return "선별 프레임에서 확인 가능한 영상 단서를 정리했습니다."


def _reason_for(facts: list[dict[str, Any]], event_summary: dict[str, Any] | None, display_allowed: bool) -> str:
    if not display_allowed:
        return ""
    rationale = _safe_text((event_summary or {}).get("rationale") or (event_summary or {}).get("reason"))
    if rationale:
        return rationale
    reasons = [_safe_text(item.get("reason")) for item in facts if item.get("reason")]
    reasons = [item for item in reasons if item]
    if reasons:
        return reasons[0]
    labels = [_safe_text(item.get("field")) for item in facts[:2] if item.get("field")]
    return " / ".join(label for label in labels if label)


def _event_phase(frame: dict[str, Any], event_summary: dict[str, Any] | None) -> str:
    role = str(frame.get("role") or frame.get("selection_reason") or "").lower()
    if any(token in role for token in ["impact", "collision", "event", "accident"]):
        return "event"
    event_refs = {_basename(ref) for ref in _as_list((event_summary or {}).get("event_frame_refs"))}
    ref = _basename(frame.get("frame_ref") or frame.get("storage_key") or frame.get("path"))
    return "event" if ref in event_refs else "context"


def _image_ref(frame: dict[str, Any], frame_ref: str, *, case_id: str, upload_id: str) -> dict[str, str]:
    storage_key = _safe_text(frame.get("storage_key"))
    payload = {
        "case_id": _safe_text(case_id),
        "upload_id": _safe_text(upload_id),
        "frame_ref": frame_ref,
    }
    if storage_key:
        payload["storage_key"] = storage_key
    return payload


def _without_internal_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_internal_keys(item)
            for key, item in value.items()
            if key not in INTERNAL_CARD_KEYS
        }
    if isinstance(value, list):
        return [_without_internal_keys(item) for item in value]
    return value


def _safe_text(value: Any) -> str:
    text = str(value or "").replace("\x00", "").strip()
    if not text:
        return ""
    for token in ("C:\\", "/app/storage", "/tmp/", "\\storage\\"):
        if token.lower() in text.lower():
            return ""
    return " ".join(text.split())


def _basename(value: Any) -> str:
    text = str(value or "").replace("\\", "/").strip()
    if not text:
        return ""
    return Path(text).name


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _to_float(value: Any, fallback: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(0.0, min(1.0, number))
