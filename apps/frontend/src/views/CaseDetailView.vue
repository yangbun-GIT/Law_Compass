<template>
  <section class="case-workspace">
    <CaseWorkspaceHeader
      :case-id="caseId"
      :case-title="caseData?.title"
      :case-status="caseData?.status"
      :initial-loading="initialLoading"
      :busy="busy"
      :status-label="statusLabel"
      @refresh="loadAll"
    />

    <p v-if="initialLoading" class="card kv">케이스와 업로드 상태를 불러오는 중입니다.</p>
    <p v-else-if="loadError" class="card msg-error">{{ loadError }}</p>

    <CaseSummaryCard
      v-if="caseData"
      :case-data="caseData"
      :description-text="descriptionText"
      :selected-keyword-count="selectedKeywords.length"
      :upload-count="uploads.length"
      :job-count="jobs.length"
      :status-label="statusLabel"
      :status-class="statusClass"
    />

    <CaseInputStep
      :description-text="descriptionText"
      :analysis-mode="analysisMode"
      :facts="facts"
      :selected-keywords="selectedKeywords"
      :keyword-pool="keywordPool"
      :busy="busy"
      @update:description-text="updateDescriptionText"
      @update:analysis-mode="updateAnalysisMode"
      @update:facts="updateFacts"
      @toggle-keyword="toggleKeyword"
      @save="saveCaseInputs"
    />

    <CaseUploadStep
      :file="file"
      :uploads="uploads"
      :selected-upload-id="selectedUploadId"
      :active-upload-id="activeUploadId"
      :view-url="viewUrl"
      :busy="busy"
      :pretty-size="prettySize"
      :format-date="formatDate"
      :status-label="statusLabel"
      :status-class="statusClass"
      @file-change="onFile"
      @update:selected-upload-id="updateSelectedUploadId"
      @upload-local="uploadLocal"
      @complete-upload="completeUpload"
      @load-uploads="loadUploads"
      @fetch-view-url="fetchViewUrl"
      @fetch-download-url="fetchDownloadUrl"
    />

    <CaseAnalysisStep
      :jobs="jobs"
      :message="message"
      :message-ok="messageOk"
      :active-upload-id="activeUploadId"
      :busy="busy"
      :status-label="statusLabel"
      :status-class="statusClass"
      @analyze-text="analyzeText"
      @analyze-video="analyzeVideo"
      @load-jobs="loadJobs"
      @load-report="loadReport"
    />

    <EasyReportView v-if="report" :report="report" />
  </section>
</template>

<script setup lang="ts">
import { useRoute } from "vue-router";
import type { AccidentFacts } from "../api/client";
import CaseAnalysisStep from "../components/case/CaseAnalysisStep.vue";
import CaseInputStep from "../components/case/CaseInputStep.vue";
import CaseSummaryCard from "../components/case/CaseSummaryCard.vue";
import CaseUploadStep from "../components/case/CaseUploadStep.vue";
import CaseWorkspaceHeader from "../components/case/CaseWorkspaceHeader.vue";
import EasyReportView from "../components/easy/EasyReportView.vue";
import { useCaseWorkspace } from "../composables/useCaseWorkspace";

const caseId = useRoute().params.caseId as string;
const {
  caseData,
  descriptionText,
  facts,
  analysisMode,
  selectedKeywords,
  keywordPool,
  file,
  uploads,
  selectedUploadId,
  activeUploadId,
  viewUrl,
  jobs,
  report,
  message,
  messageOk,
  initialLoading,
  loadError,
  busy,
  applyPreset,
  analyzeText,
  analyzeVideo,
  completeUpload,
  fetchDownloadUrl,
  fetchViewUrl,
  formatDate,
  loadAll,
  loadJobs,
  loadReport,
  loadUploads,
  onFile,
  prettySize,
  saveCaseInputs,
  statusClass,
  statusLabel,
  toggleKeyword,
  uploadLocal
} = useCaseWorkspace(caseId);

function updateDescriptionText(value: string) {
  descriptionText.value = value;
}

function updateAnalysisMode(value: string) {
  analysisMode.value = value;
  applyPreset();
}

function updateFacts(value: AccidentFacts) {
  facts.value = value;
}

function updateSelectedUploadId(value: string) {
  selectedUploadId.value = value;
}
</script>

<style scoped>
.case-workspace {
  display: grid;
  gap: 16px;
}
</style>
