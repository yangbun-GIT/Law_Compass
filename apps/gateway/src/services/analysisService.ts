import type { FastifyRequest } from "fastify";
import { randomUUID } from "node:crypto";

export type AnalysisRouteOptions = {
  apiPrefix: string;
  db: any;
  redis: any;
  agentUrl: string;
  internalToken: string;
  analyzeTimeoutMs: number;
  retryCount: number;
  errorPayload: (code: string, message: string, traceId: string) => any;
};

export function trace(req: FastifyRequest) {
  return (req.headers["x-correlation-id"] as string) || randomUUID();
}

export function easyReportQuestionCount(report: any) {
  const questions = report?.missing_info?.questions;
  return Array.isArray(questions) ? questions.length : 0;
}

type AnyRecord = Record<string, any>;
const GUIDED_PROGRESS_VERSION = "gateway-guided-progress-v1";

const USER_STAGE_MESSAGES: Record<string, string> = {
  draft: "사고 설명을 정리하고 있습니다.",
  ready: "사고유형을 확인할 준비가 되었습니다.",
  analyzing: "비슷한 KNIA 기준과 과실비율을 확인하고 있습니다.",
  completed: "분석 결과를 정리했습니다.",
  failed: "분석 실패. 다시 시도해 주세요.",
  queued: "대기 중입니다.",
  running: "분석 중입니다.",
  retrying: "잠시 후 다시 확인하고 있습니다.",
  succeeded: "완료되었습니다.",
  ready_for_analysis: "분석 준비가 끝났습니다.",
  uploaded: "영상을 확인하고 있습니다.",
  processing: "사고 장면을 찾고 있습니다.",
};

function isNonEmptyRecord(value: any): value is AnyRecord {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value) && Object.keys(value).length > 0;
}

export function publicStatusLabel(status?: string) {
  return USER_STAGE_MESSAGES[String(status || "")] || "상태를 확인하고 있습니다.";
}

export function publicJobTypeLabel(type?: string) {
  const labels: Record<string, string> = {
    video_preprocess: "영상 확인 중",
    video_analyze: "사고 장면 분석 중",
  };
  return labels[String(type || "")] || "분석 준비 중";
}

function elapsedSeconds(value: any) {
  const timestamp = value ? new Date(value).getTime() : Date.now();
  if (!Number.isFinite(timestamp)) return 0;
  return Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
}

function stagePercent(stepKey: string, basePercent: number, elapsed: number) {
  if (stepKey === "scene") return Math.min(58, basePercent + Math.min(10, Math.floor(elapsed / 6)));
  if (stepKey === "scenario") return Math.min(72, basePercent + Math.min(10, Math.floor(elapsed / 6)));
  if (stepKey === "knia") return Math.min(87, basePercent + Math.min(12, Math.floor(elapsed / 8)));
  if (stepKey === "adjustment") return Math.min(96, basePercent + Math.min(8, Math.floor(elapsed / 8)));
  return basePercent;
}

function estimateRemainingSeconds(stepKey: string, elapsed: number) {
  const targets: Record<string, number> = {
    input: 10,
    upload: 15,
    scene: 45,
    scenario: 40,
    knia: 55,
    adjustment: 25,
    result: 0,
  };
  return Math.max(0, (targets[stepKey] ?? 30) - elapsed);
}

function userStatusNote(stepKey: string, remainingSteps: string[]) {
  if (stepKey === "result") return "결과 화면으로 이동할 수 있습니다.";
  if (stepKey === "knia") return "KNIA 기준과 과실 가감요소를 대조하고 있습니다.";
  if (stepKey === "scene") return "영상에서 사고 장면과 핵심 단서를 확인하고 있습니다.";
  if (remainingSteps.length) return `${remainingSteps.length}개 단계가 남았습니다.`;
  return "결과 화면을 준비하고 있습니다.";
}

