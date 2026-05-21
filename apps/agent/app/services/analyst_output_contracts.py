from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


EvidenceSupportLevel = Literal["direct", "partial", "insufficient"]
JudgmentStatus = Literal["evidence_supported", "needs_review", "unsupported"]


class AnalystOutputBase(BaseModel):
    model_config = ConfigDict(extra="allow")

    evidence_count: int = Field(default=0, ge=0)
    evidence_ids: list[str] = Field(default_factory=list)
    used_evidence_ids: list[str] = Field(default_factory=list)
    required_evidence_family: str = "any"
    evidence_support_level: EvidenceSupportLevel = "insufficient"
    judgment_status: JudgmentStatus = "unsupported"
    caveats: list[str] = Field(default_factory=list)

    @field_validator("evidence_ids", "used_evidence_ids", "caveats", mode="before")
    @classmethod
    def _normalize_common_lists(cls, value: Any) -> list[str]:
        return _string_list(value)

    @field_validator("required_evidence_family", mode="before")
    @classmethod
    def _normalize_family(cls, value: Any) -> str:
        return _string_value(value) or "any"


class TrafficLawAnalysisOutput(AnalystOutputBase):
    applicable_rules: list[str] = Field(default_factory=list)
    legal_issue_summary: str = ""
    risk_flags: list[str] = Field(default_factory=list)
    required_facts: list[str] = Field(default_factory=list)

    @field_validator("applicable_rules", "risk_flags", "required_facts", mode="before")
    @classmethod
    def _normalize_lists(cls, value: Any) -> list[str]:
        return _string_list(value)

    @field_validator("legal_issue_summary", mode="before")
    @classmethod
    def _normalize_text(cls, value: Any) -> str:
        return _string_value(value)


class FaultRatioAnalysisOutput(AnalystOutputBase):
    my: int = Field(default=50, ge=0, le=100)
    other: int = Field(default=50, ge=0, le=100)
    confidence: float = Field(default=0.45, ge=0.0, le=1.0)
    basis: str = ""
    key_factors: list[str] = Field(default_factory=list)

    @field_validator("key_factors", mode="before")
    @classmethod
    def _normalize_lists(cls, value: Any) -> list[str]:
        return _string_list(value)

    @field_validator("basis", mode="before")
    @classmethod
    def _normalize_text(cls, value: Any) -> str:
        return _string_value(value)


class CriminalLiabilityAnalysisOutput(AnalystOutputBase):
    reporting_required: bool | None = None
    criminal_risk_level: str = "unknown"
    risk_flags: list[str] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)
    note: str = ""
    decision_status: str = "needs_review"

    @field_validator("risk_flags", "checklist", mode="before")
    @classmethod
    def _normalize_lists(cls, value: Any) -> list[str]:
        return _string_list(value)

    @field_validator("criminal_risk_level", "note", "decision_status", mode="before")
    @classmethod
    def _normalize_text(cls, value: Any) -> str:
        return _string_value(value)

    @field_validator("reporting_required", mode="before")
    @classmethod
    def _normalize_bool(cls, value: Any) -> bool | None:
        if value is None or isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in {"true", "yes", "y", "1", "예", "필요", "필요함"}:
            return True
        if text in {"false", "no", "n", "0", "아니오", "불필요", "필요 없음", "필요없음"}:
            return False
        return None


class InsuranceAnalysisOutput(AnalystOutputBase):
    summary: str = ""
    claim_type: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    settlement_example: str = ""
    next_steps: list[str] = Field(default_factory=list)

    @field_validator("claim_type", "steps", "required_documents", "next_steps", mode="before")
    @classmethod
    def _normalize_lists(cls, value: Any) -> list[str]:
        return _string_list(value)

    @field_validator("summary", "settlement_example", mode="before")
    @classmethod
    def _normalize_text(cls, value: Any) -> str:
        return _string_value(value)


def validate_traffic_law_output(data: dict[str, Any]) -> dict[str, Any]:
    return TrafficLawAnalysisOutput.model_validate(data).model_dump()


def validate_fault_ratio_output(data: dict[str, Any]) -> dict[str, Any]:
    return FaultRatioAnalysisOutput.model_validate(data).model_dump()


def validate_criminal_liability_output(data: dict[str, Any]) -> dict[str, Any]:
    return CriminalLiabilityAnalysisOutput.model_validate(data).model_dump()


def validate_insurance_output(data: dict[str, Any]) -> dict[str, Any]:
    return InsuranceAnalysisOutput.model_validate(data).model_dump()


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        items = [value.decode("utf-8", errors="ignore") if isinstance(value, bytes) else value]
    elif isinstance(value, list):
        items = value
    elif isinstance(value, (tuple, set)):
        items = list(value)
    else:
        items = [value]
    return [str(item).strip() for item in items if item is not None and str(item).strip()]


def _string_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, bytes)):
        return value.decode("utf-8", errors="ignore").strip() if isinstance(value, bytes) else value.strip()
    if isinstance(value, (list, tuple, set)):
        items = _string_list(value)
        return items[0] if items else ""
    return str(value).strip()
