from __future__ import annotations

from typing import Any

from app.services.analyst_output_guard import guard_criminal_liability_output
from app.services.llm_client import generate_criminal_liability_analysis


def analyze_criminal_liability(
    *,
    scenario_type: str,
    facts: dict[str, Any],
    evidence: list[dict[str, Any]],
    legal_analysis: dict[str, Any],
    text: str,
) -> dict[str, Any]:
    llm = generate_criminal_liability_analysis(text=text, scenario_type=scenario_type, facts=facts, evidence=evidence, legal_analysis=legal_analysis)
    if llm:
        return guard_criminal_liability_output(llm, evidence)

    risk_flags = set(legal_analysis.get("risk_flags", []))
    if facts.get("injury"):
        risk_flags.add("injury_reporting_review")
    reporting_required = bool(facts.get("injury") or scenario_type in {"school_zone_child_accident", "hit_and_run_risk", "drunk_or_unlicensed_accident"})
    level = "high" if scenario_type in {"school_zone_child_accident", "hit_and_run_risk", "drunk_or_unlicensed_accident"} else ("medium" if reporting_required else "low")
    return guard_criminal_liability_output({
        "reporting_required": reporting_required,
        "criminal_risk_level": level,
        "risk_flags": sorted(risk_flags),
        "checklist": [
            "인명피해 및 진단 여부 확인",
            "음주/무면허/도주 여부 확인",
            "신호위반, 중앙선 침범, 횡단보도 보행자 보호의무 위반 등 12대 중과실 여부 확인",
            "어린이보호구역 및 피해자 어린이 여부 확인",
        ],
        "note": "형사책임은 수사기관과 법원의 판단 영역이며, 본 결과는 검토 필요성을 알려주는 참고 정보입니다.",
        "evidence_ids": [ev.get("chunk_id") for ev in evidence[:6] if ev.get("chunk_id")],
    }, evidence)
