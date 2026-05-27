import type { FastifyInstance, FastifyRequest } from "fastify";
import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { randomUUID } from "node:crypto";
import { requireUser } from "../lib/request-guards.js";
import type { StorageProvider } from "../storage/provider.js";

export type UploadRouteOptions = {
  apiPrefix: string;
  db: any;
  redis: any;
  storage: StorageProvider;
  localViewExpires: number;
  localDownloadExpires: number;
  errorPayload: (code: string, message: string, traceId: string) => any;
};

function trace(req: FastifyRequest) {
  return (req.headers["x-correlation-id"] as string) || randomUUID();
}

async function enqueueVideoPreprocessJob(opts: UploadRouteOptions, caseId: string, uploadId: string, ownerId: string, storagePath: string, autoAnalyzeAfterPreprocess = true) {
  const jobRes = await opts.db.query(
    `INSERT INTO jobs(case_id, upload_id, owner_user_id, type, status, payload)
     VALUES($1,$2,$3,'video_preprocess','queued',$4) RETURNING id`,
    [caseId, uploadId, ownerId, JSON.stringify({ upload_id: uploadId, case_id: caseId, storage_path: storagePath, auto_analyze_after_preprocess: autoAnalyzeAfterPreprocess })]
  );
  await opts.redis.xadd(
    process.env.REDIS_STREAM_KEY ?? "jobs:v1:stream",
    "MAXLEN",
    "~",
    "10000",
    "*",
    "job_id",
    jobRes.rows[0].id,
    "job_type",
    "video_preprocess"
  );
  return jobRes.rows[0].id as string;
}

async function createGetUrl(
  opts: UploadRouteOptions,
  uploadId: string,
  ownerId: string,
  disposition: "inline" | "attachment",
  expiresIn: number
) {
  const row = await opts.db.query(`SELECT * FROM uploads WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`, [uploadId, ownerId]);
  if (!row.rowCount) return null;
  const upload = row.rows[0];
  if (!["verified", "processing", "ready"].includes(upload.status)) return { blocked: true } as any;
  if (upload.storage_provider !== "local") return { blocked: true } as any;
  return {
    upload,
    url: `${opts.apiPrefix}/uploads/${uploadId}/local-content?disposition=${disposition}`,
    local: true,
    expiresIn
  } as any;
}

async function completeLocalUpload(
  opts: UploadRouteOptions,
  uploadId: string,
  ownerId: string,
  traceId: string,
  reply: any,
  mode: "body" | "path",
  autoAnalyzeAfterPreprocess = true
) {
  const found = await opts.db.query(
    `SELECT u.*, c.id as case_exists FROM uploads u
     JOIN cases c ON c.id=u.case_id
     WHERE u.id=$1 AND u.owner_user_id=$2 AND u.deleted_at IS NULL`,
    [uploadId, ownerId]
  );
  if (!found.rowCount) return reply.code(404).send(opts.errorPayload("UPLOAD_NOT_FOUND", "업로드를 찾을 수 없습니다.", traceId));
  const upload = found.rows[0];

  if (mode === "path" && (upload.storage_provider !== "local" || !upload.storage_path)) {
    return reply.code(409).send(opts.errorPayload("LOCAL_UPLOAD_ONLY", "현재는 로컬 업로드만 완료 처리할 수 있습니다.", traceId));
  }
  if (mode === "body") {
    if (upload.storage_provider !== "local") {
      return reply.code(409).send(opts.errorPayload("LOCAL_UPLOAD_ONLY", "현재는 로컬 업로드만 완료 처리할 수 있습니다.", traceId));
    }
    if (!upload.storage_path) {
      return reply.code(400).send(opts.errorPayload("UPLOAD_PATH_MISSING", "저장된 영상 경로를 찾을 수 없습니다.", traceId));
    }
  }
  let info;
  try {
    info = await stat(upload.storage_path);
  } catch {
    return reply.code(400).send(opts.errorPayload("LOCAL_FILE_NOT_FOUND", "로컬 업로드 파일을 확인하지 못했습니다.", traceId));
  }
  if (mode === "body" && !upload.content_type?.startsWith("video/")) {
    return reply.code(400).send(opts.errorPayload("INVALID_CONTENT_TYPE", "영상 파일만 업로드할 수 있습니다.", traceId));
  }

  await opts.db.query(
    `UPDATE uploads
     SET status='verified',
         file_size_bytes=$2,
         metadata = metadata || $3::jsonb
     WHERE id=$1`,
    [
      uploadId,
      Number(info.size),
      JSON.stringify({ completed_at: new Date().toISOString(), local_verified: true })
    ]
  );

  const existingJob = await opts.db.query(
    `SELECT id FROM jobs
     WHERE upload_id=$1 AND owner_user_id=$2 AND type='video_preprocess' AND status IN ('queued','running','retrying','succeeded')
     ORDER BY created_at DESC LIMIT 1`,
    [uploadId, ownerId]
  );
  const jobId = existingJob.rowCount
    ? existingJob.rows[0].id
    : await enqueueVideoPreprocessJob(opts, upload.case_id, uploadId, ownerId, upload.storage_path, autoAnalyzeAfterPreprocess);
  return { upload_id: uploadId, job_id: jobId, status: "verified", trace_id: traceId };
}

