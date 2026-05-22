<template>
  <section class="agent-lab">
    <div class="workspace-head">
      <div>
        <p class="eyebrow">Agent Lab</p>
        <h2>Agent 개별 테스트</h2>
        <p class="kv">현재 케이스 입력, 영상 전처리, 최신 분석 결과를 기준으로 Agent 섹션별 산출물을 분리해서 확인합니다.</p>
      </div>
      <div class="btn-row">
        <RouterLink class="btn secondary" :to="`/cases/${caseId}/wizard`">입력 화면</RouterLink>
        <RouterLink class="btn secondary" :to="`/cases/${caseId}/result`">결과 화면</RouterLink>
        <button class="btn" :disabled="loading || !!busy" @click="loadAll">{{ loading ? "불러오는 중..." : "새로고침" }}</button>
      </div>
    </div>

    <p v-if="error" class="card msg-error">{{ error }}</p>

    <div class="lab-grid">
      <article class="card lab-panel">
        <h3>공통 입력</h3>
        <label>사고 설명
          <textarea v-model.trim="descriptionText" rows="5" />
        </label>
        <div class="form-grid">
          <label>사고 유형
            <select v-model="facts.accident_type">
              <option value="rear_end_collision">후미추돌</option>
              <option value="intersection_collision">교차로 충돌</option>
              <option value="lane_change_collision">차선변경 충돌</option>
              <option value="pedestrian_crosswalk_accident">보행자 사고</option>
              <option value="bicycle_collision">자전거 사고</option>
              <option value="general_collision">기타</option>
            </select>
          </label>
          <label>상대 차량 행동
            <input v-model.trim="facts.opponent_behavior" placeholder="rear_collision, lane_change 등" />
          </label>
        </div>
        <div class="chips">
          <label class="chip"><input type="checkbox" v-model="facts.stopped" /> 정차 중</label>
          <label class="chip"><input type="checkbox" v-model="facts.sudden_brake" /> 급정거</label>
          <label class="chip"><input type="checkbox" v-model="facts.injury" /> 부상 있음</label>
          <label class="chip"><input type="checkbox" v-model="facts.opponent_signal_violation" /> 상대 신호위반</label>
          <label class="chip"><input type="checkbox" v-model="facts.lane_change" /> 차선변경</label>
        </div>
        <label>선택 키워드
          <input v-model.trim="keywordsText" placeholder="후미추돌, 안전거리, 과실비율" />
        </label>
        <div class="btn-row">
          <button class="btn secondary" :disabled="!!busy" @click="saveInputs">입력 저장</button>
          <button class="btn" :disabled="!!busy" @click="runTextAnalysis">{{ busy === "text" ? "분석 중..." : "텍스트 분석 실행" }}</button>
          <button class="btn secondary" :disabled="!selectedUploadId || !!busy" @click="runVideoAnalysis">{{ busy === "video" ? "등록 중..." : "영상 분석 실행" }}</button>
        </div>
        <p v-if="message" :class="messageOk ? 'msg-ok' : 'msg-error'">{{ message }}</p>
      </article>

      <article class="card lab-panel">
        <h3>영상/Task 연결</h3>
        <label>업로드 선택
          <select v-model="selectedUploadId">
            <option value="">업로드 없음</option>
            <option v-for="upload in uploads" :key="upload.id" :value="upload.id">
              {{ upload.file_name }} / {{ upload.status }}
            </option>
          </select>
        </label>
        <div class="metric-row">
          <div><strong>{{ uploads.length }}</strong><span>uploads</span></div>
          <div><strong>{{ jobs.length }}</strong><span>jobs</span></div>
          <div><strong>{{ latestResultVersion }}</strong><span>result version</span></div>
        </div>
        <div class="btn-row">
          <button class="btn secondary" :disabled="loading" @click="loadUploadsAndJobs">업로드/작업 새로고침</button>
          <button class="btn secondary" :disabled="!selectedUploadId || !!busy" @click="completeUpload">영상 전처리 실행</button>
        </div>
        <div class="mini-list">
          <div v-for="job in jobs.slice(0, 6)" :key="job.id" class="mini-item">
            <strong>{{ job.type }}</strong>
            <span class="badge" :class="statusClass(job.status)">{{ job.status }}</span>
          </div>
        </div>
      </article>
    </div>

    <article class="card lab-panel">
      <div class="section-head">
        <div>
          <h3>Agent 섹션별 결과</h3>
          <p class="kv">한 번의 분석 결과를 Agent 책임 단위로 분해합니다. 법률 근거와 과실비율은 같은 입력/영상 fact를 공유하지만 별도 탭에서 확인합니다.</p>
        </div>
      </div>
      <div class="agent-tabs">
        <button
          v-for="agent in agentSections"
          :key="agent.key"
          class="tab-btn"
          :class="{ active: activeAgent === agent.key }"
          type="button"
          @click="activeAgent = agent.key"
        >
          {{ agent.label }}
        </button>
      </div>

      <div v-if="activeSection" class="agent-output-grid">
        <div class="agent-summary">
          <h4>{{ activeSection.label }}</h4>
          <p>{{ activeSection.description }}</p>
          <dl>
            <div v-for="item in activeSection.metrics" :key="item.label">
              <dt>{{ item.label }}</dt>
              <dd>{{ item.value }}</dd>
            </div>
          </dl>
        </div>
        <pre class="json-panel">{{ prettyJson(activeSection.payload) }}</pre>
      </div>
      <p v-else class="kv">아직 분석 결과가 없습니다. 텍스트 분석 또는 영상 분석을 먼저 실행해 주세요.</p>
    </article>

    <article class="card lab-panel">
      <h3>영상 추출 데이터</h3>
      <div class="agent-output-grid">
        <div>
          <h4>프레임/관찰값</h4>
          <p class="kv">Worker가 저장한 프레임 추출과 OpenAI 프레임 분석 결과입니다.</p>
          <div class="mini-list">
            <div v-for="frame in videoFrames.slice(0, 10)" :key="frame.path || frame.frame_ref || frame.time_sec" class="mini-item">
              <strong>{{ frame.role || "frame" }}</strong>
              <span>{{ frame.time_sec ?? "?" }}s</span>
            </div>
          </div>
        </div>
        <pre class="json-panel">{{ prettyJson(videoDebugPayload) }}</pre>
      </div>
    </article>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { api, formatApiError, type AccidentFacts, type CaseItem, type UploadItem } from "../api/client";

