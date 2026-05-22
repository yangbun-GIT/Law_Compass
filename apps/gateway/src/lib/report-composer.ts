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
  "video_input_contract", "_video_input_contract", "accepted_observations", "uncertain_observations", "ignored_observations", "fact_patch",
  "fact_arbitration", "_fact_arbitration", "fact_sources", "_fact_sources", "video_primary_fields", "user_primary_fields",
  "applied_video_fields", "kept_user_fields", "confirmed_fields", "conflicts", "requires_confirmation",
  "agent_trace", "reflection_loop", "trace_policy", "packet", "step_count", "requery_attempted",
  "requery_added_evidence_count", "iterations_used", "initial_requery_reasons", "final_missing_requirements", "next_action"
]);
const BAD_VALUE_PATTERNS = [/\b[a-z]+(?:_[a-z0-9]+)+\b/g, /\b[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+\b/g, /\?\?+/g, /score\s*[:=]?\s*\d+(\.\d+)?/gi, /chunk[_ ]?id\s*[:=]?\s*[\w-]+/gi, /model[_ ]?info/gi];
const SAFE_INPUT_FIELDS = new Set(["accident_type", "signal_state", "injury", "opponent_behavior", "damage_level", "stopped", "sudden_brake", "school_zone", "victim_is_child", "crosswalk_nearby", "lane_change_actor", "turn_signal", "user_signal", "opponent_signal", "pedestrian_signal", "bicycle_location", "bicycle_direction"]);
function asArray(value: any): any[] { return Array.isArray(value) ? value : []; }
function unique(values: any[]) {
  return Array.from(new Set(values.map((value) => String(value || "").trim()).filter(Boolean)));
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
      const question = cleanText(item.question ?? item.label);
      if (!question) return undefined;
      return {
        field: cleanText(item.field, ""),
        label: cleanText(item.label ?? item.field ?? question),
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
export function composeReanalysisChangeCard(previous: AnyRecord | undefined, next: AnyRecord = {}) {
  if (!previous || !Object.keys(previous).length) return undefined;
  const beforeFault = faultPair(previous);
  const afterFault = faultPair(next);
  const beforeEvidence = evidenceStatsOf(previous);
  const afterEvidence = evidenceStatsOf(next);
  const evidenceChanges = evidenceDiff(previous, next);
  const beforeAdjustments = adjustmentSummaryOf(previous);
  const afterAdjustments = adjustmentSummaryOf(next);
  const adjustmentChanges = adjustmentDiff(previous, next);
  const beforeQuestionCount = questionCountOf(previous);
  const afterQuestionCount = questionCountOf(next);
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
  pushChange(changes, "판단 상태", judgmentLabel(previous.agent_judgment?.overall_status), judgmentLabel(next.agent_judgment?.overall_status));
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

  return {
    title: "보완 입력 반영 결과",
    summary: changes.length
      ? "추가로 입력한 내용을 반영해 이전 분석과 달라진 판단 항목을 정리했습니다."
      : "추가 입력을 반영했지만 핵심 판단 수치와 근거 상태는 크게 달라지지 않았습니다.",
    changes,
    stats: [
      { label: "현재 내 책임", value: afterFault.my !== undefined ? `${afterFault.my}%` : "확인 필요" },
      { label: "현재 상대 책임", value: afterFault.other !== undefined ? `${afterFault.other}%` : "확인 필요" },
      { label: "근거 충족도", value: coverageLevelOf(next) },
      { label: "남은 질문", value: `${afterQuestionCount}개` },
      { label: "대표 KNIA", value: kniaStandardLabel(next) },
      { label: "관련 근거", value: `${afterEvidence.relevant}개` },
    ],
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
      ? "근거가 부족한 판단은 확정 표현보다 추가 확인이 필요한 참고 정보로 보셔야 합니다."
      : "근거와 연결된 판단이라도 최종 판단은 보험사, 분쟁심의위, 수사기관, 법원의 확인이 필요합니다.",
  };
}

function composeVideoFactExplanationCard(result: AnyRecord = {}) {
  const contract = result.video_input_contract ?? result.model_info?.video_input_contract ?? {};
  const arbitration = result.fact_arbitration ?? result.model_info?.fact_arbitration ?? {};
  const accepted = asArray(contract.accepted_observations);
  const uncertain = asArray(contract.uncertain_observations);
  const appliedFields = asArray(arbitration.applied_video_fields).map((field) => String(field));
  const reviewItems = asArray(arbitration.conflicts);
  const hasVideoFacts = accepted.length || uncertain.length || appliedFields.length || reviewItems.length;
  if (!hasVideoFacts) return undefined;

  const appliedItems = appliedFields
    .map((field) => {
      const observation = accepted.find((item: AnyRecord) => String(item?.field) === field) ?? {};
      const value = contract.fact_patch?.[field] ?? observation.value;
      return {
        label: videoFactLabel(field),
        value: videoFactValueLabel(field, value),
        confidence: confidenceLabel(observation.confidence),
        frame_label: frameCountLabel(observation.frame_refs),
        explanation: "영상 프레임에서 직접 확인 가능한 물리적 사실로 보아 Agent 입력에 반영했습니다.",
      };
    })
    .filter((item) => item.label && item.value)
    .slice(0, 6);

  const conflictItems = reviewItems
    .map((item: AnyRecord) => {
      const field = String(item?.field ?? "");
      const winner = String(item?.winner ?? item?.selected_source ?? "");
      const selectedValue = winner === "video" ? item.video_value : item.user_value;
      return {
        label: videoFactLabel(field),
        selected_source: winner === "video" ? "영상" : "사용자 입력",
        selected_value: videoFactValueLabel(field, selectedValue),
        confidence: confidenceLabel(item.video_confidence ?? item.confidence),
        frame_label: frameCountLabel(item.frame_refs),
        explanation: winner === "video"
          ? "영상에서 직접 확인 가능한 물리적 사실이라 영상 기준을 우선 적용했습니다."
          : "영상만으로 확정하기 어려운 항목이라 사용자 입력을 유지했습니다.",
      };
    })
    .filter((item) => item.label)
    .slice(0, 5);

  const uncertainItems = uncertain
    .map((item: AnyRecord) => ({
      label: videoFactLabel(String(item?.field ?? "")),
      confidence: confidenceLabel(item?.confidence),
      explanation: "신뢰도 기준에 미치지 않아 판단 사실로 바로 반영하지 않았습니다.",
    }))
    .filter((item) => item.label)
    .slice(0, 5);

  const summary = appliedItems.length
    ? "영상에서 확인된 물리적 사실을 Agent 판단 입력에 우선 반영했습니다."
    : uncertainItems.length
      ? "일부 영상 관찰값은 신뢰도 기준에 미치지 않아 참고로만 보관했습니다."
      : "영상 관찰값은 확인됐지만 기존 입력과 충돌하지 않았습니다.";

  return {
    title: "영상 기반 사실 반영",
    summary,
    stats: [
      { label: "확인된 영상 사실", value: `${accepted.length}개` },
      { label: "판단 반영", value: `${appliedItems.length}개` },
      { label: "입력 충돌 검토", value: `${conflictItems.length}개` },
      { label: "보류 관찰값", value: `${uncertainItems.length}개` },
    ],
    applied_items: appliedItems,
    review_items: conflictItems,
    uncertain_items: uncertainItems,
    notice: "영상 분석값도 최종 판정이 아니라 프레임에서 확인된 사실 후보입니다. 신뢰도 기준을 넘은 물리적 사실만 Agent 입력에 반영합니다.",
  };
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
    const label = videoFactLabel(field);
    const options = unique([selectedLabel, alternateLabel, "확인 필요"]).filter((value: string) => value !== "확인 필요" || selectedLabel !== "확인 필요");
    questions.push({
      field,
      label,
      question: `${label}은(는) ${selectedLabel}로 보입니다. 실제와 맞나요?`,
      input_type: "single_choice",
      options: options.length ? options : ["맞음", "아님", "확인 필요"],
    });
  }
  return questions.slice(0, 4);
}

function mergeVideoQuestions(report: AnyRecord = {}, questions: AnyRecord[] = []) {
  if (!questions.length) return report;
  const missing = report.missing_info && typeof report.missing_info === "object" ? report.missing_info : {};
  const existingQuestions = asArray(missing.questions);
  const existingFields = new Set(existingQuestions.map((item: AnyRecord) => String(item?.field ?? "")).filter(Boolean));
  const nextQuestions = [
    ...existingQuestions,
    ...questions.filter((item) => !existingFields.has(String(item.field))),
  ].slice(0, 8);
  const nextItems = unique([
    ...asArray(missing.items).map((item) => cleanText(item, "")),
    ...questions.map((item) => cleanText(item.question, "")),
  ]).filter(Boolean).slice(0, 8);
  return {
    ...report,
    missing_info: {
      ...missing,
      title: cleanText(missing.title, "더 정확한 분석을 위해 확인할 정보"),
      items: nextItems,
      questions: nextQuestions,
    },
  };
}

function videoFactLabel(field: string) {
  const labels: AnyRecord = {
    stopped: "정차 여부",
    sudden_brake: "급정거 여부",
    opponent_behavior: "상대 차량 행동",
    lane_change_actor: "차선변경 주체",
    turn_signal: "방향지시등 사용",
    user_signal: "내 차량 신호",
    opponent_signal: "상대 차량 신호",
    opponent_signal_violation: "상대 신호위반",
    crosswalk_nearby: "횡단보도 주변",
    school_zone: "어린이보호구역",
    injury: "인명피해 여부",
    damage_level: "파손 정도",
  };
  return labels[field] ?? cleanText(field, "");
}

function videoFactValueLabel(field: string, value: any) {
  if (typeof value === "boolean") return value ? "예" : "아니오";
  const key = String(value ?? "");
  const labels: AnyRecord = {
    rear_collision: "뒤에서 추돌",
    lane_change: "차선 변경",
    signal_violation: "신호 위반",
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
  const videoQuestions = composeVideoConflictQuestions(result);
  const mergedReport = mergeVideoQuestions(report, videoQuestions);
  return {
    ...mergedReport,
    ...(card ? { evidence_reliability_card: card } : {}),
    ...(processCard ? { agent_process_card: processCard } : {}),
    ...(videoFactCard ? { video_fact_explanation_card: videoFactCard } : {}),
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
    warnings,
    notice: "이 카드는 Agent 내부 원문 로그가 아니라 판단 가능 여부, 근거 보강 여부, 보완 입력 상태만 요약합니다.",
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
  const question = cleanText(value.question ?? value.label, "");
  if (!question) return undefined;
  return {
    field: SAFE_INPUT_FIELDS.has(field) ? field : "",
    label: cleanText(value.label ?? field ?? question),
    question,
    input_type: String(value.input_type ?? "text"),
    options: asArray(value.options).map((option) => cleanText(option, "")).filter(Boolean).slice(0, 8),
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
    fault_explanation: { title: "과실비율 참고 추정", my_label: "내 책임", other_label: "상대방 책임", my_percent: my, other_percent: other, easy_explanation: scenario === "rear_end_collision" ? "정차 중 뒤에서 추돌당한 사고라면 일반적으로 뒤차의 책임이 더 크게 볼 수 있습니다." : "입력하신 사고 내용과 근거를 바탕으로 참고용 과실비율을 추정했습니다.", why: scenario === "rear_end_collision" ? ["내 차량이 정차 중이었다는 점", "상대 차량이 뒤에서 추돌했다는 점", "뒤차는 앞차와 안전거리를 유지해야 한다는 점"] : asArray(fault.key_factors).map((x) => cleanText(x)).slice(0, 4), caution: "급정거 여부나 사고 당시 도로 상황에 따라 달라질 수 있습니다." },
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
