import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { api, formatApiError, type AccidentFacts, type CaseItem, type UploadItem } from "../api/client";

export type CaseWorkspaceBusyState = "" | "save" | "upload" | "preprocess" | "text-analysis" | "video-analysis";

type JobItem = {
  id: string;
  type: string;
  status: string;
  attempts?: number;
  attempt?: number;
};

const DEFAULT_KEYWORDS = ["블랙박스", "과실비율", "교통사고", "보험처리"];
const RUNNING_JOB_STATUSES = ["queued", "running", "retrying", "processing", "analyzing"];
export const guidedAccidentTypeOptions = [
  { label: "뒤에서 들이받은 사고", scenario_type: "rear_end_collision", accident_party_type: "car_vs_car", hint: "내 차 앞뒤 방향으로 뒤차가 추돌한 경우" },
  { label: "앞차가 갑자기 멈춘 사고", scenario_type: "rear_end_collision", accident_party_type: "car_vs_car", hint: "앞차 급정거 여부가 쟁점인 경우" },
  { label: "교차로에서 부딪힌 사고", scenario_type: "intersection_collision", accident_party_type: "car_vs_car", hint: "직진, 좌회전, 우회전 중 충돌한 경우" },
  { label: "신호위반이 관련된 사고", scenario_type: "intersection_signal_violation", accident_party_type: "car_vs_car", hint: "빨간불 진입이나 신호 확인이 핵심인 경우" },
  { label: "차선변경 중 부딪힌 사고", scenario_type: "lane_change_collision", accident_party_type: "car_vs_car", hint: "끼어들기, 진로변경, 방향지시등이 쟁점인 경우" },
  { label: "자전거와 부딪힌 사고", scenario_type: "bicycle_collision", accident_party_type: "car_vs_bicycle", hint: "자전거도로, 차도, 횡단보도 주행이 관련된 경우" },
  { label: "보행자와 부딪힌 사고", scenario_type: "pedestrian_crosswalk_accident", accident_party_type: "car_vs_person", hint: "횡단보도, 보행자 신호, 어린이보호구역이 관련된 경우" },
  { label: "시설물/물체와 부딪힌 사고", scenario_type: "object_collision", accident_party_type: "car_vs_object", hint: "가드레일, 기둥, 주차물, 낙하물이 관련된 경우" },
  { label: "단독 사고", scenario_type: "single_vehicle_accident", accident_party_type: "single_vehicle", hint: "다른 차량 없이 내 차량만 사고가 난 경우" },
  { label: "잘 모르겠어요", scenario_type: "", accident_party_type: "unknown", hint: "설명과 영상으로 가장 가능성 높은 유형을 추정합니다" },
];

export const guidedAnalysisModes = [
  { value: "quick_summary", label: "빠른 요약", hint: "핵심 결론과 과실비율만 짧게 봅니다." },
  { value: "fault_ratio_focused", label: "과실비율 중심", hint: "급정거, 제동등, 정차 위치 같은 가감요소를 자세히 확인합니다." },
  { value: "legal_precedent_focused", label: "법률/판례 근거 중심", hint: "관련 법규, KNIA 해설, 판례 부족 여부를 함께 봅니다." },
  { value: "insurance_response_focused", label: "보험 대응 중심", hint: "보험사에 말할 핵심 문장과 챙길 자료를 정리합니다." },
  { value: "full_deep_research", label: "전체 심층 리서치 분석", hint: "사실, 영상, KNIA, 법률, 보험 대응을 모두 펼쳐 봅니다." },
];

