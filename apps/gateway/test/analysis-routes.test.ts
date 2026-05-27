import { describe, expect, it } from "vitest";
import { buildReanalysisVideoMetadata, composeGuidedProgressPayload } from "../src/routes/analysis.js";

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
    expect(progress.current_stage).toBe("영상 확인 중");
    expect(progress.current_message).toBe("분석 중입니다.");
    expect(text).toContain("사고 장면을 찾고 있습니다.");
    expect(text).not.toContain("video_preprocess");
    expect(text).not.toContain("video_analyze");
    expect(text).not.toContain("attempts");
    expect(text).not.toContain("job-1");
  });
});
