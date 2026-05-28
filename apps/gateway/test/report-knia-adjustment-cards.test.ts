import { describe, expect, it } from "vitest";
import { enrichEasyReport, sanitizeEasyReport } from "../src/lib/report-composer.js";

describe("KNIA adjustment report cards", () => {
  it("splits basic, applied, unknown, and conditional adjustment payloads", () => {
    const enriched: any = enrichEasyReport(
      sanitizeEasyReport({ headline: "후미추돌 사고" }),
      {
        knia_primary_match: {
          chart_no: "차41-1",
          title: "정차 중 후방추돌",
          source_url: "https://accident.knia.or.kr/myaccident-content?chartNo=car41-1",
        },
        fault_ratio: {
          my: 0,
          other: 100,
          base_fault: { my: 0, other: 100 },
          final_fault: { my: 0, other: 100 },
          fault_range: { my: "0~10%", other: "90~100%" },
          applied_adjustments: [
            { label: "정상 신호대기 정차", delta_my: 0, reason: "정당한 정차 사유입니다." },
          ],
          not_applied_adjustments: [
            { label: "이유 없는 급정거", reason: "정당한 정차 사유가 확인되어 적용하지 않았습니다." },
          ],
          unknown_adjustments: [
            { label: "브레이크등 작동 여부", possible_delta_my: "0~10%p", reason: "확인되면 과실 범위가 달라질 수 있습니다." },
          ],
          conditional_outcomes: [
            { label: "브레이크등 고장인 경우", my_range: "0~10%", other_range: "90~100%", explanation: "고장 확인 시 앞차 과실이 늘 수 있습니다." },
          ],
        },
      }
    );

    expect(enriched.knia_basic_fault_card.chart_no).toBe("차41-1");
    expect(enriched.knia_basic_fault_card.base_fault).toEqual({ my: 0, other: 100 });
    expect(enriched.knia_applied_adjustment_card.items[0].label).toBe("정상 신호대기 정차");
    expect(enriched.knia_not_applied_adjustment_card.items[0].label).toBe("이유 없는 급정거");
    expect(enriched.knia_unknown_adjustment_card.items[0].delta).toBe("0~10%p");
    expect(enriched.knia_conditional_outcome_card.items[0].label).toBe("브레이크등 고장인 경우");
    expect(JSON.stringify(enriched)).not.toContain("chunk_id");
    expect(JSON.stringify(enriched)).not.toContain("source_type");
  });
});
