<template>
  <section class="result-page">
    <div class="workspace-head">
      <div>
        <p class="eyebrow">Analysis Result</p>
        <h2>분석 결과</h2>
        <p class="kv">분석이 완료되면 쉬운 리포트와 근거 요약을 확인할 수 있습니다.</p>
      </div>
      <div class="btn-row">
        <RouterLink class="btn secondary" :to="`/cases/${caseId}/wizard`">입력 화면으로 돌아가기</RouterLink>
        <button class="btn" :disabled="loading" @click="load">{{ loading ? "새로고침 중..." : "결과 새로고침" }}</button>
      </div>
    </div>

    <article v-if="loading" class="card result-state">
      <h3>결과를 불러오는 중입니다</h3>
      <p class="kv">분석 결과와 쉬운 리포트 표시 정보를 확인하고 있습니다.</p>
    </article>

    <article v-else-if="error" class="card result-state">
      <h3>결과를 불러오지 못했습니다</h3>
      <p class="msg-error">{{ error }}</p>
      <RouterLink class="btn secondary" :to="`/cases/${caseId}/wizard`">입력/작업 상태 확인</RouterLink>
    </article>

    <EasyReportView v-else-if="report" :report="report" />

    <article v-else class="card result-state">
      <h3>아직 결과가 없습니다</h3>
      <p>텍스트 분석을 실행했거나 영상 전처리와 분석 작업이 끝나면 이 화면에서 쉬운 리포트를 볼 수 있습니다.</p>
      <RouterLink class="btn" :to="`/cases/${caseId}/wizard`">분석 요청하러 가기</RouterLink>
    </article>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import EasyReportView from "../components/easy/EasyReportView.vue";
import { api, formatApiError } from "../api/client";

const caseId = useRoute().params.caseId as string;
const report = ref<any>(null);
const loading = ref(false);
const error = ref("");

async function load() {
  loading.value = true;
  error.value = "";
  try {
    report.value = await api.getEasyReport(caseId);
  } catch (e: any) {
    report.value = null;
    const status = Number(e?.status || 0);
    if (status === 404) return;
    error.value = formatApiError(e, "분석 결과를 불러오지 못했습니다.");
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.result-page {
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

.result-state {
  display: grid;
  justify-items: start;
  gap: 10px;
  padding: 24px;
}

.result-state h3,
.result-state p {
  margin: 0;
}

@media (max-width: 900px) {
  .workspace-head {
    flex-direction: column;
  }
}
</style>
