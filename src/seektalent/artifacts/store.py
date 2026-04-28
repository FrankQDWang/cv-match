from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, TextIO

from ulid import ULID

from seektalent import __version__
from .models import (
    ArtifactKind,
    ArtifactManifest,
    ArtifactStatus,
    ChildArtifactRef,
    LogicalArtifactEntry,
    MANIFEST_FILENAME_BY_KIND,
    manifest_model_for_kind,
    parse_manifest,
)
from .registry import default_logical_artifacts, resolve_registered_descriptor

COLLECTION_ROOT_BY_KIND: dict[ArtifactKind, str] = {
    ArtifactKind.RUN: "runs",
    ArtifactKind.BENCHMARK: "benchmark-executions",
    ArtifactKind.REPLAY: "replays",
    ArtifactKind.DEBUG: "debug",
    ArtifactKind.IMPORT: "imports",
}


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(text)
        temp_name = handle.name
    os.replace(temp_name, path)


def safe_artifact_path(root: Path, relative_path: str | Path) -> Path:
    relative = Path(relative_path)
    if relative.is_absolute():
        raise ValueError(f"Artifact path escape blocked: {relative_path}")
    root_resolved = root.resolve()
    candidate = (root / relative).resolve(strict=False)
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"Artifact path escape blocked: {relative_path}") from exc
    return candidate


def _utc_now_z() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _producer_version() -> str:
    try:
        return package_version("seektalent")
    except PackageNotFoundError:
        return __version__


@dataclass
class ArtifactSession:
    store: ArtifactStore
    root: Path
    manifest: ArtifactManifest

    @property
    def artifact_id(self) -> str:
        return self.manifest.artifact_id

    @property
    def kind(self) -> ArtifactKind:
        return self.manifest.kind

    @property
    def manifest_path(self) -> Path:
        return self.root / MANIFEST_FILENAME_BY_KIND[self.kind]

    def resolve(self, descriptor: str, *, round_no: int | None = None) -> Path:
        entry = self._logical_entry(descriptor, round_no=round_no)
        return safe_artifact_path(self.root, entry.relative_path)

    def resolve_optional(self, descriptor: str, *, round_no: int | None = None) -> Path | None:
        entry = self.manifest.logical_artifacts.get(descriptor)
        if entry is not None:
            return safe_artifact_path(self.root, entry.relative_path)
        try:
            default_entry = resolve_registered_descriptor(descriptor, round_no=round_no)
        except KeyError:
            return None
        if default_entry is None:
            return None
        return safe_artifact_path(self.root, default_entry.relative_path)

    def resolve_many(
        self,
        descriptors: Mapping[str, object] | Iterable[str],
        *,
        round_no: int | None = None,
    ) -> dict[str, Path]:
        names = descriptors.keys() if isinstance(descriptors, Mapping) else descriptors
        return {descriptor: self.resolve(descriptor, round_no=round_no) for descriptor in names}

    def resolve_for_write(self, descriptor: str, *, round_no: int | None = None) -> Path:
        path = self.resolve(descriptor, round_no=round_no)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def write_json(self, descriptor: str, payload: Any, *, round_no: int | None = None) -> Path:
        path = self.resolve_for_write(descriptor, round_no=round_no)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def write_jsonl(self, descriptor: str, payloads: list[Any], *, round_no: int | None = None) -> Path:
        path = self.resolve_for_write(descriptor, round_no=round_no)
        lines = [json.dumps(payload, ensure_ascii=False, sort_keys=True) for payload in payloads]
        path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        return path

    def append_jsonl(self, descriptor: str, payload: Any, *, round_no: int | None = None) -> Path:
        path = self.resolve_for_write(descriptor, round_no=round_no)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
        return path

    def write_text(self, descriptor: str, text: str, *, round_no: int | None = None) -> Path:
        path = self.resolve_for_write(descriptor, round_no=round_no)
        path.write_text(text, encoding="utf-8")
        return path

    def open_text_stream(self, descriptor: str, *, round_no: int | None = None, mode: str = "a") -> TextIO:
        path = self.resolve_for_write(descriptor, round_no=round_no)
        return path.open(mode, encoding="utf-8")

    def register_path(self, descriptor: str, relative_path: str) -> Path:
        safe_artifact_path(self.root, relative_path)
        registered = self.manifest.logical_artifacts.get(descriptor)
        normalized_relative_path = Path(relative_path).as_posix()
        if registered is not None and registered.relative_path != normalized_relative_path:
            raise ValueError(f"Artifact descriptor already registered: {descriptor}")
        self.manifest.logical_artifacts[descriptor] = LogicalArtifactEntry(
            name=descriptor,
            relative_path=normalized_relative_path,
        )
        self._write_manifest()
        return self.resolve(descriptor)

    def _logical_entry(self, descriptor: str, *, round_no: int | None = None) -> LogicalArtifactEntry:
        entry = self.manifest.logical_artifacts.get(descriptor)
        if entry is not None:
            return entry
        default_entry = resolve_registered_descriptor(descriptor, round_no=round_no)
        if default_entry is None:
            raise KeyError(f"Unknown artifact descriptor: {descriptor}")
        return default_entry

    def _touch_runtime_files(self) -> None:
        for descriptor in ("runtime.trace_log", "runtime.events"):
            self.resolve_for_write(descriptor).touch(exist_ok=True)

    def _write_manifest(self) -> None:
        self.manifest.updated_at = _utc_now_z()
        payload = self.manifest.model_dump(mode="json")
        atomic_write_text(
            self.manifest_path,
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )


class ArtifactStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def collection_root(self, kind: ArtifactKind) -> Path:
        return self.root / COLLECTION_ROOT_BY_KIND[kind]

    def create_root(
        self,
        kind: ArtifactKind,
        *,
        child_artifacts: list[ChildArtifactRef] | None = None,
        failure_summary: str | None = None,
    ) -> ArtifactSession:
        artifact_id = str(ULID())
        artifact_root = self.collection_root(kind) / artifact_id
        artifact_root.mkdir(parents=True, exist_ok=False)
        now = _utc_now_z()
        manifest_model = manifest_model_for_kind(kind)
        manifest = manifest_model(
            artifact_id=artifact_id,
            status=ArtifactStatus.RUNNING,
            producer_version=_producer_version(),
            created_at=now,
            updated_at=now,
            logical_artifacts=default_logical_artifacts(),
            child_artifacts=list(child_artifacts or []),
            failure_summary=failure_summary,
        )
        session = ArtifactSession(store=self, root=artifact_root, manifest=manifest)
        session._write_manifest()
        session._touch_runtime_files()
        return session

    def open(self, root: Path | str) -> ArtifactSession:
        artifact_root = Path(root)
        manifest_paths = [
            artifact_root / filename
            for filename in MANIFEST_FILENAME_BY_KIND.values()
            if (artifact_root / filename).exists()
        ]
        if len(manifest_paths) != 1:
            raise ValueError(f"Expected exactly one artifact manifest in {artifact_root}.")
        manifest_payload = json.loads(manifest_paths[0].read_text(encoding="utf-8"))
        manifest = parse_manifest(manifest_payload)
        return ArtifactSession(store=self, root=artifact_root, manifest=manifest)
