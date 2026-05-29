import { detectObjectsWithMlKit, getMlKitPluginStatus } from "../plugins/mlkitObjectDetector";
import type { ClientPreObservation, ClientPreObservationsPayload } from "../types/mobileObservations";
import { findForbiddenClientObservationFields } from "../types/mobileObservations";
import type { MlKitDetectedObject, MlKitDetection, MlKitFrameInput } from "../types/mlkit";

export type MlKitDemoOptions = {
  samplingFps: number;
  maxFrames: number;
  confidenceThreshold: number;
  enableTracking: boolean;
  resizeWidth: number;
  mockMode: boolean;
};

export type SampledVideoFrame = MlKitFrameInput & {
  previewUrl: string;
};

export type MlKitDemoRunResult = {
  provider: "google_mlkit" | "mock_mlkit_web_fallback";
  providerVersion: string;
  platform: "android" | "ios" | "web" | "unknown";
  videoDurationSec: number;
  originalWidth: number;
  originalHeight: number;
  sampledFrames: SampledVideoFrame[];
  detections: MlKitDetection[];
  payload: ClientPreObservationsPayload;
  detectedObjectCount: number;
  uniqueTrackCount: number;
  averageConfidence: number;
};

const WARNING_TEXT = "ML Kit 결과는 사고유형, 과실비율, 신호위반 확정값이 아닙니다.";

function waitForEvent(target: EventTarget, event: string) {
  return new Promise<void>((resolve, reject) => {
    const onSuccess = () => {
      cleanup();
      resolve();
    };
    const onError = () => {
      cleanup();
      reject(new Error(`video ${event} failed`));
    };
    const cleanup = () => {
      target.removeEventListener(event, onSuccess);
      target.removeEventListener("error", onError);
    };
    target.addEventListener(event, onSuccess, { once: true });
    target.addEventListener("error", onError, { once: true });
  });
}

function clampNumber(value: number, min: number, max: number) {
  if (!Number.isFinite(value)) return min;
  return Math.min(max, Math.max(min, value));
}

export async function readVideoMetadata(file: File): Promise<{ durationSec: number; originalWidth: number; originalHeight: number; sizeBytes: number }> {
  const url = URL.createObjectURL(file);
  const video = document.createElement("video");
  video.preload = "metadata";
  video.muted = true;
  video.playsInline = true;
  video.src = url;

  try {
    await waitForEvent(video, "loadedmetadata");
    const durationSec = Number.isFinite(video.duration) ? video.duration : 0;
    return {
      durationSec,
      originalWidth: video.videoWidth || 0,
      originalHeight: video.videoHeight || 0,
      sizeBytes: file.size,
    };
  } finally {
    URL.revokeObjectURL(url);
  }
}

export async function sampleVideoFrames(file: File, options: MlKitDemoOptions): Promise<{ durationSec: number; originalWidth: number; originalHeight: number; frames: SampledVideoFrame[] }> {
  const url = URL.createObjectURL(file);
  const video = document.createElement("video");
  video.preload = "metadata";
  video.muted = true;
  video.playsInline = true;
  video.src = url;

  try {
    await waitForEvent(video, "loadedmetadata");
    const durationSec = Number.isFinite(video.duration) ? video.duration : 0;
    const samplingFps = clampNumber(options.samplingFps, 0.1, 10);
    const maxFrames = Math.max(1, Math.floor(options.maxFrames));
    const intervalSec = 1 / samplingFps;
    const times: number[] = [];

    for (let time = 0; time <= Math.max(0, durationSec - 0.05) && times.length < maxFrames; time += intervalSec) {
      times.push(Number(time.toFixed(3)));
    }
    if (!times.length) times.push(0);

    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("canvas unavailable");

    const sourceWidth = video.videoWidth || options.resizeWidth;
    const sourceHeight = video.videoHeight || Math.round(options.resizeWidth * 0.5625);
    const targetWidth = Math.max(160, Math.min(options.resizeWidth || sourceWidth, sourceWidth));
    const targetHeight = Math.max(90, Math.round((sourceHeight / sourceWidth) * targetWidth));
    canvas.width = targetWidth;
    canvas.height = targetHeight;

    const frames: SampledVideoFrame[] = [];
    for (let index = 0; index < times.length; index += 1) {
      video.currentTime = times[index];
      await waitForEvent(video, "seeked");
      ctx.drawImage(video, 0, 0, targetWidth, targetHeight);
      const imageDataUrl = canvas.toDataURL("image/jpeg", 0.82);
      frames.push({
        frameIndex: index,
        frameTimeSec: times[index],
        imageDataUrl,
        previewUrl: imageDataUrl,
        width: targetWidth,
        height: targetHeight,
        confidenceThreshold: options.confidenceThreshold,
        enableTracking: options.enableTracking,
      });
    }

    return { durationSec, originalWidth: sourceWidth, originalHeight: sourceHeight, frames };
  } finally {
    URL.revokeObjectURL(url);
  }
}

function mockDetectionForFrame(frame: SampledVideoFrame): MlKitDetection {
  const started = performance.now();
  const left = Math.round(frame.width * 0.28);
  const top = Math.round(frame.height * 0.34);
  const width = Math.round(frame.width * 0.32);
  const height = Math.round(frame.height * 0.24);

  return {
    frameIndex: frame.frameIndex,
    frameTimeSec: frame.frameTimeSec,
    processingMs: Math.max(1, Math.round(performance.now() - started + 8)),
    width: frame.width,
    height: frame.height,
    objects: [
      {
        trackingId: optionsTrackId(frame.frameIndex),
        labels: [{ text: "vehicle", confidence: Math.max(frame.confidenceThreshold, 0.72), index: 0 }],
        boundingBox: {
          left,
          top,
          right: left + width,
          bottom: top + height,
          width,
          height,
        },
      },
    ],
  };
}

