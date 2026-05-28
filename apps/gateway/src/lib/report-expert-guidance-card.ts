import { asArray, cleanText, safeHttpUrl, type AnyRecord } from "./report-composer-common.js";

export function composeExpertGuidanceCard(result: AnyRecord = {}) {
  const source = result.expert_guidance_sections ?? result.elderly_friendly_report?.expert_guidance_sections ?? {};
  if (!source || typeof source !== "object" || !Object.keys(source).length) return undefined;
  const legal = source.legal_prediction ?? {};
  const insurance = source.insurance_prediction ?? {};
  const missing = source.missing_facts ?? {};
  const legalPoints = [
    ...asArray(legal.civil_points).map((item) => cleanText(item, "")),
    ...asArray(legal.criminal_points).map((item) => cleanText(item, "")),
  ].filter(Boolean).slice(0, 6);
  const basis = augmentExpertBasisReasons(asArray(legal.basis ?? source.basis)
    .map((item: AnyRecord) => ({
      family_label: cleanText(item?.family_label, "참고 근거"),
      title: cleanText(item?.title, "교통사고 관련 근거"),
      reason: cleanText(item?.reason, "입력 사고와 연결해 참고할 수 있는 근거입니다."),
      source_quality: typeof item?.source_quality === "string" ? item.source_quality : "",
      source_quality_label: cleanText(item?.source_quality_label, "근거 출처 확인 필요"),
      source_review_note: cleanText(item?.source_review_note, ""),
      source_url: safeHttpUrl(item?.source_url),
      needs_original_source_review: item?.needs_original_source_review === true,
    }))
    .filter((item) => item.title)
    .slice(0, 4), legalPoints);
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
    source_summary: expertBasisSourceSummary(basis),
    missing_items: missingItems,
    notice: cleanText(source.notice, "확정 판단이 아닌 참고용 예상입니다."),
  };
}

function expertBasisSourceSummary(basis: AnyRecord[]) {
  if (!basis.length) return "";
  const originalCount = basis.filter((item) => item.source_quality === "collected_original").length;
  const staticCount = basis.filter((item) => item.source_quality === "static_support").length;
  const reviewCount = basis.filter((item) => item.needs_original_source_review).length;
  if (originalCount && !staticCount && !reviewCount) {
    return "원문 링크가 있는 근거를 우선 표시했습니다.";
  }
  if (originalCount && (staticCount || reviewCount)) {
    return "원문 근거와 보조 기준이 함께 표시됩니다. 보조 기준은 원문 대조가 필요합니다.";
  }
  if (staticCount || reviewCount) {
    return "일부 근거는 보조 기준입니다. 실제 적용 전 원문 대조가 필요합니다.";
  }
  return "사고 유형과 관련된 참고 근거를 표시했습니다.";
}

function augmentExpertBasisReasons<T extends { title: string; reason: string }>(basis: T[], legalPoints: string[]): T[] {
  const context = legalPoints.join(" ").toLowerCase();
  const additions: string[] = [];
  if (hasAny(context, ["자전거", "bicycle"]) && hasAny(context, ["비접촉", "유발", "후방", "시간", "안전거리"])) {
    additions.push("자전거의 비접촉 유발 여부, 트럭·앞차 정지의 불가피성, 실제 충돌 상대가 후방 차량인지, 급차로변경·급제동 여부, 뒤차의 반응 시간과 안전거리 확보 가능성을 함께 봅니다.");
  }
  if (hasAny(context, ["중앙선", "대향", "마주", "2차", "후속"])) {
    additions.push("중앙선 침범 사유, 도로 장애물·불법 주정차 영향, 마주오던 차량의 회피 가능성, 정차 후 2차 충돌 여부를 분리해 검토합니다.");
  }
  if (hasAny(context, ["무등화", "스텔스", "시인성"]) || (hasAny(context, ["속도위반", "제한속도", "과속"]) && hasAny(context, ["형사", "민사", "사망"]))) {
    additions.push("야간 무등화 정차 차량의 시인성, 제한속도와 실제 속도, 회피 가능성, 사망 사고의 형사·민사 책임을 분리해 봅니다.");
  }
  if (!additions.length || !basis.length) return basis;

  const copy = basis.map((item) => ({ ...item }));
  for (const addition of additions) {
    const index = basisTargetIndex(copy, addition);
    copy[index].reason = appendUniqueSentence(copy[index].reason, addition);
  }
  return copy;
}

function basisTargetIndex<T extends { title: string; reason: string }>(basis: T[], note: string) {
  const noteTerms = note.split(/[,\s·]+/).filter((term) => term.length >= 2);
  let bestIndex = 0;
  let bestScore = -1;
  basis.forEach((item, index) => {
    const text = `${item.title} ${item.reason}`.toLowerCase();
    const score = noteTerms.reduce((count, term) => count + (text.includes(term.toLowerCase()) ? 1 : 0), 0);
    if (score > bestScore) {
      bestIndex = index;
      bestScore = score;
    }
  });
  return bestIndex;
}

function appendUniqueSentence(text: string, sentence: string) {
  const current = cleanText(text, "");
  if (current.includes(sentence)) return current;
  return current.endsWith(".") || current.endsWith("다.") ? `${current} ${sentence}` : `${current}. ${sentence}`;
}

function hasAny(text: string, terms: string[]) {
  return terms.some((term) => text.includes(term.toLowerCase()));
}

function expertGuidanceStatusLabel(value: any) {
  const labels: AnyRecord = {
    evidence_supported_reference: "근거 확인됨",
    reference_only: "참고용",
    needs_more_facts: "추가 확인 필요",
  };
  return labels[String(value)] ?? "참고용";
}
