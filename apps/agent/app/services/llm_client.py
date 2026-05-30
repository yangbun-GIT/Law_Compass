from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_TIMEOUT_SEC = float(os.getenv("OPENAI_TIMEOUT_SEC", "18"))


def _safe_json_loads(raw: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass
    match = re.search(r"\{[\s\S]*\}", raw or "")
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _generate_json(system_prompt: str, user_payload: dict[str, Any], max_tokens: int = 1400) -> dict[str, Any] | None:
    if os.getenv("ENABLE_OPENAI_ANALYSTS", "0") != "1":
        return None
    if not OPENAI_API_KEY:
        return None
    payload = {
        "model": OPENAI_MODEL,
        "temperature": 0.15,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt + " 반드시 JSON 객체만 출력한다. 법률 확정 판단 표현은 금지한다."},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
    }
    try:
        with httpx.Client(timeout=OPENAI_TIMEOUT_SEC) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json=payload,
            )
            if resp.status_code >= 400:
                return None
            data = resp.json()
    except Exception:
        return None
    content = (((data.get("choices") or [{}])[0].get("message") or {}).get("content"))
    if isinstance(content, list):
        content = "\n".join(str(x.get("text", "")) for x in content if isinstance(x, dict))
    return _safe_json_loads(content) if isinstance(content, str) else None


def generate_traffic_law_analysis(*, text: str, scenario_type: str, facts: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any] | None:
    return _generate_json(
        "너는 대한민국 교통사고 민형사 사건에 특화된 AI 교통사고 전문 변호사형 분석관이다. 도로교통법, 교통사고처리 특례법, 판례·법령 근거, 사고 후 조치 의무를 근거 기반으로 검토하고, 근거가 부족하면 추가 확인 필요 사항을 명시한다.",
        {"text": text, "scenario_type": scenario_type, "facts": facts, "evidence": evidence, "required_keys": ["applicable_rules", "legal_issue_summary", "risk_flags", "required_facts", "evidence_ids"]},
    )


def generate_fault_ratio_analysis(*, text: str, scenario_type: str, facts: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any] | None:
    return _generate_json(
        "너는 대한민국 교통사고 전문 변호사형 과실비율 분석관이다. 유사 판례, KNIA 과실비율 기준, 법령 근거, 영상/사용자 입력 사실을 대조해 예상 과실범위와 수정 요소를 제시한다. 단일 정답처럼 단정하지 말고, 유사 근거와 불확실성을 함께 설명한다.",
        {"text": text, "scenario_type": scenario_type, "facts": facts, "evidence": evidence, "required_keys": ["my", "other", "confidence", "basis", "key_factors", "evidence_ids"]},
    )


def generate_criminal_liability_analysis(*, text: str, scenario_type: str, facts: dict[str, Any], evidence: list[dict[str, Any]], legal_analysis: dict[str, Any]) -> dict[str, Any] | None:
    return _generate_json(
        "너는 교통사고 형사 리스크를 검토하는 AI 교통사고 전문 변호사형 분석관이다. 12대 중과실, 사망·상해, 신호위반, 중앙선 침범, 속도위반, 신고의무, 음주/무면허/도주 리스크를 실제 법령·판례 근거 기반의 가능성으로 표현하고, 형사 사건화 가능성이 높으면 대응 방향과 필요한 증거를 분리해 제시한다.",
        {"text": text, "scenario_type": scenario_type, "facts": facts, "evidence": evidence, "legal_analysis": legal_analysis, "required_keys": ["reporting_required", "criminal_risk_level", "checklist", "risk_flags", "evidence_ids"]},
    )


def generate_insurance_analysis(*, text: str, scenario_type: str, facts: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any] | None:
    return _generate_json(
        "너는 교통사고 보험 처리 실무 분석관이다. KNIA 과실 기준, 보험 실무, 대인/대물 접수, 분쟁심의 가능성, 필요 서류를 근거 기반으로 안내한다. 보상금액이나 책임을 확정하지 말고 예상 처리 흐름과 쟁점을 분리한다.",
        {"text": text, "scenario_type": scenario_type, "facts": facts, "evidence": evidence, "required_keys": ["summary", "claim_type", "steps", "required_documents", "settlement_example", "next_steps"]},
    )


def generate_action_plan(*, text: str, scenario_type: str, facts: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any] | None:
    return _generate_json(
        "너는 교통사고 민사·형사·보험 대응 코치다. 변호사 관점의 쟁점, 보험 처리 관점의 제출자료, 추가 확인이 필요한 영상/CCTV/신호/속도 자료를 단계별로 정리한다.",
        {"text": text, "scenario_type": scenario_type, "facts": facts, "evidence": evidence, "required_keys": ["action_plan"]},
    )


def generate_final_report(**payload: Any) -> dict[str, Any] | None:
    return _generate_json(
        (
            "너는 교통사고 분석 결과를 사용자가 이해하기 쉬운 짧은 JSON으로 정리한다. "
            "accident_title은 '사고 상황을 간단히 정리했어요' 같은 안내 문구가 아니라 "
            "사고 자체를 명사형 제목으로 쓴다. 예: '야간 중 음주운전 트럭의 교량 아래 스텔스 주차로 인한 사고'. "
            "accident_summary는 1~2문장으로 사고 경위와 핵심 확인 요소만 설명한다. "
            "법률 판단 확정, 과실비율 확정, 변호사 자문처럼 표현하지 않는다."
        ),
        {**payload, "required_keys": ["accident_title", "accident_summary"]},
        max_tokens=900,
    )


def generate_with_openai(
    accident_text: str,
    evidence: list[dict[str, Any]],
    *,
    ai_profile: str | None = None,
    specialist_roles: list[str] | None = None,
    video_metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    return generate_final_report(
        accident_text=accident_text,
        evidence=evidence,
        ai_profile=ai_profile,
        specialist_roles=specialist_roles or [],
        video_metadata=video_metadata or {},
    )


def generate_accident_input_filter(
    *,
    description_text: str,
    structured_facts: dict[str, Any] | None = None,
    selected_keywords: list[str] | None = None,
) -> dict[str, Any] | None:
    return _generate_json(
        (
            "너는 교통사고 입력 정규화 필터다. "
            "반드시 JSON 객체만 반환한다. "
            "트럭, 주차 차량, 정차 차량, 앞차, 상대 차량이 명시되면 자전거로 분류하지 않는다. "
            "사용자가 자전거와 직접 충돌했다고 말하지 않았으면 car_vs_bicycle을 선택하지 않는다. "
            "야간, 스텔스, 무등화, 교량 아래, 화단, 음주운전 후 정차가 있으면 "
            "car_vs_car + stealth_illegal_parked_vehicle_collision으로 본다. "
            "LLM은 과실비율 숫자를 산정하지 않는다."
        ),
        {
            "description_text": description_text,
            "structured_facts": structured_facts or {},
            "selected_keywords": selected_keywords or [],
            "required_keys": [
                "knia_major_party_type",
                "accident_type",
                "accident_subtype",
                "collision_partner_type",
                "direct_collision_target",
                "target_vehicle_status",
                "scenario_tags",
                "facts_patch",
                "exclude_party_types",
                "confidence",
                "reason",
            ],
        },
        max_tokens=900,
    )
