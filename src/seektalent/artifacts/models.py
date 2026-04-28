from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ArtifactKind(StrEnum):
    RUN = "run"
    BENCHMARK = "benchmark"
    REPLAY = "replay"
    DEBUG = "debug"
    IMPORT = "import"


class ArtifactStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ChildArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ArtifactKind
    artifact_id: str = Field(min_length=1)
    relationship: str | None = None


class LogicalArtifactEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    relative_path: str = Field(min_length=1)


class ArtifactManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(min_length=1)
    kind: ArtifactKind
    status: ArtifactStatus = ArtifactStatus.RUNNING
    layout_version: int = 1
    producer: str = "seektalent"
    producer_version: str = Field(min_length=1)
    created_at: str = Field(min_length=1)
    updated_at: str = Field(min_length=1)
    logical_artifacts: dict[str, LogicalArtifactEntry] = Field(default_factory=dict)
    child_artifacts: list[ChildArtifactRef] = Field(default_factory=list)
    failure_summary: str | None = None


class RunArtifactManifest(ArtifactManifest):
    kind: Literal[ArtifactKind.RUN] = ArtifactKind.RUN


class BenchmarkArtifactManifest(ArtifactManifest):
    kind: Literal[ArtifactKind.BENCHMARK] = ArtifactKind.BENCHMARK


class ReplayArtifactManifest(ArtifactManifest):
    kind: Literal[ArtifactKind.REPLAY] = ArtifactKind.REPLAY


class DebugArtifactManifest(ArtifactManifest):
    kind: Literal[ArtifactKind.DEBUG] = ArtifactKind.DEBUG


class ImportArtifactManifest(ArtifactManifest):
    kind: Literal[ArtifactKind.IMPORT] = ArtifactKind.IMPORT


MANIFEST_FILENAME_BY_KIND: dict[ArtifactKind, str] = {
    ArtifactKind.RUN: "run.manifest.json",
    ArtifactKind.BENCHMARK: "benchmark.manifest.json",
    ArtifactKind.REPLAY: "replay.manifest.json",
    ArtifactKind.DEBUG: "debug.manifest.json",
    ArtifactKind.IMPORT: "import.manifest.json",
}

MANIFEST_MODEL_BY_KIND = {
    ArtifactKind.RUN: RunArtifactManifest,
    ArtifactKind.BENCHMARK: BenchmarkArtifactManifest,
    ArtifactKind.REPLAY: ReplayArtifactManifest,
    ArtifactKind.DEBUG: DebugArtifactManifest,
    ArtifactKind.IMPORT: ImportArtifactManifest,
}


def manifest_model_for_kind(kind: ArtifactKind) -> type[ArtifactManifest]:
    return MANIFEST_MODEL_BY_KIND[kind]


def parse_manifest(payload: object) -> ArtifactManifest:
    if not isinstance(payload, dict):
        raise TypeError("Artifact manifest payload must be a JSON object.")
    kind = ArtifactKind(payload["kind"])
    model = manifest_model_for_kind(kind)
    return model.model_validate(payload)
