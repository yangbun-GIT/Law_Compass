from __future__ import annotations

from typing import Any

from app.services.chat.chat_case_draft_builder import build_case_draft
from app.services.chat.chat_intent_classifier import classify_chat_intent
from app.services.chat.chat_knia_helper import find_knia_for_chat
from app.services.chat.chat_response_builder import build_chat_reply
from app.services.chat.chat_suggestion_builder import build_suggestions, initial_suggestions, violation_suggestions
from app.services.chat.chat_violation_guard import check_chat_violation


def handle_chat_message(payload: dict[str, Any]) -> dict[str, Any]:
    message = (payload.get("message") or "").strip()
    context = payload.get("context") or {}
    session_id = payload.get("session_id")
    if not message:
        return {
            "reply": "궁금한 내용을 짧게 적어 주세요. 사고 상황을 적어 주시면 입력 초안도 만들어 드릴 수 있습니다.",
            "intent": "service_usage_help",
            "suggestions": initial_suggestions(),
            "draft_case": None,
            "knia_matches": [],
            "knia_primary_match": None,
            "safety": {"allowed": True, "flags": [], "severity": "low"},
            "route_hint": None,
        }

    safety = check_chat_violation(message)
    intent = classify_chat_intent(message, context)
    if not safety.get("allowed"):
        return {
            "session_id": session_id,
            "reply": safety["safe_reply"],
            "intent": "violation",
            "suggestions": violation_suggestions(),
            "draft_case": None,
            "knia_matches": [],
            "knia_primary_match": None,
            "safety": safety,
            "route_hint": None,
        }

    draft_case = build_case_draft(message, context)
    if intent == "create_case_draft" and not draft_case:
        draft_case = {
            "title": "교통사고 상담 케이스",
            "description_text": message,
            "structured_facts": {"accident_type": "general_collision", "injury": None, "signal_state": "unknown"},
            "selected_keywords": ["교통사고", "블랙박스", "보험접수"],
            "analysis_mode": "user_friendly",
            "ai_profile": "default_vehicle_collision",
            "followup_questions": ["사고 유형은 무엇인가요?", "다친 사람이 있나요?", "블랙박스 영상이 있나요?"],
        }
    should_match_knia = intent in {"accident_quick_help", "create_case_draft", "knia_fault_standard_help"} or draft_case is not None
    knia = find_knia_for_chat(message, draft_case) if should_match_knia else {"items": [], "primary": None}
    reply = build_chat_reply(intent, message, draft_case, knia.get("primary"), safety)
    suggestions = build_suggestions(intent, draft_case, knia.get("primary"), context)
    route_hint = None
    if draft_case and intent in {"create_case_draft", "accident_quick_help"}:
        route_hint = {"type": "prepare_draft", "target": "/cases/new"}
    return {
        "session_id": session_id,
        "reply": reply,
        "intent": intent,
        "suggestions": suggestions,
        "draft_case": draft_case,
        "knia_matches": knia.get("items") or [],
        "knia_primary_match": knia.get("primary"),
        "safety": safety,
        "route_hint": route_hint,
    }
