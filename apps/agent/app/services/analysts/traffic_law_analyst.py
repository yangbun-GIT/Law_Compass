from __future__ import annotations

from typing import Any

from app.services.analyst_output_guard import guard_traffic_law_output
from app.services.llm_client import generate_traffic_law_analysis


def analyze_traffic_law(
    *,
    scenario_type: str,
    facts: dict[str, Any],
    evidence: list[dict[str, Any]],
    text: str,
) -> dict[str, Any]:
    llm = generate_traffic_law_analysis(text=text, scenario_type=scenario_type, facts=facts, evidence=evidence)
    if llm:
        return guard_traffic_law_output(llm, evidence)
    evidence_ids = [ev.get("chunk_id") for ev in evidence[:6] if ev.get("chunk_id")]
    flags: list[str] = []
    applicable: list[str] = []
    if scenario_type == "school_zone_child_accident":
        flags.extend(["school_zone_criminal_review", "child_injury_review"])
        applicable.extend(["SCHOOL_ZONE_CHILD_PROTECTION", "CROSSWALK_PEDESTRIAN_PROTECTION"])
    if scenario_type == "intersection_signal_violation":
        flags.extend(["signal_violation_review", "twelve_gross_negligence_review"])
        applicable.append("SIGNAL_VIOLATION")
    if scenario_type == "rear_end_collision":
        applicable.append("REAR_END_SAFE_DISTANCE")
    if facts.get("injury"):
        flags.append("injury_reporting_review")
        applicable.append("ROAD_ACCIDENT_REPORTING_DUTY")
    return guard_traffic_law_output({
        "applicable_rules": list(dict.fromkeys(applicable)),
        "legal_issue_summary": "입력된 사고 사실과 검색된 교통법규 근거를 기준으로 적용 가능 법규를 검토했습니다.",
        "risk_flags": list(dict.fromkeys(flags)),
        "required_facts": ["인명피해 여부", "신호 상태", "사고 장소", "상대방 행위"],
        "evidence_ids": evidence_ids,
    }, evidence)
