import {
  asArray,
  cleanText,
  safeKniaThumbnailUrl,
  safeKniaUrl,
  toNumber,
  type AnyRecord,
} from "./report-composer-common.js";

const KNIA_SOURCE_LINK_NOTICE = "영상 파일은 LawCompass 서버에 저장하지 않고, 과실비율정보포털 원본 링크로만 제공합니다.";
const KNIA_MISSING_SOURCE_NOTICE = "수집된 KNIA 원문 링크가 없습니다. 관리자 KNIA 상세 수집을 먼저 실행해 주세요.";

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

  const seen = new Set<string>();
  return candidates
    .map(normalizeKniaCandidate)
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
    chart_type: cleanText(item.chart_type, ""),
    title: cleanText(item.title ?? item.chart_title ?? item.article_title, ""),
    accident_party_label: cleanText(item.accident_party_label, ""),
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

function isVideoUrl(value: string) {
  return /\.(mp4|mov|m4v|webm)(?:$|\?)/i.test(String(value || ""));
}

function buildKniaLinkCard(item: AnyRecord = {}) {
  const hasUrl = Boolean(item.source_url || item.button_url);
  return {
    title: "KNIA 원문 기준 및 관련 영상",
    description: "과실비율정보포털에서 제공하는 유사 사고 기준을 원문 링크로 확인할 수 있습니다.",
    chart_no: item.chart_no || undefined,
    chart_type: item.chart_type || undefined,
    chart_title: item.title || undefined,
    accident_party_label: item.accident_party_label || undefined,
    display_mode: "external_link",
    button_url: item.source_url || undefined,
    source_url: item.source_url || undefined,
    video_url: item.video_url || undefined,
    source_detail_url: item.source_detail_url || undefined,
    source_page_url: item.source_page_url || undefined,
    thumbnail_url: item.thumbnail_url || undefined,
    button_label: item.video_url ? "KNIA 관련 영상 보기" : "KNIA 원문 기준 보기",
    notice: hasUrl ? KNIA_SOURCE_LINK_NOTICE : KNIA_MISSING_SOURCE_NOTICE,
    missing_source_notice: hasUrl ? undefined : KNIA_MISSING_SOURCE_NOTICE,
    has_knia_candidate: true,
    source_label: "자료 출처: 과실비율정보포털",
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
