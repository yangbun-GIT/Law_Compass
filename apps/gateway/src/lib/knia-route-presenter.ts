export function cleanKniaPublicText(value: any, fallback: string) {
  const text = String(value ?? "").replace(/\s+/g, " ").trim();
  if (!text) return fallback;
  if (text.length > 420 || text.includes("과실비율의 이해 과실비율 인정기준") || text.includes(" Main ")) return fallback;
  return text;
}

export function summarizeRankingDetailStatus(rows: any[]) {
  const total = rows.length;
  const detailReady = rows.filter((row: any) => !!row.has_detail).length;
  const missing = Math.max(total - detailReady, 0);
  return {
    displayed_count: total,
    detail_ready_count: detailReady,
    detail_missing_count: missing,
    detail_ready_ratio: total ? Math.round((detailReady / total) * 100) : 0,
    needs_detail_collection: missing > 0,
  };
}

export function publicKniaThumbnail(value: any) {
  const text = String(value ?? "").trim();
  const lowered = text.toLowerCase();
  if (!text || lowered.includes("logo_test.jpg") || lowered.includes("/images/common/logo_test")) {
    return null;
  }
  return text;
}

export function asArray(value: any): any[] {
  return Array.isArray(value) ? value : [];
}

export function safeText(value: any) {
  return String(value ?? "").replace(/\s+/g, " ").trim();
}

function isNumericAdjustmentText(value: any) {
  const text = safeText(value);
  return /^[AB]?\s*[+-]?\d+(?:\.\d+)?%?$/.test(text) || /^조정값\s*[+-]?\d+(?:\.\d+)?%?$/.test(text);
}

function isSyntheticAdjustmentLabel(value: any) {
  const text = safeText(value);
  return isNumericAdjustmentText(text) || /^가감요소\s*\d+$/i.test(text);
}

export function normalizeAdjustmentFactors(value: any, sourceDetailUrl?: any) {
  return asArray(value)
    .map((item: any, index: number) => {
      const delta = finiteNumber(item?.delta);
      const target = safeText(item?.applies_to_candidate ?? item?.applies_to ?? item?.target).toUpperCase();
      let deltaA = finiteNumber(item?.delta_a);
      let deltaB = finiteNumber(item?.delta_b);
      if (delta != null && deltaA == null && deltaB == null) {
        if (target.includes("B")) deltaB = delta;
        else deltaA = delta;
      }
      const rawLabel = safeText(item?.label ?? item?.title ?? item?.label_candidate ?? item?.source_line);
      const rawDescription = safeText(item?.description ?? item?.condition_text ?? item?.source_text ?? item?.source_line);
      const hasMeaningfulLabel = rawLabel && !isSyntheticAdjustmentLabel(rawLabel);
      const hasMeaningfulDescription = rawDescription && !isSyntheticAdjustmentLabel(rawDescription) && rawDescription !== rawLabel;

      if (!hasMeaningfulLabel && !hasMeaningfulDescription) {
        return null;
      }

      const label = hasMeaningfulLabel ? rawLabel : rawDescription;
      const description = hasMeaningfulDescription ? rawDescription : "";
      return {
        label,
        title: label,
        description,
        condition_text: description,
        condition_code: item?.condition_code ?? null,
        checkbox_value: item?.checkbox_value ?? label,
        delta_a: deltaA ?? 0,
        delta_b: deltaB ?? 0,
        source_case_id: item?.source_case_id ?? item?.subchart_no ?? "structured-json",
        factor_order: finiteNumber(item?.factor_order ?? item?.source_line_index) ?? index + 1,
        source_detail_url: item?.source_detail_url ?? sourceDetailUrl ?? null,
        review_required: !!item?.review_required,
      };
    })
    .filter(Boolean)
    .filter((item: any) => safeText(item.label));
}

