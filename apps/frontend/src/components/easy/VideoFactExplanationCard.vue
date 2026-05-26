<template>
  <article v-if="card" class="card easy-card wide-card video-fact-card">
    <div class="video-fact-header">
      <div>
        <p class="kv">영상 사실 반영</p>
        <h2>{{ text(card.title || "영상 기반 사실 반영") }}</h2>
      </div>
    </div>
    <p class="big-text">{{ text(card.summary) }}</p>

    <div class="video-fact-stats">
      <div v-for="item in card.stats || []" :key="`${item.label}-${item.value}`" class="video-fact-stat">
        <span>{{ text(item.label) }}</span>
        <strong>{{ text(item.value) }}</strong>
      </div>
    </div>

    <section v-if="card.event_candidate" class="video-fact-section event-section">
      <div>
        <span class="item-label">{{ text(card.event_candidate.label) }}</span>
        <strong>{{ text(card.event_candidate.status_label) }}</strong>
      </div>
      <p>{{ text(card.event_candidate.explanation) }}</p>
      <div class="chips compact">
        <span class="chip selected">{{ text(card.event_candidate.frame_label) }}</span>
        <span v-if="card.event_candidate.pre_impact_frame_count" class="chip">
          충돌 전 {{ card.event_candidate.pre_impact_frame_count }}장
        </span>
        <span v-if="card.event_candidate.post_impact_frame_count" class="chip">
          충돌 후 {{ card.event_candidate.post_impact_frame_count }}장
        </span>
      </div>
    </section>

    <section v-if="card.quality_summary" class="video-fact-section quality-section">
      <div class="quality-head">
        <div>
          <span class="item-label">영상 관찰값 상태</span>
          <strong>{{ text(card.quality_summary.status_label) }}</strong>
        </div>
        <div class="chips compact">
          <span class="chip selected">분석 반영 {{ card.quality_summary.accepted_count || 0 }}개</span>
          <span class="chip">확인 필요 {{ (card.quality_summary.uncertain_count || 0) + (card.quality_summary.ignored_count || 0) }}개</span>
          <span v-if="card.quality_summary.supporting_count" class="chip">참고 {{ card.quality_summary.supporting_count }}개</span>
          <span class="chip">복수 프레임 {{ card.quality_summary.multi_frame_count || 0 }}개</span>
        </div>
      </div>
      <ul v-if="card.quality_summary.notes?.length" class="check-list">
        <li v-for="note in card.quality_summary.notes" :key="note">{{ text(note) }}</li>
      </ul>
      <div v-if="card.quality_summary.hold_items?.length" class="reason-grid">
        <span
          v-for="reason in card.quality_summary.hold_items"
          :key="`${reason.label}-${reason.count}`"
          class="chip"
        >
          {{ text(reason.label) }} {{ reason.count }}개
        </span>
      </div>
      <div v-if="card.quality_summary.recovery_actions?.length" class="recovery-list">
        <div
          v-for="action in card.quality_summary.recovery_actions"
          :key="action.label"
          class="recovery-item"
        >
          <span class="item-label">{{ text(action.label) }}</span>
          <p>{{ text(action.reason) }}</p>
        </div>
      </div>
    </section>

    <section v-if="card.applied_items?.length" class="video-fact-section">
      <h3>판단에 반영한 영상 사실</h3>
      <div class="video-fact-list">
        <div v-for="item in card.applied_items" :key="`${item.label}-${item.value}`" class="video-fact-item">
          <span class="item-label">{{ text(item.label) }}</span>
          <strong>{{ text(item.value) }}</strong>
          <p>{{ text(item.explanation) }}</p>
          <div class="chips compact">
            <span class="chip selected">신뢰도 {{ text(item.confidence) }}</span>
            <span v-if="item.frame_label" class="chip">{{ text(item.frame_label) }}</span>
          </div>
        </div>
      </div>
    </section>

    <section v-if="card.confirmed_items?.length" class="video-fact-section">
      <h3>기존 입력과 일치한 영상 사실</h3>
      <div class="video-fact-list">
        <div v-for="item in card.confirmed_items" :key="`${item.label}-${item.value}`" class="video-fact-item">
          <span class="item-label">{{ text(item.label) }}</span>
          <strong>{{ text(item.value) }}</strong>
          <p>{{ text(item.explanation) }}</p>
          <div class="chips compact">
            <span class="chip selected">영상 확인</span>
            <span v-if="item.confidence" class="chip">신뢰도 {{ text(item.confidence) }}</span>
            <span v-if="item.frame_label" class="chip">{{ text(item.frame_label) }}</span>
          </div>
        </div>
      </div>
    </section>

    <section v-if="card.review_items?.length" class="video-fact-section">
      <h3>사용자 입력과 비교가 필요한 항목</h3>
      <div class="video-fact-list">
        <div v-for="item in card.review_items" :key="`${item.label}-${item.selected_source}`" class="video-fact-item">
          <span class="item-label">{{ text(item.label) }}</span>
          <strong>{{ text(item.selected_source) }} 기준: {{ text(item.selected_value) }}</strong>
          <div v-if="item.input_label || item.video_label" class="comparison-row">
            <span>입력 {{ text(item.input_label) }}</span>
            <span>영상 {{ text(item.video_label) }}</span>
          </div>
          <p v-if="item.comparison">{{ text(item.comparison) }}</p>
          <p>{{ text(item.explanation) }}</p>
          <div class="chips compact">
            <span v-if="item.status_label" class="chip selected">{{ text(item.status_label) }}</span>
            <span v-if="item.confidence" class="chip">영상 신뢰도 {{ text(item.confidence) }}</span>
            <span v-if="item.frame_label" class="chip">{{ text(item.frame_label) }}</span>
          </div>
        </div>
      </div>
    </section>

    <section v-if="card.uncertain_items?.length" class="video-fact-section">
      <h3>확인이 필요한 영상 관찰값</h3>
      <ul class="check-list">
        <li v-for="item in card.uncertain_items" :key="item.label">
          {{ text(item.label) }} · 신뢰도 {{ text(item.confidence) }} · {{ text(item.explanation) }}
        </li>
      </ul>
    </section>

    <section v-if="card.supporting_items?.length" class="video-fact-section">
      <h3>참고로만 보는 영상 관찰</h3>
      <div class="video-fact-list">
        <div v-for="item in card.supporting_items" :key="`${item.label}-${item.value}`" class="video-fact-item">
          <span class="item-label">{{ text(item.label) }}</span>
          <strong>{{ text(item.value) }}</strong>
          <p>{{ text(item.explanation) }}</p>
          <div class="chips compact">
            <span v-if="item.confidence" class="chip">영상 신뢰도 {{ text(item.confidence) }}</span>
          </div>
        </div>
      </div>
    </section>

    <p v-if="card.notice" class="kv">{{ text(card.notice) }}</p>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { sanitizeDisplayText } from "../../utils/displaySanitizer";

