<template>
  <article v-if="card" class="card easy-card wide-card agent-process-card">
    <div class="process-header">
      <div>
        <p class="kv">Agent 검증 상태</p>
        <h2>{{ text(card.title || "판단 검증 흐름") }}</h2>
      </div>
      <span class="process-status">{{ text(card.status_label || "확인 필요") }}</span>
    </div>
    <p class="big-text">{{ text(card.summary) }}</p>
    <div class="process-stats">
      <div v-for="item in card.stats || []" :key="`${item.label}-${item.value}`" class="process-stat">
        <span>{{ text(item.label) }}</span>
        <strong>{{ text(item.value) }}</strong>
      </div>
    </div>
    <div v-if="card.steps?.length" class="process-steps">
      <div v-for="step in card.steps" :key="`${step.phase_label}-${step.label}`" class="process-step">
        <span class="step-phase">{{ text(step.phase_label) }}</span>
        <strong>{{ text(step.label) }}</strong>
        <span>{{ text(step.status_label) }}</span>
      </div>
    </div>
    <ul v-if="card.decision_notes?.length" class="decision-notes">
      <li v-for="note in card.decision_notes" :key="note">{{ text(note) }}</li>
    </ul>
    <ul v-if="card.warnings?.length" class="check-list">
      <li v-for="warning in card.warnings" :key="warning">{{ text(warning) }}</li>
    </ul>
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
.agent-process-card {
  display: grid;
  gap: 18px;
  min-width: 0;
}

.process-header {
  align-items: flex-start;
  display: flex;
  gap: 16px;
  justify-content: space-between;
}

.process-status {
  background: var(--accent-soft);
  border: 1px solid rgba(201, 169, 98, 0.40);
  border-radius: 999px;
  color: var(--accent-strong);
  flex: 0 0 auto;
  font-weight: 900;
  min-height: 30px;
  padding: 6px 12px;
  width: fit-content;
}

.process-stats {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  margin-top: 4px;
}

.process-stat {
  background: rgba(28, 23, 20, 0.44);
  border: 1px solid rgba(201, 169, 98, 0.22);
  border-radius: 16px;
  min-width: 0;
  padding: 12px 14px;
  overflow-wrap: anywhere;
}

.process-stat span,
.process-step span {
  color: var(--text-sub);
  display: block;
  font-size: 0.9rem;
}

.process-stat strong,
.process-step strong {
  color: var(--text-main);
  display: block;
  margin-top: 6px;
  overflow-wrap: anywhere;
}

.process-steps {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 4px;
}

.process-step {
  background: rgba(37, 30, 25, 0.72);
  border: 1px solid rgba(201, 169, 98, 0.20);
  border-radius: 16px;
  min-width: 0;
  padding: 12px 14px;
  color: var(--text-main);
  overflow-wrap: anywhere;
}

.process-step .step-phase {
  color: var(--accent-strong);
  font-weight: 900;
}

.decision-notes {
  display: grid;
  gap: 8px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.decision-notes li {
  background: var(--warning-soft);
  border: 1px solid rgba(215, 181, 109, 0.30);
  border-radius: 14px;
  color: #f1d99a;
  line-height: 1.55;
  padding: 10px 12px;
  overflow-wrap: anywhere;
}

@media (max-width: 760px) {
  .process-header {
    display: grid;
  }

  .process-stats {
    grid-template-columns: 1fr;
  }

  .process-stat,
  .process-step {
    border-radius: 14px;
    padding: 11px 12px;
  }

  .process-status {
    justify-self: flex-start;
  }
}
</style>
