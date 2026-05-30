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
            <option v-for="option in analysisModeOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
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
        <label>사고 대분류
          <select v-model="facts.accident_party_type" :disabled="!usesText">
            <option v-for="option in partyTypeOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
        <label>사고 유형
          <select v-model="facts.accident_type" :disabled="!usesText">
            <option v-for="option in accidentTypeOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
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
        <label class="chip"><input v-model="facts.front_vehicle_stopped" :disabled="!usesText" type="checkbox" /> 앞차 정차</label>
        <label class="chip"><input v-model="facts.centerline_crossed" :disabled="!usesText" type="checkbox" /> 중앙선 침범</label>
        <label class="chip"><input v-model="facts.road_obstruction" :disabled="!usesText" type="checkbox" /> 도로 장애물</label>
        <label class="chip"><input v-model="facts.illegal_parking_obstruction" :disabled="!usesText" type="checkbox" /> 불법 주정차 영향</label>
        <label class="chip"><input v-model="facts.opposing_vehicle_present" :disabled="!usesText" type="checkbox" /> 대향 차량</label>
        <label class="chip"><input v-model="facts.stopped_vehicle_without_lights" :disabled="!usesText" type="checkbox" /> 무등화 정차 차량</label>
        <label class="chip"><input v-model="facts.highway_or_expressway" :disabled="!usesText" type="checkbox" /> 고속도로/전용도로</label>
        <label class="chip"><input v-model="facts.bicycle_involved" :disabled="!usesText" type="checkbox" /> 자전거 관련</label>
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
          <span>영상 처리</span>
          <strong>{{ preprocessJobId || "-" }}</strong>
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

    <article v-if="videoPreprocessDiagnostic" class="card video-diagnostic-panel">
      <div class="diagnostic-head">
        <div>
          <p class="eyebrow">Video Preprocess</p>
          <h3>Agent 전달 전 영상 처리 결과</h3>
          <p class="kv">
            YOLO 객체 후보와 OpenAI 프레임 관찰값이 Agent로 넘어가기 전에 어떤 데이터로 정리됐는지 확인합니다.
          </p>
        </div>
        <button
          v-if="canContinueAgentAnalysis"
          class="btn"
          :disabled="busy"
          @click="continueAgentAnalysis"
        >
          {{ busy === "video-analysis" ? "Agent 분석 실행 중..." : "Agent 분석 계속 실행" }}
        </button>
      </div>

      <div class="diagnostic-grid">
        <div class="diagnostic-stat">
          <span>대표 프레임</span>
          <strong>{{ diagnosticFrameCount }}장</strong>
        </div>
        <div class="diagnostic-stat">
          <span>OpenAI 관찰</span>
          <strong>{{ diagnosticOpenAiCount }}개</strong>
          <small>{{ diagnosticOpenAiStatus }}</small>
        </div>
        <div class="diagnostic-stat">
          <span>YOLO 관찰</span>
          <strong>{{ diagnosticYoloCount }}개</strong>
          <small>{{ diagnosticYoloStatus }}</small>
        </div>
        <div class="diagnostic-stat">
          <span>병합 관찰값</span>
          <strong>{{ diagnosticMergedCount }}개</strong>
        </div>
      </div>

      <div class="observation-section">
        <h4>사람이 보기 쉬운 관찰값</h4>
        <ul v-if="diagnosticObservations.length" class="list-reset observation-list">
          <li v-for="(item, index) in diagnosticObservations" :key="`${item.field}-${index}`">
            <div>
              <strong>{{ item.display_label || observationFieldLabel(item.field) }}</strong>
              <span class="badge" :class="diagnosticStatusClass(item.status)">
                {{ item.status_label || item.source_family || "merged" }}
              </span>
            </div>
            <p>{{ item.display_value || observationValueLabel(item.field, item.value) }}</p>
            <p v-if="item.reason" class="kv">{{ item.reason }}</p>
            <p class="kv">
              신뢰도 {{ formatConfidence(item.confidence) }}
              <template v-if="item.frame_ref_count">/ 프레임 {{ item.frame_ref_count }}장</template>
              <template v-if="item.source_families?.length">/ 출처 {{ item.source_families.join(", ") }}</template>
              <template v-else-if="item.source_family">/ 출처 {{ item.source_family }}</template>
            </p>
          </li>
        </ul>
        <p v-else class="kv">아직 영상 관찰값이 없습니다. 영상 전처리 작업 완료 후 표시됩니다.</p>
      </div>

      <details class="raw-diagnostic">
        <summary>원본 진단 JSON 보기</summary>
        <pre>{{ formatJson(videoPreprocessDiagnostic) }}</pre>
      </details>
    </article>

    <EasyReportView
      v-if="report"
      :report="report"
      :analysis-mode="analysisMode"
      :followup-submitting="reanalyzing"
      :followup-error="followupError"
      @submit-followup="submitFollowup"
    />

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

