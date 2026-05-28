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

function storageReference(upload: any) {
  return {
    storage_driver: upload.storage_driver ?? upload.storage_provider ?? "local",
    storage_key: upload.storage_key ?? upload.s3_key ?? upload.storage_path,
    storage_path: upload.storage_path,
  };
}

export function publicUpload(upload: any) {
  const {
    storage_path: _storagePath,
    s3_key: _s3Key,
    s3_bucket: _s3Bucket,
    storage_key: _storageKey,
    storage_driver: _storageDriver,
    storage_provider: _storageProvider,
    storage_status: _storageStatus,
    frame_dir: _frameDir,
    derived_path: _derivedPath,
    preprocess_summary: _preprocessSummary,
    ...safe
  } = upload;
  return {
    ...safe,
    metadata: sanitizeUploadMetadata(safe.metadata),
  };
}

function sanitizeUploadMetadata(metadata: any) {
  if (!metadata || typeof metadata !== "object" || Array.isArray(metadata)) return metadata;
  const copy = { ...metadata };
  for (const key of [
    "storage_path",
    "storage_key",
    "source_storage_key",
    "local_cache_path",
    "storage_driver",
    "storage_provider",
    "storage_status",
    "processed_frames_key",
    "processed_clips_key",
    "representative_frames",
    "representative_frame_details",
    "extracted_frame_paths",
    "openai_frame_analysis",
    "yolo_frame_analysis",
    "preprocess_summary",
  ]) {
    delete copy[key];
  }
  for (const key of Object.keys(copy)) {
    const lowered = key.toLowerCase();
    if (lowered.includes("password") || lowered.includes("secret") || lowered.includes("token") || lowered === "nas_user" || lowered === "nas_host") {
      delete copy[key];
    }
  }
  return copy;
}

function maskStorageKey(value: string) {
  const parts = String(value || "").replace(/\\/g, "/").split("/").filter(Boolean);
  if (parts.length <= 2) return parts.join("/");
  return `${parts.slice(0, 2).join("/")}/.../${parts.at(-1)}`;
}

