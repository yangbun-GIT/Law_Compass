<template>
  <article v-if="visibleCards.length" class="card easy-card wide-card frame-evidence-card">
    <p class="eyebrow">확인된 영상 프레임 근거</p>
    <h2>모델이 참고한 선별 프레임</h2>
    <p class="easy-summary">
      아래 이미지는 모델이 판단에 참고한 선별 프레임입니다. 프레임상 명확히 보이는 내용만 표시하며, 보이지 않는 사실은 확정하지 않습니다.
    </p>

    <div class="frame-evidence-grid">
      <article v-for="card in visibleCards" :key="cardKey(card)" class="frame-evidence-item">
        <img
          v-if="frameImageUrl(card)"
          class="frame-evidence-image"
          :src="frameImageUrl(card)"
          :alt="frameAlt(card)"
          loading="lazy"
        />
        <div v-else class="frame-evidence-image is-placeholder" aria-hidden="true">
          FRAME
        </div>
        <div class="frame-evidence-body">
          <div class="frame-evidence-meta">
            <span>{{ timeLabel(card.time_sec) }}</span>
            <span>{{ phaseLabel(card.event_phase) }}</span>
            <span>{{ confidenceLabel(card.confidence) }}</span>
          </div>
          <h3>{{ text(card.interpretation_summary || "선별 프레임에서 확인 가능한 영상 단서를 정리했습니다.") }}</h3>
          <p v-if="card.judgment_reason" class="frame-evidence-reason">
            판단 이유: {{ text(card.judgment_reason) }}
          </p>
          <ul v-if="card.observed_facts?.length" class="frame-fact-list">
            <li v-for="fact in card.observed_facts.slice(0, 4)" :key="`${cardKey(card)}-${fact.field}-${fact.value}`">
              <strong>{{ text(fact.field) }}</strong>
              <span>{{ text(fact.value) }}</span>
            </li>
          </ul>
        </div>
      </article>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { sanitizeDisplayText } from "../../utils/displaySanitizer";

type FrameFact = {
  field?: string;
  value?: string;
  confidence?: number;
  source?: string;
};

type FrameCard = {
  frame_ref?: string;
  time_sec?: number;
  event_phase?: string;
  interpretation_summary?: string;
  judgment_reason?: string;
  observed_facts?: FrameFact[];
  confidence?: number;
  event_probability?: number;
  visibility?: string;
  display_allowed?: boolean;
  image_url?: string;
  image_ref?: {
    case_id?: string;
    upload_id?: string;
    frame_ref?: string;
  };
};

const props = defineProps<{ cards?: FrameCard[] }>();

const visibleCards = computed(() => (props.cards || []).filter((card) => card?.display_allowed === true).slice(0, 6));

function frameImageUrl(card: FrameCard) {
  const explicit = safeFrameUrl(card.image_url);
  if (explicit) return explicit;
  const ref = card.image_ref || {};
  if (!ref.case_id || !ref.upload_id || !ref.frame_ref) return "";
  return `/api/v1/cases/${encodeURIComponent(ref.case_id)}/uploads/${encodeURIComponent(ref.upload_id)}/frames/${encodeURIComponent(ref.frame_ref)}`;
}

function safeFrameUrl(value: unknown) {
  const raw = String(value || "").trim();
  if (!raw || raw.startsWith("file:") || raw.includes("\\") || raw.includes("/app/storage")) return "";
  return raw.startsWith("/api/") ? raw : "";
}

function cardKey(card: FrameCard) {
  return `${card.image_ref?.upload_id || "upload"}-${card.frame_ref || card.image_ref?.frame_ref || card.time_sec || "frame"}`;
}

function timeLabel(value: unknown) {
  const n = Number(value);
  return Number.isFinite(n) ? `${Math.max(0, Math.round(n * 10) / 10)}초` : "선별 프레임";
}

function phaseLabel(value: unknown) {
  return String(value || "") === "event" ? "사고 구간" : "전후 맥락";
}

function confidenceLabel(value: unknown) {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return "확인됨";
  return `신뢰도 ${Math.round(Math.min(1, Math.max(0, n)) * 100)}%`;
}

function frameAlt(card: FrameCard) {
  return `${timeLabel(card.time_sec)} ${phaseLabel(card.event_phase)} 선별 프레임`;
}

function text(value: unknown) {
  return sanitizeDisplayText(value, "");
}
</script>

<style scoped>
.frame-evidence-card {
  display: grid;
  gap: 14px;
}

.frame-evidence-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 14px;
}

.frame-evidence-item {
  display: grid;
  grid-template-rows: auto 1fr;
  min-width: 0;
  overflow: hidden;
  border-radius: 18px;
  border: 1px solid rgba(201, 169, 98, 0.28);
  background: linear-gradient(145deg, rgba(61, 51, 43, 0.92), rgba(37, 30, 25, 0.96));
  color: var(--text-main);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.2);
}

.frame-evidence-image {
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  background: rgba(28, 23, 20, 0.72);
  border-bottom: 1px solid rgba(201, 169, 98, 0.22);
}

.frame-evidence-image.is-placeholder {
  display: grid;
  place-items: center;
  color: var(--text-faint);
  font-weight: 900;
  letter-spacing: 0.08em;
}

.frame-evidence-body {
  display: grid;
  gap: 10px;
  min-width: 0;
  padding: 15px;
}

.frame-evidence-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.frame-evidence-meta span {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 4px 9px;
  border-radius: 999px;
  border: 1px solid rgba(201, 169, 98, 0.28);
  background: rgba(232, 223, 212, 0.08);
  color: var(--text-sub);
  font-size: 0.82rem;
  font-weight: 900;
}

.frame-evidence-body h3 {
  margin: 0;
  color: var(--text-main);
  font-size: 1rem;
  line-height: 1.45;
  font-weight: 900;
  word-break: keep-all;
  overflow-wrap: anywhere;
}

.frame-evidence-reason {
  margin: 0;
  color: var(--text-sub);
  font-size: 0.92rem;
  line-height: 1.55;
  word-break: keep-all;
  overflow-wrap: anywhere;
}

.frame-fact-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.frame-fact-list li {
  display: grid;
  gap: 3px;
  min-width: 0;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(201, 169, 98, 0.18);
  background: rgba(28, 23, 20, 0.36);
}

.frame-fact-list strong {
  color: var(--accent-strong);
  font-size: 0.86rem;
}

.frame-fact-list span {
  color: var(--text-sub);
  line-height: 1.5;
  word-break: keep-all;
  overflow-wrap: anywhere;
}

@media (max-width: 640px) {
  .frame-evidence-grid {
    grid-template-columns: 1fr;
  }

  .frame-evidence-body {
    padding: 13px;
  }
}
</style>