const analysisModeOptions = [
  { value: "user_friendly", label: "일반사용자모드" },
  { value: "expert", label: "전문가모드" }
];

const partyTypeOptions = [
  { value: "", label: "영상/설명 기준으로 판단" },
  { value: "car_vs_car", label: "차 대 차" },
  { value: "car_vs_person", label: "차 대 사람" },
  { value: "car_vs_bicycle", label: "차 대 자전거/이륜" },
  { value: "car_vs_object", label: "차 대 물체/시설물" },
  { value: "single_vehicle", label: "단독 사고" },
  { value: "unknown", label: "확인 필요" }
];

const accidentTypeOptions = [
  { value: "", label: "영상/설명 기준으로 판단" },
  { value: "rear_end_collision", label: "후방추돌/앞뒤 충돌" },
  { value: "right_turn_front_stop", label: "우회전 중 앞차 정차 추돌" },
  { value: "intersection_collision", label: "교차로 충돌" },
  { value: "intersection_signal_violation", label: "교차로 신호 쟁점" },
  { value: "lane_change_collision", label: "차선변경/진로변경 충돌" },
  { value: "centerline_obstacle_collision", label: "중앙선/장애물 회피 중 대향 충돌" },
  { value: "stopped_vehicle_collision", label: "정차 차량/무등화 차량 추돌" },
  { value: "non_contact_trigger", label: "비접촉 유발/급정지 유발" },
  { value: "pedestrian_crosswalk_accident", label: "보행자 사고" },
  { value: "bicycle_collision", label: "자전거 사고" },
  { value: "object_collision", label: "물체/시설물 충돌" },
  { value: "single_vehicle_accident", label: "단독 사고" },
  { value: "general_collision", label: "기타/불명확" }
];

const FAILED_JOB_STATUSES = new Set(["failed", "cancelled"]);

const mode = ref<TestMode>("video");
const title = ref("관리자 Agent 테스트");
const description = ref("");
const analysisMode = ref("user_friendly");
const facts = reactive<AccidentFacts>({});
const file = ref<File | null>(null);
const currentCaseId = ref("");
const uploadId = ref("");
const preprocessJobId = ref("");
const analysisJobId = ref("");
const jobs = ref<any[]>([]);
const report = ref<any>(null);
const videoPreprocessDiagnostic = ref<any>(null);
const traceDiagnostic = ref<any>(null);
const busy = ref(false);
const message = ref("");
const messageOk = ref(true);
const reanalyzing = ref(false);
const followupError = ref("");

