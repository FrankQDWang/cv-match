export const WORKER_CONTRACT_VERSION = "liepin-worker-v1" as const;

export type WorkerContractVersion = typeof WORKER_CONTRACT_VERSION;

export type LiepinWorkerHealthResponse = {
  status: "ok";
  workerVersion: WorkerContractVersion;
};
