import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { api, formatApiError, type AccidentFacts, type CaseItem, type UploadItem } from "../api/client";
import { formatDate, prettySize, statusClass, statusLabel } from "./caseWorkspaceFormatters";
import {
    DEFAULT_KEYWORDS,
    DEFAULT_PROGRESS_STEPS,
    REPORT_READY_RETRY_DELAY_MS,
    REPORT_READY_RETRY_LIMIT,
    caseKeywordPool,
    getFallbackGuidedQuestions,
    guidedAccidentTypeOptions,
    guidedAnalysisModes,
} from "./caseWorkspaceGuidance";
import { applyGuidedQuestionAnswer, getGuidedQuestionId } from "./caseWorkspaceFactMapping";
import {
    getReportPayload,
    isFailedJob,
    isFinishedJob,
    isReadyReport,
    isRunningJob,
    type JobItem,
} from "./caseWorkspaceProgress";
import {
    createCaseWorkspaceProgressController,
    delay,
    getRunningJobProgress,
    type GuidedStep,
} from "./caseWorkspaceOrchestration";
import {
    buildCaseInputPayload,
    buildFollowupAnalysisPayload,
    buildTextAnalysisPayload,
    buildVideoAnalysisPayload,
    normalizeCaseDescription,
} from "./caseWorkspacePayloads";

export { formatDate, prettySize, statusClass, statusLabel } from "./caseWorkspaceFormatters";
export { guidedAccidentTypeOptions, guidedAnalysisModes } from "./caseWorkspaceGuidance";

export type CaseWorkspaceBusyState = "" | "save" | "upload" | "preprocess" | "text-analysis" | "video-analysis";

function normalizeAnalysisMode(mode?: string | null) {
    const value = String(mode || "").trim();

    if (
        value === "expert" ||
        value === "legal_precedent_focused" ||
        value === "full_deep_research" ||
        value === "deep_research" ||
        value === "debug"
    ) {
        return "expert";
    }

    return "user_friendly";
}

