import { createReadStream, createWriteStream } from "node:fs";
import { mkdir, readFile, rm, stat } from "node:fs/promises";
import { createHash, randomUUID } from "node:crypto";
import os from "node:os";
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

type SftpClient = any;

export type NasSftpConfig = {
  host: string;
  port: number;
  username: string;
  password?: string;
  privateKeyPath?: string;
  privateKeyPassphrase?: string;
  baseDir: string;
  tmpDir?: string;
};

export class NasSftpStorageAdapter implements StorageAdapter {
  readonly driver = "nas_sftp" as const;

  constructor(private readonly config: NasSftpConfig) {}

  normalizePath(inputPath: string): string {
    return normalizeStorageKey(inputPath);
  }

  safeJoin(...parts: string[]): string {
    return safePosixJoin(this.config.baseDir, normalizeStorageKey(parts.join("/")));
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
      };
  }

  async putFile(localPath: string, destinationPath: string, metadata: PutMetadata = {}): Promise<StoredObject> {
    const key = normalizeStorageKey(destinationPath);
    const remotePath = this.safeJoin(key);
    const info = await stat(localPath);
    const sha256 = metadata.sha256 ?? await sha256File(localPath);
    await this.withClient(async (client) => {
      await ensureRemoteDir(client, remotePath);
      await client.fastPut(localPath, remotePath);
    });
    return {
      provider: this.driver,
      driver: this.driver,
      storageProvider: this.driver,
      storageDriver: this.driver,
      storageKey: key,
      storagePath: remotePath,
      contentType: metadata.contentType,
      originalFilename: metadata.originalFilename,
      mimeType: metadata.contentType,
      sizeBytes: info.size,
      sha256,
    };
  }

  async putStream(readableStream: NodeJS.ReadableStream, destinationPath: string, metadata: PutMetadata = {}): Promise<StoredObject> {
    const localTmp = path.join(this.config.tmpDir || os.tmpdir(), `lawcompass-upload-${randomUUID()}.part`);
    await mkdir(path.dirname(localTmp), { recursive: true });
    const hash = createHash("sha256");
    let sizeBytes = 0;
    readableStream.on("data", (chunk: Buffer) => {
      hash.update(chunk);
      sizeBytes += chunk.length;
    });
    await pipeline(readableStream, createWriteStream(localTmp, { flags: "w" }));
    try {
      return await this.putFile(localTmp, destinationPath, {
        ...metadata,
        sizeBytes,
        sha256: hash.digest("hex"),
      });
    } finally {
      await rm(localTmp, { force: true });
    }
  }

  async getFile(remotePath: string, localDestination: string): Promise<void> {
    const remote = this.safeJoin(remotePath);
    await mkdir(path.dirname(localDestination), { recursive: true });
    await this.withClient(async (client) => {
      await client.fastGet(remote, localDestination);
    });
  }

  async getStream(remotePath: string): Promise<Readable> {
    const localTmp = path.join(this.config.tmpDir || os.tmpdir(), `lawcompass-download-${randomUUID()}`);
    await this.getFile(remotePath, localTmp);
    const stream = createReadStream(localTmp);
    stream.on("close", () => {
      void rm(localTmp, { force: true });
    });
    return stream;
  }

  async exists(remotePath: string): Promise<boolean> {
    const remote = this.safeJoin(remotePath);
    return this.withClient(async (client) => Boolean(await client.exists(remote)));
  }

  async delete(remotePath: string): Promise<void> {
    const remote = this.safeJoin(remotePath);
    await this.withClient(async (client) => {
      if (await client.exists(remote)) {
        await client.delete(remote);
      }
    });
  }

  async move(sourcePath: string, destinationPath: string): Promise<void> {
    const source = this.safeJoin(sourcePath);
    const destination = this.safeJoin(destinationPath);
    await this.withClient(async (client) => {
      await ensureRemoteDir(client, destination);
      await client.rename(source, destination);
    });
  }

  async list(prefix: string): Promise<string[]> {
    const key = normalizeStorageKey(prefix);
    const remote = this.safeJoin(key);
    return this.withClient(async (client) => {
      const entries = await client.list(remote);
      return entries.map((entry: any) => normalizeStorageKey(`${key}/${entry.name}`));
    });
  }

  async getPublicDownloadUrl(remotePath: string): Promise<string | null> {
    normalizeStorageKey(remotePath);
    return null;
  }

  async createDownloadToken(remotePath: string): Promise<string | null> {
    normalizeStorageKey(remotePath);
    return randomUUID();
  }

  private async withClient<T>(fn: (client: SftpClient) => Promise<T>): Promise<T> {
    const client = await createSftpClient();
    try {
      await client.connect(await this.connectionOptions());
      return await fn(client);
    } finally {
      try {
        await client.end();
      } catch {
        // Connection cleanup failure must not leak NAS details to callers.
      }
    }
  }

  private async connectionOptions(): Promise<Record<string, unknown>> {
    const options: Record<string, unknown> = {
      host: this.config.host,
      port: this.config.port,
      username: this.config.username,
      readyTimeout: 15_000,
    };
    if (this.config.privateKeyPath) {
      options.privateKey = await readFile(this.config.privateKeyPath, "utf8");
      if (this.config.privateKeyPassphrase) {
        options.passphrase = this.config.privateKeyPassphrase;
      }
    } else if (this.config.password) {
      options.password = this.config.password;
    }
    return options;
  }
}

async function createSftpClient(): Promise<SftpClient> {
  const packageName = "ssh2-sftp-client";
  const mod = await import(packageName);
  const Client = (mod as any).default ?? mod;
  return new Client("lawcompass-nas-sftp");
}

async function ensureRemoteDir(client: SftpClient, remotePath: string): Promise<void> {
  const dir = remotePath.split("/").slice(0, -1).join("/");
  await client.mkdir(dir, true);
}

async function sha256File(localPath: string): Promise<string> {
  const hash = createHash("sha256");
  for await (const chunk of createReadStream(localPath)) {
    hash.update(chunk as Buffer);
  }
  return hash.digest("hex");
}
