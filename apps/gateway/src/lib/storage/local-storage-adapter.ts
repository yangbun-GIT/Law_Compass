import { createReadStream, createWriteStream } from "node:fs";
import { mkdir, rename, rm, stat, readdir, copyFile } from "node:fs/promises";
import { createHash, randomUUID } from "node:crypto";
import path from "node:path";
import { pipeline } from "node:stream/promises";
import type { Readable } from "node:stream";
import {
  isAllowedVideoUpload,
  makeUploadObjectKey,
  normalizeStorageKey,
  safePosixJoin,
  type PutMetadata,
  type StorageAdapter,
  type StoredObject,
  type UploadInput,
} from "./storage-adapter.js";

export class LocalStorageAdapter implements StorageAdapter {
  readonly driver = "local" as const;

  constructor(private readonly rootDir: string) {}

  normalizePath(inputPath: string): string {
    return normalizeStorageKey(inputPath);
  }

  safeJoin(...parts: string[]): string {
    const key = normalizeStorageKey(parts.join("/"));
    return path.join(this.rootDir, key);
  }

  async putUpload(input: UploadInput): Promise<StoredObject> {
    if (!isAllowedVideoUpload(input.fileName, input.contentType)) {
      throw new Error("INVALID_CONTENT_TYPE");
    }
    const tmpKey = makeUploadObjectKey({ ...input, tmp: true });
    const finalKey = makeUploadObjectKey(input);
    const tmpObject = await this.putStream(input.stream, tmpKey, {
      contentType: input.contentType,
      originalFilename: input.fileName,
    });
    await this.move(tmpKey, finalKey);
    return {
      ...tmpObject,
      provider: this.driver,
      driver: this.driver,
      storageProvider: this.driver,
      storageDriver: this.driver,
      storageKey: finalKey,
      storagePath: this.safeJoin(finalKey),
      tmpPath: tmpObject.storagePath,
    };
  }

  async putFile(localPath: string, destinationPath: string, metadata: PutMetadata = {}): Promise<StoredObject> {
    const key = normalizeStorageKey(destinationPath);
    const target = this.safeJoin(key);
    await mkdir(path.dirname(target), { recursive: true });
    await copyFile(localPath, target);
    const info = await stat(target);
    return {
      provider: this.driver,
      driver: this.driver,
      storageProvider: this.driver,
      storageDriver: this.driver,
      storageKey: key,
      storagePath: target,
      contentType: metadata.contentType,
      originalFilename: metadata.originalFilename,
      mimeType: metadata.contentType,
      sizeBytes: info.size,
      sha256: metadata.sha256,
    };
  }

  async putStream(readableStream: NodeJS.ReadableStream, destinationPath: string, metadata: PutMetadata = {}): Promise<StoredObject> {
    const key = normalizeStorageKey(destinationPath);
    const target = this.safeJoin(key);
    await mkdir(path.dirname(target), { recursive: true });
    const hash = createHash("sha256");
    let sizeBytes = 0;
    readableStream.on("data", (chunk: Buffer) => {
      hash.update(chunk);
      sizeBytes += chunk.length;
    });
    await pipeline(readableStream, createWriteStream(target, { flags: "w" }));
    return {
      provider: this.driver,
      driver: this.driver,
      storageProvider: this.driver,
      storageDriver: this.driver,
      storageKey: key,
      storagePath: target,
      contentType: metadata.contentType,
      originalFilename: metadata.originalFilename,
      mimeType: metadata.contentType,
      sizeBytes,
      sha256: hash.digest("hex"),
    };
  }

  async getFile(remotePath: string, localDestination: string): Promise<void> {
    await mkdir(path.dirname(localDestination), { recursive: true });
    await copyFile(this.safeJoin(remotePath), localDestination);
  }

  async getStream(remotePath: string): Promise<Readable> {
    return createReadStream(this.safeJoin(remotePath));
  }

  async exists(remotePath: string): Promise<boolean> {
    try {
      await stat(this.safeJoin(remotePath));
      return true;
    } catch {
      return false;
    }
  }

  async delete(remotePath: string): Promise<void> {
    await rm(this.safeJoin(remotePath), { force: true });
  }

  async move(sourcePath: string, destinationPath: string): Promise<void> {
    const source = this.safeJoin(sourcePath);
    const destination = this.safeJoin(destinationPath);
    await mkdir(path.dirname(destination), { recursive: true });
    await rename(source, destination);
  }

  async list(prefix: string): Promise<string[]> {
    const key = normalizeStorageKey(prefix);
    const dir = this.safeJoin(key);
    const entries = await readdir(dir, { recursive: true, withFileTypes: true });
    return entries
      .filter((entry) => entry.isFile())
      .map((entry) => normalizeStorageKey(path.posix.join(key, entry.name)));
  }

  async getPublicDownloadUrl(remotePath: string): Promise<string | null> {
    normalizeStorageKey(remotePath);
    return null;
  }

  async createDownloadToken(remotePath: string): Promise<string | null> {
    normalizeStorageKey(remotePath);
    return randomUUID();
  }
}

export { safePosixJoin };
