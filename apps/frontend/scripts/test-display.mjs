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
const analysisLoadingSpinner = readFileSync("src/components/case/AnalysisLoadingSpinner.vue", "utf8");
const loginView = readFileSync("src/views/LoginView.vue", "utf8");
const signupView = readFileSync("src/views/SignupView.vue", "utf8");
const routerIndex = readFileSync("src/router/index.ts", "utf8");
const sessionStore = readFileSync("src/stores/session.ts", "utf8");
const resultView = readFileSync("src/views/CaseResultView.vue", "utf8");
const evidenceView = readFileSync("src/views/EvidenceDetailView.vue", "utf8");
const easyReportView = readFileSync("src/components/easy/EasyReportView.vue", "utf8");
const relatedVideoCard = readFileSync("src/components/knia/RelatedVideoCard.vue", "utf8");
const kniaVideoLinkCard = readFileSync("src/components/knia/KniaVideoLinkCard.vue", "utf8");
const topConclusionCard = readFileSync("src/components/easy/TopConclusionCard.vue", "utf8");
const accidentPartyTypeActionCard = readFileSync("src/components/result/AccidentPartyTypeActionCard.vue", "utf8");
const elderlyActionCard = readFileSync("src/components/easy/ElderlyActionCard.vue", "utf8");
const expertGuidanceCard = readFileSync("src/components/easy/ExpertGuidanceCard.vue", "utf8");
const easyLegalBasisCard = readFileSync("src/components/easy/EasyLegalBasisCard.vue", "utf8");
const evidenceReliabilityCard = readFileSync("src/components/easy/EvidenceReliabilityCard.vue", "utf8");
const videoFactExplanationCard = readFileSync("src/components/easy/VideoFactExplanationCard.vue", "utf8");
const frameEvidenceCard = readFileSync("src/components/easy/FrameEvidenceCard.vue", "utf8");
const agentProcessCard = readFileSync("src/components/easy/AgentProcessCard.vue", "utf8");
const kniaRankingView = readFileSync("src/views/KniaRankingView.vue", "utf8");
const kniaChartView = readFileSync("src/views/KniaChartView.vue", "utf8");
const kniaFaultRatioBar = readFileSync("src/components/knia/KniaFaultRatioBar.vue", "utf8");
const kniaDetailEvidenceCard = readFileSync("src/components/knia/KniaDetailEvidenceCard.vue", "utf8");
const kniaJsonSearchBox = readFileSync("src/components/knia/KniaJsonSearchBox.vue", "utf8");
const displaySanitizer = readFileSync("src/utils/displaySanitizer.ts", "utf8");
const styles = readFileSync("src/styles.css", "utf8");
const agentVideoSummarizer = readFileSync("../agent/app/services/video_observation_summarizer.py", "utf8");
const agentVideoRules = readFileSync("../agent/app/services/video_input_contract_rules.py", "utf8");
const agentInputNormalizer = readFileSync("../agent/app/services/input_normalizer.py", "utf8");
const agentScenarioClassifier = readFileSync("../agent/app/services/scenario_classifier.py", "utf8");
const agentFaultRatioAnalyst = readFileSync("../agent/app/services/analysts/fault_ratio_analyst.py", "utf8");
const agentDynamicQuestionnaire = readFileSync("../agent/app/services/dynamic_questionnaire.py", "utf8");
const agentVideoFactGuards = readFileSync("../agent/app/services/video_input_contract_guards.py", "utf8");
const workerFrameAnalysis = readFileSync("../worker/worker/frame_analysis.py", "utf8");
const sanitizerContracts = [
  "sanitizeUserVisibleText",
  "cleanUserFacingCopy",
  "removeRawJsonFragments",
  "collapseRepeatedPhrases",
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

const videoOnlySceneContracts = [
  "build_video_scene_summary",
  "영상에서 확인된 사고 개요",
  "confirmed_visual_facts",
  "needs_user_confirmation",
  "ego_vehicle_type",
  "direct_collision_partner_type",
  "speed_limit_kmh",
  "oncoming_bicycle_present",
  "child_candidate",
  "overlay_text_hint",
  "오토바이와 자전거 사고",
  "is_video_only",
];
const videoOnlySceneSource = [
  agentVideoSummarizer,
  agentVideoRules,
  workerFrameAnalysis,
  easyReportView,
  displaySanitizer,
  caseWorkspacePayloads,
].join("\n");
const missingVideoOnlySceneContracts = videoOnlySceneContracts.filter((token) => !videoOnlySceneSource.includes(token));
if (missingVideoOnlySceneContracts.length) {
  console.error("video-only frame observation summary contract failed", missingVideoOnlySceneContracts);
  process.exit(1);
}

const nonContactMotorcycleContracts = [
  "non_contact_motorcycle_single_fall",
  "narrow_curve_oncoming_motorcycle_loss_of_control",
  "direct_contact_with_ego",
  "ego_collision_confirmed",
  "opponent_single_fall",
  "non_contact_near_miss",
  "opponent_motorcycle_nearby",
  "physical_contact_frame_refs",
  "non_contact_motorcycle_single_fall_rule",
  "no_primary_contact_standard",
  "direct_contact_negative_fact_blocks_contact_partner",
  "비접촉 이륜차 단독 전도",
];
const nonContactMotorcycleSource = [
  agentInputNormalizer,
  agentScenarioClassifier,
  agentFaultRatioAnalyst,
  agentDynamicQuestionnaire,
  agentVideoRules,
  agentVideoFactGuards,
  workerFrameAnalysis,
  displaySanitizer,
].join("\n");
const missingNonContactMotorcycleContracts = nonContactMotorcycleContracts.filter((token) => !nonContactMotorcycleSource.includes(token));
if (missingNonContactMotorcycleContracts.length) {
  console.error("non-contact motorcycle single-fall contract failed", missingNonContactMotorcycleContracts);
  process.exit(1);
}
if (agentDynamicQuestionnaire.includes("opponent_signal") && agentDynamicQuestionnaire.includes("non_contact_motorcycle_single_fall")) {
  const nonContactQuestionBlock = agentDynamicQuestionnaire.slice(agentDynamicQuestionnaire.indexOf("non_contact_motorcycle_single_fall"));
  if (nonContactQuestionBlock.slice(0, 1800).includes("opponent_signal")) {
    console.error("non-contact motorcycle flow must not start with irrelevant signal questions");
    process.exit(1);
  }
}

const brandLinkContracts = [
  '<RouterLink class="brand brand-link" to="/"',
  'aria-label="LawCompass 메인 화면으로 이동"',
  "LawCompass",
  "교통사고 AI 분석 도우미",
  ".brand-link:focus-visible",
];
const brandLinkSource = [appView, styles].join("\n");
const missingBrandLinkContracts = brandLinkContracts.filter((token) => !brandLinkSource.includes(token));
if (missingBrandLinkContracts.length) {
  console.error("app brand must navigate to the main route with accessible focus styling", missingBrandLinkContracts);
  process.exit(1);
}

const publicUserFiles = [dashboardView, caseDetailView, easyReportView, caseWorkspaceGuidanceData].join("\n");
const forbiddenPublicPhrases = [
  "직접 충돌 대상이 사람이면 KNIA 보 계열 기준만 사용해야 합니다.",
  "관련성이 있는 근거입니다.",
  "교통사고 법률 설명 자료",
  "=4, =4.",
  "=9",
  ", =",
];
const publicReportFiles = [easyReportView, relatedVideoCard, kniaVideoLinkCard, topConclusionCard].join("\n");
const forbiddenGeneralReportPhrases = [
  "영상 파일은 LawCompass 서버에 저장하지 않고",
  "과실비율정보포털에서 제공하는 유사 사고 기준을 원문 링크로 확인할 수 있습니다",
  "참고용 분석입니다",
  "조건부 결과는 특정 테스트 영상에 맞춘 답이 아니라",
  "이 내용은 유사 근거와 입력 사실을 바탕으로 한 참고용 예상입니다",
  "더 확인하면 좋은 사실",
  "차량 파손 정도는 어느 정도인가요",
  "인명피해 여부",
  "신호 상태",
  "사고 장소",
  "상대방 행위",
  "{\"inj",
  "정차 중 후미추돌 사고 정차 중 후미추돌 사고",
];
const publicPhraseLeaks = forbiddenPublicPhrases.filter((token) => publicUserFiles.includes(token));
if (publicPhraseLeaks.length) {
  console.error("public display exposes internal wording", publicPhraseLeaks);
  process.exit(1);
}
const publicReportPhraseLeaks = forbiddenGeneralReportPhrases.filter((token) => publicReportFiles.includes(token));
if (publicReportPhraseLeaks.length) {
  console.error("general user report exposes hidden copy", publicReportPhraseLeaks);
  process.exit(1);
}
if (accidentPartyTypeActionCard.includes("먼저 해 주세요") || accidentPartyTypeActionCard.includes("top_actions")) {
  console.error("accident party card must not duplicate action checklist shown in the three-action card");
  process.exit(1);
}
const expertSource = [
  elderlyActionCard,
  expertGuidanceCard,
  videoFactExplanationCard,
  frameEvidenceCard,
  easyLegalBasisCard,
  easyReportView,
  agentProcessCard,
  styles,
  displaySanitizer,
].join("\n");
const expertScopedSource = [
  elderlyActionCard,
  expertGuidanceCard,
  videoFactExplanationCard,
  frameEvidenceCard,
  easyLegalBasisCard,
  agentProcessCard,
].join("\n");
const requiredExpertTokens = [
  "importance-badge",
  ".action-steps li::before",
  ".expert-panel",
  ".basis-meta",
  ".source-badge.review",
  ".video-fact-stat",
  ".video-fact-section",
  ".video-fact-item",
  ".comparison-row",
  ".basis-card",
  ".legal-paragraphs",
  ".inline-details",
  "sanitizeDisplayText",
];
const missingExpertTokens = requiredExpertTokens.filter((token) => !expertSource.includes(token));
if (missingExpertTokens.length) {
  console.error("expert result UI contract missing", missingExpertTokens);
  process.exit(1);
}
const frameEvidenceContracts = [
  "확인된 영상 프레임 근거",
  "아래 이미지는 모델이 판단에 참고한 선별 프레임입니다",
  "display_allowed",
  "frameImageUrl",
  "image_ref",
  "judgment_reason",
  "event_probability",
  "frame_interpretation_cards",
  "FrameEvidenceCard",
];
const frameEvidenceSource = [frameEvidenceCard, easyReportView].join("\n");
const missingFrameEvidenceContracts = frameEvidenceContracts.filter((token) => !frameEvidenceSource.includes(token));
if (missingFrameEvidenceContracts.length) {
  console.error("frame evidence card display contract missing", missingFrameEvidenceContracts);
  process.exit(1);
}
const forbiddenFrameEvidenceTokens = ["local_cache_path", "raw_prompt", "storage_path"];
const frameEvidenceLeaks = forbiddenFrameEvidenceTokens.filter((token) => frameEvidenceCard.includes(token));
if (frameEvidenceLeaks.length) {
  console.error("frame evidence component exposes internal frame details", frameEvidenceLeaks);
  process.exit(1);
}
const brokenDisplayTokens = ["12?", "? ? ?", ", =9", "=9", "=4"];
const brokenLeaks = brokenDisplayTokens.filter((token) => {
  if (token === "12?") {
    return expertSource.includes("<h3>12?</h3>") || expertSource.includes('"12?"') || expertSource.includes("'12?'");
  }
  return expertSource.includes(token);
});
if (brokenLeaks.length) {
  console.error("broken display placeholder leaked", brokenLeaks);
  process.exit(1);
}
const legacyExpertColors = [
  "#ffffff",
  "#fff",
  "background: white",
  "background-color: white",
  "#f8fafc",
  "#f1f5f9",
  "#e5e7eb",
  "#cbd5e1",
  "#dbeafe",
  "#0f172a",
  "#1e293b",
  "#2dd4bf",
  "#3b82f6",
  "#60efff",
];
const legacyExpertLeaks = legacyExpertColors.filter((token) => expertScopedSource.toLowerCase().includes(token.toLowerCase()));
if (legacyExpertLeaks.length) {
  console.error("legacy expert result colors leaked", legacyExpertLeaks);
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
  "관련 기준을 찾지 못했습니다.",
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
const displayFiles = [apiClient, styles, appView, dashboardView, caseDetailView, caseCreateView, caseWorkspaceHeader, analysisLoadingSpinner, loginView, signupView, routerIndex, sessionStore, resultView, evidenceView, easyReportView, topConclusionCard, relatedVideoCard, kniaVideoLinkCard, kniaFaultRatioBar, evidenceReliabilityCard, videoFactExplanationCard, frameEvidenceCard, kniaRankingView, kniaChartView, kniaJsonSearchBox, displaySanitizer, useCaseWorkspace, caseWorkspaceGuidance, caseWorkspaceGuidanceData, caseWorkspaceFormatters, caseWorkspaceProgress, caseWorkspaceFactMapping, caseWorkspaceOrchestration, caseWorkspacePayloads];
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
  "target=\"_blank\"",
  "rel=\"noopener noreferrer\"",
  "safeSourceUrl || hasKniaCandidate",
  "KNIA 관련 영상 보기",
  "KNIA 원문 기준 보기",
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
const forbiddenKniaNoticeText = [
  "KNIA 원문 기준 및 관련 영상",
  "과실비율정보포털에서 제공하는 유사 사고 기준을 원문 링크로 확인할 수 있습니다.",
  "영상 파일은 LawCompass 서버에 저장하지 않고",
  "자료 출처: 과실비율정보포털",
];
const kniaNoticeLeaks = forbiddenKniaNoticeText.filter((token) => kniaVideoLinkCard.includes(token) || easyReportView.includes(token));
if (kniaNoticeLeaks.length) {
  console.error("user-facing KNIA link copy should stay inside evidence cards without notice text", kniaNoticeLeaks);
  process.exit(1);
}

const brokenKniaSelectors = [
  /(^|,|\s)factor-row\s*\{/m,
  /(^|,|\s)mini-badge\s*\{/m,
  /(^|,|\s)reference-card\s*\{/m,
  /,\s*factor-row\s+\.(factor-source|delta)/m,
  /,\s*factor-row\s*\[/m,
];
const brokenKniaSelectorHits = brokenKniaSelectors.filter((pattern) => pattern.test(kniaChartView));
if (brokenKniaSelectorHits.length) {
  console.error("KNIA chart view has class selectors missing dot", brokenKniaSelectorHits.map(String));
  process.exit(1);
}

const requiredKniaUiTokens = [
  "knia-tabs",
  "factor-table",
  "KniaFaultRatioBar",
  "knia-fault-ratio-track",
  "knia-fault-ratio-segment",
  "knia-fault-ratio-a",
  "knia-fault-ratio-b",
  "knia-fault-ratio-readout",
  "factor-mobile-meta",
  "factor-state",
  "factor-row.selected",
  "font-variant-numeric: tabular-nums",
  "transition:",
];
const kniaRatioSource = [kniaChartView, kniaFaultRatioBar, styles].join("\n");
const missingKniaUiTokens = requiredKniaUiTokens.filter((token) => !kniaRatioSource.includes(token));
if (missingKniaUiTokens.length) {
  console.error("KNIA chart mobile UI contract missing", missingKniaUiTokens);
  process.exit(1);
}

const ratioBarContracts = [
  ":style=\"{ flexBasis:",
  "min-width: 0",
  "height: 56px",
  "fallbackText",
  "normalizeRatioPair",
];
const missingRatioBarContracts = ratioBarContracts.filter((token) => !kniaFaultRatioBar.includes(token));
if (missingRatioBarContracts.length) {
  console.error("KNIA fault ratio bar contract missing", missingRatioBarContracts);
  process.exit(1);
}

const stableRatioContracts = [
  ".fault-ratio-value",
  ".ratio-percent",
  ".knia-percent",
  ".easy-ratio-row span",
  ".user-adjustment-row",
  "min-width: 4.5ch",
  "font-feature-settings: \"tnum\"",
];
const missingStableRatioContracts = stableRatioContracts.filter((token) => !styles.includes(token));
if (missingStableRatioContracts.length) {
  console.error("fault ratio layout stability contract failed", missingStableRatioContracts);
  process.exit(1);
}

const unstableKniaTransitions = [kniaChartView, kniaFaultRatioBar, styles].join("\n").match(/transition:\s*all\b/g);
if (unstableKniaTransitions?.length) {
  console.error("KNIA/fault ratio UI must not use transition: all");
  process.exit(1);
}

const forbiddenKniaColors = ["#2dd4bf", "#3b82f6", "#60efff", "#67e8f9", "#8dd7ff", "#0a1628", "#050c18"];
const kniaColorLeaks = forbiddenKniaColors.filter((token) => kniaChartView.includes(token) || kniaRankingView.includes(token));
if (kniaColorLeaks.length) {
  console.error("KNIA ranking/chart views still use legacy cyan/blue colors", kniaColorLeaks);
  process.exit(1);
}

const kniaRankingSearchContracts = [
  "관련 기준을 찾지 못했습니다.",
  "검색어를 바꿔 다시 시도해 주세요.",
  "검색 결과를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.",
  "accident_party_label",
  "차대자전거 사고",
];
const missingKniaRankingSearchContracts = kniaRankingSearchContracts.filter((token) => ![kniaRankingView, readFileSync("src/components/knia/KniaRankingCard.vue", "utf8")].some((text) => text.includes(token)));
if (missingKniaRankingSearchContracts.length) {
  console.error("KNIA ranking bicycle search UX contract failed", missingKniaRankingSearchContracts);
  process.exit(1);
}
if (kniaRankingView.includes("요청 처리 중 문제가 발생했습니다.")) {
  console.error("KNIA ranking view must not surface the generic red request failure copy");
  process.exit(1);
}

const forbiddenDashboardKniaSearchCardCopy = [
  "KNIA 기준 검색",
  "기준번호/사고유형 검색",
  "검색순위 화면에서 기준번호나 사고유형명으로 저장된 기준을 찾습니다.",
];
const dashboardKniaSearchCardLeaks = forbiddenDashboardKniaSearchCardCopy.filter((token) => dashboardView.includes(token));
if (dashboardKniaSearchCardLeaks.length || !dashboardView.includes("많이 검색된 사고유형")) {
  console.error("dashboard must keep only the popular KNIA ranking entry card", dashboardKniaSearchCardLeaks);
  process.exit(1);
}

const userFriendlyKniaContracts = [
  "관련 KNIA 근거 및 영상",
  "simple_report?.knia_and_video?.primary",
  "KniaDetailEvidenceCard",
  "api.getKniaChart",
  "dedupeSituationLines",
  "KNIA 관련 영상 보기",
  "KNIA 원문 기준 보기",
  "simpleKniaPartyLabel",
  "차대차 사고",
];
const missingUserFriendlyKnia = userFriendlyKniaContracts.filter((token) => !easyReportView.includes(token) && !kniaVideoLinkCard.includes(token) && !kniaDetailEvidenceCard.includes(token));
if (missingUserFriendlyKnia.length) {
  console.error("user-friendly KNIA display contract failed", missingUserFriendlyKnia);
  process.exit(1);
}

const guidedFlowContracts = [
  "guidedAccidentMajorCategoryOptions",
  "guidedAccidentSubtypeOptions",
  "selectAccidentMajorCategory",
  "selectAccidentSubtype",
  "initial_intake",
  "natural_language_policy",
  "source_type: \"subjective_user_claim\"",
  "can_override_video: false",
  "can_override_structured_followup: false",
  "사고의 큰 유형을 먼저 선택해 주세요",
  "영상은 사고 판단의 핵심 근거",
  "추가 설명은 선택 사항입니다",
  "설명은 참고 자료로만 사용",
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

const videoFirstFlowContracts = [
  "car_vs_two_wheeler",
  "highway",
  "parking_or_stationary",
  "getGuidedAccidentSubtypeOptions",
  "guidedAccidentSubtypeOptionsByMajorCategory",
  "buildInitialIntakePayload",
  "initial_accident_major_category",
  "initial_preliminary_accident_type",
];
const missingVideoFirstFlowContracts = videoFirstFlowContracts.filter((token) => !displayFiles.some((text) => text.includes(token)));
if (missingVideoFirstFlowContracts.length) {
  console.error("video-first intake contract failed", missingVideoFirstFlowContracts);
  process.exit(1);
}

const kniaFiveCategoryQuestionContracts = [
  "고속도로 사고",
  "합류도로 사고",
  "차로 감소도로 사고",
  "갓길 진로 변경 사고",
  "마주보는 방향 진행차량 사고",
  "같은 방향 진행차량 사고",
  "기타 유형 사고(주차장·회전교차로 등)",
  "횡단보도 내(신호등 있음)",
  "횡단보도 부근(신호등 있음)",
  "횡단시설 부근(신호등 없음)",
  "횡단보도 없음",
  "자동차 대 이륜차 특수유형",
  "직진 대(對) 직진 사고",
  "직진 대(對) 좌회전 사고(맞은편)",
  "삼거리(T자형) 교차로 사고",
  "차대자전거",
  "자전거 사고유형",
  "bicycle_opposite_direction_collision",
  "highwayGuidedQuestions",
  "motorcycleGuidedQuestions",
  "vehicleProgressGuidedQuestions",
];
const missingKniaFiveCategoryQuestions = kniaFiveCategoryQuestionContracts.filter((token) => !caseWorkspaceGuidanceData.includes(token));
if (missingKniaFiveCategoryQuestions.length) {
  console.error("KNIA myaccident1-5 guided question coverage failed", missingKniaFiveCategoryQuestions);
  process.exit(1);
}

const authStabilityContracts = [
  "bootstrapPromise",
  "refreshPromise",
  "credentials: \"include\"",
  "retryAuth",
  "AUTH_USER_EVENT",
  "await session.bootstrap",
  "authStatus === \"unknown\"",
];
const missingAuthStability = authStabilityContracts.filter((token) => !displayFiles.some((text) => text.includes(token)));
if (missingAuthStability.length) {
  console.error("auth session stability contract failed", missingAuthStability);
  process.exit(1);
}

const guidedQuestionNavigationContracts = [
  "activeGuidedQuestionSetKey",
  "firstUnansweredQuestionIndex",
  "nextUnansweredQuestionIndexAfter",
  "visibleGuidedQuestions",
  "currentGuidedQuestionIndex",
];
const missingQuestionNavigation = guidedQuestionNavigationContracts.filter((token) => !useCaseWorkspace.includes(token));
if (missingQuestionNavigation.length) {
  console.error("guided question navigation contract failed", missingQuestionNavigation);
  process.exit(1);
}

const collisionTargetIndex = caseWorkspaceGuidanceData.indexOf("충돌한 대상은 주차 또는 정차된 차량이었나요?");
const locationIndex = caseWorkspaceGuidanceData.indexOf("상대 차량은 정상 주차구역이 아닌 위험한 위치에 있었나요?");
if (collisionTargetIndex < 0 || locationIndex < 0 || collisionTargetIndex > locationIndex) {
  console.error("stealth parked vehicle flow must ask collision target before opponent vehicle location");
  process.exit(1);
}

const spinnerContracts = [
  "analysis-loading-spinner",
  "analysis-loading-text",
  "analysis-loading-title",
  "analysis-loading-message",
  "spinner-orb",
  "--progress",
  "safePercent",
  "prefers-reduced-motion",
  "AnalysisLoadingSpinner",
];
const missingSpinnerContracts = spinnerContracts.filter((token) => !analysisLoadingSpinner.includes(token) && !caseDetailView.includes(token));
if (missingSpinnerContracts.length) {
  console.error("analysis loading spinner contract failed", missingSpinnerContracts);
  process.exit(1);
}

const agentProcessContracts = [
  ".agent-process-card",
  ".process-stat",
  ".process-step",
  "overflow-wrap: anywhere",
  "rgba(201, 169, 98",
  "grid-template-columns: repeat(auto-fit",
];
const missingAgentProcessContracts = agentProcessContracts.filter((token) => !agentProcessCard.includes(token));
if (missingAgentProcessContracts.length) {
  console.error("agent process diagnostics card contract failed", missingAgentProcessContracts);
  process.exit(1);
}

if (caseCreateView.includes("<select v-model=\"analysisMode\"")) {
  console.error("analysis mode dropdown must not appear on the first create screen");
  process.exit(1);
}
const instantVideoCaseContracts = [
  "영상부터 바로 시작합니다",
  "createImmediately",
  "router.replace(`/cases/${data.case.id}/wizard?start=video`)",
  "DEFAULT_TITLE",
  "initialGuidedStepFromRoute",
  "route.query.start",
  "영상을 먼저 선택하거나 사고 설명을 입력해 주세요",
];
const instantVideoCaseSource = [caseCreateView, useCaseWorkspace].join("\n");
const missingInstantVideoCaseContracts = instantVideoCaseContracts.filter((token) => !instantVideoCaseSource.includes(token));
if (missingInstantVideoCaseContracts.length) {
  console.error("new case flow must create immediately and start on video input", missingInstantVideoCaseContracts);
  process.exit(1);
}
if (caseCreateView.includes("<input v-model=\"title\"") || caseCreateView.includes("<textarea v-model=\"description\"")) {
  console.error("new case create screen must not ask for title or description before video input");
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
