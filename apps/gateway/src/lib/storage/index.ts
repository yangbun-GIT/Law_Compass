import os from "node:os";
import { LocalStorageAdapter } from "./local-storage-adapter.js";
import { NasSftpStorageAdapter } from "./nas-sftp-storage-adapter.js";
import { S3StorageAdapter } from "./s3-storage-adapter.js";
import type { StorageAdapter, StorageDriver } from "./storage-adapter.js";

export function createStorageAdapter(env: NodeJS.ProcessEnv = process.env): StorageAdapter {
  const driver = normalizeStorageDriver(env.STORAGE_DRIVER ?? env.STORAGE_PROVIDER ?? "local");
  if (driver === "nas_sftp") {
    return new NasSftpStorageAdapter({
      host: env.NAS_HOST ?? "",
      port: Number(env.NAS_PORT ?? 22),
      username: env.NAS_USER ?? "",
      password: env.NAS_PASSWORD || undefined,
      privateKeyPath: env.NAS_PRIVATE_KEY_PATH || undefined,
      privateKeyPassphrase: env.NAS_PRIVATE_KEY_PASSPHRASE || undefined,
      baseDir: env.NAS_BASE_DIR ?? "/lawcompass",
      tmpDir: env.LOCAL_VIDEO_CACHE_DIR ?? os.tmpdir(),
    });
  }
  if (driver === "s3") {
    return new S3StorageAdapter();
  }
  return new LocalStorageAdapter(env.LOCAL_STORAGE_ROOT ?? "/app/storage");
}

export function normalizeStorageDriver(value: string): StorageDriver {
  const driver = String(value || "").trim().toLowerCase();
  if (driver === "nas_sftp") return "nas_sftp";
  if (driver === "s3") return "s3";
  return "local";
}

export type { StorageAdapter, StorageDriver, StoredObject, UploadInput } from "./storage-adapter.js";
export { normalizeStorageKey, safePosixJoin, makeFrameObjectKey, makeUploadObjectKey } from "./storage-adapter.js";
