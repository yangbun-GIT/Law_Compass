from dataclasses import dataclass

@dataclass
class TaskPlan:
    goal: str
    tasks: list[str]


def build_task_plan() -> TaskPlan:
    return TaskPlan(
        goal="교통사고 사실 기반으로 한국어 분석 리포트를 생성한다.",
        tasks=[
            "입력 정규화 및 민감정보 마스킹",
            "사고 유형 분류",
            "RAG 근거 검색",
            "과실비율/보험/형사책임 추론",
            "행동 지침 및 면책 문구 생성",
        ],
    )

