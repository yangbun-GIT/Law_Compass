import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { Readable } from "node:stream";
import { describe, expect, it } from "vitest";
import { createStorageAdapter, makeUploadObjectKey, normalizeStorageKey } from "../src/lib/storage/index.js";
import { LocalStorageAdapter } from "../src/lib/storage/local-storage-adapter.js";

describe("storage adapter", () => {
  it("selects nas_sftp driver from storage factory", () => {
    const adapter = createStorageAdapter({
      STORAGE_DRIVER: "nas_sftp",
      NAS_HOST: "192.168.1.164",
      NAS_PORT: "22",
      NAS_USER: "lawcompass_storage",
      NAS_BASE_DIR: "/lawcompass",
    } as any);

    expect(adapter.driver).toBe("nas_sftp");
  });

  it("blocks path traversal in storage keys", () => {
    expect(() => normalizeStorageKey("../secret.mp4")).toThrow("INVALID_STORAGE_PATH");
    expect(() => normalizeStorageKey("uploads/original/case/../../secret.mp4")).toThrow("INVALID_STORAGE_PATH");
    expect(normalizeStorageKey("uploads\\original\\case\\upload\\original.mp4")).toBe("uploads/original/case/upload/original.mp4");
  });

  it("returns the final upload key after moving the temporary object", async () => {
    const root = await mkdtemp(path.join(tmpdir(), "lawcompass-storage-test-"));
    const adapter = new LocalStorageAdapter(root);
    const input = {
      caseId: "case-1",
      uploadId: "upload-1",
      fileName: "accident.mp4",
      contentType: "video/mp4",
      stream: Readable.from(Buffer.from("fake video bytes")),
    };

    try {
      const stored = await adapter.putUpload(input);
      const finalKey = makeUploadObjectKey(input);
      const tmpKey = makeUploadObjectKey({ ...input, tmp: true });

      expect(stored.storageKey).toBe(finalKey);
      expect(stored.storagePath).toBe(adapter.safeJoin(finalKey));
      expect(stored.tmpPath).toBe(adapter.safeJoin(tmpKey));
      expect(await adapter.exists(stored.storageKey)).toBe(true);
      expect(await adapter.exists(finalKey)).toBe(true);
      expect(await adapter.exists(tmpKey)).toBe(false);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });
});
