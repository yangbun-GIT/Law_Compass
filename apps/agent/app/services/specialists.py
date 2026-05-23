from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpecialistRole:
    role_id: str
    title: str
    focus: str


ALL_SPECIALISTS: list[SpecialistRole] = [
    SpecialistRole("traffic-accident-attorney-analyst", "AI 교통사고 전문 변호사형 분석관", "판례·법령·KNIA 기준 기반 예상 판결과 민형사 쟁점"),
    SpecialistRole("insurance-claims-practice-analyst", "AI 보험 처리 실무 분석관", "보험 접수·대인/대물·분쟁심의 기준 기반 예상 처리"),
    SpecialistRole("impact-dynamics-analyst", "충돌역학 분석가", "충돌 방향/속도/접촉 패턴"),
    SpecialistRole("rear-end-fault-specialist", "후미추돌 과실 전문가", "후미추돌 기본 과실 분기"),
    SpecialistRole("braking-pattern-analyst", "제동패턴 분석가", "급제동/제동거리 가정"),
    SpecialistRole("distance-keeping-evaluator", "안전거리 평가자", "차간거리 확보 여부"),
    SpecialistRole("signal-compliance-analyst", "신호준수 분석가", "신호위반 가능성"),
    SpecialistRole("right-of-way-specialist", "통행우선권 전문가", "교차로 우선권 판단"),
    SpecialistRole("intersection-collision-analyst", "교차로 충돌 분석가", "교차로 진입 타이밍"),
    SpecialistRole("lane-change-rule-specialist", "차선변경 규정 전문가", "진로변경 위법성"),
    SpecialistRole("blind-spot-risk-analyst", "사각지대 위험 분석가", "시야 사각영역 충돌"),
    SpecialistRole("turn-signal-compliance-analyst", "방향지시등 준수 분석가", "신호등/지시등 사용"),
    SpecialistRole("speed-feasibility-analyst", "속도 타당성 분석가", "상황 대비 속도 적정성"),
    SpecialistRole("road-condition-analyst", "노면상태 분석가", "노면/기상/시야 영향"),
    SpecialistRole("pedestrian-protection-analyst", "보행자 보호 분석가", "보행자 보호 의무"),
    SpecialistRole("crosswalk-priority-specialist", "횡단보도 우선권 전문가", "횡단보도 규정"),
    SpecialistRole("injury-severity-flagger", "상해심각도 플래거", "대인사고 위험 신호"),
    SpecialistRole("criminal-risk-analyst", "형사책임 위험 분석가", "12대중과실/형사리스크"),
    SpecialistRole("reporting-duty-specialist", "신고의무 전문가", "경찰신고/조치의무 체크"),
    SpecialistRole("insurance-liability-planner", "보험책임 플래너", "대인/대물 처리 시나리오"),
    SpecialistRole("claim-document-checker", "보험서류 체크 전문가", "필수 서류/증빙 리스트"),
    SpecialistRole("medical-process-advisor", "대인치료 프로세스 가이드", "진단서/치료비 절차"),
    SpecialistRole("vehicle-repair-advisor", "수리견적 프로세스 가이드", "수리/휴차료 흐름"),
    SpecialistRole("legal-obligation-checker", "법적 의무 점검자", "현장조치/신고/보전의무"),
    SpecialistRole("evidence-relevance-auditor", "근거 적합성 감사자", "근거-주장 정합성"),
    SpecialistRole("precedent-linker", "판례 연결 분석가", "유사 판례/규정 연결"),
    SpecialistRole("uncertainty-calibrator", "불확실성 보정가", "근거 부족/가정 표시"),
]


def all_specialist_ids() -> list[str]:
    return [s.role_id for s in ALL_SPECIALISTS]


def pick_specialists(ai_profile: str, requested_roles: list[str] | None = None) -> list[str]:
    if requested_roles:
        valid = [r for r in requested_roles if r in all_specialist_ids()]
        if valid:
            return valid

    mapping = {
        "rear_end_focus": [
            "traffic-accident-attorney-analyst",
            "impact-dynamics-analyst",
            "rear-end-fault-specialist",
            "braking-pattern-analyst",
            "distance-keeping-evaluator",
            "insurance-claims-practice-analyst",
            "claim-document-checker",
            "legal-obligation-checker",
            "uncertainty-calibrator",
        ],
        "intersection_focus": [
            "traffic-accident-attorney-analyst",
            "signal-compliance-analyst",
            "right-of-way-specialist",
            "intersection-collision-analyst",
            "speed-feasibility-analyst",
            "criminal-risk-analyst",
            "insurance-claims-practice-analyst",
            "reporting-duty-specialist",
            "precedent-linker",
            "uncertainty-calibrator",
        ],
        "lane_change_focus": [
            "traffic-accident-attorney-analyst",
            "lane-change-rule-specialist",
            "blind-spot-risk-analyst",
            "turn-signal-compliance-analyst",
            "impact-dynamics-analyst",
            "insurance-claims-practice-analyst",
            "precedent-linker",
            "evidence-relevance-auditor",
            "uncertainty-calibrator",
        ],
        "pedestrian_focus": [
            "traffic-accident-attorney-analyst",
            "pedestrian-protection-analyst",
            "crosswalk-priority-specialist",
            "injury-severity-flagger",
            "criminal-risk-analyst",
            "insurance-claims-practice-analyst",
            "reporting-duty-specialist",
            "medical-process-advisor",
            "precedent-linker",
            "uncertainty-calibrator",
        ],
    }

    return mapping.get(
        ai_profile,
        [
            "traffic-accident-attorney-analyst",
            "impact-dynamics-analyst",
            "insurance-claims-practice-analyst",
            "criminal-risk-analyst",
            "evidence-relevance-auditor",
            "precedent-linker",
            "uncertainty-calibrator",
        ],
    )


def describe_roles(role_ids: list[str]) -> list[dict[str, str]]:
    table = {s.role_id: s for s in ALL_SPECIALISTS}
    out: list[dict[str, str]] = []
    for rid in role_ids:
        s = table.get(rid)
        if s:
            out.append({"role_id": s.role_id, "title": s.title, "focus": s.focus})
    return out
