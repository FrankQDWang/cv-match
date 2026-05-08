import { describe, expect, it } from "bun:test";

import {
  captureResponsesDuringAction,
  endpointFingerprint,
  responseShapeHash,
  tokenizedCaptureRecord,
} from "../src/networkCapture";

class FakePage {
  readonly responseHandlers: Array<(response: FakeResponse) => void> = [];
  readonly attachedEvents: string[] = [];

  on(event: "response", handler: (response: FakeResponse) => void): void {
    this.attachedEvents.push(event);
    this.responseHandlers.push(handler);
  }

  off(event: "response", handler: (response: FakeResponse) => void): void {
    expect(event).toBe("response");
    const index = this.responseHandlers.indexOf(handler);
    if (index !== -1) {
      this.responseHandlers.splice(index, 1);
    }
  }

  emitResponse(response: FakeResponse): void {
    for (const handler of this.responseHandlers) {
      handler(response);
    }
  }
}

type FakeResponseOptions = {
  url: string;
  jsonBody: unknown;
  status?: number;
  jsonError?: Error;
};

class FakeResponse {
  private readonly responseUrl: string;
  private readonly jsonBody: unknown;
  private readonly responseStatus: number;
  private readonly jsonError: Error | undefined;

  constructor(options: FakeResponseOptions) {
    this.responseUrl = options.url;
    this.jsonBody = options.jsonBody;
    this.responseStatus = options.status ?? 200;
    this.jsonError = options.jsonError;
  }

  url(): string {
    return this.responseUrl;
  }

  status(): number {
    return this.responseStatus;
  }

  async json(): Promise<unknown> {
    if (this.jsonError) {
      throw this.jsonError;
    }
    return this.jsonBody;
  }
}

describe("passive network capture", () => {
  it("uses page response events and only keeps responses produced during a visible action", async () => {
    const page = new FakePage();

    const captured = await captureResponsesDuringAction(page, async () => {
      page.emitResponse(
        new FakeResponse({
          url: "https://www.liepin.com/api/cards?page=1&timestamp=111",
          jsonBody: { data: { list: [{ candidateId: "cand-redacted-1" }] } },
        })
      );
    });

    page.emitResponse(
      new FakeResponse({
        url: "https://www.liepin.com/api/cards?page=2&timestamp=222",
        jsonBody: { data: { list: [{ candidateId: "cand-redacted-2" }] } },
      })
    );

    expect(page.attachedEvents).toEqual(["response"]);
    expect(captured).toHaveLength(1);
    expect(captured[0]?.url).toContain("page=1");
    expect(page.responseHandlers).toHaveLength(0);
  });

  it("tokenizes auth-bearing URLs and never stores request or response headers", async () => {
    const record = await tokenizedCaptureRecord(
      new FakeResponse({
        url: "https://www.liepin.com/api/detail?candidateId=cand-redacted-1&token=secret&signature=abc&ts=999",
        jsonBody: { data: { candidateId: "cand-redacted-1", title: "Backend Engineer" } },
      })
    );

    expect(record.url).toBe(
      "https://www.liepin.com/api/detail?candidateId=cand-redacted-1&token=[REDACTED]&signature=[REDACTED]&ts=999"
    );
    expect(JSON.stringify(record)).not.toContain("secret");
    expect(JSON.stringify(record)).not.toContain("Authorization");
    expect(JSON.stringify(record)).not.toContain("Cookie");
  });

  it("writes artifact metadata and redacted fixture payloads without raw auth-like fields", async () => {
    const record = await tokenizedCaptureRecord(
      new FakeResponse({
        url: "https://www.liepin.com/api/cards?page=1&token=url-secret",
        jsonBody: {
          headers: {
            Authorization: "Bearer header-secret",
            Cookie: "session=cookie-secret",
          },
          token: "body-token-secret",
          data: {
            cards: [
              {
                candidateId: "cand-redacted-1",
                title: "Backend Engineer",
                email: "candidate@example.test",
              },
            ],
          },
        },
      })
    );

    expect(record).toMatchObject({
      extractorVersion: "liepin-passive-extractor-v1",
      extractionSource: "network",
      missingFields: [],
      redactedFixture: {
        manifest: {
          redaction_policy_version: "liepin-fixture-redaction-v1",
          redaction_passed: true,
          unsafe_reasons: [],
        },
      },
    });
    expect(record.redactedFixture.payload.headers).toBe("[REDACTED]");
    expect(record.redactedFixture.payload.token).toBe("[REDACTED]");
    expect(record.redactedFixture.payload.data.cards[0].email).toBe("[REDACTED]");

    const serialized = JSON.stringify(record);
    expect(serialized).not.toContain("url-secret");
    expect(serialized).not.toContain("header-secret");
    expect(serialized).not.toContain("cookie-secret");
    expect(serialized).not.toContain("body-token-secret");
    expect(serialized).not.toContain("candidate@example.test");
  });

  it("ignores non-json and unrelated json responses while keeping candidate payloads", async () => {
    const page = new FakePage();

    const captured = await captureResponsesDuringAction(page, async () => {
      page.emitResponse(
        new FakeResponse({
          url: "https://www.liepin.com/search",
          jsonBody: undefined,
          jsonError: new Error("not json"),
        })
      );
      page.emitResponse(
        new FakeResponse({
          url: "https://www.liepin.com/api/metrics",
          jsonBody: { ok: true, event: "page-view" },
        })
      );
      page.emitResponse(
        new FakeResponse({
          url: "https://www.liepin.com/api/cards?page=1",
          jsonBody: {
            data: {
              cards: [{ candidateId: "cand-redacted-1", title: "Backend Engineer" }],
            },
          },
        })
      );
    });

    expect(captured).toHaveLength(1);
    expect(captured[0]?.redactedFixture.payload.data.cards[0].candidateId).toBe(
      "cand-redacted-1"
    );
  });

  it("strips volatile query params from endpoint fingerprints", () => {
    expect(
      endpointFingerprint(
        "https://www.liepin.com/api/cards?page=3&timestamp=123456&signature=abc&nonce=n1&keyword=python"
      )
    ).toBe("GET www.liepin.com/api/cards?keyword=python&page=3");
  });

  it("builds stable response shape hashes from structure instead of volatile values", () => {
    const first = responseShapeHash({
      data: {
        list: [
          {
            candidateId: "cand-redacted-1",
            title: "Backend Engineer",
            updatedAt: 1710000000,
          },
        ],
      },
    });
    const second = responseShapeHash({
      data: {
        list: [
          {
            candidateId: "cand-redacted-2",
            title: "ML Engineer",
            updatedAt: 1720000000,
          },
        ],
      },
    });

    expect(first).toBe(second);
  });
});
