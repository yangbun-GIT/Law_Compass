const forbidden = ["chunk_id", "score", "model_info", "cache_key", "rag_top_k", "ai_profile", "llm_enabled", "orchestrator", "scenario_classifier", "claim_id", "evidence_refs", "required_evidence_family", "rear_end_collision", "REAR_END_SAFE_DISTANCE", "ROAD_ACCIDENT_REPORTING_DUTY", "???", '"injury":', '"stopped":', '"weather":'];
function sanitize(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "boolean") return value ? "예" : "아니오";
  let text = String(value).trim();
  if ((text.startsWith("{") && text.endsWith("}")) || (text.startsWith("[") && text.endsWith("]"))) return "";
  return text.replace(/\b[a-z]+(?:_[a-z0-9]+)+\b/g, "").replace(/\b[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+\b/g, "").replace(/\?\?+/g, "").replace(/score\s*[:=]?\s*\d+(\.\d+)?/gi, "").replace(/chunk[_ ]?id\s*[:=]?\s*[\w-]+/gi, "").replace(/model[_ ]?info/gi, "").trim();
}
const mockVisibleText = [
  "이번 사고는 정차 중 뒤차가 들이받은 사고로 보이며, 상대 차량 책임이 더 클 가능성이 높습니다.",
  "블랙박스 원본 보관",
  "내 책임 10%",
  "상대방 책임 90%",
  sanitize("REAR_END_SAFE_DISTANCE"),
  sanitize('{"injury": null, "stopped": true}')
].join("\n");
const leaked = forbidden.filter((token) => mockVisibleText.includes(token));
if (leaked.length) {
  console.error("display sanitizer failed", leaked, mockVisibleText);
  process.exit(1);
}

import { readFileSync } from "node:fs";

const apiClient = readFileSync("src/api/client.ts", "utf8");
const appView = readFileSync("src/App.vue", "utf8");
const dashboardView = readFileSync("src/views/DashboardView.vue", "utf8");
const caseDetailView = readFileSync("src/views/CaseDetailView.vue", "utf8");
const caseCreateView = readFileSync("src/views/CaseCreateView.vue", "utf8");
const useCaseWorkspace = readFileSync("src/composables/useCaseWorkspace.ts", "utf8");
const caseWorkspaceGuidance = readFileSync("src/composables/caseWorkspaceGuidance.ts", "utf8");
const caseWorkspaceGuidanceData = readFileSync("src/data/caseWorkspaceGuidanceData.ts", "utf8");
const caseWorkspaceFormatters = readFileSync("src/composables/caseWorkspaceFormatters.ts", "utf8");
const caseWorkspaceProgress = readFileSync("src/composables/caseWorkspaceProgress.ts", "utf8");
const caseWorkspaceFactMapping = readFileSync("src/composables/caseWorkspaceFactMapping.ts", "utf8");
const caseWorkspaceOrchestration = readFileSync("src/composables/caseWorkspaceOrchestration.ts", "utf8");
const caseWorkspacePayloads = readFileSync("src/composables/caseWorkspacePayloads.ts", "utf8");
const caseWorkspaceHeader = readFileSync("src/components/case/CaseWorkspaceHeader.vue", "utf8");
const loginView = readFileSync("src/views/LoginView.vue", "utf8");
const signupView = readFileSync("src/views/SignupView.vue", "utf8");
const resultView = readFileSync("src/views/CaseResultView.vue", "utf8");
const evidenceView = readFileSync("src/views/EvidenceDetailView.vue", "utf8");
const easyReportView = readFileSync("src/components/easy/EasyReportView.vue", "utf8");
const relatedVideoCard = readFileSync("src/components/knia/RelatedVideoCard.vue", "utf8");
const kniaVideoLinkCard = readFileSync("src/components/knia/KniaVideoLinkCard.vue", "utf8");
const evidenceReliabilityCard = readFileSync("src/components/easy/EvidenceReliabilityCard.vue", "utf8");
const videoFactExplanationCard = readFileSync("src/components/easy/VideoFactExplanationCard.vue", "utf8");
const kniaRankingView = readFileSync("src/views/KniaRankingView.vue", "utf8");
const kniaChartView = readFileSync("src/views/KniaChartView.vue", "utf8");
const kniaJsonSearchBox = readFileSync("src/components/knia/KniaJsonSearchBox.vue", "utf8");
const displaySanitizer = readFileSync("src/utils/displaySanitizer.ts", "utf8");
const sanitizerContracts = [
  "sanitizeUserVisibleText",
  "formatKniaBody",
  "splitLegalBasisParagraphs",
  "참고할 수 있는 근거",
  "교통사고 법률 설명 자료",
  "직접 충돌 대상이 사람이면"
];
const missingSanitizerContracts = sanitizerContracts.filter((token) => !displaySanitizer.includes(token));
if (missingSanitizerContracts.length) {
  console.error("display sanitizer contract failed", missingSanitizerContracts);
  process.exit(1);
}
const publicUserFiles = [dashboardView, caseDetailView, easyReportView, caseWorkspaceGuidanceData].join("\n");
const forbiddenPublicPhrases = ["직접 충돌 대상이 사람이면 KNIA 보 계열 기준만 사용해야 합니다.", "관련성이 있는 근거입니다.", "교통사고 법률 설명 자료", "=4, =4.", "=9", ", ="];
const publicPhraseLeaks = forbiddenPublicPhrases.filter((token) => publicUserFiles.includes(token));
if (publicPhraseLeaks.length) {
  console.error("public display exposes internal wording", publicPhraseLeaks);
  process.exit(1);
}
const requiredErrorUx = [
  "export function formatApiError",
  "normalizeValidation(data?.error?.details?.validation)",
  "white-space: pre-line",
  "v-if=\"!session.user\"",
  "dashboard-hero",
  "첫 케이스 만들기",
  "사고 입력",
  "Analysis Result",
  "개발자 전용 원문",
  "법률 근거가 부족합니다",
  "근거 연결 상태",
  "검색 조건에 맞는 기준이 없습니다",
  "상세 기준 수집 필요",
  "상세 기준 수집",
  "검색순위에만 저장",
  "기본과실은 상세 기준 수집 후 표시됩니다",
  "수집 요청은 완료됐지만 상세 기준 본문이 저장되지 않았습니다",
  "KNIA 기준을 불러오지 못했습니다",
  "KNIA JSON 검색에 실패했습니다",
  "autocomplete=\"current-password\"",
  "autocomplete=\"new-password\"",
  "comparison-row",
  "input_label",
  "video_label",
  "영상 신뢰도"
];
const styles = readFileSync("src/styles.css", "utf8");
const displayFiles = [apiClient, styles, appView, dashboardView, caseDetailView, caseCreateView, caseWorkspaceHeader, loginView, signupView, resultView, evidenceView, easyReportView, relatedVideoCard, kniaVideoLinkCard, evidenceReliabilityCard, videoFactExplanationCard, kniaRankingView, kniaChartView, kniaJsonSearchBox, displaySanitizer, useCaseWorkspace, caseWorkspaceGuidance, caseWorkspaceGuidanceData, caseWorkspaceFormatters, caseWorkspaceProgress, caseWorkspaceFactMapping, caseWorkspaceOrchestration, caseWorkspacePayloads];
const missingErrorUx = requiredErrorUx.filter((token) => !displayFiles.some((text) => text.includes(token)));
if (missingErrorUx.length) {
  console.error("frontend error UX contract failed", missingErrorUx);
  process.exit(1);
}

