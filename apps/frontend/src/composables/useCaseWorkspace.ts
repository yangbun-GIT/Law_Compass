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
    running: "진행 중",
    retrying: "재시도 중",
    processing: "처리 중",
    analyzing: "분석 중",
    completed: "완료",
    ready_for_analysis: "분석 준비",
    failed: "실패",
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
  const report = ref<any>(null);
  const message = ref("");
  const messageOk = ref(true);
  const initialLoading = ref(false);
  const loadError = ref("");
  const followupError = ref("");
  const reanalyzing = ref(false);
  const busy = ref<CaseWorkspaceBusyState>("");
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

  async function saveCaseInputs() {
    if (!descriptionText.value.trim()) {
      showMessage("사고 설명을 먼저 입력해 주세요.", false);
      return false;
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
      showMessage("로컬 업로드가 완료되었습니다.");
      await loadUploads();
    } catch (e: any) {
      showMessage(formatApiError(e, "영상 업로드에 실패했습니다."), false);
    } finally {
      busy.value = "";
    }
  }

  async function completeUpload() {
    if (!activeUploadId.value) return;
    busy.value = "preprocess";
    try {
      const data = await api.completeUpload(activeUploadId.value);
      showMessage(`전처리 작업 등록: ${data.job_id}`);
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
    if (!(await saveCaseInputs())) return;
    busy.value = "text-analysis";
    try {
      await api.analyzeText(caseId, payload());
      showMessage("텍스트 분석을 완료했습니다.");
      await loadReport();
      await loadCase();
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
      const data = await api.analyzeVideo(caseId, { upload_id: activeUploadId.value, ...payload() });
      showMessage(`영상 분석 작업 등록: ${data.job_id}`);
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
      report.value = response.report || response.result || report.value;
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

  async function loadReport() {
    try {
      report.value = await api.getEasyReport(caseId);
    } catch {
      report.value = null;
    }
  }

  async function loadAll() {
    initialLoading.value = true;
    loadError.value = "";
    try {
      await Promise.all([loadCase(), loadUploads(), loadJobs(), loadReport()]);
    } catch (e: any) {
      loadError.value = formatApiError(e, "케이스 정보를 불러오지 못했습니다.");
    } finally {
      initialLoading.value = false;
    }
  }

  function startPollingJobs() {
    stopPolling();
    pollTimer = window.setInterval(async () => {
      await loadJobs();
      if (!jobs.value.some((job) => RUNNING_JOB_STATUSES.includes(job.status))) {
        stopPolling();
        await loadUploads();
        await loadReport();
        await loadCase();
      }
    }, 2500);
  }

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
    report,
    message,
    messageOk,
    initialLoading,
    loadError,
    followupError,
    reanalyzing,
    busy,
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
    submitFollowup,
    toggleKeyword,
    uploadLocal
  };
}
