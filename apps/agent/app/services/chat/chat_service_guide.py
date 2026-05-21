from __future__ import annotations

from typing import Any


def service_guide(intent: str, message: str, context: dict[str, Any] | None = None) -> str:
    if intent == "upload_help":
        return "블랙박스 영상은 사고 입력 화면에서 올릴 수 있습니다. 먼저 케이스를 만들고, 영상 업로드 단계에서 파일을 선택해 주세요. 지금은 로컬 업로드 방식으로 동작합니다."
    if intent == "report_explanation":
        return "결과 화면에서는 맨 위의 한 줄 결론을 먼저 보시면 됩니다. 과실비율은 참고 추정입니다. 최종 판단은 보험사, 분쟁심의, 법원 판단에 따라 달라질 수 있습니다."
    if intent == "insurance_help":
        return "보험 처리는 보통 사고 접수, 사고접수번호 기록, 블랙박스 보관, 차량 사진과 수리 견적서 준비 순서로 진행합니다. 통증이 있으면 병원 진료 기록도 챙겨두세요."
    if intent == "medical_help":
        return "통증이 있으면 늦추지 말고 병원 진료를 받아보세요. 저는 의료 진단은 할 수 없지만, 진료확인서나 진단서는 사고 처리에 도움이 될 수 있습니다."
    if intent == "legal_general_help":
        return "다친 사람이 있거나 음주, 무면허, 도주, 신호위반 같은 큰 위반이 의심되면 신고 여부를 확인해야 합니다. 형사책임은 경찰이나 법원의 판단이 필요합니다."
    if intent == "knia_fault_standard_help":
        return "과실비율 인정기준은 비슷한 사고 유형을 비교할 때 참고할 수 있는 자료입니다. 최종 과실비율은 보험사나 과실비율분쟁심의위원회 판단에 따라 달라질 수 있습니다."
    if intent == "smalltalk":
        return "안녕하세요. 사고 입력, 블랙박스 업로드, 결과 해석, 보험 처리 순서를 쉽게 도와드릴게요. 사고 상황을 편하게 적어 주세요."
    if intent == "unsupported":
        return "저는 교통사고 분석과 LawCompass 사용을 돕는 상담 도우미입니다. 사고 상황, 보험 접수, 블랙박스 업로드, 과실비율 기준에 대해 물어봐 주세요."
    return "LawCompass 사용과 교통사고 대응을 쉽게 도와드릴게요. 사고 상황을 짧게 적어 주시면 다음 단계를 안내해 드립니다."
