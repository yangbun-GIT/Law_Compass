import type { MlKitDetection, MlKitFrameInput, MlKitPluginStatus } from "../types/mlkit";

type CapacitorLike = {
  getPlatform?: () => string;
  Plugins?: Record<string, any>;
};

declare global {
  interface Window {
    Capacitor?: CapacitorLike;
  }
}

const PLUGIN_NAME = "MlKitObjectDetector";

export class MlKitNativeUnavailableError extends Error {
  constructor(message = "native plugin unavailable") {
    super(message);
    this.name = "MlKitNativeUnavailableError";
  }
}

function capacitor() {
  return typeof window !== "undefined" ? window.Capacitor : undefined;
}

export function getMlKitPluginStatus(): MlKitPluginStatus {
  const cap = capacitor();
  const platform = (cap?.getPlatform?.() || "web") as MlKitPluginStatus["platform"];
  const plugin = cap?.Plugins?.[PLUGIN_NAME];
  const available = Boolean(plugin?.detectObjects);

  return {
    available,
    provider: available ? "google_mlkit" : "mock_mlkit_web_fallback",
    providerVersion: available ? "native-capacitor-mlkit-object-detection" : "web-noop",
    platform,
    reason: available ? undefined : "Capacitor native ML Kit plugin is not available in this runtime.",
  };
}

export async function detectObjectsWithMlKit(input: MlKitFrameInput): Promise<MlKitDetection> {
  const plugin = capacitor()?.Plugins?.[PLUGIN_NAME];
  if (!plugin?.detectObjects) {
    throw new MlKitNativeUnavailableError();
  }

  const response = await plugin.detectObjects({
    frameIndex: input.frameIndex,
    frameTimeSec: input.frameTimeSec,
    imageDataUrl: input.imageDataUrl,
    width: input.width,
    height: input.height,
    confidenceThreshold: input.confidenceThreshold,
    enableTracking: input.enableTracking,
  });

  return {
    frameIndex: Number(response?.frameIndex ?? input.frameIndex),
    frameTimeSec: Number(response?.frameTimeSec ?? input.frameTimeSec),
    processingMs: Number(response?.processingMs ?? 0),
    width: Number(response?.width ?? input.width),
    height: Number(response?.height ?? input.height),
    objects: Array.isArray(response?.objects) ? response.objects : [],
  };
}

