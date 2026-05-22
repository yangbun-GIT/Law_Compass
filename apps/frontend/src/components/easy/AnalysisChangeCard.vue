<template>
  <article class="card easy-card analysis-change-card" v-if="card">
    <div class="analysis-change-head">
      <div>
        <p class="eyebrow">재분석 비교</p>
        <h2>{{ text(card.title || "보완 입력 반영 결과") }}</h2>
      </div>
    </div>
    <p class="big-text">{{ text(card.summary) }}</p>
    <div v-if="card.status_label" class="status-strip">
      <span>재분석 상태</span>
      <strong>{{ text(card.status_label) }}</strong>
    </div>
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
    <section v-if="card.answer_items?.length" class="answer-result-section">
      <h3>보완 답변 처리 결과</h3>
      <div class="answer-result-grid">
        <div v-for="item in card.answer_items" :key="`${item.label}-${item.status_label}`" class="answer-result-item">
          <span>{{ text(item.status_label) }}</span>
          <strong>{{ text(item.label) }}</strong>
          <p>{{ text(item.explanation) }}</p>
        </div>
      </div>
    </section>
    <section v-if="card.decision_notes?.length" class="change-note-section">
      <h3>판단 변화 요약</h3>
      <ul class="check-list">
        <li v-for="note in card.decision_notes" :key="note">{{ text(note) }}</li>
      </ul>
    </section>
    <ul v-if="card.evidence_notes?.length" class="check-list">
      <li v-for="note in card.evidence_notes" :key="note">{{ text(note) }}</li>
    </ul>
    <div v-if="hasEvidenceChanges" class="evidence-diff-grid">
      <section v-if="card.evidence_changes?.added?.length" class="evidence-diff">
        <h3>새로 반영된 근거</h3>
        <div v-for="item in card.evidence_changes.added" :key="`${item.title}-${item.source_label}`" class="evidence-diff-item">
          <span>{{ text(item.family_label) }}</span>
          <strong>{{ text(item.title) }}</strong>
          <p>{{ text(item.source_label) }}</p>
        </div>
      </section>
      <section v-if="card.evidence_changes?.removed?.length" class="evidence-diff">
        <h3>이번 결과에서 빠진 근거</h3>
        <div v-for="item in card.evidence_changes.removed" :key="`${item.title}-${item.source_label}`" class="evidence-diff-item">
          <span>{{ text(item.family_label) }}</span>
          <strong>{{ text(item.title) }}</strong>
          <p>{{ text(item.source_label) }}</p>
        </div>
      </section>
    </div>
    <p class="soft-warning">{{ text(card.notice) }}</p>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { sanitizeDisplayText } from "../../utils/displaySanitizer";

const props = defineProps<{ card: any }>();

const hasEvidenceChanges = computed(() =>
  Boolean(props.card?.evidence_changes?.added?.length || props.card?.evidence_changes?.removed?.length)
);

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
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
}

.status-strip {
  align-items: center;
  background: rgba(103, 232, 249, 0.1);
  border: 1px solid rgba(103, 232, 249, 0.28);
  border-radius: 8px;
  display: flex;
  gap: 10px;
  justify-content: space-between;
  padding: 12px 14px;
}

.status-strip span {
  color: #b7c8d9;
  font-size: 0.9rem;
  font-weight: 800;
}

.status-strip strong {
  color: #f1f7ff;
  overflow-wrap: anywhere;
}

.change-stats div,
.change-row,
.answer-result-item {
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.32);
  padding: 12px;
}

.change-stats span {
  display: block;
  color: #67e8f9;
  font-size: 1.1rem;
  font-weight: 900;
  line-height: 1.1;
  overflow-wrap: anywhere;
}

.change-stats p,
.change-row p {
  margin: 6px 0 0;
}

.change-list {
  display: grid;
  gap: 10px;
}

.change-note-section {
  display: grid;
  gap: 8px;
}

.answer-result-section {
  display: grid;
  gap: 10px;
}

.answer-result-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.answer-result-item {
  display: grid;
  gap: 6px;
}

.answer-result-item span {
  color: #67e8f9;
  font-size: 0.85rem;
  font-weight: 900;
}

.answer-result-item strong,
.answer-result-item p {
  margin: 0;
  overflow-wrap: anywhere;
}

.answer-result-item p {
  color: #cbd5e1;
}

.change-note-section h3,
.answer-result-section h3 {
  margin: 0;
}

.change-row strong {
  color: #e5f7ff;
}

.change-row p {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  overflow-wrap: anywhere;
}

.change-row b {
  color: #67e8f9;
}

.evidence-diff-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.evidence-diff {
  display: grid;
  align-content: start;
  gap: 10px;
  min-width: 0;
}

.evidence-diff h3 {
  margin: 0;
}

.evidence-diff-item {
  display: grid;
  gap: 5px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.28);
  padding: 12px;
}

.evidence-diff-item span {
  color: #67e8f9;
  font-size: 0.82rem;
  font-weight: 900;
}

.evidence-diff-item strong,
.evidence-diff-item p {
  margin: 0;
  overflow-wrap: anywhere;
}

.evidence-diff-item p {
  color: #cbd5e1;
}

@media (max-width: 760px) {
  .evidence-diff-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .change-stats {
    grid-template-columns: 1fr;
  }
}
</style>
