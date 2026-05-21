import { createHash } from "node:crypto";

const SENSITIVE_PATTERNS = [
  /\b\d{2,3}-\d{3,4}-\d{4}\b/g,
  /\b\d{6}-?[1-4]\d{6}\b/g,
  /\b\d{2,3}[°¡-ÆR]\s?\d{4}\b/g,
];

export function sha256(input: string) {
  return createHash("sha256").update(input).digest("hex");
}

export function maskSensitive(text: string) {
  let out = text;
  for (const re of SENSITIVE_PATTERNS) {
    out = out.replace(re, "[REDACTED]");
  }
  return out;
}
