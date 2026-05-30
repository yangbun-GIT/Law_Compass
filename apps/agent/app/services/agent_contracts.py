from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


TaskStatus = Literal["pending", "running", "succeeded", "needs_review", "blocked", "failed"]
FinalityStatus = Literal["decision_ready", "needs_review", "reference_only", "blocked"]
Visibility = Literal["public", "internal", "restricted"]
ToolScope = Literal["knia.read", "legal.read", "evidence.audit", "cache.write", "storage.read", "video.observe"]
PlanInputMode = Literal["text_only", "video_only", "text_and_video", "followup_reanalysis", "admin_diagnostic"]
PlanStatus = Literal["ready", "safe_fallback", "blocked"]

SPECIALIST_ROLE_IDS = {
    "traffic_accident_attorney",
    "knia_standard_agent",
    "fault_ratio_agent",
    "criminal_liability_agent",
    "insurance_handling_agent",
    "evidence_audit_agent",
    "video_observation_agent",
}


class AgentInputRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref_type: Literal[
        "case",
        "upload",
        "structured_fact",
        "video_observation",
        "evidence",
        "tool_result",
        "agent_result",
        "safe_summary",
        "questionnaire_answer",
    ]
    ref_id: str | None = None
    field_path: str | None = None
    visibility: Visibility = "internal"
    summary: str | None = None

    @model_validator(mode="after")
    def _block_public_sensitive_refs(self) -> "AgentInputRef":
        if self.visibility == "public" and _has_sensitive_marker(
            {
                "ref_type": self.ref_type,
                "ref_id": self.ref_id,
                "field_path": self.field_path,
                "summary": self.summary,
            }
        ):
            raise ValueError("public AgentInputRef cannot expose raw text, prompts, secrets, or tokens")
        return self


class EvidenceRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_type: Literal["law", "knia", "precedent", "video", "user_fact", "insurance", "police", "medical", "any"]
    directness: Literal["direct", "partial", "context", "missing"] = "partial"
    required: bool = True
    reason: str = ""


class AgentClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_type: str
    text: str
    evidence_refs: list[AgentInputRef] = Field(default_factory=list)
    support_level: Literal["direct", "partial", "unsupported"] = "unsupported"

    @field_validator("claim_type", "text", mode="before")
    @classmethod
    def _normalize_text(cls, value: Any) -> str:
        return _string_value(value)


class AgentGoalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str
    status: TaskStatus
    claims: list[AgentClaim] = Field(default_factory=list)
    evidence_refs: list[AgentInputRef] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    uncertainties: list[str] = Field(default_factory=list)
    next_required_inputs: list[str] = Field(default_factory=list)
    finality: FinalityStatus = "needs_review"

    @model_validator(mode="after")
    def _guard_decision_ready_result(self) -> "AgentGoalResult":
        if self.finality == "decision_ready" and self.status not in {"succeeded", "needs_review"}:
            raise ValueError("decision_ready goal result requires succeeded or needs_review status")
        if self.finality == "decision_ready" and not self.evidence_refs and not any(claim.evidence_refs for claim in self.claims):
            raise ValueError("decision_ready goal result requires evidence references")
        return self


class AgentTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    task_type: Literal[
        "input_normalization",
        "video_observation",
        "fact_arbitration",
        "scenario_classification",
        "evidence_retrieval",
        "knia_matching",
        "fault_ratio",
        "criminal_liability",
        "insurance_guidance",
        "action_guidance",
        "presentation_policy",
        "tool_call",
        "specialist_agent",
    ]
    goal: str
    input_refs: list[AgentInputRef] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    required_evidence: list[EvidenceRequirement] = Field(default_factory=list)
    status: TaskStatus = "pending"
    blocking_reasons: list[str] = Field(default_factory=list)
    result_ref: str | None = None

    @model_validator(mode="after")
    def _guard_blocked_task(self) -> "AgentTask":
        if self.status in {"blocked", "failed"} and not self.blocking_reasons:
            raise ValueError("blocked or failed task requires blocking_reasons")
        return self


class AgentPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = "agent-plan-v1"
    plan_id: str
    case_id: str
    trace_id: str
    input_mode: PlanInputMode = "text_only"
    plan_status: PlanStatus = "ready"
    tasks: list[AgentTask]
    execution_order: list[str]
    replan_policy: Literal["none", "bounded_on_blocker", "manual_only"] = "none"
    created_by: Literal["static_stage_adapter", "planner", "admin_diagnostic"] = "static_stage_adapter"
    failure_observations: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _guard_execution_order(self) -> "AgentPlan":
        task_ids = {task.task_id for task in self.tasks}
        missing = [task_id for task_id in self.execution_order if task_id not in task_ids]
        if missing:
            raise ValueError(f"execution_order contains unknown task ids: {', '.join(missing)}")
        return self


class SpecialistRoleProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_id: str
    role_name: str
    professional_identity: str
    primary_responsibility: str
    decision_authority: list[str] = Field(default_factory=list)
    must_not_decide: list[str] = Field(default_factory=list)
    required_evidence_types: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    handoff_targets: list[str] = Field(default_factory=list)
    output_tone: str = "근거 기반의 보수적인 한국어 안내"
    safety_constraints: list[str] = Field(default_factory=list)

    @field_validator("role_id")
    @classmethod
    def _validate_role_id(cls, value: str) -> str:
        if value not in SPECIALIST_ROLE_IDS:
            raise ValueError(f"unknown specialist role_id: {value}")
        return value


class SpecialistAgentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_id: str
    goal: str
    input_facts_used: list[AgentInputRef] = Field(default_factory=list)
    evidence_used: list[AgentInputRef] = Field(default_factory=list)
    claims: list[AgentClaim] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    recommended_next_action: list[str] = Field(default_factory=list)
    finality: FinalityStatus = "needs_review"
    summary: str = ""

    @field_validator("role_id")
    @classmethod
    def _validate_role_id(cls, value: str) -> str:
        if value not in SPECIALIST_ROLE_IDS:
            raise ValueError(f"unknown specialist role_id: {value}")
        return value

    @model_validator(mode="after")
    def _guard_structured_result(self) -> "SpecialistAgentResult":
        if not self.claims and not self.unsupported_claims and not self.uncertainties:
            raise ValueError("specialist result requires claims, unsupported_claims, or uncertainties")
        if self.finality == "decision_ready" and (self.unsupported_claims or self.uncertainties):
            raise ValueError("decision_ready specialist result cannot contain unsupported claims or uncertainties")
        if self.finality == "decision_ready" and not self.evidence_used and not any(claim.evidence_refs for claim in self.claims):
            raise ValueError("decision_ready specialist result requires evidence_used")
        return self


class MCPToolErrorPacket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str
    status: Literal["failed"] = "failed"
    error_code: str
    message: str
    retryable: bool = False
    observation_status: Literal["failed", "blocked", "needs_review"] = "failed"
    trace_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MCPToolSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    required_scopes: list[ToolScope] = Field(default_factory=list)
    timeout_ms: int = Field(default=5000, gt=0)
    failure_packet_schema: str = "MCPToolErrorPacket"
    trace_destination: Literal["mcp_tool_calls", "agent_trace", "both"] = "both"
    standard_mcp_ready: bool = False