export function normalizeRelatedLaws(value: any, sourceDetailUrl?: any) {
  return asArray(value)
    .map((item: any, index: number) => {
      if (typeof item === "string") {
        return {
          section_type: "related_law",
          law_title: "관련 법규",
          law_text: safeText(item),
          item_order: index + 1,
          source_detail_url: sourceDetailUrl ?? null,
        };
      }
      return {
        section_type: "related_law",
        law_title: safeText(item?.law_title ?? item?.title ?? "관련 법규"),
        law_text: safeText(item?.law_text ?? item?.body ?? item?.text),
        item_order: finiteNumber(item?.item_order) ?? index + 1,
        source_detail_url: item?.source_detail_url ?? sourceDetailUrl ?? null,
      };
    })
    .filter((item: any) => safeText(item.law_text));
}

export function normalizeAdjustmentExplanations(value: any, chart: any) {
  const sourceDetailUrl = chart?.source_detail_url ?? chart?.source_url;
  const rows = asArray(value)
    .map((item: any, index: number) => ({
      section_type: "adjustment_explanation",
      title: safeText(item?.title ?? "수정요소 해설"),
      body: safeText(item?.body ?? item?.text ?? item?.summary),
      item_order: finiteNumber(item?.item_order) ?? index + 1,
      source_detail_url: item?.source_detail_url ?? sourceDetailUrl ?? null,
    }))
    .filter((item: any) => safeText(item.body));
  const baseFaultExplanation = safeText(chart?.base_fault_explanation);
  if (!rows.length && baseFaultExplanation) {
    rows.push({
      section_type: "adjustment_explanation",
      title: "기본 과실 해설",
      body: baseFaultExplanation,
      item_order: 1,
      source_detail_url: sourceDetailUrl ?? null,
    });
  }
  const usageNotes = safeText(chart?.usage_notes);
  if (usageNotes && !rows.some((item: any) => item.body === usageNotes)) {
    rows.push({
      section_type: "adjustment_explanation",
      title: "활용 참고사항",
      body: usageNotes,
      item_order: rows.length + 1,
      source_detail_url: sourceDetailUrl ?? null,
    });
  }
  return rows;
}

export function normalizeCaseReferences(value: any, sourceDetailUrl?: any) {
  return asArray(value)
    .map((item: any, index: number) => {
      if (typeof item === "string") {
        return {
          section_type: "case_reference",
          case_title: "판례·조정사례",
          case_body: safeText(item),
          decision_summary: null,
          item_order: index + 1,
          source_detail_url: sourceDetailUrl ?? null,
        };
      }
      return {
        section_type: "case_reference",
        case_title: safeText(item?.case_title ?? item?.title ?? "판례·조정사례"),
        case_body: safeText(item?.case_body ?? item?.body ?? item?.text),
        decision_summary: safeText(item?.decision_summary),
        item_order: finiteNumber(item?.item_order) ?? index + 1,
        source_detail_url: item?.source_detail_url ?? sourceDetailUrl ?? null,
      };
    })
    .filter((item: any) => safeText(item.case_body));
}

export const KNIA_RANKING_CATEGORIES = [
  { label: "전체", value: "all", source_value: "전체" },
  { label: "차대차", value: "car_vs_car", source_value: "차대차" },
  { label: "차대사람", value: "car_vs_person", source_value: "차대사람" },
  { label: "차대자전거", value: "car_vs_bicycle", source_value: "차대자전거" }
];

const KNIA_PARTY_LABELS: Record<string, string> = {
  car_vs_car: "차대차 사고",
  car_vs_person: "차대보행자 사고",
  car_vs_bicycle: "차대자전거 사고",
  single_vehicle: "단독 사고",
  car_vs_object: "물체/시설물 사고",
  unknown: "확인이 필요합니다."
};

export function normalizeKniaRankingQuery(value: unknown) {
  const raw = String(value ?? "").trim();
  if (!raw) return "";
  try {
    return decodeURIComponent(raw).replace(/\s+/g, " ").trim().slice(0, 120);
  } catch {
    return raw.replace(/\s+/g, " ").trim().slice(0, 120);
  }
}

export function parameter(params: any[], value: any) {
  params.push(value);
  return `$${params.length}`;
}

