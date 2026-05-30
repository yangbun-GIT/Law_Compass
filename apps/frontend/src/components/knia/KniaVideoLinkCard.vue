<script setup lang="ts">
import { computed } from "vue";
import { sanitizeDisplayText } from "../../utils/displaySanitizer";

type AnyRecord = Record<string, any>;

const props = defineProps<{
  video?: AnyRecord | null;
  card?: AnyRecord | null;
}>();

const KNIA_ALLOWED_HOST = "accident.knia.or.kr";

const video = computed<AnyRecord>(() => props.card ?? props.video ?? {});

function safeKniaUrl(value: unknown): string {
  const text = String(value ?? "").trim();
  if (!text || /\s/.test(text) || !/^https?:\/\//i.test(text)) return "";
  try {
    const url = new URL(text);
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
const displayButtonLabel = computed(() => {
  const provided = sanitizeDisplayText(video.value.button_label, "");
  return /^KNIA\s+(관련 영상 보기|원문 기준 보기)$/.test(provided) ? provided : buttonLabel.value;
});
const hasKniaCandidate = computed(() => Boolean(video.value.has_knia_candidate || video.value.chart_no || video.value.chart_title || video.value.title));
const title = computed(() => {
  const value = sanitizeDisplayText(video.value.title || video.value.chart_title, "");
  const legacyTitle = ["KNIA 원문 기준", "관련 영상"].join(" 및 ");
  return value && value !== legacyTitle ? value : "";
});

function faultText(value: any): string {
  if (!value) return "";
  if (typeof value === "string" || typeof value === "number") return sanitizeDisplayText(value);
  if (typeof value !== "object") return "";
  const my = value.my ?? value.A ?? value.user ?? value.ego ?? value.driver;
  const other = value.other ?? value.B ?? value.opponent ?? value.counterparty;
  if (my !== undefined && other !== undefined) return `A ${formatPercent(my)} / B ${formatPercent(other)}`;
  const min = value.min ?? value.minimum;
  const max = value.max ?? value.maximum;
  if (min !== undefined && max !== undefined) return `${formatPercent(min)}~${formatPercent(max)}`;
  return sanitizeDisplayText(value.label || value.summary || "");
}

function formatPercent(value: any): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return sanitizeDisplayText(value);
  return `${Math.round(n)}%`;
}
</script>

<template>
  <article v-if="safeSourceUrl || hasKniaCandidate" class="card easy-card knia-card knia-link-card">
    <p class="eyebrow">과실비율정보포털 기준</p>
    <h2 v-if="title">{{ title }}</h2>

    <div v-if="video.chart_no || video.chart_title" class="chips">
      <span v-if="video.chart_no" class="chip selected">기준번호 {{ sanitizeDisplayText(video.chart_no) }}</span>
      <span v-if="video.subchart_no" class="chip selected">세부 {{ sanitizeDisplayText(video.subchart_no) }}</span>
      <span v-if="video.chart_title" class="chip">{{ sanitizeDisplayText(video.chart_title) }}</span>
    </div>

    <p v-if="video.menu_path?.length" class="muted">{{ video.menu_path.map(sanitizeDisplayText).filter(Boolean).join(" > ") }}</p>

    <div v-if="faultText(video.base_fault) || faultText(video.final_fault) || faultText(video.fault_range)" class="chips">
      <span v-if="faultText(video.base_fault)" class="chip">기준 과실 {{ faultText(video.base_fault) }}</span>
      <span v-if="faultText(video.final_fault)" class="chip selected">수정 과실 {{ faultText(video.final_fault) }}</span>
      <span v-if="faultText(video.fault_range)" class="chip">참고 범위 {{ faultText(video.fault_range) }}</span>
    </div>

    <div v-if="safeSourceUrl" class="btn-row">
      <a
        class="btn primary"
        :href="safeSourceUrl"
        target="_blank"
        rel="noopener noreferrer"
      >
        {{ displayButtonLabel }}
      </a>
    </div>
  </article>
</template>
