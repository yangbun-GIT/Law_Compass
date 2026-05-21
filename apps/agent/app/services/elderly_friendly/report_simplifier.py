from __future__ import annotations
from typing import Any
from app.services.elderly_friendly.elderly_report_schema import ElderlyFriendlyReport
from app.services.elderly_friendly.legal_explainer_agent import LegalExplainerAgent
from app.services.elderly_friendly.plain_language_agent import PlainLanguageAgent
from app.services.elderly_friendly.ui_text_mapper import scrub_user_text
from app.services.knia.knia_report_adapter import adapt_knia_for_report

_FORBIDDEN_EVIDENCE_KEYS = {"chunk_id", "score", "document_id", "scenario_tags", "keywords", "cache_key", "source_uri"}

def _safe_evidence_summaries(evidence: list[dict[str, Any]]) -> list[str]:
    summaries: list[str] = []
    for item in evidence[:5]:
        title = scrub_user_text(item.get("article_title") or item.get("chunk_summary") or item.get("title"), "교통사고 관련 근거")
        reason = scrub_user_text(item.get("related_reason") or item.get("used_for") or item.get("plain_summary"), "이 사고 판단에 참고할 수 있는 근거입니다.")
        text = f"{title}: {reason}"
        if text not in summaries:
            summaries.append(text)
    return summaries

def build_elderly_friendly_report(technical_result: dict[str, Any]) -> dict[str, Any]:
    plain = PlainLanguageAgent()
    explainer = LegalExplainerAgent()
    evidence = technical_result.get("evidence") or []
    report = ElderlyFriendlyReport(
        headline=plain.make_headline(technical_result),
        summary_for_user=plain.make_summary(technical_result),
        top_actions=plain.make_top_actions(technical_result),
        fault_explanation=plain.make_fault_explanation(technical_result),
        insurance_explanation=plain.make_insurance_explanation(technical_result),
        legal_explanation=plain.make_legal_explanation(technical_result),
        legal_basis_cards=explainer.explain(evidence, technical_result),
        missing_info=plain.make_missing_info(technical_result),
        detail_sections={"evidence_summaries": _safe_evidence_summaries(evidence)},
    )
    safe_report = report.model_dump(exclude_none=True)
    party_guide = technical_result.get("party_type_action_guide") or {}
    if party_guide:
        safe_report["accident_party_type_card"] = {
            "title": "사고 유형",
            "label": party_guide.get("label") or technical_result.get("accident_party_label") or "사고유형 확인 필요",
            "summary": party_guide.get("summary") or "사고 유형을 기준으로 필요한 조치를 정리했습니다.",
            "top_actions": party_guide.get("top_actions") or [],
            "cautions": party_guide.get("cautions") or [],
        }
    return adapt_knia_for_report(
        safe_report,
        technical_result.get("knia_primary_match"),
        technical_result.get("knia_matches") or [],
    )
