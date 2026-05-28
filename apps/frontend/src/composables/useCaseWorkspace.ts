import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { api, formatApiError, type AccidentFacts, type CaseItem, type UploadItem } from "../api/client";
import { formatDate, prettySize, statusClass, statusLabel } from "./caseWorkspaceFormatters";
import {
    DEFAULT_KEYWORDS,
    DEFAULT_PROGRESS_STEPS,
    FAILED_JOB_STATUSES,
    FINISHED_JOB_STATUSES,
    REPORT_READY_RETRY_DELAY_MS,
    REPORT_READY_RETRY_LIMIT,
    RUNNING_JOB_STATUSES,
    caseKeywordPool,
    getFallbackGuidedQuestions,
    guidedAccidentTypeOptions,
    guidedAnalysisModes,
} from "./caseWorkspaceGuidance";

export { formatDate, prettySize, statusClass, statusLabel } from "./caseWorkspaceFormatters";
export { guidedAccidentTypeOptions, guidedAnalysisModes } from "./caseWorkspaceGuidance";

export type CaseWorkspaceBusyState = "" | "save" | "upload" | "preprocess" | "text-analysis" | "video-analysis";

type JobItem = {
    id: string;
    type: string;
    status: string;
    attempts?: number;
    attempt?: number;
};

function normalizeProgressStepLabel(step: any) {
    const key = String(step?.key ?? step?.stage ?? "").toLowerCase();

    const labels: Record<string, string> = {
        input: "입력 정리",
        upload: "영상 확인",
        scene: "사고 장면 확인",
        scenario: "사고유형 판단",
        knia: "KNIA 과실 기준 검색",
        adjustment: "가감요소 계산",
        result: "결과 정리",
    };

    const currentLabel = String(step?.label ?? step?.message ?? "");
    if (currentLabel.includes("??") || !currentLabel.trim()) {
        return labels[key] ?? currentLabel;
    }

    return currentLabel;
}

