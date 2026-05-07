import { describe, expect, it } from "bun:test";

import {
  WORKER_CONTRACT_VERSION,
  type LiepinWorkerHealthResponse,
} from "../src/contracts";

describe("liepin worker harness", () => {
  it("loads the shared worker contracts", () => {
    const response: LiepinWorkerHealthResponse = {
      ok: true,
      contractVersion: WORKER_CONTRACT_VERSION,
    };

    expect(response).toEqual({
      ok: true,
      contractVersion: "liepin-worker-v1",
    });
  });
});
