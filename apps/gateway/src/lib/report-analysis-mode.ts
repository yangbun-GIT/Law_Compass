import { isPlainObject, type AnyRecord } from "./report-composer-common.js";

export function applyAnalysisModeContract(report: AnyRecord = {}, result: AnyRecord = {}): AnyRecord {
    const mode = normalizeAnalysisMode(
        result.analysis_mode ??
        result.analysisMode ??
        result.analysis_mode_contract?.mode ??
        result.structured_facts?.analysis_mode ??
        result.model_info?.analysis_mode ??
        report.analysis_mode ??
        report.analysis_mode_contract?.mode,
    );

    const nextReport: AnyRecord = {
        ...report,
        analysis_mode: mode,
        analysis_mode_contract: {
            ...(isPlainObject(report.analysis_mode_contract) ? report.analysis_mode_contract : {}),
            mode,
            label: analysisModeLabel(mode),
            description: analysisModeDescription(mode),
            hidden_sections: analysisModeHiddenSections(mode),
            compact: mode === "quick_summary",
        },
    };

    if (mode === "fault_ratio_focused") {
        if (isPlainObject(nextReport.knia_fault_adjustment_card)) {
            nextReport.knia_fault_adjustment_card.title = "KNIA 기본과실과 가감요소";
        }
    }

    if (isLegacyQuickSummaryPruningRequested(report, result, mode)) {
        delete nextReport.legal_explanation;
        nextReport.legal_basis_cards = [];
        delete nextReport.expert_guidance_card;
        delete nextReport.knia_fault_adjustment_card;
        nextReport.detail_sections = {
            ...(isPlainObject(nextReport.detail_sections) ? nextReport.detail_sections : {}),
            notice: "빠른 요약에서는 긴 법률·판례 설명을 접어두고 핵심 판단만 보여줍니다.",
            evidence_summaries: [],
        };
    }

    return nextReport;
}

function normalizeAnalysisMode(value: unknown): string {
    const mode = String(value ?? "").trim();

    const allowed = new Set([
        "quick_summary",
        "fault_ratio_focused",
        "legal_precedent_focused",
        "insurance_response_focused",
        "full_deep_research",
    ]);

    if (allowed.has(mode)) {
        return mode;
    }

    if (mode === "fast" || mode === "summary" || mode === "quick") {
        return "quick_summary";
    }
    if (mode === "fault" || mode === "fault_ratio" || mode === "fault-focused") {
        return "fault_ratio_focused";
    }
    if (mode === "legal" || mode === "precedent" || mode === "legal_basis" || mode === "legal-focused" || mode === "criminal-liability-focused") {
        return "legal_precedent_focused";
    }
    if (mode === "insurance" || mode === "insurance-focused") {
        return "insurance_response_focused";
    }
    if (mode === "deep" || mode === "full" || mode === "research" || mode === "evidence-review") {
        return "full_deep_research";
    }

    return "quick_summary";
}

function analysisModeLabel(mode: string): string {
    const labels: Record<string, string> = {
        quick_summary: "빠른 요약",
        fault_ratio_focused: "과실비율 중심",
        legal_precedent_focused: "법률/판례 근거 중심",
        insurance_response_focused: "보험 대응 중심",
        full_deep_research: "전체 심층 리서치 분석",
    };
    return labels[mode] ?? "빠른 요약";
}

function analysisModeDescription(mode: string): string {
    const descriptions: Record<string, string> = {
        quick_summary: "핵심 상황과 예상 과실비율만 간단히 보여줍니다.",
        fault_ratio_focused: "KNIA 기준과 가감요소를 중심으로 과실비율을 계산합니다.",
        legal_precedent_focused: "과실비율 산정 후 관련 법률과 판례 근거를 자세히 보여줍니다.",
        insurance_response_focused: "보험사 대응에 필요한 자료와 주장 포인트를 중심으로 정리합니다.",
        full_deep_research: "사고 사실, 영상 관찰, KNIA, 법률, 보험 대응을 모두 자세히 보여줍니다.",
    };
    return descriptions[mode] ?? descriptions.quick_summary;
}

function analysisModeHiddenSections(mode: string): string[] {
    const hiddenSections: Record<string, string[]> = {
        quick_summary: ["long_legal_text", "deep_research_details"],
        fault_ratio_focused: ["long_legal_text"],
        legal_precedent_focused: [],
        insurance_response_focused: ["long_legal_text", "deep_research_details"],
        full_deep_research: [],
    };
    return hiddenSections[mode] ?? hiddenSections.quick_summary;
}

function isLegacyQuickSummaryPruningRequested(report: AnyRecord, result: AnyRecord, mode: string): boolean {
    if (mode !== "quick_summary") return false;
    if (result.analysis_mode || result.analysisMode || report.analysis_mode) return false;
    const contract = result.analysis_mode_contract;
    if (!isPlainObject(contract) || contract.mode !== "quick_summary") return false;
    return !("hidden_sections" in contract) && !("compact" in contract) && !("preserve_report_fields" in contract);
}
