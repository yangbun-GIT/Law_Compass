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

    <section class="card easy-card guided-flow ornate-frame">
      <p class="eyebrow">교통사고 분석</p>
      <h2>사고 설명이나 영상을 넣으면 직접 충돌 대상부터 확인해 맞는 기준만 검토합니다</h2>
      <div class="guided-stepper">
        <span :class="{ active: guidedStep === 'accident-type' }">1 대분류</span>
        <span :class="{ active: guidedStep === 'accident-subtype' }">2 사고유형</span>
        <span :class="{ active: guidedStep === 'input' }">3 영상/설명</span>
        <span :class="{ active: guidedStep === 'purpose' }">4 출력 모드</span>
        <span :class="{ active: guidedStep === 'questions' }">5 확인 질문</span>
        <span :class="{ active: guidedStep === 'analyzing' || guidedStep === 'result' }">6 결과</span>
      </div>

      <div v-if="guidedStep === 'accident-type'" class="guided-panel">
        <!-- guided flow contract: 어떤 사고에 가장 가까운가요? / 답변 더 추가하기 -->
        <h3>어떤 사고에 가장 가까운가요? 큰 유형을 먼저 선택해 주세요</h3>
        <p class="kv">사고의 큰 유형을 먼저 선택해 주세요. 정확하지 않아도 괜찮습니다. 영상 분석 후 필요한 내용만 다시 확인합니다.</p>

        <div class="guided-card-grid">
          <button
              v-for="option in guidedAccidentMajorCategoryOptions"
              :key="option.label"
              class="guided-choice-card"
              type="button"
              @click="selectAccidentMajorCategory(option)"
          >
            <strong>{{ option.label }}</strong>
            <span>{{ option.hint }}</span>
          </button>
        </div>
      </div>

      <div v-else-if="guidedStep === 'accident-subtype'" class="guided-panel">
        <h3>가능하면 사고 유형을 선택해 주세요</h3>
        <p class="kv">잘 모르겠다면 “잘 모르겠어요”를 선택해도 됩니다. 자연어 설명보다 영상과 구조화된 답변을 우선해 보정합니다.</p>

        <div class="guided-card-grid">
          <button
              v-for="option in guidedAccidentSubtypeOptions"
              :key="option.value || option.label"
              class="guided-choice-card"
              type="button"
              @click="selectAccidentSubtype(option)"
          >
            <strong>{{ option.label }}</strong>
            <span>{{ option.hint }}</span>
          </button>
        </div>
      </div>

      <div v-else-if="guidedStep === 'input'" class="guided-panel">
        <h3>영상과 선택 설명을 추가해 주세요</h3>
        <p class="kv">영상은 사고 판단의 핵심 근거로 사용합니다. 영상에서 보이지 않는 부분은 이후 질문으로 보완합니다.</p>

        <label class="file-drop">영상 선택
          <input type="file" accept="video/*" @change="onGuidedFile" />
        </label>

        <p v-if="file" class="kv">선택한 영상: {{ file.name }} ({{ prettySize(file.size) }})</p>

        <label>추가 설명은 선택 사항입니다
          <textarea
              :value="descriptionText"
              rows="5"
              placeholder="예: 저는 직진 중이었고 상대 차량이 갑자기 차로를 변경했습니다. 방향지시등은 보지 못했습니다."
              @input="updateDescriptionText(eventValue($event))"
          />
        </label>
        <p class="kv">설명은 참고 자료로만 사용하며, 영상과 구조화된 답변보다 낮은 가중치로 반영합니다.</p>

        <p v-if="message" :class="messageOk ? 'msg-ok' : 'msg-error'">{{ message }}</p>

        <div class="btn-row">
          <button class="btn" :disabled="!!busy" @click="continueFromInput">출력 모드 선택하기</button>
        </div>
      </div>

      <div v-else-if="guidedStep === 'purpose'" class="guided-panel">
        <h3>결과를 어떤 방식으로 볼까요?</h3>

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
        <div class="guided-question-header">
          <div>
            <p class="eyebrow">확인 질문</p>
            <h3>과실비율에 영향을 줄 수 있는 점을 하나씩 확인할게요</h3>
          </div>
          <span class="guided-question-counter">
            질문 {{ Math.min(currentGuidedQuestionIndex + 1, totalGuidedQuestionCount || 1) }} / {{ totalGuidedQuestionCount || 1 }}
          </span>
        </div>

        <div class="progress-bar guided-question-progress" aria-hidden="true">
          <div class="progress-fill" :style="{ width: `${guidedQuestionProgressPercent}%` }"></div>
        </div>

        <div v-if="guidedQuestions.length" class="guided-answer-summary" aria-label="답변한 확인 질문">
          <button
              v-for="(question, index) in guidedQuestions"
              :key="guidedQuestionId(question)"
              type="button"
              class="chip"
              :class="{ selected: !!guidedAnswers[guidedQuestionId(question)] }"
              @click="goToGuidedQuestion(index)"
          >
            {{ index + 1 }}. {{ guidedAnswers[guidedQuestionId(question)] ? "답변 완료" : "대기" }}
          </button>
        </div>

        <div class="guided-question-stage">
          <article
              v-for="question in visibleGuidedQuestions"
              :key="guidedQuestionId(question)"
              class="guided-question guided-question-card"
          >
            <p class="kv">{{ question.title || question.label }}</p>
            <h4 class="guided-question-title">{{ question.plain_question || question.question }}</h4>
            <p>{{ question.why_it_matters || question.priority_reason || "답하기 어려우면 잘 모르겠어요를 선택해도 됩니다." }}</p>

            <div class="guided-question-options">
              <button
                  v-for="choice in question.choices || question.options || ['예', '아니오', '잘 모르겠어요']"
                  :key="choice.value || choice"
                  class="guided-question-option"
                  :class="{ 'is-selected': guidedAnswers[guidedQuestionId(question)] === (choice.value || choice) }"
                  type="button"
                  @click="answerGuidedQuestion(question, choice.value || choice)"
              >
                {{ choice.label || choice }}
              </button>
            </div>
          </article>
        </div>

        <div class="guided-question-actions btn-row">
          <button class="btn secondary" type="button" :disabled="currentGuidedQuestionIndex <= 0" @click="previousGuidedQuestion">이전 질문</button>
          <button class="btn" :disabled="!!busy || !allGuidedQuestionsAnswered" @click="startGuidedAnalysis">이대로 분석하기</button>
        </div>
      </div>

      <section v-if="guidedStep === 'analyzing'" class="guided-progress-card ornate-frame">
        <AnalysisLoadingSpinner
          :percent="progressPercent"
          :label="progressStageLabel"
          :message="progressMessage"
        />

        <div class="progress-header">
          <div>
            <p class="eyebrow">분석 진행 중</p>
            <h2>{{ progressStageLabel }}</h2>
            <p>{{ progressMessage }}</p>
          </div>

          <strong>{{ Math.round(progressPercent) }}%</strong>
        </div>

        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: `${progressPercent}%` }"></div>
        </div>

        <div class="progress-status-grid">
          <div class="progress-status-item">
            <span>현재 단계</span>
            <strong>{{ progressStageLabel }}</strong>
          </div>
          <div class="progress-status-item">
            <span>남은 단계</span>
            <strong>{{ remainingProgressSteps.length ? remainingProgressSteps.join(" · ") : "결과 준비 중" }}</strong>
          </div>
          <div class="progress-status-item">
            <span>예상 대기</span>
            <strong>{{ progressEtaText }}</strong>
          </div>
        </div>

        <ol class="progress-steps">
          <li
              v-for="step in progressSteps"
              :key="step.key || step.stage || step.label"
              :class="{
              done: progressPercent >= Number(step.percent || 0),
              active: progressStageLabel === step.label || progressStageLabel === step.message
            }"
          >
            <span>{{ step.label || step.message }}</span>
          </li>
        </ol>

        <div class="progress-note">
          <strong>다음 단계</strong>
          <p>{{ progressStatusText }}</p>
        </div>
      </section>

      <section v-if="guidedStep === 'result'" class="guided-result-card">
        <div v-if="resultStreaming && !report" class="guided-progress-card ornate-frame">
          <AnalysisLoadingSpinner
            :percent="progressPercent"
            :label="progressStageLabel"
            :message="progressMessage"
          />

          <div class="progress-header">
            <div>
              <p class="eyebrow">결과 정리 중</p>
              <h2>{{ progressStageLabel }}</h2>
              <p>{{ progressMessage }}</p>
            </div>

            <strong>{{ Math.round(progressPercent) }}%</strong>
          </div>

          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: `${progressPercent}%` }"></div>
          </div>

          <div class="progress-status-grid">
            <div class="progress-status-item">
              <span>현재 단계</span>
              <strong>{{ progressStageLabel }}</strong>
            </div>
            <div class="progress-status-item">
              <span>남은 단계</span>
              <strong>{{ remainingProgressSteps.length ? remainingProgressSteps.join(" · ") : "결과 표시 준비" }}</strong>
            </div>
            <div class="progress-status-item">
              <span>예상 대기</span>
              <strong>{{ progressEtaText }}</strong>
            </div>
          </div>
        </div>

        <GroupedResultReportView
            v-else-if="report"
            :report="report"
            :followup-submitting="reanalyzing"
            :followup-error="followupError"
            @submit-followup="submitFollowup"
        />

        <div v-else class="empty-result">
          <h2>결과를 불러오는 중입니다</h2>
          <p>분석은 완료되었고 결과 화면을 정리하고 있습니다.</p>
          <button type="button" @click="loadReport">결과 새로고침</button>
        </div>
      </section>

      <p v-if="guidedStep !== 'input' && message" :class="messageOk ? 'msg-ok' : 'msg-error'">{{ message }}</p>
    </section>

    <details class="card diagnostic-panel">
      <summary>고급 입력/진행 상태 보기</summary>
      <p class="kv">일반 분석 화면에는 숨긴 상세 입력, 업로드, 작업 상태를 접어서 확인할 수 있습니다.</p>

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
import AnalysisLoadingSpinner from "../components/case/AnalysisLoadingSpinner.vue";
import GroupedResultReportView from "../components/easy/GroupedResultReportView.vue";
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
  progressPercent,
  progressStageLabel,
  progressMessage,
  progressSteps,
  remainingProgressSteps,
  progressEtaText,
  progressStatusText,
  resultStreaming,
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
  currentGuidedQuestionIndex,
  guidedAccidentMajorCategoryOptions,
  guidedAccidentSubtypeOptions,
  guidedAnalysisModes,
  guidedQuestions,
  visibleGuidedQuestions,
  totalGuidedQuestionCount,
  guidedQuestionProgressPercent,
  allGuidedQuestionsAnswered,
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
  selectAccidentMajorCategory,
  selectAccidentSubtype,
  selectGuidedAnalysisMode,
  answerGuidedQuestion,
  guidedQuestionId,
  goToGuidedQuestion,
  previousGuidedQuestion,
  startGuidedAnalysis,
  statusClass,
  statusLabel,
  submitFollowup,
  toggleKeyword,
  uploadLocal,
} = useCaseWorkspace(caseId);

function eventValue(event: Event) {
  return (event.target as HTMLInputElement | HTMLTextAreaElement).value;
}

function updateDescriptionText(value: string) {
  descriptionText.value = value;
}

function updateAnalysisMode(value: string) {
  analysisMode.value =
    value === "expert" ||
    value === "legal_precedent_focused" ||
    value === "full_deep_research" ||
    value === "deep_research" ||
    value === "debug"
      ? "expert"
      : "user_friendly";
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
