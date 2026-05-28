import type { AccidentFacts } from "../api/client";

export interface CaseWorkspacePayloadInput {
    descriptionText: string;
    facts: AccidentFacts;
    selectedKeywords: string[];
    analysisMode: string;
}

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

export function buildTextAnalysisPayload(input: CaseWorkspacePayloadInput) {
    return buildCaseInputPayload(input);
}

export function buildVideoAnalysisPayload(uploadId: string, input: CaseWorkspacePayloadInput) {
    return {
        upload_id: uploadId,
        ...buildCaseInputPayload(input),
    };
}

export function buildFollowupAnalysisPayload(input: CaseWorkspacePayloadInput, followupAnswers: Record<string, string>) {
    return {
        ...buildCaseInputPayload(input),
        followup_answers: followupAnswers,
    };
}
