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

    <EasyReportView
      v-else-if="report"
      :report="report"
      :followup-submitting="reanalyzing"
      :followup-error="followupError"
      @submit-followup="submitFollowup"
    />

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
import { api, formatApiError, type AccidentFacts, type CaseItem } from "../api/client";

const caseId = useRoute().params.caseId as string;
const report = ref<any>(null);
const caseData = ref<CaseItem | null>(null);
const loading = ref(false);
const reanalyzing = ref(false);
const error = ref("");
const followupError = ref("");

async function load() {
  loading.value = true;
  error.value = "";
  followupError.value = "";
  try {
    const caseResp = await api.getCase(caseId);
    caseData.value = caseResp.case;
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

async function submitFollowup(answers: Record<string, string>) {
  followupError.value = "";
  reanalyzing.value = true;
  try {
    const currentCase = caseData.value || (await api.getCase(caseId)).case;
    caseData.value = currentCase;
    const patch = normalizeAnswerPatch(answers);
    if (!Object.keys(patch).length) {
      followupError.value = "반영할 답변을 선택해 주세요.";
      return;
    }
    const nextFacts = { ...(currentCase.structured_facts || {}), ...patch };
    const response = await api.reanalyzeText(caseId, {
      description_text: currentCase.description_text || "",
      structured_facts: nextFacts,
      selected_keywords: currentCase.selected_keywords || [],
      analysis_mode: currentCase.analysis_mode || "quick_summary",
    });
    report.value = response.report || response.result || report.value;
    caseData.value = { ...currentCase, structured_facts: nextFacts, status: "completed" };
  } catch (e: any) {
    followupError.value = formatApiError(e, "보완 답변을 반영해 재분석하지 못했습니다.");
  } finally {
    reanalyzing.value = false;
  }
}

function normalizeAnswerPatch(answers: Record<string, string>): AccidentFacts {
  const patch: AccidentFacts = {};
  for (const [field, raw] of Object.entries(answers)) {
    const value = raw.trim();
    if (!value) continue;
    if (field === "injury") patch.injury = value.includes("없음") ? false : value.includes("확인") ? null : true;
    else if (field === "stopped") {
      patch.stopped = value.includes("정차");
      if (value.includes("급정거")) patch.sudden_brake = true;
      if (value.includes("정차")) patch.sudden_brake = false;
    } else if (field === "sudden_brake") patch.sudden_brake = !value.includes("없음");
    else if (field === "school_zone") patch.school_zone = value.includes("맞음") ? true : value.includes("아님") ? false : undefined;
    else if (field === "victim_is_child") patch.victim_is_child = value.includes("미만") ? true : value.includes("이상") ? false : undefined;
    else if (field === "crosswalk_nearby") patch.crosswalk_nearby = value.includes("아님") ? false : value.includes("확인") ? undefined : true;
    else if (field === "turn_signal") patch.turn_signal = value.includes("켰음") ? true : value.includes("않음") ? false : undefined;
    else if (field === "signal_state") {
      patch.signal_state = value;
      if (value.includes("상대 신호위반")) patch.opponent_signal_violation = true;
    } else if (field === "accident_type") patch.accident_type = mapAccidentType(value);
    else (patch as Record<string, any>)[field] = value;
  }
  return Object.fromEntries(Object.entries(patch).filter(([, value]) => value !== undefined)) as AccidentFacts;
}

function mapAccidentType(value: string) {
  if (value.includes("후미")) return "rear_end_collision";
  if (value.includes("차선")) return "lane_change_collision";
  if (value.includes("교차")) return "intersection_collision";
  if (value.includes("보행")) return "pedestrian_crosswalk_accident";
  if (value.includes("자전거")) return "bicycle_collision";
  if (value.includes("시설물") || value.includes("단독")) return "object_collision";
  return value;
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