export function useCaseWorkspace(caseId: string) {
    const caseData = ref<CaseItem | null>(null);
    const descriptionText = ref("");
    const facts = ref<AccidentFacts>({ injury: null });
    const analysisMode = ref("user_friendly");
    const selectedKeywords = ref<string[]>([...DEFAULT_KEYWORDS]);
    const file = ref<File | null>(null);
    const uploads = ref<UploadItem[]>([]);
    const selectedUploadId = ref("");
    const viewUrl = ref("");
    const jobs = ref<JobItem[]>([]);
    const progress = ref<any>(null);
    const progressPercent = ref(0);
    const progressStageLabel = ref("입력 대기");
    const progressMessage = ref("사고 설명이나 영상을 입력해 주세요.");
    const progressSteps = ref<any[]>(DEFAULT_PROGRESS_STEPS);
    const resultWaitAttempt = ref(0);
    const analysisStarted = ref(false);
    const resultStreaming = ref(false);
    const report = ref<any>(null);
    const message = ref("");
    const messageOk = ref(true);
    const initialLoading = ref(false);
    const loadError = ref("");
    const followupError = ref("");
    const reanalyzing = ref(false);
    const busy = ref<CaseWorkspaceBusyState>("");
    const guidedStep = ref<GuidedStep>("input");
    const guidedAnswers = ref<Record<string, string>>({});
    let pollTimer: number | null = null;

    const activeUploadId = computed(() => selectedUploadId.value);
    const remainingProgressSteps = computed(() =>
        progressSteps.value
            .filter((step) => Number(step.percent || 0) > progressPercent.value)
            .map((step) => step.label || step.message)
            .filter(Boolean)
    );
    const progressEtaText = computed(() => {
        if (progressPercent.value >= 100) return "완료되었습니다.";

        const backendSeconds = Number(progress.value?.estimated_remaining_seconds);

        if (Number.isFinite(backendSeconds) && backendSeconds > 0) {
            if (backendSeconds >= 60) return `약 ${Math.ceil(backendSeconds / 60)}분 이내`;
            return `약 ${Math.max(5, Math.ceil(backendSeconds / 5) * 5)}초 이내`;
        }

        if (progressPercent.value >= 88) return "결과 화면을 정리하고 있습니다.";
        if (progressPercent.value >= 75) return "KNIA 기준과 가감요소를 대조하고 있습니다.";
        if (progressPercent.value >= 45) return "영상과 사고 정보를 확인하고 있습니다.";

        return "잠시 후 다음 단계로 넘어갑니다.";
    });
    const progressStatusText = computed(() => {
        const backendNote = String(progress.value?.status_note || "").trim();
        if (backendNote) return backendNote;

        if (remainingProgressSteps.value.length) {
            return `${remainingProgressSteps.value.length}개 단계가 남았습니다.`;
        }

        return "결과 화면으로 이동할 준비를 하고 있습니다.";
    });

    function showMessage(text: string, ok = true) {
        message.value = text;
        messageOk.value = ok;
    }

    const { applyBackendProgress, applyLocalProgress, markReportReady } = createCaseWorkspaceProgressController({
        progressPercent,
        progressStageLabel,
        progressMessage,
        progressSteps,
        guidedStep,
    });

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

    function payloadInput() {
        return {
            descriptionText: descriptionText.value,
            facts: facts.value,
            selectedKeywords: selectedKeywords.value,
            analysisMode: normalizeAnalysisMode(analysisMode.value),
        };
    }

    async function loadCase() {
        const data = await api.getCase(caseId);

        caseData.value = data.case;
        descriptionText.value = data.case.description_text || "";
        facts.value = { ...facts.value, ...(data.case.structured_facts || {}) };
        selectedKeywords.value = data.case.selected_keywords?.length ? data.case.selected_keywords : selectedKeywords.value;
        analysisMode.value = normalizeAnalysisMode(data.case.analysis_mode || analysisMode.value);
    }

    function isAnalysisReady() {
        return Boolean(descriptionText.value.trim() || activeUploadId.value || file.value);
    }

    async function saveCaseInputs() {
        descriptionText.value = normalizeCaseDescription(descriptionText.value);

        busy.value = "save";

        try {
            const data = await api.updateCase(caseId, buildCaseInputPayload(payloadInput()));

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
        if (!file.value) return false;
        if (!(await saveCaseInputs())) return false;

        busy.value = "upload";

        try {
            applyLocalProgress({
                percent: 20,
                stage: "영상 업로드 중",
                message: "선택한 영상을 안전하게 저장하고 있습니다.",
            });

            const data = await api.localUpload(caseId, file.value);
            selectedUploadId.value = data.upload_id;

            applyLocalProgress({
                percent: 30,
                stage: "영상 저장 완료",
                message: "영상 저장이 완료되었습니다. 추가 사고정보를 입력해 주세요.",
            });

            showMessage("영상 저장 완료. 추가 사고정보를 입력해 주세요.");
            await loadUploads();

            return true;
        } catch (e: any) {
            selectedUploadId.value = "";
            showMessage(formatApiError(e, "영상 업로드에 실패했습니다."), false);
            return false;
        } finally {
            busy.value = "";
        }
    }

    async function completeUpload(options: { autoAnalyzeAfterPreprocess?: boolean } = {}) {
        if (!activeUploadId.value) return false;

        busy.value = "preprocess";

        try {
            const autoAnalyze = options.autoAnalyzeAfterPreprocess !== false;

            await api.completeUpload(activeUploadId.value, options);
            await loadJobs();
            await loadProgress();

            if (!autoAnalyze) {
                applyLocalProgress({
                    percent: 30,
                    stage: "영상 저장 완료",
                    message: "영상은 저장되었습니다. 이제 사고유형과 추가 사고정보를 입력해 주세요.",
                });

                showMessage("영상 저장 완료. 아래 질문에 답하면 과실비율을 더 정확하게 볼 수 있습니다.");
                guidedStep.value = "accident-type";
                return true;
            }

            applyLocalProgress({
                percent: 35,
                stage: "영상 확인 중",
                message: "영상에서 사고 장면을 확인하고 있습니다.",
            });

            showMessage("영상에서 사고 장면을 확인하고 있습니다.");
            startPollingJobs();
            return true;
        } catch (e: any) {
            showMessage(formatApiError(e, "전처리 작업 등록에 실패했습니다."), false);
            return false;
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

    async function loadJobs() {
        try {
            jobs.value = (await api.getJobs(caseId)).items || [];
        } catch (e: any) {
            showMessage(formatApiError(e, "작업 목록을 불러오지 못했습니다."), false);
        }
    }

    async function loadProgress() {
        try {
            const data = await api.getAnalysisProgress(caseId);
            progress.value = data;
            applyBackendProgress(data);

            if (data?.result_ready === true || data?.can_show_result === true) {
                await loadReport();

                if (isReadyReport(report.value)) {
                    markReportReady();
                    resultStreaming.value = false;
                    guidedStep.value = "result";
                }
            }
        } catch {
            progress.value = null;
        }
    }

    async function loadReport() {
        try {
            const response = await api.getEasyReport(caseId);
            report.value = getReportPayload(response);
        } catch {
            report.value = null;
        }
    }

    async function waitForReadyReport(options: { retryLimit?: number; delayMs?: number } = {}) {
        const retryLimit = options.retryLimit ?? REPORT_READY_RETRY_LIMIT;
        const delayMs = options.delayMs ?? REPORT_READY_RETRY_DELAY_MS;

        for (let attempt = 0; attempt < retryLimit; attempt += 1) {
            resultWaitAttempt.value = attempt + 1;

            const percent = Math.min(99, 88 + Math.floor((attempt / retryLimit) * 11));

            applyLocalProgress({
                percent,
                stage: "결과 정리 중",
                message: `분석 결과를 화면에 맞게 정리하고 있습니다. 잠시만 기다려 주세요. (${attempt + 1}/${retryLimit})`,
            });

            await Promise.all([loadReport(), loadProgress()]);

            if (isReadyReport(report.value)) {
                markReportReady();
                guidedStep.value = "result";
                resultStreaming.value = false;
                showMessage("분석 결과가 준비되었습니다.");
                return true;
            }

            await delay(delayMs);
        }

        return false;
    }

    async function analyzeText() {
        if (!isAnalysisReady()) {
            showMessage("사고 설명을 쓰거나 영상을 먼저 선택해 주세요.", false);
            return;
        }

        if (!(await saveCaseInputs())) return;

        busy.value = "text-analysis";
        analysisStarted.value = true;
        resultStreaming.value = true;
        guidedStep.value = "analyzing";

        try {
            applyLocalProgress({
                percent: 45,
                stage: "분석 시작",
                message: "입력한 사고정보를 바탕으로 분석을 시작합니다.",
            });

            await api.analyzeText(caseId, buildTextAnalysisPayload(payloadInput()));
            showMessage("분석 결과를 정리하고 있습니다.");

            await loadCase();

            const ready = await waitForReadyReport({ retryLimit: 20, delayMs: 1000 });

            if (!ready) {
                showMessage("분석 결과를 불러오는 데 시간이 오래 걸리고 있습니다. 결과 새로고침을 눌러 다시 확인해 주세요.", false);
                guidedStep.value = "result";
                resultStreaming.value = false;
            }
        } catch (e: any) {
            showMessage(formatApiError(e, "텍스트 분석에 실패했습니다."), false);
            resultStreaming.value = false;
        } finally {
            busy.value = "";
        }
    }

    async function analyzeVideo() {
        if (!activeUploadId.value) return false;
        if (!(await saveCaseInputs())) return false;

        busy.value = "video-analysis";
        analysisStarted.value = true;
        resultStreaming.value = true;
        guidedStep.value = "analyzing";

        try {
            applyLocalProgress({
                percent: 45,
                stage: "영상 분석 시작",
                message: "입력한 사고정보와 영상을 함께 확인하고 있습니다.",
            });

            await api.analyzeVideo(caseId, buildVideoAnalysisPayload(activeUploadId.value, payloadInput()));

            applyLocalProgress({
                percent: 55,
                stage: "사고유형 확인 중",
                message: "사고유형과 충돌 상황을 확인하고 있습니다.",
            });

            await loadJobs();
            await loadProgress();
            startPollingJobs();

            return true;
        } catch (e: any) {
            showMessage(formatApiError(e, "영상 분석 작업 등록에 실패했습니다."), false);
            resultStreaming.value = false;
            return false;
        } finally {
            busy.value = "";
        }
    }

    async function submitFollowup(answers: Record<string, string>) {
        followupError.value = "";
        reanalyzing.value = true;

        try {
            await api.reanalyzeText(caseId, buildFollowupAnalysisPayload(payloadInput(), answers));
            await Promise.all([loadCase(), loadReport()]);

            if (isReadyReport(report.value)) {
                guidedStep.value = "result";
            }

            showMessage("보완 답변을 반영해 재분석했습니다.");
        } catch (e: any) {
            followupError.value = formatApiError(e, "보완 답변을 반영해 재분석하지 못했습니다.");
        } finally {
            reanalyzing.value = false;
        }
    }

    async function loadAll() {
        initialLoading.value = true;
        loadError.value = "";

        try {
            await Promise.all([loadCase(), loadUploads(), loadJobs(), loadReport(), loadProgress()]);

            if (isReadyReport(report.value)) {
                guidedStep.value = "result";
                return;
            }

            if (guidedStep.value === "result") guidedStep.value = "input";
        } catch (error: any) {
            loadError.value = error?.message || "케이스 정보를 불러오지 못했습니다.";
        } finally {
            initialLoading.value = false;
        }
    }

    function startPollingJobs() {
        stopPolling();

        pollTimer = window.setInterval(async () => {
            await Promise.all([loadJobs(), loadProgress()]);

            const hasRunningJob = jobs.value.some(isRunningJob);
            const hasFailedJob = jobs.value.some(isFailedJob);
            const hasFinishedJob = jobs.value.some(isFinishedJob);
            const shouldProbeReport =
                progress.value?.result_ready === true ||
                progress.value?.can_show_result === true ||
                progressPercent.value >= 75 ||
                hasFinishedJob;

            if (shouldProbeReport) {
                await loadReport();

                if (isReadyReport(report.value)) {
                    markReportReady();
                    guidedStep.value = "result";
                    resultStreaming.value = false;
                    stopPolling();
                    showMessage("분석 결과가 준비되었습니다.");
                    return;
                }
            }

            if (hasRunningJob) {
                const runningJob = jobs.value.find(isRunningJob);
                applyLocalProgress(getRunningJobProgress(runningJob?.type, progressPercent.value));

                return;
            }

            stopPolling();
            await Promise.all([loadUploads(), loadCase(), loadProgress()]);

            if (hasFailedJob) {
                resultStreaming.value = false;
                showMessage("영상 분석 중 일부 작업이 실패했습니다. 고급 진단 보기에서 작업 상태를 확인해 주세요.", false);
                guidedStep.value = "questions";
                return;
            }

            if (hasFinishedJob || jobs.value.length > 0) {
                applyLocalProgress({
                    percent: 88,
                    stage: "결과 정리 중",
                    message: "분석 작업이 끝났습니다. 결과 화면을 정리하고 있습니다.",
                });

                const ready = await waitForReadyReport();
                if (ready) return;

                resultStreaming.value = false;
                showMessage("분석 결과를 불러오는 데 시간이 오래 걸리고 있습니다. 결과 새로고침을 눌러 다시 확인해 주세요.", false);

                if (guidedStep.value === "analyzing") guidedStep.value = "result";
            }
        }, 1200);
    }

    async function continueFromInput() {
        if (!isAnalysisReady()) {
            showMessage("사고 설명을 쓰거나 영상을 먼저 선택해 주세요.", false);
            return;
        }

        const saved = await saveCaseInputs();
        if (!saved) return;

        guidedAnswers.value = {};
        guidedStep.value = "accident-type";
    }

    function selectAccidentType(option: { scenario_type: string; accident_party_type: string }) {
        const scenarioType = option.scenario_type || "";
        const partyType = option.accident_party_type || facts.value.accident_party_type || "unknown";

        const nextFacts: AccidentFacts = {
            ...facts.value,
            accident_type: scenarioType,
            accident_party_type: partyType,
            scenario_hint: option.scenario_type ? "user_selected" : "agent_infer",
            ...(scenarioType === "rear_end_collision"
                ? { rear_end_role: (facts.value as any).rear_end_role || "unknown" }
                : {}),
        };

        (nextFacts as any).knia_major_party_type = partyType;
        if (partyType === "car_vs_person") {
            nextFacts.accident_type = scenarioType || "pedestrian_crosswalk_accident";
            (nextFacts as any).collision_partner_type = "pedestrian";
            (nextFacts as any).direct_collision_partner_type = "pedestrian";
            (nextFacts as any).excluded_knia_party_types = ["car_vs_car", "car_vs_bicycle", "car_vs_motorcycle", "car_vs_object", "single_vehicle"];
        } else if (partyType === "car_vs_bicycle") {
            (nextFacts as any).collision_partner_type = "bicycle";
            (nextFacts as any).direct_collision_partner_type = "bicycle";
            (nextFacts as any).excluded_knia_party_types = ["car_vs_car", "car_vs_person", "car_vs_motorcycle", "car_vs_object", "single_vehicle"];
        } else if (partyType === "car_vs_motorcycle") {
            (nextFacts as any).collision_partner_type = "motorcycle";
            (nextFacts as any).direct_collision_partner_type = "motorcycle";
            (nextFacts as any).excluded_knia_party_types = ["car_vs_car", "car_vs_person", "car_vs_bicycle", "car_vs_object", "single_vehicle"];
        } else if (partyType === "car_vs_object") {
            (nextFacts as any).collision_partner_type = "object";
            (nextFacts as any).direct_collision_partner_type = "object";
            (nextFacts as any).excluded_knia_party_types = ["car_vs_car", "car_vs_person", "car_vs_bicycle", "car_vs_motorcycle", "single_vehicle"];
        } else if (partyType === "single_vehicle") {
            (nextFacts as any).collision_partner_type = "none";
            delete (nextFacts as any).direct_collision_partner_type;
            (nextFacts as any).excluded_knia_party_types = ["car_vs_car", "car_vs_person", "car_vs_bicycle", "car_vs_motorcycle", "car_vs_object"];
        } else if (partyType === "car_vs_car") {
            (nextFacts as any).collision_partner_type = "vehicle";
            (nextFacts as any).direct_collision_partner_type = "vehicle";
            (nextFacts as any).excluded_knia_party_types = ["car_vs_person", "car_vs_bicycle", "car_vs_motorcycle", "car_vs_object", "single_vehicle"];
        }

        if (scenarioType === "stealth_illegal_parked_vehicle_collision") {
            nextFacts.accident_type = "stealth_illegal_parked_vehicle_collision";
            nextFacts.accident_party_type = "car_vs_car";
            (nextFacts as any).knia_major_party_type = "car_vs_car";
            (nextFacts as any).collision_partner_type = "vehicle";
            (nextFacts as any).direct_collision_partner_type = "vehicle";
            (nextFacts as any).target_vehicle_status = "abnormal_parked";
            (nextFacts as any).is_parked_vehicle_collision = true;
            (nextFacts as any).is_stealth_parked_vehicle_collision = true;
            (nextFacts as any).excluded_knia_party_types = ["car_vs_bicycle", "car_vs_person"];
        }

        facts.value = nextFacts;
        guidedAnswers.value = {};
        guidedStep.value = "purpose";
    }

    function selectGuidedAnalysisMode(mode: string) {
        analysisMode.value = normalizeAnalysisMode(mode);
        guidedStep.value = "questions";
    }

    function answerGuidedQuestion(question: any, value: string) {
        const questionId = getGuidedQuestionId(question);
        guidedAnswers.value = { ...guidedAnswers.value, [questionId]: value };
        facts.value = applyGuidedQuestionAnswer(facts.value, question, value);
    }

    async function startGuidedAnalysis() {
        if (!(await saveCaseInputs())) return;

        analysisStarted.value = true;
        resultStreaming.value = true;
        guidedStep.value = "analyzing";

        applyLocalProgress({
            percent: 40,
            stage: "분석 시작",
            message: "입력한 사고정보를 바탕으로 분석을 시작합니다.",
        });

        if (activeUploadId.value) {
            const started = await analyzeVideo();

            if (!started) {
                resultStreaming.value = false;
                guidedStep.value = "questions";
            }

            return;
        }

        await analyzeText();

        if (!isReadyReport(report.value) && guidedStep.value === "analyzing") {
            guidedStep.value = "result";
        }
    }

    async function onGuidedFile(e: Event) {
        onFile(e);
        if (!file.value) return;

        const uploaded = await uploadLocal();
        if (!uploaded || !activeUploadId.value) return;

        await completeUpload({ autoAnalyzeAfterPreprocess: false });
    }

    const guidedQuestions = computed(() => {
        const currentReport = getReportPayload(report.value) || report.value;

        const fromReport =
            currentReport?.guided_questionnaire?.questions ||
            currentReport?.missing_info?.questions ||
            currentReport?.report?.guided_questionnaire?.questions ||
            currentReport?.report?.missing_info?.questions ||
            [];

        if (fromReport.length) return fromReport;

        return getFallbackGuidedQuestions(facts.value, descriptionText.value);
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
        progressPercent,
        progressStageLabel,
        progressMessage,
        progressSteps,
        remainingProgressSteps,
        progressEtaText,
        progressStatusText,
        resultWaitAttempt,
        analysisStarted,
        resultStreaming,
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
        uploadLocal,
    };
}
