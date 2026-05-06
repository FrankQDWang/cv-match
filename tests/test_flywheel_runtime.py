from __future__ import annotations

import json
from pathlib import Path

from seektalent.artifacts import ArtifactStore
from seektalent.flywheel.runtime import build_run_query_rows, query_hit_rows_from_hits
from seektalent.models import QueryResumeHit, SentQueryRecord


def test_build_run_query_rows_include_canonical_query_spec(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    session = store.create_root(kind="run", display_name="run", producer="test")

    rows = build_run_query_rows(
        run_id=session.manifest.artifact_id,
        artifact_id=session.manifest.artifact_id,
        sent_query_records=[
            SentQueryRecord(
                round_no=1,
                lane_type="exploit",
                query_instance_id="query-1",
                query_fingerprint="fingerprint-1",
                batch_no=1,
                requested_count=5,
                query_terms=["LangGraph", "Agent"],
                keyword_query="LangGraph Agent",
                source_plan_version=1,
                rationale="test",
            )
        ],
        canonical_query_specs={
            "query-1": {
                "lane_type": "exploit",
                "rendered_provider_query": "LangGraph Agent",
                "provider_filters": {"city": "上海"},
            }
        },
        job_intent_fingerprint="intent-1",
        query_policy_version="query-policy-v1",
    )

    row = rows[0]
    assert row["canonical_query_spec_json"]
    assert json.loads(row["canonical_query_spec_json"])["lane_type"] == "exploit"
    assert row["query_spec_schema_version"] == "canonical-query-spec-v1"
    assert row["job_intent_fingerprint"] == "intent-1"


def test_query_hit_rows_require_snapshot_hash_for_normal_hits() -> None:
    hit = QueryResumeHit(
        run_id="run-1",
        query_instance_id="query-1",
        query_fingerprint="fingerprint-1",
        hit_sequence_no=1,
        snapshot_sha256="snapshot-1",
        resume_id="resume-1",
        round_no=1,
        lane_type="exploit",
        batch_no=1,
        rank_in_query=1,
        provider_name="cts",
        dedup_key="resume-1",
        was_new_to_pool=True,
        was_duplicate=False,
    )

    rows = query_hit_rows_from_hits([hit])

    assert rows[0]["snapshot_sha256"] == "snapshot-1"
    assert rows[0]["snapshot_missing_reason"] is None
