<template>
  <section>
    <div class="btn-row">
      <RouterLink class="btn secondary" :to="`/cases/${caseId}`">입력 화면으로 돌아가기</RouterLink>
      <button class="btn" @click="load">결과 새로고침</button>
    </div>
    <EasyReportView v-if="report" :report="report" />
    <article v-else class="card"><h2>아직 결과가 없습니다</h2><p>영상 전처리와 분석 작업이 끝나면 이 화면에서 쉬운 리포트를 볼 수 있습니다.</p></article>
  </section>
</template>
<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import EasyReportView from "../components/easy/EasyReportView.vue";
import { api } from "../api/client";
const caseId = useRoute().params.caseId as string;
const report = ref<any>(null);
async function load() { try { report.value = await api.getEasyReport(caseId); } catch { report.value = null; } }
onMounted(load);
</script>
