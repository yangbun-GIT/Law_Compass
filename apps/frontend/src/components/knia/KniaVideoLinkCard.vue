<script setup lang="ts">
import { computed } from "vue";

type AnyRecord = Record<string, any>;

const props = defineProps<{
  video?: AnyRecord | null;
  card?: AnyRecord | null;
}>();

const MISSING_KNIA_SOURCE_NOTICE = "수집된 KNIA 원문 링크가 없습니다. 관리자 KNIA 상세 수집을 먼저 실행해 주세요.";
const KNIA_SOURCE_LINK_NOTICE = "영상 파일은 LawCompass 서버에 저장하지 않고, 과실비율정보포털 원본 링크로만 제공합니다.";
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
const hasKniaCandidate = computed(() => Boolean(video.value.has_knia_candidate || video.value.chart_no || video.value.chart_title || video.value.title));
const missingNotice = computed(() => (!safeSourceUrl.value && hasKniaCandidate.value)
  ? (video.value.missing_source_notice || MISSING_KNIA_SOURCE_NOTICE)
  : "");
const notice = computed(() => safeSourceUrl.value ? (video.value.notice || KNIA_SOURCE_LINK_NOTICE) : "");
const sourceLabel = computed(() => video.value.source_label || video.value.attribution || "자료 출처: 과실비율정보포털");
</script>

<template>
  <article v-if="safeSourceUrl || video.has_knia_candidate" class="card easy-card knia-card knia-link-card">
    <p class="eyebrow">과실비율정보포털 기준</p>
    <h2>{{ video.title || "KNIA 원문 기준 및 관련 영상" }}</h2>
    <p class="muted">
      {{ video.description || "과실비율정보포털에서 제공하는 유사 사고 기준을 원문 링크로 확인할 수 있습니다." }}
    </p>

    <div v-if="video.chart_no || video.chart_title" class="chips">
      <span v-if="video.chart_no" class="chip selected">기준번호 {{ video.chart_no }}</span>
      <span v-if="video.chart_title" class="chip">{{ video.chart_title }}</span>
    </div>

    <div v-if="safeSourceUrl" class="btn-row">
      <a
        class="btn primary"
        :href="safeSourceUrl"
        target="_blank"
        rel="noopener noreferrer"
      >
        {{ video.button_label || buttonLabel }}
      </a>
    </div>

    <p v-else-if="missingNotice" class="soft-warning">
      {{ missingNotice }}
    </p>

    <p v-if="notice" class="soft-warning">
      {{ notice }}
    </p>
    <p class="source-label">{{ sourceLabel }}</p>
  </article>
</template>
