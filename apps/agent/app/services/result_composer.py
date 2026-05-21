from typing import Any


def compose_action_plan(facts: dict[str, Any], risk_flags: list[str]) -> list[str]:
    base = [
        "현장 사진/영상, 블랙박스 원본, 보험 접수번호를 정리하세요.",
        "인명피해가 의심되면 즉시 119/112 신고 여부를 확인하세요.",
        "과실비율은 확정이 아니라 분쟁조정/소송에서 달라질 수 있습니다.",
    ]
    if "injury_possible" in risk_flags:
        base.append("진단서 발급 가능성이 있으면 사고 경위서를 최대한 빠르게 작성하세요.")
    return base


def build_disclaimers() -> list[str]:
    return [
        "본 결과는 법률/보험 자문이 아닌 AI 기반 참고 정보입니다.",
        "최종 과실비율, 보상금액, 형사책임은 수사기관/보험사/법원의 판단에 따릅니다.",
    ]

