<template>
  <article class="card easy-card missing-info-card">
    <h2>{{ text(missing.title || "더 정확한 분석을 위해 필요한 정보") }}</h2>
    <ul class="check-list" v-if="items.length">
      <li v-for="item in items" :key="item">{{ text(item) }}</li>
    </ul>

    <form v-if="questions.length" class="followup-form" @submit.prevent="submit">
      <div class="followup-grid">
        <label v-for="question in questions" :key="question.field || question.question">
          <span>{{ text(question.question || question.label) }}</span>
          <select v-if="question.options?.length" v-model="answers[question.field]">
            <option value="">선택</option>
            <option v-for="option in question.options" :key="option" :value="option">{{ text(option) }}</option>
          </select>
          <input v-else v-model.trim="answers[question.field]" placeholder="확인한 내용을 입력해 주세요" />
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
  label?: string;
  question?: string;
  input_type?: string;
  options?: string[];
};

const props = defineProps<{ missing: any; submitting?: boolean; error?: string }>();
const emit = defineEmits<{ submit: [answers: Record<string, string>] }>();
const answers = reactive<Record<string, string>>({});

const items = computed(() => Array.isArray(props.missing?.items) ? props.missing.items : []);
const questions = computed<MissingQuestion[]>(() => {
  const raw = Array.isArray(props.missing?.questions) ? props.missing.questions : [];
  return raw
    .filter((item: any) => item?.field && (item?.question || item?.label))
    .map((item: any) => ({
      field: String(item.field),
      label: String(item.label || item.field),
      question: String(item.question || item.label || item.field),
      input_type: String(item.input_type || "text"),
      options: Array.isArray(item.options) ? item.options.map(String).filter(Boolean) : [],
    }));
});
const hasAnswers = computed(() => Object.values(answers).some((value) => String(value || "").trim()));

watch(questions, (next) => {
  const allowed = new Set(next.map((item) => item.field));
  for (const key of Object.keys(answers)) {
    if (!allowed.has(key)) delete answers[key];
  }
  for (const question of next) {
    if (!(question.field in answers)) answers[question.field] = "";
  }
}, { immediate: true });

function submit() {
  const payload: Record<string, string> = {};
  for (const [field, value] of Object.entries(answers)) {
    const trimmed = String(value || "").trim();
    if (trimmed) payload[field] = trimmed;
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

@media (max-width: 760px) {
  .followup-grid {
    grid-template-columns: 1fr;
  }
}
</style>