P1_INTERNAL_TOOL_SPECS: dict[str, MCPToolSpec] = {
    "legal_rag_search_tool": MCPToolSpec(
        name="legal_rag_search_tool",
        description="법령/RAG 근거 후보를 검색한다.",
        input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        output_schema={"type": "object", "properties": {"items": {"type": "array"}}},
        required_scopes=["legal.read"],
    ),
    "import_knia_json_tool": MCPToolSpec(
        name="import_knia_json_tool",
        description="KNIA JSON 기준 데이터를 가져온다.",
        input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"status": {"type": "string"}}},
        required_scopes=["knia.read", "cache.write"],
    ),
    "get_knia_myaccident_pages_tool": MCPToolSpec(
        name="get_knia_myaccident_pages_tool",
        description="KNIA 사고 기준 페이지 목록을 조회한다.",
        input_schema={"type": "object", "properties": {"limit": {"type": "integer"}}},
        output_schema={"type": "object", "properties": {"items": {"type": "array"}}},
        required_scopes=["knia.read"],
    ),
    "get_knia_menu_tree_tool": MCPToolSpec(
        name="get_knia_menu_tree_tool",
        description="KNIA 기준 메뉴 트리를 조회한다.",
        input_schema={"type": "object", "properties": {"party_type": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"tree": {"type": "array"}}},
        required_scopes=["knia.read"],
    ),
    "search_knia_json_rag_tool": MCPToolSpec(
        name="search_knia_json_rag_tool",
        description="KNIA JSON/RAG 기준 후보를 검색한다.",
        input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        output_schema={"type": "object", "properties": {"items": {"type": "array"}}},
        required_scopes=["knia.read"],
    ),
    "get_knia_media_by_query_tool": MCPToolSpec(
        name="get_knia_media_by_query_tool",
        description="KNIA 원문/영상 링크 후보를 검색한다.",
        input_schema={"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["query"]},
        output_schema={"type": "object", "properties": {"items": {"type": "array"}}},
        required_scopes=["knia.read"],
    ),
    "evidence_guard_tool": MCPToolSpec(
        name="evidence_guard_tool",
        description="주장과 근거의 직접성 및 부족 상태를 점검한다.",
        input_schema={"type": "object", "properties": {"claims": {"type": "array"}, "evidence": {"type": "array"}}},
        output_schema={"type": "object", "properties": {"status": {"type": "string"}, "blocking_reasons": {"type": "array"}}},
        required_scopes=["evidence.audit"],
    ),
    "invalidate_cache_tool": MCPToolSpec(
        name="invalidate_cache_tool",
        description="허용된 cache key를 무효화한다.",
        input_schema={"type": "object", "properties": {"key": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"status": {"type": "string"}}},
        required_scopes=["cache.write"],
    ),
}


def validate_specialist_result_against_profile(result: SpecialistAgentResult, profile: SpecialistRoleProfile) -> SpecialistAgentResult:
    if result.role_id != profile.role_id:
        raise ValueError("specialist result role_id does not match role profile")
    if result.finality == "decision_ready" and not profile.decision_authority:
        raise ValueError("decision_ready specialist result requires role decision_authority")
    return result


def list_internal_tool_specs() -> list[MCPToolSpec]:
    return [P1_INTERNAL_TOOL_SPECS[name] for name in sorted(P1_INTERNAL_TOOL_SPECS)]


def build_tool_error_packet(tool_name: str, message: str, *, error_code: str = "tool_failed", retryable: bool = False, trace_id: str | None = None) -> dict[str, Any]:
    return MCPToolErrorPacket(
        tool_name=tool_name,
        error_code=error_code,
        message=message,
        retryable=retryable,
        trace_id=trace_id,
    ).model_dump()


def _has_sensitive_marker(value: Any) -> bool:
    markers = ("raw_user_text", "prompt", "secret", "password", "api_key", "token", "refresh_token", ".env")
    if isinstance(value, dict):
        for key, item in value.items():
            if any(marker in str(key).lower() for marker in markers) or _has_sensitive_marker(item):
                return True
        return False
    if isinstance(value, (list, tuple, set)):
        return any(_has_sensitive_marker(item) for item in value)
    if value is None:
        return False
    return any(marker in str(value).lower() for marker in markers)


def _string_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, bytes)):
        return value.decode("utf-8", errors="ignore").strip() if isinstance(value, bytes) else value.strip()
    return str(value).strip()
