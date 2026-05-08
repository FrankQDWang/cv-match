import { describe, expect, it } from "bun:test";

import {
  WORKER_CONTRACT_VERSION,
  type LiepinWorkerHealthResponse,
} from "../src/contracts";

describe("liepin worker harness", () => {
  it("loads the shared worker contracts", () => {
    const response: LiepinWorkerHealthResponse = {
      status: "ok",
      workerVersion: WORKER_CONTRACT_VERSION,
    };

    expect(response).toEqual({
      status: "ok",
      workerVersion: "liepin-worker-v1",
    });
  });
});
