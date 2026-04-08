from __future__ import annotations

from typing import Never

from seektalent.config import AppSettings

RUNTIME_PHASE_GATE_MESSAGE = (
    "SeekTalent v0.3 ships a bootstrap core, but the full runtime loop is not available yet. "
    "run remains gated until search execution and ranking land."
)


class RuntimePhaseGateError(RuntimeError):
    pass


class WorkflowRuntime:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def run(self, *, job_description: str, hiring_notes: str = "") -> Never:
        del job_description, hiring_notes
        raise RuntimePhaseGateError(RUNTIME_PHASE_GATE_MESSAGE)

    async def run_async(self, *, job_description: str, hiring_notes: str = "") -> Never:
        del job_description, hiring_notes
        raise RuntimePhaseGateError(RUNTIME_PHASE_GATE_MESSAGE)
