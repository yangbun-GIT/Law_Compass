import {
  BAD_VALUE_PATTERNS,
  SAFE_INPUT_FIELDS,
  TECHNICAL_KEYS,
  asArray,
  cleanText,
  compactDisplayItems,
  hasAny,
  isPlainObject,
  safeHttpUrl,
  safeKniaUrl,
  scenarioLabel,
  toNumber,
  unique,
  type AnyRecord,
} from "./report-composer-common.js";
import { applyAnalysisModeContract, normalizeAnalysisMode } from "./report-analysis-mode.js";
import { composeKniaLinkCards, removeDuplicateKniaRelatedVideo } from "./report-knia-links.js";
import { composeExpertGuidanceCard } from "./report-expert-guidance-card.js";

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

function composeVideoFactExplanationCard(result: AnyRecord = {}) {
  const contract = result.video_input_contract ?? result.model_info?.video_input_contract ?? {};
  const arbitration = result.fact_arbitration ?? result.model_info?.fact_arbitration ?? {};
  const technical = contract.technical_metadata && typeof contract.technical_metadata === "object" ? contract.technical_metadata : {};
  const accepted = asArray(contract.accepted_observations);
  const uncertain = asArray(contract.uncertain_observations);
  const supporting = asArray(contract.supporting_observations);
  const observedCount = accepted.length + uncertain.length + supporting.length + asArray(contract.ignored_observations).length;
  const representativeFrameCount = toNumber(technical.representative_frame_count, 0);
  const eventCandidate = videoAccidentEventCandidate(technical.accident_event_summary);
  const appliedFields = asArray(arbitration.applied_video_fields).map((field) => String(field));
  const confirmedFields = asArray(arbitration.confirmed_fields).map((field) => String(field));
  const reviewItems = [
    ...asArray(arbitration.conflicts),
    ...asArray(arbitration.pending_video_confirmations),
  ];
  const hasVideoFacts = accepted.length || uncertain.length || supporting.length || appliedFields.length || confirmedFields.length || reviewItems.length || eventCandidate;
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
      const status = String(item?.status ?? "");
      const videoValue = item.video_value;
      const userValue = item.user_value;
      const selectedValue = winner === "video" ? item.video_value : winner === "none" ? item.video_value : item.user_value;
      const videoValueLabel = videoFactValueLabel(field, videoValue);
      const userValueLabel = videoFactValueLabel(field, userValue);
      return {
        label: videoFactLabel(field),
        selected_source: winner === "video" ? "영상" : winner === "none" ? "확인 필요" : "사용자 입력",
        selected_value: videoFactValueLabel(field, selectedValue),
        input_label: userValueLabel,
        video_label: videoValueLabel,
        status_label: videoReviewStatusLabel(winner, status),
        comparison: userValueLabel && videoValueLabel
          ? `사용자 입력은 ${userValueLabel}, 영상 관찰은 ${videoValueLabel}로 달라 보입니다.`
          : videoValueLabel
            ? `영상에서는 ${videoValueLabel} 후보가 보였지만 확정 기준을 넘지 못했습니다.`
          : "",
        confidence: confidenceLabel(item.video_confidence ?? item.confidence),
        frame_label: frameCountLabel(item.frame_refs),
        explanation: videoReviewExplanation(winner, status),
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
      explanation: String(item?.field ?? "") === "visual_evidence_limited"
        ? "프레임은 분석됐지만 직접 판단에 반영할 만큼 확실한 물리 사실은 확인되지 않았습니다."
        : "충돌 방향처럼 의미는 있지만 단독으로 과실 판단 사실이 되지는 않는 참고 관찰입니다.",
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
          : eventCandidate
            ? "영상에서 사고 발생 구간 후보는 찾았지만, 바로 판단에 반영할 물리 사실 관찰값은 부족합니다."
          : representativeFrameCount
            ? "영상 프레임은 추출됐지만 현재 기준으로 바로 판단에 반영할 수 있는 물리 사실은 확인되지 않았습니다."
            : "영상 관찰값은 확인됐지만 기존 입력과 충돌하지 않았습니다.";

  return {
    title: "영상 기반 사실 반영",
    summary,
    stats: [
      ...(representativeFrameCount ? [{ label: "대표 프레임", value: `${representativeFrameCount}장` }] : []),
      ...(eventCandidate ? [{ label: "사고 시점 후보", value: eventCandidate.frame_label }] : []),
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
    event_candidate: eventCandidate,
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
  const recoveryActions = asArray(summary.recovery_actions)
    .map((item: AnyRecord) => ({
      label: cleanText(item?.label, ""),
      reason: cleanText(item?.reason, ""),
    }))
    .filter((item) => item.label)
    .slice(0, 4);
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
    recoveryActions.length
      ? "프레임은 충분하지만 판단 반영값이 부족해 재시도 또는 보조 분석이 필요합니다."
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
    recovery_actions: recoveryActions,
  };
}

function videoAccidentEventCandidate(value: any) {
  if (!value || typeof value !== "object") return undefined;
  const eventCount = toNumber(value.event_frame_count, 0);
  const preCount = toNumber(value.pre_impact_frame_count, 0);
  const postCount = toNumber(value.post_impact_frame_count, 0);
  if (!eventCount && !preCount && !postCount) return undefined;
  const impactVisible = value.impact_visible === true;
  return {
    label: "사고 발생 구간 후보",
    status_label: impactVisible ? "충돌 구간 후보 확인" : "충돌 전후 문맥 후보",
    frame_label: impactVisible ? `${eventCount}장` : `${preCount + postCount}장`,
    explanation: impactVisible
      ? "영상 전체 프레임 순서를 비교해 실제 충돌 또는 직후로 보이는 구간 후보를 찾았습니다. 이 정보는 품질 점검용이며, 개별 물리 사실은 별도 신뢰도 기준을 통과해야 판단에 반영됩니다."
      : "영상에서 충돌 장면 자체는 명확하지 않지만, 충돌 전후로 보이는 문맥 후보를 찾았습니다. 이 경우 사용자 입력이나 추가 자료 확인이 더 중요합니다.",
    impact_visible: impactVisible,
    event_frame_count: eventCount,
    pre_impact_frame_count: preCount,
    post_impact_frame_count: postCount,
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

function videoReviewStatusLabel(winner: string, status: string) {
  if (winner === "video") return "영상 기준 반영";
  if (status === "missing_user_fact_video_held") return "영상 후보 확인 필요";
  if (status === "user_video_conflict_video_held") return "사용자 입력 유지, 영상 후보 확인";
  if (status === "user_supported_by_held_video_needs_context_confirmation") return "사용자 입력 확인 필요";
  if (status === "user_supported_by_held_video") return "사용자 입력 보강 후보";
  return "확인 후 사용자 입력 유지";
}

function videoReviewExplanation(winner: string, status: string) {
  if (winner === "video") {
    return "영상에서 직접 확인 가능한 물리적 사실이라 영상 기준을 우선 적용했습니다.";
  }
  if (status === "missing_user_fact_video_held") {
    return "사용자 입력에는 없지만 영상에서 후보가 보였습니다. 신뢰도나 프레임 근거가 부족해 확인 질문으로 넘겼습니다.";
  }
  if (status === "user_video_conflict_video_held") {
    return "영상 후보가 기존 입력과 다르지만 확정 기준을 넘지 않아 사용자 입력을 유지하고 확인 질문으로 넘겼습니다.";
  }
  if (status === "user_supported_by_held_video_needs_context_confirmation") {
    return "영상 후보가 사용자 입력과 같은 방향이지만 사고유형을 바꿀 수 있는 핵심 맥락이 부족해 확인 질문으로 넘겼습니다.";
  }
  if (status === "user_supported_by_held_video") {
    return "영상 후보가 기존 입력과 같은 방향이지만 확정 기준은 넘지 못해 참고 보강 정보로만 표시합니다.";
  }
  return "영상 관찰값이 기존 입력과 다르지만, 확정 기준을 넘지 않아 사용자 입력을 유지하고 확인 질문으로 넘겼습니다.";
}

function composeVideoConflictQuestions(result: AnyRecord = {}) {
  const arbitration = result.fact_arbitration ?? result.model_info?.fact_arbitration ?? {};
  const questions: AnyRecord[] = [];
  const reviewItems = [
    ...asArray(arbitration.conflicts),
    ...asArray(arbitration.pending_video_confirmations),
  ].filter((item: AnyRecord) => item?.needs_confirmation !== false);
  for (const item of reviewItems) {
    const field = String(item?.field ?? "");
    if (!SAFE_INPUT_FIELDS.has(field)) continue;
    const winner = String(item?.winner ?? item?.selected_source ?? "");
    const status = String(item?.status ?? "");
    const selectedValue = winner === "video" ? item.video_value : winner === "none" ? item.video_value : item.user_value;
    const alternateValue = winner === "video" ? item.user_value : item.video_value;
    const selectedLabel = videoFactValueLabel(field, selectedValue);
    const alternateLabel = videoFactValueLabel(field, alternateValue);
    const userLabel = videoFactValueLabel(field, item.user_value);
    const videoLabel = videoFactValueLabel(field, item.video_value);
    const label = videoFactLabel(field);
    const baseOptions = status
      ? videoFactQuestionOptions(field, item.video_value)
      : [selectedLabel, alternateLabel, "확인 필요"];
    const options = unique(baseOptions).filter((value: string) => value && (value !== "확인 필요" || selectedLabel !== "확인 필요"));
    const question = status
      ? videoQualityQuestionText(field, label, videoLabel)
      : videoConflictQuestionText(field, label, videoLabel, userLabel, selectedLabel);
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
  const fieldQuestions: Record<string, string> = {
    accident_party_type: "실제 사고 대상은 어느 유형에 가깝나요?",
    accident_type: "사고 유형은 어느 쪽에 가장 가깝나요?",
    collision_partner_type: "실제로 충돌하거나 사고에 직접 관여한 대상은 무엇인가요?",
    primary_collision_target: "주된 충돌 대상은 누구 또는 무엇인가요?",
    collision_point_visible: "영상에서 실제 충돌 지점이 보이나요?",
    collision_point_location: "주된 충돌 위치는 어디에 가깝나요?",
    front_vehicle_stopped: "충돌 직전 앞차가 정차 중이었나요?",
    ego_turn_direction: "내 차량은 사고 직전 어느 방향으로 진행했나요?",
    intersection: "사고 지점이 교차로 또는 교차로 진입부인가요?",
    user_signal: "내 차량이 교차로에 진입할 때 신호는 무엇이었나요?",
    opponent_signal_visible: "영상이나 자료에서 상대 차량 신호를 확인할 수 있나요?",
    opponent_signal: "상대 차량이 교차로에 진입할 때 신호는 무엇이었나요?",
    signal_transition: "내 차량 진입부터 충돌 직전까지 신호 변화는 어느 쪽에 가깝나요?",
    opponent_signal_violation: "상대 차량이 신호를 위반했다고 볼 자료가 있나요?",
    damage_level: "차량 파손 정도는 어느 정도인가요?",
    injury: "다친 사람이 있나요?",
    crosswalk_nearby: "횡단보도는 사고 지점과 얼마나 가까웠나요?",
    pedestrian_visible: "실제 사고 대상 또는 위험 대상으로 보행자가 보였나요?",
    centerline_crossed: "내 차량 또는 상대 차량이 중앙선을 넘었나요?",
    centerline_cross_reason: "중앙선을 넘은 이유는 무엇인가요?",
    road_obstruction: "차로를 막은 장애물이나 주정차 차량이 있었나요?",
    illegal_parking_obstruction: "불법 주정차 차량이 사고 경로에 영향을 줬나요?",
    opposing_vehicle_present: "마주오던 차량이 있었나요?",
    opposing_vehicle_did_not_stop: "마주오던 차량이 멈추거나 감속했나요?",
    secondary_collision: "첫 충돌 뒤 후속 충돌이 있었나요?",
    non_contact_trigger: "직접 부딪히지 않았지만 사고를 유발한 대상이 있었나요?",
    trigger_actor_type: "사고를 유발한 대상은 무엇인가요?",
    trigger_actor_behavior: "사고 유발 대상은 어떻게 움직였나요?",
    direct_collision_partner_type: "실제로 접촉한 상대는 무엇인가요?",
    rear_vehicle_collision: "뒤에서 온 차량이 후방을 추돌했나요?",
    stopped_vehicle_without_lights: "상대 차량이 등화나 비상등 없이 정차해 있었나요?",
    highway_or_expressway: "사고 장소가 고속도로 또는 자동차전용도로인가요?",
  };
  const directQuestion = fieldQuestions[field];
  if (directQuestion) return directQuestion;
  if (observedLabel && observedLabel !== "확인 필요" && observedLabel !== label) {
    return `${label}은(는) 영상에서 ${observedLabel}처럼 보였지만 확정하기 어렵습니다. 실제 상황을 선택해 주세요.`;
  }
  return `${label}은(는) 영상만으로 충분히 확인하지 못했습니다. 실제 상황을 선택해 주세요.`;
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
    accident_party_type: 5,
    collision_partner_type: 10,
    stopped: 20,
    primary_collision_target: 30,
    collision_point_visible: 40,
    collision_point_location: 50,
    front_vehicle_stopped: 60,
    ego_turn_direction: 70,
    opponent_behavior: 80,
    intersection: 90,
    user_signal: 100,
    opponent_signal_visible: 110,
    opponent_signal: 120,
    signal_transition: 130,
    opponent_signal_violation: 140,
    centerline_crossed: 150,
    centerline_cross_reason: 160,
    road_obstruction: 170,
    illegal_parking_obstruction: 180,
    opposing_vehicle_present: 190,
    opposing_vehicle_did_not_stop: 200,
    secondary_collision: 210,
    non_contact_trigger: 220,
    trigger_actor_type: 230,
    trigger_actor_behavior: 240,
    direct_collision_partner_type: 250,
    rear_vehicle_collision: 260,
    stopped_vehicle_without_lights: 270,
    highway_or_expressway: 280,
    sudden_brake: 290,
    lane_change_actor: 300,
    turn_signal: 310,
    crosswalk_nearby: 320,
    pedestrian_visible: 330,
    pedestrian_signal: 340,
    school_zone: 350,
    injury: 360,
    damage_level: 370,
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
    accident_party_type: ["차 대 차", "차 대 사람", "차 대 자전거/이륜", "차 대 물체/시설물", "단독 사고", "확인 필요"],
    collision_partner_type: ["차량", "보행자", "자전거", "물체", "확인 필요"],
    primary_collision_target: ["상대 차량", "보행자/자전거", "시설물/장애물", "확인 필요"],
    collision_point_visible: ["충돌 지점 보임", "충돌 지점 불명확", "확인 필요"],
    collision_point_location: ["전방", "후방", "측면", "교차로 내부", "확인 필요"],
    front_vehicle_stopped: ["앞차가 정차함", "앞차 정차 아님", "확인 필요"],
    ego_turn_direction: ["우회전", "좌회전", "직진", "확인 필요"],
    intersection: ["교차로 사고", "교차로 아님", "확인 필요"],
    sudden_brake: ["급정거함", "급정거 아님", "확인 필요"],
    opponent_behavior: ["뒤에서 추돌", "차선 변경", "신호 위반", "확인 필요"],
    lane_change_actor: ["내 차량", "상대 차량", "양측", "확인 필요"],
    turn_signal: ["켰음", "켜지 않음", "확인 필요"],
    user_signal: ["녹색", "황색", "적색", "신호 없음", "확인 필요"],
    opponent_signal_visible: ["상대 신호 보임", "상대 신호 보이지 않음", "확인 필요"],
    opponent_signal: ["녹색", "황색", "적색", "신호 없음", "확인 필요"],
    signal_transition: ["녹색에서 황색", "황색에서 적색", "적색에서 녹색", "확인 필요"],
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
    non_contact_trigger: ["비접촉 유발 요인 있음", "비접촉 유발 요인 없음", "확인 필요"],
    trigger_actor_type: ["자전거", "보행자", "차량", "물체/장애물", "확인 필요"],
    trigger_actor_behavior: ["역주행/역방향", "갑작스러운 진입", "정차/장애물", "확인 필요"],
    direct_collision_partner_type: ["차량", "보행자", "자전거", "물체", "확인 필요"],
    rear_vehicle_collision: ["후방 차량 추돌 있음", "후방 차량 추돌 없음", "확인 필요"],
    stopped_vehicle_without_lights: ["등화 없는 정차 차량", "등화/표시 확인", "확인 필요"],
    highway_or_expressway: ["고속도로/자동차전용도로", "일반도로", "확인 필요"],
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
  const contextText = missingInfoContextText(report);
  const questions = asArray(missing.questions)
    .map((item, index) => annotateMissingInfoQuestion(item, index, contextText))
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

function annotateMissingInfoQuestion(value: any, index = 0, contextText = "") {
  if (!value || typeof value !== "object") return undefined;
  const field = String(value.field ?? "");
  if (!SAFE_INPUT_FIELDS.has(field)) return undefined;
  const label = safeInputQuestionLabel(field, value.label);
  const question = replaceRawFieldTokens(cleanText(value.question ?? label, ""));
  if (!question) return undefined;
  const priority = missingInfoQuestionPriority(field, contextText);
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

function missingInfoContextText(report: AnyRecord = {}) {
  return JSON.stringify({
    headline: report.headline,
    summary: report.summary,
    missing_info: report.missing_info,
    expert_guidance_card: report.expert_guidance_card,
    conditional_outcome_card: report.conditional_outcome_card,
  }).toLowerCase();
}

function missingInfoQuestionPriority(field: string, contextText = "") {
  const signalContext = hasAny(contextText, ["신호", "교차로", "좌회전", "황색", "적색", "signal", "intersection"]);
  if (signalContext) {
    const signalOrder: AnyRecord = {
      opponent_signal_visible: 1,
      opponent_signal: 1,
      opponent_signal_violation: 1,
      user_signal: 2,
      signal_transition: 2,
      signal_state: 2,
      intersection: 3,
    };
    if (signalOrder[field] !== undefined) return signalOrder[field];
  }
  const order: AnyRecord = {
    accident_party_type: 1,
    collision_partner_type: 2,
    accident_type: 3,
    stopped: 4,
    primary_collision_target: 4,
    collision_point_visible: 5,
    collision_point_location: 6,
    front_vehicle_stopped: 7,
    ego_turn_direction: 8,
    opponent_behavior: 9,
    intersection: 10,
    user_signal: 11,
    opponent_signal_visible: 12,
    opponent_signal: 13,
    signal_transition: 14,
    opponent_signal_violation: 15,
    centerline_crossed: 16,
    centerline_cross_reason: 17,
    road_obstruction: 18,
    illegal_parking_obstruction: 19,
    opposing_vehicle_present: 20,
    opposing_vehicle_did_not_stop: 21,
    secondary_collision: 22,
    non_contact_trigger: 23,
    trigger_actor_type: 24,
    trigger_actor_behavior: 25,
    direct_collision_partner_type: 26,
    rear_vehicle_collision: 27,
    stopped_vehicle_without_lights: 28,
    highway_or_expressway: 29,
    sudden_brake: 30,
    lane_change_actor: 31,
    bicycle_location: 32,
    bicycle_direction: 33,
    crosswalk_nearby: 34,
    pedestrian_visible: 35,
    pedestrian_signal: 36,
    school_zone: 37,
    victim_is_child: 38,
    injury: 39,
    damage_level: 40,
    signal_state: 41,
    turn_signal: 42,
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
    accident_party_type: "사고 대분류가 정해져야 차대차, 차대사람, 자전거, 기물 사고의 근거군을 안전하게 좁힐 수 있습니다.",
    accident_type: "사고 유형이 정해져야 적용할 KNIA 기준과 법률 근거를 좁힐 수 있습니다.",
    stopped: "정차 여부는 후방 추돌과 급정거 쟁점의 출발점입니다.",
    collision_partner_type: "사고 대상을 먼저 확인해야 차대차, 차대사람, 자전거, 기물 사고를 구분할 수 있습니다.",
    primary_collision_target: "실제로 충돌한 대상은 사고 환경보다 먼저 확정해야 하는 핵심 사실입니다.",
    collision_point_visible: "충돌 지점이 보이는지는 영상 관찰값의 신뢰도를 판단하는 기준입니다.",
    collision_point_location: "충돌 지점 위치는 상대 진행 방향과 회피 가능성 판단에 필요합니다.",
    front_vehicle_stopped: "앞차 정차 여부는 우회전·횡단보도 주변 후방 추돌에서 사고 원인을 가르는 핵심 사실입니다.",
    ego_turn_direction: "내 차량 진행 방향은 좌회전·우회전·직진 사고 기준을 나누는 기준입니다.",
    opponent_behavior: "상대 차량 행동은 과실비율 후보를 고르는 핵심 사실입니다.",
    intersection: "교차로 여부는 신호와 진입 시점 판단의 출발점입니다.",
    lane_change_actor: "차선변경 주체는 차선변경 사고의 책임 방향을 가릅니다.",
    opponent_signal_violation: "신호위반은 과실과 형사 리스크 판단에 직접 영향을 줍니다.",
    user_signal: "내 차량 신호는 신호위반 여부와 책임 판단의 기준입니다.",
    opponent_signal_visible: "상대 차량 신호가 영상에 보이지 않으면 CCTV나 신호체계 자료 확인이 필요합니다.",
    opponent_signal: "상대 차량 신호는 신호위반 여부를 확인하는 기준입니다.",
    signal_transition: "신호 변경 순서는 황색 진입과 적색 충돌 쟁점을 나누는 기준입니다.",
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
    non_contact_trigger: "직접 부딪히지 않은 유발 요인이 있는지 확인해야 실제 충돌 상대와 원인을 분리할 수 있습니다.",
    trigger_actor_type: "사고를 유발한 객체와 실제 충돌 상대를 분리해야 자전거·보행자·차량 사고를 오분류하지 않습니다.",
    trigger_actor_behavior: "유발 객체의 움직임은 급정지나 회피가 불가피했는지 판단하는 기준입니다.",
    direct_collision_partner_type: "실제로 접촉한 상대를 확인해야 과실 기준과 근거군을 안전하게 좁힐 수 있습니다.",
    rear_vehicle_collision: "후방 차량의 추돌 여부는 안전거리와 후속 책임 판단의 핵심입니다.",
    stopped_vehicle_without_lights: "등화 없는 정차 차량은 야간·고속도로 사고의 회피 가능성 판단에 필요합니다.",
    highway_or_expressway: "고속도로 또는 자동차전용도로 여부는 정차 차량 사고와 속도 쟁점 판단에 필요합니다.",
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
    accident_party_type: "사고 대분류",
    accident_type: "사고 유형",
    signal_state: "신호 상태",
    stopped: "정차 여부",
    collision_partner_type: "사고 대상 유형",
    primary_collision_target: "주 충돌 대상",
    collision_point_visible: "충돌 지점 보임",
    collision_point_location: "충돌 지점 위치",
    front_vehicle_stopped: "앞차 정차",
    ego_turn_direction: "내 차량 진행 방향",
    intersection: "교차로 여부",
    sudden_brake: "급정거 여부",
    opponent_behavior: "상대 차량 행동",
    lane_change_actor: "차선변경 주체",
    turn_signal: "방향지시등 사용",
    user_signal: "내 차량 신호",
    opponent_signal_visible: "상대 신호 보임 여부",
    opponent_signal: "상대 차량 신호",
    signal_transition: "신호 변경 흐름",
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
    non_contact_trigger: "비접촉 유발 요인",
    trigger_actor_type: "사고 유발 대상",
    trigger_actor_behavior: "유발 대상 행동",
    direct_collision_partner_type: "실제 충돌 상대",
    rear_vehicle_collision: "후방 차량 추돌",
    stopped_vehicle_without_lights: "등화 없는 정차 차량",
    highway_or_expressway: "고속도로/자동차전용도로",
    visual_evidence_limited: "영상 근거 제한",
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
      collision_point_visible: ["충돌 지점 보임", "충돌 지점 불명확"],
      front_vehicle_stopped: ["앞차가 정차함", "앞차 정차 아님"],
      intersection: ["교차로", "교차로 아님"],
      sudden_brake: ["급정거함", "급정거 아님"],
      opponent_signal_violation: ["신호위반 있음", "신호위반 없음"],
      opponent_signal_visible: ["상대 신호 보임", "상대 신호 보이지 않음"],
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
      non_contact_trigger: ["비접촉 유발 요인 있음", "비접촉 유발 요인 없음"],
      rear_vehicle_collision: ["후방 차량 추돌 있음", "후방 차량 추돌 없음"],
      stopped_vehicle_without_lights: ["등화 없는 정차 차량", "등화/표시 확인"],
      highway_or_expressway: ["고속도로/자동차전용도로", "일반도로"],
      visual_evidence_limited: ["직접 반영할 영상 사실 부족", "영상 근거 충분"],
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
    straight: "직진",
    u_turn: "유턴",
    vehicle: "차량",
    pedestrian: "보행자",
    bicycle: "자전거",
    motorcycle: "이륜차",
    object: "물체/시설물",
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
    green_to_yellow: "녹색에서 황색",
    yellow_to_red: "황색에서 적색",
    red_to_green: "적색에서 녹색",
    green_to_red: "녹색에서 적색",
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

function collectConditionalContext(result: AnyRecord = {}, report: AnyRecord = {}) {
  const contract = result.video_input_contract ?? result.model_info?.video_input_contract ?? {};
  const arbitration = result.fact_arbitration ?? result.model_info?.fact_arbitration ?? {};
  const confirmationGroups = asArray(contract.confirmation_groups);
  const qualitySummary = contract.observation_quality_summary ?? {};
  const fieldSources = [
    ...asArray(result.required_input_questions ?? result.input_requirements?.questions),
    ...asArray(result.missing_info?.questions),
    ...asArray(report.missing_info?.questions),
    ...asArray(contract.uncertain_observations),
    ...asArray(contract.accepted_observations),
    ...asArray(contract.supporting_observations),
    ...asArray(contract.confirmation_candidates),
    ...asArray(qualitySummary.high_priority_uncertain_fields).map((field) => ({ field })),
    ...confirmationGroups.flatMap((group: AnyRecord) => asArray(group.fields).map((field) => ({ field }))),
    ...asArray(arbitration.conflicts),
    ...asArray(arbitration.pending_video_confirmations),
    ...asArray(arbitration.requires_confirmation),
  ];
  const fields = new Set(
    [
      ...fieldSources.map((item: AnyRecord) => String(item?.field ?? "")),
      ...asArray(arbitration.confirmation_fields).map((field) => String(field)),
      ...asArray(arbitration.held_video_fields).map((field) => String(field)),
    ].filter(Boolean)
  );
  const facts = result.structured_facts ?? {};
  const text = [
    result.scenario_type,
    facts.accident_party_type,
    facts.accident_type,
    facts.collision_partner_type,
    facts.direct_collision_partner_type,
    facts.primary_collision_target,
    facts.intersection,
    facts.ego_turn_direction,
    facts.signal_state,
    facts.user_signal,
    facts.opponent_signal,
    facts.signal_transition,
    facts.opponent_signal_visible,
    facts.opponent_signal_violation,
    facts.opponent_behavior,
    facts.centerline_crossed,
    facts.centerline_cross_reason,
    facts.road_obstruction,
    facts.illegal_parking_obstruction,
    facts.opposing_vehicle_present,
    facts.opposing_vehicle_did_not_stop,
    facts.front_vehicle_stopped,
    facts.rear_vehicle_collision,
    facts.non_contact_trigger,
    facts.trigger_actor_type,
    facts.trigger_actor_behavior,
    facts.secondary_collision,
    facts.stopped_vehicle_without_lights,
    result.accident_summary,
    report.headline,
    report.summary,
    report.summary_for_user?.short_summary,
    report.missing_info,
  ].map((value) => String(value ?? "")).join(" ");
  return { facts, fields, text };
}

function hasConditionalField(fields: Set<string>, names: string[]) {
  return names.some((field) => fields.has(field));
}

function isUnknownValue(value: any) {
  if (value === undefined || value === null || value === "") return true;
  return ["unknown", "unclear", "확인 필요", "미확인", "모름"].includes(String(value).toLowerCase());
}

type ConditionalBranchKey = "provided_conditions" | "signal" | "non_contact" | "centerline" | "rear_stop" | "collision_target";

function conditionalBranch(key: ConditionalBranchKey, label: string, reason: string, fields: string[] = []) {
  return { key, label, reason, fields };
}

function withConditionalBranchMetadata(card: AnyRecord, selectedKey: ConditionalBranchKey, branches: AnyRecord[]) {
  const uniqueBranches = branches.filter(
    (branch, index, items) => branch?.key && items.findIndex((item) => item.key === branch.key) === index
  );
  return {
    ...card,
    branch_key: selectedKey,
    detected_branch_keys: uniqueBranches.map((branch) => branch.key),
    secondary_branches: uniqueBranches
      .filter((branch) => branch.key !== selectedKey)
      .map((branch) => ({
        key: branch.key,
        label: branch.label,
        reason: branch.reason,
        fields: branch.fields,
      })),
    coverage: {
      expected_branch_keys: ["signal", "non_contact", "centerline", "rear_stop", "collision_target"],
      detected_count: uniqueBranches.length,
      detected_ratio: Math.min(1, uniqueBranches.length / 5),
      selected_branch_key: selectedKey,
    },
  };
}

function conditionalCardFromOutcomeItems(items: AnyRecord[], title: string, summary: string, neededEvidence: string[], notice: string) {
  return {
    title,
    summary,
    cases: items.slice(0, 3).map((item: AnyRecord) => ({
      label: cleanText(item.label, "조건별 판단"),
      likely_direction: `${cleanText(item.my_range, "확인 필요")} / ${cleanText(item.other_range, "확인 필요")} 참고`,
      explanation: cleanText(item.explanation, "이 조건이 확인되면 과실 방향이 달라질 수 있습니다."),
      check_points: asArray(item.basis).map((x) => cleanText(x, "")).filter(Boolean).slice(0, 5),
    })),
    needed_evidence: neededEvidence,
    notice,
  };
}

function signalConditionalOutcomeCard() {
  return {
    title: "신호 확인에 따라 달라지는 판단",
    summary: "상대 차량 신호나 진입 시점이 확인되지 않으면 한 가지 과실비율로 단정하기 어렵습니다. 아래 경우를 나눠 확인해야 합니다.",
    cases: [
      {
        label: "상대 차량 신호가 정상 진행 신호였다면",
        likely_direction: "내 차량의 책임 비율이 더 높아질 수 있습니다.",
        explanation: "내 차량이 황색 또는 적색 전환 구간에 교차로에 진입했고 상대 차량은 정상 신호에 직진한 것으로 확인되면, 신호 준수와 정지선 통과 시점이 내 차량에게 불리한 핵심 근거가 됩니다.",
        check_points: ["내 차량 정지선 통과 시점", "내 차량 진입 당시 신호", "황색 전환 시점", "충돌 직전 신호 색상"],
      },
      {
        label: "상대 차량도 적색 또는 신호위반이었다면",
        likely_direction: "상대 차량의 책임 비율이 더 높아질 수 있습니다.",
        explanation: "상대 차량이 적색 또는 진입 금지 신호에 들어온 사실이 확인되면, 상대 차량의 신호위반과 전방주시 의무 위반이 더 큰 과실 근거가 됩니다.",
        check_points: ["상대 차량 진입 당시 신호", "CCTV 또는 신호체계 자료", "상대 차량 정지선 통과 시점", "상대 차량 진입 속도와 좌우 확인 가능성"],
      },
    ],
    needed_evidence: ["교차로 CCTV", "신호 주기표 또는 신호체계 자료", "각 차량의 정지선 통과 시점", "블랙박스 원본 전체 구간"],
    notice: "위 분기는 특정 영상에 맞춘 결론이 아니라, 신호가 보이지 않는 교차로 사고에서 공통으로 확인해야 하는 판단 구조입니다.",
  };
}

function collisionTargetConditionalOutcomeCard() {
  return {
    title: "사고 대상 확인에 따라 달라지는 판단",
    summary: "영상에 보행자나 자전거가 보이더라도 실제 충돌 대상인지, 단순 주변 환경인지가 확인되어야 사고 유형과 적용 근거가 달라집니다.",
    cases: [
      {
        label: "차량끼리 직접 충돌한 사고라면",
        likely_direction: "차대차 기준의 신호, 진로, 안전거리, 회피 가능성을 중심으로 봅니다.",
        explanation: "사람이나 횡단보도가 화면에 보여도 실제 충돌 상대가 차량이면 보행자 사고 기준을 우선 적용하지 않습니다. 직접 충돌 대상과 충돌 지점이 근거 선택의 출발점입니다.",
        check_points: ["실제 접촉한 대상", "충돌 지점", "각 차량 진행 방향", "보행자 또는 자전거가 충돌에 직접 관여했는지"],
      },
      {
        label: "보행자·자전거·물체가 직접 사고 대상이라면",
        likely_direction: "보호의무, 비접촉 유발, 도로 장애물 기준을 별도로 검토해야 합니다.",
        explanation: "차량이 아닌 대상이 직접 충돌 대상이거나 사고를 유발한 주체라면 차대차 과실표만으로 결론을 내리면 안 됩니다. 직접 접촉 여부와 비접촉 유발 여부를 나눠야 합니다.",
        check_points: ["직접 접촉 여부", "비접촉 유발 대상", "보행자 신호 또는 자전거 진행 방향", "회피 가능성"],
      },
    ],
    needed_evidence: ["충돌 직전·직후 원본 영상", "접촉 부위 사진", "현장 사진", "블랙박스 전후방 영상"],
    notice: "주변에 보이는 객체를 사고 대상으로 단정하지 않고, 실제 충돌 또는 유발 관계가 확인될 때만 해당 기준을 적용합니다.",
  };
}

function centerlineConditionalOutcomeCard() {
  return {
    title: "중앙선 침범 사유에 따라 달라지는 판단",
    summary: "중앙선을 넘은 사실만으로 끝나지 않고, 장애물 회피 필요성·정차 여부·마주오던 차량의 회피 가능성을 함께 나눠 봐야 합니다.",
    cases: [
      {
        label: "장애물 회피 때문에 일시적으로 중앙선을 넘었다면",
        likely_direction: "내 차량 책임이 줄어들 수 있지만, 반대 차로 안전 확인 의무는 남습니다.",
        explanation: "불법 주정차나 도로 장애물 때문에 불가피하게 중앙선을 물었다면 침범 사유가 중요한 완화 근거가 됩니다. 다만 마주오던 차량을 확인하고 정지했는지, 충분한 공간을 확보했는지는 별도로 검토합니다.",
        check_points: ["도로 장애물 또는 불법 주정차 존재", "내 차량 정차 여부", "반대 차로 시야", "마주오던 차량의 감속·회피 가능성"],
      },
      {
        label: "회피 필요성이 부족하거나 무리하게 넘어갔다면",
        likely_direction: "내 차량의 책임 비율이 더 높아질 수 있습니다.",
        explanation: "장애물이 없거나 충분히 기다릴 수 있었는데 중앙선을 넘어 진행했다면 차로 유지 의무 위반이 핵심 근거가 됩니다. 상대 차량의 중앙선 침범 여부와 회피 가능성은 별도로 비교해야 합니다.",
        check_points: ["중앙선 침범 시작 시점", "대기 가능성", "상대 차량의 차로 점유", "양 차량의 정지 또는 감속 여부"],
      },
    ],
    needed_evidence: ["원본 영상 전체 구간", "도로 폭과 차선 사진", "불법 주정차 또는 장애물 사진", "상대 차량 진행 방향 영상"],
    notice: "중앙선 관련 분기는 모든 중앙선 사고에 공통으로 필요한 확인 구조이며, 특정 테스트 케이스에 맞춘 결론이 아닙니다.",
  };
}

function nonContactConditionalOutcomeCard() {
  return {
    title: "비접촉 유발 여부에 따라 달라지는 판단",
    summary: "직접 부딪힌 대상과 사고를 유발한 대상이 다를 수 있으면, 실제 충돌 책임과 비접촉 유발 책임을 나눠 확인해야 합니다.",
    cases: [
      {
        label: "제3의 차량·자전거·보행자가 사고를 유발했다면",
        likely_direction: "직접 충돌 차량만이 아니라 유발 주체의 책임을 함께 검토해야 합니다.",
        explanation: "차량이 직접 부딪히지 않았더라도 갑작스러운 진입, 역주행, 무리한 횡단처럼 사고를 만든 움직임이 확인되면 비접촉 유발 책임이 별도로 문제될 수 있습니다.",
        check_points: ["유발 주체", "유발 주체의 움직임", "회피 가능 시간", "직접 충돌 차량의 안전거리"],
      },
      {
        label: "비접촉 유발이 확인되지 않고 단순 후방추돌이라면",
        likely_direction: "후행 차량의 안전거리·전방주시 의무가 중심이 됩니다.",
        explanation: "외부 유발 요인이 확인되지 않으면 실제로 부딪힌 차량들 사이의 거리, 정차 이유, 급제동 필요성을 중심으로 과실을 봅니다.",
        check_points: ["충돌 직전 5~10초 영상", "앞차 정차 사유", "뒤차 제동 여부", "주변 차량 또는 자전거 움직임"],
      },
    ],
    needed_evidence: ["충돌 전 전체 구간 영상", "비접촉 유발 주체가 보이는 프레임", "직접 충돌 지점", "목격자 또는 주변 CCTV"],
    notice: "비접촉 유발 분기는 특정 사고에 맞춘 결론이 아니라, 직접 충돌 대상과 사고 원인이 분리될 수 있는 사고에서 공통으로 확인해야 하는 구조입니다.",
  };
}

function rearStopConditionalOutcomeCard() {
  return {
    title: "정차·급정거 사유에 따라 달라지는 판단",
    summary: "후방 추돌처럼 보이는 사고도 앞차 정차 사유, 급정거 필요성, 비접촉 유발 대상에 따라 책임 방향이 달라질 수 있습니다.",
    cases: [
      {
        label: "앞차 정차나 급정거에 정당한 이유가 있었다면",
        likely_direction: "뒤차의 안전거리 미확보 책임이 중심이 될 수 있습니다.",
        explanation: "횡단보도, 신호, 전방 장애물, 자전거 등 때문에 앞차가 멈춘 상황이면 뒤차가 앞차 움직임을 예상하고 안전거리를 유지했는지가 핵심입니다.",
        check_points: ["앞차 정차 사유", "전방 장애물 또는 신호", "뒤차와의 거리", "정차 후 충돌까지 시간"],
      },
      {
        label: "이유 없는 급정거 또는 차로변경 직후 정차라면",
        likely_direction: "앞차 또는 유발 차량의 책임이 일부 커질 수 있습니다.",
        explanation: "앞차가 갑자기 끼어든 직후 급정거했거나 정차 사유가 부족하면 단순 후방 추돌과 달리 앞차 행위도 과실 판단에 들어갑니다.",
        check_points: ["차로변경 직후 여부", "정차 이유", "비접촉 유발 대상", "뒤차 회피 가능 시간"],
      },
    ],
    needed_evidence: ["충돌 전 최소 5~10초 영상", "전방 차량 정차 사유", "후방 영상", "현장 신호와 횡단보도 상태"],
    notice: "후방 추돌 분기는 안전거리 원칙과 앞차 정차 사유를 함께 확인하기 위한 공통 판단 구조입니다.",
  };
}

function composeConditionalOutcomeCard(result: AnyRecord = {}, report: AnyRecord = {}) {
  const { facts, fields: questionFields, text } = collectConditionalContext(result, report);
  const signalRelevant =
    result.scenario_type === "intersection_signal_violation" ||
    facts.intersection === true ||
    Boolean(facts.user_signal) ||
    Boolean(facts.signal_transition) ||
    facts.opponent_signal_visible === false ||
    /교차로|신호|황색|적색|녹색|intersection|signal/i.test(text) ||
    hasConditionalField(questionFields, ["user_signal", "opponent_signal", "opponent_signal_visible", "signal_transition", "opponent_signal_violation"]);
  const opponentSignalUnclear =
    facts.opponent_signal_visible === false ||
    isUnknownValue(facts.opponent_signal) ||
    hasConditionalField(questionFields, ["opponent_signal", "opponent_signal_visible"]);
  const collisionTargetAmbiguous = hasConditionalField(questionFields, [
    "collision_partner_type",
    "direct_collision_partner_type",
    "primary_collision_target",
  ]);
  const nonContactAmbiguous =
    hasConditionalField(questionFields, ["non_contact_trigger", "trigger_actor_type", "trigger_actor_behavior"]) ||
    facts.non_contact_trigger === true ||
    /비접촉|유발|자전거|역주행|non.?contact|trigger/i.test(text);
  const centerlineAmbiguous =
    hasConditionalField(questionFields, [
      "centerline_cross_reason",
      "road_obstruction",
      "illegal_parking_obstruction",
      "opposing_vehicle_present",
      "opposing_vehicle_did_not_stop",
    ]) ||
    (facts.centerline_crossed === true && /중앙선|centerline|장애물|불법\s*주정차|대향|마주/i.test(text));
  const rearStopAmbiguous =
    hasConditionalField(questionFields, ["front_vehicle_stopped", "rear_vehicle_collision", "sudden_brake", "stopped"]) ||
    /후방\s*추돌|급정거|정차|뒤에서|rear.?end|rear_collision/i.test(text);
  const branches = [
    signalRelevant && opponentSignalUnclear
      ? conditionalBranch("signal", "신호 확인", "상대 신호 또는 진입 시점에 따라 책임 방향이 달라질 수 있습니다.", [
          "opponent_signal",
          "opponent_signal_visible",
          "signal_transition",
        ])
      : undefined,
    nonContactAmbiguous
      ? conditionalBranch("non_contact", "비접촉 유발", "직접 충돌 대상과 사고 유발 주체가 다를 수 있습니다.", [
          "non_contact_trigger",
          "trigger_actor_type",
          "trigger_actor_behavior",
        ])
      : undefined,
    centerlineAmbiguous
      ? conditionalBranch("centerline", "중앙선 침범 사유", "중앙선 침범이 불가피한 회피였는지 무리한 진행이었는지에 따라 달라집니다.", [
          "centerline_cross_reason",
          "road_obstruction",
          "illegal_parking_obstruction",
        ])
      : undefined,
    rearStopAmbiguous
      ? conditionalBranch("rear_stop", "정차·후방추돌 사유", "앞차 정차 사유와 뒤차 안전거리 유지 여부를 함께 확인해야 합니다.", [
          "front_vehicle_stopped",
          "rear_vehicle_collision",
          "sudden_brake",
        ])
      : undefined,
    collisionTargetAmbiguous
      ? conditionalBranch("collision_target", "사고 대상 확인", "화면에 보인 객체와 실제 충돌 대상이 다를 수 있습니다.", [
          "collision_partner_type",
          "direct_collision_partner_type",
          "primary_collision_target",
        ])
      : undefined,
  ].filter(Boolean) as AnyRecord[];
  const conditionalOutcomes = asArray(result.fault_ratio?.conditional_outcomes);
  if (conditionalOutcomes.length) {
    const selectedKey = (branches[0]?.key ?? "provided_conditions") as ConditionalBranchKey;
    const sourceBranches = branches.length
      ? branches
      : [conditionalBranch("provided_conditions", "제공된 조건별 결과", "Agent가 제공한 조건별 과실 방향을 그대로 표시합니다.")];
    return withConditionalBranchMetadata(conditionalCardFromOutcomeItems(
      conditionalOutcomes,
      signalRelevant ? "신호 확인에 따라 달라지는 판단" : "조건 확인에 따라 달라지는 판단",
      "확인되지 않은 핵심 사실에 따라 과실 방향이 달라질 수 있어 조건별로 나눠 봐야 합니다.",
      signalRelevant
        ? ["교차로 CCTV", "신호 주기표 또는 신호체계 자료", "각 차량의 정지선 통과 시점", "블랙박스 원본 전체 구간"]
        : ["블랙박스 원본 전체 구간", "현장 사진", "상대 차량 진술", "보험사 사고 조사 자료"],
      "조건부 결과는 특정 테스트 영상에 맞춘 답이 아니라, 확인되지 않은 핵심 사실이 있는 사고에서 공통으로 적용하는 판단 구조입니다."
    ), selectedKey, sourceBranches);
  }
  if (!branches.length) return undefined;
  const selectedKey = branches[0].key as ConditionalBranchKey;
  if (selectedKey === "signal") return withConditionalBranchMetadata(signalConditionalOutcomeCard(), selectedKey, branches);
  if (selectedKey === "non_contact") return withConditionalBranchMetadata(nonContactConditionalOutcomeCard(), selectedKey, branches);
  if (selectedKey === "centerline") return withConditionalBranchMetadata(centerlineConditionalOutcomeCard(), selectedKey, branches);
  if (selectedKey === "rear_stop") return withConditionalBranchMetadata(rearStopConditionalOutcomeCard(), selectedKey, branches);
  if (selectedKey === "collision_target") {
    return withConditionalBranchMetadata(collisionTargetConditionalOutcomeCard(), selectedKey, branches);
  }
  return undefined;
}

export function enrichEasyReport(report: AnyRecord = {}, result: AnyRecord = {}): AnyRecord {
    const card = composeEvidenceReliabilityCard(result);
    const processCard = composeAgentProcessCard(result);
    const videoFactCard = composeVideoFactExplanationCard(result);
    const expertGuidanceCard = composeExpertGuidanceCard(result);
    const kniaAdjustmentCards = composeKniaAdjustmentCards(result);
    const videoQuestions = combineVideoQuestions(
        composeVideoConflictQuestions(result),
        composeVideoQualityQuestions(result),
    );

    const mergedReport: AnyRecord = prioritizeMissingInfo(mergeVideoQuestions(report, videoQuestions));
    const conditionalOutcomeCard = composeConditionalOutcomeCard(result, mergedReport);
    const reportWithConditionalOutcome: AnyRecord = conditionalOutcomeCard
        ? prioritizeMissingInfo({ ...mergedReport, conditional_outcome_card: conditionalOutcomeCard })
        : mergedReport;

    const kniaLinkCards: AnyRecord = composeKniaLinkCards(result, reportWithConditionalOutcome);
    const reportWithoutDuplicateKniaVideo: AnyRecord = removeDuplicateKniaRelatedVideo(
        reportWithConditionalOutcome,
        kniaLinkCards.related_knia_video_card,
    );

    const enrichedReport: AnyRecord = {
        ...reportWithoutDuplicateKniaVideo,
        ...kniaLinkCards,
        ...(card ? { evidence_reliability_card: card } : {}),
        ...(processCard ? { agent_process_card: processCard } : {}),
        ...(videoFactCard ? { video_fact_explanation_card: videoFactCard } : {}),
        ...(expertGuidanceCard ? { expert_guidance_card: expertGuidanceCard } : {}),
        ...kniaAdjustmentCards,
        ...(conditionalOutcomeCard ? { conditional_outcome_card: conditionalOutcomeCard } : {}),
        ...(result.guided_questionnaire ? { guided_questionnaire: sanitizeGuidedQuestionnaire(result.guided_questionnaire) } : {}),
    };

    const displayMode = normalizeAnalysisMode(
        result.analysis_mode ??
        result.display_mode ??
        report.analysis_mode ??
        report.display_mode ??
        report.analysis_mode_contract?.mode,
    );
    const withMode = applyAnalysisModeContract(enrichedReport, { ...result, analysis_mode: displayMode });

    return {
        ...withMode,
        display_mode: displayMode,
        analysis_mode: displayMode,
        simple_report: composeSimpleReport(withMode, { ...result, analysis_mode: displayMode }),
    };
}

function composeSimpleReport(report: AnyRecord = {}, result: AnyRecord = {}): AnyRecord {
    const faultRatio: AnyRecord = report.fault_ratio || report.fault_explanation || result.fault_ratio || {};
    const userFault: AnyRecord = faultRatio.user_fault || faultRatio.final_fault || {};
    const kniaCandidates = collectSimpleKniaCandidates(report, result);
    const knia: AnyRecord | null = kniaCandidates[0] ?? null;
    const videoSummary = cleanText(
        report.video_summary ||
        result.video_summary ||
        result.video_context_summary ||
        result.video_observation_summary ||
        "",
        "",
    );
    const keyFactors = asArray(faultRatio.key_factors ?? faultRatio.applied_adjustments)
        .map((item) => cleanText(isPlainObject(item) ? item.label ?? item.reason : item, ""))
        .filter(Boolean)
        .slice(0, 4);

    return {
        situation_summary: composeSimpleSituationSummary(report, result),
        fault_ratio: {
            my: faultRatio.my ?? faultRatio.my_percent ?? faultRatio.my_fault ?? userFault.my ?? null,
            other: faultRatio.other ?? faultRatio.other_percent ?? faultRatio.opponent_fault ?? userFault.other ?? null,
            range: faultRatio.fault_range ?? faultRatio.range ?? null,
            basis: cleanText(
                faultRatio.basis || faultRatio.summary || faultRatio.simple_summary || "",
                "입력한 사고 사실과 KNIA 기준을 함께 검토한 참고용 산정입니다.",
            ),
            key_factors: keyFactors,
            reference_only:
                faultRatio.reference_only === true ||
                result.presentation_status === "reference_only" ||
                result.judgment_status === "needs_review",
        },
        knia_video_evidence: knia,
        knia_and_video: {
            primary: knia,
            candidates: kniaCandidates.slice(0, 3),
            source_notice: "영상 파일은 LawCompass 서버에 저장하지 않고, 과실비율정보포털 원본 링크로만 제공합니다.",
        },
        video_summary: videoSummary,
    };
}

function composeSimpleSituationSummary(report: AnyRecord = {}, result: AnyRecord = {}): string {
    const candidates = [
        report.simple_report?.situation_summary,
        report.current_situation_summary,
        report.situation_summary,
        report.one_line_summary,
        report.summary,
        result.accident_summary,
        result.description_text,
        report.structured_facts?.description_text,
    ];
    for (const candidate of candidates) {
        const summary = cleanSituationSummary(candidate);
        if (summary) return summary;
    }
    return "입력한 사고 설명과 영상 자료를 바탕으로 사고 상황을 정리했습니다.";
}

function cleanSituationSummary(value: any): string {
    let text = cleanText(value, "");
    if (!text) return "";

    const legalTails = [
        "입력된 사고 사실과 검색된 교통법규 근거를 기준으로 적용 가능 법규를 검토했습니다.",
        "입력한 사고 사실과 검색된 교통법규 근거를 기준으로 적용 가능 법규를 검토했습니다.",
        "검색된 교통법규 근거를 기준으로 적용 가능 법규를 검토했습니다.",
        "교통법규 근거를 바탕으로 과실, 신고 필요 여부, 보험 대응을 검토했습니다.",
    ];
    for (const tail of legalTails) text = text.replace(tail, "").trim();

    const mixed = text.match(/^(.+?\s*사고)\s*상황은\s*[^,.。]*로 보이며(?:,|\s|$)/);
    if (mixed?.[1]) return `${mixed[1].trim()} 상황입니다.`;

    const legalStart = text.search(/(?:교통법규|적용 가능 법규|보험 대응|신고 필요 여부|검색된 교통법규)/);
    if (legalStart > 0) text = text.slice(0, legalStart);

    text = text
        .replace(/\s*,\s*$/, "")
        .replace(/\s*이며\s*$/, "입니다.")
        .trim();

    if (!text) return "";
    if (!/[.!?。]$/.test(text)) text = `${text}.`;
    return text;
}

function collectSimpleKniaCandidates(report: AnyRecord = {}, result: AnyRecord = {}): AnyRecord[] {
    const requestedParty = partyCode(
        result.knia_major_party_type ??
        result.accident_party_type ??
        report.knia_major_party_type ??
        report.accident_party_type ??
        result.scenario?.accident_party_type ??
        result.normalized?.structured_facts?.knia_major_party_type,
    );
    const rawCandidates = [
        report.related_knia_video_card,
        report.related_video,
        report.simple_report?.knia_and_video?.primary,
        report.simple_report?.knia_video_evidence,
        report.knia_match_summary,
        result.knia_match_summary,
        result.knia_primary_match,
        result.knia_reference,
        asArray(report.knia_basis_cards)[0],
        asArray(result.knia_basis_cards)[0],
        asArray(result.knia_matches)[0],
        report.related_fault_standard,
        result.related_fault_standard,
        asArray(result.elderly_friendly_report?.knia_basis_cards)[0],
        result.fault_ratio?.knia_match,
        result.fault_ratio?.knia_reference_fault?.source_chart,
        result.fault_ratio?.knia_reference_fault,
    ];

    const output: AnyRecord[] = [];
    const byKey = new Map<string, AnyRecord>();
    for (const candidate of rawCandidates
        .map(normalizeSimpleKniaCandidate)
        .filter((candidate): candidate is AnyRecord => Boolean(candidate))
        .filter((candidate) => isSimpleKniaCandidateAllowedForParty(candidate, requestedParty))) {
        const key = (candidate.chart_no || candidate.subchart_no)
            ? [candidate.chart_no, candidate.subchart_no].filter(Boolean).join("|").toLowerCase()
            : [candidate.button_url, candidate.source_url, candidate.title].filter(Boolean).join("|").toLowerCase();
        if (!key) continue;
        const existing = byKey.get(key);
        if (!existing) {
            byKey.set(key, candidate);
            output.push(candidate);
            continue;
        }
        for (const field of ["source_url", "button_url", "video_url", "button_label", "base_fault", "final_fault", "fault_range", "menu_path", "match_reason", "summary", "missing_source_notice"]) {
            if (!existing[field] || (Array.isArray(existing[field]) && !existing[field].length)) {
                existing[field] = candidate[field];
            }
        }
    }
    return output;
}

function normalizeSimpleKniaCandidate(candidate: any): AnyRecord | null {
    if (!isPlainObject(candidate)) return null;
    const chartNo = cleanText(candidate.chart_no ?? candidate.chartNo, "");
    const subchartNo = cleanText(candidate.subchart_no ?? candidate.subchartNo, "");
    const title = cleanText(candidate.chart_title ?? candidate.title ?? candidate.article_title, "");
    const sourceUrl = safeKniaUrl(candidate.button_url || candidate.source_url || candidate.source_detail_url || candidate.source_page_url || candidate.video_url);
    const hasCandidate = candidate.has_knia_candidate === true || Boolean(chartNo || subchartNo || title || sourceUrl);
    if (!hasCandidate) return null;

    const videoUrl = safeKniaUrl(candidate.video_url);
    const buttonUrl = safeKniaUrl(candidate.button_url || candidate.source_url || candidate.source_detail_url || candidate.source_page_url || candidate.video_url);
    const baseFault = candidate.base_fault ?? candidate.knia_reference_fault?.base_fault ?? null;
    const finalFault = candidate.final_fault ?? candidate.adjusted_fault ?? candidate.knia_reference_fault?.final_fault ?? null;
    const faultRange = candidate.fault_range ?? candidate.range ?? candidate.knia_reference_fault?.fault_range ?? null;

    return {
        chart_no: chartNo,
        subchart_no: subchartNo,
        title,
        major_party_type: cleanText(candidate.major_party_type ?? candidate.accident_party_type, ""),
        accident_party_type: cleanText(candidate.accident_party_type ?? candidate.major_party_type, ""),
        summary: cleanText(candidate.summary ?? candidate.description ?? candidate.accident_situation, ""),
        menu_path: asArray(candidate.menu_path).map((item) => cleanText(item, "")).filter(Boolean),
        source_url: sourceUrl,
        button_url: buttonUrl,
        video_url: videoUrl,
        button_label: videoUrl ? "KNIA 관련 영상 보기" : "KNIA 원문 기준 보기",
        source_url_is_fallback: candidate.source_url_is_fallback === true,
        match_reason: cleanText(candidate.match_reason || candidate.why_matched, ""),
        reference_only: candidate.reference_only === true || candidate.presentation_status === "reference_only",
        base_fault: baseFault,
        final_fault: finalFault,
        fault_range: faultRange,
        source_notice: cleanText(candidate.notice, "영상 파일은 LawCompass 서버에 저장하지 않고, 과실비율정보포털 원본 링크로만 제공합니다."),
        missing_source_notice: sourceUrl
            ? ""
            : cleanText(candidate.missing_source_notice, "상세 기준 수집 필요: KNIA 원문 링크는 아직 연결되지 않았습니다."),
        candidate_charts: asArray(candidate.candidate_charts).slice(0, 3),
        has_knia_candidate: true,
    };
}

function isSimpleKniaCandidateAllowedForParty(candidate: AnyRecord, requestedParty: string) {
    if (!requestedParty) return true;
    const party = partyCode(candidate.major_party_type || candidate.accident_party_type);
    if (party && party !== requestedParty) return false;
    const chartNo = String(candidate.chart_no || "");
    if (!chartNo) return true;
    if (requestedParty === "car_vs_person") return chartNo.startsWith("보");
    if (requestedParty === "car_vs_bicycle") return chartNo.startsWith("거") || chartNo.startsWith("자");
    if (requestedParty === "car_vs_car") return chartNo.startsWith("차");
    return true;
}

function sanitizeGuidedQuestionnaire(value: AnyRecord = {}) {
  return {
    version: cleanText(value.version, ""),
    analysis_mode: cleanText(value.analysis_mode, ""),
    question_count: toNumber(value.question_count, asArray(value.questions).length),
    auto_analysis_policy: {
      can_auto_start_when_required_answered: value.auto_analysis_policy?.can_auto_start_when_required_answered === true,
      user_controls: asArray(value.auto_analysis_policy?.user_controls).map((item) => cleanText(item, "")).filter(Boolean).slice(0, 3),
      batch_size_hint: toNumber(value.auto_analysis_policy?.batch_size_hint, 3),
    },
    questions: asArray(value.questions).map((item: AnyRecord) => ({
      question_id: cleanText(item.question_id, ""),
      title: cleanText(item.title, ""),
      plain_question: cleanText(item.plain_question ?? item.question, ""),
      why_it_matters: cleanText(item.why_it_matters ?? item.reason, ""),
      choices: asArray(item.choices).map((choice: AnyRecord) => ({
        value: cleanText(choice.value, ""),
        label: cleanText(choice.label, ""),
      })).filter((choice) => choice.label).slice(0, 6),
      default_choice: cleanText(item.default_choice, "unknown"),
      affects_fault_ratio: item.affects_fault_ratio === true,
      knia_factor_key: cleanText(item.knia_factor_key, ""),
      fact_key: cleanText(item.fact_key, ""),
    })).filter((item) => item.plain_question).slice(0, 12),
  };
}

function composeKniaAdjustmentCards(result: AnyRecord = {}) {
  const fault = result.fault_ratio ?? {};
  const baseFault = fault.base_fault ?? fault.knia_adjustment_registry?.base_fault;
  const finalFault = fault.final_fault ?? fault.knia_adjustment_registry?.final_fault ?? { my: fault.my, other: fault.other };
  const faultRange = fault.fault_range ?? fault.knia_adjustment_registry?.fault_range;
  const applied = asArray(fault.applied_adjustments ?? fault.knia_adjustment_registry?.applied_adjustments);
  const notApplied = asArray(fault.not_applied_adjustments ?? fault.knia_adjustment_registry?.not_applied_adjustments);
  const unknown = asArray(fault.unknown_adjustments ?? fault.knia_adjustment_registry?.unknown_adjustments);
  const conditional = asArray(fault.conditional_outcomes ?? fault.knia_adjustment_registry?.conditional_outcomes);
  const facts = result.normalized?.structured_facts ?? result.structured_facts ?? result.facts ?? {};
  const majorPartyType = partyCode(
    result.knia_major_party_type ??
    result.accident_party_type ??
    result.scenario?.accident_party_type ??
    facts.knia_major_party_type ??
    facts.accident_party_type,
  );
  const primaryCandidates = [
    result.knia_primary_match,
    ...asArray(result.knia_matches),
    fault.knia_reference_fault?.source_chart ?? fault.knia_reference_fault,
    fault.knia_fault_estimate?.source_chart ?? fault.knia_fault_estimate,
  ].filter((item) => item && typeof item === "object");
  const primary = primaryCandidates.find((item) => kniaCandidateAllowedForMajorParty(item, majorPartyType)) ?? primaryCandidates[0] ?? {};
  const hasAnyAdjustment = baseFault || finalFault || applied.length || notApplied.length || unknown.length || conditional.length;
  if (!hasAnyAdjustment) return {};
  const baseLabel = userFaultLabel(baseFault);
  const finalLabel = userFaultLabel(finalFault);
  const basicFaultCard = {
    title: "기본 과실",
    summary: finalLabel ? `현재 입력 기준 최종 과실은 ${finalLabel}입니다.` : "현재 입력 기준 과실을 참고 범위로 표시합니다.",
    chart_no: cleanText(primary.chart_no, ""),
    chart_title: cleanText(primary.title ?? primary.chart_title, ""),
    major_party_type: majorPartyType || undefined,
    major_party_label: majorPartyLabel(majorPartyType),
    classification_reason: majorPartyType === "car_vs_person"
      ? "입력에서 사람 또는 도로 작업자와의 직접 충돌이 확인되어 차대사람 사고로 분류했습니다."
      : undefined,
    source_url: safeHttpUrl(primary.source_url ?? primary.source_detail_url ?? primary.video_url),
    base_fault: baseFault ? safeFaultPair(baseFault) : undefined,
    final_fault: finalFault ? safeFaultPair(finalFault) : undefined,
    fault_range: faultRange ? safeFaultRange(faultRange) : undefined,
    notice: cleanText(fault.no_knia_match_reason, "") || "과실비율은 보험사, 분쟁심의위, 법원 판단에 따라 달라질 수 있습니다.",
  };
  return {
    knia_basic_fault_card: basicFaultCard,
    ...(applied.length ? { knia_applied_adjustment_card: adjustmentListCard("적용된 가감요소", applied, "적용된 항목과 적용 전후 과실을 정리했습니다.") } : {}),
    ...(notApplied.length ? { knia_not_applied_adjustment_card: adjustmentListCard("적용하지 않은 가감요소", notApplied, "답변상 적용하지 않은 항목과 이유입니다.") } : {}),
    ...(unknown.length ? { knia_unknown_adjustment_card: adjustmentListCard("모름/불확실 항목", unknown, "확인되면 과실 범위가 달라질 수 있는 항목입니다.") } : {}),
    ...(conditional.length ? { knia_conditional_outcome_card: conditionalOutcomeListCard(conditional) } : {}),
  };
}

function adjustmentListCard(title: string, items: AnyRecord[], summary: string) {
  return {
    title,
    summary,
    items: items.map((item) => ({
      label: cleanText(item.label, "가감요소"),
      before_fault: item.before_fault ? userFaultLabel(item.before_fault) : undefined,
      after_fault: item.after_fault ? userFaultLabel(item.after_fault) : undefined,
      delta: item.delta_my !== undefined ? `내 과실 ${Number(item.delta_my) > 0 ? "+" : ""}${toNumber(item.delta_my, 0)}%p` : cleanText(item.possible_delta_my, ""),
      reason: cleanText(item.reason, "입력 답변과 KNIA 수정요소 기준에 따라 판단했습니다."),
      source_label: cleanText(item.source, "KNIA 수정요소"),
    })).filter((item) => item.label).slice(0, 8),
  };
}

function conditionalOutcomeListCard(items: AnyRecord[]) {
  return {
    title: "조건별 결과",
    summary: "확인 결과에 따라 달라질 수 있는 과실 범위를 접힘 카드로 표시할 수 있게 정리했습니다.",
    items: items.map((item) => ({
      label: cleanText(item.label, "조건별 결과"),
      my_range: cleanText(item.my_range, ""),
      other_range: cleanText(item.other_range, ""),
      explanation: cleanText(item.explanation, ""),
    })).filter((item) => item.label).slice(0, 8),
  };
}

function majorPartyLabel(value: string) {
  const labels: Record<string, string> = {
    car_vs_car: "차대차 사고",
    car_vs_person: "차대사람 사고",
    car_vs_bicycle: "차대자전거 사고",
    car_vs_motorcycle: "차대오토바이 사고",
    car_vs_object: "차대기물 사고",
    single_vehicle: "차량단독 사고",
  };
  return labels[value] || undefined;
}

function partyCode(value: any) {
  const text = String(value ?? "").trim().toLowerCase();
  const allowed = new Set(["car_vs_car", "car_vs_person", "car_vs_bicycle", "car_vs_motorcycle", "car_vs_object", "single_vehicle"]);
  return allowed.has(text) ? text : "";
}

function kniaCandidateAllowedForMajorParty(item: AnyRecord = {}, party: string) {
  if (!party) return true;
  const itemParty = partyCode(item.major_party_type ?? item.accident_party_type);
  if (itemParty && itemParty !== party) return false;
  const chart = cleanText(item.chart_no, "");
  if (!chart) return true;
  if (party === "car_vs_person") return chart.startsWith("보") || chart.startsWith("蹂");
  if (party === "car_vs_car") return chart.startsWith("차") || chart.startsWith("李");
  if (party === "car_vs_bicycle") return chart.startsWith("거") || chart.startsWith("자") || chart.startsWith("嫄");
  if (party === "car_vs_object" || party === "single_vehicle") {
    return !(chart.startsWith("보") || chart.startsWith("蹂") || chart.startsWith("거") || chart.startsWith("자") || chart.startsWith("嫄"));
  }
  return true;
}

function safeFaultPair(value: AnyRecord = {}) {
  if (value.my === undefined || value.other === undefined) return undefined;
  const my = toNumber(value.my);
  const other = toNumber(value.other);
  if (!Number.isFinite(my) || !Number.isFinite(other)) return undefined;
  return { my: Math.round(my), other: Math.round(other) };
}

function safeFaultRange(value: AnyRecord = {}) {
  return {
    my: cleanText(value.my, ""),
    other: cleanText(value.other, ""),
  };
}

function userFaultLabel(value: AnyRecord = {}) {
  if (value.my === undefined || value.other === undefined) return "";
  const my = toNumber(value.my);
  const other = toNumber(value.other);
  if (!Number.isFinite(my) || !Number.isFinite(other)) return "";
  return `내 책임 ${Math.round(my)}% / 상대 ${Math.round(other)}%`;
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
  const displayEvidence = filterEvidenceForDisplay(evidence, facts, scenario);
  const requiredQuestions = requiredQuestionTexts(result);
  const missingQuestions = requiredQuestionsForReport(result);
  const fault = result.fault_ratio ?? {};
  const legal = result.legal_liability ?? {};
  const insurance = result.insurance_guide ?? {};
  const centerlineContext = isCenterlineObstacleContext(facts, result);
  const signalUncertaintyContext = isSignalUncertaintyContext(facts, result);
  const headline = centerlineContext
    ? "중앙선·도로 장애물 회피 중 대향 차량과 충돌한 사고로 보이며, 회피 사유와 상대 차량의 감속 가능성을 함께 봐야 합니다."
    : signalUncertaintyContext
      ? "교차로에서 좌회전 차량과 직진 차량이 충돌한 차대차 사고로 보이며, 상대 신호 확인 여부에 따라 과실 방향이 달라질 수 있습니다."
    : scenario === "rear_end_collision"
      ? "이번 사고는 정차 중 뒤차가 들이받은 사고로 보이며, 상대 차량 책임이 더 클 가능성이 높습니다."
      : scenario === "school_zone_child_accident"
        ? "어린이보호구역 사고로 보이며, 신고와 형사 문제를 꼭 확인해 보셔야 합니다."
        : "입력하신 사고 사실과 관련 근거를 바탕으로 과실과 신고 필요 여부를 검토했습니다.";
  const my = typeof fault.my === "number" ? Math.round(fault.my) : scenario === "rear_end_collision" ? 10 : 50;
  const other = typeof fault.other === "number" ? Math.round(fault.other) : 100 - my;
  const faultWhy = centerlineContext
    ? ["불법 주정차 또는 도로 장애물 때문에 중앙선을 넘은 사유", "마주오던 차량과의 충돌 구조", "내 차량의 정차 또는 감속 여부", "상대 차량의 전방주시·감속 가능성"]
    : signalUncertaintyContext
      ? ["내 차량이 교차로에 진입한 시점의 신호", "황색에서 적색으로 바뀐 정확한 시점", "상대 차량의 진행 신호가 보이지 않는 점", "좌회전 차량과 직진 차량의 충돌 구조"]
    : scenario === "rear_end_collision"
      ? ["내 차량이 정차 중이었다는 점", "상대 차량이 뒤에서 추돌했다는 점", "뒤차는 앞차와 안전거리를 유지해야 한다는 점"]
      : asArray(fault.key_factors).map((x) => cleanText(x)).slice(0, 4);
  const faultEasyExplanation = centerlineContext
    ? "주차 차량이나 도로 장애물 때문에 중앙선을 넘은 뒤 대향 차량과 충돌한 사고는 중앙선 침범 자체만이 아니라 회피 불가피성, 정차 위치, 상대 차량의 전방주시·감속 가능성을 함께 봅니다."
    : signalUncertaintyContext
      ? "황색에서 적색으로 바뀌는 교차로 진입 사고는 내 차량의 정지선 통과 시점과 상대 차량의 신호가 핵심입니다. 상대 신호가 정상 진행 신호였는지, 상대도 신호위반이었는지에 따라 과실 범위가 크게 달라질 수 있습니다."
    : scenario === "rear_end_collision"
      ? "정차 중 뒤에서 추돌당한 사고라면 일반적으로 뒤차의 책임이 더 크게 볼 수 있습니다."
      : "입력하신 사고 내용과 근거를 바탕으로 참고용 과실비율을 추정했습니다.";
  return enrichEasyReport(sanitizeEasyReport({
    headline,
    summary_for_user: { accident_type_label: scenarioLabel(scenario), short_summary: cleanText(result.accident_summary, "입력하신 사고 내용을 바탕으로 대응 방향을 정리했습니다."), confidence_label: Number(fault.confidence ?? 0) >= 0.65 ? "비교적 신뢰할 수 있음" : "보통", warning: "정확한 과실비율은 보험사나 분쟁심의 결과에 따라 달라질 수 있습니다." },
    top_actions: [
      { order: 1, title: "블랙박스 원본 보관", description: "영상 파일을 삭제하지 말고 따로 저장해 두세요.", importance: "매우 중요" },
      { order: 2, title: facts.injury ? "병원 진료 확인" : "사고 관련 자료 정리", description: facts.injury ? "통증이 있으면 병원 진료를 받고 진단서 또는 진료확인서를 받아두세요." : "차량 파손 사진, 사고 현장 사진, 수리 견적서를 모아두세요.", importance: "중요" },
      { order: 3, title: "보험사 사고 접수", description: "보험사에 사고를 접수하고 사고접수번호를 기록하세요.", importance: "중요" }
    ],
    fault_explanation: { title: "과실비율 참고 추정", my_label: "내 책임", other_label: "상대방 책임", my_percent: my, other_percent: other, easy_explanation: faultEasyExplanation, why: faultWhy, caution: centerlineContext ? "중앙선을 넘은 사유, 정차 위치, 상대 차량의 시야와 감속 가능성, 후속 추돌의 원인 분리에 따라 비율이 조정될 수 있습니다." : signalUncertaintyContext ? "상대 차량 신호, CCTV, 신호 주기표가 확인되면 조건별 과실 범위 중 어느 쪽에 가까운지 다시 좁혀야 합니다." : "급정거 여부, 충돌 직전 움직임, 도로 상황이 확인되면 비율이 조정될 수 있습니다." },
    insurance_explanation: { title: "보험 처리 안내", simple_summary: cleanText(insurance.summary, "대물 접수와 대인 접수 여부를 확인해야 합니다."), steps: asArray(insurance.steps).map((x) => cleanText(x)).slice(0, 6), documents: asArray(insurance.required_documents).map((x) => cleanText(x)).slice(0, 8) },
    legal_explanation: { title: "법률상 확인할 점", simple_summary: legal.reporting_required ? "신고나 형사 문제를 확인해 볼 필요가 있습니다." : "인명피해가 있거나 큰 위반이 의심되면 신고 여부를 확인해야 합니다.", risk_label: legal.criminal_risk_level === "high" ? "높음" : legal.criminal_risk_level === "low" ? "낮음" : "보통", checklist: asArray(legal.checklist).map((x) => cleanText(x)).slice(0, 7), caution: "형사책임 여부는 경찰이나 법원의 판단이 필요합니다." },
    legal_basis_cards: displayEvidence.slice(0, 6).map((ev: AnyRecord) => ({ law_name: cleanText(ev.law_name ?? "법률 근거"), easy_title: cleanText(ev.article_title ?? ev.chunk_summary ?? "교통사고 관련 확인 사항"), easy_explanation: cleanText(ev.plain_summary ?? ev.snippet, "이 사고에서 확인해야 할 법률상 기준입니다."), related_to_this_case: cleanText(ev.related_reason ?? ev.used_for, "이번 사고와 관련해 함께 검토할 수 있는 법률 근거입니다."), confidence_label: "근거용", source_label: cleanText(ev.source ?? "법률 근거") })),
    missing_info: { title: "더 정확한 분석을 위해 필요한 정보", items: Array.from(new Set([...requiredQuestions, ...(requiredQuestions.length ? [] : detectMissingFields(facts)), ...asArray(result.suggested_next_inputs).map((x) => cleanText(x)), ...asArray(result.followup_questions).map((x) => cleanText(x))])).slice(0, 6), questions: missingQuestions },
    detail_sections: { evidence_summaries: safeEvidenceSummaries(displayEvidence) }
  }), result);
}

function isCenterlineObstacleContext(facts: AnyRecord = {}, result: AnyRecord = {}) {
  const text = [
    facts.accident_type,
    facts.centerline_cross_reason,
    facts.opponent_behavior,
    result.accident_summary,
    result.scenario_type,
  ].map((value) => String(value ?? "")).join(" ");
  const centerline = facts.centerline_crossed === true || /중앙선|황색\s*실선|centerline/i.test(text);
  const obstruction = facts.road_obstruction === true || facts.illegal_parking_obstruction === true || /장애|주차|주정차|가구|사물|obstacle|parking/i.test(text);
  const oncoming = facts.opposing_vehicle_present === true || /마주오|대향|상대차|oncoming/i.test(text);
  return centerline && obstruction && oncoming;
}

function isSignalUncertaintyContext(facts: AnyRecord = {}, result: AnyRecord = {}) {
  const text = [
    facts.accident_type,
    facts.signal_state,
    facts.user_signal,
    facts.opponent_signal,
    facts.opponent_behavior,
    facts.signal_transition,
    result.accident_summary,
    result.scenario_type,
  ].map((value) => String(value ?? "")).join(" ");
  return (
    result.scenario_type === "intersection_signal_violation" &&
    (facts.opponent_signal_visible === false || !facts.opponent_signal || /상대.*신호|opponent.*signal|unknown|확인/i.test(text)) &&
    (facts.intersection === true || /교차로|intersection|좌회전|직진/i.test(text)) &&
    (/황색|노란불|적색|빨간불|yellow|red|signal_transition/i.test(text) || Boolean(facts.user_signal))
  );
}

function filterEvidenceForDisplay(evidence: any[] = [], facts: AnyRecord = {}, scenario: any = "") {
  const scenarioText = String(scenario ?? "");
  const vehicleContext =
    facts.accident_party_type === "car_vs_car" ||
    facts.collision_partner_type === "vehicle" ||
    facts.direct_collision_partner_type === "vehicle" ||
    /intersection_signal_violation|rear_end_collision|lane_change_collision|parking_or_stopped_vehicle_accident/.test(scenarioText);
  if (!vehicleContext) return evidence;
  return evidence.filter((ev: AnyRecord) => {
    const text = [
      ev.source_type,
      ev.title,
      ev.article_title,
      ev.law_name,
      ev.plain_summary,
      ev.related_reason,
      ev.used_for,
      ev.accident_party_type,
      ...(asArray(ev.scenario_tags)),
      ...(asArray(ev.display_tags)),
    ].map((value) => String(value ?? "").toLowerCase()).join(" ");
    const pedestrianTarget = /pedestrian_crosswalk_accident|school_zone_child_accident|보행자 사고|보행자 보호|pedestrian protection|child protection/.test(text);
    return !pedestrianTarget;
  });
}
export function composeClientReport(result: AnyRecord = {}, context: AnyRecord = {}) {
  return composeEasyFallback(result, context);
}
export function composeDebugReport(result: AnyRecord = {}, context: AnyRecord = {}) {
  return { technical: result, context };
}
