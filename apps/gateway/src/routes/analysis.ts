import type { FastifyInstance } from "fastify";
import { callInternalAgent } from "../lib/internal-client.js";
import { selectVideoAiRoute } from "../lib/ai-router.js";
import { normalizeFollowupAnswers } from "../lib/followup-normalizer.js";
import {
  composeClientReport,
  composeDebugReport,
  composeEasyFallback,
  composeReanalysisChangeCard,
  enrichEasyReport,
  sanitizeEasyReport
} from "../lib/report-composer.js";
import { maskSensitive } from "../lib/security.js";
import { requireUser } from "../lib/request-guards.js";
import {
  buildReanalysisVideoMetadata,
  buildReportContext,
  composeGuidedProgressPayload,
  easyReportQuestionCount,
  insertAnalysisResult,
  trace,
  type AnalysisRouteOptions,
} from "../services/analysisService.js";

export {
  buildReanalysisVideoMetadata,
  composeGuidedProgressPayload,
  publicJobTypeLabel,
  publicStatusLabel,
} from "../services/analysisService.js";

export function registerAnalysisRoutes(app: FastifyInstance, opts: AnalysisRouteOptions) {
  app.post(`${opts.apiPrefix}/cases/:caseId/analyze-text`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const { caseId } = req.params as any;
    const body = req.body as any;

    const caseRow = await opts.db.query(`SELECT * FROM cases WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`, [caseId, (req as any).user.id]);
    if (!caseRow.rowCount) return reply.code(404).send(opts.errorPayload("CASE_NOT_FOUND", "케이스를 찾을 수 없습니다.", traceId));

    let agentResp;
    try {
      agentResp = await callInternalAgent("/internal/v1/analyze/text", {
        case_id: caseId,
        user_id: (req as any).user.id,
        description_text: maskSensitive(body?.description_text ?? caseRow.rows[0].description_text ?? ""),
        structured_facts: body?.structured_facts ?? caseRow.rows[0].structured_facts ?? {},
        selected_keywords: body?.selected_keywords ?? caseRow.rows[0].selected_keywords ?? [],
        analysis_mode: body?.analysis_mode ?? caseRow.rows[0].analysis_mode ?? "quick_summary",
        ai_profile: body?.ai_profile,
        specialist_roles: body?.specialist_roles
      }, traceId, { baseUrl: opts.agentUrl, internalToken: opts.internalToken, timeoutMs: opts.analyzeTimeoutMs, retryCount: opts.retryCount });
    } catch {
      return reply.code(502).send(opts.errorPayload("AI_TEMPORARY_UNAVAILABLE", "AI 분석 서비스가 일시적으로 불안정합니다. 잠시 후 재시도해 주세요.", traceId));
    }

    const ver = await opts.db.query(`SELECT COALESCE(MAX(version),0)+1 AS v FROM analysis_results WHERE case_id=$1`, [caseId]);
    const nextVersion = Number(ver.rows[0].v);
    const reportPayload = composeClientReport(agentResp, { case: caseRow.rows[0] });
    const inserted = await insertAnalysisResult(
      opts,
      caseId,
      (req as any).user.id,
      "text",
      agentResp,
      reportPayload,
      agentResp.elderly_friendly_report ?? {},
      nextVersion
    );
    await opts.db.query(`UPDATE cases SET status='completed', latest_result_id=$2 WHERE id=$1`, [caseId, inserted.id]);
    const easyReport = enrichEasyReport(sanitizeEasyReport(agentResp.elderly_friendly_report ?? composeEasyFallback(agentResp, { case: caseRow.rows[0] })), agentResp);

    return {
      result_id: inserted.id,
      version: nextVersion,
      result: easyReport,
      report: easyReport,
      trace_id: traceId
    };
  });

  app.post(`${opts.apiPrefix}/cases/:caseId/analyze-video`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const { caseId } = req.params as any;
    const body = req.body as any;
    const caseRow = await opts.db.query(`SELECT id,title,description_text FROM cases WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`, [caseId, (req as any).user.id]);
    if (!caseRow.rowCount) return reply.code(404).send(opts.errorPayload("CASE_NOT_FOUND", "케이스를 찾을 수 없습니다.", traceId));
    const uploadRow = await opts.db.query(`SELECT id FROM uploads WHERE id=$1 AND case_id=$2 AND owner_user_id=$3 AND deleted_at IS NULL`, [body.upload_id, caseId, (req as any).user.id]);
    if (!uploadRow.rowCount) return reply.code(404).send(opts.errorPayload("UPLOAD_NOT_FOUND", "업로드를 찾을 수 없습니다.", traceId));
    const uploadFull = await opts.db.query(`SELECT file_name, metadata FROM uploads WHERE id=$1`, [body.upload_id]);
    const route = selectVideoAiRoute({
      caseTitle: caseRow.rows[0].title ?? "",
      caseDescription: `${caseRow.rows[0].description_text ?? ""} ${JSON.stringify(body.structured_facts ?? {})} ${(body.selected_keywords ?? []).join(" ")}`,
      fileName: uploadFull.rows[0]?.file_name ?? "",
      uploadMetadata: uploadFull.rows[0]?.metadata ?? {}
    });
    const job = await opts.db.query(
      `INSERT INTO jobs(case_id, upload_id, owner_user_id, type, status, payload)
       VALUES($1,$2,$3,'video_analyze','queued',$4) RETURNING id`,
      [caseId, body.upload_id, (req as any).user.id, JSON.stringify({
        case_id: caseId,
        upload_id: body.upload_id,
        ai_profile: route.aiProfile,
        specialist_roles: route.specialistRoles,
        routing_reason: route.reason,
        video_metadata: body.video_metadata ?? {},
        structured_facts: body.structured_facts ?? {},
        selected_keywords: body.selected_keywords ?? [],
        analysis_mode: body.analysis_mode ?? "quick_summary"
      })]
    );
    await opts.redis.xadd(process.env.REDIS_STREAM_KEY ?? "jobs:v1:stream", "MAXLEN", "~", "10000", "*", "job_id", job.rows[0].id, "job_type", "video_analyze");
    return { job_id: job.rows[0].id, status: "queued", ai_profile: route.aiProfile, specialist_roles: route.specialistRoles, trace_id: traceId };
  });

  app.get(`${opts.apiPrefix}/cases/:caseId/jobs`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const { caseId } = req.params as any;
    const rows = await opts.db.query(
      `SELECT id,type,status,attempts,attempt,max_attempts,last_error,error_info,artifacts,created_at,updated_at
       FROM jobs WHERE case_id=$1 AND owner_user_id=$2 ORDER BY created_at DESC LIMIT 50`,
      [caseId, (req as any).user.id]
    );
    return { items: rows.rows, trace_id: traceId };
  });

  app.get(`${opts.apiPrefix}/cases/:caseId/analysis-progress`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const { caseId } = req.params as any;
    const caseRow = await opts.db.query(
      `SELECT id,status FROM cases WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`,
      [caseId, (req as any).user.id]
    );
    if (!caseRow.rowCount) return reply.code(404).send(opts.errorPayload("CASE_NOT_FOUND", "케이스를 찾을 수 없습니다.", traceId));
    const jobs = await opts.db.query(
      `SELECT type,status,created_at,updated_at
       FROM jobs WHERE case_id=$1 AND owner_user_id=$2 ORDER BY created_at DESC LIMIT 5`,
      [caseId, (req as any).user.id]
    );
    const latestResult = await opts.db.query(
      `SELECT id FROM analysis_results
         WHERE case_id=$1 AND owner_user_id=$2
         ORDER BY version DESC LIMIT 1`,
      [caseId, (req as any).user.id]
    );
    return {
      ...composeGuidedProgressPayload(caseRow.rows[0], jobs.rows, {
        resultReady: latestResult.rowCount > 0,
      }),
      trace_id: traceId
    };
  });

  app.get(`${opts.apiPrefix}/cases/:caseId/result`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const { caseId } = req.params as any;
    const row = await opts.db.query(`SELECT * FROM analysis_results WHERE case_id=$1 AND owner_user_id=$2 ORDER BY version DESC LIMIT 1`, [caseId, (req as any).user.id]);
    if (!row.rowCount) return reply.code(404).send(opts.errorPayload("RESULT_NOT_FOUND", "분석 결과가 없습니다.", traceId));
    const context = await buildReportContext(opts, caseId, (req as any).user.id, row.rows[0]);
    const debug = String((req.query as any)?.debug ?? "") === "1";
    const easyReport = enrichEasyReport(sanitizeEasyReport(row.rows[0].elderly_friendly_report && Object.keys(row.rows[0].elderly_friendly_report).length ? row.rows[0].elderly_friendly_report : composeEasyFallback(row.rows[0].result, context)), row.rows[0].result);
    return debug
      ? { result: easyReport, report: easyReport, debug: composeDebugReport(row.rows[0].result, context), trace_id: traceId }
      : { result: easyReport, report: easyReport, trace_id: traceId };
  });

  app.get(`${opts.apiPrefix}/cases/:caseId/report`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const { caseId } = req.params as any;
    const row = await opts.db.query(`SELECT * FROM analysis_results WHERE case_id=$1 AND owner_user_id=$2 ORDER BY version DESC LIMIT 1`, [caseId, (req as any).user.id]);
    if (!row.rowCount) return reply.code(404).send(opts.errorPayload("RESULT_NOT_FOUND", "분석 결과가 없습니다.", traceId));
    const context = await buildReportContext(opts, caseId, (req as any).user.id, row.rows[0]);
    const debug = String((req.query as any)?.debug ?? "") === "1";
    const report = enrichEasyReport(sanitizeEasyReport(row.rows[0].elderly_friendly_report && Object.keys(row.rows[0].elderly_friendly_report).length ? row.rows[0].elderly_friendly_report : composeClientReport(row.rows[0].result, context)), row.rows[0].result);
    await opts.db.query(`UPDATE analysis_results SET report_payload=$2 WHERE id=$1`, [row.rows[0].id, JSON.stringify(report)]).catch(() => undefined);
    return debug ? { report, debug: composeDebugReport(row.rows[0].result, context), trace_id: traceId } : { report, trace_id: traceId };
  });

  app.get(`${opts.apiPrefix}/cases/:caseId/easy-report`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const { caseId } = req.params as any;
    const caseRow = await opts.db.query(
      `SELECT id FROM cases WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`,
      [caseId, (req as any).user.id]
    );
    if (!caseRow.rowCount) return reply.code(404).send(opts.errorPayload("CASE_NOT_FOUND", "케이스를 찾을 수 없습니다.", traceId));
    const row = await opts.db.query(
      `SELECT * FROM analysis_results WHERE case_id=$1 AND owner_user_id=$2 ORDER BY version DESC LIMIT 1`,
      [caseId, (req as any).user.id]
    );
    if (!row.rowCount) return { status: "not_ready", message: "아직 분석 결과가 없습니다.", report: null, trace_id: traceId };
    const result = row.rows[0].result ?? {};
    const stored = row.rows[0].elderly_friendly_report;
    const easyReport = enrichEasyReport(sanitizeEasyReport(
      stored && Object.keys(stored).length
        ? stored
        : result.elderly_friendly_report && Object.keys(result.elderly_friendly_report).length
          ? result.elderly_friendly_report
          : composeEasyFallback(result, await buildReportContext(opts, caseId, (req as any).user.id, row.rows[0]))
    ), result);
    await opts.db.query(`UPDATE analysis_results SET elderly_friendly_report=$2 WHERE id=$1`, [row.rows[0].id, JSON.stringify(easyReport)]).catch(() => undefined);
    if (String((req.query as any)?.debug ?? "") === "1") {
      const context = await buildReportContext(opts, caseId, (req as any).user.id, row.rows[0]);
      return { case_id: caseId, report_type: "elderly_friendly", ...easyReport, debug: composeDebugReport(result, context), trace_id: traceId };
    }
    return { case_id: caseId, report_type: "elderly_friendly", ...easyReport, trace_id: traceId };
  });

  app.post(`${opts.apiPrefix}/cases/:caseId/reanalyze`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const { caseId } = req.params as any;
    const body = req.body as any;
    const caseRow = await opts.db.query(`SELECT * FROM cases WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`, [caseId, (req as any).user.id]);
    if (!caseRow.rowCount) return reply.code(404).send(opts.errorPayload("CASE_NOT_FOUND", "케이스를 찾을 수 없습니다.", traceId));
    const currentCase = caseRow.rows[0];
    const previousResultRow = await opts.db.query(
      `SELECT result, elderly_friendly_report, report_payload FROM analysis_results WHERE case_id=$1 AND owner_user_id=$2 ORDER BY version DESC LIMIT 1`,
      [caseId, (req as any).user.id]
    );
    const previousRecord = previousResultRow.rows[0] ?? {};
    const previousResult = previousRecord.result ?? {};
    const previousStoredReport = previousRecord.elderly_friendly_report ?? previousRecord.report_payload;
    const previousEasyReport = enrichEasyReport(
      sanitizeEasyReport(
        previousStoredReport && Object.keys(previousStoredReport).length
          ? previousStoredReport
          : previousResult.elderly_friendly_report && Object.keys(previousResult.elderly_friendly_report).length
            ? previousResult.elderly_friendly_report
            : composeEasyFallback(previousResult, { case: currentCase })
      ),
      previousResult
    );
    const normalizedFollowup = normalizeFollowupAnswers(body?.followup_answers ?? body?.followupAnswers ?? {}, currentCase.structured_facts ?? {});
    const structuredFacts = {
      ...(currentCase.structured_facts ?? {}),
      ...(body?.structured_facts ?? {}),
      ...normalizedFollowup.patch
    };
    const descriptionText = maskSensitive(body?.description_text ?? currentCase.description_text ?? "");
    const selectedKeywords = body?.selected_keywords ?? currentCase.selected_keywords ?? [];
    const analysisMode = body?.analysis_mode ?? currentCase.analysis_mode ?? "quick_summary";
    const latestUpload = await opts.db.query(
      `SELECT metadata,file_name,status,preprocess_summary
       FROM uploads
       WHERE case_id=$1 AND owner_user_id=$2 AND deleted_at IS NULL
       ORDER BY updated_at DESC LIMIT 1`,
      [caseId, (req as any).user.id]
    );
    const videoMetadata = buildReanalysisVideoMetadata(latestUpload.rows[0], body?.video_metadata ?? body?.videoMetadata);

    await opts.db.query(
      `UPDATE cases
       SET description_text=$3,
           structured_facts=$4::jsonb,
           selected_keywords=$5,
           analysis_mode=$6,
           status='analyzing'
       WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`,
      [caseId, (req as any).user.id, descriptionText, JSON.stringify(structuredFacts), selectedKeywords, analysisMode]
    );

    let agentResp;
    try {
      agentResp = await callInternalAgent("/internal/v1/analyze/text", {
        case_id: caseId,
        user_id: (req as any).user.id,
        description_text: descriptionText,
        structured_facts: structuredFacts,
        selected_keywords: selectedKeywords,
        video_metadata: videoMetadata,
        analysis_mode: analysisMode,
        ai_profile: body?.ai_profile,
        specialist_roles: body?.specialist_roles
      }, traceId, { baseUrl: opts.agentUrl, internalToken: opts.internalToken, timeoutMs: opts.analyzeTimeoutMs, retryCount: opts.retryCount });
    } catch {
      await opts.db.query(`UPDATE cases SET status='failed' WHERE id=$1 AND owner_user_id=$2`, [caseId, (req as any).user.id]).catch(() => undefined);
      return reply.code(502).send(opts.errorPayload("AI_TEMPORARY_UNAVAILABLE", "AI 분석 서비스가 일시적으로 불안정합니다. 잠시 후 재시도해 주세요.", traceId));
    }
    const baseEasyReport = enrichEasyReport(
      sanitizeEasyReport(agentResp.elderly_friendly_report ?? composeEasyFallback(agentResp, { case: { ...currentCase, structured_facts: structuredFacts } })),
      agentResp
    );
    const reanalysisChangeCard = composeReanalysisChangeCard(previousResult, agentResp, {
      ...normalizedFollowup,
      before_question_count: easyReportQuestionCount(previousEasyReport),
      after_question_count: easyReportQuestionCount(baseEasyReport),
    });
    const easyReport = reanalysisChangeCard ? { ...baseEasyReport, analysis_change_card: reanalysisChangeCard } : baseEasyReport;
    const ver = await opts.db.query(`SELECT COALESCE(MAX(version),0)+1 AS v FROM analysis_results WHERE case_id=$1`, [caseId]);
    const nextVersion = Number(ver.rows[0].v);
    const inserted = await insertAnalysisResult(opts, caseId, (req as any).user.id, "text", agentResp, easyReport, easyReport, nextVersion);
    await opts.db.query(`UPDATE cases SET status='completed', latest_result_id=$2 WHERE id=$1`, [caseId, inserted.id]);
    return {
      result_id: inserted.id,
      version: nextVersion,
      result: easyReport,
      report: easyReport,
      trace_id: traceId
    };
  });

  app.get(`${opts.apiPrefix}/cases/:caseId/evidence`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const { caseId } = req.params as any;
    const row = await opts.db.query(`SELECT evidence FROM analysis_results WHERE case_id=$1 AND owner_user_id=$2 ORDER BY version DESC LIMIT 1`, [caseId, (req as any).user.id]);
    if (!row.rowCount) return reply.code(404).send(opts.errorPayload("EVIDENCE_NOT_FOUND", "근거 데이터를 찾을 수 없습니다.", traceId));
    return { evidence: row.rows[0].evidence, trace_id: traceId };
  });

  app.get(`${opts.apiPrefix}/evidence/:chunkId`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const { chunkId } = req.params as any;
    const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    if (!uuidPattern.test(chunkId)) {
      return {
        chunk: {
          id: chunkId,
          chunk_summary: "정적 fallback 근거입니다. 외부 법률 API 또는 KB 적재가 부족할 때 최소 근거로 사용됩니다.",
          chunk_text: "국가법령정보센터/공공데이터 API 승인 또는 KB ingest 후에는 PostgreSQL에 저장된 실제 chunk 상세가 표시됩니다.",
          document_title: "Static Legal Fallback",
          source_name: "local-static-fallback",
          source_type: "static"
        },
        trace_id: traceId
      };
    }
    const row = await opts.db.query(
      `SELECT kc.id, kc.chunk_text, kc.chunk_summary, kc.metadata AS chunk_metadata,
              kd.id AS document_id, kd.title AS document_title, kd.doc_type, kd.metadata AS document_metadata,
              ks.name AS source_name, ks.source_type, ks.source_uri
       FROM kb_chunks kc
       JOIN kb_documents kd ON kd.id=kc.document_id
       JOIN kb_sources ks ON ks.id=kd.source_id
       WHERE kc.id=$1`,
      [chunkId]
    );
    if (!row.rowCount) return reply.code(404).send(opts.errorPayload("CHUNK_NOT_FOUND", "근거 문서를 찾을 수 없습니다.", traceId));
    return { chunk: row.rows[0], trace_id: traceId };
  });

  app.get(`${opts.apiPrefix}/legal/evidence/:chunkId`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const { chunkId } = req.params as any;
    const row = await opts.db.query(
      `SELECT kc.id, kc.chunk_text, kc.chunk_summary, kc.article_no, kc.clause_no,
              kc.scenario_tags, kc.keywords, kc.metadata AS chunk_metadata,
              kd.id AS document_id, kd.title AS document_title, kd.doc_type, kd.summary AS document_summary,
              kd.metadata AS document_metadata, ks.name AS source_name, ks.source_type, ks.source_uri
       FROM kb_chunks kc
       JOIN kb_documents kd ON kd.id=kc.document_id
       JOIN kb_sources ks ON ks.id=kd.source_id
       WHERE kc.id=$1`,
      [chunkId]
    );
    if (!row.rowCount) return reply.code(404).send(opts.errorPayload("CHUNK_NOT_FOUND", "근거 문서를 찾을 수 없습니다.", traceId));
    return { chunk: row.rows[0], trace_id: traceId };
  });
}