function kniaPartyFromChartNo(value: unknown) {
  const chartNo = String(value ?? "").trim();
  if (chartNo.startsWith("차")) return "car_vs_car";
  if (chartNo.startsWith("보")) return "car_vs_person";
  if (chartNo.startsWith("자") || chartNo.startsWith("거")) return "car_vs_bicycle";
  if (chartNo.startsWith("단")) return "single_vehicle";
  if (chartNo.startsWith("기") || chartNo.startsWith("물")) return "car_vs_object";
  return "";
}

function normalizeKniaRankingParty(input: { accident_party_type?: any; chart_no?: any; source_category?: any }) {
  const byPrefix = kniaPartyFromChartNo(input.chart_no);
  if (byPrefix) return byPrefix;
  const raw = String(input.accident_party_type ?? "").trim();
  if (raw && raw !== "unknown") return raw;
  const source = String(input.source_category ?? "").trim();
  if (source.includes("차대자전거") || source.includes("자전거")) return "car_vs_bicycle";
  if (source.includes("차대사람") || source.includes("보행")) return "car_vs_person";
  if (source.includes("차대차")) return "car_vs_car";
  return raw || "unknown";
}

function kniaRankingPartyLabel(input: { accident_party_label?: any; accident_party_type?: any; chart_no?: any; source_category?: any }) {
  const byPrefix = kniaPartyFromChartNo(input.chart_no);
  if (byPrefix) return KNIA_PARTY_LABELS[byPrefix] ?? KNIA_PARTY_LABELS.unknown;
  const existing = String(input.accident_party_label ?? "").trim();
  if (existing && existing !== "확인이 필요합니다." && existing !== "사고유형 확인 필요") return existing;
  const party = normalizeKniaRankingParty(input);
  return KNIA_PARTY_LABELS[party] ?? KNIA_PARTY_LABELS.unknown;
}

function rankingSourceCategoryForParty(party: string) {
  return KNIA_RANKING_CATEGORIES.find((item) => item.value === party)?.source_value ?? "";
}

export function buildKniaRankingPartyClause(alias: string, params: any[], accidentPartyType: string, sourceAlias?: string) {
  if (!accidentPartyType || accidentPartyType === "all") return "";
  const partyParam = parameter(params, accidentPartyType);
  const sourceLabel = rankingSourceCategoryForParty(accidentPartyType);
  const sourceClause = sourceAlias && sourceLabel ? ` OR ${sourceAlias}.source_category=${parameter(params, sourceLabel)}` : "";

  if (accidentPartyType === "car_vs_car") {
    return ` AND (${alias}.accident_party_type=${partyParam} OR ${alias}.chart_no LIKE '차%'${sourceClause})`;
  }
  if (accidentPartyType === "car_vs_person") {
    return ` AND (${alias}.accident_party_type=${partyParam} OR ${alias}.chart_no LIKE '보%'${sourceClause})`;
  }
  if (accidentPartyType === "car_vs_bicycle") {
    return ` AND (${alias}.accident_party_type=${partyParam} OR ${alias}.chart_no LIKE '자%' OR ${alias}.chart_no LIKE '거%'${sourceClause})`;
  }
  if (accidentPartyType === "single_vehicle") {
    return ` AND (${alias}.accident_party_type=${partyParam} OR ${alias}.chart_no LIKE '단%'${sourceClause})`;
  }
  return ` AND (${alias}.accident_party_type=${partyParam}${sourceClause})`;
}

function rankingSearchTerms(q: string, accidentPartyType: string) {
  const terms = [q].filter(Boolean);
  const isBicycleQuery = accidentPartyType === "car_vs_bicycle" || /자전거|차대자전거|bike|bicycle/i.test(q);
  if (isBicycleQuery) {
    for (const term of ["자전거", "차대자전거", "자전거도로", "자전거 사고"]) {
      if (!terms.includes(term)) terms.push(term);
    }
  }
  return terms;
}