const forbiddenAuthDefaults = ["password123", "user@example.com"];
const authDefaults = forbiddenAuthDefaults.filter((token) => loginView.includes(token) || signupView.includes(token));
if (authDefaults.length) {
  console.error("auth form default credentials found", authDefaults);
  process.exit(1);
}

if (loginView.includes("S3에 private로 저장")) {
  console.error("login guide still describes inactive S3 storage");
  process.exit(1);
}

const forbiddenEvidenceText = ["chunk_id:", "{{ chunk?.id }}", "<pre v-if=\"chunk?.chunk_text\">"];
const evidenceLeaks = forbiddenEvidenceText.filter((token) => evidenceView.includes(token));
if (evidenceLeaks.length) {
  console.error("evidence detail exposes internal identifiers by default", evidenceLeaks);
  process.exit(1);
}

const kniaLinkCardContracts = [
  "KNIA 원문 기준 및 관련 영상",
  "과실비율정보포털에서 제공하는 유사 사고 기준을 원문 링크로 확인할 수 있습니다.",
  "target=\"_blank\"",
  "rel=\"noopener noreferrer\"",
  "safeSourceUrl || video.has_knia_candidate",
  "수집된 KNIA 원문 링크가 없습니다. 관리자 KNIA 상세 수집을 먼저 실행해 주세요.",
];
const kniaCardText = [relatedVideoCard, kniaVideoLinkCard, easyReportView, kniaChartView].join("\n");
const missingKniaCardContracts = kniaLinkCardContracts.filter((token) => !kniaCardText.includes(token));
if (missingKniaCardContracts.length) {
  console.error("KNIA link card contract failed", missingKniaCardContracts);
  process.exit(1);
}
if (kniaCardText.includes("<iframe") || kniaCardText.includes("<video")) {
  console.error("KNIA card must not render iframe or video tags by default");
  process.exit(1);
}
if (relatedVideoCard.includes("<img") || kniaVideoLinkCard.includes("<img")) {
  console.error("KNIA link cards must not render default thumbnails as images");
  process.exit(1);
}
const userFriendlyKniaContracts = [
  "관련 KNIA 근거 및 영상",
  "RelatedVideoCard v-if=\"simpleKniaLinkCard\"",
  "simple_report?.knia_and_video?.primary",
  "KNIA 관련 영상 보기",
  "KNIA 원문 기준 보기",
  "상세 기준 수집 필요",
];
const missingUserFriendlyKnia = userFriendlyKniaContracts.filter((token) => !easyReportView.includes(token) && !kniaVideoLinkCard.includes(token));
if (missingUserFriendlyKnia.length) {
  console.error("user-friendly KNIA display contract failed", missingUserFriendlyKnia);
  process.exit(1);
}

