from __future__ import annotations

from typing import Any


def initial_suggestions() -> list[dict[str, Any]]:
    return [
        {"label": "블랙박스 영상 올리는 법", "action": "send_message", "message": "블랙박스 영상 어디서 올려?"},
        {"label": "정차 중 후미추돌 사고 도움", "action": "send_message", "message": "정차 중 뒤차가 박았어. 어떻게 해야 해?"},
        {"label": "사고 상황 입력 도와줘", "action": "send_message", "message": "사고 상황 입력 도와줘"},
        {"label": "분석 결과 쉽게 설명해줘", "action": "send_message", "message": "결과가 무슨 뜻인지 모르겠어."},
        {"label": "많이 검색된 사고유형 보기", "action": "navigate", "target": "/knia/ranking"},
    ]


def build_suggestions(intent: str, draft_case: dict[str, Any] | None = None, knia_primary: dict[str, Any] | None = None, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    if intent in {"accident_quick_help", "create_case_draft"}:
        if draft_case:
            suggestions.append({"label": "이 내용으로 사고 입력하기", "action": "apply_case_draft", "payload": {"draft_case": draft_case, "knia_match": knia_primary}})
        suggestions.extend([
            {"label": "블랙박스 업로드 방법", "action": "send_message", "message": "블랙박스 영상 어디서 올려?"},
            {"label": "보험 접수 방법", "action": "send_message", "message": "보험 접수 방법 알려줘"},
            {"label": "병원 진료/진단서 확인", "action": "send_message", "message": "통증이 있는데 병원 진료가 필요할까?"},
        ])
    if intent in {"upload_help", "service_usage_help"}:
        suggestions.extend([
            {"label": "사고 입력 화면으로 이동", "action": "navigate", "target": "/cases/new"},
            {"label": "후미추돌 사고 입력 예시", "action": "send_message", "message": "후미추돌 사고로 작성해줘"},
        ])
    if intent == "report_explanation":
        suggestions.extend([
            {"label": "내 과실 10% 설명", "action": "send_message", "message": "내 과실 10%가 무슨 뜻이야?"},
            {"label": "보험 처리 다음 단계", "action": "send_message", "message": "보험 처리 다음 단계 알려줘"},
            {"label": "법률 근거 쉽게 보기", "action": "send_message", "message": "법률 근거 쉽게 설명해줘"},
        ])
    if knia_primary:
        chart_no = knia_primary.get("chart_no")
        video_url = knia_primary.get("video_url") or knia_primary.get("source_url")
        if chart_no:
            suggestions.append({"label": "비슷한 과실비율 기준 보기", "action": "navigate", "target": f"/knia/charts/{chart_no}", "payload": {"chart_no": chart_no}})
        if video_url:
            suggestions.append({"label": "관련 영상 보기", "action": "open_external", "target": video_url, "payload": {"chart_no": chart_no, "source": "KNIA"}})
    suggestions.append({"label": "많이 검색된 사고유형 보기", "action": "navigate", "target": "/knia/ranking"})
    if not suggestions:
        return initial_suggestions()
    return _dedupe(suggestions)[:9]


def violation_suggestions() -> list[dict[str, Any]]:
    return [
        {"label": "블랙박스 원본 보관 방법", "action": "send_message", "message": "블랙박스 원본 보관 방법 알려줘"},
        {"label": "보험사 제출 자료 보기", "action": "send_message", "message": "보험사에 제출할 자료 알려줘"},
        {"label": "사고 입력 페이지로 이동", "action": "navigate", "target": "/cases/new"},
    ]


def _dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        key = f"{item.get('label')}:{item.get('action')}:{item.get('target')}:{item.get('message')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out
