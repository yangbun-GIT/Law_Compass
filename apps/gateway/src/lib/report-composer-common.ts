export type AnyRecord = Record<string, any>;

export const TECHNICAL_KEYS = new Set([
  "model_info", "technical_model_info", "scenario_classifier", "retrieval", "cache_key", "evidence_cache_key",
  "chunk_id", "score", "rag_top_k", "ai_profile", "llm_enabled", "llm_usage", "llm_policy", "analysis_source", "provider_enabled", "allowed_outputs", "deterministic_authority", "orchestrator", "security_flags",
  "scenario_tags", "scenario_type", "document_id", "source_uri", "evidence_ids", "used_evidence_ids", "persona_outputs",
  "claim_evidence", "claim_id", "evidence_refs", "required_evidence_family", "support_level", "unsupported_claims",
  "evidence_support_level", "decision_status", "judgment_status", "agent_judgment", "stage_statuses", "blocking_reasons",
  "must_not_present_as_final", "user_reference_allowed", "agent_judgment_contract_version", "agent_judgment_overall_status",
  "decision_blockers", "decision_readiness", "knia_basis",
  "presentation_policy", "presentation_status", "restricted_sections", "finality",
  "input_requirements", "followup_loop", "required_input_questions", "blocking_fields", "optional_fields",
  "video_input_contract", "_video_input_contract", "accepted_observations", "uncertain_observations", "supporting_observations", "ignored_observations", "fact_patch",
  "confirmation_candidates", "confirmation_groups", "observation_quality", "observation_quality_summary", "quality_gate", "frame_refs",
  "fact_arbitration", "_fact_arbitration", "fact_sources", "_fact_sources", "video_primary_fields", "user_primary_fields",
  "applied_video_fields", "kept_user_fields", "confirmed_fields", "conflicts", "requires_confirmation",
  "agent_trace", "reflection_loop", "trace_policy", "packet", "step_count", "requery_attempted",
  "requery_added_evidence_count", "iterations_used", "initial_requery_reasons", "initial_query_terms", "final_missing_requirements", "next_action",
  "expert_guidance_sections", "source_blocked_reason", "retrieval_id", "trace_id", "raw_trace_id", "raw_prompt"
]);

export const BAD_VALUE_PATTERNS = [/\b[a-z]+(?:_[a-z0-9]+)+\b/g, /\b[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+\b/g, /\?\?+/g, /score\s*[:=]?\s*\d+(\.\d+)?/gi, /chunk[_ ]?id\s*[:=]?\s*[\w-]+/gi, /model[_ ]?info/gi, /Local video verified.?/gi, /duration\s*=\s*[\d.]+s?/gi, /resolution\s*=\s*\d+x\d+/gi, /frames\s*=\s*\d+/gi, /fps\s*=\s*[\d.]+/gi, /codec\s*=\s*[a-z0-9_.-]+/gi, /,\s*=0/g];

export const SAFE_INPUT_FIELDS = new Set(["accident_party_type", "accident_type", "signal_state", "injury", "opponent_behavior", "damage_level", "stopped", "sudden_brake", "school_zone", "victim_is_child", "crosswalk_nearby", "pedestrian_visible", "lane_change_actor", "turn_signal", "user_signal", "opponent_signal", "opponent_signal_visible", "signal_transition", "pedestrian_signal", "bicycle_location", "bicycle_direction", "centerline_crossed", "centerline_cross_reason", "road_obstruction", "illegal_parking_obstruction", "opposing_vehicle_present", "opposing_vehicle_did_not_stop", "secondary_collision", "non_contact_trigger", "trigger_actor_type", "trigger_actor_behavior", "direct_collision_partner_type", "rear_vehicle_collision", "collision_partner_type", "primary_collision_target", "collision_point_visible", "collision_point_location", "front_vehicle_stopped", "ego_turn_direction", "intersection", "stopped_vehicle_without_lights", "highway_or_expressway"]);

export function asArray(value: any): any[] {
  return Array.isArray(value) ? value : [];
}

export function unique(values: any[]) {
  return Array.from(new Set(values.map((value) => String(value || "").trim()).filter(Boolean)));
}

export function compactDisplayItems(values: any[], questionTexts: any[] = [], limit = 8) {
  const questionSet = new Set(questionTexts.map((value) => cleanText(value, "").replace(/\s+/g, " ").trim()).filter(Boolean));
  const output: string[] = [];
  const seen = new Set<string>();
  for (const value of values) {
    const text = cleanText(value, "").replace(/\s+/g, " ").trim();
    if (!text || seen.has(text) || questionSet.has(text)) continue;
    seen.add(text);
    output.push(text);
    if (output.length >= limit) break;
  }
  return output;
}

export function cleanText(value: any, fallback = "확인이 필요합니다.") {
  if (value === null || value === undefined) return fallback;
  if (typeof value === "boolean") return value ? "예" : "아니오";
  const raw = String(value).trim();
  if (!raw || raw === "unknown" || raw === "모름" || raw === "null") return fallback;
  if ((raw.startsWith("{") && raw.endsWith("}")) || (raw.startsWith("[") && raw.endsWith("]"))) return fallback;
  const mapped = { medium: "보통", high: "높음", low: "낮음" }[raw.toLowerCase()];
  if (mapped) return mapped;
  let text = raw;
  for (const pattern of BAD_VALUE_PATTERNS) text = text.replace(pattern, "");
  text = text
    .replace(/^\s*[,.]\s*/g, "")
    .replace(/\s*,\s*,\s*/g, ", ")
    .replace(/\s+\./g, ".")
    .replace(/\s+/g, " ")
    .trim();
  return text || fallback;
}

export function safeHttpUrl(value: any) {
  const text = String(value ?? "").trim();
  if (!/^https?:\/\//i.test(text)) return "";
  return text;
}

export function safeKniaUrl(value: any) {
  const text = String(value ?? "").trim();
  if (!text || /\s/.test(text) || !/^https?:\/\//i.test(text)) return "";
  try {
    const url = new URL(text);
    const host = url.hostname.toLowerCase();
    if (host !== "accident.knia.or.kr") return "";
    if (url.username || url.password) return "";
    return url.toString();
  } catch {
    return "";
  }
}

export function safeKniaThumbnailUrl(value: any) {
  const url = safeKniaUrl(value);
  if (!url) return "";
  const lowered = url.toLowerCase();
  if (lowered.includes("logo_test.jpg") || lowered.includes("/images/common/logo_test")) return "";
  return url;
}

export function scenarioLabel(value: string) {
  const map: AnyRecord = { rear_end_collision: "후미추돌 사고", school_zone_child_accident: "어린이보호구역 사고", intersection_signal_violation: "교차로 신호위반 사고", lane_change_collision: "차선변경 사고", pedestrian_crosswalk_accident: "보행자 사고", parking_or_stopped_vehicle_accident: "중앙선·정차 차량 관련 차대차 사고", general_collision: "교통사고", general_vehicle_collision: "교통사고" };
  return map[value] ?? "교통사고";
}

export function toNumber(value: any, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

export function isPlainObject(value: unknown): value is AnyRecord {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

export function hasAny(text: string, terms: string[]) {
  return terms.some((term) => text.includes(term.toLowerCase()));
}
