import type { AccidentFacts } from "../api/client";

export interface CaseWorkspacePayloadInput {
    descriptionText: string;
    facts: AccidentFacts;
    selectedKeywords: string[];
    analysisMode: string;
}

export type InitialIntakePayload = {
    accident_major_category: string;
    preliminary_accident_type: string;
    is_video_only?: boolean;
    video_upload_id?: string;
    natural_language_description?: string;
    natural_language_policy: {
        weight: "low";
        source_type: "subjective_user_claim";
        can_override_video: false;
        can_override_structured_followup: false;
    };
};

export function normalizeCaseDescription(descriptionText: string) {
    const trimmed = descriptionText.trim();
    return trimmed || "영상 자료 기반 사고 분석";
}

export function buildCaseInputPayload(input: CaseWorkspacePayloadInput) {
    return {
        description_text: normalizeCaseDescription(input.descriptionText),
        structured_facts: input.facts,
        selected_keywords: input.selectedKeywords,
        analysis_mode: input.analysisMode,
    };
}

function normalizeMajorCategory(value: unknown, fallback = "unknown") {
    const raw = String(value || "").trim();
    if (!raw) return fallback;
    if (raw === "car_vs_two_wheeler") return "car_vs_two_wheeler";
    if (raw === "car_vs_motorcycle") return "car_vs_two_wheeler";
    if (raw === "car_vs_object") return "single_vehicle";
    return raw;
}

function normalizePreliminaryType(value: unknown) {
    const raw = String(value || "").trim();
    return raw && raw !== "unknown" ? raw : "unknown";
}

export function buildInitialIntakePayload(input: CaseWorkspacePayloadInput, uploadId?: string): InitialIntakePayload {
    const facts = input.facts || {};
    const description = input.descriptionText.trim();
    const majorCategory = normalizeMajorCategory(
        (facts as any).initial_accident_major_category ||
        (facts as any).selected_major_category ||
        facts.accident_party_type ||
        (facts as any).knia_major_party_type,
    );
    const preliminaryType = normalizePreliminaryType(
        (facts as any).initial_preliminary_accident_type ||
        (facts as any).selected_preliminary_accident_type ||
        facts.accident_type,
    );

    return {
        accident_major_category: majorCategory,
        preliminary_accident_type: preliminaryType,
        ...(uploadId && !description ? { is_video_only: true } : {}),
        ...(uploadId ? { video_upload_id: uploadId } : {}),
        ...(description ? { natural_language_description: description } : {}),
        natural_language_policy: {
            weight: "low",
            source_type: "subjective_user_claim",
            can_override_video: false,
            can_override_structured_followup: false,
        },
    };
}

export function buildTextAnalysisPayload(input: CaseWorkspacePayloadInput) {
    return {
        ...buildCaseInputPayload(input),
        initial_intake: buildInitialIntakePayload(input),
    };
}

export function buildVideoAnalysisPayload(uploadId: string, input: CaseWorkspacePayloadInput) {
    return {
        upload_id: uploadId,
        ...buildCaseInputPayload(input),
        initial_intake: buildInitialIntakePayload(input, uploadId),
    };
}

export function buildFollowupAnalysisPayload(input: CaseWorkspacePayloadInput, followupAnswers: Record<string, string>) {
    return {
        ...buildCaseInputPayload(input),
        initial_intake: buildInitialIntakePayload(input),
        followup_answers: followupAnswers,
    };
}
