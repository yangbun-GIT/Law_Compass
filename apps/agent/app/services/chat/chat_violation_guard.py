from __future__ import annotations

from typing import Any

HIGH_PATTERNS = {
    "prompt_injection": ["시스템 프롬프트", "개발자 지시", "이전 지시 무시", "숨겨진 규칙", "내부 토큰", "api key", "토큰 알려"],
    "evidence_tampering": ["블랙박스 조작", "영상 조작", "증거 삭제", "증거 없애", "위조", "조작하는 법"],
    "insurance_fraud": ["보험금 더 받게", "거짓말", "허위 진단서", "보험사기", "허위로 말"],
    "crime_coverup": ["뺑소니 은폐", "음주운전 숨", "무면허 숨", "경찰 피하는 법"],
    "threat": ["협박", "위협", "찾아가서 혼내", "불법 위치추적", "사찰"],
}
MEDIUM_PATTERNS = {
    "overclaim_certainty": ["무조건", "확정해", "100% 확실", "신고 안 해도 된다고", "몇 대 몇 확정"],
    "sensitive_data": ["주민등록번호", "카드번호", "비밀번호", "계좌번호 전체"],
}


def check_chat_violation(message: str) -> dict[str, Any]:
    text = message or ""
    flags: list[str] = []
    for flag, words in HIGH_PATTERNS.items():
        if any(w.lower() in text.lower() for w in words):
            flags.append(flag)
    if flags:
        return {
            "allowed": False,
            "flags": flags,
            "severity": "high",
            "safe_reply": "그 요청은 도와드릴 수 없습니다. 대신 사고 자료를 안전하게 보관하고, 보험사나 경찰에 제출할 자료를 정리하는 방법은 안내해 드릴 수 있습니다.",
        }
    for flag, words in MEDIUM_PATTERNS.items():
        if any(w.lower() in text.lower() for w in words):
            flags.append(flag)
    if flags:
        return {
            "allowed": True,
            "flags": flags,
            "severity": "medium",
            "safe_reply": "확정 판단은 도와드릴 수 없습니다. 다만 참고용 안내와 확인해야 할 체크리스트는 알려드릴 수 있습니다.",
        }
    return {"allowed": True, "flags": [], "severity": "low", "safe_reply": None}
