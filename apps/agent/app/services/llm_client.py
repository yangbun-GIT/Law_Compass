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
        "너는 한국 교통법규 해석 전문가다. 도로교통법, 교통사고처리 특례법, 민식이법, 사고 후 조치 의무를 검토한다.",
        {"text": text, "scenario_type": scenario_type, "facts": facts, "evidence": evidence, "required_keys": ["applicable_rules", "legal_issue_summary", "risk_flags", "required_facts", "evidence_ids"]},
    )


def generate_fault_ratio_analysis(*, text: str, scenario_type: str, facts: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any] | None:
    return _generate_json(
        "너는 교통사고 과실비율 손해사정 전문가다. 기본 과실과 수정 요소를 참고용으로만 제시한다.",
        {"text": text, "scenario_type": scenario_type, "facts": facts, "evidence": evidence, "required_keys": ["my", "other", "confidence", "basis", "key_factors", "evidence_ids"]},
    )


def generate_criminal_liability_analysis(*, text: str, scenario_type: str, facts: dict[str, Any], evidence: list[dict[str, Any]], legal_analysis: dict[str, Any]) -> dict[str, Any] | None:
    return _generate_json(
        "너는 형사책임 검토 전문가다. 12대 중과실, 부상, 신고의무, 음주/무면허/도주 리스크를 가능성으로 표현한다.",
        {"text": text, "scenario_type": scenario_type, "facts": facts, "evidence": evidence, "legal_analysis": legal_analysis, "required_keys": ["reporting_required", "criminal_risk_level", "checklist", "risk_flags", "evidence_ids"]},
    )


def generate_insurance_analysis(*, text: str, scenario_type: str, facts: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any] | None:
    return _generate_json(
        "너는 보험 보상 담당자다. 대인/대물 접수, 필요 서류, 예시 범위만 안내한다.",
        {"text": text, "scenario_type": scenario_type, "facts": facts, "evidence": evidence, "required_keys": ["summary", "claim_type", "steps", "required_documents", "settlement_example", "next_steps"]},
    )


def generate_action_plan(*, text: str, scenario_type: str, facts: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any] | None:
    return _generate_json(
        "너는 교통사고 후속 대응 코치다. 사용자가 지금 해야 할 일을 단계별로 정리한다.",
        {"text": text, "scenario_type": scenario_type, "facts": facts, "evidence": evidence, "required_keys": ["action_plan"]},
    )


def generate_final_report(**payload: Any) -> dict[str, Any] | None:
    return _generate_json(
        "너는 여러 분석가의 결과를 종합해 사용자가 이해하기 쉬운 한국어 사고 리포트를 작성한다.",
        {**payload, "required_keys": ["accident_summary"]},
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
