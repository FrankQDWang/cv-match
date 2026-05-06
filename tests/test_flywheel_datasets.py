from __future__ import annotations

import json
from pathlib import Path

from seektalent.artifacts import ArtifactStore
from seektalent.flywheel.datasets import export_query_rewriting_dataset
from seektalent.flywheel.store import FlywheelStore


def test_dataset_export_is_deterministic(tmp_path: Path) -> None:
    db_path = tmp_path / "flywheel.sqlite3"
    store = FlywheelStore(db_path)
    try:
        task_id = store.upsert_task(job_title="Agent Engineer", jd_text="JD", notes_text="")
        store.start_run(
            run_id="run-1",
            task_id=task_id,
            version="0.6.2",
            git_sha="abc123",
            artifact_ref_id=None,
            artifact_root=str(tmp_path / "artifacts/runs/run-1"),
            config_hash="config-hash",
            config_payload={"max_rounds": 3},
            status="completed",
            eval_enabled=True,
            benchmark_id=None,
            benchmark_case_id=None,
        )
        store.record_query_judge_outcomes(
            [
                {
                    "run_id": "run-1",
                    "query_instance_id": "query-1",
                    "query_fingerprint": "fingerprint-1",
                    "task_id": task_id,
                    "judge_contract_hash": "judge-contract",
                    "judge_model_id": "deepseek-v4-pro",
                    "judge_prompt_hash": "prompt-hash",
                    "label_schema_version": "judge-label-v1",
                    "outcome_schema_version": "query-judge-outcome-v1",
                    "outcome_policy_version": "query-judge-outcome-policy-v1",
                    "outcome_thresholds_hash": "thresholds-hash",
                    "outcome_thresholds_json": "{}",
                    "provider_returned_count": 1,
                    "new_unique_resume_count": 1,
                    "judged_resume_count": 1,
                    "new_judge_positive_count": 1,
                    "new_judge_near_positive_count": 0,
                    "judge_positive_rate": 1.0,
                    "duplicate_count": 0,
                    "primary_label": "marginal_gain",
                    "labels_json": json.dumps(["marginal_gain"]),
                    "reasons_json": json.dumps(["judge positive"]),
                    "artifact_ref_id": None,
                }
            ]
        )
        artifact_store = ArtifactStore(tmp_path / "artifacts")

        first = export_query_rewriting_dataset(
            store=store,
            artifact_store=artifact_store,
            dataset_version="dataset-v1",
            builder_config={"min_positive": 1},
            run_ids=["run-1"],
        )
        second = export_query_rewriting_dataset(
            store=store,
            artifact_store=artifact_store,
            dataset_version="dataset-v1",
            builder_config={"min_positive": 1},
            run_ids=["run-1"],
        )

        assert first.sha256 == second.sha256
        first_lines = (first.root / "flywheel/query_rewrite_samples.jsonl").read_text(encoding="utf-8").splitlines()
        second_lines = (second.root / "flywheel/query_rewrite_samples.jsonl").read_text(encoding="utf-8").splitlines()
        assert first_lines == second_lines
        for name in [
            "query_outcomes",
            "query_judge_outcomes",
            "term_events",
            "term_outcomes",
            "query_rewrite_samples",
        ]:
            assert (first.root / f"flywheel/{name}.jsonl").exists()
    finally:
        store.close()
