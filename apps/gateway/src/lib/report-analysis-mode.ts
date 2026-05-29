import { isPlainObject, type AnyRecord } from "./report-composer-common.js";

export function applyAnalysisModeContract(report: AnyRecord = {}, result: AnyRecord = {}): AnyRecord {
  const mode = normalizeAnalysisMode(
    result.analysis_mode ??
      result.analysisMode ??
      result.analysis_mode_contract?.mode ??
      result.structured_facts?.analysis_mode ??
      result.model_info?.analysis_mode ??
      report.analysis_mode ??
      report.display_mode ??
      report.analysis_mode_contract?.mode,
  );

  const nextReport: AnyRecord = {
    ...report,
    display_mode: mode,
    analysis_mode: mode,
    analysis_mode_contract: {
      ...(isPlainObject(report.analysis_mode_contract) ? report.analysis_mode_contract : {}),
      mode,
      label: analysisModeLabel(mode),
      description: analysisModeDescription(mode),
      hidden_sections: analysisModeHiddenSections(mode),
      visible_sections: analysisModeVisibleSections(mode),
      compact: mode === "user_friendly",
      preserve_report_fields: true,
    },
  };

  if (mode === "expert" && isPlainObject(nextReport.knia_fault_adjustment_card)) {
    nextReport.knia_fault_adjustment_card.title = nextReport.knia_fault_adjustment_card.title || "KNIA 기본과실과 가감요소";
  }

  return nextReport;
}

export function normalizeAnalysisMode(value: unknown): string {
  const mode = String(value ?? "").trim();

  if (
    mode === "expert" ||
    mode === "legal_precedent_focused" ||
    mode === "full_deep_research" ||
    mode === "deep_research" ||
    mode === "debug" ||
    mode === "legal" ||
    mode === "precedent" ||
    mode === "legal_basis" ||
    mode === "legal-focused" ||
    mode === "criminal-liability-focused" ||
    mode === "deep" ||
    mode === "full" ||
    mode === "research" ||
    mode === "evidence-review"
  ) {
    return "expert";
  }

  return "user_friendly";
}

function analysisModeLabel(mode: string): string {
  return mode === "expert" ? "전문가모드" : "일반사용자모드";
}

function analysisModeDescription(mode: string): string {
  if (mode === "expert") {
    return "KNIA 기준, 법률 근거, 가감요소, 증거, 추가 확인사항까지 자세히 보여줍니다.";
  }

  return "현재 상황, 과실비율, 관련 KNIA 근거와 영상만 간단히 보여줍니다.";
}

function analysisModeHiddenSections(mode: string): string[] {
  if (mode === "expert") return ["developer_diagnostics"];
  return ["raw_evidence", "debug_diagnostics", "model_info", "token_usage", "internal_trace", "long_legal_text"];
}

function analysisModeVisibleSections(mode: string): string[] {
  if (mode === "expert") return ["full_report"];
  return ["current_situation", "fault_ratio", "knia_and_video"];
}
