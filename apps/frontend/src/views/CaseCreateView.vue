<template>
  <section class="card easy-card case-create-card instant-video-case" aria-live="polite">
    <p class="eyebrow">새 사고 케이스</p>
    <h2>영상이나 설명부터 바로 시작합니다</h2>
    <p class="kv">
      빈 케이스를 먼저 만들고, 곧바로 영상과 사고 설명 입력 화면으로 이동합니다. 대분류와 확인 질문은 다음 단계에서 보완할 수 있습니다.
    </p>

    <div v-if="draftApplied" class="soft-warning">
      AI가 채팅 내용을 바탕으로 만든 초안을 새 케이스에 함께 저장합니다. 영상 업로드 화면에서 수정할 수 있습니다.
    </div>

    <div class="case-create-loading" role="status">
      <span class="case-create-spinner" aria-hidden="true"></span>
      <div>
        <strong>{{ loading ? "케이스를 준비하고 있습니다" : "케이스 준비가 필요합니다" }}</strong>
        <p class="kv">
          {{ loading ? "잠시 후 영상·설명 입력 화면으로 이동합니다." : "자동 이동이 멈췄다면 다시 시도해 주세요." }}
        </p>
      </div>
    </div>

    <div class="btn-row">
      <button class="btn" :disabled="loading" @click="createImmediately">
        {{ loading ? "생성 중..." : "다시 시도" }}
      </button>
      <RouterLink class="btn secondary" to="/">목록으로</RouterLink>
    </div>

    <p v-if="message" :class="ok ? 'msg-ok' : 'msg-error'">{{ message }}</p>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { api, formatApiError, type AccidentFacts } from "../api/client";

const DRAFT_KEY = "lawcompass:draftCase";
const DEFAULT_TITLE = "영상 사고 분석 케이스";

const router = useRouter();
const title = ref(DEFAULT_TITLE);
const description = ref("");
const analysisMode = ref("user_friendly");
const keywords = ref<string[]>(["블랙박스", "과실비율"]);
const facts = reactive<AccidentFacts>({ injury: null });
const loading = ref(false);
const message = ref("");
const ok = ref(true);
const draftApplied = ref(false);

onMounted(() => {
  applyDraftIfPresent();
  void createImmediately();
});

function applyDraftIfPresent() {
  const raw = localStorage.getItem(DRAFT_KEY);
  if (!raw) return;

  try {
    const draft = JSON.parse(raw);
    title.value = normalizeTitle(draft.title);
    description.value = String(draft.description_text || "");
    analysisMode.value = normalizeAnalysisMode(draft.analysis_mode || analysisMode.value);
    keywords.value = Array.isArray(draft.selected_keywords) ? draft.selected_keywords : keywords.value;
    Object.assign(facts, draft.structured_facts || {});
    draftApplied.value = true;
  } catch {
    localStorage.removeItem(DRAFT_KEY);
  }
}

async function createImmediately() {
  if (loading.value) return;
  loading.value = true;
  message.value = "";
  ok.value = true;

  try {
    const data = await api.createCase({
      title: normalizeTitle(title.value),
      description_text: description.value.trim(),
      structured_facts: { ...facts },
      selected_keywords: keywords.value,
      analysis_mode: normalizeAnalysisMode(analysisMode.value),
    });

    localStorage.removeItem(DRAFT_KEY);
    await router.replace(`/cases/${data.case.id}?start=input`);
  } catch (e: any) {
    message.value = formatApiError(e, "케이스 생성에 실패했습니다.");
    ok.value = false;
  } finally {
    loading.value = false;
  }
}

function normalizeTitle(value?: string | null) {
  const text = String(value || "").trim();
  return text || DEFAULT_TITLE;
}

function normalizeAnalysisMode(mode?: string | null) {
  const value = String(mode || "").trim();

  if (
    value === "expert" ||
    value === "legal_precedent_focused" ||
    value === "full_deep_research" ||
    value === "deep_research" ||
    value === "debug"
  ) {
    return "expert";
  }

  return "user_friendly";
}
</script>

<style scoped>
.case-create-card {
  display: grid;
  gap: 14px;
}

.case-create-loading {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
  padding: 16px;
  border-radius: 16px;
  border: 1px solid rgba(201, 169, 98, 0.26);
  background: rgba(232, 223, 212, 0.065);
}

.case-create-loading strong {
  display: block;
  color: var(--text-main);
  line-height: 1.35;
  word-break: keep-all;
}

.case-create-spinner {
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  border-radius: 999px;
  border: 2px solid rgba(232, 223, 212, 0.12);
  border-top-color: var(--accent-strong);
  border-right-color: rgba(139, 38, 53, 0.78);
  animation: case-create-spin 0.9s linear infinite;
}

@keyframes case-create-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .case-create-spinner {
    animation: none;
  }
}

@media (max-width: 640px) {
  .case-create-loading {
    align-items: flex-start;
    padding: 14px;
  }
}
</style>
