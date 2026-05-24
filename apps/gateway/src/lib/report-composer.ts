type AnyRecord = Record<string, any>;

const TECHNICAL_KEYS = new Set([
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
  "expert_guidance_sections"
]);
const BAD_VALUE_PATTERNS = [/\b[a-z]+(?:_[a-z0-9]+)+\b/g, /\b[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+\b/g, /\?\?+/g, /score\s*[:=]?\s*\d+(\.\d+)?/gi, /chunk[_ ]?id\s*[:=]?\s*[\w-]+/gi, /model[_ ]?info/gi];
const SAFE_INPUT_FIELDS = new Set(["accident_type", "signal_state", "injury", "opponent_behavior", "damage_level", "stopped", "sudden_brake", "school_zone", "victim_is_child", "crosswalk_nearby", "pedestrian_visible", "lane_change_actor", "turn_signal", "user_signal", "opponent_signal", "pedestrian_signal", "bicycle_location", "bicycle_direction", "centerline_crossed", "centerline_cross_reason", "road_obstruction", "illegal_parking_obstruction", "opposing_vehicle_present", "opposing_vehicle_did_not_stop", "secondary_collision"]);
function asArray(value: any): any[] { return Array.isArray(value) ? value : []; }
function unique(values: any[]) {
  return Array.from(new Set(values.map((value) => String(value || "").trim()).filter(Boolean)));
}
function compactDisplayItems(values: any[], questionTexts: any[] = [], limit = 8) {
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
function requiredQuestionTexts(result: AnyRecord = {}) {
  return asArray(result.required_input_questions ?? result.input_requirements?.questions)
    .map((item) => cleanText(item && typeof item === "object" ? item.question ?? item.label : item))
    .filter(Boolean)
    .slice(0, 8);
}
function requiredQuestionsForReport(result: AnyRecord = {}) {
  return asArray(result.required_input_questions ?? result.input_requirements?.questions)
    .map((item) => {
      if (!item || typeof item !== "object") return undefined;
      const field = String(item.field ?? "");
      if (!SAFE_INPUT_FIELDS.has(field)) return undefined;
      const question = cleanText(item.question ?? item.label);
      if (!question) return undefined;
      return {
        field,
        label: safeInputQuestionLabel(field, item.label ?? question),
        question,
        input_type: cleanText(item.input_type ?? "text"),
        options: asArray(item.options).map((option) => cleanText(option)).filter(Boolean).slice(0, 8),
      };
    })
    .filter(Boolean)
    .slice(0, 8);
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
function judgmentLabel(status: any) {
  if (status === "evidence_supported") return "근거 확인됨";
  if (status === "unsupported") return "근거 부족";
  if (status === "blocked_for_final") return "확정 판단 보류";
  if (status === "needs_review") return "추가 확인 필요";
  return "추가 확인 필요";
}
function faultPair(result: AnyRecord = {}) {
  const fault = result.fault_ratio ?? {};
  const my = Number(fault.my);
  const other = Number(fault.other);
  return {
    my: Number.isFinite(my) ? Math.round(my) : undefined,
    other: Number.isFinite(other) ? Math.round(other) : undefined,
  };
}
function coverageLevelOf(result: AnyRecord = {}) {
  return coverageLabel(
    result.evidence_audit?.scenario_evidence_coverage?.coverage_level
      ?? result.claim_evidence?.coverage_level
      ?? result.evidence_audit?.claim_evidence_coverage?.level
  );
}
function kniaStandardLabel(result: AnyRecord = {}) {
  const primary = result.knia_primary_match ?? asArray(result.knia_matches)[0];
  if (!primary || typeof primary !== "object") return "관련 KNIA 기준 없음";
  const chartNo = cleanText(primary.chart_no, "");
  const title = cleanText(primary.title, "");
  if (chartNo && title) return `${chartNo} ${title}`;
  return chartNo || title || "관련 KNIA 기준 없음";
}
function evidenceFamily(item: AnyRecord = {}) {
  const sourceType = String(item.source_type ?? "").toLowerCase();
  const source = [
    item.source,
    item.title,
    item.source_url,
    item.law_name,
  ].map((value) => String(value ?? "").toLowerCase()).join(" ");
  if (sourceType.startsWith("knia") || source.includes("knia") || source.includes("과실비율")) return "knia";
  if (item.chunk_id || item.law_name || source.includes("law.go.kr") || source.includes("법")) return "legal";
  return "general";
}
function evidenceStatsOf(result: AnyRecord = {}) {
  const evidence = asArray(result.evidence);
  const familyCounts = result.evidence_audit?.scenario_evidence_coverage?.evidence_family_counts ?? {};
  const legal = toNumber(familyCounts.legal, evidence.filter((item) => evidenceFamily(item) === "legal").length);
  const knia = toNumber(familyCounts.knia, evidence.filter((item) => evidenceFamily(item) === "knia").length);
  const general = toNumber(familyCounts.general, evidence.filter((item) => evidenceFamily(item) === "general").length);
  const relevant = toNumber(result.evidence_audit?.scenario_evidence_coverage?.scenario_relevant_count, 0);
  const missingRequirements = asArray(result.evidence_audit?.scenario_evidence_coverage?.missing_requirements);
  return { total: evidence.length, legal, knia, general, relevant, missingRequirements: missingRequirements.length };
}
function evidenceStatsLabel(stats: ReturnType<typeof evidenceStatsOf>) {
  return `전체 ${stats.total}개 / 관련 ${stats.relevant}개 / KNIA ${stats.knia}개`;
}
function faultABLabel(value: AnyRecord | undefined) {
  if (!value || typeof value !== "object") return "";
  const a = Number(value.A);
  const b = Number(value.B);
  if (!Number.isFinite(a) || !Number.isFinite(b)) return "";
  return `A ${Math.round(a)}% / B ${Math.round(b)}%`;
}
function adjustmentItemsOf(result: AnyRecord = {}) {
  const card = result.elderly_friendly_report?.knia_fault_adjustment_card ?? {};
  const applied = asArray(result.knia_applied_adjustments ?? card.applied_adjustments);
  return applied
    .map((item: AnyRecord) => ({
      label: cleanText(item?.label, ""),
      effect: item?.applied_effect && typeof item.applied_effect === "object"
        ? faultABLabel({ A: item.applied_effect.A, B: item.applied_effect.B })
        : "",
      reason: cleanText(asArray(item?.matched_by).join(", "), ""),
    }))
    .filter((item) => item.label)
    .slice(0, 8);
}
function adjustmentKey(item: ReturnType<typeof adjustmentItemsOf>[number]) {
  return `${item.label}|${item.effect}`.toLowerCase();
}
function adjustmentDiff(previous: AnyRecord = {}, next: AnyRecord = {}) {
  const previousItems = adjustmentItemsOf(previous);
  const nextItems = adjustmentItemsOf(next);
  const previousKeys = new Set(previousItems.map(adjustmentKey));
  const nextKeys = new Set(nextItems.map(adjustmentKey));
  return {
    added: nextItems.filter((item) => !previousKeys.has(adjustmentKey(item))).slice(0, 5),
    removed: previousItems.filter((item) => !nextKeys.has(adjustmentKey(item))).slice(0, 5),
  };
}
function adjustmentSummaryOf(result: AnyRecord = {}) {
  const card = result.elderly_friendly_report?.knia_fault_adjustment_card ?? {};
  const baseFault = result.knia_base_fault ?? card.base_fault;
  const finalFault = result.knia_final_fault ?? card.final_fault;
  const applied = adjustmentItemsOf(result);
  return {
    baseLabel: faultABLabel(baseFault),
    finalLabel: faultABLabel(finalFault),
    appliedCount: applied.length,
    applied,
  };
}
function evidenceFamilyLabel(family: string) {
  if (family === "knia") return "KNIA 기준";
  if (family === "legal") return "법률 근거";
  return "참고 근거";
}
function evidenceDisplayItem(item: AnyRecord = {}) {
  const family = evidenceFamily(item);
  const title = cleanText(
    item.title ?? item.article_title ?? item.law_name ?? item.chunk_summary ?? item.plain_summary ?? item.snippet,
    "교통사고 관련 근거"
  );
  const source = cleanText(item.source ?? item.law_name ?? item.attribution ?? evidenceFamilyLabel(family), evidenceFamilyLabel(family));
  return {
    key: evidenceKey(item, title),
    title,
    source_label: source,
    family_label: evidenceFamilyLabel(family),
  };
}
function evidenceKey(item: AnyRecord = {}, fallbackTitle = "") {
  return cleanText(
    item.chunk_id ?? item.source_url ?? item.title ?? item.article_title ?? item.law_name ?? fallbackTitle,
    fallbackTitle || "evidence"
  ).toLowerCase();
}
function evidenceDiff(previous: AnyRecord = {}, next: AnyRecord = {}) {
  const previousItems = asArray(previous.evidence).map((item) => evidenceDisplayItem(item));
  const nextItems = asArray(next.evidence).map((item) => evidenceDisplayItem(item));
  const previousKeys = new Set(previousItems.map((item) => item.key));
  const nextKeys = new Set(nextItems.map((item) => item.key));
  const added = uniqueEvidenceItems(nextItems.filter((item) => !previousKeys.has(item.key))).slice(0, 5);
  const removed = uniqueEvidenceItems(previousItems.filter((item) => !nextKeys.has(item.key))).slice(0, 5);
  return {
    added: added.map(stripEvidenceKey),
    removed: removed.map(stripEvidenceKey),
  };
}
function uniqueEvidenceItems(items: ReturnType<typeof evidenceDisplayItem>[]) {
  const seen = new Set<string>();
  const unique = [];
  for (const item of items) {
    if (seen.has(item.key)) continue;
    seen.add(item.key);
    unique.push(item);
  }
  return unique;
}
function stripEvidenceKey(item: ReturnType<typeof evidenceDisplayItem>) {
  return {
    title: item.title,
    source_label: item.source_label,
    family_label: item.family_label,
  };
}
function questionCountOf(result: AnyRecord = {}) {
  return asArray(result.required_input_questions ?? result.input_requirements?.questions).length;
}
function pushChange(changes: AnyRecord[], label: string, beforeValue: any, afterValue: any) {
  const beforeText = cleanText(beforeValue, "");
  const afterText = cleanText(afterValue, "");
  if (!beforeText || !afterText || beforeText === afterText) return;
  changes.push({ label, before: beforeText, after: afterText });
}
function followupFieldLabels(values: any) {
  return unique(asArray(values)
    .map((field) => String(field))
    .filter((field) => SAFE_INPUT_FIELDS.has(field))
    .map((field) => videoFactLabel(field))
    .filter(Boolean)
  ).slice(0, 8);
}
function followupAnswerItems(answeredLabels: string[], unresolvedLabels: string[], ignoredCount: number) {
  const answered = answeredLabels.map((label) => ({
    label,
    status_label: "분석 반영",
    explanation: "선택한 답변을 케이스 입력값으로 반영해 다시 판단했습니다.",
  }));
  const unresolved = unresolvedLabels.map((label) => ({
    label,
    status_label: "추가 확인 필요",
    explanation: "확인 필요로 남겨 확정 사실에는 반영하지 않았습니다.",
  }));
  const ignored = ignoredCount
    ? [{
        label: "반영 제외 답변",
        status_label: `${ignoredCount}개 제외`,
        explanation: "지원하지 않는 항목이거나 빈 답변이라 분석 입력에서 제외했습니다.",
      }]
    : [];
  return [...answered, ...unresolved, ...ignored].slice(0, 10);
}
export function composeReanalysisChangeCard(previous: AnyRecord | undefined, next: AnyRecord = {}, followupContext: AnyRecord = {}) {
  if (!previous || !Object.keys(previous).length) return undefined;
  const beforeFault = faultPair(previous);
  const afterFault = faultPair(next);
  const beforeEvidence = evidenceStatsOf(previous);
  const afterEvidence = evidenceStatsOf(next);
  const evidenceChanges = evidenceDiff(previous, next);
  const beforeAdjustments = adjustmentSummaryOf(previous);
  const afterAdjustments = adjustmentSummaryOf(next);
  const adjustmentChanges = adjustmentDiff(previous, next);
  const beforeQuestionCount = toNumber(followupContext.before_question_count, questionCountOf(previous));
  const afterQuestionCount = toNumber(followupContext.after_question_count, questionCountOf(next));
  const questionDelta = beforeQuestionCount - afterQuestionCount;
  const answeredLabels = followupFieldLabels(followupContext.answered_fields);
  const unresolvedLabels = followupFieldLabels(followupContext.unresolved_fields);
  const ignoredCount = asArray(followupContext.ignored_fields).length;
  const answerItems = followupAnswerItems(answeredLabels, unresolvedLabels, ignoredCount);
  const beforeJudgment = judgmentLabel(previous.agent_judgment?.overall_status);
  const afterJudgment = judgmentLabel(next.agent_judgment?.overall_status);
  const reflection = next.reflection_loop ?? next.model_info?.reflection_loop ?? {};
  const changes: AnyRecord[] = [];

  pushChange(changes, "사고 유형", scenarioLabel(previous.scenario_type), scenarioLabel(next.scenario_type));
  if (beforeFault.my !== undefined && afterFault.my !== undefined && beforeFault.other !== undefined && afterFault.other !== undefined) {
    pushChange(changes, "과실비율", `내 책임 ${beforeFault.my}% / 상대 ${beforeFault.other}%`, `내 책임 ${afterFault.my}% / 상대 ${afterFault.other}%`);
  }
  pushChange(changes, "대표 KNIA 기준", kniaStandardLabel(previous), kniaStandardLabel(next));
  pushChange(changes, "근거 충족도", coverageLevelOf(previous), coverageLevelOf(next));
  pushChange(changes, "근거 구성", evidenceStatsLabel(beforeEvidence), evidenceStatsLabel(afterEvidence));
  pushChange(changes, "KNIA 기본과실", beforeAdjustments.baseLabel, afterAdjustments.baseLabel);
  pushChange(changes, "KNIA 가감 후 과실", beforeAdjustments.finalLabel, afterAdjustments.finalLabel);
  if (beforeAdjustments.appliedCount !== afterAdjustments.appliedCount) {
    changes.push({ label: "적용된 가감요소", before: `${beforeAdjustments.appliedCount}개`, after: `${afterAdjustments.appliedCount}개` });
  }
  pushChange(changes, "판단 상태", beforeJudgment, afterJudgment);
  if (beforeEvidence.missingRequirements !== afterEvidence.missingRequirements) {
    changes.push({ label: "부족한 근거 조건", before: `${beforeEvidence.missingRequirements}개`, after: `${afterEvidence.missingRequirements}개` });
  }
  if (beforeQuestionCount !== afterQuestionCount) {
    changes.push({ label: "남은 보완 질문", before: `${beforeQuestionCount}개`, after: `${afterQuestionCount}개` });
  }
  const evidenceNotes = [
    `현재 대표 KNIA 기준: ${kniaStandardLabel(next)}`,
    afterAdjustments.finalLabel
      ? `현재 KNIA 가감 후 과실: ${afterAdjustments.finalLabel}`
      : "현재 KNIA 가감 후 과실은 확인되지 않았습니다.",
    `현재 적용된 KNIA 가감요소: ${afterAdjustments.appliedCount}개`,
    `현재 근거 구성: 법률 ${afterEvidence.legal}개, KNIA ${afterEvidence.knia}개, 기타 ${afterEvidence.general}개`,
    `사고 유형과 직접 맞는 근거: ${afterEvidence.relevant}개`,
    afterEvidence.missingRequirements
      ? `아직 충족되지 않은 근거 조건이 ${afterEvidence.missingRequirements}개 남아 있습니다.`
      : "필수 근거 조건은 현재 비교 기준에서 충족된 상태입니다.",
  ];
  const decisionNotes = [
    answeredLabels.length
      ? `이번 재분석에 반영된 보완 답변: ${answeredLabels.join(", ")}`
      : "이번 재분석에서 새로 반영된 보완 답변은 확인되지 않았습니다.",
    unresolvedLabels.length
      ? `아직 확정하지 못한 답변 항목: ${unresolvedLabels.join(", ")}`
      : "보완 답변 중 미해결로 남은 항목은 없습니다.",
    ignoredCount
      ? `분석 입력으로 쓰이지 않은 답변 ${ignoredCount}개는 안전하게 제외했습니다.`
      : "",
    beforeJudgment !== afterJudgment
      ? `판단 상태가 ${beforeJudgment}에서 ${afterJudgment}(으)로 바뀌었습니다.`
      : `판단 상태는 ${afterJudgment}로 유지되었습니다.`,
    beforeQuestionCount !== afterQuestionCount
      ? `남은 보완 질문이 ${beforeQuestionCount}개에서 ${afterQuestionCount}개로 바뀌었습니다.`
      : answeredLabels.length
        ? "보완 답변은 반영됐지만 남은 질문 수는 그대로입니다. 다른 불확실성이 아직 남아 있을 수 있습니다."
        : "",
    reflection.requery_attempted
      ? `부족한 근거를 한 번 더 검색했고 관련 근거 ${toNumber(reflection.requery_added_evidence_count, 0)}개를 추가 확인했습니다.`
      : "추가 근거 재검색 없이 기존 근거와 보완 입력으로 재판단했습니다.",
  ].filter(Boolean);

  return {
    title: "보완 입력 반영 결과",
    summary: changes.length
      ? "보완 답변을 반영해 이전 분석과 달라진 판단 항목을 정리했습니다."
      : answeredLabels.length || unresolvedLabels.length
        ? "보완 답변은 처리됐지만 핵심 판단 수치와 근거 상태는 크게 달라지지 않았습니다."
        : "추가 입력을 반영했지만 핵심 판단 수치와 근거 상태는 크게 달라지지 않았습니다.",
    status_label: afterQuestionCount
      ? "추가 확인 필요"
      : answeredLabels.length || unresolvedLabels.length
        ? "답변 처리 완료"
        : "핵심 변화 없음",
    changes,
    answer_items: answerItems,
    stats: [
      { label: "현재 내 책임", value: afterFault.my !== undefined ? `${afterFault.my}%` : "확인 필요" },
      { label: "현재 상대 책임", value: afterFault.other !== undefined ? `${afterFault.other}%` : "확인 필요" },
      { label: "근거 충족도", value: coverageLevelOf(next) },
      { label: "남은 질문", value: `${afterQuestionCount}개` },
      { label: "질문 변화", value: questionDelta > 0 ? `${questionDelta}개 감소` : questionDelta < 0 ? `${Math.abs(questionDelta)}개 증가` : "변화 없음" },
      { label: "반영 답변", value: `${answeredLabels.length}개` },
      { label: "대표 KNIA", value: kniaStandardLabel(next) },
      { label: "관련 근거", value: `${afterEvidence.relevant}개` },
    ],
    question_flow: {
      before_count: beforeQuestionCount,
      after_count: afterQuestionCount,
      answered_count: answeredLabels.length,
      unresolved_count: unresolvedLabels.length,
      ignored_count: ignoredCount,
      status_label: questionDelta > 0
        ? "질문 감소"
        : answeredLabels.length || unresolvedLabels.length
          ? "답변 반영"
          : "변화 없음",
    },
    decision_notes: decisionNotes,
    evidence_notes: evidenceNotes,
    evidence_changes: evidenceChanges,
    knia_adjustment_changes: adjustmentChanges,
    notice: "이 비교는 같은 케이스에서 직전 분석과 새 분석을 대조한 참고 정보입니다. 최종 책임 판단은 보험사, 분쟁심의위, 수사기관, 법원 판단에 따라 달라질 수 있습니다.",
  };
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
      ? "근거가 부족한 판단은 추가 확인이 필요한 참고 정보로 표시합니다."
      : "이 카드는 판단 문장과 근거 문서가 얼마나 연결됐는지 보여줍니다.",
  };
}

function composeExpertGuidanceCard(result: AnyRecord = {}) {
  const source = result.expert_guidance_sections ?? result.elderly_friendly_report?.expert_guidance_sections ?? {};
  if (!source || typeof source !== "object" || !Object.keys(source).length) return undefined;
  const legal = source.legal_prediction ?? {};
  const insurance = source.insurance_prediction ?? {};
  const missing = source.missing_facts ?? {};
  const basis = asArray(legal.basis ?? source.basis)
    .map((item: AnyRecord) => ({
      family_label: cleanText(item?.family_label, "참고 근거"),
      title: cleanText(item?.title, "교통사고 관련 근거"),
      reason: cleanText(item?.reason, "입력 사고와 연결해 참고할 수 있는 근거입니다."),
    }))
    .filter((item) => item.title)
    .slice(0, 4);
  const legalPoints = [
    ...asArray(legal.civil_points).map((item) => cleanText(item, "")),
    ...asArray(legal.criminal_points).map((item) => cleanText(item, "")),
  ].filter(Boolean).slice(0, 6);
  const insuranceSteps = asArray(insurance.expected_steps).map((item) => cleanText(item, "")).filter(Boolean).slice(0, 5);
  const documents = asArray(insurance.documents).map((item) => cleanText(item, "")).filter(Boolean).slice(0, 6);
  const missingItems = asArray(missing.items).map((item) => cleanText(item, "")).filter(Boolean).slice(0, 5);
  const statusLabel = expertGuidanceStatusLabel(source.status);

  if (!basis.length && !legalPoints.length && !insuranceSteps.length && !missingItems.length && !legal.summary && !insurance.summary) {
    return undefined;
  }

  return {
    title: "전문가 관점 예상 안내",
    status_label: statusLabel,
    summary: cleanText(source.summary, "입력 사실과 유사 근거를 바탕으로 참고용 예상 안내를 정리했습니다."),
    legal: {
      title: cleanText(legal.title, "법률 관점 예상"),
      summary: cleanText(legal.summary, ""),
      fault_range_label: cleanText(legal.fault_range_label, "과실범위 확인 필요"),
      points: legalPoints,
      limits: asArray(legal.limits).map((item) => cleanText(item, "")).filter(Boolean).slice(0, 4),
    },
    insurance: {
      title: cleanText(insurance.title, "보험 처리 예상"),
      summary: cleanText(insurance.summary, ""),
      steps: insuranceSteps,
      documents,
    },
    basis,
    missing_items: missingItems,
    notice: cleanText(source.notice, "확정 판단이 아닌 참고용 예상입니다."),
  };
}

function expertGuidanceStatusLabel(value: any) {
  const labels: AnyRecord = {
    evidence_supported_reference: "근거 확인됨",
    reference_only: "참고용",
    needs_more_facts: "추가 확인 필요",
  };
  return labels[String(value)] ?? "참고용";
}

function composeVideoFactExplanationCard(result: AnyRecord = {}) {
  const contract = result.video_input_contract ?? result.model_info?.video_input_contract ?? {};
  const arbitration = result.fact_arbitration ?? result.model_info?.fact_arbitration ?? {};
  const technical = contract.technical_metadata && typeof contract.technical_metadata === "object" ? contract.technical_metadata : {};
  const accepted = asArray(contract.accepted_observations);
  const uncertain = asArray(contract.uncertain_observations);
  const supporting = asArray(contract.supporting_observations);
  const observedCount = accepted.length + uncertain.length + supporting.length + asArray(contract.ignored_observations).length;
  const representativeFrameCount = toNumber(technical.representative_frame_count, 0);
  const appliedFields = asArray(arbitration.applied_video_fields).map((field) => String(field));
  const confirmedFields = asArray(arbitration.confirmed_fields).map((field) => String(field));
  const reviewItems = asArray(arbitration.conflicts);
  const hasVideoFacts = accepted.length || uncertain.length || supporting.length || appliedFields.length || confirmedFields.length || reviewItems.length;
  const hasVideoProcessing = Boolean(contract.version) && (representativeFrameCount > 0 || Boolean(contract.observation_quality_summary));
  if (!hasVideoFacts && !hasVideoProcessing) return undefined;
  const qualitySummary = videoObservationQualitySummary(contract, representativeFrameCount);

  const observationByField = new Map<string, AnyRecord>();
  for (const item of accepted) {
    const field = String(item?.field ?? "");
    if (field && !observationByField.has(field)) observationByField.set(field, item);
  }

  const appliedItems = appliedFields
    .map((field) => {
      const observation = observationByField.get(field) ?? {};
      const value = contract.fact_patch?.[field] ?? observation.value;
      return {
        label: videoFactLabel(field),
        value: videoFactValueLabel(field, value),
        confidence: confidenceLabel(observation.confidence),
        frame_label: frameCountLabel(observation.frame_refs),
        explanation: "영상 프레임에서 직접 확인 가능한 물리적 사실로 보아 분석 입력에 반영했습니다.",
      };
    })
    .filter((item) => item.label && item.value)
    .slice(0, 6);

  const confirmedItems = confirmedFields
    .map((field) => {
      const observation = observationByField.get(field) ?? {};
      const value = contract.fact_patch?.[field] ?? observation.value;
      return {
        label: videoFactLabel(field),
        value: videoFactValueLabel(field, value),
        confidence: confidenceLabel(observation.confidence),
        frame_label: frameCountLabel(observation.frame_refs),
        explanation: "영상 관찰값이 기존 입력과 같은 방향이라, 해당 사실을 확인된 입력으로 유지했습니다.",
      };
    })
    .filter((item) => item.label && item.value)
    .slice(0, 6);

  const conflictItems = reviewItems
    .map((item: AnyRecord) => {
      const field = String(item?.field ?? "");
      const winner = String(item?.winner ?? item?.selected_source ?? "");
      const videoValue = item.video_value;
      const userValue = item.user_value;
      const selectedValue = winner === "video" ? item.video_value : item.user_value;
      const videoValueLabel = videoFactValueLabel(field, videoValue);
      const userValueLabel = videoFactValueLabel(field, userValue);
      return {
        label: videoFactLabel(field),
        selected_source: winner === "video" ? "영상" : "사용자 입력",
        selected_value: videoFactValueLabel(field, selectedValue),
        input_label: userValueLabel,
        video_label: videoValueLabel,
        status_label: winner === "video" ? "영상 기준 반영" : "확인 후 사용자 입력 유지",
        comparison: userValueLabel && videoValueLabel
          ? `사용자 입력은 ${userValueLabel}, 영상 관찰은 ${videoValueLabel}로 달라 보입니다.`
          : "",
        confidence: confidenceLabel(item.video_confidence ?? item.confidence),
        frame_label: frameCountLabel(item.frame_refs),
        explanation: winner === "video"
          ? "영상에서 직접 확인 가능한 물리적 사실이라 영상 기준을 우선 적용했습니다."
          : "영상 관찰값이 기존 입력과 다르지만, 확정 기준을 넘지 않아 사용자 입력을 유지하고 확인 질문으로 넘겼습니다.",
      };
    })
    .filter((item) => item.label)
    .slice(0, 5);

  const uncertainItems = uncertain
    .map((item: AnyRecord) => ({
      label: videoFactLabel(String(item?.field ?? "")),
      confidence: confidenceLabel(item?.confidence),
      explanation: "신뢰도나 프레임 근거가 충분하지 않아 바로 반영하지 않고 확인 질문으로 넘겼습니다.",
    }))
    .filter((item) => item.label)
    .slice(0, 5);

  const supportingItems = supporting
    .map((item: AnyRecord) => ({
      label: videoFactLabel(String(item?.field ?? "")),
      value: videoFactValueLabel(String(item?.field ?? ""), item?.value),
      confidence: confidenceLabel(item?.confidence),
      explanation: "충돌 방향처럼 의미는 있지만 단독으로 과실 판단 사실이 되지는 않는 참고 관찰입니다.",
    }))
    .filter((item) => item.label && item.value)
    .slice(0, 5);

  const summary = appliedItems.length
    ? "영상에서 확인된 물리적 사실을 판단 입력에 우선 반영했습니다."
    : confirmedItems.length
      ? "영상 관찰값이 기존 입력과 같은 사실을 확인해 판단 근거를 보강했습니다."
      : conflictItems.length
        ? "영상 관찰값과 기존 입력이 달라 사용자 확인이 필요한 상태입니다."
        : uncertainItems.length
          ? "영상에서 사고 사실 후보를 찾았지만 바로 반영하지 않고 사용자 확인 질문으로 넘겼습니다."
          : supportingItems.length
            ? "영상에서 참고 관찰값은 확인했지만, 단독으로 판단 사실에 반영하지는 않았습니다."
          : representativeFrameCount
            ? "영상 프레임은 추출됐지만 현재 기준으로 바로 판단에 반영할 수 있는 물리 사실은 확인되지 않았습니다."
            : "영상 관찰값은 확인됐지만 기존 입력과 충돌하지 않았습니다.";

  return {
    title: "영상 기반 사실 반영",
    summary,
    stats: [
      ...(representativeFrameCount ? [{ label: "대표 프레임", value: `${representativeFrameCount}장` }] : []),
      { label: "영상 관찰 후보", value: `${observedCount}개` },
      { label: "판단 반영", value: `${appliedItems.length}개` },
      { label: "영상 확인", value: `${confirmedItems.length}개` },
      { label: "입력 충돌 검토", value: `${conflictItems.length}개` },
      { label: "확인 필요", value: `${uncertainItems.length}개` },
      ...(supportingItems.length ? [{ label: "참고 관찰", value: `${supportingItems.length}개` }] : []),
      { label: "품질 상태", value: qualitySummary.status_label },
    ],
    quality_summary: qualitySummary,
    applied_items: appliedItems,
    confirmed_items: confirmedItems,
    review_items: conflictItems,
    uncertain_items: uncertainItems,
    supporting_items: supportingItems,
    notice: "영상 관찰값은 프레임에서 보이는 사실 후보입니다. 신뢰도와 프레임 근거가 충분한 물리 사실만 판단 입력에 반영합니다.",
  };
}

function videoObservationQualitySummary(contract: AnyRecord = {}, representativeFrameCount = 0) {
  const summary = contract.observation_quality_summary && typeof contract.observation_quality_summary === "object"
    ? contract.observation_quality_summary
    : {};
  const acceptedCount = toNumber(summary.accepted_count, asArray(contract.accepted_observations).length);
  const uncertainCount = toNumber(summary.uncertain_count, asArray(contract.uncertain_observations).length);
  const ignoredCount = toNumber(summary.ignored_count, asArray(contract.ignored_observations).length);
  const supportingCount = toNumber(summary.supporting_count, asArray(contract.supporting_observations).length);
  const singleFrameCount = toNumber(summary.accepted_single_frame_count, 0);
  const multiFrameCount = toNumber(summary.accepted_multi_frame_count, 0);
  const reasonEntries = Object.entries(summary.uncertain_reasons ?? {})
    .map(([reason, count]) => ({
      label: videoObservationReasonLabel(reason),
      count: toNumber(count),
    }))
    .filter((item) => item.label && item.count > 0)
    .slice(0, 5);
  const notes = [
    !acceptedCount && !uncertainCount && !ignoredCount && !supportingCount && representativeFrameCount
      ? `대표 프레임 ${representativeFrameCount}장을 확인했지만 확정 가능한 사고 사실 관찰값은 만들지 않았습니다.`
      : "",
    acceptedCount
      ? `품질 기준을 통과한 영상 관찰값 ${acceptedCount}개를 확인했습니다.`
      : "바로 반영할 수 있는 영상 관찰값은 아직 없습니다.",
    singleFrameCount
      ? `단일 프레임에서만 보인 관찰값 ${singleFrameCount}개는 보강 정보로만 신중하게 사용합니다.`
      : "",
    multiFrameCount
      ? `복수 프레임에서 반복 확인된 관찰값 ${multiFrameCount}개가 있습니다.`
      : "",
    uncertainCount || ignoredCount
      ? `추가 확인이 필요한 관찰값 ${uncertainCount + ignoredCount}개는 확정 사실로 반영하지 않았습니다.`
      : "",
    supportingCount
      ? `충돌 방향 등 참고 관찰값 ${supportingCount}개는 사용자 확인이나 다른 사실과 함께만 해석합니다.`
      : "",
  ].filter(Boolean);
  return {
    status_label: videoObservationQualityStatus(acceptedCount, uncertainCount, ignoredCount, representativeFrameCount),
    accepted_count: acceptedCount,
    uncertain_count: uncertainCount,
    ignored_count: ignoredCount,
    supporting_count: supportingCount,
    representative_frame_count: representativeFrameCount,
    single_frame_count: singleFrameCount,
    multi_frame_count: multiFrameCount,
    hold_items: reasonEntries,
    notes,
  };
}

function videoObservationQualityStatus(acceptedCount: number, uncertainCount: number, ignoredCount: number, representativeFrameCount = 0) {
  if (acceptedCount > 0 && uncertainCount + ignoredCount === 0) return "반영 가능";
  if (acceptedCount > 0) return "일부 반영";
  if (uncertainCount + ignoredCount > 0) return "확인 필요";
  if (representativeFrameCount > 0) return "확정 사실 없음";
  return "확인 필요";
}

function videoObservationReasonLabel(value: string) {
  const labels: AnyRecord = {
    confidence_below_field_threshold: "신뢰도 기준 미달",
    missing_frame_reference: "프레임 근거 없음",
    missing_field_or_value: "관찰 항목 불명확",
    unsupported_field: "지원하지 않는 관찰 항목",
    unsupported_source: "지원하지 않는 관찰 출처",
    invalid_source: "관찰 출처 확인 필요",
    unknown: "확인 필요",
  };
  return labels[value] ?? cleanText(value, "");
}

function composeVideoConflictQuestions(result: AnyRecord = {}) {
  const arbitration = result.fact_arbitration ?? result.model_info?.fact_arbitration ?? {};
  const questions: AnyRecord[] = [];
  for (const item of asArray(arbitration.conflicts)) {
    const field = String(item?.field ?? "");
    if (!SAFE_INPUT_FIELDS.has(field)) continue;
    const winner = String(item?.winner ?? item?.selected_source ?? "");
    const selectedValue = winner === "video" ? item.video_value : item.user_value;
    const alternateValue = winner === "video" ? item.user_value : item.video_value;
    const selectedLabel = videoFactValueLabel(field, selectedValue);
    const alternateLabel = videoFactValueLabel(field, alternateValue);
    const userLabel = videoFactValueLabel(field, item.user_value);
    const videoLabel = videoFactValueLabel(field, item.video_value);
    const label = videoFactLabel(field);
    const options = unique([selectedLabel, alternateLabel, "확인 필요"]).filter((value: string) => value !== "확인 필요" || selectedLabel !== "확인 필요");
    const question = videoConflictQuestionText(field, label, videoLabel, userLabel, selectedLabel);
    questions.push({
      field,
      label,
      question,
      input_type: "single_choice",
      options: options.length ? options : ["맞음", "아님", "확인 필요"],
    });
  }
  return questions.slice(0, 4);
}

function composeVideoQualityQuestions(result: AnyRecord = {}) {
  const contract = result.video_input_contract ?? result.model_info?.video_input_contract ?? {};
  const questions: AnyRecord[] = [];
  const observations = asArray(contract.uncertain_observations).sort(compareVideoObservationPriority);
  for (const item of observations) {
    const field = String(item?.field ?? "");
    if (!SAFE_INPUT_FIELDS.has(field)) continue;
    const label = videoFactLabel(field);
    const observedLabel = videoFactValueLabel(field, item?.value);
    const question = videoQualityQuestionText(field, label, observedLabel);
    questions.push({
      field,
      label,
      question,
      input_type: "single_choice",
      options: videoFactQuestionOptions(field, item?.value),
    });
  }
  return questions.slice(0, 4);
}

function videoConflictQuestionText(field: string, label: string, videoLabel: string, userLabel: string, selectedLabel: string) {
  if (field === "stopped") {
    return `충돌 직전 내 차량이 완전히 정차 중이었나요, 움직이는 중이었나요? 영상 관찰은 ${videoLabel}, 기존 입력은 ${userLabel}입니다.`;
  }
  if (field === "opponent_behavior") {
    return `충돌 직전 상대 차량은 어떤 행동을 했나요? 영상 관찰은 ${videoLabel}, 기존 입력은 ${userLabel}입니다.`;
  }
  if (userLabel && videoLabel && userLabel !== videoLabel) {
    return `영상 기준 ${label}: ${videoLabel}, 기존 입력: ${userLabel}입니다. 실제 상황은 어느 쪽에 가깝나요?`;
  }
  return `${label}은(는) ${selectedLabel}로 보입니다. 실제와 맞나요?`;
}

function videoQualityQuestionText(field: string, label: string, observedLabel: string) {
  if (field === "stopped") {
    return observedLabel && observedLabel !== "확인 필요"
      ? `충돌 직전 내 차량이 ${observedLabel}처럼 보였지만, 신뢰도가 충분하지 않았습니다. 실제로는 정차 중이었나요, 움직이는 중이었나요?`
      : "영상만으로는 충돌 직전 내 차량의 정차 여부를 충분히 확인하지 못했습니다. 실제 상황을 선택해 주세요.";
  }
  if (field === "opponent_behavior") {
    return observedLabel && observedLabel !== "확인 필요"
      ? `영상에서 상대 차량 행동이 ${observedLabel}처럼 보였지만, 신뢰도가 충분하지 않았습니다. 실제 상대 차량의 행동을 선택해 주세요.`
      : "영상만으로는 충돌 직전 상대 차량 행동을 충분히 확인하지 못했습니다. 실제 상황을 선택해 주세요.";
  }
  return observedLabel && observedLabel !== "확인 필요"
    ? `영상에서 ${label}이(가) ${observedLabel}처럼 보였지만, 신뢰도가 충분하지 않아 바로 반영하지 않았습니다. 실제 상황은 어느 쪽에 가깝나요?`
    : `영상만으로는 ${label}을(를) 충분히 확인하지 못했습니다. 실제 상황을 선택해 주세요.`;
}

function compareVideoObservationPriority(left: AnyRecord, right: AnyRecord) {
  const leftField = String(left?.field ?? "");
  const rightField = String(right?.field ?? "");
  const fieldDelta = videoQuestionPriority(leftField) - videoQuestionPriority(rightField);
  if (fieldDelta !== 0) return fieldDelta;
  const frameDelta = frameRefCount(right?.frame_refs) - frameRefCount(left?.frame_refs);
  if (frameDelta !== 0) return frameDelta;
  return toNumber(right?.confidence, 0) - toNumber(left?.confidence, 0);
}

function videoQuestionPriority(field: string) {
  const order: AnyRecord = {
    stopped: 10,
    opponent_behavior: 20,
    centerline_crossed: 30,
    centerline_cross_reason: 40,
    road_obstruction: 50,
    illegal_parking_obstruction: 60,
    opposing_vehicle_present: 70,
    opposing_vehicle_did_not_stop: 80,
    secondary_collision: 90,
    sudden_brake: 100,
    lane_change_actor: 110,
    opponent_signal_violation: 120,
    user_signal: 130,
    opponent_signal: 140,
    turn_signal: 150,
    crosswalk_nearby: 160,
    pedestrian_visible: 170,
    school_zone: 180,
    injury: 190,
    damage_level: 200,
  };
  return toNumber(order[field], 999);
}

function frameRefCount(value: any) {
  return asArray(value).filter((item) => String(item ?? "").trim()).length;
}

function combineVideoQuestions(...groups: AnyRecord[][]) {
  const combined: AnyRecord[] = [];
  const seen = new Set<string>();
  for (const question of groups.flat()) {
    const field = String(question?.field ?? "");
    if (!field || seen.has(field)) continue;
    seen.add(field);
    combined.push(question);
  }
  return combined.slice(0, 6);
}

function videoFactQuestionOptions(field: string, observedValue: any) {
  const observedLabel = videoFactValueLabel(field, observedValue);
  const optionMap: AnyRecord = {
    stopped: ["정차 중", "주행 중", "확인 필요"],
    sudden_brake: ["급정거함", "급정거 아님", "확인 필요"],
    opponent_behavior: ["뒤에서 추돌", "차선 변경", "신호 위반", "확인 필요"],
    lane_change_actor: ["내 차량", "상대 차량", "양측", "확인 필요"],
    turn_signal: ["켰음", "켜지 않음", "확인 필요"],
    user_signal: ["녹색", "황색", "적색", "신호 없음", "확인 필요"],
    opponent_signal: ["녹색", "황색", "적색", "신호 없음", "확인 필요"],
    opponent_signal_violation: ["예", "아니오", "확인 필요"],
    crosswalk_nearby: ["횡단보도 주변", "횡단보도 아님", "확인 필요"],
    pedestrian_visible: ["보행자 보임", "보행자 보이지 않음", "확인 필요"],
    centerline_crossed: ["중앙선 침범 있음", "중앙선 침범 없음", "확인 필요"],
    centerline_cross_reason: ["주차 차량/장애물 회피", "차로 이탈", "확인 필요"],
    road_obstruction: ["도로 장애물 있음", "도로 장애물 없음", "확인 필요"],
    illegal_parking_obstruction: ["불법 주정차 영향 있음", "불법 주정차 영향 없음", "확인 필요"],
    opposing_vehicle_present: ["마주오던 차량 있음", "마주오던 차량 없음", "확인 필요"],
    opposing_vehicle_did_not_stop: ["상대가 멈추지 않음", "상대가 멈춤/감속", "확인 필요"],
    secondary_collision: ["2차 충돌 있음", "2차 충돌 없음", "확인 필요"],
    school_zone: ["어린이보호구역 맞음", "어린이보호구역 아님", "확인 필요"],
    injury: ["다친 사람 있음", "다친 사람 없음", "확인 필요"],
    damage_level: ["경미", "보통", "심함", "확인 필요"],
  };
  const defaults = optionMap[field] ?? [observedLabel, "아님", "확인 필요"];
  return unique([observedLabel, ...defaults]).filter(Boolean).slice(0, 5);
}

function mergeVideoQuestions(report: AnyRecord = {}, questions: AnyRecord[] = []) {
  if (!questions.length) return prioritizeMissingInfo(report);
  const missing = report.missing_info && typeof report.missing_info === "object" ? report.missing_info : {};
  const existingQuestions = asArray(missing.questions);
  const videoFields = new Set(questions.map((item: AnyRecord) => String(item?.field ?? "")).filter(Boolean));
  const existingFields = new Set(
    existingQuestions
      .map((item: AnyRecord) => String(item?.field ?? ""))
      .filter((field: string) => field && !videoFields.has(field))
  );
  const nextQuestions = [
    ...existingQuestions.filter((item: AnyRecord) => !videoFields.has(String(item?.field ?? ""))),
    ...questions.filter((item) => !existingFields.has(String(item.field))),
  ].slice(0, 8);
  const questionTexts = nextQuestions.map((item) => item?.question);
  const nextItems = compactDisplayItems([
    ...asArray(missing.items).map((item) => cleanText(item, "")),
    ...questions.map((item) => cleanText(item.question, "")),
  ], questionTexts, 8);
  return prioritizeMissingInfo({
    ...report,
    missing_info: {
      ...missing,
      title: cleanText(missing.title, "더 정확한 분석을 위해 확인할 정보"),
      items: nextItems,
      questions: nextQuestions,
    },
  });
}

function prioritizeMissingInfo(report: AnyRecord = {}) {
  const missing = report.missing_info && typeof report.missing_info === "object" ? report.missing_info : undefined;
  if (!missing) return report;
  const questions = asArray(missing.questions)
    .map((item, index) => annotateMissingInfoQuestion(item, index))
    .filter(Boolean)
    .sort((a: AnyRecord, b: AnyRecord) => toNumber(a.priority_order, 999) - toNumber(b.priority_order, 999))
    .slice(0, 8)
    .map(({ priority_order: _priorityOrder, ...item }) => item);
  if (!questions.length) return report;
  const questionTexts = questions.map((item: AnyRecord) => item.question);
  const items = compactDisplayItems(asArray(missing.items), questionTexts, 8);
  const priorityItems = questions.slice(0, 3).map((item: AnyRecord) => ({
    label: item.label,
    question: replaceRawFieldTokens(item.question),
    priority_label: item.priority_label,
    reason: replaceRawFieldTokens(item.priority_reason),
  }));
  const top = priorityItems[0];
  return {
    ...report,
    missing_info: {
      ...missing,
      items,
      questions,
      priority_items: priorityItems,
      next_focus: top,
      guidance: top
        ? `${top.label}부터 확인하면 다음 재분석에서 판단 근거를 가장 먼저 보강할 수 있습니다.`
        : cleanText(missing.guidance, ""),
    },
  };
}

function annotateMissingInfoQuestion(value: any, index = 0) {
  if (!value || typeof value !== "object") return undefined;
  const field = String(value.field ?? "");
  if (!SAFE_INPUT_FIELDS.has(field)) return undefined;
  const label = safeInputQuestionLabel(field, value.label);
  const question = replaceRawFieldTokens(cleanText(value.question ?? label, ""));
  if (!question) return undefined;
  const priority = missingInfoQuestionPriority(field);
  return {
    ...value,
    field,
    label,
    question,
    priority_label: missingInfoPriorityLabel(priority),
    priority_reason: missingInfoPriorityReason(field),
    priority_order: priority * 100 + index,
  };
}

function missingInfoQuestionPriority(field: string) {
  const order: AnyRecord = {
    accident_type: 1,
    stopped: 2,
    opponent_behavior: 3,
    centerline_crossed: 4,
    centerline_cross_reason: 5,
    road_obstruction: 6,
    illegal_parking_obstruction: 7,
    opposing_vehicle_present: 8,
    opposing_vehicle_did_not_stop: 9,
    secondary_collision: 10,
    sudden_brake: 11,
    lane_change_actor: 12,
    opponent_signal_violation: 13,
    user_signal: 14,
    opponent_signal: 15,
    bicycle_location: 16,
    bicycle_direction: 17,
    crosswalk_nearby: 18,
    pedestrian_visible: 19,
    pedestrian_signal: 20,
    school_zone: 21,
    victim_is_child: 22,
    injury: 23,
    damage_level: 24,
    signal_state: 25,
    turn_signal: 26,
  };
  return toNumber(order[field], 99);
}

function missingInfoPriorityLabel(priority: number) {
  if (priority <= 5) return "우선 확인";
  if (priority <= 12) return "중요";
  return "추가 확인";
}

function missingInfoPriorityReason(field: string) {
  const labels: AnyRecord = {
    accident_type: "사고 유형이 정해져야 적용할 KNIA 기준과 법률 근거를 좁힐 수 있습니다.",
    stopped: "정차 여부는 후방 추돌과 급정거 쟁점의 출발점입니다.",
    opponent_behavior: "상대 차량 행동은 과실비율 후보를 고르는 핵심 사실입니다.",
    lane_change_actor: "차선변경 주체는 차선변경 사고의 책임 방향을 가릅니다.",
    opponent_signal_violation: "신호위반은 과실과 형사 리스크 판단에 직접 영향을 줍니다.",
    user_signal: "내 차량 신호는 신호위반 여부와 책임 판단의 기준입니다.",
    opponent_signal: "상대 차량 신호는 신호위반 여부를 확인하는 기준입니다.",
    signal_state: "신호 상태는 교차로 사고 판단의 기본 조건입니다.",
    crosswalk_nearby: "횡단보도 주변 여부는 교차로와 도로 위치 맥락을 확인하는 데 필요합니다.",
    pedestrian_visible: "보행자가 실제로 보였는지는 차대사람 사고 여부를 가르는 핵심 사실입니다.",
    centerline_crossed: "중앙선 침범 여부는 복합 차대차 사고의 책임 방향을 크게 바꿉니다.",
    centerline_cross_reason: "중앙선을 넘은 이유가 주차 차량이나 장애물 회피인지 확인해야 합니다.",
    road_obstruction: "도로 장애물은 회피 가능성과 차로 침범 사유 판단에 필요합니다.",
    illegal_parking_obstruction: "불법 주정차 영향은 중앙선 회피와 상대 과실 판단에 필요합니다.",
    opposing_vehicle_present: "마주오던 차량 존재는 대향 차로 사고 구조를 확인하는 기준입니다.",
    opposing_vehicle_did_not_stop: "상대 차량의 정지 또는 감속 여부는 회피 가능성 판단에 필요합니다.",
    secondary_collision: "2차 충돌 여부는 사고 원인과 후속 책임을 분리하는 데 필요합니다.",
    school_zone: "어린이보호구역 여부는 법적 위험과 처리 절차에 영향을 줍니다.",
    injury: "인명피해 여부는 신고, 보험 처리, 법적 리스크 판단에 필요합니다.",
    damage_level: "파손 정도는 보험 처리와 후속 자료 준비에 영향을 줍니다.",
    sudden_brake: "급정거 여부는 정차/후방 추돌 사고에서 예외 사유가 될 수 있습니다.",
    turn_signal: "방향지시등 사용 여부는 차선변경 사고의 보조 판단 요소입니다.",
  };
  return labels[field] ?? "답변하면 재분석에서 불확실한 입력을 줄일 수 있습니다.";
}

function videoFactLabel(field: string) {
  const labels: AnyRecord = {
    accident_type: "사고 유형",
    signal_state: "신호 상태",
    stopped: "정차 여부",
    sudden_brake: "급정거 여부",
    opponent_behavior: "상대 차량 행동",
    lane_change_actor: "차선변경 주체",
    turn_signal: "방향지시등 사용",
    user_signal: "내 차량 신호",
    opponent_signal: "상대 차량 신호",
    opponent_signal_violation: "상대 신호위반",
    crosswalk_nearby: "횡단보도 주변",
    pedestrian_visible: "보행자 보임",
    school_zone: "어린이보호구역",
    victim_is_child: "어린이 피해 여부",
    pedestrian_signal: "보행자 신호",
    bicycle_location: "자전거 위치",
    bicycle_direction: "자전거 진행 방향",
    impact_direction: "충격 방향 참고",
    collision_direction: "충돌 방향 참고",
    centerline_crossed: "중앙선 침범",
    centerline_cross_reason: "중앙선 침범 사유",
    road_obstruction: "도로 장애물",
    illegal_parking_obstruction: "불법 주정차 영향",
    opposing_vehicle_present: "마주오던 차량",
    opposing_vehicle_did_not_stop: "상대 차량 미정지",
    secondary_collision: "2차 충돌",
    injury: "인명피해 여부",
    damage_level: "파손 정도",
  };
  return labels[field] ?? cleanText(field, "");
}

function safeInputQuestionLabel(field: string, fallback: any = "") {
  const mapped = videoFactLabel(field);
  if (mapped && mapped !== field) return mapped;
  const label = cleanText(fallback, "");
  return label && !containsBadValuePattern(label) ? label : "확인할 정보";
}

function replaceRawFieldTokens(value: any) {
  let text = cleanText(value, "");
  if (!text) return text;
  for (const field of SAFE_INPUT_FIELDS) {
    const label = videoFactLabel(field);
    if (!label || label === field) continue;
    text = text.split(field).join(label);
  }
  return text;
}

function containsBadValuePattern(value: string) {
  return BAD_VALUE_PATTERNS.some((pattern) => {
    pattern.lastIndex = 0;
    return pattern.test(value);
  });
}

function videoFactValueLabel(field: string, value: any) {
  if (typeof value === "boolean") {
    const booleanLabels: Record<string, [string, string]> = {
      stopped: ["정차 중", "주행 중"],
      sudden_brake: ["급정거함", "급정거 아님"],
      opponent_signal_violation: ["신호위반 있음", "신호위반 없음"],
      crosswalk_nearby: ["횡단보도 주변", "횡단보도 아님"],
      pedestrian_visible: ["보행자 보임", "보행자 보이지 않음"],
      school_zone: ["어린이보호구역", "어린이보호구역 아님"],
      victim_is_child: ["어린이 피해", "어린이 피해 아님"],
      injury: ["다친 사람 있음", "다친 사람 없음"],
      centerline_crossed: ["중앙선 침범 있음", "중앙선 침범 없음"],
      road_obstruction: ["도로 장애물 있음", "도로 장애물 없음"],
      illegal_parking_obstruction: ["불법 주정차 영향 있음", "불법 주정차 영향 없음"],
      opposing_vehicle_present: ["마주오던 차량 있음", "마주오던 차량 없음"],
      opposing_vehicle_did_not_stop: ["상대가 멈추지 않음", "상대가 멈춤/감속"],
      secondary_collision: ["2차 충돌 있음", "2차 충돌 없음"],
    };
    const labels = booleanLabels[field];
    if (labels) return value ? labels[0] : labels[1];
    return value ? "예" : "아니오";
  }
  const key = String(value ?? "");
  const labels: AnyRecord = {
    rear_collision: "뒤에서 추돌",
    lane_change: "차선 변경",
    signal_violation: "신호 위반",
    rear: "뒤쪽",
    front: "앞쪽",
    left: "왼쪽",
    right: "오른쪽",
    side: "측면",
    unknown: "확인 필요",
    opponent: "상대 차량",
    user: "내 차량",
    both: "양측",
    none: "없음",
    minor: "경미",
    moderate: "보통",
    severe: "심함",
    high: "높음",
    medium: "보통",
    low: "낮음",
    parked_vehicle_obstruction: "주차 차량/장애물 회피",
    road_obstruction: "도로 장애물 회피",
    lane_departure: "차로 이탈",
    illegal_parking_obstruction: "불법 주정차 영향",
  };
  return labels[key] ?? cleanText(value, "확인 필요");
}

function confidenceLabel(value: any) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "확인 필요";
  const ratio = n > 1 ? n : n * 100;
  return `${Math.max(0, Math.min(100, Math.round(ratio)))}%`;
}

function frameCountLabel(value: any) {
  const count = asArray(value).length;
  return count ? `대표 프레임 ${count}장` : "";
}

export function enrichEasyReport(report: AnyRecord = {}, result: AnyRecord = {}) {
  const card = composeEvidenceReliabilityCard(result);
  const processCard = composeAgentProcessCard(result);
  const videoFactCard = composeVideoFactExplanationCard(result);
  const expertGuidanceCard = composeExpertGuidanceCard(result);
  const videoQuestions = combineVideoQuestions(
    composeVideoConflictQuestions(result),
    composeVideoQualityQuestions(result),
  );
  const mergedReport = prioritizeMissingInfo(mergeVideoQuestions(report, videoQuestions));
  return {
    ...mergedReport,
    ...(card ? { evidence_reliability_card: card } : {}),
    ...(processCard ? { agent_process_card: processCard } : {}),
    ...(videoFactCard ? { video_fact_explanation_card: videoFactCard } : {}),
    ...(expertGuidanceCard ? { expert_guidance_card: expertGuidanceCard } : {}),
  };
}

function composeAgentProcessCard(result: AnyRecord = {}) {
  const judgment = result.agent_judgment ?? {};
  const reflection = result.reflection_loop ?? result.model_info?.reflection_loop ?? {};
  const trace = result.agent_trace ?? result.model_info?.agent_trace ?? {};
  const hasProcess = Object.keys(judgment).length || Object.keys(reflection).length || Object.keys(trace).length;
  if (!hasProcess) return undefined;

  const traceSteps = asArray(trace.steps)
    .map((step: AnyRecord) => ({
      label: traceStepLabel(step.id),
      phase_label: phaseLabel(step.phase),
      status_label: processStatusLabel(step.status),
    }))
    .filter((step) => step.label)
    .slice(0, 9);
  const blockerCount = asArray(judgment.decision_blockers).length || asArray(judgment.blocking_reasons).length;
  const missingCount = asArray(reflection.final_missing_requirements).length;
  const requeryAttempted = reflection.requery_attempted === true;
  const requeryAdded = toNumber(reflection.requery_added_evidence_count, 0);
  const nextAction = String(reflection.next_action ?? "");
  const status = String(reflection.status ?? judgment.overall_status ?? trace.overall_status ?? "");
  const summary = processSummary({ requeryAttempted, requeryAdded, nextAction, missingCount, blockerCount });
  const missingRequirementLabels = unique(asArray(reflection.final_missing_requirements).map((item) => missingRequirementLabel(String(item))).filter(Boolean)).slice(0, 5);
  const blockingFieldLabels = unique(asArray(reflection.blocking_fields).map((item) => videoFactLabel(String(item))).filter(Boolean)).slice(0, 5);
  const decisionNotes = [
    cleanText(reflection.user_message, ""),
    ...(blockingFieldLabels.length ? [`보완 입력이 필요한 항목: ${blockingFieldLabels.join(", ")}`] : []),
    ...(missingRequirementLabels.length ? [`보강이 필요한 근거 조건: ${missingRequirementLabels.join(", ")}`] : []),
    ...asArray(reflection.recovery_suggestions).map((item) => cleanText(item, "")).filter(Boolean).slice(0, 4),
  ].filter(Boolean).slice(0, 6);
  const warnings = [
    ...(blockerCount ? [`판단을 확정하기 전에 확인할 항목이 ${blockerCount}개 남아 있습니다.`] : []),
    ...(missingCount ? [`근거 조건 중 ${missingCount}개는 아직 보강이 필요합니다.`] : []),
  ].slice(0, 3);

  return {
    title: "판단 검증 흐름",
    status_label: processStatusLabel(status),
    summary,
    stats: [
      { label: "다음 처리", value: nextActionLabel(nextAction) },
      { label: "근거 재검색", value: requeryAttempted ? "실행됨" : "불필요" },
      { label: "추가 근거", value: `${requeryAdded}개` },
      { label: "검증 단계", value: `${toNumber(trace.step_count, traceSteps.length)}개` },
    ],
    steps: traceSteps,
    decision_notes: decisionNotes,
    warnings,
    notice: "일반 화면에는 판단 가능 여부, 근거 보강 여부, 보완 입력 상태만 요약합니다.",
  };
}

function processSummary(input: { requeryAttempted: boolean; requeryAdded: number; nextAction: string; missingCount: number; blockerCount: number }) {
  if (input.nextAction === "request_missing_input") return "판단을 더 좁히려면 사용자의 보완 입력이 필요합니다.";
  if (input.nextAction === "present_reference_only") return "근거 조건이 충분하지 않아 참고용 결과로만 표시됩니다.";
  if (input.nextAction === "manual_review") return "자동 판단만으로 확정하기 어려워 검토가 필요한 상태입니다.";
  if (input.requeryAttempted) return `근거가 부족한 지점을 한 번 더 검색했고, 관련 근거 ${input.requeryAdded}개를 추가로 확인했습니다.`;
  if (input.blockerCount || input.missingCount) return "입력과 근거를 확인했지만 일부 조건은 아직 보강이 필요합니다.";
  return "입력, 근거 검색, 판단 계약, 보완 질문 상태를 단계별로 확인했습니다.";
}

function traceStepLabel(value: any) {
  const labels: AnyRecord = {
    input_normalization: "입력 정리",
    fact_arbitration: "영상/사용자 사실 중재",
    scenario_classification: "사고 유형 분류",
    evidence_retrieval: "법률·KNIA 근거 검색",
    analyst_execution: "전문 분석 실행",
    claim_validation: "주장-근거 연결 검증",
    judgment_contract: "판단 가능 조건 확인",
    reflection_loop: "근거 보강 검토",
    followup_loop: "보완 질문 확인",
  };
  return labels[String(value)] ?? "";
}

function phaseLabel(value: any) {
  const labels: AnyRecord = {
    perceive: "입력",
    observe: "관찰",
    plan: "분류",
    act: "검색",
    solve: "분석",
    verify: "검증",
    guard: "통제",
    recover: "보강",
  };
  return labels[String(value)] ?? "처리";
}

function nextActionLabel(value: any) {
  const labels: AnyRecord = {
    finalize: "결과 표시 가능",
    request_missing_input: "보완 입력 필요",
    present_reference_only: "참고용 표시",
    manual_review: "수동 검토 필요",
    requery_evidence: "근거 재검색",
  };
  return labels[String(value)] ?? "확인 필요";
}

function missingRequirementLabel(value: string) {
  const labels: AnyRecord = {
    total_evidence: "전체 근거 수",
    scenario_relevant_evidence: "사고 유형 직접 근거",
    average_score: "근거 관련성",
    "family:legal": "법률 근거",
    "family:knia": "KNIA 과실 기준",
    required_input_fields: "필수 사고 사실",
  };
  return labels[value] ?? "";
}

function processStatusLabel(value: any) {
  const labels: AnyRecord = {
    completed: "완료",
    skipped: "건너뜀",
    unknown: "확인 필요",
    resolved: "해결됨",
    waiting_for_input: "입력 대기",
    reference_only: "참고용",
    needs_review: "검토 필요",
    evidence_supported: "근거 확인됨",
    unsupported: "근거 부족",
    blocked_for_final: "확정 보류",
    review_required: "검토 필요",
    partial: "부분 확인",
    insufficient: "부족",
  };
  return labels[String(value)] ?? cleanText(value, "확인 필요");
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
      if (key === "questions" && Array.isArray(nested)) {
        out[key] = nested.map(sanitizeInputQuestion).filter(Boolean);
        continue;
      }
      if (key === "priority_items" && Array.isArray(nested)) {
        out[key] = nested.map(sanitizePriorityItem).filter(Boolean).slice(0, 3);
        continue;
      }
      if (key === "next_focus" && nested && typeof nested === "object") {
        const safe = sanitizePriorityItem(nested);
        if (safe) out[key] = safe;
        continue;
      }
      const safe = sanitizeValue(nested);
      if (safe !== undefined) out[key] = safe;
    }
    return out;
  }
  return undefined;
}
function sanitizeInputQuestion(value: any) {
  if (!value || typeof value !== "object") return undefined;
  const field = String(value.field ?? "");
  if (!SAFE_INPUT_FIELDS.has(field)) return undefined;
  const question = replaceRawFieldTokens(value.question ?? value.label);
  if (!question) return undefined;
  return {
    field,
    label: safeInputQuestionLabel(field, value.label ?? question),
    question,
    input_type: String(value.input_type ?? "text"),
    options: asArray(value.options).map((option) => cleanText(option, "")).filter(Boolean).slice(0, 8),
    priority_label: cleanText(value.priority_label, ""),
    priority_reason: replaceRawFieldTokens(value.priority_reason),
  };
}
function sanitizePriorityItem(value: any) {
  if (!value || typeof value !== "object") return undefined;
  const label = replaceRawFieldTokens(value.label);
  const question = replaceRawFieldTokens(value.question);
  if (!label && !question) return undefined;
  return {
    label,
    question,
    priority_label: cleanText(value.priority_label, ""),
    reason: replaceRawFieldTokens(value.reason ?? value.priority_reason),
  };
}
export function composeEasyFallback(result: AnyRecord = {}, context: AnyRecord = {}) {
  const facts = result.structured_facts ?? context.case?.structured_facts ?? {};
  const scenario = result.scenario_type ?? facts.scenario_type ?? "general_collision";
  const evidence = asArray(result.evidence);
  const requiredQuestions = requiredQuestionTexts(result);
  const missingQuestions = requiredQuestionsForReport(result);
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
    fault_explanation: { title: "과실비율 참고 추정", my_label: "내 책임", other_label: "상대방 책임", my_percent: my, other_percent: other, easy_explanation: scenario === "rear_end_collision" ? "정차 중 뒤에서 추돌당한 사고라면 일반적으로 뒤차의 책임이 더 크게 볼 수 있습니다." : "입력하신 사고 내용과 근거를 바탕으로 참고용 과실비율을 추정했습니다.", why: scenario === "rear_end_collision" ? ["내 차량이 정차 중이었다는 점", "상대 차량이 뒤에서 추돌했다는 점", "뒤차는 앞차와 안전거리를 유지해야 한다는 점"] : asArray(fault.key_factors).map((x) => cleanText(x)).slice(0, 4), caution: "급정거 여부, 충돌 직전 움직임, 도로 상황이 확인되면 비율이 조정될 수 있습니다." },
    insurance_explanation: { title: "보험 처리 안내", simple_summary: cleanText(insurance.summary, "대물 접수와 대인 접수 여부를 확인해야 합니다."), steps: asArray(insurance.steps).map((x) => cleanText(x)).slice(0, 6), documents: asArray(insurance.required_documents).map((x) => cleanText(x)).slice(0, 8) },
    legal_explanation: { title: "법률상 확인할 점", simple_summary: legal.reporting_required ? "신고나 형사 문제를 확인해 볼 필요가 있습니다." : "인명피해가 있거나 큰 위반이 의심되면 신고 여부를 확인해야 합니다.", risk_label: legal.criminal_risk_level === "high" ? "높음" : legal.criminal_risk_level === "low" ? "낮음" : "보통", checklist: asArray(legal.checklist).map((x) => cleanText(x)).slice(0, 7), caution: "형사책임 여부는 경찰이나 법원의 판단이 필요합니다." },
    legal_basis_cards: evidence.slice(0, 6).map((ev: AnyRecord) => ({ law_name: cleanText(ev.law_name ?? "교통사고 관련 기준"), easy_title: cleanText(ev.article_title ?? ev.chunk_summary ?? "교통사고 관련 확인 사항"), easy_explanation: cleanText(ev.plain_summary ?? ev.snippet, "이 사고에서 확인해야 할 법률상 기준입니다."), related_to_this_case: cleanText(ev.related_reason ?? ev.used_for, "입력하신 사고 사실과 연결해서 참고할 수 있는 근거입니다."), confidence_label: "관련성이 있는 근거입니다.", source_label: cleanText(ev.source ?? "교통사고 법률 설명 자료") })),
    missing_info: { title: "더 정확한 분석을 위해 필요한 정보", items: Array.from(new Set([...requiredQuestions, ...(requiredQuestions.length ? [] : detectMissingFields(facts)), ...asArray(result.suggested_next_inputs).map((x) => cleanText(x)), ...asArray(result.followup_questions).map((x) => cleanText(x))])).slice(0, 6), questions: missingQuestions },
    detail_sections: { evidence_summaries: safeEvidenceSummaries(evidence) }
  }), result);
}
export function composeClientReport(result: AnyRecord = {}, context: AnyRecord = {}) {
  return composeEasyFallback(result, context);
}
export function composeDebugReport(result: AnyRecord = {}, context: AnyRecord = {}) {
  return { technical: result, context };
}
