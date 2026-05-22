type AnyRecord = Record<string, any>;

const DIAGNOSTIC_VERSION = "agent-trace-diagnostic-v1";
const SENSITIVE_KEY_PATTERN = /(password|secret|token|authorization|cookie|api[_-]?key|email|raw[_-]?text|user[_-]?text|description|prompt|message|chunk[_-]?id|document[_-]?id|source[_-]?uri|snippet|plain[_-]?summary)/i;

function asArray(value: any): any[] {
  return Array.isArray(value) ? value : [];
}

function asRecord(value: any): AnyRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function toNumber(value: any, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function safeString(value: any) {
  const text = String(value ?? "").replace(/\s+/g, " ").trim();
  if (!text) return undefined;
  return text.length > 160 ? `${text.slice(0, 157)}...` : text;
}

function safeValue(key: string, value: any, depth = 0): any {
  if (SENSITIVE_KEY_PATTERN.test(key)) return undefined;
  if (value === null || value === undefined) return undefined;
  if (typeof value === "boolean" || typeof value === "number") return value;
  if (typeof value === "string") return safeString(value);
  if (Array.isArray(value)) {
    if (depth > 1) return { count: value.length };
    const primitive = value.every((item) => item === null || ["string", "number", "boolean"].includes(typeof item));
    if (primitive) return value.map((item) => safeValue(key, item, depth + 1)).filter((item) => item !== undefined).slice(0, 12);
    return { count: value.length };
  }
  if (typeof value === "object") {
    if (depth > 1) return { key_count: Object.keys(value).length };
    const out: AnyRecord = {};
    for (const [childKey, childValue] of Object.entries(value)) {
      const next = safeValue(childKey, childValue, depth + 1);
      if (next !== undefined) out[childKey] = next;
    }
    return out;
  }
  return undefined;
}

function safePacket(packet: AnyRecord = {}) {
  const out: AnyRecord = {};
  for (const [key, value] of Object.entries(packet)) {
    const safe = safeValue(key, value);
    if (safe !== undefined) out[key] = safe;
  }
  return out;
}

function safeTraceSteps(trace: AnyRecord = {}) {
  return asArray(trace.steps).map((step: AnyRecord) => ({
    id: safeString(step.id) ?? "unknown",
    phase: safeString(step.phase) ?? "unknown",
    status: safeString(step.status) ?? "unknown",
    packet_summary: safePacket(asRecord(step.packet)),
  })).slice(0, 16);
}

function safeFieldList(values: any) {
  return asArray(values)
    .map((value) => safeString(value))
    .filter(Boolean)
    .slice(0, 16);
}

function summarizeConflicts(conflicts: any) {
  return asArray(conflicts).map((item: AnyRecord) => ({
    field: safeString(item.field) ?? "unknown",
    winner: safeString(item.winner ?? item.selected_source) ?? "unknown",
    video_confidence: item.video_confidence ?? item.confidence ?? null,
    frame_ref_count: asArray(item.frame_refs).length,
  })).slice(0, 12);
}

function countByStatus(steps: AnyRecord[]) {
  return steps.reduce((acc: AnyRecord, step) => {
    const status = String(step.status ?? "unknown");
    acc[status] = toNumber(acc[status]) + 1;
    return acc;
  }, {});
}

export function composeAgentTraceDiagnostic(row: AnyRecord = {}) {
  const result = asRecord(row.result);
  const modelInfo = asRecord(row.model_info);
  const trace = asRecord(result.agent_trace ?? modelInfo.agent_trace);
  const reflection = asRecord(result.reflection_loop ?? modelInfo.reflection_loop);
  const videoContract = asRecord(result.video_input_contract ?? modelInfo.video_input_contract);
  const arbitration = asRecord(result.fact_arbitration ?? modelInfo.fact_arbitration);
  const evidenceAudit = asRecord(result.evidence_audit ?? row.evidence_audit);
  const coverage = asRecord(evidenceAudit.scenario_evidence_coverage);
  const judgment = asRecord(result.agent_judgment);
  const presentation = asRecord(result.presentation_policy);
  const steps = safeTraceSteps(trace);

  return {
    diagnostic_version: DIAGNOSTIC_VERSION,
    result: {
      id: row.id,
      case_id: row.case_id,
      version: row.version,
      source_type: row.source_type,
      created_at: row.created_at,
    },
    pipeline: {
      trace_version: trace.version ?? "unknown",
      trace_policy: trace.trace_policy ?? "safe_metadata_only_no_raw_user_text",
      overall_status: trace.overall_status ?? judgment.overall_status ?? "unknown",
      step_count: toNumber(trace.step_count, steps.length),
      status_counts: countByStatus(steps),
      steps,
    },
    judgment: {
      overall_status: judgment.overall_status ?? "unknown",
      must_not_present_as_final: Boolean(judgment.must_not_present_as_final),
      blocker_count: asArray(judgment.decision_blockers ?? judgment.blocking_reasons).length,
      stage_statuses: asArray(judgment.stage_statuses).map((stage: AnyRecord) => ({
        name: safeString(stage.name) ?? "unknown",
        status: safeString(stage.status) ?? "unknown",
      })).slice(0, 16),
    },
    reflection: {
      status: reflection.status ?? "unknown",
      next_action: reflection.next_action ?? "unknown",
      requery_attempted: Boolean(reflection.requery_attempted),
      requery_added_evidence_count: toNumber(reflection.requery_added_evidence_count),
      iterations_used: toNumber(reflection.iterations_used),
      missing_requirement_count: asArray(reflection.final_missing_requirements).length,
    },
    video_input: {
      contract_version: videoContract.version ?? "unknown",
      accepted_observation_count: asArray(videoContract.accepted_observations).length,
      uncertain_observation_count: asArray(videoContract.uncertain_observations).length,
      ignored_observation_count: asArray(videoContract.ignored_observations).length,
      promoted_fields: safeFieldList(Object.keys(asRecord(videoContract.fact_patch))),
    },
    fact_arbitration: {
      contract_version: arbitration.version ?? "unknown",
      applied_video_fields: safeFieldList(arbitration.applied_video_fields),
      kept_user_fields: safeFieldList(arbitration.kept_user_fields),
      conflict_count: asArray(arbitration.conflicts).length,
      conflicts: summarizeConflicts(arbitration.conflicts),
      confirmation_count: asArray(arbitration.requires_confirmation).length,
    },
    evidence: {
      coverage_level: coverage.coverage_level ?? "unknown",
      decision_ready: coverage.decision_ready ?? null,
      scenario_relevant_count: toNumber(coverage.scenario_relevant_count),
      missing_requirement_count: asArray(coverage.missing_requirements).length,
      family_counts: safePacket(asRecord(coverage.evidence_family_counts)),
    },
    presentation: {
      finality: presentation.finality ?? "unknown",
      user_reference_allowed: presentation.user_reference_allowed ?? null,
      restricted_section_count: asArray(presentation.restricted_sections).length,
    },
  };
}
