import { FAILED_JOB_STATUSES, FINISHED_JOB_STATUSES, RUNNING_JOB_STATUSES } from "./caseWorkspaceGuidance";

export type JobItem = {
    id: string;
    type: string;
    status: string;
    attempts?: number;
    attempt?: number;
};

export function normalizeStatus(value: any): string {
    return String(value ?? "").trim().toLowerCase();
}

export function isRunningJob(job: JobItem): boolean {
    return RUNNING_JOB_STATUSES.includes(normalizeStatus(job.status));
}

export function isFinishedJob(job: JobItem): boolean {
    return FINISHED_JOB_STATUSES.includes(normalizeStatus(job.status));
}

export function isFailedJob(job: JobItem): boolean {
    return FAILED_JOB_STATUSES.includes(normalizeStatus(job.status));
}

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

export function normalizeProgressSteps(steps: any[]) {
    return steps.map((step) => ({
        ...step,
        label: normalizeProgressStepLabel(step),
    }));
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

export function getReportPayload(value: any): any | null {
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

export function isReadyReport(value: any): boolean {
    return Boolean(getReportPayload(value));
}
