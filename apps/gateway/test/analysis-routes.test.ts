import Fastify from "fastify";
import { describe, expect, it } from "vitest";
import { buildReanalysisVideoMetadata, composeGuidedProgressPayload, registerAnalysisRoutes } from "../src/routes/analysis.js";
import { errorPayload } from "../src/lib/errors.js";

describe("analysis route helpers", () => {
  it("preserves latest upload metadata for followup reanalysis", () => {
    const metadata = buildReanalysisVideoMetadata({
      metadata: {
        observations: [{ field: "stopped", value: false, confidence: 0.93 }],
        representative_frames: ["frame_001.jpg"],
        preprocess_summary: "Local video verified.",
      },
      file_name: "accident.mp4",
      status: "ready",
      preprocess_summary: "Local video verified.",
    });

    expect(metadata).toMatchObject({
      upload_status: "ready",
      file_name: "accident.mp4",
      preprocess_summary: "Local video verified.",
    });
    expect(metadata?.metadata.observations[0].field).toBe("stopped");
  });

  it("lets explicit request video metadata override stored upload metadata", () => {
    const metadata = buildReanalysisVideoMetadata(
      { metadata: { observations: [{ field: "stopped", value: true }] }, file_name: "stored.mp4" },
      { metadata: { observations: [{ field: "lane_change_actor", value: "opponent" }] } }
    );

    expect(metadata?.metadata.observations[0].field).toBe("lane_change_actor");
  });

  it("builds guided progress without exposing internal job terms", () => {
    const progress = composeGuidedProgressPayload(
      { status: "analyzing" },
      [
        { type: "video_preprocess", status: "running", attempts: 2, id: "job-1" },
        { type: "video_analyze", status: "queued", attempts: 1, id: "job-2" },
      ]
    );

    const text = JSON.stringify(progress);
    expect(progress.current_stage).toBe("사고 장면 확인");
    expect(progress.current_message).toBe("사고 장면을 찾고 있습니다.");
    expect(text).toContain("사고 장면을 찾고 있습니다.");
    expect(text).not.toContain("video_preprocess");
    expect(text).not.toContain("video_analyze");
    expect(text).not.toContain("attempts");
    expect(text).not.toContain("job-1");
  });

  it("marks dead jobs as failed without exposing internal job fields", () => {
    const progress = composeGuidedProgressPayload(
      { status: "analyzing" },
      [{ type: "video_analyze", status: "dead", attempts: 3, last_error: "secret stack", id: "job-dead" }]
    );

    const text = JSON.stringify(progress);
    expect(progress.failed).toBe(true);
    expect(progress.result_ready).toBe(false);
    expect(progress.can_show_result).toBe(false);
    expect(progress.error_message).toBe("분석 중 문제가 발생했습니다. 다시 시도하거나 고급 진단을 확인해 주세요.");
    expect(text).not.toContain("video_analyze");
    expect(text).not.toContain("secret stack");
    expect(text).not.toContain("job-dead");
    expect(text).not.toContain("attempts");
  });

  it("returns ready progress when a result exists", () => {
    const progress = composeGuidedProgressPayload({ status: "analyzing", latest_result_id: "result-1" }, []);

    expect(progress.progress_percent).toBe(100);
    expect(progress.result_ready).toBe(true);
    expect(progress.can_show_result).toBe(true);
    expect(progress.current_stage).toBe("결과 준비 완료");
  });

  it("returns not_ready easy report instead of 404 when analysis is not created yet", async () => {
    const app = Fastify({ logger: false });
    app.addHook("onRequest", async (req) => {
      (req as any).user = { id: "user-1", role: "user" };
    });
    const db = {
      async query(sql: string) {
        if (sql.includes("FROM cases")) return { rowCount: 1, rows: [{ id: "case-1" }] };
        if (sql.includes("FROM analysis_results")) return { rowCount: 0, rows: [] };
        return { rowCount: 0, rows: [] };
      },
    };
    registerAnalysisRoutes(app, {
      apiPrefix: "/api/v1",
      db,
      redis: {},
      agentUrl: "http://agent",
      internalToken: "token",
      analyzeTimeoutMs: 1000,
      retryCount: 0,
      errorPayload,
    });

    const response = await app.inject({ method: "GET", url: "/api/v1/cases/case-1/easy-report" });
    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      status: "not_ready",
      message: "아직 분석 결과가 없습니다.",
      report: null,
    });
    await app.close();
  });
});
