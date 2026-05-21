import { describe, expect, it } from "vitest";
import { composeReanalysisChangeCard, enrichEasyReport, sanitizeEasyReport } from "../src/lib/report-composer.js";

describe("report composer", () => {
  it("adds a user-safe evidence reliability card without raw claim internals", () => {
    const report = sanitizeEasyReport({ headline: "테스트 리포트" });
    const enriched = enrichEasyReport(report, {
      claim_evidence: {
        coverage_level: "high",
        coverage_ratio: 0.9,
        claim_count: 10,
        supported_claim_count: 9,
        unsupported_claim_count: 0,
        weak_claim_count: 1,
        unsupported_claims: [{ claim_id: "x", support_level: "unsupported" }],
        warnings: ["일부 판단은 간접 근거만 있어 추가 확인이 필요합니다."],
      },
      evidence_audit: {
        claim_evidence_coverage: { level: "high", ratio: 0.9 },
      },
    });

    const text = JSON.stringify(enriched);
    expect(enriched.evidence_reliability_card.level_label).toBe("높음");
    expect(enriched.evidence_reliability_card.summary).toContain("주요 판단 10개");
    expect(text).not.toContain("claim_id");
    expect(text).not.toContain("evidence_refs");
    expect(text).not.toContain("support_level");
  });

  it("keeps user-safe missing-info questions usable after sanitizing", () => {
    const report = sanitizeEasyReport({
      missing_info: {
        title: "더 정확한 분석을 위해 필요한 정보",
        questions: [
          {
            field: "injury",
            label: "인명피해 여부",
            question: "다친 사람이 있나요?",
            input_type: "single_choice",
            options: ["다친 사람 없음", "내가 다침"],
          },
        ],
      },
      input_requirements: { blocking_fields: ["injury"] },
    });

    expect(report.missing_info.questions[0].field).toBe("injury");
    expect(report.missing_info.questions[0].question).toBe("다친 사람이 있나요?");
    expect(JSON.stringify(report)).not.toContain("input_requirements");
    expect(JSON.stringify(report)).not.toContain("blocking_fields");
  });

  it("summarizes reanalysis changes without exposing judgment internals", () => {
    const card = composeReanalysisChangeCard(
      {
        scenario_type: "rear_end_collision",
        fault_ratio: { my: 30, other: 70 },
        evidence_audit: { scenario_evidence_coverage: { coverage_level: "low" } },
        agent_judgment: { overall_status: "needs_review" },
        required_input_questions: [{ field: "injury", question: "다친 사람이 있나요?" }],
      },
      {
        scenario_type: "rear_end_collision",
        fault_ratio: { my: 10, other: 90 },
        evidence_audit: { scenario_evidence_coverage: { coverage_level: "high" } },
        agent_judgment: { overall_status: "evidence_supported" },
        required_input_questions: [],
      }
    );

    expect(card?.changes.map((item: any) => item.label)).toContain("과실비율");
    expect(card?.stats.find((item: any) => item.label === "남은 질문")?.value).toBe("0개");
    expect(JSON.stringify(card)).not.toContain("agent_judgment");
    expect(JSON.stringify(card)).not.toContain("evidence_supported");
  });
});