const guidedFlowContracts = [
  "어떤 사고에 가장 가까운가요?",
  "잘 모르겠어요",
  "결과를 어떤 방식으로 볼까요?",
  "이대로 분석하기",
  "답변 더 추가하기",
  "고급 진단 보기",
  "영상 확인 중",
  "사고 장면 분석 중",
  "user_friendly",
  "expert",
  "일반사용자모드",
  "전문가모드",
  "fault-summary-card",
  "isQuickSummary",
  "analysis_mode_contract",
];
const missingGuidedContracts = guidedFlowContracts.filter((token) => !displayFiles.some((text) => text.includes(token)));
if (missingGuidedContracts.length) {
  console.error("guided analysis flow contract failed", missingGuidedContracts);
  process.exit(1);
}
if (caseCreateView.includes("<select v-model=\"analysisMode\"")) {
  console.error("analysis mode dropdown must not appear on the first create screen");
  process.exit(1);
}
function blockFor(source, marker) {
  const start = source.indexOf(marker);
  if (start < 0) return "";
  const rest = source.slice(start);
  const next = rest.indexOf("} else if", marker.length);
  return next >= 0 ? rest.slice(0, next) : rest;
}
const crosswalkContextMapping = blockFor(caseWorkspaceFactMapping, 'factKey === "crosswalk_context"');
if (crosswalkContextMapping.includes("car_vs_person") || crosswalkContextMapping.includes("pedestrian_crosswalk_accident")) {
  console.error("crosswalk context alone must not promote a case to pedestrian accident");
  process.exit(1);
}
const locationContextMapping = blockFor(caseWorkspaceFactMapping, 'factKey === "accident_location_context"');
const crosswalkLocation = locationContextMapping.slice(locationContextMapping.indexOf('value === "crosswalk"'));
if (crosswalkLocation.includes("car_vs_person") || crosswalkLocation.includes("pedestrian_crosswalk_accident")) {
  console.error("crosswalk location alone must remain road context until collision counterpart is confirmed");
  process.exit(1);
}
const defaultCaseDetail = caseDetailView.replace(/<details[\s\S]*?<\/details>/g, "");
const hiddenDeveloperTerms = ["Local video verified", "duration=", "resolution=", "frames=", "attempts:", "video_preprocess", "video_analyze", "job id", "Redis", "worker"];
const visibleLeaks = hiddenDeveloperTerms.filter((token) => defaultCaseDetail.includes(token));
if (visibleLeaks.length) {
  console.error("default guided flow exposes technical terms", visibleLeaks);
  process.exit(1);
}

if (useCaseWorkspace.includes("shouldProbeReport") || useCaseWorkspace.includes("progressPercent.value >= 75 ||")) {
  console.error("guided polling must not probe easy-report from a 75 percent heuristic");
  process.exit(1);
}
if (useCaseWorkspace.includes("Promise.all([loadReport(), loadProgress()])")) {
  console.error("guided polling must keep easy-report and analysis-progress polling separated");
  process.exit(1);
}
if (!caseWorkspaceGuidanceData.includes('"dead"')) {
  console.error("guided polling must treat dead jobs as failed jobs");
  process.exit(1);
}

const publicStorageText = [caseDetailView, loginView, dashboardView, useCaseWorkspace, caseWorkspaceGuidance, caseWorkspaceFormatters, caseWorkspaceProgress, caseWorkspaceFactMapping, caseWorkspaceOrchestration, caseWorkspacePayloads, readFileSync("src/components/case/CaseUploadStep.vue", "utf8")].join("\n");
const hiddenStorageTerms = ["S3", "NAS", "SFTP", "/volume1/lawcompass", "storage_key", "storage_path"];
const storageLeaks = hiddenStorageTerms.filter((token) => publicStorageText.includes(token));
if (storageLeaks.length) {
  console.error("default upload UI exposes internal storage terms", storageLeaks);
  process.exit(1);
}

console.log("frontend_display_safety=passed");
