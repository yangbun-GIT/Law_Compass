import {
  asArray,
  cleanText,
  cleanUserFacingCopy,
  resolveAccidentPartyLabel,
  safeKniaThumbnailUrl,
  safeKniaUrl,
  toNumber,
  type AnyRecord,
} from "./report-composer-common.js";

const KNIA_MISSING_SOURCE_NOTICE = "상세 기준 수집 필요";

export function composeKniaLinkCards(result: AnyRecord = {}, report: AnyRecord = {}): AnyRecord {
  const candidates = collectKniaDisplayCandidates(result, report);
  if (!candidates.length) return {};

  const urlCandidates = candidates.filter((item) => Boolean(item.source_url));
  const selected = urlCandidates[0] ?? candidates[0];
  const card = buildKniaLinkCard(selected);
  const auxiliary = urlCandidates
    .slice(0, 3)
    .map(buildKniaLinkCard)
    .filter((item, index, array) => {
      const key = kniaCandidateKey(item);
      return key && array.findIndex((candidate) => kniaCandidateKey(candidate) === key) === index;
    });

  return {
    related_knia_video_card: card,
    ...(auxiliary.length ? { knia_link_cards: auxiliary } : {}),
  };
}

export function removeDuplicateKniaRelatedVideo(report: AnyRecord = {}, canonicalCard?: AnyRecord) {
  const legacy = report.related_video;
  if (!legacy || typeof legacy !== "object" || !looksLikeKniaCandidate(legacy)) return report;

  const normalizedLegacy = normalizeKniaCandidate(legacy);
  const normalizedCanonical = canonicalCard ? normalizeKniaCandidate(canonicalCard) : undefined;
  const legacyKey = kniaCandidateKey(normalizedLegacy);
  const canonicalKey = normalizedCanonical ? kniaCandidateKey(normalizedCanonical) : "";

  if (!canonicalKey || legacyKey === canonicalKey || normalizedLegacy.has_knia_candidate) {
    const { related_video: _removedRelatedVideo, ...rest } = report;
    return rest;
  }
  return report;
}

