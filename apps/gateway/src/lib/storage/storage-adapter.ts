import type { Readable } from "node:stream";
import path from "node:path";

export type StorageDriver = "local" | "s3" | "nas_sftp";

export type PutMetadata = {
  contentType?: string;
  originalFilename?: string;
  sizeBytes?: number;
  sha256?: string;
};

export type StoredObject = {
  provider: StorageDriver;
  driver: StorageDriver;
  storageProvider: StorageDriver;
  storageDriver: StorageDriver;
  storageKey: string;
  storagePath: string;
  tmpPath?: string;
  contentType?: string;
  originalFilename?: string;
  mimeType?: string;
  sizeBytes: number;
  sha256?: string;
};

export type UploadInput = {
  caseId: string;
  uploadId: string;
  fileName: string;
  contentType: string;
  stream: NodeJS.ReadableStream;
};

export interface StorageAdapter {
  readonly driver: StorageDriver;
  putFile(localPath: string, destinationPath: string, metadata?: PutMetadata): Promise<StoredObject>;
  putStream(readableStream: NodeJS.ReadableStream, destinationPath: string, metadata?: PutMetadata): Promise<StoredObject>;
  getFile(remotePath: string, localDestination: string): Promise<void>;
  getStream(remotePath: string): Promise<Readable>;
  exists(remotePath: string): Promise<boolean>;
  delete(remotePath: string): Promise<void>;
  move(sourcePath: string, destinationPath: string): Promise<void>;
  list(prefix: string): Promise<string[]>;
  getPublicDownloadUrl?(remotePath: string): Promise<string | null>;
  createDownloadToken?(remotePath: string): Promise<string | null>;
  normalizePath(inputPath: string): string;
  safeJoin(...parts: string[]): string;
  putUpload(input: UploadInput): Promise<StoredObject>;
}

export const VIDEO_EXTENSIONS = new Set([".mp4", ".mov", ".avi", ".mkv", ".webm"]);

export function safeExt(fileName: string): string {
  const ext = path.extname(fileName || "").toLowerCase().replace(/[^a-z0-9.]/g, "");
  return VIDEO_EXTENSIONS.has(ext) ? ext : ".mp4";
}

export function hasAllowedVideoExtension(fileName: string): boolean {
  const ext = path.extname(fileName || "").toLowerCase().replace(/[^a-z0-9.]/g, "");
  return VIDEO_EXTENSIONS.has(ext);
}

export function makeUploadObjectKey(input: { caseId: string; uploadId: string; fileName: string; tmp?: boolean }): string {
  const ext = safeExt(input.fileName);
  const suffix = input.tmp ? ".part" : "";
  return normalizeStorageKey(["uploads", input.tmp ? "tmp" : "original", input.caseId, input.uploadId, `original${ext}${suffix}`].join("/"));
}

export function makeFrameObjectKey(input: { caseId: string; uploadId: string; frameName: string }): string {
  return normalizeStorageKey(["processed", "frames", input.caseId, input.uploadId, input.frameName].join("/"));
}

export function normalizeStorageKey(value: string): string {
  const normalized = String(value || "").replace(/\\/g, "/").replace(/\/+/g, "/").replace(/^\/+/, "");
  if (!normalized || normalized.includes("\0")) {
    throw new Error("INVALID_STORAGE_PATH");
  }
  const parts = normalized.split("/");
  if (parts.some((part) => !part || part === "." || part === "..")) {
    throw new Error("INVALID_STORAGE_PATH");
  }
  return parts.join("/");
}

export function safePosixJoin(baseDir: string, key: string): string {
  const safeKey = normalizeStorageKey(key);
  const normalizedBase = String(baseDir || "").replace(/\\/g, "/").replace(/\/+$/, "");
  if (!normalizedBase.startsWith("/")) {
    throw new Error("INVALID_STORAGE_BASE");
  }
  return `${normalizedBase}/${safeKey}`;
}

export function isAllowedVideoUpload(fileName: string, contentType: string): boolean {
  return hasAllowedVideoExtension(fileName) && String(contentType || "").toLowerCase().startsWith("video/");
}