type BusyState = "" | "text" | "video" | "preprocess" | "save";
type AgentSection = {
  key: string;
  label: string;
  description: string;
  payload: unknown;
  metrics: Array<{ label: string; value: string }>;
};

const caseId = useRoute().params.caseId as string;
const caseData = ref<CaseItem | null>(null);
const uploads = ref<UploadItem[]>([]);
const jobs = ref<any[]>([]);
const debugResult = ref<any>(null);
const report = ref<any>(null);
const descriptionText = ref("");
const facts = ref<AccidentFacts>({ accident_type: "rear_end_collision", stopped: true, injury: null });
const keywordsText = ref("후미추돌, 안전거리, 과실비율");
const selectedUploadId = ref("");
const activeAgent = ref("legal");
const loading = ref(false);
const busy = ref<BusyState>("");
const error = ref("");
const message = ref("");
const messageOk = ref(true);

const technical = computed(() => debugResult.value?.technical || {});
const context = computed(() => debugResult.value?.context || {});
const latestUpload = computed(() => uploads.value.find((item) => item.id === selectedUploadId.value) || uploads.value[0] || null);
const latestResultVersion = computed(() => context.value?.analysis?.version || "-");
const selectedKeywords = computed(() => keywordsText.value.split(",").map((item) => item.trim()).filter(Boolean));
const videoFrames = computed(() => latestUpload.value?.metadata?.representative_frame_details || latestUpload.value?.metadata?.representative_frames || []);
const videoDebugPayload = computed(() => ({
  upload: latestUpload.value
    ? {
        id: latestUpload.value.id,
        file_name: latestUpload.value.file_name,
        status: latestUpload.value.status,
        metadata: latestUpload.value.metadata,
      }
    : null,
  video_input_contract: technical.value.video_input_contract,
  fact_arbitration: technical.value.fact_arbitration,
  structured_video_context: technical.value.structured_facts?.video_context,
}));

