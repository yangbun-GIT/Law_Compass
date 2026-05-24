<template>
  <section class="admin-agent-test">
    <div class="workspace-head">
      <div>
        <p class="eyebrow">Admin Test</p>
        <h2>Agent 입력 테스트</h2>
        <p class="kv">관리자 계정에서 텍스트, 영상, 텍스트+영상 입력 경로를 분리해 확인합니다.</p>
      </div>
      <div class="btn-row">
        <RouterLink v-if="currentCaseId" class="btn secondary" :to="`/cases/${currentCaseId}/result`" target="_blank">
          결과 새 탭으로 보기
        </RouterLink>
        <button class="btn secondary" :disabled="busy" @click="resetRun">초기화</button>
      </div>
    </div>

    <article class="card test-panel">
      <div class="mode-tabs" role="tablist" aria-label="테스트 입력 방식">
        <button
          v-for="option in modeOptions"
          :key="option.value"
          type="button"
          class="mode-tab"
          :class="{ active: mode === option.value }"
          :disabled="busy"
          @click="mode = option.value"
        >
          <strong>{{ option.label }}</strong>
          <span>{{ option.description }}</span>
        </button>
      </div>

      <div class="form-grid">
        <label>테스트 케이스 제목
          <input v-model="title" placeholder="예: 관리자 영상 분석 테스트" />
        </label>
        <label>분석 모드
          <select v-model="analysisMode">
            <option value="quick_summary">빠른 요약</option>
            <option value="rear-end-focused">후방추돌</option>
            <option value="intersection-signal-focused">교차로 신호위반</option>
            <option value="lane-change-focused">차선변경</option>
            <option value="school-zone-focused">어린이보호구역</option>
            <option value="insurance-focused">보험/대응 중심</option>
          </select>
        </label>
      </div>

      <label :class="{ mutedBlock: !usesText }">사고 설명
        <textarea
          v-model="description"
          rows="5"
          :disabled="!usesText"
          :placeholder="usesText ? '예: 정차 중 뒤 차량이 후미를 추돌했습니다.' : '영상만 테스트에서는 설명 입력이 필수가 아닙니다.'"
        />
      </label>
      <p class="kv" v-if="!usesText">
        영상만 모드에서는 사고 설명, 사고 유형, 체크박스 기본값을 Agent 입력으로 보내지 않습니다.
      </p>

      <div class="form-grid" :class="{ mutedBlock: !usesText }">
        <label>사고 유형
          <select v-model="facts.accident_type" :disabled="!usesText">
            <option value="">영상/설명 기준으로 판단</option>
            <option value="rear_end_collision">후방추돌</option>
            <option value="intersection_collision">교차로 충돌</option>
            <option value="lane_change_collision">차선변경 충돌</option>
            <option value="pedestrian_crosswalk_accident">보행자 사고</option>
            <option value="parking_or_stopped_vehicle_accident">주차/정차 중 사고</option>
            <option value="bicycle_collision">자전거 사고</option>
            <option value="general_collision">기타</option>
          </select>
        </label>
        <label>상대 차량 행동
          <input v-model="facts.opponent_behavior" :disabled="!usesText" placeholder="예: 뒤에서 추돌, 좌측에서 직진" />
        </label>
        <label>신호 상태
          <input v-model="facts.signal_state" :disabled="!usesText" placeholder="예: 황색 전환, 적색 확인 필요" />
        </label>
        <label>손상/피해 정도
          <input v-model="facts.damage_level" :disabled="!usesText" placeholder="예: 후방 범퍼 파손, 인명 피해 없음" />
        </label>
      </div>

      <div class="chips" :class="{ mutedBlock: !usesText }">
        <label class="chip"><input v-model="facts.stopped" :disabled="!usesText" type="checkbox" /> 정차 중</label>
        <label class="chip"><input v-model="facts.sudden_brake" :disabled="!usesText" type="checkbox" /> 급정거</label>
        <label class="chip"><input v-model="facts.lane_change" :disabled="!usesText" type="checkbox" /> 차선변경</label>
        <label class="chip"><input v-model="facts.intersection" :disabled="!usesText" type="checkbox" /> 교차로</label>
        <label class="chip"><input v-model="facts.crosswalk_nearby" :disabled="!usesText" type="checkbox" /> 횡단보도 인접</label>
        <label class="chip"><input v-model="facts.opponent_signal_violation" :disabled="!usesText" type="checkbox" /> 상대 신호위반 의심</label>
        <label class="chip"><input v-model="facts.injury" :disabled="!usesText" type="checkbox" /> 다친 사람 있음</label>
      </div>

      <label :class="{ mutedBlock: !usesVideo }">사고 영상
        <input :disabled="!usesVideo" type="file" accept="video/*" @change="onFile" />
      </label>
      <p v-if="file" class="kv">선택 영상: {{ file.name }} / {{ prettySize(file.size) }}</p>

      <div class="btn-row">
        <button class="btn" :disabled="busy || !canRun" @click="runTest">
          {{ busy ? "테스트 실행 중..." : "테스트 실행" }}
        </button>
        <button class="btn secondary" :disabled="busy || !currentCaseId" @click="refreshOutputs">결과/진단 새로고침</button>
      </div>
      <p v-if="message" :class="messageOk ? 'msg-ok' : 'msg-error'">{{ message }}</p>
    </article>

    <article class="card run-state">
      <h3>실행 상태</h3>
      <div class="state-grid">
        <div>
          <span>케이스</span>
          <strong>{{ currentCaseId || "-" }}</strong>
        </div>
        <div>
          <span>업로드</span>
          <strong>{{ uploadId || "-" }}</strong>
        </div>
        <div>
          <span>분석 작업</span>
          <strong>{{ analysisJobId || "-" }}</strong>
        </div>
        <div>
          <span>결과</span>
          <strong>{{ report ? "표시 가능" : "대기 중" }}</strong>
        </div>
      </div>

      <ul v-if="jobs.length" class="list-reset job-list">
        <li v-for="job in jobs" :key="job.id">
          <strong>{{ job.type }}</strong>
          <span class="badge" :class="statusClass(job.status)">{{ statusLabel(job.status) }}</span>
          <p class="kv">attempt: {{ job.attempts ?? job.attempt ?? 0 }}</p>
          <p v-if="job.last_error" class="msg-error">{{ job.last_error }}</p>
        </li>
      </ul>
      <p v-else class="kv">아직 등록된 작업이 없습니다.</p>
    </article>

    <EasyReportView v-if="report" :report="report" />

    <article v-if="traceDiagnostic" class="card diagnostic-panel">
      <h3>관리자 Agent 진단</h3>
      <p class="kv">Gateway의 관리자 진단 API가 반환한 safe metadata입니다.</p>
      <pre>{{ formatJson(traceDiagnostic.diagnostic || traceDiagnostic) }}</pre>
    </article>
  </section>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import EasyReportView from "../components/easy/EasyReportView.vue";
