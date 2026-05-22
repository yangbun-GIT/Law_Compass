<template>
  <section class="case-workspace">
    <div class="workspace-head">
      <div>
        <p class="eyebrow">Case Workspace</p>
        <h2>{{ caseData?.title || "사고 케이스" }}</h2>
        <p class="kv">{{ caseData ? statusLabel(caseData.status) : "케이스 정보를 확인하는 중입니다." }}</p>
      </div>
      <div class="btn-row">
        <button class="btn secondary" :disabled="initialLoading || !!busy" @click="loadAll">새로고침</button>
        <RouterLink class="btn secondary" :to="`/cases/${caseId}/result`">결과 크게 보기</RouterLink>
      </div>
    </div>

    <p v-if="initialLoading" class="card kv">케이스와 업로드 상태를 불러오는 중입니다.</p>
    <p v-else-if="loadError" class="card msg-error">{{ loadError }}</p>

    <article v-if="caseData" class="card hero-card case-summary">
      <div>
        <span class="badge" :class="statusClass(caseData.status)">{{ statusLabel(caseData.status) }}</span>
        <h3>{{ caseData.title }}</h3>
        <p>{{ descriptionText || "사고 설명을 입력해 주세요." }}</p>
      </div>
      <div class="summary-metrics">
        <div>
          <strong>{{ selectedKeywords.length }}</strong>
          <span>선택 키워드</span>
        </div>
        <div>
          <strong>{{ uploads.length }}</strong>
          <span>업로드</span>
        </div>
        <div>
          <strong>{{ jobs.length }}</strong>
          <span>작업</span>
        </div>
      </div>
    </article>

    <article class="card easy-card">
      <div class="step-head">
        <span class="step-index">1</span>
        <div>
          <h2>사고 상황 입력</h2>
          <p class="kv">분석에 필요한 기본 사실관계와 키워드를 먼저 저장합니다.</p>
        </div>
      </div>

      <label>사고 설명
        <textarea v-model.trim="descriptionText" rows="5" placeholder="예: 신호대기 중 정차했는데 뒤 차량이 추돌했습니다. 목이 아픕니다." />
      </label>

      <div class="form-grid">
        <label>분석 모드
          <select v-model="analysisMode" @change="applyPreset">
            <option value="quick_summary">빠른 요약</option>
            <option value="rear-end-focused">후미추돌</option>
            <option value="intersection-signal-focused">교차로 신호위반</option>
            <option value="lane-change-focused">차선변경</option>
            <option value="school-zone-focused">어린이보호구역</option>
          </select>
        </label>
        <label>사고 유형
          <select v-model="facts.accident_type">
            <option value="rear_end_collision">후미추돌</option>
            <option value="intersection_collision">교차로 충돌</option>
            <option value="lane_change_collision">차선변경 충돌</option>
            <option value="pedestrian_crosswalk_accident">보행자 사고</option>
            <option value="parking_or_stopped_vehicle_accident">주차/정차 중 사고</option>
            <option value="general_collision">기타</option>
          </select>
        </label>
        <label>상대 차량 행동 <input v-model.trim="facts.opponent_behavior" placeholder="예: 뒤에서 추돌" /></label>
        <label>차량 손상 정도 <input v-model.trim="facts.damage_level" placeholder="예: 범퍼 파손" /></label>
      </div>

      <div class="chips">
        <label class="chip"><input type="checkbox" v-model="facts.stopped" /> 정차 중</label>
        <label class="chip"><input type="checkbox" v-model="facts.sudden_brake" /> 급정거</label>
        <label class="chip"><input type="checkbox" v-model="facts.injury" /> 다친 사람 있음</label>
        <label class="chip"><input type="checkbox" v-model="facts.school_zone" /> 어린이보호구역</label>
        <label class="chip"><input type="checkbox" v-model="facts.opponent_signal_violation" /> 상대 신호위반</label>
        <label class="chip"><input type="checkbox" v-model="facts.lane_change" /> 차선변경</label>
      </div>

      <div class="chips">
        <button
          v-for="kw in keywordPool"
          :key="kw"
          class="chip"
          :class="{ selected: selectedKeywords.includes(kw) }"
          type="button"
          @click="toggleKeyword(kw)"
        >
          {{ kw }}
        </button>
      </div>

      <button class="btn" :disabled="!!busy" @click="saveCaseInputs">
        {{ busy === "save" ? "저장 중..." : "입력 저장" }}
      </button>
    </article>

    <article class="card easy-card">
      <div class="step-head">
        <span class="step-index">2</span>
        <div>
          <h2>영상 업로드</h2>
          <p class="kv">현재는 S3 없이 로컬 업로드로 작동합니다.</p>
        </div>
      </div>

      <input type="file" accept="video/*" @change="onFile" />
      <p v-if="file" class="kv">선택 파일: {{ file.name }} ({{ prettySize(file.size) }})</p>

      <div class="btn-row">
        <button class="btn" :disabled="!file || !!busy" @click="uploadLocal">
          {{ busy === "upload" ? "업로드 중..." : "로컬 업로드" }}
        </button>
        <button class="btn secondary" :disabled="!activeUploadId || !!busy" @click="completeUpload">
          {{ busy === "preprocess" ? "전처리 등록 중..." : "전처리 시작" }}
        </button>
        <button class="btn secondary" :disabled="!!busy" @click="loadUploads">업로드 목록 갱신</button>
      </div>

      <label>업로드 선택
        <select v-model="selectedUploadId">
          <option value="">선택하세요</option>
          <option v-for="up in uploads" :key="up.id" :value="up.id">
            {{ up.file_name }} / {{ statusLabel(up.status) }}
          </option>
        </select>
      </label>

      <ul v-if="uploads.length" class="list-reset upload-list">
        <li v-for="up in uploads" :key="up.id">
          <strong>{{ up.file_name }}</strong>
          <span class="badge" :class="statusClass(up.status)">{{ statusLabel(up.status) }}</span>
          <p class="kv">{{ prettySize(up.file_size_bytes) }} / {{ formatDate(up.created_at) }}</p>
        </li>
      </ul>

      <div class="btn-row">
        <button class="btn secondary" :disabled="!activeUploadId || !!busy" @click="fetchViewUrl">영상 재생</button>
        <button class="btn secondary" :disabled="!activeUploadId || !!busy" @click="fetchDownloadUrl">다운로드</button>
      </div>
      <video v-if="viewUrl" controls :src="viewUrl" class="video-preview"></video>
    </article>

    <article class="card easy-card">
      <div class="step-head">
        <span class="step-index">3</span>
        <div>
          <h2>분석 요청</h2>
          <p class="kv">텍스트 분석은 즉시 결과를 만들고, 영상 분석은 작업 큐에 등록됩니다.</p>
        </div>
      </div>

      <div class="btn-row">
        <button class="btn" :disabled="!!busy" @click="analyzeText">
          {{ busy === "text-analysis" ? "분석 중..." : "텍스트 분석" }}
        </button>
        <button class="btn secondary" :disabled="!activeUploadId || !!busy" @click="analyzeVideo">
          {{ busy === "video-analysis" ? "작업 등록 중..." : "영상 분석 작업 등록" }}
        </button>
        <button class="btn secondary" :disabled="!!busy" @click="loadJobs">작업 조회</button>
        <button class="btn secondary" :disabled="!!busy" @click="loadReport">결과 새로고침</button>
      </div>

      <p v-if="message" :class="messageOk ? 'msg-ok' : 'msg-error'">{{ message }}</p>

      <ul v-if="jobs.length" class="list-reset job-list">
        <li v-for="job in jobs" :key="job.id">
          <strong>{{ job.type }}</strong>
          <span class="badge" :class="statusClass(job.status)">{{ statusLabel(job.status) }}</span>
          <p class="kv">attempts: {{ job.attempts ?? job.attempt ?? 0 }}</p>
        </li>
      </ul>
      <p v-else class="kv">등록된 분석 작업이 없습니다.</p>
    </article>

    <EasyReportView v-if="report" :report="report" />
  </section>