const props = defineProps<{ card?: any }>();
const card = computed(() => props.card);

function text(value: unknown) {
  return sanitizeDisplayText(value);
}
</script>

<style scoped>
.video-fact-card {
  display: grid;
  gap: 18px;
}

.video-fact-header {
  align-items: flex-start;
  display: flex;
  gap: 16px;
  justify-content: space-between;
}

.video-fact-stats {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
}

.video-fact-stat,
.video-fact-item {
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 12px;
  min-width: 0;
  padding: 14px;
}

.video-fact-stat span,
.item-label {
  color: #76e4ef;
  display: block;
  font-size: 0.9rem;
  font-weight: 800;
}

.video-fact-stat strong,
.video-fact-item strong {
  color: #f1f7ff;
  display: block;
  margin-top: 6px;
}

.video-fact-section {
  display: grid;
  gap: 12px;
}

.video-fact-list {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.video-fact-item p {
  color: #c5d0df;
  margin: 10px 0 0;
}

.comparison-row {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: 12px;
}

.comparison-row span {
  background: rgba(255, 255, 255, 0.055);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 10px;
  color: #edf6ff;
  font-weight: 800;
  min-width: 0;
  overflow-wrap: anywhere;
  padding: 10px 12px;
}

.quality-section {
  background: rgba(76, 213, 226, 0.08);
  border: 1px solid rgba(76, 213, 226, 0.22);
  border-radius: 12px;
  padding: 14px;
}

.event-section {
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(76, 213, 226, 0.22);
  border-radius: 12px;
  padding: 14px;
}

.event-section p {
  color: #c5d0df;
  margin: 8px 0 0;
}

.quality-head {
  align-items: flex-start;
  display: flex;
  gap: 14px;
  justify-content: space-between;
}

.quality-head strong {
  color: #f1f7ff;
  display: block;
  margin-top: 6px;
}

.reason-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.recovery-list {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.recovery-item {
  background: rgba(255, 221, 119, 0.08);
  border: 1px solid rgba(255, 221, 119, 0.22);
  border-radius: 10px;
  padding: 12px;
}

.recovery-item p {
  color: #d7dfeb;
  margin: 8px 0 0;
}

.compact {
  margin-top: 12px;
}

@media (max-width: 760px) {
  .video-fact-stats,
  .video-fact-list,
  .comparison-row {
    grid-template-columns: 1fr;
  }

  .quality-head {
    display: grid;
  }
}
</style>
