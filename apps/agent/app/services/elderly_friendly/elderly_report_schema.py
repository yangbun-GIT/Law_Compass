from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

class SummaryForUser(BaseModel):
    accident_type_label: str
    short_summary: str
    confidence_label: str
    warning: str = "정확한 과실비율은 보험사, 분쟁심의, 법원 판단에 따라 달라질 수 있습니다."

class TopAction(BaseModel):
    order: int
    title: str
    description: str
    importance: str

class FaultExplanation(BaseModel):
    title: str = "과실비율 참고 추정"
    my_label: str = "내 책임"
    other_label: str = "상대방 책임"
    my_percent: int = 50
    other_percent: int = 50
    easy_explanation: str
    why: list[str] = Field(default_factory=list)
    caution: str

class InsuranceExplanation(BaseModel):
    title: str = "보험 처리 안내"
    simple_summary: str
    steps: list[str] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)

class LegalExplanation(BaseModel):
    title: str = "법률상 확인할 점"
    simple_summary: str
    risk_label: str
    checklist: list[str] = Field(default_factory=list)
    caution: str = "형사책임 여부는 경찰이나 법원의 판단이 필요합니다."

class LegalBasisCard(BaseModel):
    law_name: str
    easy_title: str
    easy_explanation: str
    related_to_this_case: str
    confidence_label: str
    source_label: str

class KniaRelatedFaultStandard(BaseModel):
    title: str = "이 사고와 비슷한 과실비율 인정기준"
    chart_no: str | None = None
    chart_title: str | None = None
    base_fault_label: str
    easy_explanation: str
    why_similar: str
    source_url: str | None = None
    source_label: str
    disclaimer: str

class KniaRelatedVideo(BaseModel):
    title: str = "관련 영상 또는 원문 보기"
    display_mode: str = "external_link"
    source_url: str | None = None
    embed_url: str | None = None
    thumbnail_url: str | None = None
    button_label: str = "과실비율정보포털에서 보기"
    notice: str = "영상 파일은 LawCompass 서버에 저장하지 않고, 원본 사이트 링크로만 제공합니다."
    source_label: str

class KniaBasisCard(BaseModel):
    chart_no: str | None = None
    title: str
    easy_explanation: str
    why_similar: str
    source_url: str | None = None
    source_label: str

class MissingInfo(BaseModel):
    title: str = "더 정확한 분석을 위해 필요한 정보"
    items: list[str] = Field(default_factory=list)

class DetailSections(BaseModel):
    evidence_summaries: list[str] = Field(default_factory=list)
    notice: str = "상세 식별자와 모델 내부 정보는 일반 화면에 표시하지 않습니다."

class ElderlyFriendlyReport(BaseModel):
    headline: str
    summary_for_user: SummaryForUser
    top_actions: list[TopAction]
    fault_explanation: FaultExplanation
    insurance_explanation: InsuranceExplanation
    legal_explanation: LegalExplanation
    legal_basis_cards: list[LegalBasisCard]
    missing_info: MissingInfo
    detail_sections: DetailSections = Field(default_factory=DetailSections)
    related_fault_standard: KniaRelatedFaultStandard | None = None
    related_video: KniaRelatedVideo | None = None
    knia_basis_cards: list[KniaBasisCard] = Field(default_factory=list)
    disclaimers: list[str] = Field(default_factory=list)
