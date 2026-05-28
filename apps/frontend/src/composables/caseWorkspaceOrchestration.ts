import type { Ref } from "vue";
import { normalizeProgressSteps } from "./caseWorkspaceProgress";

export type GuidedStep = "input" | "accident-type" | "purpose" | "questions" | "analyzing" | "result";

export interface ProgressUpdate {
    percent?: number;
    stage?: string;
    message?: string;
    steps?: any[];
}

export interface ProgressControllerContext {
    progressPercent: Ref<number>;
    progressStageLabel: Ref<string>;
    progressMessage: Ref<string>;
    progressSteps: Ref<any[]>;
    guidedStep: Ref<GuidedStep>;
}

export function delay(ms: number) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export function createCaseWorkspaceProgressController(context: ProgressControllerContext) {
    const { progressPercent, progressStageLabel, progressMessage, progressSteps, guidedStep } = context;

    function applyLocalProgress(next: ProgressUpdate) {
        if (typeof next.percent === "number") {
            progressPercent.value = Math.max(progressPercent.value, Math.min(100, Math.max(0, next.percent)));
        }

        if (next.stage) progressStageLabel.value = next.stage;
        if (next.message) progressMessage.value = next.message;
        if (Array.isArray(next.steps) && next.steps.length) progressSteps.value = normalizeProgressSteps(next.steps);
    }

    function markReportReady() {
        progressPercent.value = 100;
        progressStageLabel.value = "결과 준비 완료";
        progressMessage.value = "분석 결과가 준비되었습니다.";
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
            markReportReady();

            if (guidedStep.value === "analyzing") {
                guidedStep.value = "result";
            }
        }
    }

    return { applyBackendProgress, applyLocalProgress, markReportReady };
}

export function getRunningJobProgress(jobType: string | undefined, currentPercent: number): ProgressUpdate {
    if (jobType === "video_preprocess") {
        return {
            percent: Math.max(currentPercent, 45),
            stage: "영상 확인 중",
            message: "영상에서 사고 장면을 찾고 있습니다.",
        };
    }

    if (jobType === "video_analyze") {
        return {
            percent: Math.max(currentPercent, 65),
            stage: "사고 분석 중",
            message: "입력한 답변과 영상을 바탕으로 과실비율을 계산하고 있습니다.",
        };
    }

    return {
        percent: Math.max(currentPercent, 55),
        stage: "분석 중",
        message: "사고 내용을 분석하고 있습니다.",
    };
}
