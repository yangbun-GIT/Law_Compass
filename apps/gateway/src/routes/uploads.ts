import type { FastifyInstance } from "fastify";
import { randomUUID } from "node:crypto";
import { requireUser } from "../lib/request-guards.js";
import {
    buildUploadInsert,
    completeLocalUpload,
    createGetUrl,
    isDatabaseSchemaError,
    publicUpload,
    sendUploadContent,
    storageErrorCode,
    storageUserMessage,
    trace,
    type UploadRouteOptions,
} from "../services/uploadService.js";

export { buildUploadInsert, publicUpload } from "../services/uploadService.js";

export function registerUploadRoutes(app: FastifyInstance, opts: UploadRouteOptions) {
    app.post(
        `${opts.apiPrefix}/uploads/init`,
        {
            schema: {
                body: {
                    type: "object",
                    required: ["case_id", "file_name", "content_type", "file_size_bytes"],
                    properties: {
                        case_id: { type: "string", format: "uuid" },
                        file_name: { type: "string", minLength: 1, maxLength: 255 },
                        content_type: { type: "string", pattern: "^video/" },
                        file_size_bytes: { type: "integer", minimum: 1, maximum: 524288000 },
                    },
                },
            },
        },
        async (req, reply) => {
            if (!requireUser(req as any, reply)) return;

            const traceId = trace(req);

            return reply
                .code(410)
                .send(opts.errorPayload("DIRECT_UPLOAD_DISABLED_USE_FORM_UPLOAD", "현재는 화면에서 영상을 선택해 저장해 주세요.", traceId));
        }
    );

    app.post(`${opts.apiPrefix}/uploads/local`, async (req, reply) => {
        if (!requireUser(req as any, reply)) return;

        const traceId = trace(req);
        const data = await (req as any).file();

        if (!data) {
            return reply.code(400).send(opts.errorPayload("FILE_REQUIRED", "영상 파일을 선택해 주세요.", traceId));
        }

        const caseId = String(data.fields?.case_id?.value ?? "");

        if (!caseId) {
            return reply.code(400).send(opts.errorPayload("CASE_ID_REQUIRED", "케이스 정보가 필요합니다.", traceId));
        }

        const ownerCase = await opts.db.query(
            `SELECT id FROM cases WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`,
            [caseId, (req as any).user.id]
        );

        if (!ownerCase.rowCount) {
            return reply.code(404).send(opts.errorPayload("CASE_NOT_FOUND", "케이스를 찾을 수 없습니다.", traceId));
        }

        const uploadId = randomUUID();
        let stored: any;

        try {
            stored = await opts.storage.putUpload({
                caseId,
                uploadId,
                fileName: data.filename,
                contentType: data.mimetype,
                stream: data.file,
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

            if (stored?.storageKey) {
                await opts.storage.delete(stored.storageKey).catch(() => undefined);
            }

            const code = isDatabaseSchemaError(err) ? "UPLOAD_SCHEMA_MISMATCH" : "UPLOAD_METADATA_SAVE_FAILED";

            return reply
                .code(500)
                .send(opts.errorPayload(code, "업로드 정보를 저장하지 못했습니다. 관리자에게 문의해 주세요.", traceId));
        }

        return {
            upload_id: uploadId,
            status: "uploaded",
            message: "영상이 안전하게 보관되었습니다.",
            trace_id: traceId,
        };
    });

    app.post(
        `${opts.apiPrefix}/uploads/complete`,
        {
            schema: {
                body: {
                    type: "object",
                    required: ["upload_id"],
                    properties: {
                        upload_id: { type: "string", format: "uuid" },
                        auto_analyze_after_preprocess: { type: "boolean" },
                    },
                },
            },
        },
        async (req, reply) => {
            if (!requireUser(req as any, reply)) return;

            const traceId = trace(req);
            const { upload_id, auto_analyze_after_preprocess } = req.body as any;

            return completeLocalUpload(
                opts,
                req,
                upload_id,
                (req as any).user.id,
                traceId,
                reply,
                "body",
                auto_analyze_after_preprocess !== false
            );
        }
    );

    app.post(`${opts.apiPrefix}/uploads/:uploadId/complete`, async (req, reply) => {
        if (!requireUser(req as any, reply)) return;

        const traceId = trace(req);
        const autoAnalyze = (req.query as any)?.autoAnalyzeAfterPreprocess !== "false";

        return completeLocalUpload(
            opts,
            req,
            (req.params as any).uploadId,
            (req as any).user.id,
            traceId,
            reply,
            "path",
            autoAnalyze
        );
    });

    app.get(`${opts.apiPrefix}/uploads/:uploadId`, async (req, reply) => {
        if (!requireUser(req as any, reply)) return;

        const traceId = trace(req);
        const { uploadId } = req.params as any;

        const row = await opts.db.query(
            `SELECT * FROM uploads WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`,
            [uploadId, (req as any).user.id]
        );

        if (!row.rowCount) {
            return reply.code(404).send(opts.errorPayload("UPLOAD_NOT_FOUND", "업로드를 찾을 수 없습니다.", traceId));
        }

        return {
            upload: publicUpload(row.rows[0]),
            trace_id: traceId,
        };
    });

    app.get(`${opts.apiPrefix}/cases/:caseId/uploads`, async (req, reply) => {
        if (!requireUser(req as any, reply)) return;

        const traceId = trace(req);
        const { caseId } = req.params as any;

        const owner = await opts.db.query(
            `SELECT id FROM cases WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`,
            [caseId, (req as any).user.id]
        );

        if (!owner.rowCount) {
            return reply.code(404).send(opts.errorPayload("CASE_NOT_FOUND", "케이스를 찾을 수 없습니다.", traceId));
        }

        const rows = await opts.db.query(
            `SELECT id,file_name,content_type,file_size_bytes,status,storage_provider,metadata,frame_dir,preprocess_summary,created_at FROM uploads
       WHERE case_id=$1 AND owner_user_id=$2 AND deleted_at IS NULL
       ORDER BY created_at DESC`,
            [caseId, (req as any).user.id]
        );

        return {
            items: rows.rows.map(publicUpload),
            trace_id: traceId,
        };
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

        const result = await createGetUrl(
            opts,
            (req.params as any).uploadId,
            (req as any).user.id,
            "inline",
            opts.localViewExpires
        );

        if (!result) {
            return reply.code(404).send(opts.errorPayload("UPLOAD_NOT_FOUND", "업로드를 찾을 수 없습니다.", traceId));
        }

        if ((result as any).blocked) {
            return reply.code(409).send(opts.errorPayload("UPLOAD_NOT_READY", "아직 검증되지 않은 업로드입니다.", traceId));
        }

        return {
            view_url: result.url,
            expires_in_sec: opts.localViewExpires,
            trace_id: traceId,
        };
    });

    app.get(`${opts.apiPrefix}/uploads/:uploadId/download-url`, async (req, reply) => {
        if (!requireUser(req as any, reply)) return;

        const traceId = trace(req);

        const result = await createGetUrl(
            opts,
            (req.params as any).uploadId,
            (req as any).user.id,
            "attachment",
            opts.localDownloadExpires
        );

        if (!result) {
            return reply.code(404).send(opts.errorPayload("UPLOAD_NOT_FOUND", "업로드를 찾을 수 없습니다.", traceId));
        }

        if ((result as any).blocked) {
            return reply.code(409).send(opts.errorPayload("UPLOAD_NOT_READY", "아직 검증되지 않은 업로드입니다.", traceId));
        }

        return {
            download_url: result.url,
            expires_in_sec: opts.localDownloadExpires,
            trace_id: traceId,
        };
    });

    app.delete(`${opts.apiPrefix}/uploads/:uploadId`, async (req, reply) => {
        if (!requireUser(req as any, reply)) return;

        const traceId = trace(req);
        const { uploadId } = req.params as any;

        const updated = await opts.db.query(
            `UPDATE uploads SET status='deleted', deleted_at=now() WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL RETURNING id`,
            [uploadId, (req as any).user.id]
        );

        if (!updated.rowCount) {
            return reply.code(404).send(opts.errorPayload("UPLOAD_NOT_FOUND", "업로드를 찾을 수 없습니다.", traceId));
        }

        return {
            ok: true,
            trace_id: traceId,
        };
    });
}