import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { buildUploadInsert, publicUpload } from "../src/routes/uploads.js";
import { makeUploadObjectKey } from "../src/lib/storage/index.js";

describe("upload storage DB contract", () => {
  it("stores nas_sftp provider and driver while filling legacy S3 columns", () => {
    const insert = buildUploadInsert(
      {
        provider: "nas_sftp",
        driver: "nas_sftp",
        storageProvider: "nas_sftp",
        storageDriver: "nas_sftp",
        storageKey: "uploads/original/case-1/upload-1/original.mp4",
        storagePath: "/lawcompass/uploads/original/case-1/upload-1/original.mp4",
        sizeBytes: 12345,
        sha256: "abc123",
        mimeType: "video/mp4",
        originalFilename: "accident.mp4",
      },
      {
        uploadId: "upload-1",
        caseId: "case-1",
        ownerUserId: "user-1",
        fileName: "accident.mp4",
        contentType: "video/mp4",
      }
    );

    expect(insert.text).toContain("storage_provider");
    expect(insert.text).toContain("storage_driver");
    expect(insert.values[3]).toBe("nas-sftp");
    expect(insert.values[4]).toBe("uploads/original/case-1/upload-1/original.mp4");
    expect(insert.values[5]).toBe("accident.mp4");
    expect(insert.values[6]).toBe("video/mp4");
    expect(insert.values[7]).toBe(12345);
    expect(insert.values[11]).toBe("nas_sftp");
    expect(insert.values[12]).toBe("/lawcompass/uploads/original/case-1/upload-1/original.mp4");
    expect(insert.values[13]).toBe("nas_sftp");
    expect(insert.values[14]).toBe("uploads/original/case-1/upload-1/original.mp4");
    expect(insert.values[16]).toBe("abc123");
  });

  it("does not reuse placeholders across varchar and text compatibility columns", () => {
    const insert = buildUploadInsert(
      {
        storageDriver: "nas_sftp",
        storageKey: "uploads/original/case-1/upload-1/original.mp4",
        storagePath: "/lawcompass/uploads/original/case-1/upload-1/original.mp4",
        sizeBytes: 12345,
        sha256: "abc123",
        mimeType: "video/mp4",
        originalFilename: "accident.mp4",
      },
      {
        uploadId: "upload-1",
        caseId: "case-1",
        ownerUserId: "user-1",
        fileName: "accident.mp4",
        contentType: "video/mp4",
      }
    );

    expect(insert.text).toContain("$6::varchar");
    expect(insert.text).toContain("$18::text");
    expect(insert.text).toContain("$7::varchar");
    expect(insert.text).toContain("$19::text");
    expect(insert.text).toContain("$12::varchar");
    expect(insert.text).toContain("$14::text");
    expect(insert.text).not.toContain("storage_provider, storage_driver,\n           storage_key");
  });

  it("keeps upload keys unique per case and upload", () => {
    const first = makeUploadObjectKey({ caseId: "case-1", uploadId: "upload-1", fileName: "accident.mp4" });
    const second = makeUploadObjectKey({ caseId: "case-1", uploadId: "upload-2", fileName: "accident.mp4" });
    expect(first).not.toBe(second);
  });

  it("preserves local storage compatibility in insert helper", () => {
    const insert = buildUploadInsert(
      {
        storageDriver: "local",
        storageKey: "uploads/original/case-1/upload-1/original.mp4",
        storagePath: "/app/storage/uploads/original/case-1/upload-1/original.mp4",
        sizeBytes: 10,
        sha256: "hash",
        mimeType: "video/mp4",
      },
      {
        uploadId: "upload-1",
        caseId: "case-1",
        ownerUserId: "user-1",
        fileName: "accident.mp4",
        contentType: "video/mp4",
      }
    );
    expect(insert.values[3]).toBe("local");
    expect(insert.values[11]).toBe("local");
    expect(insert.values[13]).toBe("local");
  });

  it("does not expose NAS internals in user upload payloads", () => {
    const upload = publicUpload({
      id: "upload-1",
      storage_provider: "nas_sftp",
      storage_driver: "nas_sftp",
      storage_key: "uploads/original/case-1/upload-1/original.mp4",
      storage_path: "/lawcompass/uploads/original/case-1/upload-1/original.mp4",
      metadata: {
        storage_key: "uploads/original/case-1/upload-1/original.mp4",
        storage_driver: "nas_sftp",
        NAS_USER: "storage-user",
        NAS_PASSWORD: "secret",
      },
    });
    const text = JSON.stringify(upload);
    expect(text).not.toContain("NAS_PASSWORD");
    expect(text).not.toContain("storage-user");
    expect(text).not.toContain("nas_sftp");
    expect(text).not.toContain("/lawcompass");
    expect(text).not.toContain("uploads/original");
  });

  it("keeps migration columns aligned with upload insert columns", () => {
    const migration = readFileSync(new URL("../../../infra/postgres/migrations/015_uploads_storage_adapter_compat.sql", import.meta.url), "utf8");
    for (const column of ["storage_driver", "storage_key", "size_bytes", "sha256", "original_filename", "mime_type", "storage_status"]) {
      expect(migration).toContain(`ADD COLUMN IF NOT EXISTS ${column}`);
    }
  });
});