import { api, formatApiError, type AccidentFacts } from "../api/client";
import { prettySize, statusClass, statusLabel } from "../composables/useCaseWorkspace";

type TestMode = "text" | "video" | "both";

const modeOptions: { value: TestMode; label: string; description: string }[] = [
  { value: "text", label: "입력만", description: "사용자 설명과 구조화 사실만 분석" },
  { value: "video", label: "영상만", description: "영상 업로드와 프레임 분석 경로 확인" },
  { value: "both", label: "입력+영상", description: "사용자 입력과 영상 관찰값 충돌/반영 확인" }
];

const FAILED_JOB_STATUSES = new Set(["failed", "cancelled"]);

const mode = ref<TestMode>("video");
const title = ref("관리자 Agent 테스트");
const description = ref("정차 중 뒤 차량이 후미를 추돌했습니다. 블랙박스 영상과 사용자 입력이 일치하는지 확인합니다.");
const analysisMode = ref("quick_summary");
const facts = reactive<AccidentFacts>({
  accident_type: "rear_end_collision",
  stopped: true,
  injury: false,
  signal_state: "unknown",
  opponent_behavior: "rear_collision"
});
const file = ref<File | null>(null);
const currentCaseId = ref("");
const uploadId = ref("");
const analysisJobId = ref("");
const jobs = ref<any[]>([]);
const report = ref<any>(null);
const traceDiagnostic = ref<any>(null);
const busy = ref(false);
const message = ref("");
const messageOk = ref(true);

