type ValidationIssue = {
  instancePath?: string;
  message?: string;
  keyword?: string;
  params?: Record<string, unknown>;
};

type ErrorDetails = {
  validation?: Array<{
    field: string;
    message: string;
    keyword?: string;
  }>;
};

export function errorPayload(code: string, message: string, traceId: string, details?: ErrorDetails) {
  return {
    error: {
      code,
      message,
      trace_id: traceId,
      ...(details ? { details } : {})
    }
  };
}

function validationField(issue: ValidationIssue, context?: string) {
  const missing = typeof issue.params?.missingProperty === "string" ? issue.params.missingProperty : "";
  const fromPath = issue.instancePath?.replace(/^\//, "").replace(/\//g, ".") ?? "";
  const field = fromPath || missing || context || "request";
  return context && !field.startsWith(`${context}.`) && field !== context ? `${context}.${field}` : field;
}

function validationMessage(issue: ValidationIssue) {
  if (issue.keyword === "required") return "필수 입력값입니다.";
  if (issue.keyword === "format") return "형식이 올바르지 않습니다.";
  if (issue.keyword === "minLength") return "입력값이 너무 짧습니다.";
  if (issue.keyword === "maxLength") return "입력값이 너무 깁니다.";
  if (issue.keyword === "minimum" || issue.keyword === "maximum") return "허용 범위를 벗어났습니다.";
  if (issue.keyword === "type") return "입력값의 타입이 올바르지 않습니다.";
  if (issue.keyword === "pattern") return "입력값 형식이 올바르지 않습니다.";
  return issue.message || "입력값을 확인해 주세요.";
}

export function validationErrorPayload(err: any, traceId: string) {
  const context = typeof err.validationContext === "string" ? err.validationContext : "body";
  const validation = Array.isArray(err.validation)
    ? err.validation.map((issue: ValidationIssue) => ({
        field: validationField(issue, context),
        message: validationMessage(issue),
        keyword: issue.keyword
      }))
    : [];

  return errorPayload("VALIDATION_ERROR", "입력값을 확인해 주세요.", traceId, { validation });
}

export function requestErrorPayload(err: any, traceId: string) {
  const code = typeof err.code === "string" && err.code ? err.code : "REQUEST_ERROR";
  const message = typeof err.message === "string" && err.message ? err.message : "요청을 처리할 수 없습니다.";
  return errorPayload(code, message, traceId);
}