export const fallbackGuidedQuestions = [
  {
    question_id: "rear_end.stopped",
    title: "정차 여부",
    plain_question: "내 차가 사고 직전에 완전히 멈춰 있었나요?",
    why_it_matters: "정상적으로 멈춰 있던 앞차를 뒤차가 들이받은 사고라면 뒤차 책임을 크게 봅니다.",
    choices: [{ value: "yes", label: "예" }, { value: "no", label: "아니오" }, { value: "unknown", label: "잘 모르겠어요" }],
    fact_key: "stopped",
  },
  {
    question_id: "rear_end.stop_reason",
    title: "정차한 이유",
    plain_question: "왜 멈춰 있었나요?",
    why_it_matters: "빨간불 신호대기, 정체, 보행자 회피처럼 정당한 이유가 있으면 내 과실을 올리지 않는 쪽으로 봅니다.",
    choices: [
      { value: "red_light", label: "빨간불 신호대기" },
      { value: "traffic", label: "앞차 정체" },
      { value: "pedestrian_or_obstacle", label: "보행자/장애물 때문에 정지" },
      { value: "no_reason", label: "이유 없이 갑자기 정지" },
      { value: "unknown", label: "잘 모르겠어요" },
    ],
    fact_key: "stop_reason",
  },
  {
    question_id: "rear_end.brake_light",
    title: "브레이크등",
    plain_question: "브레이크등이 정상적으로 켜졌나요?",
    why_it_matters: "브레이크등 고장은 내 과실이 일부 생길 수 있는 요소입니다.",
    choices: [{ value: "normal", label: "정상 작동" }, { value: "failed", label: "고장 또는 미점등" }, { value: "unknown", label: "잘 모르겠어요" }],
    fact_key: "brake_light",
  },
];

export const caseKeywordPool = [
  "후미추돌",
  "안전거리",
  "신호위반",
  "교차로",
  "차선변경",
  "방향지시등",
  "횡단보도",
  "보행자",
  "어린이보호구역",
  "민식이법",
  "대인접수",
  "진단서"
];

