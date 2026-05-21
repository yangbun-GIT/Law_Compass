import { randomUUID } from "node:crypto";

export type AgentCallOptions = {
  baseUrl: string;
  internalToken: string;
  timeoutMs: number;
  retryCount: number;
};

export async function callInternalAgent(path: string, payload: unknown, traceId: string, opts: AgentCallOptions) {
  for (let attempt = 0; attempt <= opts.retryCount; attempt += 1) {
    try {
      const ctl = new AbortController();
      const timer = setTimeout(() => ctl.abort(), opts.timeoutMs + attempt * 1500);
      const res = await fetch(`${opts.baseUrl}${path}`, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-internal-token": opts.internalToken,
          "x-correlation-id": traceId || randomUUID()
        },
        body: JSON.stringify(payload),
        signal: ctl.signal
      });
      clearTimeout(timer);

      if (res.ok) return await res.json();
      const bodyText = await res.text().catch(() => "");
      if (res.status >= 500 && attempt < opts.retryCount) continue;
      throw new Error(`internal_agent_error_${res.status}:${bodyText.slice(0, 300)}`);
    } catch (err) {
      if (attempt === opts.retryCount) throw err;
    }
  }
}