const usesText = computed(() => mode.value === "text" || mode.value === "both");
const usesVideo = computed(() => mode.value === "video" || mode.value === "both");
const hasCompletedVideoAnalysis = computed(() => jobs.value.some(isCompletedVideoAnalysisJob));
const canContinueAgentAnalysis = computed(() => Boolean(
  currentCaseId.value
  && uploadId.value
  && videoPreprocessDiagnostic.value
  && !hasCompletedVideoAnalysis.value
));
const diagnosticFrameCount = computed(() => videoPreprocessDiagnostic.value?.frame_selection?.representative_frame_count ?? 0);
const diagnosticOpenAiCount = computed(() => videoPreprocessDiagnostic.value?.openai_frame_analysis?.observation_count ?? 0);
const diagnosticYoloCount = computed(() => videoPreprocessDiagnostic.value?.yolo_frame_analysis?.observation_count ?? 0);
const diagnosticMergedCount = computed(() => videoPreprocessDiagnostic.value?.merged_observations?.observation_count ?? 0);
const diagnosticObservations = computed(() => (
  videoPreprocessDiagnostic.value?.merged_observations?.human_observations
  ?? videoPreprocessDiagnostic.value?.merged_observations?.observations
  ?? []
));
const diagnosticOpenAiStatus = computed(() => {
  const payload = videoPreprocessDiagnostic.value?.openai_frame_analysis;
  if (!payload) return "대기";
  return payload.enabled ? `${payload.model || "모델"} / ${payload.selected_frame_count ?? 0}장` : "비활성";
});
const diagnosticYoloStatus = computed(() => {
  const payload = videoPreprocessDiagnostic.value?.yolo_frame_analysis;
  if (!payload) return "대기";
  return payload.enabled ? `${payload.model || "모델"} / ${payload.selected_frame_count ?? 0}장` : "비활성";
});
const canRun = computed(() => {
  if (!title.value.trim()) return false;
  if (usesText.value && !description.value.trim()) return false;
  if (usesVideo.value && !file.value) return false;
  return true;
});

function isSuccessfulJobStatus(status: unknown) {
  return ["succeeded", "completed", "success", "done", "finished"].includes(String(status));
}

function isCompletedVideoAnalysisJob(job: any) {
  return String(job?.type) === "video_analyze" && isSuccessfulJobStatus(job?.status);
}

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
  preprocessJobId.value = "";
  analysisJobId.value = "";
  jobs.value = [];
  report.value = null;
  videoPreprocessDiagnostic.value = null;
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
      setMessage("영상을 업로드하고 Agent 전달 전 영상 처리 작업을 등록하고 있습니다.");
      const uploaded = await api.localUpload(created.case.id, file.value as File);
      uploadId.value = uploaded.upload_id;
      const queued = await api.completeUpload(uploaded.upload_id, { autoAnalyzeAfterPreprocess: false });
      preprocessJobId.value = queued.job_id;
      await pollVideoPreprocessUntilReady(created.case.id);
      await loadVideoPreprocessDiagnostic();
      setMessage("영상 처리 결과를 불러왔습니다. 아래 관찰값을 확인한 뒤 Agent 분석 계속 실행을 눌러 주세요.");
    } else {
      setMessage("텍스트 분석을 실행하고 있습니다.");
      await api.analyzeText(created.case.id, {
        description_text: description.value.trim(),
        ...payload
      });
    }

    await refreshOutputs();
    if (usesVideo.value) return;
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
  preprocessJobId.value = "";
  analysisJobId.value = "";
  jobs.value = [];
  report.value = null;
  videoPreprocessDiagnostic.value = null;
  traceDiagnostic.value = null;
  followupError.value = "";
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
  if (facts.accident_party_type === "car_vs_car") keywords.add("차대차");
  if (facts.accident_party_type === "car_vs_person") keywords.add("보행자");
  if (facts.accident_party_type === "car_vs_bicycle") keywords.add("자전거");
  if (facts.accident_type === "rear_end_collision") keywords.add("후미추돌");
  if (facts.accident_type === "right_turn_front_stop") keywords.add("우회전");
  if (facts.accident_type === "centerline_obstacle_collision" || facts.centerline_crossed) keywords.add("중앙선");
  if (facts.accident_type === "stopped_vehicle_collision" || facts.stopped_vehicle_without_lights) keywords.add("정차 차량");
  if (facts.accident_type === "non_contact_trigger") keywords.add("비접촉 유발");
  if (facts.accident_type === "intersection_collision" || facts.accident_type === "intersection_signal_violation" || facts.intersection) keywords.add("교차로");
  if (facts.lane_change) keywords.add("차선변경");
  if (facts.opponent_signal_violation || (facts.signal_state && facts.signal_state !== "unknown")) keywords.add("신호");
  if (facts.road_obstruction || facts.illegal_parking_obstruction) keywords.add("도로 장애물");
  keywords.add("과실비율");
  keywords.add("블랙박스");
  return [...keywords];
}

