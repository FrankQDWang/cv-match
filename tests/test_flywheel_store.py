from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from seektalent.config import AppSettings
from seektalent.flywheel.store import (
    FLYWHEEL_LABEL_SCHEMA_VERSION,
    FlywheelStore,
    build_judge_contract_hash,
    canonical_json,
    task_sha256,
)


def test_flywheel_store_creates_tables_and_enables_foreign_keys(tmp_path: Path) -> None:
    store = FlywheelStore(tmp_path / "flywheel.sqlite3")
    try:
        conn = store.connect()
        table_names = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        }
        assert {
            "tasks",
            "schema_meta",
            "resume_snapshots",
            "artifact_refs",
            "runs",
            "run_queries",
            "query_resume_hits",
            "judge_labels",
            "query_outcomes",
            "query_judge_outcomes",
            "term_events",
            "term_outcomes",
            "query_rewrite_samples",
            "dataset_exports",
        } <= table_names
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
        assert conn.execute("SELECT json_valid(?)", ("{}",)).fetchone()[0] == 1
        assert conn.execute("SELECT value FROM schema_meta WHERE key = 'schema_version'").fetchone()[0] == "flywheel-schema-v1"
    finally:
        store.close()


def test_settings_resolves_flywheel_path(tmp_path: Path) -> None:
    settings = AppSettings(_env_file=None, workspace_root=str(tmp_path), flywheel_db_path=".seektalent/flywheel.sqlite3")

    assert settings.flywheel_path == tmp_path / ".seektalent/flywheel.sqlite3"


def test_task_hash_includes_job_title_and_notes() -> None:
    base = task_sha256(job_title="Agent Engineer", jd="Build agents.", notes="")
    different_title = task_sha256(job_title="Data Engineer", jd="Build agents.", notes="")
    different_notes = task_sha256(job_title="Agent Engineer", jd="Build agents.", notes="Prefer LangGraph")
    assert base != different_title
    assert base != different_notes


def test_json_columns_reject_invalid_json(tmp_path: Path) -> None:
    store = FlywheelStore(tmp_path / "flywheel.sqlite3")
    try:
        store.upsert_task(job_title="Agent Engineer", jd_text="JD", notes_text="")
        conn = store.connect()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO resume_snapshots (
                    snapshot_sha256, source_resume_id, dedup_key, raw_json,
                    normalized_preview_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("snapshot-invalid", "r1", "r1", "{bad json", "{}", "2026-05-06T00:00:00Z"),
            )
    finally:
        store.close()


