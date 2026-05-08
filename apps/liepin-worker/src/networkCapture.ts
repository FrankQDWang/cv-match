import { createHash } from "node:crypto";

import { EXTRACTOR_VERSION } from "./extraction";
import { REDACTED_VALUE, type RedactionResult, redactFixturePayload } from "./redaction";

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
  visibleAction: () => Promise<void>
): Promise<CapturedResponseRecord[]> {
  const pending: Array<Promise<CapturedResponseRecord | null>> = [];

  const onResponse = (response: ResponseLike): void => {
    pending.push(candidateCaptureRecord(response));
  };

  page.on("response", onResponse);
  try {
    await visibleAction();
  } finally {
    page.off("response", onResponse);
  }

  const settled = await Promise.all(pending);
  return settled.filter((record): record is CapturedResponseRecord => record !== null);
}

export async function tokenizedCaptureRecord(
  response: ResponseLike
): Promise<CapturedResponseRecord> {
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

function isCandidatePayload(payload: unknown): boolean {
  if (payload === null || typeof payload !== "object") {
    return false;
  }

  const data = objectValue(payload, "data");
  const cards = data ? arrayValue(data, "cards") ?? arrayValue(data, "list") : undefined;
  if (cards !== undefined) {
    return cards.some((card) => stringProperty(card, "candidateId").length > 0);
  }

  const detail = data ? objectValue(data, "detail") : undefined;
  return detail !== undefined && stringProperty(detail, "candidateId").length > 0;
}

function missingFieldsForCandidatePayload(payload: unknown): string[] {
  const missing = new Set<string>();
  const data = objectValue(payload, "data");
  const cards = data ? arrayValue(data, "cards") ?? arrayValue(data, "list") : undefined;
  const detail = data ? objectValue(data, "detail") : undefined;

  if (cards !== undefined) {
    for (const card of cards) {
      addMissingCandidateFields(card, missing);
    }
  } else if (detail !== undefined) {
    addMissingCandidateFields(detail, missing);
    if (stringProperty(detail, "detailId").length === 0) {
      missing.add("detailId");
    }
  }

  return [...missing].sort();
}

function addMissingCandidateFields(value: unknown, missing: Set<string>): void {
  if (stringProperty(value, "candidateId").length === 0) {
    missing.add("candidateId");
  }
  if (stringProperty(value, "title").length === 0) {
    missing.add("title");
  }
}

function objectValue(value: unknown, key: string): Record<string, unknown> | undefined {
  if (value === null || typeof value !== "object") {
    return undefined;
  }

  const entry = (value as Record<string, unknown>)[key];
  return entry !== null && typeof entry === "object" && !Array.isArray(entry)
    ? (entry as Record<string, unknown>)
    : undefined;
}

function arrayValue(value: unknown, key: string): unknown[] | undefined {
  if (value === null || typeof value !== "object") {
    return undefined;
  }

  const entry = (value as Record<string, unknown>)[key];
  return Array.isArray(entry) ? entry : undefined;
}

function stringProperty(value: unknown, key: string): string {
  if (value === null || typeof value !== "object") {
    return "";
  }

  const entry = (value as Record<string, unknown>)[key];
  return typeof entry === "string" ? entry.trim() : "";
}