async function submitFollowup(answers: Record<string, string>) {
  if (!currentCaseId.value) return;
  followupError.value = "";
  reanalyzing.value = true;
  try {
    const payload = buildAnalysisPayload();
    const response = await api.reanalyzeText(currentCaseId.value, {
      description_text: usesText.value ? description.value.trim() : undefined,
      structured_facts: usesText.value ? payload.structured_facts : undefined,
      selected_keywords: usesText.value ? payload.selected_keywords : [],
      analysis_mode: analysisMode.value,
      followup_answers: answers
    });
    report.value = response.report || response.result || report.value;
    await refreshOutputs();
    setMessage("보완 답변을 반영해 재분석했습니다.");
  } catch (error: any) {
    followupError.value = formatApiError(error, "보완 답변을 반영해 재분석하지 못했습니다.");
  } finally {
    reanalyzing.value = false;
  }
}

async function continueAgentAnalysis() {
  if (!currentCaseId.value || !uploadId.value) {
    setMessage("먼저 영상 처리 결과를 만든 뒤 Agent 분석을 실행해 주세요.", false);
    return;
  }

  busy.value = true;
  setMessage("영상 처리 결과와 입력값을 Agent 분석으로 전달하고 있습니다.");

  try {
    const payload = buildAnalysisPayload();
    await api.analyzeVideo(currentCaseId.value, {
      upload_id: uploadId.value,
      structured_facts: payload.structured_facts,
      selected_keywords: payload.selected_keywords,
      analysis_mode: payload.analysis_mode
    });
    const finalVideoJob = await pollVideoPipelineUntilAnalyzed(currentCaseId.value);
    analysisJobId.value = finalVideoJob?.id || analysisJobId.value;
    await refreshOutputs();
    setMessage(report.value ? "Agent 분석 결과를 불러왔습니다." : "Agent 분석은 완료됐지만 아직 표시할 결과가 없습니다.", Boolean(report.value));
  } catch (error: any) {
    setMessage(formatApiError(error, "Agent 분석 실행에 실패했습니다."), false);
  } finally {
    busy.value = false;
  }
}

async function loadVideoPreprocessDiagnostic() {
  if (!uploadId.value) return null;
  const response = await api.adminGetVideoPreprocessDiagnostic(uploadId.value);
  videoPreprocessDiagnostic.value = response.diagnostic || response;
  return videoPreprocessDiagnostic.value;
}

async function pollVideoPreprocessUntilReady(caseId: string) {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    await sleep(attempt === 0 ? 600 : 2000);
    const response = await api.getJobs(caseId);
    jobs.value = response.items || [];
    const failedJob = jobs.value.find((job) => FAILED_JOB_STATUSES.has(String(job.status)));
    if (failedJob) {
      throw new Error(`${failedJob.type || "video job"} 작업이 실패했습니다. ${failedJob.last_error || ""}`.trim());
    }
    const preprocessJob = jobs.value.find((job) => String(job.type) === "video_preprocess");
    if (preprocessJob?.id) {
      preprocessJobId.value = preprocessJob.id;
    }
    if (String(preprocessJob?.status) === "succeeded") {
      return preprocessJob;
    }
  }
  throw new Error("영상 처리 작업이 아직 완료되지 않았습니다. 잠시 뒤 결과/진단 새로고침을 눌러 확인해 주세요.");
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
    if (isSuccessfulJobStatus(videoAnalyzeJob?.status)) {
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
  const shouldLoadReport = !usesVideo.value || jobs.value.some(isCompletedVideoAnalysisJob);
  if (shouldLoadReport) {
    try {
      report.value = await api.getEasyReport(currentCaseId.value);
    } catch {
      report.value = null;
    }
  } else {
    report.value = null;
  }
  try {
    traceDiagnostic.value = await api.adminGetAgentTrace(currentCaseId.value);
  } catch {
    traceDiagnostic.value = null;
  }
  try {
    if (uploadId.value) await loadVideoPreprocessDiagnostic();
  } catch {
    videoPreprocessDiagnostic.value = null;
  }
}