const agentSections = computed<AgentSection[]>(() => [
  {
    key: "legal",
    label: "법률 근거",
    description: "검색된 법률/KNIA 근거와 교통법규 분석 결과를 확인합니다.",
    payload: {
      legal_analysis: technical.value.legal_analysis,
      legal_evidence: technical.value.legal_evidence,
      combined_evidence: technical.value.combined_evidence,
      evidence_audit: technical.value.evidence_audit,
    },
    metrics: [
      { label: "근거 수", value: String((technical.value.legal_evidence || technical.value.evidence || []).length || 0) },
      { label: "coverage", value: technical.value.evidence_audit?.scenario_evidence_coverage?.coverage_level || "-" },
      { label: "judgment", value: technical.value.agent_judgment?.overall_status || technical.value.agent_judgment?.status || "-" },
    ],
  },
  {
    key: "fault",
    label: "과실비율",
    description: "KNIA 매칭, 기본 과실, 가감요소, 최종 과실 산출을 확인합니다.",
    payload: {
      fault_ratio: technical.value.fault_ratio,
      knia_primary_match: technical.value.knia_primary_match,
      knia_matches: technical.value.knia_matches,
      knia_evidence: technical.value.knia_evidence,
      knia_basis: technical.value.agent_judgment?.knia_basis,
    },
    metrics: [
      { label: "내 과실", value: percent(technical.value.fault_ratio?.my) },
      { label: "상대 과실", value: percent(technical.value.fault_ratio?.other) },
      { label: "KNIA", value: technical.value.knia_primary_match?.chart_no || technical.value.fault_ratio?.knia_chart_no || "-" },
    ],
  },
  {
    key: "criminal",
    label: "형사책임",
    description: "신고 필요성, 형사 리스크, 확인 체크리스트를 분리해서 봅니다.",
    payload: technical.value.legal_liability,
    metrics: [
      { label: "리스크", value: technical.value.legal_liability?.criminal_risk_level || "-" },
      { label: "신고 필요", value: yesNo(technical.value.legal_liability?.reporting_required) },
      { label: "체크 수", value: String((technical.value.legal_liability?.checklist || []).length || 0) },
    ],
  },
  {
    key: "insurance",
    label: "보험/행동",
    description: "보험 처리 안내와 사용자 행동 계획을 확인합니다.",
    payload: {
      insurance_guide: technical.value.insurance_guide,
      action_plan: technical.value.action_plan,
    },
    metrics: [
      { label: "필요 서류", value: String((technical.value.insurance_guide?.required_documents || []).length || 0) },
      { label: "단계 수", value: String((technical.value.action_plan || []).length || 0) },
      { label: "요약", value: shortText(technical.value.insurance_guide?.summary) },
    ],
  },
  {
    key: "input",
    label: "입력/영상 계약",
    description: "영상 입력 계약, 사실 중재, 보완 질문 루프를 확인합니다.",
    payload: {
      structured_facts: technical.value.structured_facts,
      video_input_contract: technical.value.video_input_contract,
      fact_arbitration: technical.value.fact_arbitration,
      input_requirements: technical.value.input_requirements,
      followup_loop: technical.value.followup_loop,
    },
    metrics: [
      { label: "영상 관찰", value: String((technical.value.video_input_contract?.accepted_observations || []).length || 0) },
      { label: "충돌", value: String((technical.value.fact_arbitration?.conflicts || []).length || 0) },
      { label: "보완 질문", value: String((technical.value.required_input_questions || []).length || 0) },
    ],
  },
  {
    key: "policy",
    label: "판단/LLM 정책",
    description: "LLM 사용 여부, 차단 사유, Agent 판단 계약을 점검합니다.",
    payload: {
      model_info: technical.value.model_info,
      agent_judgment: technical.value.agent_judgment,
      uncertainty: technical.value.uncertainty,
      disclaimers: technical.value.disclaimers,
    },
    metrics: [
      { label: "LLM", value: technical.value.model_info?.llm_enabled ? "enabled" : "fallback" },
      { label: "blockers", value: String((technical.value.agent_judgment?.decision_blockers || []).length || 0) },
      { label: "uncertainty", value: technical.value.uncertainty?.level || "-" },
    ],
  },
]);

const activeSection = computed(() => agentSections.value.find((item) => item.key === activeAgent.value) || agentSections.value[0]);

function payload() {
  return {
    description_text: descriptionText.value,
    structured_facts: facts.value,
    selected_keywords: selectedKeywords.value,
    analysis_mode: caseData.value?.analysis_mode || "quick_summary",
  };
}

function showMessage(text: string, ok = true) {
  message.value = text;
  messageOk.value = ok;
}

async function loadAll() {
  loading.value = true;
  error.value = "";
  try {
    await Promise.all([loadCase(), loadUploadsAndJobs(), loadDebugResult()]);
  } catch (err: any) {
    error.value = formatApiError(err, "Agent 테스트 데이터를 불러오지 못했습니다.");
  } finally {
    loading.value = false;
  }
}

async function loadCase() {
  const data = await api.getCase(caseId);
  caseData.value = data.case;
  descriptionText.value = data.case.description_text || "";
  facts.value = { ...facts.value, ...(data.case.structured_facts || {}) };
  keywordsText.value = data.case.selected_keywords?.length ? data.case.selected_keywords.join(", ") : keywordsText.value;
}

async function loadUploadsAndJobs() {
  const [uploadResp, jobResp] = await Promise.all([api.getCaseUploads(caseId), api.getJobs(caseId)]);
  uploads.value = uploadResp.items || [];
  jobs.value = jobResp.items || [];
  if (!selectedUploadId.value && uploads.value.length) selectedUploadId.value = uploads.value[0].id;
}

async function loadDebugResult() {
  try {
    const data = await api.getDebugResult(caseId);
    debugResult.value = data.debug || null;
    report.value = data.report || data.result || null;
  } catch (err: any) {
    if (Number(err?.status || 0) === 404) {
      debugResult.value = null;
      report.value = null;
      return;
    }
    throw err;
  }
}

