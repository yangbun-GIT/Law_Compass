<template>
  <section class="card case-create-card">
    <p class="eyebrow">새 사고 케이스</p>
    <h2>사고 내용을 입력해 주세요</h2>
    <p class="kv">제목과 기본 설명만 입력해도 시작할 수 있습니다. 자세한 사고 정보와 영상은 다음 단계에서 보완합니다.</p>

    <div v-if="draftApplied" class="soft-warning">
      AI가 채팅 내용을 바탕으로 입력 초안을 만들었습니다. 틀린 부분이 있으면 편하게 수정해 주세요.
    </div>

    <label>케이스 제목
      <input v-model="title" placeholder="예: 정차 중 후미추돌 사고" />
    </label>
    <label>기본 사고 설명
      <textarea v-model="description" rows="5" placeholder="예: 신호대기 중 정차해 있던 중 뒤 차량이 후미를 추돌했습니다. 목 통증이 있습니다." />
    </label>

    <div class="chips" v-if="keywords.length">
      <span v-for="keyword in keywords" :key="keyword" class="chip selected">{{ keyword }}</span>
    </div>

    <div class="btn-row">
      <button class="btn" :disabled="loading || !title.trim()" @click="create">
        {{ loading ? "생성 중..." : "케이스 생성 후 사고 입력으로 이동" }}
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
const router = useRouter();
const title = ref("");
const description = ref("");
const analysisMode = ref("user_friendly");
const keywords = ref<string[]>(["블랙박스", "과실비율"]);
const facts = reactive<AccidentFacts>({ accident_type: "", accident_party_type: "", injury: null });
const loading = ref(false);
const message = ref("");
const ok = ref(true);
const draftApplied = ref(false);

onMounted(() => {
  const raw = localStorage.getItem(DRAFT_KEY);
  if (!raw) return;
  try {
    const draft = JSON.parse(raw);
    title.value = draft.title || title.value;
    description.value = draft.description_text || description.value;
    analysisMode.value = normalizeAnalysisMode(draft.analysis_mode || analysisMode.value);
    keywords.value = Array.isArray(draft.selected_keywords) ? draft.selected_keywords : keywords.value;
    Object.assign(facts, draft.structured_facts || {});
    draftApplied.value = true;
  } catch {
    localStorage.removeItem(DRAFT_KEY);
  }
});

async function create() {
  loading.value = true;
  message.value = "";
  ok.value = true;
  try {
    const data = await api.createCase({
      title: title.value.trim(),
      description_text: description.value.trim(),
      structured_facts: { ...facts },
      selected_keywords: keywords.value,
      analysis_mode: normalizeAnalysisMode(analysisMode.value)
    });
    localStorage.removeItem(DRAFT_KEY);
    await router.push(`/cases/${data.case.id}/wizard`);
  } catch (e: any) {
    message.value = formatApiError(e, "케이스 생성에 실패했습니다.");
    ok.value = false;
  } finally {
    loading.value = false;
  }
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
