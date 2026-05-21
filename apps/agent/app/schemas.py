from pydantic import BaseModel, Field
from typing import Any


class AnalyzeTextRequest(BaseModel):
    case_id: str
    user_id: str
    description_text: str = Field(min_length=1, max_length=10000)
    structured_facts: dict[str, Any] | None = None
    selected_keywords: list[str] | None = None
    analysis_mode: str | None = None
    ai_profile: str | None = None
    specialist_roles: list[str] | None = None


class AnalyzeVideoRequest(BaseModel):
    case_id: str
    user_id: str
    upload_id: str
    preprocessed_summary: str | None = None
    ai_profile: str | None = None
    specialist_roles: list[str] | None = None
    video_metadata: dict[str, Any] | None = None
    structured_facts: dict[str, Any] | None = None
    selected_keywords: list[str] | None = None
    analysis_mode: str | None = None


class EvidenceItem(BaseModel):
    chunk_id: str | None = None
    title: str
    source: str
    score: float | None = None
    snippet: str | None = None
    law_name: str | None = None
    article_title: str | None = None
    plain_summary: str | None = None
    related_reason: str | None = None
    source_url: str | None = None
    confidence_label: str | None = None
    display_priority: int | None = None
    source_type: str | None = None
    used_for: str | None = None


class AnalysisOutput(BaseModel):
    accident_summary: str
    scenario_type: str
    accident_party_type: str | None = None
    accident_party_label: str | None = None
    party_type_action_guide: dict[str, Any] = Field(default_factory=dict)
    structured_facts: dict[str, Any]
    legal_analysis: dict[str, Any]
    fault_ratio: dict[str, Any]
    insurance_guide: dict[str, Any]
    legal_liability: dict[str, Any]
    action_plan: list[str]
    evidence: list[EvidenceItem]
    legal_evidence: list[EvidenceItem] = Field(default_factory=list)
    knia_evidence: list[EvidenceItem] = Field(default_factory=list)
    combined_evidence: list[EvidenceItem] = Field(default_factory=list)
    knia_matches: list[dict[str, Any]] = Field(default_factory=list)
    knia_primary_match: dict[str, Any] | None = None
    evidence_audit: dict[str, Any]
    claim_evidence: dict[str, Any] = Field(default_factory=dict)
    agent_judgment: dict[str, Any] = Field(default_factory=dict)
    uncertainty: dict[str, Any]
    disclaimers: list[str]
    followup_questions: list[str]
    recommended_keywords: list[str] = []
    recommended_specialists: list[str] = []
    suggested_next_inputs: list[str] = []
    model_info: dict[str, Any]
    elderly_friendly_report: dict[str, Any] = Field(default_factory=dict)