async function saveInputs() {
  busy.value = "save";
  try {
    await api.updateCase(caseId, {
      description_text: descriptionText.value,
      structured_facts: facts.value,
      selected_keywords: selectedKeywords.value,
      analysis_mode: caseData.value?.analysis_mode || "quick_summary",
    });
    showMessage("입력을 저장했습니다.");
    await loadCase();
    return true;
  } catch (err: any) {
    showMessage(formatApiError(err, "입력 저장에 실패했습니다."), false);
    return false;
  } finally {
    busy.value = "";
  }
}

async function runTextAnalysis() {
  if (!(await saveInputs())) return;
  busy.value = "text";
  try {
    await api.analyzeText(caseId, payload());
    showMessage("텍스트 분석을 완료했습니다.");
    await loadAll();
  } catch (err: any) {
    showMessage(formatApiError(err, "텍스트 분석에 실패했습니다."), false);
  } finally {
    busy.value = "";
  }
}

async function completeUpload() {
  if (!selectedUploadId.value) return;
  busy.value = "preprocess";
  try {
    const data = await api.completeUpload(selectedUploadId.value);
    showMessage(`영상 전처리 작업을 등록했습니다. job=${data.job_id}`);
    await loadUploadsAndJobs();
  } catch (err: any) {
    showMessage(formatApiError(err, "영상 전처리 등록에 실패했습니다."), false);
  } finally {
    busy.value = "";
  }
}

async function runVideoAnalysis() {
  if (!selectedUploadId.value) return;
  if (!(await saveInputs())) return;
  busy.value = "video";
  try {
    const data = await api.analyzeVideo(caseId, { upload_id: selectedUploadId.value, ...payload() });
    showMessage(`영상 분석 작업을 등록했습니다. job=${data.job_id}`);
    await loadUploadsAndJobs();
  } catch (err: any) {
    showMessage(formatApiError(err, "영상 분석 작업 등록에 실패했습니다."), false);
  } finally {
    busy.value = "";
  }
}

function prettyJson(value: unknown) {
  return JSON.stringify(value ?? null, null, 2);
}

function percent(value: unknown) {
  const n = Number(value);
  return Number.isFinite(n) ? `${Math.round(n)}%` : "-";
}

function yesNo(value: unknown) {
  if (value === true) return "예";
  if (value === false) return "아니오";
  return "-";
}

function shortText(value: unknown) {
  const text = String(value || "").trim();
  return text.length > 24 ? `${text.slice(0, 24)}...` : text || "-";
}

function statusClass(status?: string) {
  if (status === "succeeded" || status === "completed" || status === "ready") return "ok";
  if (status === "failed") return "fail";
  return "warn";
}

onMounted(loadAll);
</script>

<style scoped>
.agent-lab {
  display: grid;
  gap: 16px;
}

.workspace-head,
.section-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.workspace-head h2,
.lab-panel h3,
.agent-summary h4 {
  margin: 0;
}

.lab-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(320px, 0.7fr);
  gap: 14px;
}

.lab-panel {
  display: grid;
  gap: 12px;
}

.metric-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.metric-row div {
  min-height: 78px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.07);
  padding: 12px;
}

.metric-row strong {
  display: block;
  font-size: 1.8rem;
}

.metric-row span {
  color: var(--text-sub);
  font-size: 0.85rem;
}

.agent-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tab-btn {
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-main);
  padding: 9px 12px;
  cursor: pointer;
}

.tab-btn.active {
  border-color: rgba(103, 232, 249, 0.7);
  background: rgba(103, 232, 249, 0.18);
}

.agent-output-grid {
  display: grid;
  grid-template-columns: minmax(260px, 0.55fr) minmax(0, 1.45fr);
  gap: 14px;
}

.agent-summary {
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.07);
  padding: 14px;
}

.agent-summary p {
  color: var(--text-sub);
  line-height: 1.6;
}

.agent-summary dl {
  display: grid;
  gap: 8px;
  margin: 0;
}

.agent-summary dl div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.15);
  padding-bottom: 8px;
}

.agent-summary dt {
  color: var(--text-sub);
}

.agent-summary dd {
  margin: 0;
  font-weight: 800;
}

.json-panel {
  min-height: 320px;
  max-height: 620px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(2, 6, 23, 0.58);
  color: #dff7ff;
  padding: 14px;
  margin: 0;
  font-size: 0.86rem;
  line-height: 1.5;
}

.mini-list {
  display: grid;
  gap: 8px;
}

.mini-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.06);
  padding: 9px 10px;
}

@media (max-width: 980px) {
  .workspace-head,
  .section-head {
    flex-direction: column;
  }

  .lab-grid,
  .agent-output-grid {
    grid-template-columns: 1fr;
  }
}
</style>
