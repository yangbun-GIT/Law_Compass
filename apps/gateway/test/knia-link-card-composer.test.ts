import { describe, expect, it } from "vitest";
import { enrichEasyReport, sanitizeEasyReport } from "../src/lib/report-composer.js";

describe("KNIA link card composition", () => {
  it("creates a KNIA link card from non-primary basis cards", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({ headline: "report" }), {
      knia_primary_match: null,
      elderly_friendly_report: {
        knia_basis_cards: [
          {
            chart_no: "TEST-GENERIC-1",
            title: "임의 KNIA 기준",
            source_url: "https://accident.knia.or.kr/myaccident-content?chartNo=TEST-GENERIC-1",
          },
        ],
      },
    });

    expect((enriched as any).related_knia_video_card.title).toBe("KNIA 원문 기준 및 관련 영상");
    expect((enriched as any).related_knia_video_card.button_label).toBe("KNIA 원문 기준 보기");
    expect((enriched as any).related_knia_video_card.source_url).toContain("https://accident.knia.or.kr");
  });

  it("prefers KNIA video urls and drops default logo thumbnails", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({ headline: "report" }), {
      related_knia_video_card: {
        chart_no: "TEST-GENERIC-2",
        title: "임의 KNIA 영상 기준",
        video_url: "https://accident.knia.or.kr/video/generic-2.mp4",
        source_url: "https://accident.knia.or.kr/myaccident-content?chartNo=TEST-GENERIC-2",
        thumbnail_url: "https://accident.knia.or.kr/images/common/logo_test.jpg",
        media_provider: "external_url",
        license_status: "source_link_only",
      },
    });

    const card = (enriched as any).related_knia_video_card;
    expect(card.button_label).toBe("KNIA 관련 영상 보기");
    expect(card.source_url).toBe("https://accident.knia.or.kr/video/generic-2.mp4");
    expect(card.thumbnail_url).toBeUndefined();
    expect(card.display_mode).toBe("external_link");
    expect(card.notice).toContain("LawCompass 서버에 저장하지 않고");
    expect((enriched as any).simple_report.knia_and_video.primary.button_label).toBe("KNIA 관련 영상 보기");
  });

  it("blocks unsafe KNIA display urls while keeping a non-empty candidate notice", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({ headline: "report" }), {
      knia_matches: [
        { chart_no: "UNSAFE-JS", title: "KNIA 기준", source_url: "javascript:alert(1)" },
        { chart_no: "UNSAFE-DATA", title: "KNIA 기준", source_url: "data:text/html,unsafe" },
        { chart_no: "UNSAFE-FILE", title: "KNIA 기준", source_url: "file:///tmp/unsafe" },
        { chart_no: "UNSAFE-LOCAL", title: "KNIA 기준", source_url: "http://localhost/internal" },
        { chart_no: "UNSAFE-IP", title: "KNIA 기준", source_url: "http://127.0.0.1/internal" },
        { chart_no: "UNSAFE-OTHER", title: "KNIA 기준", source_url: "https://example.com/unsafe" },
      ],
    });

    const text = JSON.stringify(enriched);
    const card = (enriched as any).related_knia_video_card;
    expect(card.source_url).toBeUndefined();
    expect(card.missing_source_notice).toContain("상세 기준 수집 필요");
    expect(card.missing_source_notice).toContain("수집된 KNIA 원문 링크가 없습니다");
    expect(text).not.toContain("javascript:");
    expect(text).not.toContain("data:text");
    expect(text).not.toContain("file://");
    expect(text).not.toContain("localhost");
    expect(text).not.toContain("127.0.0.1");
    expect(text).not.toContain("example.com");
    expect(text).not.toContain("source_blocked_reason");
  });

  it("does not display vehicle or bicycle KNIA links for car_vs_person results", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({ headline: "차대사람 사고" }), {
      knia_major_party_type: "car_vs_person",
      knia_matches: [
        { chart_no: "차43", major_party_type: "car_vs_car", title: "차대차 진로변경", source_url: "https://accident.knia.or.kr/car43" },
        { chart_no: "거1", major_party_type: "car_vs_bicycle", title: "자전거", source_url: "https://accident.knia.or.kr/bike1" },
        { chart_no: "보1", major_party_type: "car_vs_person", title: "보행자 사고", source_url: "https://accident.knia.or.kr/person1" },
      ],
      fault_ratio: {
        base_fault: {},
        final_fault: {},
        knia_reference_fault: {
          source_chart: { chart_no: "보1", major_party_type: "car_vs_person", title: "보행자 사고" },
        },
      },
    });

    const text = JSON.stringify(enriched);
    expect((enriched as any).related_knia_video_card.chart_no).toBe("보1");
    expect((enriched as any).simple_report.knia_and_video.primary.chart_no).toBe("보1");
    expect(text).toContain("보1");
    expect(text).not.toContain("차43");
    expect(text).not.toContain("거1");
  });
});
