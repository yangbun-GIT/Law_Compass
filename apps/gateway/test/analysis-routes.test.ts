import { describe, expect, it } from "vitest";
import { buildReanalysisVideoMetadata } from "../src/routes/analysis.js";

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
});
