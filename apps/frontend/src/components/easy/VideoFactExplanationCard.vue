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

    <section v-if="card.applied_items?.length" class="video-fact-section">
      <h3>판단에 반영된 영상 사실</h3>
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

    <section v-if="card.review_items?.length" class="video-fact-section">
      <h3>사용자 입력과 비교한 항목</h3>
      <div class="video-fact-list">
        <div v-for="item in card.review_items" :key="`${item.label}-${item.selected_source}`" class="video-fact-item">
          <span class="item-label">{{ text(item.label) }}</span>
          <strong>{{ text(item.selected_source) }} 기준: {{ text(item.selected_value) }}</strong>
          <p>{{ text(item.explanation) }}</p>
        </div>
      </div>
    </section>

    <section v-if="card.uncertain_items?.length" class="video-fact-section">
      <h3>보류된 영상 관찰값</h3>
      <ul class="check-list">
        <li v-for="item in card.uncertain_items" :key="item.label">
          {{ text(item.label) }} · 신뢰도 {{ text(item.confidence) }} · {{ text(item.explanation) }}
        </li>
      </ul>
    </section>

    <p class="soft-warning">{{ text(card.notice) }}</p>
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
  grid-template-columns: repeat(4, minmax(0, 1fr));
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

.compact {
  margin-top: 12px;
}

@media (max-width: 760px) {
  .video-fact-stats,
  .video-fact-list {
    grid-template-columns: 1fr;
  }
}
</style>
