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
};

class FakeResponse {
  private readonly responseUrl: string;
  private readonly jsonBody: unknown;
  private readonly responseStatus: number;

  constructor(options: FakeResponseOptions) {
    this.responseUrl = options.url;
    this.jsonBody = options.jsonBody;
    this.responseStatus = options.status ?? 200;
  }

  url(): string {
    return this.responseUrl;
  }

  status(): number {
    return this.responseStatus;
  }

  async json(): Promise<unknown> {
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
