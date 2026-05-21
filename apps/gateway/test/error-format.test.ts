import { describe, it, expect } from "vitest";
import { errorPayload, requestErrorPayload, validationErrorPayload } from "../src/lib/errors.js";

describe("error format", () => {
  it("should have code/message/trace_id fields", () => {
    const payload = errorPayload("CASE_NOT_FOUND", "케이스를 찾을 수 없습니다.", "abc");
    expect(payload.error.code).toBeTruthy();
    expect(payload.error.message).toBeTruthy();
    expect(payload.error.trace_id).toBeTruthy();
  });

  it("should normalize Fastify validation errors as 400-safe payloads", () => {
    const payload = validationErrorPayload({
      validationContext: "body",
      validation: [
        { instancePath: "/email", keyword: "format", message: "must match format \"email\"" },
        { instancePath: "", keyword: "required", params: { missingProperty: "password" }, message: "must have required property 'password'" }
      ]
    }, "trace-1");

    expect(payload.error.code).toBe("VALIDATION_ERROR");
    expect(payload.error.message).toBe("입력값을 확인해 주세요.");
    expect(payload.error.trace_id).toBe("trace-1");
    expect(payload.error.details?.validation?.[0]).toEqual({ field: "body.email", message: "형식이 올바르지 않습니다.", keyword: "format" });
    expect(payload.error.details?.validation?.[1]).toEqual({ field: "body.password", message: "필수 입력값입니다.", keyword: "required" });
  });

  it("should keep client errors in the standard envelope", () => {
    const payload = requestErrorPayload({ code: "FST_ERR_CTP_EMPTY_JSON_BODY", message: "Body cannot be empty" }, "trace-2");
    expect(payload.error).toEqual({
      code: "FST_ERR_CTP_EMPTY_JSON_BODY",
      message: "Body cannot be empty",
      trace_id: "trace-2"
    });
  });
});
