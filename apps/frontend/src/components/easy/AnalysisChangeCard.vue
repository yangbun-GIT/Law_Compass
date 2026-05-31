<template>
  <article class="card easy-card analysis-change-card" v-if="card">
    <div class="analysis-change-head">
      <div>
        <p class="eyebrow">분석 비교</p>
        <h2>{{ text(card.title, "보완 입력 반영 결과") }}</h2>
      </div>
    </div>
    <p class="big-text">{{ text(card.summary, "추가 답변이 기존 분석에 어떤 영향을 주었는지 정리했습니다.") }}</p>
    <div v-if="card.status_label" class="status-strip">
      <span>분석 상태</span>
      <strong>{{ text(card.status_label) }}</strong>
    </div>
    <div v-if="card.stats?.length" class="change-stats">
      <div v-for="item in card.stats" :key="`${item.label}-${item.value}`">
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
        <h3>새로 반영한 근거</h3>
        <div v-for="item in card.evidence_changes.added" :key="`${item.title}-${item.source_label}`" class="evidence-diff-item">
          <span>{{ text(item.family_label) }}</span>
          <strong>{{ text(item.title) }}</strong>
          <p>{{ text(item.source_label) }}</p>
        </div>
      </section>
      <section v-if="card.evidence_changes?.removed?.length" class="evidence-diff">
        <h3>이번 결과에서 제외한 근거</h3>
        <div v-for="item in card.evidence_changes.removed" :key="`${item.title}-${item.source_label}`" class="evidence-diff-item">
          <span>{{ text(item.family_label) }}</span>
          <strong>{{ text(item.title) }}</strong>
          <p>{{ text(item.source_label) }}</p>
        </div>
      </section>
    </div>
    <p v-if="card.notice" class="kv">{{ text(card.notice) }}</p>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { sanitizeDisplayText } from "../../utils/displaySanitizer";

const props = defineProps<{ card: any }>();

const hasEvidenceChanges = computed(() =>
  Boolean(props.card?.evidence_changes?.added?.length || props.card?.evidence_changes?.removed?.length)
);

function text(value: unknown, fallback = "") {
  return sanitizeDisplayText(value, fallback);
}
</script>

<style scoped>
.analysis-change-card,
.change-list,
.change-note-section,
.answer-result-section,
.evidence-diff,
.answer-result-item,
.evidence-diff-item {
  display: grid;
  gap: 10px;
}

.analysis-change-head {
  align-items: flex-start;
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

.change-stats,
.answer-result-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
}

.status-strip,
.change-stats div,
.change-row,
.answer-result-item,
.evidence-diff-item {
  background: rgba(28, 23, 20, 0.46);
  border: 1px solid rgba(201, 169, 98, 0.24);
  border-radius: 12px;
  padding: 12px;
}

.status-strip {
  align-items: center;
  display: flex;
  gap: 10px;
  justify-content: space-between;
}

.status-strip span,
.answer-result-item span,
.evidence-diff-item span {
  color: var(--accent);
  font-size: 0.86rem;
  font-weight: 900;
}

.status-strip strong,
.change-row strong,
.answer-result-item strong,
.evidence-diff-item strong {
  color: var(--text-main);
  overflow-wrap: anywhere;
}

.change-stats span {
  color: var(--accent);
  display: block;
  font-size: 1.1rem;
  font-weight: 900;
}

.change-stats p,
.change-row p,
.answer-result-item p,
.evidence-diff-item p {
  color: var(--text-sub);
  margin: 6px 0 0;
  overflow-wrap: anywhere;
}

.change-row p {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.change-row b {
  color: var(--accent);
}

.evidence-diff-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

@media (max-width: 760px) {
  .evidence-diff-grid,
  .change-stats {
    grid-template-columns: 1fr;
  }
}
</style>
