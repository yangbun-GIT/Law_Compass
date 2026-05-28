const INTERNAL_MAP: Record<string, string> = {
  rear_end_collision: "후미추돌 사고",
  school_zone_child_accident: "어린이보호구역 사고",
  intersection_signal_violation: "교차로 신호위반 사고",
  lane_change_collision: "차선변경 사고",
  pedestrian_crosswalk_accident: "보행자 사고",
  bicycle_collision: "차대자전거 사고",
  object_collision: "차대기물 사고",
  single_vehicle_accident: "차량단독 사고",
  car_vs_car: "차대차 사고",
  car_vs_person: "차대사람 사고",
  car_vs_bicycle: "차대자전거 사고",
  car_vs_object: "차대기물 사고",
  single_vehicle: "차량단독 사고",
  REAR_END_SAFE_DISTANCE: "앞차와 안전거리를 지켜야 하는 의무",
  ROAD_ACCIDENT_REPORTING_DUTY: "사고가 났을 때 정차하고 필요한 조치를 해야 하는 의무",
  SAFE_DRIVING_DUTY: "주변 상황을 살피며 안전하게 운전해야 하는 의무",
  SIGNAL_VIOLATION: "신호를 지켜야 하는 의무",
  LANE_CHANGE_CAUTION: "차선을 바꿀 때 주변 차량을 살펴야 하는 의무",
  CROSSWALK_PEDESTRIAN_PROTECTION: "횡단보도에서 보행자를 보호해야 하는 의무",
  SCHOOL_ZONE_CHILD_PROTECTION: "어린이보호구역에서 더 주의해서 운전해야 하는 의무",
  TWELVE_GROSS_NEGLIGENCE: "중대한 교통법규 위반 여부 확인",
  HIT_AND_RUN_RISK: "사고 후 필요한 조치를 하지 않았는지 확인"
};
const TECHNICAL_KEYS = new Set(["model_info", "technical_model_info", "scenario_classifier", "retrieval", "cache_key", "evidence_cache_key", "chunk_id", "score", "rag_top_k", "ai_profile", "llm_enabled", "llm_usage", "llm_policy", "analysis_source", "provider_enabled", "allowed_outputs", "deterministic_authority", "orchestrator", "security_flags", "scenario_tags", "scenario_type", "document_id", "source_uri", "evidence_ids", "used_evidence_ids", "claim_evidence", "claim_id", "evidence_refs", "required_evidence_family", "support_level", "unsupported_claims", "evidence_support_level", "decision_status", "judgment_status", "agent_judgment", "stage_statuses", "blocking_reasons", "must_not_present_as_final", "user_reference_allowed", "agent_judgment_contract_version", "agent_judgment_overall_status", "decision_blockers", "decision_readiness", "knia_basis", "presentation_policy", "presentation_status", "restricted_sections", "finality", "input_requirements", "followup_loop", "required_input_questions", "blocking_fields", "optional_fields", "video_input_contract", "_video_input_contract", "accepted_observations", "uncertain_observations", "supporting_observations", "ignored_observations", "fact_patch", "confirmation_candidates", "confirmation_groups", "observation_quality", "observation_quality_summary", "quality_gate", "frame_refs", "fact_arbitration", "_fact_arbitration", "fact_sources", "_fact_sources", "video_primary_fields", "user_primary_fields", "applied_video_fields", "kept_user_fields", "confirmed_fields", "held_video_fields", "tentatively_supported_fields", "pending_video_confirmations", "confirmation_fields", "conflicts", "requires_confirmation", "agent_trace", "reflection_loop", "trace_policy", "packet", "step_count", "requery_attempted", "requery_added_evidence_count", "iterations_used", "initial_requery_reasons", "initial_query_terms", "final_missing_requirements", "next_action", "expert_guidance_sections", "source_blocked_reason", "retrieval_id", "trace_id", "raw_trace_id", "raw_prompt"]);
const BAD_PATTERNS = [/\?\?+/g, /\b[a-z]+(?:_[a-z0-9]+)+\b/g, /\b[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+\b/g, /score\s*[:=]?\s*\d+(\.\d+)?/gi, /chunk[_ ]?id\s*[:=]?\s*[\w-]+/gi, /model[_ ]?info/gi, /Local video verified.?/gi, /duration\s*=\s*[\d.]+s?/gi, /resolution\s*=\s*\d+x\d+/gi, /frames\s*=\s*\d+/gi, /fps\s*=\s*[\d.]+/gi, /codec\s*=\s*[a-z0-9_.-]+/gi, /,\s*=0/g];
export function shouldHideTechnicalKey(key: string) { return TECHNICAL_KEYS.has(key); }
export function mapInternalCodeToKorean(value: string): string { return INTERNAL_MAP[value] || value; }
export function hasBadDebugText(value: unknown): boolean {
  const text = typeof value === "string" ? value : JSON.stringify(value ?? "");
  return /\?\?+|chunk_id|score|model_info|cache_key|rag_top_k|ai_profile|llm_enabled|orchestrator|scenario_classifier|rear_end_collision|REAR_END_SAFE_DISTANCE|ROAD_ACCIDENT_REPORTING_DUTY|"injury"\s*:|"stopped"\s*:|"weather"\s*:/i.test(text);
}
export function sanitizeDisplayText(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "boolean") return value ? "예" : "아니오";
  let text = String(value).trim();
  if (!text || text === "null" || text === "undefined") return "";
  if ((text.startsWith("{") && text.endsWith("}")) || (text.startsWith("[") && text.endsWith("]"))) return "";
  text = mapInternalCodeToKorean(text);
  const mappedLevel = { medium: "보통", high: "높음", low: "낮음" }[text.toLowerCase()];
  if (mappedLevel) return mappedLevel;
  text = text.replace(/^unknown$|^모름$/gi, "확인이 필요합니다");
  for (const pattern of BAD_PATTERNS) text = text.replace(pattern, "");
  return text.replace(/\s+/g, " ").trim() || "확인이 필요합니다";
}
export function removeTechnicalFields<T>(obj: T): T {
  if (Array.isArray(obj)) return obj.map(removeTechnicalFields).filter((x) => x !== undefined) as T;
  if (obj && typeof obj === "object") {
    const out: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
      if (shouldHideTechnicalKey(key)) continue;
      const safe = removeTechnicalFields(value);
      if (safe !== undefined && safe !== "") out[key] = safe;
    }
    return out as T;
  }
  if (typeof obj === "string") return sanitizeDisplayText(obj) as T;
  if (obj === null || obj === undefined) return undefined as T;
  return obj;
}
