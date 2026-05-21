import { createWriteStream } from "node:fs";
import { mkdir, stat } from "node:fs/promises";
import path from "node:path";
import { pipeline } from "node:stream/promises";

export type StoredObject = {
  provider: "local" | "s3";
  storagePath: string;
  publicPath?: string;
  sizeBytes: number;
};

export interface StorageProvider {
  putUpload(input: {
    caseId: string;
    uploadId: string;
    fileName: string;
    contentType: string;
    stream: NodeJS.ReadableStream;
  }): Promise<StoredObject>;
}

function safeExt(fileName: string) {
  const ext = path.extname(fileName || "").toLowerCase().replace(/[^a-z0-9.]/g, "");
  return ext && ext.length <= 12 ? ext : ".mp4";
}

export class LocalStorageProvider implements StorageProvider {
  constructor(private readonly rootDir: string) {}

  async putUpload(input: {
    caseId: string;
    uploadId: string;
    fileName: string;
    contentType: string;
    stream: NodeJS.ReadableStream;
  }): Promise<StoredObject> {
    if (!input.contentType.startsWith("video/")) {
      throw new Error("INVALID_CONTENT_TYPE");
    }

    const dir = path.join(this.rootDir, "uploads", input.caseId, input.uploadId);
    await mkdir(dir, { recursive: true });
    const storagePath = path.join(dir, `original${safeExt(input.fileName)}`);
    await pipeline(input.stream, createWriteStream(storagePath, { flags: "w" }));
    const info = await stat(storagePath);
    return {
      provider: "local",
      storagePath,
      publicPath: `/api/v1/uploads/${input.uploadId}/local-content`,
      sizeBytes: info.size
    };
  }
}

export class S3StorageProvider implements StorageProvider {
  async putUpload(): Promise<StoredObject> {
    throw new Error("S3_STORAGE_NOT_ENABLED");
  }
}
