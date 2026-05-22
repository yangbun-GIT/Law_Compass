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
.agent-process-card {
  display: grid;
  gap: 18px;
}

.process-header {
  align-items: flex-start;
  display: flex;
  gap: 16px;
  justify-content: space-between;
}

.process-status {
  background: rgba(84, 226, 243, 0.14);
  border: 1px solid rgba(84, 226, 243, 0.46);
  border-radius: 999px;
  color: #7ae8f4;
  flex: 0 0 auto;
  font-weight: 800;
  padding: 9px 13px;
}

.process-stats {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.process-stat {
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 12px;
  min-width: 0;
  padding: 14px;
}

.process-stat span,
.process-step span {
  color: #b9c6d8;
  display: block;
  font-size: 0.9rem;
}

.process-stat strong,
.process-step strong {
  color: #f1f7ff;
  display: block;
  margin-top: 6px;
}

.process-steps {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.process-step {
  background: rgba(9, 16, 28, 0.42);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  min-width: 0;
  padding: 13px;
}

.process-step .step-phase {
  color: #6de3ef;
  font-weight: 800;
}

.decision-notes {
  display: grid;
  gap: 8px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.decision-notes li {
  background: rgba(84, 226, 243, 0.08);
  border: 1px solid rgba(84, 226, 243, 0.18);
  border-radius: 10px;
  color: #d8e5f6;
  line-height: 1.55;
  padding: 10px 12px;
}

@media (max-width: 760px) {
  .process-header {
    display: grid;
  }

  .process-stats,
  .process-steps {
    grid-template-columns: 1fr;
  }

  .process-status {
    justify-self: flex-start;
  }
}
</style>