export function buildKniaRankingSearchClause(params: any[], q: string, accidentPartyType: string) {
  if (!q) return "";
  const includesBicyclePrefix = accidentPartyType === "car_vs_bicycle" && /자전거|차대자전거|bike|bicycle/i.test(q);
  const clauses = rankingSearchTerms(q, accidentPartyType).map((term) => {
    const like = parameter(params, `%${term}%`);
    return `(
      r.chart_no ILIKE ${like}
      OR r.title ILIKE ${like}
      OR COALESCE(r.source_category, '') ILIKE ${like}
      OR COALESCE(r.source_url, '') ILIKE ${like}
      OR COALESCE(r.source_detail_url, '') ILIKE ${like}
      OR COALESCE(c.accident_summary, '') ILIKE ${like}
      OR COALESCE(c.basic_fault_text, '') ILIKE ${like}
      OR COALESCE(c.display_tags::text, '') ILIKE ${like}
      OR COALESCE(c.category_path::text, '') ILIKE ${like}
    )`;
  });
  const prefixFallback = includesBicyclePrefix ? " OR r.chart_no LIKE '자%' OR r.chart_no LIKE '거%'" : "";
  return ` AND (${clauses.join(" OR ")}${prefixFallback})`;
}

export function buildKniaChartFallbackSearchClause(params: any[], q: string, accidentPartyType: string) {
  if (!q) return "";
  const includesBicyclePrefix = accidentPartyType === "car_vs_bicycle" && /자전거|차대자전거|bike|bicycle/i.test(q);
  const clauses = rankingSearchTerms(q, accidentPartyType).map((term) => {
    const like = parameter(params, `%${term}%`);
    return `(
      c.chart_no ILIKE ${like}
      OR c.title ILIKE ${like}
      OR COALESCE(c.accident_summary, '') ILIKE ${like}
      OR COALESCE(c.basic_fault_text, '') ILIKE ${like}
      OR COALESCE(c.display_tags::text, '') ILIKE ${like}
      OR COALESCE(c.category_path::text, '') ILIKE ${like}
      OR COALESCE(c.source_url, '') ILIKE ${like}
      OR COALESCE(c.source_detail_url, '') ILIKE ${like}
    )`;
  });
  const prefixFallback = includesBicyclePrefix ? " OR c.chart_no LIKE '자%' OR c.chart_no LIKE '거%'" : "";
  return ` AND (${clauses.join(" OR ")}${prefixFallback})`;
}

export function normalizeKniaRankingRow(row: any) {
  const party = normalizeKniaRankingParty(row);
  const chartType = row.chart_type ?? "1";
  const chartNo = row.chart_no;
  const localUrl = row.local_chart_url ?? row.chart_url ?? `/knia/charts/${encodeURIComponent(chartNo)}?chartType=${encodeURIComponent(chartType)}`;
  return {
    rank: row.rank == null ? null : Number(row.rank),
    rank_no: row.rank == null ? null : Number(row.rank),
    chart_no: chartNo,
    chart_type: chartType,
    title: row.title || `KNIA 과실비율 인정기준 ${chartNo}`,
    search_count: row.search_count == null ? null : Number(row.search_count),
    percentage: row.percentage == null ? null : Number(row.percentage),
    source_category: row.source_category || rankingSourceCategoryForParty(party) || "전체",
    accident_party_type: party,
    accident_party_label: kniaRankingPartyLabel(row),
    source_url: row.source_url,
    source_detail_url: row.source_detail_url,
    local_chart_url: localUrl,
    source_onclick: row.source_onclick,
    chart_url: localUrl,
    has_detail: !!row.has_detail,
    base_fault_a: row.base_fault_a == null ? null : Number(row.base_fault_a),
    base_fault_b: row.base_fault_b == null ? null : Number(row.base_fault_b),
    adjustment_factor_count: Number(row.adjustment_factor_count ?? 0),
    reference_section_count: Number(row.reference_section_count ?? 0),
    collected_at: row.collected_at,
    summary: row.summary ?? row.accident_summary ?? row.basic_fault_text ?? null,
    matched_by: row.matched_by ?? "ranking",
  };
}