async function enqueueVideoPreprocessJob(opts: UploadRouteOptions, caseId: string, uploadId: string, ownerId: string, upload: any, autoAnalyzeAfterPreprocess = true) {
  const ref = storageReference(upload);
  const jobRes = await opts.db.query(
    `INSERT INTO jobs(case_id, upload_id, owner_user_id, type, status, payload)
     VALUES($1,$2,$3,'video_preprocess','queued',$4) RETURNING id`,
    [caseId, uploadId, ownerId, JSON.stringify({ upload_id: uploadId, case_id: caseId, ...ref, auto_analyze_after_preprocess: autoAnalyzeAfterPreprocess })]
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
  return {
    upload,
    url: `${opts.apiPrefix}/uploads/${uploadId}/download?disposition=${disposition}`,
    gateway_proxy: true,
    expiresIn
  } as any;
}

async function sendUploadContent(opts: UploadRouteOptions, req: FastifyRequest, reply: any) {
  const traceId = trace(req);
  const { uploadId } = req.params as any;
  const disposition = ((req.query as any)?.disposition === "attachment" ? "attachment" : "inline") as "inline" | "attachment";
  const row = await opts.db.query(
    `SELECT * FROM uploads WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`,
    [uploadId, (req as any).user.id]
  );
  if (!row.rowCount) return reply.code(404).send(opts.errorPayload("UPLOAD_NOT_FOUND", "업로드를 찾을 수 없습니다.", traceId));
  const upload = row.rows[0];
  if (!["uploaded", "verified", "processing", "ready"].includes(upload.status)) {
    return reply.code(409).send(opts.errorPayload("UPLOAD_NOT_READY", "아직 재생할 수 없는 업로드입니다.", traceId));
  }
  const ref = storageReference(upload);
  if (!ref.storage_key) return reply.code(404).send(opts.errorPayload("STORED_FILE_NOT_FOUND", "저장된 영상을 찾지 못했습니다. 다시 업로드해 주세요.", traceId));
  try {
    const stream = ((upload.storage_provider ?? upload.storage_driver) === "local" && upload.storage_path && !upload.storage_key)
      ? createReadStream(upload.storage_path)
      : await opts.storage.getStream(ref.storage_key);
    reply.header("content-type", upload.content_type);
    if (upload.file_size_bytes || upload.size_bytes) reply.header("content-length", String(upload.file_size_bytes ?? upload.size_bytes));
    reply.header("content-disposition", `${disposition}; filename="${encodeURIComponent(upload.file_name)}"`);
    return reply.send(stream);
  } catch (err: any) {
    return reply.code(404).send(opts.errorPayload(storageErrorCode(err), storageUserMessage(err), traceId));
  }
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

  const ref = storageReference(upload);
  if (!ref.storage_key) return reply.code(400).send(opts.errorPayload("UPLOAD_PATH_MISSING", "저장된 영상 경로를 찾을 수 없습니다.", traceId));
  let sizeBytes = Number(upload.size_bytes ?? upload.file_size_bytes ?? 0);
  try {
    if ((upload.storage_provider ?? upload.storage_driver) === "local" && upload.storage_path && !upload.storage_key) {
      const info = await stat(upload.storage_path);
      sizeBytes = Number(info.size);
    } else if (!await opts.storage.exists(ref.storage_key)) {
      return reply.code(400).send(opts.errorPayload("STORED_FILE_NOT_FOUND", "저장된 영상을 찾지 못했습니다. 다시 업로드해 주세요.", traceId));
    }
  } catch (err: any) {
    return reply.code(400).send(opts.errorPayload(storageErrorCode(err), storageUserMessage(err), traceId));
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
      sizeBytes,
      JSON.stringify({ completed_at: new Date().toISOString(), storage_verified: true })
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
    : await enqueueVideoPreprocessJob(opts, upload.case_id, uploadId, ownerId, upload, autoAnalyzeAfterPreprocess);
  return { upload_id: uploadId, job_id: jobId, status: "verified", trace_id: traceId };
}

function storageErrorCode(err: any) {
  const message = String(err?.message || "");
  const lowered = message.toLowerCase();
  if (lowered.includes("authentication") || lowered.includes("auth failed") || lowered.includes("all configured authentication methods failed")) return "STORAGE_AUTH_FAILED";
  if (lowered.includes("permission") || lowered.includes("eacces") || lowered.includes("denied")) return "STORAGE_PERMISSION_DENIED";
  if (lowered.includes("no such file") || lowered.includes("not found") || lowered.includes("enoent")) return "STORAGE_PATH_NOT_FOUND";
  if (message.includes("ENOSPC") || message.includes("NO_SPACE")) return "STORAGE_CAPACITY_EXCEEDED";
  if (lowered.includes("connect") || message.includes("ECONN") || lowered.includes("timed out") || lowered.includes("timeout")) return "STORAGE_UNAVAILABLE";
  return "STORAGE_ERROR";
}

function storageUserMessage(err: any) {
  const code = storageErrorCode(err);
  if (code === "STORAGE_AUTH_FAILED") return "영상 저장소 인증에 실패했습니다. 관리자에게 문의해 주세요.";
  if (code === "STORAGE_PATH_NOT_FOUND") return "영상 저장 폴더를 찾지 못했습니다. 관리자에게 문의해 주세요.";
  if (code === "STORAGE_PERMISSION_DENIED") return "영상 저장 권한을 확인해야 합니다. 관리자에게 문의해 주세요.";
  if (code === "STORAGE_CAPACITY_EXCEEDED") return "저장 공간이 부족하여 영상을 저장하지 못했습니다. 관리자에게 문의해 주세요.";
  if (code === "STORAGE_UNAVAILABLE") return "영상 저장소에 일시적으로 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.";
  return "영상 저장 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.";
}

function isDatabaseSchemaError(err: any) {
  const code = String(err?.code || "");
  const message = String(err?.message || "").toLowerCase();
  return code === "42703" || code === "42P01" || message.includes("column") || message.includes("relation");
}

function storageDriverOf(stored: any): string {
  return stored.storageDriver ?? stored.driver ?? stored.storageProvider ?? stored.provider ?? "local";
}

function legacyBucketFor(driver: string): string {
  return driver === "nas_sftp" ? "nas-sftp" : driver;
}

export function buildUploadInsert(stored: any, input: { uploadId: string; caseId: string; ownerUserId: string; fileName: string; contentType: string }) {
  const storageDriver = storageDriverOf(stored);
  const originalFilename = stored.originalFilename ?? input.fileName;
  const contentType = stored.mimeType ?? stored.contentType ?? input.contentType;
  const storageKey = stored.storageKey;
  const storagePath = stored.storagePath;
  const sizeBytes = stored.sizeBytes;
  const sha256 = stored.sha256 ?? null;
  const etag = sha256;
  const metadata = {
    storage_driver: storageDriver,
    storage_provider: storageDriver,
    storage_key: storageKey,
    original_filename: originalFilename,
    size_bytes: sizeBytes,
    sha256,
    mime_type: contentType,
    upload_message: "영상이 안전하게 저장되었습니다.",
  };
  return {
    text: `INSERT INTO uploads(
           id, case_id, owner_user_id, s3_bucket, s3_key, file_name, content_type,
           file_size_bytes, etag, status, metadata, storage_provider, storage_path,
           storage_driver, storage_key, size_bytes, sha256, original_filename, mime_type,
           storage_status
         )
         VALUES(
           $1::uuid,
           $2::uuid,
           $3::uuid,
           $4::text,
           $5::text,
           $6::varchar,
           $7::varchar,
           $8::bigint,
           $9::varchar,
           $10::upload_status,
           $11::jsonb,
           $12::varchar,
           $13::text,
           $14::text,
           $15::text,
           $16::bigint,
           $17::text,
           $18::text,
           $19::text,
           $20::text
         )`,
    values: [
      input.uploadId,
      input.caseId,
      input.ownerUserId,
      legacyBucketFor(storageDriver),
      storageKey,
      originalFilename,
      contentType,
      sizeBytes,
      etag,
      "uploaded",
      JSON.stringify(metadata),
      storageDriver,
      storagePath,
      storageDriver,
      storageKey,
      sizeBytes,
      sha256,
      originalFilename,
      contentType,
      "stored",
    ],
    metadata,
  };
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
          file_size_bytes: { type: "integer", minimum: 1, maximum: 524288000 }
        }
      }
    }
  }, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    return reply.code(410).send(opts.errorPayload("DIRECT_UPLOAD_DISABLED_USE_FORM_UPLOAD", "현재는 화면에서 영상을 선택해 저장해 주세요.", traceId));
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
      return reply.code(503).send(opts.errorPayload(storageErrorCode(err), storageUserMessage(err), traceId));
    }

    try {
      const insert = buildUploadInsert(stored, {
        uploadId,
        caseId,
        ownerUserId: (req as any).user.id,
        fileName: data.filename,
        contentType: data.mimetype,
      });
      await opts.db.query(insert.text, insert.values);
    } catch (err: any) {
      (req as any).log?.error?.({ err, trace_id: traceId }, "upload metadata insert failed");
      await opts.storage.delete(stored.storageKey).catch(() => undefined);
      const code = isDatabaseSchemaError(err) ? "UPLOAD_SCHEMA_MISMATCH" : "UPLOAD_METADATA_SAVE_FAILED";
      return reply.code(500).send(opts.errorPayload(code, "업로드 정보를 저장하지 못했습니다. 관리자에게 문의해 주세요.", traceId));
    }
    return { upload_id: uploadId, status: "uploaded", message: "영상이 안전하게 보관되었습니다.", trace_id: traceId };
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
    return { upload: publicUpload(row.rows[0]), trace_id: traceId };
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
    return { items: rows.rows.map(publicUpload), trace_id: traceId };
  });

  app.get(`${opts.apiPrefix}/uploads/:uploadId/local-content`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    return sendUploadContent(opts, req, reply);
  });

  app.get(`${opts.apiPrefix}/uploads/:uploadId/download`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    return sendUploadContent(opts, req, reply);
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
