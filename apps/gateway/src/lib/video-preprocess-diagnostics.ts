type AnyRecord = Record<string, any>;

const DIAGNOSTIC_VERSION = "video-preprocess-diagnostic-v1";
const OBSERVATION_LIMIT = 80;
const FRAME_REF_LIMIT = 12;

function asRecord(value: any): AnyRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function asArray(value: any): any[] {
  return Array.isArray(value) ? value : [];
}

function toNumber(value: any, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function safeString(value: any, maxLength = 240) {
  const text = String(value ?? "").replace(/\s+/g, " ").trim();
  if (!text) return null;
  return text.length > maxLength ? `${text.slice(0, maxLength - 3)}...` : text;
}

function basename(value: any) {
  const text = safeString(value, 260);
  if (!text) return null;
  const normalized = text.replace(/\\/g, "/");
  return normalized.split("/").filter(Boolean).at(-1) ?? text;
}

function countBy(items: any[], field: string) {
  return items.reduce((acc: AnyRecord, item) => {
    const key = safeString(asRecord(item)[field], 80) ?? "unknown";
    acc[key] = toNumber(acc[key]) + 1;
    return acc;
  }, {});
}

function compactObservation(item: any) {
  const source = safeString(item?.source, 120);
  return {
    field: safeString(item?.field, 120) ?? "unknown",
    value: item?.value,
    confidence: item?.confidence ?? null,
    source,
    source_family: source?.includes("yolo")
      ? "YOLO"
      : source?.includes("openai") || source?.includes("frame_analysis")
        ? "OpenAI frame"
        : "merged",
    frame_refs: asArray(item?.frame_refs).map(basename).filter(Boolean).slice(0, FRAME_REF_LIMIT),
    frame_ref_count: asArray(item?.frame_refs).length,
    reason: safeString(item?.reason, 260),
  };
}

function valueKey(value: any) {
  if (value === null || value === undefined) return "unknown";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function isAffirmative(value: any) {
  const key = valueKey(value).toLowerCase();
  return key === "true" || key === "yes" || key === "present" || key === "visible";
}

function isNegative(value: any) {
  const key = valueKey(value).toLowerCase();
  return key === "false" || key === "no" || key === "absent" || key === "not_visible";
}

function maxConfidence(items: any[]) {
  const values = items.map((item) => Number(item.confidence)).filter(Number.isFinite);
  if (!values.length) return null;
  return Math.max(...values);
}

function sumFrameRefs(items: any[]) {
  return items.reduce((acc, item) => acc + toNumber(item.frame_ref_count), 0);
}

function uniqueStrings(items: Array<string | null | undefined>) {
  return Array.from(new Set(items.filter(Boolean) as string[]));
}

function candidateLabel(value: any) {
  const labels: AnyRecord = {
    vehicle: "차량",
    vehicle_candidate: "차량 후보",
    pedestrian: "보행자",
    pedestrian_candidate: "보행자 후보",
    bicycle: "자전거",
    bicycle_candidate: "자전거 후보",
    motorcycle: "이륜차",
    motorcycle_candidate: "이륜차 후보",
    object: "물체",
    object_candidate: "물체 후보",
  };
  return labels[valueKey(value)] ?? valueKey(value);
}

function defaultDisplayValue(field: string, value: any) {
  if (typeof value === "boolean") return value ? "예" : "아니오";
  if (field === "primary_collision_target" || field === "direct_collision_partner_type") {
    return `${candidateLabel(value)}입니다. 확정 사실이 아니라 Agent 판단 전 확인 후보입니다.`;
  }
  return valueKey(value);
}

function makeHumanObservation(params: {
  field: string;
  value: any;
  displayLabel?: string;
  displayValue: string;
  status: string;
  statusLabel: string;
  items: any[];
  reason?: string | null;
}) {
  return {
    field: params.field,
    value: params.value,
    display_label: params.displayLabel ?? params.field,
    display_value: params.displayValue,
    status: params.status,
    status_label: params.statusLabel,
    confidence: maxConfidence(params.items),
    source_families: uniqueStrings(params.items.map((item) => item.source_family)),
    frame_ref_count: sumFrameRefs(params.items),
    evidence_count: params.items.length,
    reason: params.reason ?? null,
  };
}

function groupHumanObservations(observations: any[]) {
  const compacted = observations.map(compactObservation);
  const groups = new Map<string, any[]>();
  for (const item of compacted) {
    const current = groups.get(item.field) ?? [];
    current.push(item);
    groups.set(item.field, current);
  }

  const rows: any[] = [];
  for (const [field, items] of groups.entries()) {
    const valueKeys = uniqueStrings(items.map((item) => valueKey(item.value)));
    const strongest = items.reduce((best, item) => {
      const bestConfidence = Number(best?.confidence ?? -1);
      const itemConfidence = Number(item.confidence ?? -1);
      return itemConfidence > bestConfidence ? item : best;
    }, items[0]);

    if (field === "pedestrian_visible") {
      const hasYes = items.some((item) => isAffirmative(item.value));
      const hasNo = items.some((item) => isNegative(item.value));
      if (hasYes && hasNo) {
        rows.push(makeHumanObservation({
          field: "pedestrian_context",
          value: "object_candidate_not_collision_target",
          displayLabel: "보행자 관련 관찰",
          displayValue:
            "충돌 경로의 보행자는 확인되지 않았고, 화면 안의 사람 객체 후보만 감지됐습니다. 보행자 사고로 확정하지 말고 주변 환경 후보로만 봐야 합니다.",
          status: "conflict",
          statusLabel: "확인 필요",
          items,
          reason: "OpenAI의 충돌 경로 관찰과 YOLO의 객체 재고 관찰은 의미가 다르므로 하나의 확정 사실로 합치지 않습니다.",
        }));
      } else if (hasYes) {
        rows.push(makeHumanObservation({
          field,
          value: true,
          displayLabel: "보행자 관련 관찰",
          displayValue: "화면 안에 보행자 후보가 보입니다. 직접 충돌 대상인지는 별도 확인이 필요합니다.",
          status: "candidate",
          statusLabel: "후보",
          items,
        }));
      } else {
        rows.push(makeHumanObservation({
          field,
          value: false,
          displayLabel: "보행자 관련 관찰",
          displayValue: "충돌 경로 또는 사고 직후 주변에서 보행자는 확인되지 않았습니다.",
          status: "confirmed",
          statusLabel: "확인",
          items,
        }));
      }
      continue;
    }

    if (field === "primary_collision_target") {
      const candidateValues = uniqueStrings(items.map((item) => valueKey(item.value)));
      rows.push(makeHumanObservation({
        field,
        value: candidateValues,
        displayLabel: "주 충돌 대상 후보",
        displayValue:
          candidateValues.length > 1
            ? `여러 사고 대상 후보가 함께 감지됐습니다: ${candidateValues.map(candidateLabel).join(", ")}. 직접 충돌 대상은 Agent 판단 전 확인이 필요합니다.`
            : `${candidateLabel(candidateValues[0])}가 주 충돌 대상 후보입니다. 확정 사실이 아니라 Agent 판단 전 확인 후보입니다.`,
        status: candidateValues.length > 1 ? "conflict" : "candidate",
        statusLabel: candidateValues.length > 1 ? "확인 필요" : "후보",
        items,
      }));
      continue;
    }

    if (valueKeys.length > 1) {
      rows.push(makeHumanObservation({
        field,
        value: valueKeys,
        displayValue: `출처별 관찰값이 다릅니다: ${valueKeys.join(", ")}. Agent 판단 전 확인이 필요합니다.`,
        status: "conflict",
        statusLabel: "확인 필요",
        items,
      }));
      continue;
    }

    rows.push(makeHumanObservation({
      field,
      value: strongest.value,
      displayValue: defaultDisplayValue(field, strongest.value),
      status: field.endsWith("_candidate") || field === "accident_event_candidate" ? "candidate" : "confirmed",
      statusLabel: field.endsWith("_candidate") || field === "accident_event_candidate" ? "후보" : "확인",
      items,
      reason: strongest.reason,
    }));
  }

  const priority: AnyRecord = {
    conflict: 0,
    candidate: 1,
    confirmed: 2,
  };
  return rows.sort((a, b) => {
    const priorityDiff = toNumber(priority[a.status], 9) - toNumber(priority[b.status], 9);
    if (priorityDiff) return priorityDiff;
    return String(a.display_label).localeCompare(String(b.display_label), "ko");
  }).slice(0, OBSERVATION_LIMIT);
}

function compactAnalysisPayload(payload: any) {
  const data = asRecord(payload);
  const observations = asArray(data.observations);
  const attempts = asArray(data.analysis_attempts);
  const summary = asRecord(data.summary);
  return {
    enabled: Boolean(data.enabled),
    provider: safeString(data.provider, 80),
    model: basename(data.model ?? data.detector ?? data.model_path ?? data.modelPath),
    detail: safeString(data.detail, 80),
    frame_selection_strategy: safeString(data.frame_selection_strategy, 120),
    available_frame_count: data.available_frame_count ?? null,
    selected_frame_count: data.selected_frame_count ?? null,
    analyzed_frame_count: data.analyzed_frame_count ?? null,
    observation_count: observations.length,
    observation_fields: countBy(observations, "field"),
    observations: observations.map(compactObservation).slice(0, OBSERVATION_LIMIT),
    attempt_count: attempts.length,
    zero_observation_retry_used: data.zero_observation_retry_used ?? null,
    has_error: Boolean(data.error || data.has_error),
    error: safeString(data.error ?? data.zero_observation_retry_error, 240),
    summary: Object.keys(summary).length ? summary : null,
  };
}

function compactFrameSelection(metadata: AnyRecord) {
  const frameDetails = asArray(metadata.representative_frame_details);
  const selectionSummary = asRecord(metadata.frame_selection_summary);
  return {
    representative_frame_count: asArray(metadata.representative_frames).length || frameDetails.length,
    event_candidate_count: frameDetails.filter((item) => Boolean(asRecord(item).is_event_candidate)).length,
    pre_event_count: frameDetails.filter((item) => String(asRecord(item).event_phase) === "pre").length,
    event_count: frameDetails.filter((item) => String(asRecord(item).event_phase) === "event").length,
    post_event_count: frameDetails.filter((item) => String(asRecord(item).event_phase) === "post").length,
    selection_summary: Object.keys(selectionSummary).length ? selectionSummary : null,
  };
}

export function composeVideoPreprocessDiagnostic(upload: AnyRecord = {}) {
  const metadata = asRecord(upload.metadata);
  const mergedObservations = asArray(metadata.observations);
  const humanObservations = groupHumanObservations(mergedObservations);
  const openai = compactAnalysisPayload(metadata.openai_frame_analysis);
  const yolo = compactAnalysisPayload(metadata.yolo_frame_analysis);

  return {
    diagnostic_version: DIAGNOSTIC_VERSION,
    upload: {
      id: upload.id,
      case_id: upload.case_id,
      file_name: safeString(upload.file_name ?? metadata.original_filename, 180),
      status: safeString(upload.status, 80),
      content_type: safeString(upload.content_type ?? metadata.mime_type, 80),
      file_size_bytes: upload.file_size_bytes ?? metadata.size_bytes ?? null,
      preprocess_summary: safeString(upload.preprocess_summary ?? metadata.preprocess_summary, 360),
      created_at: upload.created_at,
      updated_at: upload.updated_at,
    },
    video_metadata: {
      duration_sec: metadata.duration_sec ?? null,
      width: metadata.width ?? null,
      height: metadata.height ?? null,
      fps: metadata.fps ?? null,
      codec: safeString(metadata.codec, 80),
    },
    frame_selection: compactFrameSelection(metadata),
    openai_frame_analysis: openai,
    yolo_frame_analysis: yolo,
    merged_observations: {
      observation_count: mergedObservations.length,
      observation_fields: countBy(mergedObservations, "field"),
      source_families: countBy(mergedObservations.map(compactObservation), "source_family"),
      human_observation_count: humanObservations.length,
      human_observations: humanObservations,
      observations: mergedObservations.map(compactObservation).slice(0, OBSERVATION_LIMIT),
    },
  };
}
