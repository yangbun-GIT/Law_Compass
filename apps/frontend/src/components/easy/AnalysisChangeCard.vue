<template>
  <article class="card easy-card analysis-change-card" v-if="card">
    <div class="analysis-change-head">
      <div>
        <p class="eyebrow">재분석 비교</p>
        <h2>{{ text(card.title || "보완 입력 반영 결과") }}</h2>
      </div>
    </div>
    <p class="big-text">{{ text(card.summary) }}</p>
    <div class="change-stats">
      <div v-for="item in card.stats || []" :key="`${item.label}-${item.value}`">
        <span>{{ text(item.value) }}</span>
        <p>{{ text(item.label) }}</p>
      </div>
    </div>
    <div v-if="card.changes?.length" class="change-list">
      <div v-for="item in card.changes" :key="`${item.label}-${item.before}-${item.after}`" class="change-row">
        <strong>{{ text(item.label) }}</strong>
        <p><span>{{ text(item.before) }}</span><b>→</b><span>{{ text(item.after) }}</span></p>
      </div>
    </div>
    <p v-else class="kv">핵심 판단 항목은 이전 분석과 크게 달라지지 않았습니다.</p>
    <p class="soft-warning">{{ text(card.notice) }}</p>
  </article>
</template>

<script setup lang="ts">
import { sanitizeDisplayText } from "../../utils/displaySanitizer";

defineProps<{ card: any }>();

function text(value: unknown) {
  return sanitizeDisplayText(value);
}
</script>

<style scoped>
.analysis-change-card {
  display: grid;
  gap: 14px;
}

.analysis-change-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.change-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.change-stats div,
.change-row {
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.32);
  padding: 12px;
}

.change-stats span {
  display: block;
  color: #67e8f9;
  font-size: 1.35rem;
  font-weight: 900;
  line-height: 1.1;
}

.change-stats p,
.change-row p {
  margin: 6px 0 0;
}

.change-list {
  display: grid;
  gap: 10px;
}

.change-row strong {
  color: #e5f7ff;
}

.change-row p {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.change-row b {
  color: #67e8f9;
}

@media (max-width: 900px) {
  .change-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .change-stats {
    grid-template-columns: 1fr;
  }
}
</style>
