<script setup lang="ts">
import { computed } from "vue";
import { sanitizeDisplayText } from "../../utils/displaySanitizer";

type AnyRecord = Record<string, any>;

const props = defineProps<{
  video?: AnyRecord | null;
  card?: AnyRecord | null;
}>();

const MISSING_KNIA_SOURCE_NOTICE = "상세 기준 수집 필요: 수집된 KNIA 원문 링크가 없습니다. 차트번호와 기준명을 먼저 참고해 주세요.";
const KNIA_SOURCE_LINK_NOTICE = "영상 파일은 LawCompass 서버에 저장하지 않고, 과실비율정보포털 원본 링크로만 제공합니다.";
const KNIA_ALLOWED_HOST = "accident.knia.or.kr";

const video = computed<AnyRecord>(() => props.card ?? props.video ?? {});

function text(value: unknown, fallback = "") {
  return sanitizeDisplayText(value, fallback);
}

function safeKniaUrl(value: unknown): string {
  const raw = String(value ?? "").trim();
  if (!raw || /\s/.test(raw) || !/^https?:\/\//i.test(raw)) return "";
  try {
    const url = new URL(raw);
    if (url.hostname.toLowerCase() !== KNIA_ALLOWED_HOST) return "";
    if (url.username || url.password) return "";
    return url.toString();
  } catch {
    return "";
  }
}

function isVideoUrl(value: string): boolean {
  return /\.(mp4|mov|m4v|webm)(?:$|\?)/i.test(value);
}

const safeVideoUrl = computed(() => {
  const directVideo = safeKniaUrl(video.value.video_url);
  if (directVideo) return directVideo;
  const source = safeKniaUrl(video.value.source_url);
  return source && isVideoUrl(source) ? source : "";
});

const safeSourcePageUrl = computed(() => (
  safeKniaUrl(video.value.source_detail_url)
  || safeKniaUrl(video.value.source_page_url)
  || (!isVideoUrl(safeKniaUrl(video.value.source_url)) ? safeKniaUrl(video.value.source_url) : "")
));

const safeSourceUrl = computed(() => safeVideoUrl.value || safeSourcePageUrl.value || safeKniaUrl(video.value.button_url));
const buttonLabel = computed(() => safeVideoUrl.value ? "KNIA 관련 영상 보기" : "KNIA 원문 기준 보기");
const hasKniaCandidate = computed(() => Boolean(video.value.has_knia_candidate || video.value.chart_no || video.value.chart_title || video.value.title));
const missingNotice = computed(() => (!safeSourceUrl.value && hasKniaCandidate.value)
  ? text(video.value.missing_source_notice, MISSING_KNIA_SOURCE_NOTICE)
  : "");
const notice = computed(() => safeSourceUrl.value ? text(video.value.notice, KNIA_SOURCE_LINK_NOTICE) : "");
const sourceLabel = computed(() => text(video.value.source_label || video.value.attribution, "자료 출처: 과실비율정보포털"));
const menuPathText = computed(() => Array.isArray(video.value.menu_path)
  ? video.value.menu_path.map((item: unknown) => text(item)).filter(Boolean).join(" > ")
  : "");

function faultText(value: any): string {
  if (!value) return "";
  if (typeof value === "string" || typeof value === "number") return text(value);
  if (typeof value !== "object") return "";
  const my = value.my ?? value.A ?? value.user ?? value.ego ?? value.driver;
  const other = value.other ?? value.B ?? value.opponent ?? value.counterparty;
  if (my !== undefined && other !== undefined) return `${my}:${other}`;
  const min = value.min ?? value.minimum;
  const max = value.max ?? value.maximum;
  if (min !== undefined && max !== undefined) return `${min}~${max}`;
  return text(value.label || value.summary || "");
}
</script>

<template>
  <article v-if="safeSourceUrl || video.has_knia_candidate" class="card easy-card knia-card knia-link-card">
    <p class="eyebrow">과실비율정보포털 기준</p>
    <h2>{{ text(video.title || video.chart_title, "KNIA 원문 기준 및 관련 영상") }}</h2>
    <p class="muted">
      {{ text(video.description, "과실비율정보포털에서 제공하는 유사 사고 기준을 원문 링크로 확인할 수 있습니다.") }}
    </p>

    <div v-if="video.chart_no || video.chart_title" class="chips">
      <span v-if="video.chart_no" class="chip selected">기준번호 {{ text(video.chart_no) }}</span>
      <span v-if="video.subchart_no" class="chip selected">세부 {{ text(video.subchart_no) }}</span>
      <span v-if="video.chart_title" class="chip">{{ text(video.chart_title) }}</span>
    </div>

    <p v-if="menuPathText" class="muted">{{ menuPathText }}</p>

    <div v-if="faultText(video.base_fault) || faultText(video.final_fault) || faultText(video.fault_range)" class="chips">
      <span v-if="faultText(video.base_fault)" class="chip">기준 과실 {{ faultText(video.base_fault) }}</span>
      <span v-if="faultText(video.final_fault)" class="chip selected">수정 과실 {{ faultText(video.final_fault) }}</span>
      <span v-if="faultText(video.fault_range)" class="chip">참고 범위 {{ faultText(video.fault_range) }}</span>
    </div>

    <div v-if="safeSourceUrl" class="btn-row">
      <a class="btn primary" :href="safeSourceUrl" target="_blank" rel="noopener noreferrer">
        {{ text(video.button_label, buttonLabel) }}
      </a>
    </div>

    <p v-else-if="missingNotice" class="soft-warning">{{ missingNotice }}</p>
    <p v-if="notice" class="soft-warning">{{ notice }}</p>
    <p v-if="video.source_url_is_fallback" class="kv">원문 링크 형식은 차트번호 기반으로 생성되었습니다.</p>
    <p class="source-label">{{ sourceLabel }}</p>
  </article>
</template>
