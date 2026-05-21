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
const requiredErrorUx = [
  "export function formatApiError",
  "normalizeValidation(data?.error?.details?.validation)",
  "white-space: pre-line"
];
const styles = readFileSync("src/styles.css", "utf8");
const missingErrorUx = requiredErrorUx.filter((token) => !(apiClient.includes(token) || styles.includes(token)));
if (missingErrorUx.length) {
  console.error("frontend error UX contract failed", missingErrorUx);
  process.exit(1);
}

console.log("frontend_display_safety=passed");