function normalizeProgressSteps(steps: any[]) {
    return steps.map((step) => ({
        ...step,
        label: normalizeProgressStepLabel(step),
    }));
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
    const guidedStep = ref<"input" | "accident-type" | "purpose" | "questions" | "analyzing" | "result">("input");
    const guidedAnswers = ref<Record<string, string>>({});
    let pollTimer: number | null = null;

    const activeUploadId = computed(() => selectedUploadId.value);

    function showMessage(text: string, ok = true) {
        message.value = text;
        messageOk.value = ok;
    }

    function normalizeStatus(value: any): string {
        return String(value ?? "").trim().toLowerCase();
    }

    function isRunningJob(job: JobItem): boolean {
        return RUNNING_JOB_STATUSES.includes(normalizeStatus(job.status));
    }

    function isFinishedJob(job: JobItem): boolean {
        return FINISHED_JOB_STATUSES.includes(normalizeStatus(job.status));
    }

    function isFailedJob(job: JobItem): boolean {
        return FAILED_JOB_STATUSES.includes(normalizeStatus(job.status));
    }

    function hasReportContent(candidate: any): boolean {
        if (!candidate || typeof candidate !== "object") return false;

        return Boolean(
            candidate.one_line_summary ||
            candidate.summary ||
            candidate.summary_for_user ||
            candidate.fault_ratio ||
            candidate.faultRatio ||
            candidate.fault_explanation ||
            candidate.elderly_friendly_report ||
            candidate.elderly_report ||
            candidate.easy_report ||
            candidate.result ||
            candidate.title ||
            candidate.headline ||
            candidate.sections ||
            candidate.judgment ||
            candidate.insurance ||
            candidate.action_plan ||
            candidate.legal_basis ||
            candidate.knia_matches ||
            candidate.report_html ||
            candidate.markdown ||
            candidate.content ||
            candidate.fault_adjustment_summary_card
        );
    }

    function getReportPayload(value: any): any | null {
        if (!value) return null;

        const status = normalizeStatus(value.status);
        if (["not_ready", "pending", "running", "processing"].includes(status)) return null;

        const candidates = [
            value.report,
            value.easy_report,
            value.elderly_friendly_report,
            value.elderly_report,
            value.result,
            value.data,
            value.payload,
            value.analysis,
            value,
        ].filter(Boolean);

        for (const candidate of candidates) {
            const candidateStatus = normalizeStatus(candidate?.status);
            if (["not_ready", "pending", "running", "processing"].includes(candidateStatus)) continue;

            if (hasReportContent(candidate)) return candidate;

            const nested = [
                candidate.report,
                candidate.easy_report,
                candidate.elderly_friendly_report,
                candidate.elderly_report,
                candidate.result,
                candidate.data,
                candidate.payload,
                candidate.analysis,
            ].filter(Boolean);

            for (const item of nested) {
                if (hasReportContent(item)) return item;
            }
        }

        return null;
    }

    function isReadyReport(value: any): boolean {
        return Boolean(getReportPayload(value));
    }

    function delay(ms: number) {
        return new Promise((resolve) => window.setTimeout(resolve, ms));
    }

    function applyLocalProgress(next: { percent?: number; stage?: string; message?: string; steps?: any[] }) {
        if (typeof next.percent === "number") {
            progressPercent.value = Math.max(progressPercent.value, Math.min(100, Math.max(0, next.percent)));
        }

        if (next.stage) progressStageLabel.value = next.stage;
        if (next.message) progressMessage.value = next.message;
        if (Array.isArray(next.steps) && next.steps.length) progressSteps.value = normalizeProgressSteps(next.steps);
    }

    function applyBackendProgress(data: any) {
        if (!data) return;

        applyLocalProgress({
            percent: Number(data.progress_percent ?? data.percent ?? progressPercent.value),
            stage: data.current_stage || data.stage_label || progressStageLabel.value,
            message: data.current_message || data.message || progressMessage.value,
            steps: Array.isArray(data.steps) ? normalizeProgressSteps(data.steps) : undefined,
        });

        if (data.result_ready === true || data.can_show_result === true) {
            progressPercent.value = 100;
            progressStageLabel.value = "결과 준비 완료";
            progressMessage.value = "분석 결과가 준비되었습니다.";

            if (guidedStep.value === "analyzing") {
                guidedStep.value = "result";
            }
        }
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
            analysis_mode: analysisMode.value,
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
        if (!descriptionText.value.trim()) descriptionText.value = "영상 자료 기반 사고 분석";

        busy.value = "save";

        try {
            const data = await api.updateCase(caseId, {
                description_text: descriptionText.value,
                structured_facts: facts.value,
                selected_keywords: selectedKeywords.value,
                analysis_mode: analysisMode.value,
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
                    progressPercent.value = 100;
                    progressStageLabel.value = "결과 준비 완료";
                    progressMessage.value = "분석 결과가 준비되었습니다.";
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
                progressPercent.value = 100;
                progressStageLabel.value = "결과 준비 완료";
                progressMessage.value = "분석 결과가 준비되었습니다.";
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

            await api.analyzeText(caseId, payload());
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

            await api.analyzeVideo(caseId, { upload_id: activeUploadId.value, ...payload() });

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
            await api.reanalyzeText(caseId, { ...payload(), followup_answers: answers });
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

            if (hasRunningJob) {
                const runningJob = jobs.value.find(isRunningJob);

                if (runningJob?.type === "video_preprocess") {
                    applyLocalProgress({
                        percent: Math.max(progressPercent.value, 45),
                        stage: "영상 확인 중",
                        message: "영상에서 사고 장면을 찾고 있습니다.",
                    });
                } else if (runningJob?.type === "video_analyze") {
                    applyLocalProgress({
                        percent: Math.max(progressPercent.value, 65),
                        stage: "사고 분석 중",
                        message: "입력한 답변과 영상을 바탕으로 과실비율을 계산하고 있습니다.",
                    });
                } else {
                    applyLocalProgress({
                        percent: Math.max(progressPercent.value, 55),
                        stage: "분석 중",
                        message: "사고 내용을 분석하고 있습니다.",
                    });
                }

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
        const scenarioType = option.scenario_type || facts.value.accident_type || "";
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
        analysisMode.value = mode;
        guidedStep.value = "questions";
    }

    function answerGuidedQuestion(question: any, value: string) {
        const questionId = question.question_id || question.field || question.fact_key || "unknown_question";
        guidedAnswers.value = { ...guidedAnswers.value, [questionId]: value };

        const factKey = question.fact_key || question.knia_factor_key || String(question.question_id || "").split(".").pop();
        const nextFacts: AccidentFacts = { ...facts.value };

        function markStealthParkedVehicleCollision() {
            nextFacts.accident_party_type = "car_vs_car";
            nextFacts.accident_type = "stealth_illegal_parked_vehicle_collision";

            (nextFacts as any).knia_major_party_type = "car_vs_car";
            (nextFacts as any).collision_partner_type = "vehicle";
            (nextFacts as any).direct_collision_partner_type = "vehicle";
            (nextFacts as any).accident_subtype = "night_unlit_illegal_parked_vehicle_collision";
            (nextFacts as any).target_vehicle_status = "abnormal_parked";
            (nextFacts as any).is_parked_vehicle_collision = true;
            (nextFacts as any).is_stealth_parked_vehicle_collision = true;
            (nextFacts as any).requires_high_opponent_fault_review = true;
            (nextFacts as any).excluded_knia_party_types = ["car_vs_bicycle", "car_vs_person"];

            delete (nextFacts as any).bicycle_involved;
            delete (nextFacts as any).possible_trigger_vehicle;
            delete (nextFacts as any).trigger_actor_type;
            delete (nextFacts as any).bicycle_location;
            delete (nextFacts as any).bicycle_movement;

            const lighting = String((nextFacts as any).parked_vehicle_lighting || "");
            const visibility = String((nextFacts as any).visibility_condition || "");
            const position = String((nextFacts as any).parked_vehicle_position || "");
            const impairment = String((nextFacts as any).opponent_impairment || "");
            const avoidability = String((nextFacts as any).avoidability || "");

            const isUnlit = lighting === "unlit_stealth" || lighting === "no_lights" || lighting === "unknown_but_dark";
            const isDark = visibility === "night_dark" || visibility === "under_bridge_dark" || visibility === "low_visibility";
            const isAbnormalPosition =
                position === "traffic_space" ||
                position === "flowerbed_or_median" ||
                position === "under_bridge" ||
                position === "roadside" ||
                position === "under_bridge_flowerbed";
            const isDrunk = impairment === "drunk_driving_confirmed" || impairment === "suspected_drunk";
            const isHardToAvoid = avoidability === "nearly_impossible" || avoidability === "limited";

            (nextFacts as any).night_no_lights_or_low_visibility = isUnlit || isDark;
            (nextFacts as any).abnormal_parking = isAbnormalPosition;
            (nextFacts as any).opponent_drunk_or_abnormal_operation = isDrunk;
            (nextFacts as any).low_avoidability = isHardToAvoid;

            if (isUnlit && isDark && isAbnormalPosition && isDrunk && isHardToAvoid) {
                (nextFacts as any).fault_ratio_claim_target = "opponent_100_ego_0_possible";
                (nextFacts as any).fault_ratio_realistic_target = "opponent_90_ego_10";
                (nextFacts as any).fault_ratio_minimum_target = "opponent_80_ego_20";
            } else if ((isUnlit && isDark && isAbnormalPosition) || (isDrunk && isAbnormalPosition)) {
                (nextFacts as any).fault_ratio_claim_target = "opponent_90_ego_10";
                (nextFacts as any).fault_ratio_realistic_target = "opponent_80_ego_20";
                (nextFacts as any).fault_ratio_minimum_target = "opponent_70_ego_30";
            }
        }

        if (factKey === "stopped") {
            nextFacts.stopped = value === "yes" ? true : value === "no" ? false : undefined;
        } else if (factKey === "sudden_brake_without_reason" || factKey === "sudden_brake") {
            nextFacts.sudden_brake = value === "yes";
        } else if (factKey === "lawful_stop_reason" || factKey === "stop_reason") {
            nextFacts.stop_reason = value;
        } else if (factKey === "brake_light_failure" || factKey === "brake_light") {
            nextFacts.brake_light = value;
        } else if (factKey === "abnormal_stop_position") {
            nextFacts.abnormal_stop = value === "abnormal_stop";
        } else if (factKey === "collision_object_type") {
            (nextFacts as any).collision_object_type = value;

            if (value === "parked_vehicle") {
                markStealthParkedVehicleCollision();
            } else if (value === "fixed_object" || value === "fallen_or_movable_object") {
                nextFacts.accident_party_type = "car_vs_object";
                nextFacts.accident_type = "object_collision";
                (nextFacts as any).knia_major_party_type = "car_vs_object";
            }
        } else if (factKey === "stealth_collision_target") {
            (nextFacts as any).stealth_collision_target = value;
            (nextFacts as any).collision_target = value === "parked_truck" ? "truck" : value === "parked_vehicle" ? "parked_vehicle" : value;
            if (value === "parked_truck" || value === "parked_vehicle") {
                markStealthParkedVehicleCollision();
            } else if (value === "fixed_object") {
                nextFacts.accident_party_type = "car_vs_object";
                nextFacts.accident_type = "object_collision";
                (nextFacts as any).knia_major_party_type = "car_vs_object";
            }
        } else if (factKey === "stealth_parked_position") {
            (nextFacts as any).stealth_parked_position = value;
            (nextFacts as any).parked_vehicle_position = value === "under_bridge_flowerbed" ? "flowerbed_or_median" : value;
            markStealthParkedVehicleCollision();
        } else if (factKey === "stealth_lighting") {
            (nextFacts as any).stealth_lighting = value;
            (nextFacts as any).parked_vehicle_lighting =
                value === "unlit_stealth" ? "unlit_stealth" : value === "lights_on" ? "all_lights_on" : value;
            markStealthParkedVehicleCollision();
        } else if (factKey === "stealth_visibility") {
            (nextFacts as any).stealth_visibility = value;
            (nextFacts as any).visibility_condition = value;
            markStealthParkedVehicleCollision();
        } else if (factKey === "opponent_drunk_driving") {
            (nextFacts as any).opponent_drunk_driving = value;
            (nextFacts as any).opponent_impairment =
                value === "drunk_confirmed" ? "drunk_driving_confirmed" : value === "drunk_suspected" ? "suspected_drunk" : value;
            markStealthParkedVehicleCollision();
        } else if (factKey === "stealth_avoidability") {
            (nextFacts as any).stealth_avoidability = value;
            (nextFacts as any).avoidability = value;
            markStealthParkedVehicleCollision();
        } else if (factKey === "collision_target") {
            (nextFacts as any).collision_target = value;

            if (value === "parked_vehicle" || value === "truck") {
                markStealthParkedVehicleCollision();
            } else if (value === "facility" || value === "fixed_object") {
                nextFacts.accident_party_type = "car_vs_object";
                nextFacts.accident_type = "object_collision";
                (nextFacts as any).knia_major_party_type = "car_vs_object";
            }
        } else if (factKey === "parked_vehicle_position") {
            (nextFacts as any).parked_vehicle_position = value;

            if (value === "traffic_space" || value === "flowerbed_or_median" || value === "under_bridge" || value === "roadside") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "parked_vehicle_lighting") {
            (nextFacts as any).parked_vehicle_lighting = value;

            if (value === "unlit_stealth" || value === "no_lights" || value === "unknown_but_dark") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "visibility_condition") {
            (nextFacts as any).visibility_condition = value;

            if (value === "night_dark" || value === "under_bridge_dark" || value === "low_visibility") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "opponent_impairment") {
            (nextFacts as any).opponent_impairment = value;

            if (value === "drunk_driving_confirmed" || value === "suspected_drunk") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "avoidability") {
            (nextFacts as any).avoidability = value;

            if (value === "limited" || value === "nearly_impossible") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "abnormal_parking") {
            (nextFacts as any).abnormal_parking = value === "yes" ? true : value === "no" ? false : undefined;

            if (value === "yes") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "visibility_issue") {
            (nextFacts as any).visibility_issue = value;
            (nextFacts as any).night_no_lights_or_low_visibility = value === "stealth_no_lights" || value === "hard_to_see";

            if (value === "stealth_no_lights" || value === "hard_to_see") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "road_environment") {
            (nextFacts as any).road_environment = value;

            if (value === "under_bridge" || value === "flowerbed_or_median" || value === "dark_road") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "avoidance_time") {
            (nextFacts as any).avoidance_time = value;

            if (value === "limited" || value === "nearly_impossible") {
                (nextFacts as any).avoidability = value;
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "crosswalk_context") {
            (nextFacts as any).crosswalk_context = value;
            if (value === "crosswalk" || value === "near_crosswalk") {
                nextFacts.accident_party_type = "car_vs_person";
                nextFacts.accident_type = "pedestrian_crosswalk_accident";
                (nextFacts as any).knia_major_party_type = "car_vs_person";
            }
        } else if (factKey === "pedestrian_signal") {
            (nextFacts as any).pedestrian_signal = value;
        } else if (factKey === "pedestrian_visibility") {
            (nextFacts as any).pedestrian_visibility = value;
        } else if (factKey === "turn_signal") {
            (nextFacts as any).turn_signal = value;
        } else if (factKey === "impact_position") {
            (nextFacts as any).impact_position = value;
        } else if (factKey === "lane_change_manner") {
            (nextFacts as any).lane_change_manner = value;
            nextFacts.accident_type = "lane_change_collision";
            nextFacts.accident_party_type = "car_vs_car";
            (nextFacts as any).knia_major_party_type = "car_vs_car";
        } else if (factKey === "signal_context") {
            (nextFacts as any).signal_context = value;
        } else if (factKey === "intersection_movement") {
            (nextFacts as any).intersection_movement = value;
            nextFacts.accident_type = "intersection_collision";
            nextFacts.accident_party_type = "car_vs_car";
            (nextFacts as any).knia_major_party_type = "car_vs_car";
        } else if (factKey === "intersection_entry_order") {
            (nextFacts as any).intersection_entry_order = value;
        } else if (factKey === "bicycle_location") {
            (nextFacts as any).bicycle_location = value;
            nextFacts.accident_party_type = "car_vs_bicycle";
            nextFacts.accident_type = "bicycle_collision";
            (nextFacts as any).knia_major_party_type = "car_vs_bicycle";
        } else if (factKey === "bicycle_movement") {
            (nextFacts as any).bicycle_movement = value;
        } else if (factKey === "single_vehicle_cause") {
            (nextFacts as any).single_vehicle_cause = value;
            nextFacts.accident_party_type = "single_vehicle";
            nextFacts.accident_type = "single_vehicle_accident";
            (nextFacts as any).knia_major_party_type = "single_vehicle";
        } else if (factKey === "external_cause_evidence") {
            (nextFacts as any).external_cause_evidence = value;
        } else if (factKey === "accident_counterpart") {
            (nextFacts as any).accident_counterpart = value;

            if (value === "person") {
                nextFacts.accident_party_type = "car_vs_person";
                nextFacts.accident_type = "pedestrian_crosswalk_accident";
                (nextFacts as any).knia_major_party_type = "car_vs_person";
            } else if (value === "bicycle") {
                nextFacts.accident_party_type = "car_vs_bicycle";
                nextFacts.accident_type = "bicycle_collision";
                (nextFacts as any).knia_major_party_type = "car_vs_bicycle";
            } else if (value === "parked_vehicle") {
                markStealthParkedVehicleCollision();
            } else if (value === "object") {
                nextFacts.accident_party_type = "car_vs_object";
                nextFacts.accident_type = "object_collision";
                (nextFacts as any).knia_major_party_type = "car_vs_object";
            } else if (value === "car") {
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
            }
        } else if (factKey === "accident_location_context") {
            (nextFacts as any).accident_location_context = value;

            if (value === "intersection") {
                nextFacts.accident_type = "intersection_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
            } else if (value === "lane") {
                nextFacts.accident_type = "lane_change_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
            } else if (value === "crosswalk") {
                nextFacts.accident_type = "pedestrian_crosswalk_accident";
                nextFacts.accident_party_type = "car_vs_person";
                (nextFacts as any).knia_major_party_type = "car_vs_person";
            } else if (value === "parking_or_roadside") {
                nextFacts.accident_type = "object_collision";
            } else if (value === "under_bridge" || value === "flowerbed_or_median") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "visibility_or_weather") {
            (nextFacts as any).visibility_or_weather = value;
            (nextFacts as any).night_no_lights_or_low_visibility = value === "night_or_dark";

            if (value === "night_or_dark") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "rear_end_role") {
            (nextFacts as any).rear_end_role = value;

            if (value === "ego_hit_front") {
                nextFacts.accident_type = "rear_end_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
                (nextFacts as any).collision_role = "ego_hit_front";
            } else if (value === "hit_by_rear") {
                nextFacts.accident_type = "rear_end_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
                (nextFacts as any).collision_role = "hit_by_rear";
            }
        } else if (factKey === "accident_direction") {
            (nextFacts as any).accident_direction = value;

            if (value === "ego_hit_front") {
                nextFacts.accident_type = "rear_end_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
                (nextFacts as any).rear_end_role = "ego_hit_front";
                (nextFacts as any).collision_role = "ego_hit_front";
            } else if (value === "hit_by_rear") {
                nextFacts.accident_type = "rear_end_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
                (nextFacts as any).rear_end_role = "hit_by_rear";
                (nextFacts as any).collision_role = "hit_by_rear";
            } else if (value === "object_collision") {
                nextFacts.accident_type = "object_collision";
                nextFacts.accident_party_type = "car_vs_object";
                (nextFacts as any).knia_major_party_type = "car_vs_object";
            } else if (value === "intersection") {
                nextFacts.accident_type = "intersection_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
            } else if (value === "lane_change") {
                nextFacts.accident_type = "lane_change_collision";
                nextFacts.accident_party_type = "car_vs_car";
                (nextFacts as any).knia_major_party_type = "car_vs_car";
            } else if (value === "pedestrian") {
                nextFacts.accident_type = "pedestrian_crosswalk_accident";
                nextFacts.accident_party_type = "car_vs_person";
                (nextFacts as any).knia_major_party_type = "car_vs_person";
            } else if (value === "parked_vehicle" || value === "stealth_parked_vehicle") {
                markStealthParkedVehicleCollision();
            }
        } else if (factKey === "front_vehicle_status") {
            (nextFacts as any).front_vehicle_status = value;
            (nextFacts as any).rear_end_role = "ego_hit_front";
            (nextFacts as any).collision_role = "ego_hit_front";

            if (value === "sudden_stop") {
                nextFacts.sudden_brake = true;
            }
        } else if (factKey === "front_stop_reason") {
            (nextFacts as any).front_stop_reason = value;
            nextFacts.stop_reason = value;
        } else if (factKey === "front_brake_light") {
            (nextFacts as any).front_brake_light = value;
            nextFacts.brake_light = value;
        } else if (factKey === "following_distance") {
            (nextFacts as any).following_distance = value;
        } else if (factKey === "rear_end_avoidance_time") {
            (nextFacts as any).rear_end_avoidance_time = value;
        } else {
            (nextFacts as any)[factKey] = value;
        }

        facts.value = nextFacts;
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