</template>

<script setup lang="ts">
import { useRoute } from "vue-router";
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
</script>

<style scoped>
.case-workspace {
  display: grid;
  gap: 16px;
}

.workspace-head,
.case-summary {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.workspace-head h2 {
  margin: 0;
}

.case-summary h3 {
  margin: 12px 0 8px;
  font-size: 1.5rem;
}

.case-summary p {
  margin: 0;
  line-height: 1.6;
}

.summary-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(92px, 1fr));
  gap: 10px;
  min-width: min(360px, 100%);
}

.summary-metrics div {
  padding: 14px;
  border-radius: 14px;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.14);
  text-align: center;
}

.summary-metrics strong {
  display: block;
  font-size: 1.7rem;
}

.summary-metrics span {
  color: var(--text-sub);
  font-size: 0.84rem;
}

.step-head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 14px;
}

.step-head h2,
.step-head p {
  margin: 0;
}

.step-head h2 {
  font-size: 1.55rem;
  line-height: 1.25;
}

.step-index {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  color: #06202a;
  background: linear-gradient(135deg, var(--accent), #a7f3d0);
  font-weight: 900;
}

.upload-list,
.job-list {
  display: grid;
  gap: 8px;
  margin: 12px 0;
}

.upload-list li,
.job-list li {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 6px 12px;
  align-items: center;
}

.upload-list .kv,
.job-list .kv {
  grid-column: 1 / -1;
}

@media (max-width: 900px) {
  .workspace-head,
  .case-summary {
    flex-direction: column;
  }

  .summary-metrics {
    width: 100%;
  }
}

@media (max-width: 560px) {
  .summary-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
