from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from seektalent import __version__
from seektalent.artifacts import ArtifactKind, ArtifactStore, ChildArtifactRef, MANIFEST_FILENAME_BY_KIND

ULID_PATTERN = re.compile(r"^[0123456789ABCDEFGHJKMNPQRSTVWXYZ]{26}$")


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("kind", "collection_name", "manifest_name"),
    [
        (ArtifactKind.RUN, "runs", MANIFEST_FILENAME_BY_KIND[ArtifactKind.RUN]),
        (ArtifactKind.BENCHMARK, "benchmark-executions", MANIFEST_FILENAME_BY_KIND[ArtifactKind.BENCHMARK]),
        (ArtifactKind.REPLAY, "replays", MANIFEST_FILENAME_BY_KIND[ArtifactKind.REPLAY]),
        (ArtifactKind.DEBUG, "debug", MANIFEST_FILENAME_BY_KIND[ArtifactKind.DEBUG]),
        (ArtifactKind.IMPORT, "imports", MANIFEST_FILENAME_BY_KIND[ArtifactKind.IMPORT]),
    ],
)
def test_create_root_uses_kind_specific_collection_roots_and_manifest_names(
    tmp_path: Path,
    kind: ArtifactKind,
    collection_name: str,
    manifest_name: str,
) -> None:
    store = ArtifactStore(tmp_path)

    session = store.create_root(kind)

    assert session.root.parent == tmp_path / collection_name
    assert store.collection_root(kind) == tmp_path / collection_name
    assert session.manifest_path == session.root / manifest_name
    assert session.manifest_path.exists()


def test_create_root_writes_running_manifest_and_runtime_files(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)

    session = store.create_root(ArtifactKind.RUN)
    manifest = _read_json(session.manifest_path)

    assert manifest["artifact_id"] == session.artifact_id
    assert manifest["kind"] == "run"
    assert manifest["status"] == "running"
    assert manifest["producer_version"] == __version__
    assert str(manifest["created_at"]).endswith("Z")
    assert str(manifest["updated_at"]).endswith("Z")
    assert (session.root / "trace.log").exists()
    assert (session.root / "events.jsonl").exists()
    assert session.resolve("runtime.trace_log") == session.root / "trace.log"
    assert session.resolve("runtime.events") == session.root / "events.jsonl"


def test_artifact_ids_are_ulid_shaped(tmp_path: Path) -> None:
    session = ArtifactStore(tmp_path).create_root(ArtifactKind.RUN)

    assert ULID_PATTERN.fullmatch(session.artifact_id)


def test_write_json_and_resolve_many_for_round_retrieval_artifacts(tmp_path: Path) -> None:
    session = ArtifactStore(tmp_path).create_root(ArtifactKind.RUN)
    expected_payloads = {
        "round.query_resume_hits": [{"resume_id": "resume-1", "query": "python"}],
        "round.replay_snapshot": {"provider": "cts", "version": "2026-04-28"},
        "round.second_lane_decision": {"enabled": True},
        "round.prf_policy_decision": {"status": "accepted"},
    }

    for descriptor, payload in expected_payloads.items():
        session.write_json(descriptor, payload, round_no=1)

    resolved = session.resolve_many(expected_payloads, round_no=1)

    assert {
        descriptor: path.relative_to(session.root).as_posix()
        for descriptor, path in resolved.items()
    } == {
        "round.query_resume_hits": "rounds/round_01/query_resume_hits.json",
        "round.replay_snapshot": "rounds/round_01/replay_snapshot.json",
        "round.second_lane_decision": "rounds/round_01/second_lane_decision.json",
        "round.prf_policy_decision": "rounds/round_01/prf_policy_decision.json",
    }
    for descriptor, payload in expected_payloads.items():
        assert _read_json(resolved[descriptor]) == payload


def test_benchmark_manifest_persists_child_artifacts_and_failure_summary(tmp_path: Path) -> None:
    child_ref = ChildArtifactRef(
        kind=ArtifactKind.RUN,
        artifact_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        relationship="benchmark-member",
    )

    session = ArtifactStore(tmp_path).create_root(
        ArtifactKind.BENCHMARK,
        child_artifacts=[child_ref],
        failure_summary="1 child run failed validation",
    )
    manifest = _read_json(session.manifest_path)

    assert manifest["child_artifacts"] == [
        {
            "kind": "run",
            "artifact_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "relationship": "benchmark-member",
        }
    ]
    assert manifest["failure_summary"] == "1 child run failed validation"


def test_register_path_rejects_escape_paths(tmp_path: Path) -> None:
    session = ArtifactStore(tmp_path).create_root(ArtifactKind.RUN)

    with pytest.raises(ValueError, match="escape"):
        session.register_path("custom.escape", "../outside.json")


def test_resolver_rejects_escape_paths_from_manifest_entries(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    session = store.create_root(ArtifactKind.RUN)
    manifest = _read_json(session.manifest_path)
    assert isinstance(manifest, dict)
    logical_artifacts = manifest["logical_artifacts"]
    assert isinstance(logical_artifacts, dict)
    logical_artifacts["custom.bad"] = {
        "name": "custom.bad",
        "relative_path": "../outside.json",
    }
    session.manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    reopened = store.open(session.root)

    with pytest.raises(ValueError, match="escape"):
        reopened.resolve("custom.bad")