export function registerUploadRoutes(app: FastifyInstance, opts: UploadRouteOptions) {
  app.post(`${opts.apiPrefix}/uploads/init`, {
    schema: {
      body: {
        type: "object",
        required: ["case_id", "file_name", "content_type", "file_size_bytes"],
        properties: {
          case_id: { type: "string", format: "uuid" },
          file_name: { type: "string", minLength: 1, maxLength: 255 },
          content_type: { type: "string", pattern: "^video/" },
          file_size_bytes: { type: "integer", minimum: 1, maximum: 104857600 }
        }
      }
    }
  }, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    return reply.code(410).send(opts.errorPayload("S3_DISABLED_USE_LOCAL_UPLOAD", "현재는 로컬 영상 업로드만 지원합니다.", traceId));
  });

  app.post(`${opts.apiPrefix}/uploads/local`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const data = await (req as any).file();
    if (!data) return reply.code(400).send(opts.errorPayload("FILE_REQUIRED", "영상 파일을 선택해 주세요.", traceId));

    const caseId = String(data.fields?.case_id?.value ?? "");
    if (!caseId) return reply.code(400).send(opts.errorPayload("CASE_ID_REQUIRED", "케이스 정보가 필요합니다.", traceId));
    const ownerCase = await opts.db.query(`SELECT id FROM cases WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`, [caseId, (req as any).user.id]);
    if (!ownerCase.rowCount) return reply.code(404).send(opts.errorPayload("CASE_NOT_FOUND", "케이스를 찾을 수 없습니다.", traceId));

    const uploadId = randomUUID();
    let stored;
    try {
      stored = await opts.storage.putUpload({
        caseId,
        uploadId,
        fileName: data.filename,
        contentType: data.mimetype,
        stream: data.file
      });
    } catch (err: any) {
      if (err?.message === "INVALID_CONTENT_TYPE") {
        return reply.code(400).send(opts.errorPayload("INVALID_CONTENT_TYPE", "영상 파일만 업로드할 수 있습니다.", traceId));
      }
      throw err;
    }

    await opts.db.query(
      `INSERT INTO uploads(id, case_id, owner_user_id, s3_bucket, s3_key, storage_provider, storage_path, file_name, content_type, file_size_bytes, status, metadata)
       VALUES($1,$2,$3,'local',$4,'local',$5,$6,$7,$8,'uploaded',$9)`,
      [
        uploadId,
        caseId,
        (req as any).user.id,
        stored.storagePath,
        stored.storagePath,
        data.filename,
        data.mimetype,
        stored.sizeBytes,
        JSON.stringify({ storage_provider: "local", original_name: data.filename })
      ]
    );
    return { upload_id: uploadId, status: "uploaded", storage_provider: "local", trace_id: traceId };
  });

  app.post(`${opts.apiPrefix}/uploads/complete`, {
    schema: {
      body: {
        type: "object",
        required: ["upload_id"],
        properties: {
          upload_id: { type: "string", format: "uuid" },
          auto_analyze_after_preprocess: { type: "boolean" }
        }
      }
    }
  }, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const { upload_id, auto_analyze_after_preprocess } = req.body as any;
    return completeLocalUpload(opts, upload_id, (req as any).user.id, traceId, reply, "body", auto_analyze_after_preprocess !== false);
  });

  app.post(`${opts.apiPrefix}/uploads/:uploadId/complete`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const autoAnalyze = (req.query as any)?.autoAnalyzeAfterPreprocess !== "false";
    return completeLocalUpload(opts, (req.params as any).uploadId, (req as any).user.id, traceId, reply, "path", autoAnalyze);
  });

  app.get(`${opts.apiPrefix}/uploads/:uploadId`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const { uploadId } = req.params as any;
    const row = await opts.db.query(`SELECT * FROM uploads WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`, [uploadId, (req as any).user.id]);
    if (!row.rowCount) return reply.code(404).send(opts.errorPayload("UPLOAD_NOT_FOUND", "업로드를 찾을 수 없습니다.", traceId));
    return { upload: row.rows[0], trace_id: traceId };
  });

  app.get(`${opts.apiPrefix}/cases/:caseId/uploads`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const { caseId } = req.params as any;
    const owner = await opts.db.query(`SELECT id FROM cases WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`, [caseId, (req as any).user.id]);
    if (!owner.rowCount) return reply.code(404).send(opts.errorPayload("CASE_NOT_FOUND", "케이스를 찾을 수 없습니다.", traceId));
    const rows = await opts.db.query(
      `SELECT id,file_name,content_type,file_size_bytes,status,storage_provider,metadata,frame_dir,preprocess_summary,created_at FROM uploads
       WHERE case_id=$1 AND owner_user_id=$2 AND deleted_at IS NULL
       ORDER BY created_at DESC`,
      [caseId, (req as any).user.id]
    );
    return { items: rows.rows, trace_id: traceId };
  });

  app.get(`${opts.apiPrefix}/uploads/:uploadId/local-content`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const { uploadId } = req.params as any;
    const disposition = ((req.query as any)?.disposition === "attachment" ? "attachment" : "inline") as "inline" | "attachment";
    const row = await opts.db.query(
      `SELECT * FROM uploads WHERE id=$1 AND owner_user_id=$2 AND storage_provider='local' AND deleted_at IS NULL`,
      [uploadId, (req as any).user.id]
    );
    if (!row.rowCount) return reply.code(404).send(opts.errorPayload("UPLOAD_NOT_FOUND", "업로드를 찾을 수 없습니다.", traceId));
    const upload = row.rows[0];
    if (!["uploaded", "verified", "processing", "ready"].includes(upload.status)) {
      return reply.code(409).send(opts.errorPayload("UPLOAD_NOT_READY", "아직 재생할 수 없는 업로드입니다.", traceId));
    }
    const info = await stat(upload.storage_path);
    reply.header("content-type", upload.content_type);
    reply.header("content-length", String(info.size));
    reply.header("content-disposition", `${disposition}; filename="${encodeURIComponent(upload.file_name)}"`);
    return reply.send(createReadStream(upload.storage_path));
  });

  app.get(`${opts.apiPrefix}/uploads/:uploadId/view-url`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const result = await createGetUrl(opts, (req.params as any).uploadId, (req as any).user.id, "inline", opts.localViewExpires);
    if (!result) return reply.code(404).send(opts.errorPayload("UPLOAD_NOT_FOUND", "업로드를 찾을 수 없습니다.", traceId));
    if ((result as any).blocked) return reply.code(409).send(opts.errorPayload("UPLOAD_NOT_READY", "아직 검증되지 않은 업로드입니다.", traceId));
    return { view_url: result.url, expires_in_sec: opts.localViewExpires, trace_id: traceId };
  });

  app.get(`${opts.apiPrefix}/uploads/:uploadId/download-url`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const result = await createGetUrl(opts, (req.params as any).uploadId, (req as any).user.id, "attachment", opts.localDownloadExpires);
    if (!result) return reply.code(404).send(opts.errorPayload("UPLOAD_NOT_FOUND", "업로드를 찾을 수 없습니다.", traceId));
    if ((result as any).blocked) return reply.code(409).send(opts.errorPayload("UPLOAD_NOT_READY", "아직 검증되지 않은 업로드입니다.", traceId));
    return { download_url: result.url, expires_in_sec: opts.localDownloadExpires, trace_id: traceId };
  });

  app.delete(`${opts.apiPrefix}/uploads/:uploadId`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const { uploadId } = req.params as any;
    const updated = await opts.db.query(
      `UPDATE uploads SET status='deleted', deleted_at=now() WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL RETURNING id`,
      [uploadId, (req as any).user.id]
    );
    if (!updated.rowCount) return reply.code(404).send(opts.errorPayload("UPLOAD_NOT_FOUND", "업로드를 찾을 수 없습니다.", traceId));
    return { ok: true, trace_id: traceId };
  });
}