export function finiteNumber(value: any) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function lowerPositiveNumber(left: any, right: any) {
  const leftNumber = finiteNumber(left);
  const rightNumber = finiteNumber(right);
  const leftValid = leftNumber != null && leftNumber > 0;
  const rightValid = rightNumber != null && rightNumber > 0;
  if (leftValid && rightValid) return Math.min(leftNumber, rightNumber);
  if (leftValid) return leftNumber;
  if (rightValid) return rightNumber;
  return null;
}

function higherNumber(left: any, right: any) {
  const leftNumber = finiteNumber(left);
  const rightNumber = finiteNumber(right);
  if (leftNumber == null) return rightNumber;
  if (rightNumber == null) return leftNumber;
  return Math.max(leftNumber, rightNumber);
}

function rankingDedupeKey(item: any) {
  const chartNo = String(item?.chart_no ?? "").trim();
  if (!chartNo) return "";
  return `${chartNo}::${String(item?.chart_type ?? "1").trim() || "1"}`;
}

function pickRicherRankingRow(left: any, right: any) {
  if (!!right.has_detail !== !!left.has_detail) return right.has_detail ? right : left;
  const rightSearchCount = finiteNumber(right.search_count) ?? -1;
  const leftSearchCount = finiteNumber(left.search_count) ?? -1;
  if (rightSearchCount !== leftSearchCount) return rightSearchCount > leftSearchCount ? right : left;
  const rightPercentage = finiteNumber(right.percentage) ?? -1;
  const leftPercentage = finiteNumber(left.percentage) ?? -1;
  if (rightPercentage !== leftPercentage) return rightPercentage > leftPercentage ? right : left;
  const rightRank = finiteNumber(right.rank) ?? Number.MAX_SAFE_INTEGER;
  const leftRank = finiteNumber(left.rank) ?? Number.MAX_SAFE_INTEGER;
  if (rightRank !== leftRank) return rightRank < leftRank ? right : left;
  return left;
}

function mergeRankingDuplicate(left: any, right: any) {
  const preferred = pickRicherRankingRow(left, right);
  const rank = lowerPositiveNumber(left.source_rank ?? left.rank, right.source_rank ?? right.rank);
  const searchCount = higherNumber(left.search_count, right.search_count);
  const percentage = higherNumber(left.percentage, right.percentage);
  return {
    ...preferred,
    source_rank: rank,
    rank,
    rank_no: rank,
    search_count: searchCount,
    percentage,
    duplicate_merged_count: Number(left.duplicate_merged_count ?? 1) + Number(right.duplicate_merged_count ?? 1),
  };
}

function sortRankingItems(left: any, right: any) {
  const leftRank = finiteNumber(left.source_rank ?? left.rank) ?? Number.MAX_SAFE_INTEGER;
  const rightRank = finiteNumber(right.source_rank ?? right.rank) ?? Number.MAX_SAFE_INTEGER;
  if (leftRank !== rightRank) return leftRank - rightRank;
  const leftSearchCount = finiteNumber(left.search_count) ?? -1;
  const rightSearchCount = finiteNumber(right.search_count) ?? -1;
  if (leftSearchCount !== rightSearchCount) return rightSearchCount - leftSearchCount;
  const leftPercentage = finiteNumber(left.percentage) ?? -1;
  const rightPercentage = finiteNumber(right.percentage) ?? -1;
  if (leftPercentage !== rightPercentage) return rightPercentage - leftPercentage;
  return String(left.chart_no ?? "").localeCompare(String(right.chart_no ?? ""), "ko");
}

export function dedupeKniaRankingItems(items: any[], limit: number) {
  const byChart = new Map<string, any>();
  const passthrough: any[] = [];
  for (const item of items) {
    const key = rankingDedupeKey(item);
    if (!key) {
      passthrough.push(item);
      continue;
    }
    const current = byChart.get(key);
    byChart.set(key, current ? mergeRankingDuplicate(current, item) : { ...item, source_rank: item.rank ?? null, duplicate_merged_count: 1 });
  }

  return [...byChart.values(), ...passthrough]
    .sort(sortRankingItems)
    .slice(0, limit)
    .map((item, index) => ({
      ...item,
      source_rank: item.source_rank ?? item.rank ?? null,
      rank: index + 1,
      rank_no: index + 1,
    }));
}
