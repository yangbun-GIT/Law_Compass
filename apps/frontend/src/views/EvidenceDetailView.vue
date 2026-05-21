<template>
  <section class="evidence-page">
    <div class="workspace-head">
      <div>
        <p class="eyebrow">Evidence</p>
        <h2>{{ title }}</h2>
        <p class="kv">{{ sourceLabel }}</p>
      </div>
      <div class="btn-row">
        <RouterLink class="btn secondary" to="/">대시보드로</RouterLink>
        <button class="btn secondary" :disabled="loading" @click="load">{{ loading ? "새로고침 중..." : "새로고침" }}</button>
      </div>
    </div>

    <article v-if="loading" class="card evidence-state">
      <h3>근거 문서를 불러오는 중입니다</h3>
      <p class="kv">내부 근거 저장소에서 문서 요약을 확인하고 있습니다.</p>
    </article>

    <article v-else-if="message" class="card evidence-state">
      <h3>근거 문서를 찾을 수 없습니다</h3>
      <p class="msg-error">{{ message }}</p>
      <p class="kv">분석 결과의 근거가 갱신되었거나 KB 적재 상태가 바뀌었을 수 있습니다.</p>
    </article>

    <article v-else-if="chunk" class="card evidence-card">
      <div class="chips">
        <span v-if="chunk.article_no" class="chip selected">{{ text(chunk.article_no) }}</span>
        <span v-if="chunk.clause_no" class="chip">{{ text(chunk.clause_no) }}</span>
        <span v-if="chunk.doc_type" class="chip">{{ text(chunk.doc_type) }}</span>
      </div>

      <h3>근거 요약</h3>
      <p class="big-text">{{ summary }}</p>

      <h3>문서 출처</h3>
      <p>{{ sourceLabel }}</p>
      <a v-if="sourceUrl" class="btn secondary" :href="sourceUrl" target="_blank" rel="noopener noreferrer">원문 출처 열기</a>

      <div v-if="debugEnabled" class="developer-debug">
        <h3>개발자 전용 원문</h3>
        <p class="soft-warning">일반 사용자 화면에서는 내부 식별자와 원문 덤프를 숨깁니다.</p>
        <pre>{{ debugText }}</pre>
      </div>
    </article>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { api, formatApiError } from "../api/client";
import { removeTechnicalFields, sanitizeDisplayText } from "../utils/displaySanitizer";

const route = useRoute();
const chunkId = route.params.chunkId as string;
const chunk = ref<any>(null);
const message = ref("");
const loading = ref(false);

const debugEnabled = computed(() => route.query.debug === "1" || import.meta.env.VITE_ENABLE_DEBUG_REPORT === "true");
const title = computed(() => text(chunk.value?.document_title || chunk.value?.article_no || "근거 문서"));
const summary = computed(() => text(chunk.value?.chunk_summary || chunk.value?.document_summary || chunk.value?.chunk_text || "표시할 수 있는 요약이 없습니다."));
const sourceUrl = computed(() => {
  const raw = String(chunk.value?.source_uri || chunk.value?.source_url || "");
  return /^https?:\/\//.test(raw) ? raw : "";
});
const sourceLabel = computed(() => text(chunk.value?.source_name || chunk.value?.source_type || "출처 확인 필요"));
const debugText = computed(() => JSON.stringify(removeTechnicalFields(chunk.value || {}), null, 2));

function text(value: unknown) {
  return sanitizeDisplayText(value);
}

async function load() {
  loading.value = true;
  message.value = "";
  try {
    chunk.value = (await api.getEvidenceChunk(chunkId)).chunk;
  } catch (e: any) {
    chunk.value = null;
    message.value = formatApiError(e, "근거 문서를 불러오지 못했습니다.");
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.evidence-page {
  display: grid;
  gap: 16px;
}

.workspace-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.workspace-head h2 {
  margin: 0;
}

.evidence-state,
.evidence-card {
  display: grid;
  gap: 14px;
  justify-items: start;
}

.evidence-state h3,
.evidence-state p,
.evidence-card h3,
.evidence-card p {
  margin: 0;
}

.developer-debug {
  width: 100%;
}

.developer-debug pre {
  max-height: 420px;
  overflow: auto;
  white-space: pre-wrap;
  padding: 14px;
  border-radius: 12px;
  background: rgba(2, 6, 23, 0.45);
}

@media (max-width: 900px) {
  .workspace-head {
    flex-direction: column;
  }
}
</style>
