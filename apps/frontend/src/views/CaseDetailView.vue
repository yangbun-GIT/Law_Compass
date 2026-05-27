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

    <section class="card easy-card guided-flow">
      <p class="eyebrow">교통사고 분석</p>
      <h2>사고 설명이나 영상을 넣으면 필요한 질문만 차례대로 확인합니다</h2>
      <div class="guided-stepper">
        <span :class="{ active: guidedStep === 'input' }">1 사고 자료</span>
        <span :class="{ active: guidedStep === 'accident-type' }">2 사고유형</span>
        <span :class="{ active: guidedStep === 'purpose' }">3 분석 목적</span>
        <span :class="{ active: guidedStep === 'questions' }">4 확인 질문</span>
        <span :class="{ active: guidedStep === 'analyzing' || guidedStep === 'result' }">5 결과</span>
      </div>

      <div v-if="guidedStep === 'input'" class="guided-panel">
        <label>사고 설명
          <textarea
            :value="descriptionText"
            rows="6"
            placeholder="예: 빨간불에 정차해 있었는데 뒤차가 갑자기 추돌했습니다."
            @input="updateDescriptionText(eventValue($event))"
          />
        </label>
        <label class="file-drop">영상 선택은 선택 사항입니다
          <input type="file" accept="video/*" @change="onGuidedFile" />
        </label>
        <p v-if="file" class="kv">선택한 영상: {{ file.name }} ({{ prettySize(file.size) }})</p>
        <p v-if="message" :class="messageOk ? 'msg-ok' : 'msg-error'">{{ message }}</p>
        <div class="btn-row">
          <button class="btn" :disabled="!!busy" @click="continueFromInput">사고유형 선택하기</button>
        </div>
      </div>

      <div v-else-if="guidedStep === 'accident-type'" class="guided-panel">
        <h3>어떤 사고에 가장 가까운가요?</h3>
        <div class="guided-card-grid">
          <button
            v-for="option in guidedAccidentTypeOptions"
            :key="option.label"
            class="guided-choice-card"
            type="button"
            @click="selectAccidentType(option)"
          >
            <strong>{{ option.label }}</strong>
            <span>{{ option.hint }}</span>
          </button>
        </div>
      </div>

      <div v-else-if="guidedStep === 'purpose'" class="guided-panel">
        <h3>무엇을 중심으로 볼까요?</h3>
        <div class="guided-card-grid">
          <button
            v-for="mode in guidedAnalysisModes"
            :key="mode.value"
            class="guided-choice-card"
            type="button"
            @click="selectGuidedAnalysisMode(mode.value)"
          >
            <strong>{{ mode.label }}</strong>
            <span>{{ mode.hint }}</span>
          </button>
        </div>
      </div>

      <div v-else-if="guidedStep === 'questions'" class="guided-panel">
        <h3>과실비율에 영향을 줄 수 있는 점을 확인할게요</h3>
        <div class="guided-question-list">
          <article v-for="question in guidedQuestions" :key="question.question_id || question.field" class="guided-question">
            <p class="kv">{{ question.title || question.label }}</p>
            <h4>{{ question.plain_question || question.question }}</h4>
            <p>{{ question.why_it_matters || question.priority_reason || "답하기 어려우면 잘 모르겠어요를 선택해도 됩니다." }}</p>
            <div class="chips">
              <button
                v-for="choice in question.choices || question.options || ['예', '아니오', '잘 모르겠어요']"
                :key="choice.value || choice"
                class="chip"
                :class="{ selected: guidedAnswers[question.question_id] === (choice.value || choice) }"
                type="button"
                @click="answerGuidedQuestion(question, choice.value || choice)"
              >
                {{ choice.label || choice }}
              </button>
            </div>
          </article>
        </div>
        <div class="btn-row">
          <button class="btn" :disabled="!!busy" @click="startGuidedAnalysis">이대로 분석하기</button>
          <button class="btn secondary" type="button">답변 더 추가하기</button>
        </div>
      </div>

      <div v-else-if="guidedStep === 'analyzing'" class="guided-panel">
        <h3>{{ progress?.current_stage || "분석 중입니다" }}</h3>
        <p class="easy-summary">{{ progress?.current_message || "비슷한 KNIA 과실비율 기준을 찾고 있습니다." }}</p>
        <ul class="check-list">
          <li v-for="step in progress?.steps || []" :key="step.stage">{{ step.message }}</li>
        </ul>
      </div>

      <p v-if="guidedStep !== 'input' && message" :class="messageOk ? 'msg-ok' : 'msg-error'">{{ message }}</p>
    </section>

    <details class="card diagnostic-panel">
      <summary>고급 진단 보기</summary>
      <p class="kv">기존 개발자용 업로드, 작업 조회, 새로고침 기능은 여기에서만 제공합니다.</p>
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
    </details>

    <EasyReportView
      v-if="report"
      :report="report"
      :followup-submitting="reanalyzing"
      :followup-error="followupError"
      @submit-followup="submitFollowup"
    />
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
  progress,
  viewUrl,
  jobs,
  report,
  message,
  messageOk,
  initialLoading,
  loadError,
  followupError,
  reanalyzing,
  busy,
  guidedStep,
  guidedAnswers,
  guidedAccidentTypeOptions,
  guidedAnalysisModes,
  guidedQuestions,
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
  onGuidedFile,
  prettySize,
  saveCaseInputs,
  continueFromInput,
  selectAccidentType,
  selectGuidedAnalysisMode,
  answerGuidedQuestion,
  startGuidedAnalysis,
  statusClass,
  statusLabel,
  submitFollowup,
  toggleKeyword,
  uploadLocal
} = useCaseWorkspace(caseId);

function eventValue(event: Event) {
  return (event.target as HTMLInputElement | HTMLTextAreaElement).value;
}

function updateDescriptionText(value: string) {
  descriptionText.value = value;
}

function updateAnalysisMode(value: string) {
  analysisMode.value = value;
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
