import type { FastifyRequest } from "fastify";
import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { randomUUID } from "node:crypto";
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

export function trace(req: FastifyRequest) {
    return (req.headers["x-correlation-id"] as string) || randomUUID();
}

function normalizeUploadStorageKey(value: any): string | null {
    const raw = String(value ?? "").trim().replace(/\\/g, "/");
    if (!raw) return null;

    const withoutBase = raw
        .replace(/^\/+lawcompass\/+/i, "")
        .replace(/^\/+volume1\/lawcompass\/+/i, "");

    return withoutBase.replace(/^\/+/, "");
}

function storageReference(upload: any) {
    const driver = upload.storage_driver ?? upload.storage_provider ?? "local";

    const normalizedKey = normalizeUploadStorageKey(upload.storage_key ?? upload.s3_key ?? null);

    // NAS/S3에서는 storage_path를 storage_key처럼 fallback하면
    // /lawcompass/lawcompass/uploads/... 형태로 경로가 꼬일 수 있다.
    // local legacy 데이터에서만 storage_path fallback을 허용한다.
    const legacyLocalKey =
        driver === "local"
            ? normalizeUploadStorageKey(upload.storage_path)
            : null;

    return {
        storage_driver: driver,
        storage_key: normalizedKey ?? legacyLocalKey,
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
        if (
            lowered.includes("password") ||
            lowered.includes("secret") ||
            lowered.includes("token") ||
            lowered === "nas_user" ||
            lowered === "nas_host"
        ) {
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

export function storageErrorCode(err: any) {
    const message = String(err?.message || "");
    const lowered = message.toLowerCase();

    if (
        lowered.includes("authentication") ||
        lowered.includes("auth failed") ||
        lowered.includes("all configured authentication methods failed")
    ) {
        return "STORAGE_AUTH_FAILED";
    }

    if (lowered.includes("permission") || lowered.includes("eacces") || lowered.includes("denied")) {
        return "STORAGE_PERMISSION_DENIED";
    }

    if (lowered.includes("no such file") || lowered.includes("not found") || lowered.includes("enoent")) {
        return "STORAGE_PATH_NOT_FOUND";
    }

    if (message.includes("ENOSPC") || message.includes("NO_SPACE")) {
        return "STORAGE_CAPACITY_EXCEEDED";
    }

    if (
        lowered.includes("connect") ||
        message.includes("ECONN") ||
        lowered.includes("timed out") ||
        lowered.includes("timeout")
    ) {
        return "STORAGE_UNAVAILABLE";
    }

    return "STORAGE_ERROR";
}

export function storageUserMessage(err: any) {
    const code = storageErrorCode(err);

    if (code === "STORAGE_AUTH_FAILED") {
        return "영상 저장소 인증에 실패했습니다. 관리자에게 문의해 주세요.";
    }

    if (code === "STORAGE_PATH_NOT_FOUND") {
        return "영상 저장 폴더를 찾지 못했습니다. 관리자에게 문의해 주세요.";
    }

    if (code === "STORAGE_PERMISSION_DENIED") {
        return "영상 저장 권한을 확인해야 합니다. 관리자에게 문의해 주세요.";
    }

    if (code === "STORAGE_CAPACITY_EXCEEDED") {
        return "저장 공간이 부족하여 영상을 저장하지 못했습니다. 관리자에게 문의해 주세요.";
    }

    if (code === "STORAGE_UNAVAILABLE") {
        return "영상 저장소에 일시적으로 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.";
    }

    return "영상 저장 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.";
}

export function isDatabaseSchemaError(err: any) {
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

function safeStoredStorageKey(stored: any): string | null {
    return normalizeUploadStorageKey(stored.storageKey ?? stored.storage_key ?? stored.s3Key ?? stored.s3_key ?? null);
}

function safeStoredStoragePath(stored: any): string | null {
    const value = stored.storagePath ?? stored.storage_path ?? null;
    return value ? String(value) : null;
}

export function buildUploadInsert(
    stored: any,
    input: {
        uploadId: string;
        caseId: string;
        ownerUserId: string;
        fileName: string;
        contentType: string;
    }
) {
    const storageDriver = storageDriverOf(stored);
    const originalFilename = stored.originalFilename ?? input.fileName;
    const contentType = stored.mimeType ?? stored.contentType ?? input.contentType;
    const storageKey = safeStoredStorageKey(stored);
    const storagePath = safeStoredStoragePath(stored);
    const sizeBytes = Number(stored.sizeBytes ?? stored.fileSizeBytes ?? 0);
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

export async function enqueueVideoPreprocessJob(
    opts: UploadRouteOptions,
    caseId: string,
    uploadId: string,
    ownerId: string,
    upload: any,
    autoAnalyzeAfterPreprocess = true
) {
    const ref = storageReference(upload);

    const jobRes = await opts.db.query(
        `INSERT INTO jobs(case_id, upload_id, owner_user_id, type, status, payload)
     VALUES($1,$2,$3,'video_preprocess','queued',$4) RETURNING id`,
        [
            caseId,
            uploadId,
            ownerId,
            JSON.stringify({
                upload_id: uploadId,
                case_id: caseId,
                ...ref,
                auto_analyze_after_preprocess: autoAnalyzeAfterPreprocess,
            }),
        ]
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

export async function createGetUrl(
    opts: UploadRouteOptions,
    uploadId: string,
    ownerId: string,
    disposition: "inline" | "attachment",
    expiresIn: number
) {
    const row = await opts.db.query(
        `SELECT * FROM uploads WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`,
        [uploadId, ownerId]
    );

    if (!row.rowCount) return null;

    const upload = row.rows[0];

    if (!["verified", "processing", "ready"].includes(upload.status)) {
        return { blocked: true } as any;
    }

    return {
        upload,
        url: `${opts.apiPrefix}/uploads/${uploadId}/download?disposition=${disposition}`,
        gateway_proxy: true,
        expiresIn,
    } as any;
}

export async function sendUploadContent(opts: UploadRouteOptions, req: FastifyRequest, reply: any) {
    const traceId = trace(req);
    const { uploadId } = req.params as any;
    const disposition = ((req.query as any)?.disposition === "attachment" ? "attachment" : "inline") as
        | "inline"
        | "attachment";

    const row = await opts.db.query(
        `SELECT * FROM uploads WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`,
        [uploadId, (req as any).user.id]
    );

    if (!row.rowCount) {
        return reply.code(404).send(opts.errorPayload("UPLOAD_NOT_FOUND", "업로드를 찾을 수 없습니다.", traceId));
    }

    const upload = row.rows[0];

    if (!["uploaded", "verified", "processing", "ready"].includes(upload.status)) {
        return reply.code(409).send(opts.errorPayload("UPLOAD_NOT_READY", "아직 재생할 수 없는 업로드입니다.", traceId));
    }

    const ref = storageReference(upload);

    if (!ref.storage_key) {
        return reply
            .code(404)
            .send(opts.errorPayload("STORED_FILE_NOT_FOUND", "저장된 영상을 찾지 못했습니다. 다시 업로드해 주세요.", traceId));
    }

    try {
        const driver = ref.storage_driver;

        const stream =
            driver === "local" && upload.storage_path && !upload.storage_key
                ? createReadStream(upload.storage_path)
                : await opts.storage.getStream(ref.storage_key);

        reply.header("content-type", upload.content_type);

        if (upload.file_size_bytes || upload.size_bytes) {
            reply.header("content-length", String(upload.file_size_bytes ?? upload.size_bytes));
        }

        reply.header("content-disposition", `${disposition}; filename="${encodeURIComponent(upload.file_name)}"`);

        return reply.send(stream);
    } catch (err: any) {
        (req as any).log?.warn?.(
            {
                err,
                trace_id: traceId,
                upload_id: uploadId,
                case_id: upload.case_id,
                storage_driver: ref.storage_driver,
                storage_key: maskStorageKey(ref.storage_key),
                status: upload.status,
                storage_status: upload.storage_status,
            },
            "upload content storage read failed"
        );

        return reply.code(404).send(opts.errorPayload(storageErrorCode(err), storageUserMessage(err), traceId));
    }
}

export async function completeLocalUpload(
    opts: UploadRouteOptions,
    req: FastifyRequest,
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

    if (!found.rowCount) {
        return reply.code(404).send(opts.errorPayload("UPLOAD_NOT_FOUND", "업로드를 찾을 수 없습니다.", traceId));
    }

    const upload = found.rows[0];
    const ref = storageReference(upload);

    if (!ref.storage_key) {
        (req as any).log?.warn?.(
            {
                trace_id: traceId,
                upload_id: uploadId,
                case_id: upload.case_id,
                storage_driver: ref.storage_driver,
                storage_key: null,
                status: upload.status,
                storage_status: upload.storage_status,
            },
            "upload complete missing storage key"
        );

        return reply.code(400).send(opts.errorPayload("UPLOAD_PATH_MISSING", "저장된 영상 경로를 찾을 수 없습니다.", traceId));
    }

    let sizeBytes = Number(upload.size_bytes ?? upload.file_size_bytes ?? 0);

    try {
        const driver = ref.storage_driver;

        if (driver === "local" && upload.storage_path && !upload.storage_key) {
            const info = await stat(upload.storage_path);
            sizeBytes = Number(info.size);
        } else {
            const exists = await opts.storage.exists(ref.storage_key);

            if (!exists) {
                (req as any).log?.warn?.(
                    {
                        trace_id: traceId,
                        upload_id: uploadId,
                        case_id: upload.case_id,
                        storage_driver: ref.storage_driver,
                        storage_key: maskStorageKey(ref.storage_key),
                        storage_path: upload.storage_path ? maskStorageKey(upload.storage_path) : null,
                        status: upload.status,
                        storage_status: upload.storage_status,
                    },
                    "upload complete stored file not found"
                );

                return reply
                    .code(400)
                    .send(opts.errorPayload("STORED_FILE_NOT_FOUND", "저장된 영상을 찾지 못했습니다. 다시 업로드해 주세요.", traceId));
            }
        }
    } catch (err: any) {
        (req as any).log?.warn?.(
            {
                err,
                trace_id: traceId,
                upload_id: uploadId,
                case_id: upload.case_id,
                storage_driver: ref.storage_driver,
                storage_key: maskStorageKey(ref.storage_key),
                storage_path: upload.storage_path ? maskStorageKey(upload.storage_path) : null,
                status: upload.status,
                storage_status: upload.storage_status,
            },
            "upload complete storage verification failed"
        );

        return reply.code(400).send(opts.errorPayload(storageErrorCode(err), storageUserMessage(err), traceId));
    }

    if (mode === "body" && !upload.content_type?.startsWith("video/")) {
        return reply.code(400).send(opts.errorPayload("INVALID_CONTENT_TYPE", "영상 파일만 업로드할 수 있습니다.", traceId));
    }

    await opts.db.query(
        `UPDATE uploads
     SET status='verified',
         file_size_bytes=$2,
         size_bytes=COALESCE(size_bytes, $2),
         storage_status=COALESCE(storage_status, 'stored'),
         metadata = metadata || $3::jsonb
     WHERE id=$1`,
        [
            uploadId,
            sizeBytes,
            JSON.stringify({
                completed_at: new Date().toISOString(),
                storage_verified: true,
                storage_key: ref.storage_key,
                storage_driver: ref.storage_driver,
            }),
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

    return {
        upload_id: uploadId,
        job_id: jobId,
        status: "verified",
        trace_id: traceId,
    };
}