export function composeGuidedProgressPayload(
  caseRow: AnyRecord | null | undefined,
  jobs: AnyRecord[] = [],
  options: { resultReady?: boolean } = {}
) {
    const stepDefs = [
        { key: "input", label: "입력 정리", percent: 15, message: "입력한 사고정보를 정리하고 있습니다." },
        { key: "upload", label: "영상 확인", percent: 30, message: "영상 파일을 확인하고 있습니다." },
        { key: "scene", label: "사고 장면 확인", percent: 45, message: "사고 장면을 찾고 있습니다." },
        { key: "scenario", label: "사고유형 판단", percent: 60, message: "어떤 사고유형인지 확인하고 있습니다." },
        { key: "knia", label: "KNIA 과실 기준 검색", percent: 75, message: "비슷한 KNIA 과실 기준을 찾고 있습니다." },
        { key: "adjustment", label: "가감요소 계산", percent: 88, message: "급정거, 제동등, 정차 위치 같은 가감요소를 확인하고 있습니다." },
        { key: "result", label: "결과 정리", percent: 100, message: "결과 화면을 정리했습니다." },
    ];

  const normalizedJobs = jobs.slice(0, 5).map((job) => {
    const status = String(job.status || "").toLowerCase();
    const elapsed = elapsedSeconds(job.created_at ?? job.updated_at);
    return {
      label: publicJobTypeLabel(job.type),
      status_label: publicStatusLabel(status),
      type: String(job.type || ""),
      status,
      elapsed_seconds: elapsed,
      is_active: ["queued", "running", "retrying", "processing", "analyzing"].includes(status),
      is_done: ["completed", "succeeded", "success", "done", "finished"].includes(status),
      is_failed: ["failed", "error", "cancelled", "canceled"].includes(status),
    };
  });

  if (options.resultReady) {
    return {
      version: GUIDED_PROGRESS_VERSION,
        current_stage: "결과 준비 완료",
        current_message: "분석 결과가 준비되었습니다.",
      current_step: "result",
      current_step_index: 6,
      progress_percent: 100,
      result_ready: true,
      can_show_result: true,
      estimated_remaining_seconds: 0,
      status_note: "결과 화면으로 이동할 수 있습니다.",
      steps: stepDefs.map((step) => ({ ...step, status: "done" })),
      remaining_steps: [],
      jobs: normalizedJobs.map(({ type: _type, ...safe }) => safe),
      hide_internal_terms: true,
    };
  }

  const activeJob = normalizedJobs.find((job) => job.is_active);
  const failedJob = normalizedJobs.find((job) => job.is_failed);
  const hasAnyJob = normalizedJobs.length > 0;
  const hasDoneJob = normalizedJobs.some((job) => job.is_done);

  let currentStep = "input";
  let currentIndex = 0;

  if (failedJob) {
    currentStep = "result";
    currentIndex = 6;
  } else if (activeJob?.type === "video_preprocess") {
    currentStep = "scene";
    currentIndex = 2;
  } else if (activeJob?.type === "video_analyze") {
    currentStep = "knia";
    currentIndex = 4;
  } else if (hasDoneJob) {
    currentStep = "adjustment";
    currentIndex = 5;
  } else if (hasAnyJob) {
    currentStep = "upload";
    currentIndex = 1;
  } else if (String(caseRow?.status || "").toLowerCase() === "analyzing") {
    currentStep = "scenario";
    currentIndex = 3;
  }

  const current = stepDefs[currentIndex];
  const currentElapsed = activeJob?.elapsed_seconds ?? 0;
  const remainingSteps = stepDefs.slice(currentIndex + 1).map((step) => step.label);
  const progressPercent = failedJob ? 100 : stagePercent(currentStep, current.percent, currentElapsed);

  return {
    version: GUIDED_PROGRESS_VERSION,
      current_stage: failedJob ? "확인 필요" : current.label,
    current_message: failedJob
        ? "분석 중 문제가 발생했습니다. 다시 시도하거나 고급 진단을 확인해 주세요."
      : current.message,
    current_step: currentStep,
    current_step_index: currentIndex,
    progress_percent: progressPercent,
    result_ready: false,
    can_show_result: false,
    estimated_remaining_seconds: failedJob ? 0 : estimateRemainingSeconds(currentStep, currentElapsed),
    status_note: failedJob ? "다시 시도하거나 고급 진단을 확인해 주세요." : userStatusNote(currentStep, remainingSteps),
    steps: stepDefs.map((step, index) => ({
      ...step,
      status: index < currentIndex ? "done" : index === currentIndex ? "active" : "waiting",
    })),
    remaining_steps: remainingSteps,
    jobs: normalizedJobs.map(({ type: _type, ...safe }) => safe),
    hide_internal_terms: true,
  };
}

