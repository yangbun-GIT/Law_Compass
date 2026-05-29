<template>
  <article class="card easy-card missing-info-card">
    <h2>{{ text(missing.title || "더 정확한 분석을 위해 필요한 정보") }}</h2>
    <section v-if="priorityItems.length" class="priority-section">
      <div class="priority-head">
        <span>먼저 확인할 항목</span>
        <strong>{{ text(priorityItems[0].label || priorityItems[0].question) }}</strong>
      </div>
      <p v-if="missing.guidance">{{ text(missing.guidance) }}</p>
      <div class="priority-grid">
        <div v-for="item in priorityItems" :key="`${item.label}-${item.question}`" class="priority-item">
          <span>{{ text(item.priority_label || "확인 필요") }}</span>
          <strong>{{ text(item.label || item.question) }}</strong>
          <p>{{ text(item.reason || item.question) }}</p>
        </div>
      </div>
    </section>
    <ul class="check-list" v-if="items.length">
      <li v-for="item in items" :key="item">{{ text(item) }}</li>
    </ul>

    <form v-if="questions.length" class="followup-form" @submit.prevent="submit">
      <div class="followup-grid">
        <label v-for="question in questions" :key="question.answerKey">
          <span>{{ text(question.question || question.label) }}</span>
          <select v-if="question.options?.length" v-model="answers[question.answerKey]">
            <option value="">선택</option>
            <option v-for="option in question.options" :key="option" :value="option">{{ text(option) }}</option>
          </select>
          <input v-else v-model.trim="answers[question.answerKey]" placeholder="확인한 내용을 입력해 주세요" />
          <small v-if="question.priority_reason">{{ text(question.priority_label || "확인 필요") }} · {{ text(question.priority_reason) }}</small>
        </label>
      </div>
      <p class="kv">답변은 케이스 입력값에 반영되고, 같은 분석 흐름으로 다시 검토됩니다.</p>
      <p v-if="error" class="msg-error">{{ error }}</p>
      <button class="btn" :disabled="submitting || !hasAnswers">{{ submitting ? "재분석 중..." : "답변 반영 후 재분석" }}</button>
    </form>
  </article>
</template>

<script setup lang="ts">
import { computed, reactive, watch } from "vue";
import { sanitizeDisplayText } from "../../utils/displaySanitizer";

type MissingQuestion = {
  field: string;
  answerKey: string;
  label?: string;
  question?: string;
  input_type?: string;
  options?: string[];
  priority_label?: string;
  priority_reason?: string;
};

type PriorityItem = {
  label?: string;
  question?: string;
  priority_label?: string;
  reason?: string;
};

const props = defineProps<{ missing: any; submitting?: boolean; error?: string }>();
const emit = defineEmits<{ submit: [answers: Record<string, string>] }>();
const answers = reactive<Record<string, string>>({});

const items = computed(() => Array.isArray(props.missing?.items) ? props.missing.items : []);
const priorityItems = computed<PriorityItem[]>(() => {
  const raw = Array.isArray(props.missing?.priority_items) ? props.missing.priority_items : [];
  return raw
    .filter((item: any) => item?.label || item?.question)
    .map((item: any) => ({
      label: String(item.label || ""),
      question: String(item.question || ""),
      priority_label: String(item.priority_label || ""),
      reason: String(item.reason || ""),
    }))
    .slice(0, 3);
});
const questions = computed<MissingQuestion[]>(() => {
  const raw = Array.isArray(props.missing?.questions) ? props.missing.questions : [];
  return raw
    .filter((item: any) => item?.field && (item?.question || item?.label))
    .map((item: any, index: number) => {
      const field = String(item.field);
      const question = String(item.question || item.label || item.field);
      return {
        field,
        answerKey: `${field}::${index}::${question}`,
        label: String(item.label || item.field),
        question,
        input_type: String(item.input_type || "text"),
        options: Array.isArray(item.options) ? item.options.map(String).filter(Boolean) : [],
        priority_label: String(item.priority_label || ""),
        priority_reason: String(item.priority_reason || ""),
      };
    });
});
const hasAnswers = computed(() => Object.values(answers).some((value) => String(value || "").trim()));

watch(questions, (next) => {
  const allowed = new Set(next.map((item) => item.answerKey));
  for (const key of Object.keys(answers)) {
    if (!allowed.has(key)) delete answers[key];
  }
  for (const question of next) {
    if (!(question.answerKey in answers)) answers[question.answerKey] = "";
  }
}, { immediate: true });

function submit() {
  const payload: Record<string, string> = {};
  for (const question of questions.value) {
    const value = answers[question.answerKey];
    const trimmed = String(value || "").trim();
    if (trimmed) payload[question.field] = trimmed;
  }
  if (Object.keys(payload).length) emit("submit", payload);
}

function text(value: unknown) {
  return sanitizeDisplayText(value);
}
</script>

<style scoped>
.missing-info-card {
  display: grid;
  gap: 12px;
}

.followup-form {
  display: grid;
  gap: 12px;
}

.priority-section {
  background: rgba(201, 169, 98, 0.08);
  border: 1px solid rgba(201, 169, 98, 0.22);
  border-radius: 8px;
  display: grid;
  gap: 12px;
  padding: 14px;
}

.priority-head {
  display: grid;
  gap: 4px;
}

.priority-head span,
.priority-item span {
  color: var(--accent);
  font-size: 0.85rem;
  font-weight: 900;
}

.priority-head strong,
.priority-item strong {
  color: #f1f7ff;
  overflow-wrap: anywhere;
}

.priority-section p,
.priority-item p {
  color: #cbd5e1;
  margin: 0;
}

.priority-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.priority-item {
  background: rgba(15, 23, 42, 0.28);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 6px;
  padding: 12px;
}

.followup-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.followup-grid label {
  min-width: 0;
}

.followup-grid span {
  display: block;
  color: #e5f7ff;
  font-weight: 800;
  line-height: 1.45;
}

.followup-grid small {
  color: #b7c8d9;
  display: block;
  line-height: 1.4;
  margin-top: 6px;
}

@media (max-width: 760px) {
  .followup-grid {
    grid-template-columns: 1fr;
  }
}
</style>
