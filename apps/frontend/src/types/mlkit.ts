export type MlKitFrameInput = {
  frameIndex: number;
  frameTimeSec: number;
  imageDataUrl: string;
  width: number;
  height: number;
  confidenceThreshold: number;
  enableTracking: boolean;
};

export type MlKitBoundingBox = {
  left: number;
  top: number;
  right: number;
  bottom: number;
  width: number;
  height: number;
};

export type MlKitObjectLabel = {
  text: string;
  confidence: number;
  index?: number;
};

export type MlKitDetectedObject = {
  trackingId?: number | string | null;
  labels?: MlKitObjectLabel[];
  boundingBox: MlKitBoundingBox;
};

export type MlKitDetection = {
  frameIndex: number;
  frameTimeSec: number;
  processingMs: number;
  width?: number;
  height?: number;
  objects: MlKitDetectedObject[];
};

export type MlKitPluginStatus = {
  available: boolean;
  provider: string;
  providerVersion?: string;
  platform: "android" | "ios" | "web" | "unknown";
  reason?: string;
};

