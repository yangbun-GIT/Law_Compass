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
  car_vs_motorcycle: "차대오토바이 사고",
  car_vs_object: "차대기물 사고",
  single_vehicle: "차량단독 사고",
  unknown: "추가 확인 필요",
  reference_only: "참고용 기준",
  fallback_used: "같은 대분류의 참고 기준",
  review_required: "추가 검토가 필요한 참고 기준",
  structured_chart_used: "구조화 KNIA 기준 사용",
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
const TECHNICAL_KEYS = new Set(["model_info", "technical_model_info", "scenario_classifier", "retrieval", "cache_key", "evidence_cache_key", "chunk_id", "score", "rag_top_k", "ai_profile", "llm_enabled", "llm_usage", "llm_policy", "analysis_source", "provider_enabled", "allowed_outputs", "deterministic_authority", "orchestrator", "security_flags", "scenario_tags", "scenario_type", "document_id", "source_uri", "source_type", "source_family", "evidence_ids", "used_evidence_ids", "claim_evidence", "claim_id", "evidence_refs", "required_evidence_family", "support_level", "unsupported_claims", "evidence_support_level", "decision_status", "judgment_status", "agent_judgment", "stage_statuses", "blocking_reasons", "must_not_present_as_final", "user_reference_allowed", "agent_judgment_contract_version", "agent_judgment_overall_status", "decision_blockers", "decision_readiness", "knia_basis", "presentation_policy", "presentation_status", "restricted_sections", "finality", "input_requirements", "followup_loop", "required_input_questions", "blocking_fields", "optional_fields", "video_input_contract", "_video_input_contract", "accepted_observations", "uncertain_observations", "supporting_observations", "ignored_observations", "fact_patch", "confirmation_candidates", "confirmation_groups", "observation_quality", "observation_quality_summary", "quality_gate", "frame_refs", "fact_arbitration", "_fact_arbitration", "fact_sources", "_fact_sources", "video_primary_fields", "user_primary_fields", "applied_video_fields", "kept_user_fields", "confirmed_fields", "held_video_fields", "tentatively_supported_fields", "pending_video_confirmations", "confirmation_fields", "conflicts", "requires_confirmation", "agent_trace", "reflection_loop", "trace_policy", "packet", "internal_packet", "metadata", "payload", "trace", "debug", "raw", "raw_payload", "raw_metadata", "raw_trace", "step_count", "requery_attempted", "requery_added_evidence_count", "iterations_used", "initial_requery_reasons", "initial_query_terms", "final_missing_requirements", "next_action", "expert_guidance_sections", "source_blocked_reason", "retrieval_id", "trace_id", "raw_trace_id", "raw_prompt", "structured_chart_used", "party_guard_policy", "rejected_mismatch_count", "fallback_used", "parsing_confidence", "review_required", "reference_only"]);
const BAD_PATTERNS = [
  /\?\?+/g,
  /\b[a-z]+(?:_[a-z0-9]+)+\b/g,
  /\b[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+\b/g,
  /score\s*[:=]?\s*\d+(\.\d+)?/gi,
  /chunk[_ ]?id\s*[:=]?\s*[\w-]+/gi,
  /model[_ ]?info/gi,
  /Local video verified.?/gi,
  /duration\s*=\s*[\d.]+s?/gi,
  /resolution\s*=\s*\d+x\d+/gi,
  /frames\s*=\s*\d+/gi,
  /fps\s*=\s*[\d.]+/gi,
  /codec\s*=\s*[a-z0-9_.-]+/gi,
  /(?:^|,\s*)=\s*\d+(?:\s*,\s*=\s*\d+)+(?:\.)?/g,
  /(?:^|[\s,])=\s*\d+(?=$|[\s,.;])/g,
  /,\s*=0/g,
];

const HIDDEN_USER_COPY_PATTERNS = [
  /영상 파일은 LawCompass 서버에 저장하지 않고.*?(?:제공합니다\.?|$)/g,
  /과실비율정보포털에서 제공하는 유사 사고 기준을 원문 링크로 확인할 수 있습니다\.?/g,
  /참고용 분석입니다\.?/g,
  /조건부 결과는 특정 테스트 영상에 맞춘 답이 아니라[\s\S]*?판단 구조입니다\.?/g,
  /이 내용은 유사 근거와 입력 사실을 바탕으로 한 참고용 예상입니다\.[\s\S]*?달라질 수 있습니다\.?/g,
  /실제 결과는 보험사, 분쟁심의, 수사기관, 법원의 판단에 따라 달라질 수 있습니다\.?/g,
  /더 확인하면 좋은 사실/g,
  /차량 파손 정도는 어느 정도인가요\??/g,
  /인명피해 여부/g,
  /신호 상태/g,
  /사고 장소/g,
  /상대방 행위/g,
];

const REPEATED_USER_PHRASES = [
  "정차 중 후미추돌 사고",
  "후미추돌 사고",
  "차대차 사고",
  "블랙박스 과실비율",
];

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function removeRawJsonFragments(value: string): string {
  return value
    .replace(/\{["']?[A-Za-z_가-힣][^{}]{0,180}(?=$|\s)/g, " ")
    .replace(/"\s*:\s*("[^"]*"|\d+|true|false|null)?/g, " ")
    .replace(/\[[\s,":A-Za-z_가-힣0-9-]{0,120}(?=$|\s)/g, " ")
    .trim();
}

export function collapseRepeatedPhrases(value: string): string {
  let output = value.replace(/\s+/g, " ").trim();
  for (const phrase of REPEATED_USER_PHRASES) {
    output = output.replace(new RegExp(`(?:${escapeRegExp(phrase)}\\s*){2,}`, "g"), `${phrase} `);
  }
  return output.replace(/\s{2,}/g, " ").trim();
}

export function cleanUserFacingCopy(value: unknown): string {
  let text = String(value ?? "");
  for (const pattern of HIDDEN_USER_COPY_PATTERNS) {
    text = text.replace(pattern, " ");
  }
  return collapseRepeatedPhrases(removeRawJsonFragments(text))
    .replace(/\s+([,.])/g, "$1")
    .replace(/^[\s,.;:·|-]+|[\s,.;:·|-]+$/g, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

export function shouldHideTechnicalKey(key: string) {
  const normalized = String(key || "").trim();
  if (TECHNICAL_KEYS.has(normalized)) return true;
  return /(^|_)(trace|debug|metadata|payload|packet|chunk_id|raw)(_|$)/i.test(normalized);
}
export function mapInternalCodeToKorean(value: string): string { return INTERNAL_MAP[value] || value; }
export function hasBadDebugText(value: unknown): boolean {
  const text = typeof value === "string" ? value : JSON.stringify(value ?? "");
  return /\?\?+|chunk_id|score|model_info|cache_key|rag_top_k|ai_profile|llm_enabled|orchestrator|scenario_classifier|rear_end_collision|REAR_END_SAFE_DISTANCE|ROAD_ACCIDENT_REPORTING_DUTY|"injury"\s*:|"stopped"\s*:|"weather"\s*:/i.test(text);
}
export function sanitizeDisplayText(value: unknown, fallback = ""): string {
  if (value === null || value === undefined) return fallback;
  if (typeof value === "boolean") return value ? "예" : "아니오";
  if (typeof value === "object") return fallback;
  let text = String(value).trim();
  if (!text || text === "null" || text === "undefined") return fallback;
  if (text === "[object Object]") return fallback;
  if ((text.startsWith("{") && text.endsWith("}")) || (text.startsWith("[") && text.endsWith("]"))) return fallback;
  text = mapInternalCodeToKorean(text);
  const compact = text.replace(/\s+/g, " ").trim();
  const brokenOnly =
    /^(\?\s*)+$/.test(compact) ||
    /^\d+\?$/.test(compact) ||
    /^(,\s*)?=\d+(,\s*=\d+)*\.?$/.test(compact) ||
    /^[\s,.;:·|-]*$/.test(compact);
  if (brokenOnly) return fallback;
  const mappedLevel = { medium: "보통", high: "높음", low: "낮음" }[text.toLowerCase()];
  if (mappedLevel) return mappedLevel;
  text = text.replace(/^(?:=\s*\d+\s*[,.)]\s*)+/g, "");
  text = text.replace(/^(?:\d+\s*[,.)]\s*){2,}/g, "");
  text = text.replace(/^unknown$|^모름$/gi, "확인이 필요합니다");
  text = text.replace(/^true$/gi, "예").replace(/^false$/gi, "아니오");
  text = text.replace(/\breference_only\b/gi, "참고용 기준");
  text = text.replace(/\bfallback_used\b/gi, "같은 대분류의 참고 기준");
  text = text.replace(/\breview_required\b/gi, "추가 검토가 필요한 참고 기준");
  text = text.replace(/\bstructured_chart_used\b/gi, "");
  text = text.replace(/직접 충돌 대상이 사람이면\s*KNIA\s*보\s*계열\s*기준만\s*사용해야\s*합니다\.?/gi, "");
  text = text.replace(/관련성이 있는 근거입니다\.?/g, "참고할 수 있는 근거");
  text = text.replace(/교통사고 법률 설명 자료/g, "법률 근거");
  text = text.replace(/검수 필요 구조화 KNIA 참고 기준입니다\.?/g, "현재 사고와 가장 가까운 KNIA 참고 기준입니다. 실제 적용 전 추가 확인이 필요합니다.");
  text = text.replace(/상세 기준 수집 필요/g, "상세 기준이 부족해 같은 대분류의 참고 기준을 함께 보여드립니다.");
  for (const pattern of BAD_PATTERNS) text = text.replace(pattern, "");
  text = cleanUserFacingCopy(text);
  text = text
    .replace(/(^|\s),\s*=\d+(,\s*=\d+)*\.?/g, " ")
    .replace(/\s{2,}/g, " ")
    .trim();
  return text || fallback || "확인이 필요합니다";
}

export function sanitizeUserVisibleText(value: unknown): string {
  return sanitizeDisplayText(value);
}

export function formatKniaBody(value: unknown): string[] {
  const text = sanitizeUserVisibleText(value)
    .replace(/\s*(⊙|①|②|③|④|⑤|※|관련 법규|참고 판례|조정사례|활용시 참고 사항|활용 참고사항)\s*/g, "\n$1 ")
    .replace(/다\.\s+(?=[가-힣A-Z0-9])/g, "다.\n")
    .replace(/요\.\s+(?=[가-힣A-Z0-9])/g, "요.\n");

  return text
    .split(/\n+/)
    .map((line) => line.replace(/^[-•]\s*/, "").trim())
    .filter((line) => line && !hasBadDebugText(line))
    .slice(0, 8);
}

export function splitLegalBasisParagraphs(value: unknown): string[] {
  return formatKniaBody(value).slice(0, 5);
}

export function toUserFriendlyEvidenceLabel(rawLabel: unknown): string {
  const label = sanitizeUserVisibleText(rawLabel);
  if (!label) return "참고용";
  if (label.includes("관련성")) return "근거용";
  if (label.includes("법률")) return "법률 근거";
  return label;
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
