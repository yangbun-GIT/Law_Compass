type AnyRecord = Record<string, any>;

const TECHNICAL_KEYS = new Set([
  "model_info", "technical_model_info", "scenario_classifier", "retrieval", "cache_key", "evidence_cache_key",
  "chunk_id", "score", "rag_top_k", "ai_profile", "llm_enabled", "orchestrator", "security_flags",
  "scenario_tags", "scenario_type", "document_id", "source_uri", "evidence_ids", "used_evidence_ids", "persona_outputs",
  "claim_evidence", "claim_id", "evidence_refs", "required_evidence_family", "support_level", "unsupported_claims",
  "evidence_support_level", "decision_status", "judgment_status", "agent_judgment", "stage_statuses", "blocking_reasons",
  "must_not_present_as_final", "user_reference_allowed", "agent_judgment_contract_version", "agent_judgment_overall_status"
]);
const BAD_VALUE_PATTERNS = [/\b[a-z]+(?:_[a-z0-9]+)+\b/g, /\b[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+\b/g, /\?\?+/g, /score\s*[:=]?\s*\d+(\.\d+)?/gi, /chunk[_ ]?id\s*[:=]?\s*[\w-]+/gi, /model[_ ]?info/gi];
function asArray(value: any): any[] { return Array.isArray(value) ? value : []; }
function cleanText(value: any, fallback = "확인이 필요합니다.") {
  if (value === null || value === undefined) return fallback;
  if (typeof value === "boolean") return value ? "예" : "아니오";
  const raw = String(value).trim();
  if (!raw || raw === "unknown" || raw === "모름" || raw === "null") return fallback;
  if ((raw.startsWith("{") && raw.endsWith("}")) || (raw.startsWith("[") && raw.endsWith("]"))) return fallback;
  const mapped = { medium: "보통", high: "높음", low: "낮음" }[raw.toLowerCase()];
  if (mapped) return mapped;
  let text = raw;
  for (const pattern of BAD_VALUE_PATTERNS) text = text.replace(pattern, "");
  text = text.replace(/\s+/g, " ").trim();
  return text || fallback;
}
function scenarioLabel(value: string) {
  const map: AnyRecord = { rear_end_collision: "후미추돌 사고", school_zone_child_accident: "어린이보호구역 사고", intersection_signal_violation: "교차로 신호위반 사고", lane_change_collision: "차선변경 사고", pedestrian_crosswalk_accident: "보행자 사고", general_collision: "교통사고", general_vehicle_collision: "교통사고" };
  return map[value] ?? "교통사고";
}
function detectMissingFields(facts: AnyRecord = {}) {
  const missing: string[] = [];
  if (!facts.accident_type) missing.push("사고 유형");
  if (!facts.signal_state) missing.push("신호 상태");
  if (facts.injury === undefined || facts.injury === null) missing.push("다친 사람이 있는지");
  if (!facts.opponent_behavior) missing.push("상대 차량의 행동");
  if (!facts.damage_level) missing.push("차량 파손 정도");
  return missing;
}
function safeEvidenceSummaries(evidence: any[]) {
  return evidence.slice(0, 5).map((ev: AnyRecord) => cleanText(ev.related_reason ?? ev.plain_summary ?? ev.used_for ?? ev.title, "이 사고 판단에 참고할 수 있는 근거입니다."));
}
function toNumber(value: any, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}
function coverageLabel(level: any) {
  if (level === "high" || level === "높음") return "높음";
  if (level === "low" || level === "낮음") return "낮음";
  return "보통";
}
function composeEvidenceReliabilityCard(result: AnyRecord = {}) {
  const claim = result.claim_evidence ?? {};
  const coverage = result.evidence_audit?.claim_evidence_coverage ?? {};
  const claimCount = toNumber(claim.claim_count);
  const supportedCount = toNumber(claim.supported_claim_count);
  const unsupportedCount = toNumber(claim.unsupported_claim_count ?? coverage.unsupported_claim_count);
  const weakCount = toNumber(claim.weak_claim_count ?? coverage.weak_claim_count);
  const level = coverageLabel(claim.coverage_level ?? coverage.level);
  const ratioRaw = toNumber(claim.coverage_ratio ?? coverage.ratio, 0);
  const ratio = ratioRaw > 1 ? Math.round(ratioRaw) : Math.round(ratioRaw * 100);
  if (!claimCount && !coverage.level && !claim.coverage_level) return undefined;
  const warnings = asArray(claim.warnings)
    .map((item) => cleanText(item, "근거 확인이 필요한 항목이 있습니다."))
    .filter(Boolean)
    .slice(0, 4);
  const summary = claimCount
    ? `주요 판단 ${claimCount}개 중 ${supportedCount}개가 근거와 연결되었습니다.`
    : "주요 판단과 근거 문서의 연결 상태를 확인했습니다.";
  return {
    title: "근거 연결 상태",
    level_label: level,
    summary,
    stats: [
      { label: "근거 연결률", value: `${ratio}%` },
      { label: "전체 판단", value: `${claimCount}개` },
      { label: "근거 부족", value: `${unsupportedCount}개` },
      { label: "간접 근거", value: `${weakCount}개` },
    ],
    warnings,
    notice: level === "낮음"
      ? "근거가 부족한 판단은 확정 표현보다 추가 확인이 필요한 참고 정보로 보셔야 합니다."
      : "근거와 연결된 판단이라도 최종 판단은 보험사, 분쟁심의위, 수사기관, 법원의 확인이 필요합니다.",
  };
}
export function enrichEasyReport(report: AnyRecord = {}, result: AnyRecord = {}) {
  const card = composeEvidenceReliabilityCard(result);
  return card ? { ...report, evidence_reliability_card: card } : report;
}
export function sanitizeEasyReport(report: AnyRecord = {}) {
  const safe: AnyRecord = {};
  for (const [key, value] of Object.entries(report)) {
    if (TECHNICAL_KEYS.has(key)) continue;
    if (key === "detail_sections") {
      safe.detail_sections = {
        evidence_summaries: asArray((value as AnyRecord)?.evidence_summaries).map((x) => cleanText(x)).slice(0, 5),
        notice: "상세 식별자와 모델 내부 정보는 일반 화면에 표시하지 않습니다."
      };
      continue;
    }
    safe[key] = sanitizeValue(value);
  }
  if (!safe.detail_sections) safe.detail_sections = { evidence_summaries: [], notice: "상세 식별자와 모델 내부 정보는 일반 화면에 표시하지 않습니다." };
  return safe;
}
function sanitizeValue(value: any): any {
  if (value === null || value === undefined) return undefined;
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return cleanText(value);
  if (Array.isArray(value)) return value.map(sanitizeValue).filter((x) => x !== undefined);
  if (typeof value === "object") {
    const out: AnyRecord = {};
    for (const [key, nested] of Object.entries(value)) {
      if (TECHNICAL_KEYS.has(key)) continue;
      const safe = sanitizeValue(nested);
      if (safe !== undefined) out[key] = safe;
    }
    return out;
  }
  return undefined;
}
export function composeEasyFallback(result: AnyRecord = {}, context: AnyRecord = {}) {
  const facts = result.structured_facts ?? context.case?.structured_facts ?? {};
  const scenario = result.scenario_type ?? facts.scenario_type ?? "general_collision";
  const evidence = asArray(result.evidence);
  const fault = result.fault_ratio ?? {};
  const legal = result.legal_liability ?? {};
  const insurance = result.insurance_guide ?? {};
  const headline = scenario === "rear_end_collision" ? "이번 사고는 정차 중 뒤차가 들이받은 사고로 보이며, 상대 차량 책임이 더 클 가능성이 높습니다." : scenario === "school_zone_child_accident" ? "어린이보호구역 사고로 보이며, 신고와 형사 문제를 꼭 확인해 보셔야 합니다." : "입력하신 사고는 추가 사실을 확인하면서 과실과 신고 필요 여부를 살펴봐야 합니다.";
  const my = typeof fault.my === "number" ? Math.round(fault.my) : scenario === "rear_end_collision" ? 10 : 50;
  const other = typeof fault.other === "number" ? Math.round(fault.other) : 100 - my;
  return enrichEasyReport(sanitizeEasyReport({
    headline,
    summary_for_user: { accident_type_label: scenarioLabel(scenario), short_summary: cleanText(result.accident_summary, "입력하신 사고 내용을 바탕으로 대응 방향을 정리했습니다."), confidence_label: Number(fault.confidence ?? 0) >= 0.65 ? "비교적 신뢰할 수 있음" : "보통", warning: "정확한 과실비율은 보험사나 분쟁심의 결과에 따라 달라질 수 있습니다." },
    top_actions: [
      { order: 1, title: "블랙박스 원본 보관", description: "영상 파일을 삭제하지 말고 따로 저장해 두세요.", importance: "매우 중요" },
      { order: 2, title: facts.injury ? "병원 진료 확인" : "사고 관련 자료 정리", description: facts.injury ? "통증이 있으면 병원 진료를 받고 진단서 또는 진료확인서를 받아두세요." : "차량 파손 사진, 사고 현장 사진, 수리 견적서를 모아두세요.", importance: "중요" },
      { order: 3, title: "보험사 사고 접수", description: "보험사에 사고를 접수하고 사고접수번호를 기록하세요.", importance: "중요" }
    ],
    fault_explanation: { title: "과실비율 참고 추정", my_label: "내 책임", other_label: "상대방 책임", my_percent: my, other_percent: other, easy_explanation: scenario === "rear_end_collision" ? "정차 중 뒤에서 추돌당한 사고라면 일반적으로 뒤차의 책임이 더 크게 볼 수 있습니다." : "입력하신 사고 내용과 근거를 바탕으로 참고용 과실비율을 추정했습니다.", why: scenario === "rear_end_collision" ? ["내 차량이 정차 중이었다는 점", "상대 차량이 뒤에서 추돌했다는 점", "뒤차는 앞차와 안전거리를 유지해야 한다는 점"] : asArray(fault.key_factors).map((x) => cleanText(x)).slice(0, 4), caution: "급정거 여부나 사고 당시 도로 상황에 따라 달라질 수 있습니다." },
    insurance_explanation: { title: "보험 처리 안내", simple_summary: cleanText(insurance.summary, "대물 접수와 대인 접수 여부를 확인해야 합니다."), steps: asArray(insurance.steps).map((x) => cleanText(x)).slice(0, 6), documents: asArray(insurance.required_documents).map((x) => cleanText(x)).slice(0, 8) },
    legal_explanation: { title: "법률상 확인할 점", simple_summary: legal.reporting_required ? "신고나 형사 문제를 확인해 볼 필요가 있습니다." : "인명피해가 있거나 큰 위반이 의심되면 신고 여부를 확인해야 합니다.", risk_label: legal.criminal_risk_level === "high" ? "높음" : legal.criminal_risk_level === "low" ? "낮음" : "보통", checklist: asArray(legal.checklist).map((x) => cleanText(x)).slice(0, 7), caution: "형사책임 여부는 경찰이나 법원의 판단이 필요합니다." },
    legal_basis_cards: evidence.slice(0, 6).map((ev: AnyRecord) => ({ law_name: cleanText(ev.law_name ?? "교통사고 관련 기준"), easy_title: cleanText(ev.article_title ?? ev.chunk_summary ?? "교통사고 관련 확인 사항"), easy_explanation: cleanText(ev.plain_summary ?? ev.snippet, "이 사고에서 확인해야 할 법률상 기준입니다."), related_to_this_case: cleanText(ev.related_reason ?? ev.used_for, "입력하신 사고 사실과 연결해서 참고할 수 있는 근거입니다."), confidence_label: "관련성이 있는 근거입니다.", source_label: cleanText(ev.source ?? "교통사고 법률 설명 자료") })),
    missing_info: { title: "더 정확한 분석을 위해 필요한 정보", items: Array.from(new Set([...detectMissingFields(facts), ...asArray(result.suggested_next_inputs).map((x) => cleanText(x)), ...asArray(result.followup_questions).map((x) => cleanText(x))])).slice(0, 6) },
    detail_sections: { evidence_summaries: safeEvidenceSummaries(evidence) }
  }), result);
}
export function composeClientReport(result: AnyRecord = {}, context: AnyRecord = {}) {
  return composeEasyFallback(result, context);
}
export function composeDebugReport(result: AnyRecord = {}, context: AnyRecord = {}) {
  return { technical: result, context };
}