const usesText = computed(() => mode.value === "text" || mode.value === "both");
const usesVideo = computed(() => mode.value === "video" || mode.value === "both");
const canRun = computed(() => {
  if (!title.value.trim()) return false;
  if (usesText.value && !description.value.trim()) return false;
  if (usesVideo.value && !file.value) return false;
  return true;
});

function onFile(event: Event) {
  const selected = (event.target as HTMLInputElement).files?.[0] || null;
  if (selected && !selected.type.startsWith("video/")) {
    file.value = null;
    setMessage("영상 파일만 선택할 수 있습니다.", false);
    return;
  }
  file.value = selected;
}

function resetRun() {
  currentCaseId.value = "";
  uploadId.value = "";
  analysisJobId.value = "";
  jobs.value = [];
  report.value = null;
  traceDiagnostic.value = null;
  message.value = "";
}

async function runTest() {
  if (!canRun.value) {
    setMessage("선택한 테스트 방식에 필요한 입력을 확인해 주세요.", false);
    return;
  }

  busy.value = true;
  resetOutputs();
  setMessage("테스트 케이스를 생성하고 있습니다.");

  try {
    const payload = buildAnalysisPayload();
    const created = await api.createCase({
      title: title.value.trim(),
      description_text: usesText.value ? description.value.trim() : "",
      structured_facts: payload.structured_facts,
      selected_keywords: payload.selected_keywords,
      analysis_mode: payload.analysis_mode
    });
    currentCaseId.value = created.case.id;

    if (usesVideo.value) {
      setMessage("영상을 업로드하고 전처리/분석 작업을 등록하고 있습니다.");
      const uploaded = await api.localUpload(created.case.id, file.value as File);
      uploadId.value = uploaded.upload_id;
      const queued = await api.completeUpload(uploaded.upload_id);
      analysisJobId.value = queued.job_id;
      const finalVideoJob = await pollVideoPipelineUntilAnalyzed(created.case.id);
      analysisJobId.value = finalVideoJob?.id || analysisJobId.value;
    } else {
      setMessage("텍스트 분석을 실행하고 있습니다.");
      await api.analyzeText(created.case.id, {
        description_text: description.value.trim(),
        ...payload
      });
    }

    await refreshOutputs();
    setMessage(report.value ? "테스트 분석 결과를 불러왔습니다." : "테스트 요청은 완료됐지만 아직 표시할 결과가 없습니다.", Boolean(report.value));
  } catch (error: any) {
    setMessage(formatApiError(error, "관리자 테스트 실행에 실패했습니다."), false);
  } finally {
    busy.value = false;
  }
}

function resetOutputs() {
  currentCaseId.value = "";
  uploadId.value = "";
  analysisJobId.value = "";
  jobs.value = [];
  report.value = null;
  traceDiagnostic.value = null;
}

function buildAnalysisPayload() {
  if (!usesText.value) {
    return {
      description_text: "",
      structured_facts: {},
      selected_keywords: [],
      analysis_mode: analysisMode.value
    };
  }
  return {
    description_text: usesText.value ? description.value.trim() : "",
    structured_facts: compactFacts(facts),
    selected_keywords: buildKeywords(),
    analysis_mode: analysisMode.value
  };
}

function compactFacts(input: AccidentFacts): AccidentFacts {
  return Object.fromEntries(
    Object.entries(input).filter(([, value]) => value !== "" && value !== undefined && value !== null)
  ) as AccidentFacts;
}