function collectKniaDisplayCandidates(result: AnyRecord = {}, report: AnyRecord = {}) {
  const candidates: AnyRecord[] = [];
  const push = (item: any, source: string) => {
    if (!item || typeof item !== "object" || isRejectedKniaCandidate(item)) return;
    if (!looksLikeKniaCandidate(item)) return;
    const candidate = { ...item, candidate_source: source };
    if (candidate.chart_title && !candidate.title) candidate.title = candidate.chart_title;
    if (candidate.media && typeof candidate.media === "object") {
      for (const key of ["video_url", "source_url", "source_detail_url", "source_page_url", "thumbnail_url", "media_provider", "license_status"]) {
        if (!candidate[key] && candidate.media[key]) candidate[key] = candidate.media[key];
      }
    }
    candidates.push(candidate);
  };

  push(result.knia_primary_match, "knia_primary_match");
  for (const item of asArray(result.knia_matches)) push(item, "knia_matches");

  push(result.related_knia_video_card, "result.related_knia_video_card");
  push(result.related_video, "result.related_video");
  push(result.related_fault_standard, "result.related_fault_standard");

  push(report.related_knia_video_card ?? result.elderly_friendly_report?.related_knia_video_card, "related_knia_video_card");
  push(report.related_video ?? result.elderly_friendly_report?.related_video, "related_video");
  push(report.related_fault_standard ?? result.elderly_friendly_report?.related_fault_standard, "related_fault_standard");

  for (const item of asArray(result.knia_basis_cards)) push(item, "result.knia_basis_cards");
  for (const item of asArray(report.knia_basis_cards ?? result.elderly_friendly_report?.knia_basis_cards)) push(item, "knia_basis_cards");
  for (const item of asArray(report.knia_link_cards ?? result.elderly_friendly_report?.knia_link_cards)) push(item, "knia_link_cards");

  for (const key of ["knia_evidence", "combined_evidence", "evidence"]) {
    for (const item of asArray(result[key])) push(item, key);
  }

  const fault = result.fault_ratio ?? {};
  push(fault.knia_reference_fault?.source_chart ?? fault.knia_reference_fault, "knia_reference_fault");
  push(fault.knia_fault_estimate?.source_chart ?? fault.knia_fault_estimate, "knia_fault_estimate");
  push(deriveScenarioKniaCandidate(result, report), "scenario_knia_candidate");

  const seen = new Set<string>();
  const requestedParty = canonicalPartyType(
    result.knia_major_party_type ??
    result.accident_party_type ??
    result.scenario?.accident_party_type ??
    result.scenario?.knia_major_party_type ??
    result.normalized?.knia_major_party_type ??
    result.normalized?.structured_facts?.knia_major_party_type ??
    result.structured_facts?.knia_major_party_type,
  );
  return candidates
    .map(normalizeKniaCandidate)
    .filter((item) => isKniaCandidateAllowedForParty(item, requestedParty))
    .filter((item) => {
      const key = kniaCandidateKey(item);
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .sort(kniaCandidateSort);
}

function normalizeKniaCandidate(item: AnyRecord = {}) {
  const media = item.media && typeof item.media === "object" ? item.media : {};
  const directSourceUrl =
    safeKniaUrl(item.source_url) ||
    safeKniaUrl(item.button_url) ||
    safeKniaUrl(item.url) ||
    safeKniaUrl(item.href) ||
    safeKniaUrl(media.source_url);
  const videoUrl =
    safeKniaUrl(item.video_url) ||
    safeKniaUrl(media.video_url) ||
    (isVideoUrl(directSourceUrl) ? directSourceUrl : "");
  const sourceDetailUrl = safeKniaUrl(item.source_detail_url) || safeKniaUrl(media.source_detail_url);
  const sourcePageUrl =
    safeKniaUrl(item.source_page_url) ||
    safeKniaUrl(media.source_page_url) ||
    (!isVideoUrl(directSourceUrl) ? directSourceUrl : "");
  const displayUrl = videoUrl || sourceDetailUrl || sourcePageUrl || directSourceUrl;

  return {
    chart_no: cleanText(item.chart_no, ""),
    subchart_no: cleanText(item.subchart_no, ""),
    chart_type: cleanText(item.chart_type, ""),
    title: cleanText(item.title ?? item.chart_title ?? item.article_title, ""),
    summary: cleanUserFacingCopy(cleanText(item.summary ?? item.description ?? item.accident_situation, "")),
    menu_path: asArray(item.menu_path).map((part) => cleanText(part, "")).filter(Boolean),
    match_reason: cleanUserFacingCopy(cleanText(item.match_reason ?? item.why_matched, "")),
    base_fault: item.base_fault ?? item.knia_reference_fault?.base_fault,
    final_fault: item.final_fault ?? item.adjusted_fault ?? item.knia_reference_fault?.final_fault,
    fault_range: item.fault_range ?? item.knia_reference_fault?.fault_range,
    reference_only: item.reference_only === true || item.presentation_status === "reference_only",
    source_url_is_fallback: item.source_url_is_fallback === true,
    accident_party_type: cleanText(item.accident_party_type ?? item.major_party_type, ""),
    major_party_type: cleanText(item.major_party_type ?? item.accident_party_type, ""),
    accident_party_label: resolveAccidentPartyLabel({
      accident_party_label: item.accident_party_label,
      accident_party_type: item.accident_party_type ?? item.major_party_type,
      chart_no: item.chart_no ?? item.subchart_no,
    }),
    video_url: videoUrl,
    source_detail_url: sourceDetailUrl,
    source_page_url: sourcePageUrl,
    source_url: displayUrl,
    button_url: displayUrl,
    thumbnail_url: safeKniaThumbnailUrl(item.thumbnail_url || media.thumbnail_url),
    display_mode: "external_link",
    button_label: videoUrl ? "KNIA 관련 영상 보기" : "KNIA 원문 기준 보기",
    media_provider: cleanText(item.media_provider ?? media.media_provider, ""),
    license_status: cleanText(item.license_status ?? media.license_status, ""),
    score: toNumber(item.score ?? item.match_score, 0),
    has_knia_candidate: true,
  };
}

function deriveScenarioKniaCandidate(result: AnyRecord = {}, report: AnyRecord = {}): AnyRecord | null {
  const facts = result.structured_facts ?? result.normalized?.structured_facts ?? report.structured_facts ?? {};
  const fault = result.fault_ratio ?? {};
  const text = [
    result.scenario_type,
    result.accident_type,
    facts.accident_type,
    facts.scenario_type,
    fault.fault_estimate_source,
    fault.knia_adjustment_policy?.id,
    fault.knia_adjustment_registry?.policy?.id,
  ].map((value) => String(value ?? "")).join(" ").toLowerCase();

  const parkedStealth = /stealth_illegal_parked_vehicle|unlit|stopped_vehicle|parking_stopped_vehicle|parked_vehicle/.test(text)
    || facts.is_stealth_parked_vehicle_collision === true
    || facts.is_parked_vehicle_collision === true
    || facts.stopped_vehicle_without_lights === true;

  if (!parkedStealth) return null;

  return {
    chart_no: "차42",
    title: "주정차 차량 추돌 사고",
    major_party_type: "car_vs_car",
    accident_party_type: "car_vs_car",
    menu_path: ["자동차와 자동차의 사고", "같은 방향 진행차량 상호 간의 사고", "주정차 차량 추돌 사고"],
    source_url: `https://accident.knia.or.kr/myaccident-content?chartNo=${encodeURIComponent("차42")}&chartType=1`,
    source_url_is_fallback: true,
    summary: "야간 무등화 또는 비정상 정차 차량과 충돌한 상황은 주정차 차량 추돌 기준을 우선 참고합니다.",
    match_reason: "스텔스·무등화 정차 차량 및 야간 시야 제한 정황이 있어 주정차 차량 추돌 기준과 가까운 후보로 표시합니다.",
    base_fault: fault.base_fault ?? fault.knia_adjustment_registry?.base_fault,
    final_fault: fault.final_fault ?? fault.knia_adjustment_registry?.final_fault,
    fault_range: fault.fault_range ?? fault.knia_adjustment_registry?.fault_range,
    reference_only: true,
    score: 0.5,
  };
}

function canonicalPartyType(value: any) {
  const text = String(value ?? "").toLowerCase();
  if (["car_vs_car", "vehicle_vs_vehicle", "vehicle"].includes(text)) return "car_vs_car";
  if (["car_vs_person", "vehicle_vs_pedestrian", "pedestrian", "person"].includes(text)) return "car_vs_person";
  if (["car_vs_bicycle", "vehicle_vs_bicycle", "bicycle", "cyclist"].includes(text)) return "car_vs_bicycle";
  if (["car_vs_motorcycle", "motorcycle", "two_wheeler"].includes(text)) return "car_vs_motorcycle";
  if (["car_vs_object", "object", "fixed_object"].includes(text)) return "car_vs_object";
  if (["single_vehicle", "vehicle_single"].includes(text)) return "single_vehicle";
  return "";
}

function isKniaCandidateAllowedForParty(item: AnyRecord, requestedParty: string) {
  if (!requestedParty) return true;
  const party = canonicalPartyType(item.major_party_type || item.accident_party_type);
  if (party && party !== requestedParty) return false;
  const chart = String(item.chart_no || "");
  if (!chart) return true;
  if (requestedParty === "car_vs_person") return chart.startsWith("보") || chart.startsWith("蹂");
  if (requestedParty === "car_vs_car") return chart.startsWith("차") || chart.startsWith("李");
  if (requestedParty === "car_vs_bicycle") return chart.startsWith("거") || chart.startsWith("자") || chart.startsWith("嫄");
  if (requestedParty === "car_vs_object") return !(chart.startsWith("보") || chart.startsWith("蹂") || chart.startsWith("거") || chart.startsWith("자") || chart.startsWith("嫄"));
  if (requestedParty === "single_vehicle") return !(chart.startsWith("보") || chart.startsWith("蹂") || chart.startsWith("거") || chart.startsWith("자") || chart.startsWith("嫄"));
  return true;
}

function isVideoUrl(value: string) {
  return /\.(mp4|mov|m4v|webm)(?:$|\?)/i.test(String(value || ""));
}

function buildKniaLinkCard(item: AnyRecord = {}) {
  const hasUrl = Boolean(item.source_url || item.button_url);
  return {
    title: item.title || undefined,
    chart_no: item.chart_no || undefined,
    subchart_no: item.subchart_no || undefined,
    chart_type: item.chart_type || undefined,
    chart_title: item.title || undefined,
    menu_path: item.menu_path || undefined,
    summary: item.summary || undefined,
    match_reason: item.match_reason || undefined,
    base_fault: item.base_fault || undefined,
    final_fault: item.final_fault || undefined,
    fault_range: item.fault_range || undefined,
    reference_only: item.reference_only === true,
    source_url_is_fallback: item.source_url_is_fallback === true,
    accident_party_label: resolveAccidentPartyLabel({
      accident_party_label: item.accident_party_label,
      accident_party_type: item.accident_party_type ?? item.major_party_type,
      chart_no: item.chart_no ?? item.subchart_no,
    }),
    display_mode: "external_link",
    button_url: item.source_url || undefined,
    source_url: item.source_url || undefined,
    video_url: item.video_url || undefined,
    source_detail_url: item.source_detail_url || undefined,
    source_page_url: item.source_page_url || undefined,
    thumbnail_url: item.thumbnail_url || undefined,
    button_label: item.video_url ? "KNIA 관련 영상 보기" : "KNIA 원문 기준 보기",
    missing_source_notice: hasUrl ? undefined : KNIA_MISSING_SOURCE_NOTICE,
    has_knia_candidate: true,
  };
}

function kniaCandidateSort(a: AnyRecord, b: AnyRecord) {
  const av = a.video_url ? 0 : 1;
  const bv = b.video_url ? 0 : 1;
  if (av !== bv) return av - bv;
  const au = a.source_url ? 0 : 1;
  const bu = b.source_url ? 0 : 1;
  if (au !== bu) return au - bu;
  return Number(b.score || 0) - Number(a.score || 0);
}

function kniaCandidateKey(item: AnyRecord = {}) {
  if (item.chart_no) return `chart:${String(item.chart_no).toLowerCase()}:${String(item.chart_type || "").toLowerCase()}`;
  for (const key of ["video_url", "source_detail_url", "source_page_url", "source_url", "button_url"]) {
    const value = safeKniaUrl(item[key]);
    if (value) return `url:${value.toLowerCase()}`;
  }
  const title = cleanText(item.title ?? item.chart_title ?? item.article_title, "").toLowerCase();
  return title ? `title:${title}` : "";
}

function looksLikeKniaCandidate(item: AnyRecord = {}) {
  const text = [
    item.source_type,
    item.source,
    item.title,
    item.chart_title,
    item.article_title,
    item.law_name,
    item.chart_no,
    item.source_url,
    item.source_detail_url,
    item.source_page_url,
    item.video_url,
    item.button_url,
    item.media?.source_url,
    item.media?.video_url,
  ].map((value) => String(value ?? "").toLowerCase()).join(" ");
  return Boolean(item.chart_no) || text.includes("knia") || text.includes("과실비율") || text.includes("accident.knia.or.kr");
}

function isRejectedKniaCandidate(item: AnyRecord = {}) {
  const text = [
    item.status,
    item.reason,
    item.exclusion_reason,
    item.mismatch_reason,
    item.knia_override_policy,
    item.candidate_source,
  ].map((value) => String(value ?? "").toLowerCase()).join(" ");
  return /rejected|mismatch|incompatible|basis_mismatch|불일치|제외/.test(text);
}