export function buildReanalysisVideoMetadata(uploadRow: AnyRecord | null | undefined, bodyVideoMetadata?: AnyRecord | null) {
  if (isNonEmptyRecord(bodyVideoMetadata)) return bodyVideoMetadata;
  if (!uploadRow) return undefined;
  const metadata = isNonEmptyRecord(uploadRow.metadata) ? uploadRow.metadata : {};
  const hasUploadContext = Boolean(uploadRow.file_name || uploadRow.status || uploadRow.preprocess_summary || Object.keys(metadata).length);
  if (!hasUploadContext) return undefined;
  return {
    upload_status: uploadRow.status ?? null,
    file_name: uploadRow.file_name ?? null,
    preprocess_summary: uploadRow.preprocess_summary ?? metadata.preprocess_summary ?? null,
    metadata,
  };
}

export async function buildReportContext(opts: AnalysisRouteOptions, caseId: string, ownerId: string, resultRow: any) {
  const caseRes = await opts.db.query(`SELECT * FROM cases WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`, [caseId, ownerId]);
  const uploadRes = await opts.db.query(
    `SELECT * FROM uploads WHERE case_id=$1 AND owner_user_id=$2 AND deleted_at IS NULL ORDER BY updated_at DESC LIMIT 1`,
    [caseId, ownerId]
  );
  const jobsRes = await opts.db.query(
    `SELECT id,type,status,attempts AS attempt,max_attempts,last_error,error_info,created_at,updated_at
     FROM jobs WHERE case_id=$1 AND owner_user_id=$2 ORDER BY created_at DESC LIMIT 10`,
    [caseId, ownerId]
  );
  return {
    case: caseRes.rows[0] ?? null,
    upload: uploadRes.rows[0] ?? null,
    jobs: jobsRes.rows,
    resultRow,
  };
}

export async function insertAnalysisResult(
  opts: AnalysisRouteOptions,
  caseId: string,
  ownerId: string,
  sourceType: "text",
  agentResp: any,
  reportPayload: any,
  elderlyFriendlyReport: any,
  nextVersion: number
) {
  const inserted = await opts.db.query(
    `INSERT INTO analysis_results(
       case_id, owner_user_id, version, source_type, result, evidence, uncertainty, model_info,
       structured_facts, recommended_keywords, suggested_next_inputs, report_payload, elderly_friendly_report,
       legal_analysis, scenario_type, used_evidence_ids, legal_risk_flags, persona_outputs, evidence_audit
     )
     VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19) RETURNING id, version`,
    [
      caseId,
      ownerId,
      nextVersion,
      sourceType,
      JSON.stringify(agentResp),
      JSON.stringify(agentResp.evidence ?? []),
      JSON.stringify(agentResp.uncertainty ?? {}),
      JSON.stringify(agentResp.model_info ?? {}),
      JSON.stringify(agentResp.structured_facts ?? {}),
      JSON.stringify(agentResp.recommended_keywords ?? []),
      JSON.stringify(agentResp.suggested_next_inputs ?? []),
      JSON.stringify(reportPayload),
      JSON.stringify(elderlyFriendlyReport),
      JSON.stringify(agentResp.legal_analysis ?? {}),
      agentResp.scenario_type ?? null,
      JSON.stringify((agentResp.evidence ?? []).map((x: any) => x.chunk_id).filter(Boolean)),
      JSON.stringify(agentResp.legal_liability?.risk_flags ?? agentResp.legal_analysis?.risk_flags ?? []),
      JSON.stringify({ analysts: agentResp.recommended_specialists ?? [] }),
      JSON.stringify(agentResp.evidence_audit ?? {})
    ]
  );
  await opts.db.query(
    `UPDATE analysis_results SET knia_matches=$2, knia_primary_match=$3 WHERE id=$1`,
    [inserted.rows[0].id, JSON.stringify(agentResp.knia_matches ?? []), JSON.stringify(agentResp.knia_primary_match ?? null)]
  ).catch(() => undefined);
  return inserted.rows[0];
}
