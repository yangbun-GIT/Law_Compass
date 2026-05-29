export type ClientPreObservation = {
  field: "object_candidate";
  value: string;
  confidence: number;
  frame_time_sec: number;
  bbox: [number, number, number, number];
  bbox_pixels?: [number, number, number, number];
  track_id?: number | string | null;
  metadata: {
    label: string;
    raw_category: string;
    frame_index: number;
    provider?: string;
  };
};

export type ClientPreObservationsPayload = {
  source: "client_pre_observation";
  provider: "google_mlkit" | "mock_mlkit_web_fallback";
  provider_version: string;
  video_id: string;
  created_at: string;
  device: {
    platform: "android" | "ios" | "web" | "unknown";
    model?: string;
    os_version?: string;
  };
  performance: {
    sampled_frame_count: number;
    processed_frame_count: number;
    failed_frame_count: number;
    total_processing_ms: number;
    avg_processing_ms_per_frame: number;
  };
  observations: ClientPreObservation[];
  warnings: string[];
};

export const FORBIDDEN_CLIENT_OBSERVATION_FIELDS = new Set([
  "fault_ratio",
  "accident_party_type",
  "collision_partner_type",
  "signal_violation",
  "knia_chart_no",
  "legal_judgment",
]);

export function findForbiddenClientObservationFields(value: unknown, path = "$"): string[] {
  if (!value || typeof value !== "object") return [];
  if (Array.isArray(value)) {
    return value.flatMap((item, index) => findForbiddenClientObservationFields(item, `${path}[${index}]`));
  }

  const found: string[] = [];
  for (const [key, nested] of Object.entries(value as Record<string, unknown>)) {
    const nextPath = `${path}.${key}`;
    if (FORBIDDEN_CLIENT_OBSERVATION_FIELDS.has(key)) {
      found.push(nextPath);
    }
    found.push(...findForbiddenClientObservationFields(nested, nextPath));
  }
  return found;
}

