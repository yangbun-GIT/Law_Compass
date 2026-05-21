from __future__ import annotations

from typing import Literal

ChatIntent = Literal[
    "service_usage_help",
    "accident_quick_help",
    "create_case_draft",
    "upload_help",
    "report_explanation",
    "knia_fault_standard_help",
    "insurance_help",
    "medical_help",
    "legal_general_help",
    "navigation",
    "smalltalk",
    "unsupported",
    "violation",
]


def classify_chat_intent(message: str, context: dict | None = None) -> ChatIntent:
    text = (message or "").lower()
    if any(w in text for w in ["시스템 프롬프트", "개발자 지시", "이전 지시 무시", "숨겨진 규칙", "내부 토큰", "보험사기", "허위 진단서", "블랙박스 조작", "증거 삭제", "뺑소니 은폐"]):
        return "violation"
    if any(w in text for w in ["안녕", "고마워", "감사", "반가워"]):
        return "smalltalk"
    if any(w in text for w in ["영상", "블랙박스", "업로드", "파일 올", "동영상"]):
        if any(w in text for w in ["어디", "방법", "어떻게", "올려"]):
            return "upload_help"
    if any(w in text for w in ["많이 검색", "검색순위", "랭킹", "사고유형 보기"]):
        return "knia_fault_standard_help"
    if any(w in text for w in ["후미", "뒤차", "박았", "추돌", "교차로", "신호위반", "차선", "횡단보도", "어린이보호구역", "사고났", "사고 났", "사람", "보행자", "자전거", "가드레일", "시설물", "기물", "혼자", "단독", "미끄러"]):
        return "accident_quick_help"
    if any(w in text for w in ["차41", "차43", "knia", "과실비율정보", "인정기준", "비슷한 기준", "관련 영상", "영상도 볼"]):
        return "knia_fault_standard_help"
    if any(w in text for w in ["입력해줘", "작성해줘", "초안", "케이스 만들어", "사고 입력"]):
        return "create_case_draft"
    if any(w in text for w in ["보험", "대인", "대물", "접수", "합의", "서류"]):
        return "insurance_help"
    if any(w in text for w in ["병원", "진단서", "목", "허리", "통증", "아파"]):
        return "medical_help"
    if any(w in text for w in ["신고", "형사", "12대", "중과실", "경찰", "법률"]):
        return "legal_general_help"
    if any(w in text for w in ["결과", "리포트", "내 과실", "무슨 뜻"]):
        return "report_explanation"
    if any(w in text for w in ["어디", "페이지", "이동", "메뉴", "사용법"]):
        return "service_usage_help"
    return "unsupported"