export function prettySize(bytes: number) {
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function formatDate(iso: string) {
  return new Date(iso).toLocaleString("ko-KR", { dateStyle: "medium", timeStyle: "short" });
}

export function statusLabel(status?: string) {
  const labels: Record<string, string> = {
    draft: "작성 중",
    ready: "분석 가능",
    queued: "대기 중",
    running: "분석 중",
    retrying: "다시 확인 중",
    processing: "영상 확인 중",
    analyzing: "사고 장면 분석 중",
    completed: "완료",
    succeeded: "완료",
    ready_for_analysis: "분석 준비",
    failed: "분석 실패. 다시 시도해 주세요.",
    uploaded: "업로드 완료"
  };
  return status ? labels[status] || status : "상태 없음";
}

export function statusClass(status?: string) {
  if (status === "completed" || status === "ready" || status === "ready_for_analysis" || status === "uploaded") return "ok";
  if (status === "failed") return "fail";
  return "warn";
}

export function useCaseWorkspace(caseId: string) {
  const caseData = ref<CaseItem | null>(null);
  const descriptionText = ref("");
  const facts = ref<AccidentFacts>({ injury: null });
  const analysisMode = ref("quick_summary");
  const selectedKeywords = ref<string[]>([...DEFAULT_KEYWORDS]);
  const file = ref<File | null>(null);
  const uploads = ref<UploadItem[]>([]);
  const selectedUploadId = ref("");
  const viewUrl = ref("");
  const jobs = ref<JobItem[]>([]);
  const progress = ref<any>(null);
  const report = ref<any>(null);
  const message = ref("");
  const messageOk = ref(true);
  const initialLoading = ref(false);
  const loadError = ref("");
  const followupError = ref("");
  const reanalyzing = ref(false);
  const busy = ref<CaseWorkspaceBusyState>("");
  const guidedStep = ref<"input" | "accident-type" | "purpose" | "questions" | "analyzing" | "result">("input");
  const guidedAnswers = ref<Record<string, string>>({});
  let pollTimer: number | null = null;

  const activeUploadId = computed(() => selectedUploadId.value);

  function showMessage(text: string, ok = true) {
    message.value = text;
    messageOk.value = ok;
  }

  function onFile(e: Event) {
    const nextFile = (e.target as HTMLInputElement).files?.[0] || null;
    if (nextFile && !nextFile.type.startsWith("video/")) {
      file.value = null;
      showMessage("영상 파일만 업로드할 수 있습니다.", false);
      return;
    }
    file.value = nextFile;
    viewUrl.value = "";
  }

  function toggleKeyword(kw: string) {
    selectedKeywords.value = selectedKeywords.value.includes(kw)
      ? selectedKeywords.value.filter((x) => x !== kw)
      : [...selectedKeywords.value, kw];
  }

  function payload() {
    return {
      description_text: descriptionText.value,
      structured_facts: facts.value,
      selected_keywords: selectedKeywords.value,
      analysis_mode: analysisMode.value
    };
  }

  async function loadCase() {
    const data = await api.getCase(caseId);
    caseData.value = data.case;
    descriptionText.value = data.case.description_text || "";
    facts.value = { ...facts.value, ...(data.case.structured_facts || {}) };
    selectedKeywords.value = data.case.selected_keywords?.length ? data.case.selected_keywords : selectedKeywords.value;
    analysisMode.value = data.case.analysis_mode || analysisMode.value;
  }

  function isAnalysisReady() {
    return Boolean(descriptionText.value.trim() || activeUploadId.value || file.value);
  }

  async function saveCaseInputs() {
    if (!descriptionText.value.trim()) {
      descriptionText.value = "영상 자료 기반 사고 분석";
    }
    busy.value = "save";
    try {
      const data = await api.updateCase(caseId, {
        description_text: descriptionText.value,
        structured_facts: facts.value,
        selected_keywords: selectedKeywords.value,
        analysis_mode: analysisMode.value
      });
      caseData.value = data.case;
      showMessage("입력값을 저장했습니다.");
      return true;
    } catch (e: any) {
      showMessage(formatApiError(e, "입력값 저장에 실패했습니다."), false);
      return false;
    } finally {
      busy.value = "";
    }
  }

  async function loadUploads() {
    try {
      const data = await api.getCaseUploads(caseId);
      uploads.value = data.items || [];
      if (!selectedUploadId.value && uploads.value.length) selectedUploadId.value = uploads.value[0].id;
    } catch (e: any) {
      showMessage(formatApiError(e, "업로드 목록을 불러오지 못했습니다."), false);
    }
  }

  async function uploadLocal() {
    if (!file.value) return;
    if (!(await saveCaseInputs())) return;
    busy.value = "upload";
    try {
      const data = await api.localUpload(caseId, file.value);
      selectedUploadId.value = data.upload_id;
      showMessage("영상을 확인하고 있습니다.");
      await loadUploads();
    } catch (e: any) {
      showMessage(formatApiError(e, "영상 업로드에 실패했습니다."), false);
    } finally {
      busy.value = "";
    }
  }

  async function completeUpload(options: { autoAnalyzeAfterPreprocess?: boolean } = {}) {
    if (!activeUploadId.value) return;
    busy.value = "preprocess";
    try {
      await api.completeUpload(activeUploadId.value, options);
      showMessage("사고 장면을 찾고 있습니다.");
      await loadJobs();
      startPollingJobs();
    } catch (e: any) {
      showMessage(formatApiError(e, "전처리 작업 등록에 실패했습니다."), false);
    } finally {
      busy.value = "";
    }
  }

  async function fetchViewUrl() {
    if (!activeUploadId.value) return;
    try {
      viewUrl.value = (await api.getViewUrl(activeUploadId.value)).view_url;
    } catch (e: any) {
      showMessage(formatApiError(e, "영상 재생 URL을 발급하지 못했습니다."), false);
    }
  }

  async function fetchDownloadUrl() {
    if (!activeUploadId.value) return;
    try {
      window.open((await api.getDownloadUrl(activeUploadId.value)).download_url, "_blank");
    } catch (e: any) {
      showMessage(formatApiError(e, "다운로드 URL을 발급하지 못했습니다."), false);
    }
  }

  async function analyzeText() {
    if (!isAnalysisReady()) {
      showMessage("사고 설명을 쓰거나 영상을 먼저 선택해 주세요.", false);
      return;
    }
    if (!(await saveCaseInputs())) return;
    busy.value = "text-analysis";
    try {
      await api.analyzeText(caseId, payload());
      showMessage("분석 결과를 정리했습니다.");
      await loadReport();
      await loadCase();
        if (isReadyReport(report.value)) {
            guidedStep.value = "result";
        }
    } catch (e: any) {
      showMessage(formatApiError(e, "텍스트 분석에 실패했습니다."), false);
    } finally {
      busy.value = "";
    }
  }

  async function analyzeVideo() {
    if (!activeUploadId.value) return;
    if (!(await saveCaseInputs())) return;
    busy.value = "video-analysis";
    try {
      await api.analyzeVideo(caseId, { upload_id: activeUploadId.value, ...payload() });
      showMessage("영상에서 정차 여부와 충돌 방향을 확인하고 있습니다.");
      await loadJobs();
      startPollingJobs();
    } catch (e: any) {
      showMessage(formatApiError(e, "영상 분석 작업 등록에 실패했습니다."), false);
    } finally {
      busy.value = "";
    }
  }

    async function submitFollowup(answers: Record<string, string>) {
        followupError.value = "";
        reanalyzing.value = true;

        try {
            const response = await api.reanalyzeText(caseId, {
                ...payload(),
                followup_answers: answers
            });

            const readyPayload = getReportPayload(response);
            if (isReadyReport(response)) {
                report.value = readyPayload;
                guidedStep.value = "result";
            }

            await Promise.all([loadCase(), loadReport()]);
            showMessage("보완 답변을 반영해 재분석했습니다.");
        } catch (e: any) {
            followupError.value = formatApiError(e, "보완 답변을 반영해 재분석하지 못했습니다.");
        } finally {
            reanalyzing.value = false;
        }
    }

  async function loadJobs() {
    try {
      jobs.value = (await api.getJobs(caseId)).items || [];
    } catch (e: any) {
      showMessage(formatApiError(e, "작업 목록을 불러오지 못했습니다."), false);
    }
  }

  async function loadProgress() {
    try {
      progress.value = await api.getAnalysisProgress(caseId);
    } catch {
      progress.value = null;
    }
  }

    function getReportPayload(value: any): any | null {
        if (!value) return null;

        const status = String(value.status ?? "").toLowerCase();
        if (status === "not_ready" || status === "pending" || status === "running") {
            return null;
        }

        const candidate = value.report ?? value.result ?? value;

        if (!candidate) return null;

        const candidateStatus = String(candidate.status ?? "").toLowerCase();
        if (candidateStatus === "not_ready" || candidateStatus === "pending" || candidateStatus === "running") {
            return null;
        }

        return candidate;
    }

    function isReadyReport(value: any): boolean {
        if (!value) return false;

        const status = String(value.status ?? "").toLowerCase();
        if (status === "not_ready" || status === "pending" || status === "running") {
            return false;
        }

        const candidate = value.report ?? value;

        if (!candidate) return false;
        if (candidate.status === "not_ready") return false;

        return Boolean(
            candidate.one_line_summary ||
            candidate.summary ||
            candidate.fault_ratio ||
            candidate.elderly_friendly_report ||
            candidate.result ||
            candidate.title ||
            candidate.sections
        );
    }

    async function loadReport() {
        try {
            const response = await api.getEasyReport(caseId);
            const readyPayload = getReportPayload(response);

            report.value = isReadyReport(response) ? readyPayload : null;
        } catch {
            report.value = null;
        }
    }

    async function loadAll() {
        initialLoading.value = true;
        loadError.value = "";

        try {
            await Promise.all([
                loadCase(),
                loadUploads(),
                loadJobs(),
                loadReport(),
                loadProgress()
            ]);

            if (isReadyReport(report.value)) {
                guidedStep.value = "result";
                return;
            }

            // report가 없으면 사고 자료 입력 단계 유지
            if (guidedStep.value === "result") {
                guidedStep.value = "input";
            }
        } catch (error: any) {
            loadError.value = error?.message || "케이스 정보를 불러오지 못했습니다.";
        } finally {
            initialLoading.value = false;
        }
    }

    function isRunningJob(job: JobItem): boolean {
        return RUNNING_JOB_STATUSES.includes(String(job.status ?? "").toLowerCase());
    }

    function startPollingJobs() {
        stopPolling();

        pollTimer = window.setInterval(async () => {
            await loadJobs();

            if (!jobs.value.some(isRunningJob)) {
                stopPolling();

                await loadUploads();
                await loadReport();
                await loadCase();
                await loadProgress();

                if (isReadyReport(report.value)) {
                    guidedStep.value = "result";
                } else if (guidedStep.value === "analyzing") {
                    showMessage("아직 분석 결과가 준비되지 않았습니다. 잠시 후 다시 확인해 주세요.", false);
                }
            }
        }, 2500);
    }

    async function continueFromInput() {
        if (!isAnalysisReady()) {
            showMessage("사고 설명을 쓰거나 영상을 먼저 선택해 주세요.", false);
            return;
        }

        const saved = await saveCaseInputs();
        if (!saved) return;

        guidedStep.value = "accident-type";
    }

  function selectAccidentType(option: { scenario_type: string; accident_party_type: string }) {
    facts.value = {
      ...facts.value,
      accident_type: option.scenario_type || facts.value.accident_type || "",
      accident_party_type: option.accident_party_type || facts.value.accident_party_type || "unknown",
      scenario_hint: option.scenario_type ? "user_selected" : "agent_infer",
    };
    guidedStep.value = "purpose";
  }

  function selectGuidedAnalysisMode(mode: string) {
    analysisMode.value = mode;
    guidedStep.value = "questions";
  }

  function answerGuidedQuestion(question: any, value: string) {
    guidedAnswers.value = { ...guidedAnswers.value, [question.question_id]: value };
    const factKey = question.fact_key || question.knia_factor_key || String(question.question_id || "").split(".").pop();
    const nextFacts: AccidentFacts = { ...facts.value };
    if (factKey === "stopped") nextFacts.stopped = value === "yes" ? true : value === "no" ? false : undefined;
    else if (factKey === "sudden_brake_without_reason" || factKey === "sudden_brake") nextFacts.sudden_brake = value === "yes";
    else if (factKey === "lawful_stop_reason" || factKey === "stop_reason") nextFacts.stop_reason = value;
    else if (factKey === "brake_light_failure" || factKey === "brake_light") nextFacts.brake_light = value;
    else if (factKey === "abnormal_stop_position") nextFacts.abnormal_stop = value === "abnormal_stop";
    else (nextFacts as any)[factKey] = value;
    facts.value = nextFacts;
  }

    async function startGuidedAnalysis() {
        if (!(await saveCaseInputs())) return;

        guidedStep.value = "analyzing";

        if (activeUploadId.value) {
            await analyzeVideo();

            if (!jobs.value.some(isRunningJob) && !isReadyReport(report.value)) {
                guidedStep.value = "questions";
            }

            return;
        }

        await analyzeText();

        if (!isReadyReport(report.value)) {
            guidedStep.value = "questions";
        }
    }

  async function onGuidedFile(e: Event) {
    onFile(e);
    if (!file.value) return;
    await uploadLocal();
    if (activeUploadId.value) await completeUpload({ autoAnalyzeAfterPreprocess: false });
  }

    const guidedQuestions = computed(() => {
        const currentReport = getReportPayload(report.value) || report.value;

        const fromReport =
            currentReport?.guided_questionnaire?.questions ||
            currentReport?.missing_info?.questions ||
            currentReport?.report?.guided_questionnaire?.questions ||
            currentReport?.report?.missing_info?.questions ||
            [];

        return fromReport.length ? fromReport : fallbackGuidedQuestions;
    });

  function stopPolling() {
    if (pollTimer !== null) window.clearInterval(pollTimer);
    pollTimer = null;
  }

  onMounted(loadAll);
  onBeforeUnmount(stopPolling);

  return {
    caseData,
    descriptionText,
    facts,
    analysisMode,
    selectedKeywords,
    keywordPool: caseKeywordPool,
    file,
    uploads,
    selectedUploadId,
    activeUploadId,
    viewUrl,
    jobs,
    progress,
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
    loadProgress,
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
  };
}