function setMessage(text: string, ok = true) {
  message.value = text;
  messageOk.value = ok;
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function observationFieldLabel(field: string) {
  const labels: Record<string, string> = {
    accident_event_candidate: "사고 발생 구간 후보",
    primary_collision_target: "주 충돌 대상 후보",
    collision_partner_type: "충돌 상대 유형",
    direct_collision_partner_type: "직접 충돌 상대",
    collision_point_visible: "충돌 지점 보임",
    collision_point_location: "충돌 위치",
    impact_direction: "충돌 방향",
    stopped: "정차 여부",
    front_vehicle_stopped: "앞차 정차",
    pedestrian_visible: "보행자 보임",
    pedestrian_context: "보행자 관련 관찰",
    bicycle_visible: "자전거 보임",
    motorcycle_visible: "이륜차 보임",
    traffic_light_visible: "신호등 보임",
    signal_state: "신호 상태",
    visual_evidence_limited: "영상 근거 제한",
    damage_level: "파손 정도"
  };
  return labels[field] || field;
}

function diagnosticStatusClass(status: string) {
  if (status === "conflict") return "needs-review";
  if (status === "candidate") return "pending";
  if (status === "confirmed") return "done";
  return "";
}

function observationValueLabel(field: string, value: unknown) {
  const text = String(value);
  const labels: Record<string, string> = {
    true: "예",
    false: "아니오",
    vehicle: "차량",
    vehicle_candidate: "차량 후보",
    pedestrian: "보행자",
    pedestrian_candidate: "보행자 후보",
    bicycle: "자전거",
    bicycle_candidate: "자전거 후보",
    motorcycle: "이륜차",
    motorcycle_candidate: "이륜차 후보",
    object: "물체",
    object_candidate: "물체 후보",
    front_ego_to_rear_opponent: "내 차량 전면과 상대 후면 방향",
    front_right: "전방 우측",
    moderate: "중간 정도"
  };
  if (field === "primary_collision_target" && text.endsWith("_candidate")) {
    return `${labels[text] || text}입니다. 확정 사실이 아니라 Agent 판단 전 확인 후보입니다.`;
  }
  return labels[text] || text;
}

function formatConfidence(value: unknown) {
  const numberValue = Number(value);
  if (!Number.isFinite(numberValue)) return "-";
  return `${Math.round(numberValue * 100)}%`;
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
  border-color: rgba(201, 169, 98, 0.72);
  background: rgba(201, 169, 98, 0.18);
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

.video-diagnostic-panel {
  display: grid;
  gap: 16px;
}

.diagnostic-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.diagnostic-head h3,
.diagnostic-head p {
  margin-top: 0;
}

.diagnostic-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.diagnostic-stat {
  min-height: 92px;
  padding: 14px;
  border: 1px solid rgba(143, 162, 185, 0.32);
  border-radius: 8px;
  background: rgba(12, 21, 33, 0.36);
}

.diagnostic-stat span,
.diagnostic-stat small {
  display: block;
  color: #bed0e1;
}

.diagnostic-stat strong {
  display: block;
  margin: 6px 0;
  font-size: 1.6rem;
}

.observation-section {
  display: grid;
  gap: 10px;
}

.observation-section h4 {
  margin: 0;
}

.observation-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.observation-list li {
  display: grid;
  gap: 6px;
  padding: 12px;
  border: 1px solid rgba(94, 226, 240, 0.22);
  border-radius: 8px;
  background: rgba(13, 23, 35, 0.42);
}

.observation-list li > div {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
}

.observation-list p {
  margin: 0;
}

.observation-list .badge.needs-review {
  color: #fde68a;
  border-color: rgba(250, 204, 21, 0.65);
}

.observation-list .badge.pending {
  color: #cffafe;
  border-color: rgba(94, 234, 212, 0.58);
}

.observation-list .badge.done {
  color: #dcfce7;
  border-color: rgba(134, 239, 172, 0.58);
}

.raw-diagnostic pre {
  max-height: 420px;
  overflow: auto;
  white-space: pre-wrap;
}

@media (max-width: 900px) {
  .workspace-head {
    flex-direction: column;
  }

  .mode-tabs,
  .state-grid,
  .diagnostic-grid,
  .observation-list {
    grid-template-columns: 1fr;
  }

  .diagnostic-head {
    display: grid;
  }
}
</style>
