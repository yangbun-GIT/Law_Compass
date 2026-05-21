import { describe, it, expect } from "vitest";

describe("error format", () => {
  it("should have code/message/trace_id fields", () => {
    const payload = {
      error: {
        code: "CASE_NOT_FOUND",
        message: "케이스를 찾을 수 없습니다.",
        trace_id: "abc"
      }
    };
    expect(payload.error.code).toBeTruthy();
    expect(payload.error.message).toBeTruthy();
    expect(payload.error.trace_id).toBeTruthy();
  });
});