function buildKeywords() {
  const keywords = new Set<string>();
  if (facts.accident_type === "rear_end_collision") keywords.add("후미추돌");
  if (facts.accident_type === "intersection_collision" || facts.intersection) keywords.add("교차로");
  if (facts.lane_change) keywords.add("차선변경");
  if (facts.opponent_signal_violation || facts.signal_state) keywords.add("신호");
  keywords.add("과실비율");
  keywords.add("블랙박스");
  return [...keywords];
}

async function pollVideoPipelineUntilAnalyzed(caseId: string) {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    await sleep(attempt === 0 ? 600 : 2500);
    const response = await api.getJobs(caseId);
    jobs.value = response.items || [];
    const failedJob = jobs.value.find((job) => FAILED_JOB_STATUSES.has(String(job.status)));
    if (failedJob) {
      throw new Error(`${failedJob.type || "video job"} 작업이 실패했습니다. ${failedJob.last_error || ""}`.trim());
    }
    const videoAnalyzeJob = jobs.value.find((job) => String(job.type) === "video_analyze");
    if (videoAnalyzeJob?.id) {
      analysisJobId.value = videoAnalyzeJob.id;
    }
    if (String(videoAnalyzeJob?.status) === "succeeded") {
      return videoAnalyzeJob;
    }
  }
  throw new Error("영상 분석 작업이 아직 완료되지 않았습니다. 잠시 뒤 결과/진단 새로고침을 눌러 확인해 주세요.");
}

async function refreshOutputs() {
  if (!currentCaseId.value) return;
  try {
    jobs.value = (await api.getJobs(currentCaseId.value)).items || [];
  } catch {
    jobs.value = [];
  }
  try {
    report.value = await api.getEasyReport(currentCaseId.value);
  } catch {
    report.value = null;
  }
  try {
    traceDiagnostic.value = await api.adminGetAgentTrace(currentCaseId.value);
  } catch {
    traceDiagnostic.value = null;
  }
}

function setMessage(text: string, ok = true) {
  message.value = text;
  messageOk.value = ok;
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function formatJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}
</script>

<style scoped>
.admin-agent-test {
  display: grid;
  gap: 16px;
}

.workspace-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.workspace-head h2,
.workspace-head p {
  margin-top: 0;
}

.test-panel {
  display: grid;
  gap: 14px;
}

.mode-tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.mode-tab {
  min-height: 88px;
  padding: 14px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: var(--text-main);
  background: rgba(255, 255, 255, 0.08);
  text-align: left;
  cursor: pointer;
}

.mode-tab.active {
  border-color: rgba(103, 232, 249, 0.72);
  background: rgba(103, 232, 249, 0.18);
}

.mode-tab strong,
.mode-tab span {
  display: block;
}

.mode-tab span {
  margin-top: 6px;
  color: var(--text-sub);
  line-height: 1.45;
}

.mutedBlock {
  opacity: 0.58;
}

.run-state {
  display: grid;
  gap: 12px;
}

.run-state h3 {
  margin: 0;
}

.state-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.state-grid div {
  min-width: 0;
  padding: 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.14);
}

.state-grid span {
  display: block;
  color: var(--text-sub);
  font-size: 0.82rem;
}

.state-grid strong {
  display: block;
  overflow-wrap: anywhere;
  margin-top: 4px;
}

.job-list {
  display: grid;
  gap: 8px;
}

.job-list li {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 6px 12px;
  align-items: center;
}

.job-list .kv,
.job-list .msg-error {
  grid-column: 1 / -1;
}

.diagnostic-panel pre {
  max-height: 520px;
  overflow: auto;
  white-space: pre-wrap;
  padding: 14px;
  border-radius: 14px;
  background: rgba(2, 6, 23, 0.42);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

@media (max-width: 900px) {
  .workspace-head {
    flex-direction: column;
  }

  .mode-tabs,
  .state-grid {
    grid-template-columns: 1fr;
  }
}
</style>
