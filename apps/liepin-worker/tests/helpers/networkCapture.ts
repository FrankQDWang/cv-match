import { createHash } from "node:crypto";

import { EXTRACTOR_VERSION } from "../../src/extraction";
import { REDACTED_VALUE, type RedactionResult, redactFixturePayload } from "../../src/redaction";

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

type CaptureOptions = {
  postActionCaptureMs?: number;
};

const DEFAULT_POST_ACTION_CAPTURE_MS = 1000;

export type CapturedResponseRecord = {
  url: string;
  status: number;
  endpointFingerprint: string;
  responseShapeHash: string;
  extractorVersion: typeof EXTRACTOR_VERSION;
  extractionSource: "network";
  missingFields: string[];
  redactedFixture: RedactionResult;
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
  visibleAction: () => Promise<void>,
  options: CaptureOptions = {}
): Promise<CapturedResponseRecord[]> {
  const pending: Array<Promise<CapturedResponseRecord | null>> = [];
  const postActionCaptureMs = options.postActionCaptureMs ?? DEFAULT_POST_ACTION_CAPTURE_MS;

  const onResponse = (response: ResponseLike): void => {
    pending.push(candidateCaptureRecord(response));
  };

  page.on("response", onResponse);
  try {
    await visibleAction();
    if (postActionCaptureMs > 0) {
      await new Promise((resolve) => setTimeout(resolve, postActionCaptureMs));
    }
  } finally {
    page.off("response", onResponse);
  }

  const settled = await Promise.all(pending);
  return settled.filter((record): record is CapturedResponseRecord => record !== null);
}

export async function tokenizedCaptureRecord(response: ResponseLike): Promise<CapturedResponseRecord> {
  const body = await response.json();
  const method = response.request?.().method?.() ?? "GET";
  const rawUrl = response.url();
  const redactedFixture = redactFixturePayload(body);

  return {
    url: tokenizeAuthBearingUrl(rawUrl),
    status: response.status(),
    endpointFingerprint: endpointFingerprint(rawUrl, method),
    responseShapeHash: responseShapeHash(body),
    extractorVersion: EXTRACTOR_VERSION,
    extractionSource: "network",
    missingFields: missingFieldsForCandidatePayload(body),
    redactedFixture,
  };
}

async function candidateCaptureRecord(response: ResponseLike): Promise<CapturedResponseRecord | null> {
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return null;
  }

  if (!isCandidatePayload(body)) {
    return null;
  }

  const method = response.request?.().method?.() ?? "GET";
  const rawUrl = response.url();

  return {
    url: tokenizeAuthBearingUrl(rawUrl),
    status: response.status(),
    endpointFingerprint: endpointFingerprint(rawUrl, method),
    responseShapeHash: responseShapeHash(body),
    extractorVersion: EXTRACTOR_VERSION,
    extractionSource: "network",
    missingFields: missingFieldsForCandidatePayload(body),
    redactedFixture: redactFixturePayload(body),
  };
}

export function tokenizeAuthBearingUrl(rawUrl: string): string {
  try {
    const parsed = new URL(rawUrl);
    const query = [...parsed.searchParams.entries()]
      .map(([key]) => `${encodeURIComponent(key)}=${REDACTED_VALUE}`)
      .join("&");
    return `${parsed.origin}${parsed.pathname}${query ? `?${query}` : ""}`;
  } catch {
    return "invalid-url";
  }
}

export function endpointFingerprint(rawUrl: string, method = "GET"): string {
  try {
    const parsed = new URL(rawUrl);
    const stableQuery = [...parsed.searchParams.keys()]
      .filter((key) => !AUTH_QUERY_KEYS.has(key.toLowerCase()))
      .filter((key) => !VOLATILE_QUERY_KEYS.has(key.toLowerCase()))
      .sort()
      .map((key) => `${encodeURIComponent(key)}=${REDACTED_VALUE}`)
      .join("&");
    return `${method.toUpperCase()} ${parsed.host}${parsed.pathname}${stableQuery ? `?${stableQuery}` : ""}`;
  } catch {
    return `${method.toUpperCase()} invalid-url`;
  }
}

export function responseShapeHash(body: unknown): string {
  return createHash("sha256").update(JSON.stringify(shapeOf(body))).digest("hex");
}

function shapeOf(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.length === 0 ? [] : [mergeShapeValues(value.map(shapeOf))];
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

function mergeShapeValues(values: unknown[]): unknown {
  if (values.length === 0) {
    return {};
  }
  return values.reduce((merged, value) => mergeTwoShapeValues(merged, value));
}

function mergeTwoShapeValues(left: unknown, right: unknown): unknown {
  if (isPlainShapeObject(left) && isPlainShapeObject(right)) {
    const keys = [...new Set([...Object.keys(left), ...Object.keys(right)])].sort();
    return Object.fromEntries(
      keys.map((key) => {
        if (!(key in left)) {
          return [key, right[key]];
        }
        if (!(key in right)) {
          return [key, left[key]];
        }
        return [key, mergeTwoShapeValues(left[key], right[key])];
      })
    );
  }
  if (JSON.stringify(left) === JSON.stringify(right)) {
    return left;
  }
  return [left, right].sort((first, second) =>
    JSON.stringify(first).localeCompare(JSON.stringify(second))
  );
}

function isPlainShapeObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isCandidatePayload(value: unknown): boolean {
  return missingFieldsForCandidatePayload(value).length === 0;
}

function missingFieldsForCandidatePayload(value: unknown): string[] {
  const payload = value as { data?: { cards?: unknown; list?: unknown; detail?: unknown } };
  const data = payload && typeof payload === "object" ? payload.data : undefined;
  const hasCards = Array.isArray(data?.cards) || Array.isArray(data?.list);
  const hasDetail = Boolean(data?.detail && typeof data.detail === "object");
  return hasCards || hasDetail ? [] : ["data.cards_or_detail"];
}
