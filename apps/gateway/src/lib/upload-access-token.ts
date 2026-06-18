import { createHmac, timingSafeEqual } from "node:crypto";

export type UploadAccessDisposition = "inline" | "attachment";

export type UploadAccessTokenClaims = {
  v: "v1";
  upload_id: string;
  owner_user_id: string;
  disposition: UploadAccessDisposition;
  iat: number;
  exp: number;
};

export type UploadAccessTokenVerification =
  | { ok: true; claims: UploadAccessTokenClaims }
  | { ok: false; reason: "missing" | "malformed" | "bad_signature" | "expired" | "wrong_upload" | "wrong_disposition" };

function encodeJson(value: unknown) {
  return Buffer.from(JSON.stringify(value), "utf8").toString("base64url");
}

function decodeJson(value: string): unknown {
  return JSON.parse(Buffer.from(value, "base64url").toString("utf8"));
}

function signature(secret: string, payload: string) {
  return createHmac("sha256", secret).update(payload).digest("base64url");
}

function secureEqual(left: string, right: string) {
  try {
    const leftBuffer = Buffer.from(left, "base64url");
    const rightBuffer = Buffer.from(right, "base64url");
    return leftBuffer.length === rightBuffer.length && timingSafeEqual(leftBuffer, rightBuffer);
  } catch {
    return false;
  }
}

function normalizeTtl(seconds: number) {
  const value = Number.isFinite(seconds) ? Math.floor(seconds) : 60;
  return Math.max(15, Math.min(value, 3600));
}

export function createUploadAccessToken(
  secret: string,
  input: {
    uploadId: string;
    ownerUserId: string;
    disposition: UploadAccessDisposition;
    expiresInSec: number;
    nowSec?: number;
  }
) {
  const now = input.nowSec ?? Math.floor(Date.now() / 1000);
  const ttl = normalizeTtl(input.expiresInSec);
  const claims: UploadAccessTokenClaims = {
    v: "v1",
    upload_id: input.uploadId,
    owner_user_id: input.ownerUserId,
    disposition: input.disposition,
    iat: now,
    exp: now + ttl,
  };
  const payload = encodeJson(claims);
  return {
    token: `${payload}.${signature(secret, payload)}`,
    claims,
    expiresInSec: ttl,
    expiresAt: new Date((now + ttl) * 1000).toISOString(),
  };
}

export function verifyUploadAccessToken(
  secret: string,
  token: string | undefined,
  expected: { uploadId: string; disposition: UploadAccessDisposition; nowSec?: number }
): UploadAccessTokenVerification {
  if (!token) return { ok: false, reason: "missing" };
  const parts = token.split(".");
  if (parts.length !== 2 || !parts[0] || !parts[1]) return { ok: false, reason: "malformed" };

  const [payload, providedSignature] = parts;
  if (!secureEqual(signature(secret, payload), providedSignature)) {
    return { ok: false, reason: "bad_signature" };
  }

  let claims: UploadAccessTokenClaims;
  try {
    const decoded = decodeJson(payload) as Partial<UploadAccessTokenClaims>;
    if (
      decoded.v !== "v1" ||
      typeof decoded.upload_id !== "string" ||
      typeof decoded.owner_user_id !== "string" ||
      (decoded.disposition !== "inline" && decoded.disposition !== "attachment") ||
      typeof decoded.exp !== "number"
    ) {
      return { ok: false, reason: "malformed" };
    }
    claims = decoded as UploadAccessTokenClaims;
  } catch {
    return { ok: false, reason: "malformed" };
  }

  if (claims.upload_id !== expected.uploadId) return { ok: false, reason: "wrong_upload" };
  if (claims.disposition !== expected.disposition) return { ok: false, reason: "wrong_disposition" };
  if (claims.exp < (expected.nowSec ?? Math.floor(Date.now() / 1000))) return { ok: false, reason: "expired" };

  return { ok: true, claims };
}
