import type { Readable } from "node:stream";
import {
  normalizeStorageKey,
  type PutMetadata,
  type StorageAdapter,
  type StoredObject,
  type UploadInput,
} from "./storage-adapter.js";

export class S3StorageAdapter implements StorageAdapter {
  readonly driver = "s3" as const;

  normalizePath(inputPath: string): string {
    return normalizeStorageKey(inputPath);
  }

  safeJoin(...parts: string[]): string {
    return normalizeStorageKey(parts.join("/"));
  }

  async putUpload(_input: UploadInput): Promise<StoredObject> {
    throw new Error("S3_STORAGE_NOT_ENABLED");
  }

  async putFile(_localPath: string, _destinationPath: string, _metadata?: PutMetadata): Promise<StoredObject> {
    throw new Error("S3_STORAGE_NOT_ENABLED");
  }

  async putStream(_readableStream: NodeJS.ReadableStream, _destinationPath: string, _metadata?: PutMetadata): Promise<StoredObject> {
    throw new Error("S3_STORAGE_NOT_ENABLED");
  }

  async getFile(_remotePath: string, _localDestination: string): Promise<void> {
    throw new Error("S3_STORAGE_NOT_ENABLED");
  }

  async getStream(_remotePath: string): Promise<Readable> {
    throw new Error("S3_STORAGE_NOT_ENABLED");
  }

  async exists(_remotePath: string): Promise<boolean> {
    throw new Error("S3_STORAGE_NOT_ENABLED");
  }

  async delete(_remotePath: string): Promise<void> {
    throw new Error("S3_STORAGE_NOT_ENABLED");
  }

  async move(_sourcePath: string, _destinationPath: string): Promise<void> {
    throw new Error("S3_STORAGE_NOT_ENABLED");
  }

  async list(_prefix: string): Promise<string[]> {
    throw new Error("S3_STORAGE_NOT_ENABLED");
  }
}

