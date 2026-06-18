import { describe, expect, it } from "vitest";
import { createUploadAccessToken, verifyUploadAccessToken } from "../src/lib/upload-access-token.js";

const secret = "test-upload-access-secret-with-enough-length";

describe("upload access HMAC token", () => {
  it("verifies a short-lived upload viewing token", () => {
    const signed = createUploadAccessToken(secret, {
      uploadId: "upload-1",
      ownerUserId: "user-1",
      disposition: "inline",
      expiresInSec: 120,
      nowSec: 1000,
    });

    const verified = verifyUploadAccessToken(secret, signed.token, {
      uploadId: "upload-1",
      disposition: "inline",
      nowSec: 1050,
    });

    expect(verified.ok).toBe(true);
    if (verified.ok) {
      expect(verified.claims.owner_user_id).toBe("user-1");
      expect(verified.claims.exp).toBe(1120);
    }
  });

  it("rejects expired, mismatched, and tampered tokens", () => {
    const signed = createUploadAccessToken(secret, {
      uploadId: "upload-1",
      ownerUserId: "user-1",
      disposition: "inline",
      expiresInSec: 20,
      nowSec: 1000,
    });

    expect(verifyUploadAccessToken(secret, signed.token, { uploadId: "upload-1", disposition: "inline", nowSec: 1021 })).toEqual({
      ok: false,
      reason: "expired",
    });
    expect(verifyUploadAccessToken(secret, signed.token, { uploadId: "upload-2", disposition: "inline", nowSec: 1001 })).toEqual({
      ok: false,
      reason: "wrong_upload",
    });
    expect(verifyUploadAccessToken(secret, signed.token, { uploadId: "upload-1", disposition: "attachment", nowSec: 1001 })).toEqual({
      ok: false,
      reason: "wrong_disposition",
    });
    expect(verifyUploadAccessToken(secret, `${signed.token}x`, { uploadId: "upload-1", disposition: "inline", nowSec: 1001 })).toEqual({
      ok: false,
      reason: "bad_signature",
    });
  });
});