function optionsTrackId(frameIndex: number) {
  return frameIndex % 2 === 0 ? 1 : 2;
}

function bestLabel(object: MlKitDetectedObject) {
  const labels = Array.isArray(object.labels) ? object.labels : [];
  const sorted = labels.slice().sort((a, b) => Number(b.confidence ?? 0) - Number(a.confidence ?? 0));
  return sorted[0] ?? null;
}

function normalizeBbox(object: MlKitDetectedObject, frameWidth: number, frameHeight: number): [number, number, number, number] {
  const box = object.boundingBox;
  const left = clampNumber(box.left / frameWidth, 0, 1);
  const top = clampNumber(box.top / frameHeight, 0, 1);
  const right = clampNumber(box.right / frameWidth, 0, 1);
  const bottom = clampNumber(box.bottom / frameHeight, 0, 1);
  return [left, top, right, bottom];
}

function pixelBbox(object: MlKitDetectedObject): [number, number, number, number] {
  const box = object.boundingBox;
  return [box.left, box.top, box.right, box.bottom];
}

export function buildClientPreObservations(input: {
  videoId: string;
  provider: "google_mlkit" | "mock_mlkit_web_fallback";
  providerVersion: string;
  platform: "android" | "ios" | "web" | "unknown";
  sampledFrameCount: number;
  failedFrameCount: number;
  detections: MlKitDetection[];
}): ClientPreObservationsPayload {
  const totalProcessingMs = input.detections.reduce((sum, item) => sum + Number(item.processingMs || 0), 0);
  const processedFrameCount = input.detections.length;
  const observations: ClientPreObservation[] = [];

  for (const detection of input.detections) {
    const frameWidth = Number(detection.width || 1);
    const frameHeight = Number(detection.height || 1);
    for (const object of detection.objects || []) {
      const label = bestLabel(object);
      const confidence = clampNumber(Number(label?.confidence ?? 0), 0, 1);
      observations.push({
        field: "object_candidate",
        value: label?.text || "unknown_object",
        confidence,
        frame_time_sec: Number(detection.frameTimeSec || 0),
        bbox: normalizeBbox(object, frameWidth, frameHeight),
        bbox_pixels: pixelBbox(object),
        track_id: object.trackingId ?? null,
        metadata: {
          label: label?.text || "unknown_object",
          raw_category: label?.text || "unknown_object",
          frame_index: detection.frameIndex,
          provider: input.provider,
        },
      });
    }
  }

  const payload: ClientPreObservationsPayload = {
    source: "client_pre_observation",
    provider: input.provider,
    provider_version: input.providerVersion,
    video_id: input.videoId,
    created_at: new Date().toISOString(),
    device: {
      platform: input.platform,
    },
    performance: {
      sampled_frame_count: input.sampledFrameCount,
      processed_frame_count: processedFrameCount,
      failed_frame_count: input.failedFrameCount,
      total_processing_ms: totalProcessingMs,
      avg_processing_ms_per_frame: processedFrameCount ? totalProcessingMs / processedFrameCount : 0,
    },
    observations,
    warnings: [WARNING_TEXT],
  };

  const forbidden = findForbiddenClientObservationFields(payload);
  if (forbidden.length) {
    throw new Error(`client_pre_observations contains forbidden fields: ${forbidden.join(", ")}`);
  }

  return payload;
}

export async function runMlKitDemo(file: File, options: MlKitDemoOptions): Promise<MlKitDemoRunResult> {
  const status = getMlKitPluginStatus();
  if (!status.available && !options.mockMode) {
    throw new Error("Native ML Kit plugin is not available. Enable mock mode for browser testing.");
  }

  const { durationSec, originalWidth, originalHeight, frames } = await sampleVideoFrames(file, options);
  const detections: MlKitDetection[] = [];
  let failedFrameCount = 0;

  for (const frame of frames) {
    try {
      detections.push(options.mockMode || !status.available ? mockDetectionForFrame(frame) : await detectObjectsWithMlKit(frame));
    } catch {
      failedFrameCount += 1;
    }
  }

  const provider = status.available && !options.mockMode ? "google_mlkit" : "mock_mlkit_web_fallback";
  const providerVersion = status.available && !options.mockMode ? status.providerVersion || "native" : "web-mock-v1";
  const payload = buildClientPreObservations({
    videoId: `local-${file.name}-${file.size}`,
    provider,
    providerVersion,
    platform: status.platform,
    sampledFrameCount: frames.length,
    failedFrameCount,
    detections,
  });

  const confidences = payload.observations.map((item) => item.confidence);
  const averageConfidence = confidences.length ? confidences.reduce((sum, value) => sum + value, 0) / confidences.length : 0;
  const uniqueTrackCount = new Set(payload.observations.map((item) => item.track_id).filter((item) => item !== null && item !== undefined)).size;

  return {
    provider,
    providerVersion,
    platform: status.platform,
    videoDurationSec: durationSec,
    originalWidth,
    originalHeight,
    sampledFrames: frames,
    detections,
    payload,
    detectedObjectCount: payload.observations.length,
    uniqueTrackCount,
    averageConfidence,
  };
}

export function downloadClientPreObservations(payload: ClientPreObservationsPayload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "client_pre_observations.json";
  link.click();
  URL.revokeObjectURL(url);
}
