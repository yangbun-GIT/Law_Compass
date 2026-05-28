import { describe, expect, it } from "vitest";
import { createStorageAdapter, normalizeStorageKey } from "../src/lib/storage/index.js";

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
});