def test_query_hits_require_snapshot_or_missing_reason(tmp_path: Path) -> None:
    store = FlywheelStore(tmp_path / "flywheel.sqlite3")
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
            config_payload={},
            status="running",
            eval_enabled=False,
            benchmark_id=None,
            benchmark_case_id=None,
        )
        conn = store.connect()
        conn.execute(
            """
            INSERT INTO run_queries (
                run_id, query_instance_id, query_fingerprint, round_no,
                lane_type, canonical_query_spec_json, query_spec_schema_version,
                query_policy_version, job_intent_fingerprint, provider_name,
                rendered_provider_query, keyword_query, query_terms_json,
                filters_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "run-1", "query-1", "fingerprint-1", 1, "exploit",
                "{}", "canonical-query-spec-v1", "query-policy-v1", "intent-1",
                "cts", "agent", "agent", "[]", "{}",
                "2026-05-06T00:00:00Z",
            ),
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO query_resume_hits (
                    run_id, query_instance_id, query_fingerprint, hit_sequence_no,
                    snapshot_sha256, snapshot_missing_reason, resume_id, round_no,
                    lane_type, batch_no, rank_in_query, provider_name,
                    was_new_to_pool, was_duplicate, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "run-1", "query-1", "fingerprint-1", 1,
                    None, None, "resume-1", 1, "exploit", 1, 1,
                    "cts", 1, 0, "2026-05-06T00:00:00Z",
                ),
            )
    finally:
        store.close()


def test_judge_label_cache_uses_contract_hash(tmp_path: Path) -> None:
    store = FlywheelStore(tmp_path / "flywheel.sqlite3")
    try:
        task_id = store.upsert_task(job_title="Agent Engineer", jd_text="JD", notes_text="")
        store.upsert_resume_snapshot(
            snapshot_sha256="snapshot-1",
            source_resume_id="resume-1",
            dedup_key="resume-1",
            raw_payload={"resume_id": "resume-1"},
            normalized_preview={"search_text": "agent"},
        )
        first_contract = build_judge_contract_hash(
            judge_model_id="deepseek-v4-pro",
            judge_protocol_family="openai_chat_completions_compatible",
            judge_provider_label="bailian",
            judge_endpoint_kind="openai-compatible",
            structured_output_mode="strict_native_schema",
            judge_prompt_hash="prompt-a",
            judge_policy_version="judge-policy-v1",
            label_schema_version=FLYWHEEL_LABEL_SCHEMA_VERSION,
            judge_output_schema_hash="schema-hash",
            reasoning_effort=None,
            temperature=0.0,
        )
        second_contract = build_judge_contract_hash(
            judge_model_id="deepseek-v4-pro",
            judge_protocol_family="openai_chat_completions_compatible",
            judge_provider_label="bailian",
            judge_endpoint_kind="openai-compatible",
            structured_output_mode="strict_native_schema",
            judge_prompt_hash="prompt-b",
            judge_policy_version="judge-policy-v1",
            label_schema_version=FLYWHEEL_LABEL_SCHEMA_VERSION,
            judge_output_schema_hash="schema-hash",
            reasoning_effort=None,
            temperature=0.0,
        )
        store.record_judge_label(
            task_id=task_id,
            snapshot_sha256="snapshot-1",
            judge_model_id="deepseek-v4-pro",
            judge_protocol_family="openai_chat_completions_compatible",
            judge_provider_label="bailian",
            judge_endpoint_kind="openai-compatible",
            structured_output_mode="strict_native_schema",
            judge_prompt_hash="prompt-a",
            judge_contract_hash=first_contract,
            judge_policy_version="judge-policy-v1",
            label_schema_version=FLYWHEEL_LABEL_SCHEMA_VERSION,
            judge_output_schema_hash="schema-hash",
            reasoning_effort=None,
            temperature=0.0,
            score=3,
            rationale="Strong fit.",
            label_payload={"score": 3, "rationale": "Strong fit."},
            judge_prompt_text="prompt text",
        )
        assert store.get_cached_judge_label(
            task_id=task_id,
            snapshot_sha256="snapshot-1",
            judge_contract_hash=first_contract,
            label_schema_version=FLYWHEEL_LABEL_SCHEMA_VERSION,
        ) == {"score": 3, "rationale": "Strong fit."}
        assert store.get_cached_judge_label(
            task_id=task_id,
            snapshot_sha256="snapshot-1",
            judge_contract_hash=second_contract,
            label_schema_version=FLYWHEEL_LABEL_SCHEMA_VERSION,
        ) is None
    finally:
        store.close()


def test_record_judge_label_rejects_mismatched_contract_hash(tmp_path: Path) -> None:
    store = FlywheelStore(tmp_path / "flywheel.sqlite3")
    try:
        task_id = store.upsert_task(job_title="Agent Engineer", jd_text="JD", notes_text="")
        store.upsert_resume_snapshot(
            snapshot_sha256="snapshot-1",
            source_resume_id="resume-1",
            dedup_key="resume-1",
            raw_payload={"resume_id": "resume-1"},
            normalized_preview={"search_text": "agent"},
        )
        with pytest.raises(ValueError, match="judge_contract_hash"):
            store.record_judge_label(
                task_id=task_id,
                snapshot_sha256="snapshot-1",
                judge_model_id="deepseek-v4-pro",
                judge_protocol_family="openai_chat_completions_compatible",
                judge_provider_label="bailian",
                judge_endpoint_kind="openai-compatible",
                structured_output_mode="strict_native_schema",
                judge_prompt_hash="prompt-a",
                judge_contract_hash="wrong",
                judge_policy_version="judge-policy-v1",
                label_schema_version=FLYWHEEL_LABEL_SCHEMA_VERSION,
                judge_output_schema_hash="schema-hash",
                reasoning_effort=None,
                temperature=0.0,
                score=3,
                rationale="Strong fit.",
                label_payload={"score": 3, "rationale": "Strong fit."},
                judge_prompt_text="prompt text",
            )
    finally:
        store.close()


def test_canonical_json_is_stable() -> None:
    assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'
