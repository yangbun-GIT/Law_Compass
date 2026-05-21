const forbidden = ["chunk_id", "score", "model_info", "cache_key", "rag_top_k", "ai_profile", "llm_enabled", "orchestrator", "scenario_classifier", "rear_end_collision", "REAR_END_SAFE_DISTANCE", "ROAD_ACCIDENT_REPORTING_DUTY", "???", '"injury":', '"stopped":', '"weather":'];
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
const loginView = readFileSync("src/views/LoginView.vue", "utf8");
const signupView = readFileSync("src/views/SignupView.vue", "utf8");
const resultView = readFileSync("src/views/CaseResultView.vue", "utf8");
const evidenceView = readFileSync("src/views/EvidenceDetailView.vue", "utf8");
const easyReportView = readFileSync("src/components/easy/EasyReportView.vue", "utf8");
const kniaRankingView = readFileSync("src/views/KniaRankingView.vue", "utf8");
const kniaChartView = readFileSync("src/views/KniaChartView.vue", "utf8");
const kniaJsonSearchBox = readFileSync("src/components/knia/KniaJsonSearchBox.vue", "utf8");
const requiredErrorUx = [
  "export function formatApiError",
  "normalizeValidation(data?.error?.details?.validation)",
  "white-space: pre-line",
  "v-if=\"!session.user\"",
  "dashboard-hero",
  "첫 케이스 만들기",
  "Case Workspace",
  "Analysis Result",
  "개발자 전용 원문",
  "법률 근거가 부족합니다",
  "검색 조건에 맞는 기준이 없습니다",
  "상세 기준 수집 필요",
  "상세 기준 수집",
  "검색순위에만 저장",
  "기본과실은 상세 기준 수집 후 표시됩니다",
  "수집 요청은 완료됐지만 상세 기준 본문이 저장되지 않았습니다",
  "KNIA 기준을 불러오지 못했습니다",
  "KNIA JSON 검색에 실패했습니다",
  "autocomplete=\"current-password\"",
  "autocomplete=\"new-password\""
];
const styles = readFileSync("src/styles.css", "utf8");
const displayFiles = [apiClient, styles, appView, dashboardView, caseDetailView, loginView, signupView, resultView, evidenceView, easyReportView, kniaRankingView, kniaChartView, kniaJsonSearchBox];
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

console.log("frontend_display_safety=passed");
