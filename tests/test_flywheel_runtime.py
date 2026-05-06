from __future__ import annotations

import json
from pathlib import Path

from seektalent.artifacts import ArtifactStore
from seektalent.flywheel.outcomes import build_runtime_query_outcome_row
from seektalent.flywheel.runtime import build_run_query_rows, materialize_flywheel_run_artifacts, query_hit_rows_from_hits
from seektalent.flywheel.store import FlywheelStore
from seektalent.models import QueryOutcomeClassification, QueryResumeHit, SentQueryRecord


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


def test_zero_recall_runtime_outcome_uses_null_precision_fields() -> None:
    row = build_runtime_query_outcome_row(
        run_id="run-1",
        query_instance_id="query-1",
        query_fingerprint="fingerprint-1",
        round_no=1,
        lane_type="exploit",
        provider_returned_count=0,
        new_unique_resume_count=0,
        duplicate_count=0,
        scored_resume_count=0,
        new_fit_count=0,
        must_have_match_scores=[],
        risk_scores=[],
        off_intent_reason_count=0,
        classification=QueryOutcomeClassification(
            primary_label="zero_recall",
            labels=["zero_recall"],
            reasons=["provider_returned_count == 0"],
        ),
        thresholds_payload={"low_recall_threshold": 2},
    )

    assert row["fit_rate"] is None
    assert row["must_have_match_avg"] is None
    assert row["risk_score_avg"] is None
    assert row["scored_resume_count"] == 0
    assert row["outcome_schema_version"] == "query-outcome-v1"


def test_materialize_flywheel_run_artifacts_backfills_artifact_refs(tmp_path: Path) -> None:
    artifact_store = ArtifactStore(tmp_path / "artifacts")
    session = artifact_store.create_root(kind="run", display_name="run", producer="test")
    store = FlywheelStore(tmp_path / "flywheel.sqlite3")
    try:
        task_id = store.upsert_task(job_title="Agent Engineer", jd_text="JD", notes_text="")
        store.start_run(
            run_id=session.manifest.artifact_id,
            task_id=task_id,
            version="0.6.2",
            git_sha="abc123",
            artifact_ref_id=None,
            artifact_root=str(session.root),
            config_hash="config",
            config_payload={},
            status="completed",
            eval_enabled=False,
            benchmark_id=None,
            benchmark_case_id=None,
        )
        store.record_query_outcomes(
            [
                build_runtime_query_outcome_row(
                    run_id=session.manifest.artifact_id,
                    query_instance_id="query-1",
                    query_fingerprint="fingerprint-1",
                    round_no=1,
                    lane_type="exploit",
                    provider_returned_count=0,
                    new_unique_resume_count=0,
                    duplicate_count=0,
                    scored_resume_count=0,
                    new_fit_count=0,
                    must_have_match_scores=[],
                    risk_scores=[],
                    off_intent_reason_count=0,
                    classification=QueryOutcomeClassification(
                        primary_label="zero_recall",
                        labels=["zero_recall"],
                        reasons=[],
                    ),
                    thresholds_payload={},
                )
            ]
        )

        materialize_flywheel_run_artifacts(session=session, store=store, run_id=session.manifest.artifact_id)

        rows = store.rows_for_run("query_outcomes", run_id=session.manifest.artifact_id)
        assert rows[0]["artifact_ref_id"] is not None
        assert (session.root / "flywheel/query_outcomes.jsonl").exists()
    finally:
        store.close()
