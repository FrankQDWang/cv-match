import { createHash } from "node:crypto";

import { REDACTED_VALUE } from "./redaction";

type ResponseLike = {
  url(): string;
  status(): number;
  json(): Promise<unknown>;
  request?: () => {
    method?: () => string;
  };
};

type PageLike = {
  on(event: "response", handler: (response: ResponseLike) => void): void;
  off(event: "response", handler: (response: ResponseLike) => void): void;
};

export type CapturedResponseRecord = {
  url: string;
  status: number;
  endpointFingerprint: string;
  responseShapeHash: string;
  body: unknown;
};

const AUTH_QUERY_KEYS = new Set([
  "access_token",
  "authorization",
  "auth",
  "cookie",
  "session",
  "sig",
  "signature",
  "token",
]);

const VOLATILE_QUERY_KEYS = new Set([
  "_",
  "_t",
  "callback",
  "nonce",
  "requestid",
  "sig",
  "signature",
  "t",
  "timestamp",
  "token",
  "traceid",
  "ts",
]);

export async function captureResponsesDuringAction(
  page: PageLike,
  visibleAction: () => Promise<void>
): Promise<CapturedResponseRecord[]> {
  const pending: Array<Promise<CapturedResponseRecord>> = [];

  const onResponse = (response: ResponseLike): void => {
    pending.push(tokenizedCaptureRecord(response));
  };

  page.on("response", onResponse);
  try {
    await visibleAction();
  } finally {
    page.off("response", onResponse);
  }

  return Promise.all(pending);
}

export async function tokenizedCaptureRecord(
  response: ResponseLike
): Promise<CapturedResponseRecord> {
  const body = await response.json();
  const method = response.request?.().method?.() ?? "GET";
  const rawUrl = response.url();

  return {
    url: tokenizeAuthBearingUrl(rawUrl),
    status: response.status(),
    endpointFingerprint: endpointFingerprint(rawUrl, method),
    responseShapeHash: responseShapeHash(body),
    body,
  };
}

export function tokenizeAuthBearingUrl(rawUrl: string): string {
  try {
    const parsed = new URL(rawUrl);
    const query = [...parsed.searchParams.entries()]
      .map(([key, value]) => {
        const safeValue = AUTH_QUERY_KEYS.has(key.toLowerCase()) ? REDACTED_VALUE : value;
        return `${encodeURIComponent(key)}=${safeValue}`;
      })
      .join("&");
    return `${parsed.origin}${parsed.pathname}${query ? `?${query}` : ""}${parsed.hash}`;
  } catch {
    return rawUrl;
  }
}

export function endpointFingerprint(rawUrl: string, method = "GET"): string {
  try {
    const parsed = new URL(rawUrl);
    const keptParams = [...parsed.searchParams.entries()]
      .filter(([key]) => {
        const normalizedKey = key.toLowerCase();
        return !VOLATILE_QUERY_KEYS.has(normalizedKey) && !AUTH_QUERY_KEYS.has(normalizedKey);
      })
      .sort(([left], [right]) => left.localeCompare(right));
    const query = new URLSearchParams(keptParams).toString();
    const path = `${parsed.host}${parsed.pathname}`;

    return `${method.toUpperCase()} ${query ? `${path}?${query}` : path}`;
  } catch {
    const [path = rawUrl] = rawUrl.split("?");
    return `${method.toUpperCase()} ${path}`;
  }
}

export function responseShapeHash(payload: unknown): string {
  return createHash("sha256").update(JSON.stringify(shapeOf(payload))).digest("hex");
}

function shapeOf(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.length === 0 ? [] : [shapeOf(value[0])];
  }

  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, entry]) => [key, shapeOf(entry)])
    );
  }

  return typeof value;
}
