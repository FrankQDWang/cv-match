from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

FLYWHEEL_SCHEMA_VERSION = "flywheel-schema-v1"
FLYWHEEL_TASK_SCHEMA_VERSION = "task-v1"
FLYWHEEL_LABEL_SCHEMA_VERSION = "judge-label-v1"


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def task_sha256(*, job_title: str, jd: str, notes: str) -> str:
    payload = {
        "task_schema_version": FLYWHEEL_TASK_SCHEMA_VERSION,
        "job_title": job_title,
        "jd_text": jd,
        "notes_text": notes,
    }
    return sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def build_judge_contract_hash(
    *,
    judge_model_id: str,
    judge_protocol_family: str,
    judge_provider_label: str,
    judge_endpoint_kind: str,
    structured_output_mode: str,
    judge_prompt_hash: str,
    judge_policy_version: str,
    label_schema_version: str,
    judge_output_schema_hash: str,
    reasoning_effort: str | None = None,
    temperature: float | None = None,
) -> str:
    payload = {
        "judge_model_id": judge_model_id,
        "judge_protocol_family": judge_protocol_family,
        "judge_provider_label": judge_provider_label,
        "judge_endpoint_kind": judge_endpoint_kind,
        "structured_output_mode": structured_output_mode,
        "judge_prompt_hash": judge_prompt_hash,
        "judge_policy_version": judge_policy_version,
        "label_schema_version": label_schema_version,
        "judge_output_schema_hash": judge_output_schema_hash,
        "reasoning_effort": reasoning_effort,
        "temperature": temperature,
    }
    return sha256(canonical_json(payload).encode("utf-8")).hexdigest()


_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS schema_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    ){strict}
    """,
    """
    CREATE TABLE IF NOT EXISTS tasks (
        task_id TEXT PRIMARY KEY,
        task_sha256 TEXT NOT NULL UNIQUE,
        task_schema_version TEXT NOT NULL,
        jd_sha256 TEXT NOT NULL,
        notes_sha256 TEXT NOT NULL,
        job_title TEXT NOT NULL,
        jd_text TEXT NOT NULL,
        notes_text TEXT NOT NULL,
        created_at TEXT NOT NULL
    ){strict}
    """,
    """
    CREATE TABLE IF NOT EXISTS resume_snapshots (
        snapshot_sha256 TEXT PRIMARY KEY,
        source_resume_id TEXT,
        dedup_key TEXT,
        raw_json TEXT NOT NULL CHECK(json_valid(raw_json)),
        normalized_preview_json TEXT CHECK(normalized_preview_json IS NULL OR json_valid(normalized_preview_json)),
        created_at TEXT NOT NULL
    ){strict}
    """,
    """
    CREATE TABLE IF NOT EXISTS artifact_refs (
        artifact_ref_id TEXT PRIMARY KEY,
        artifact_kind TEXT NOT NULL,
        artifact_id TEXT NOT NULL,
        artifact_root TEXT NOT NULL,
        logical_name TEXT NOT NULL,
        relative_path TEXT,
        content_sha256 TEXT,
        schema_version TEXT,
        created_at TEXT NOT NULL,
        UNIQUE(artifact_kind, artifact_id, logical_name)
    ){strict}
    """,
    """
    CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL REFERENCES tasks(task_id),
        version TEXT,
        git_sha TEXT,
        artifact_ref_id TEXT REFERENCES artifact_refs(artifact_ref_id),
        artifact_root TEXT NOT NULL,
        config_hash TEXT NOT NULL,
        config_json TEXT NOT NULL CHECK(json_valid(config_json)),
        status TEXT NOT NULL,
        eval_enabled INTEGER NOT NULL,
        benchmark_id TEXT,
        benchmark_case_id TEXT,
        failure_summary TEXT,
        started_at TEXT NOT NULL,
        completed_at TEXT
    ){strict}
    """,
    """
    CREATE TABLE IF NOT EXISTS run_queries (
        run_id TEXT NOT NULL REFERENCES runs(run_id),
        query_instance_id TEXT NOT NULL,
        query_fingerprint TEXT NOT NULL,
        round_no INTEGER NOT NULL,
        lane_type TEXT NOT NULL,
        query_role TEXT,
        canonical_query_spec_json TEXT NOT NULL CHECK(json_valid(canonical_query_spec_json)),
        query_spec_schema_version TEXT NOT NULL,
        query_policy_version TEXT NOT NULL,
        job_intent_fingerprint TEXT NOT NULL,
        provider_name TEXT NOT NULL,
        rendered_provider_query TEXT NOT NULL,
        keyword_query TEXT NOT NULL,
        query_terms_json TEXT NOT NULL CHECK(json_valid(query_terms_json)),
        filters_json TEXT NOT NULL CHECK(json_valid(filters_json)),
        location_key TEXT,
        batch_no INTEGER,
        source_plan_version TEXT,
        selected_prf_expression TEXT,
        accepted_prf_term_family_id TEXT,
        fallback_reason TEXT,
        artifact_ref_id TEXT REFERENCES artifact_refs(artifact_ref_id),
        created_at TEXT NOT NULL,
        PRIMARY KEY (run_id, query_instance_id)
    ){strict}
    """,
    """
    CREATE TABLE IF NOT EXISTS query_resume_hits (
        run_id TEXT NOT NULL REFERENCES runs(run_id),
        query_instance_id TEXT NOT NULL,
        query_fingerprint TEXT NOT NULL,
        hit_sequence_no INTEGER NOT NULL,
        snapshot_sha256 TEXT REFERENCES resume_snapshots(snapshot_sha256),
        snapshot_missing_reason TEXT,
        resume_id TEXT NOT NULL,
        round_no INTEGER NOT NULL,
        lane_type TEXT NOT NULL,
        location_key TEXT,
        location_type TEXT,
        batch_no INTEGER NOT NULL,
        rank_in_query INTEGER NOT NULL,
        rank_global_in_query INTEGER,
        provider_name TEXT NOT NULL,
        provider_page_no INTEGER,
        provider_fetch_no INTEGER,
        provider_score_if_any REAL,
        dedup_key TEXT,
        was_new_to_pool INTEGER NOT NULL,
        was_duplicate INTEGER NOT NULL,
        scored_fit_bucket TEXT,
        overall_score REAL,
        must_have_match_score REAL,
        risk_score REAL,
        off_intent_reason_count INTEGER NOT NULL DEFAULT 0,
        final_candidate_status TEXT,
        created_at TEXT NOT NULL,
        CHECK(snapshot_sha256 IS NOT NULL OR snapshot_missing_reason IS NOT NULL),
        PRIMARY KEY (run_id, query_instance_id, hit_sequence_no),
        FOREIGN KEY (run_id, query_instance_id) REFERENCES run_queries(run_id, query_instance_id)
    ){strict}
    """,
    """
    CREATE TABLE IF NOT EXISTS judge_labels (
        task_id TEXT NOT NULL REFERENCES tasks(task_id),
        snapshot_sha256 TEXT NOT NULL REFERENCES resume_snapshots(snapshot_sha256),
        judge_model_id TEXT NOT NULL,
        judge_prompt_hash TEXT NOT NULL,
        judge_contract_hash TEXT NOT NULL,
        judge_protocol_family TEXT NOT NULL,
        judge_provider_label TEXT NOT NULL,
        judge_endpoint_kind TEXT NOT NULL,
        structured_output_mode TEXT NOT NULL,
        judge_policy_version TEXT NOT NULL,
        label_schema_version TEXT NOT NULL,
        judge_output_schema_hash TEXT NOT NULL,
        reasoning_effort TEXT,
        temperature REAL,
        score INTEGER NOT NULL,
        rationale TEXT NOT NULL,
        label_json TEXT NOT NULL CHECK(json_valid(label_json)),
        judge_prompt_text TEXT,
        judge_output_schema_json TEXT CHECK(judge_output_schema_json IS NULL OR json_valid(judge_output_schema_json)),
        latency_ms INTEGER,
        judge_call_artifact_ref_id TEXT REFERENCES artifact_refs(artifact_ref_id),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (task_id, snapshot_sha256, judge_contract_hash, label_schema_version)
    ){strict}
    """,
    """
    CREATE TABLE IF NOT EXISTS query_outcomes (
        run_id TEXT NOT NULL REFERENCES runs(run_id),
        query_instance_id TEXT NOT NULL,
        query_fingerprint TEXT NOT NULL,
        outcome_schema_version TEXT NOT NULL,
        outcome_policy_version TEXT NOT NULL,
        outcome_thresholds_hash TEXT NOT NULL,
        outcome_thresholds_json TEXT NOT NULL CHECK(json_valid(outcome_thresholds_json)),
        scoring_policy_version TEXT,
        dedupe_version TEXT,
        outcome_basis TEXT NOT NULL,
        round_no INTEGER NOT NULL,
        lane_type TEXT NOT NULL,
        provider_returned_count INTEGER NOT NULL,
        new_unique_resume_count INTEGER NOT NULL,
        duplicate_count INTEGER NOT NULL,
        scored_resume_count INTEGER NOT NULL,
        new_fit_count INTEGER NOT NULL,
        new_near_fit_count INTEGER NOT NULL,
        fit_rate_denominator TEXT,
        fit_rate REAL,
        must_have_match_avg REAL,
        risk_score_avg REAL,
        off_intent_reason_count INTEGER NOT NULL,
        primary_label TEXT NOT NULL,
        labels_json TEXT NOT NULL CHECK(json_valid(labels_json)),
        reasons_json TEXT NOT NULL CHECK(json_valid(reasons_json)),
        latency_ms INTEGER,
        cost_estimate_usd REAL,
        artifact_ref_id TEXT REFERENCES artifact_refs(artifact_ref_id),
        created_at TEXT NOT NULL,
        PRIMARY KEY (run_id, query_instance_id)
    ){strict}
    """,
    """
    CREATE TABLE IF NOT EXISTS query_judge_outcomes (
        run_id TEXT NOT NULL REFERENCES runs(run_id),
        query_instance_id TEXT NOT NULL,
        query_fingerprint TEXT NOT NULL,
        task_id TEXT NOT NULL REFERENCES tasks(task_id),
        judge_contract_hash TEXT NOT NULL,
        judge_model_id TEXT NOT NULL,
        judge_prompt_hash TEXT NOT NULL,
        label_schema_version TEXT NOT NULL,
        outcome_schema_version TEXT NOT NULL,
        outcome_policy_version TEXT NOT NULL,
        outcome_thresholds_hash TEXT NOT NULL,
        outcome_thresholds_json TEXT NOT NULL CHECK(json_valid(outcome_thresholds_json)),
        provider_returned_count INTEGER NOT NULL,
        new_unique_resume_count INTEGER NOT NULL,
        judged_resume_count INTEGER NOT NULL,
        new_judge_positive_count INTEGER NOT NULL,
        new_judge_near_positive_count INTEGER NOT NULL,
        judge_positive_rate REAL,
        duplicate_count INTEGER NOT NULL,
        primary_label TEXT NOT NULL,
        labels_json TEXT NOT NULL CHECK(json_valid(labels_json)),
        reasons_json TEXT NOT NULL CHECK(json_valid(reasons_json)),
        artifact_ref_id TEXT REFERENCES artifact_refs(artifact_ref_id),
        created_at TEXT NOT NULL,
        PRIMARY KEY (run_id, query_instance_id, judge_contract_hash)
    ){strict}
    """,
    """
    CREATE TABLE IF NOT EXISTS term_events (
        run_id TEXT NOT NULL REFERENCES runs(run_id),
        term_event_id TEXT NOT NULL,
        proposal_id TEXT,
        prf_decision_id TEXT,
        prf_candidate_artifact_ref_id TEXT REFERENCES artifact_refs(artifact_ref_id),
        prf_policy_decision_artifact_ref_id TEXT REFERENCES artifact_refs(artifact_ref_id),
        prf_proposal_extractor_version TEXT,
        prf_familying_version TEXT,
        prf_gate_version TEXT,
        candidate_query_fingerprint TEXT,
        executed_query_instance_id TEXT,
        selected_query_instance_id TEXT,
        term_surface TEXT NOT NULL,
        term_family_id TEXT NOT NULL,
        term_role TEXT NOT NULL,
        source TEXT NOT NULL,
        round_no INTEGER NOT NULL,
        lane_type TEXT,
        accepted_by_prf_gate INTEGER,
        prf_reject_reasons_json TEXT CHECK(prf_reject_reasons_json IS NULL OR json_valid(prf_reject_reasons_json)),
        supporting_resume_ids_json TEXT CHECK(supporting_resume_ids_json IS NULL OR json_valid(supporting_resume_ids_json)),
        negative_resume_ids_json TEXT CHECK(negative_resume_ids_json IS NULL OR json_valid(negative_resume_ids_json)),
        artifact_ref_id TEXT REFERENCES artifact_refs(artifact_ref_id),
        created_at TEXT NOT NULL,
        PRIMARY KEY (run_id, term_event_id)
    ){strict}
    """,
    """
    CREATE TABLE IF NOT EXISTS term_outcomes (
        run_id TEXT NOT NULL REFERENCES runs(run_id),
        term_event_id TEXT NOT NULL,
        term_family_id TEXT NOT NULL,
        term_outcome_schema_version TEXT NOT NULL,
        term_familying_version TEXT NOT NULL,
        prf_gate_version TEXT,
        prf_policy_version TEXT,
        execution_status TEXT NOT NULL,
        runtime_outcome_json TEXT CHECK(runtime_outcome_json IS NULL OR json_valid(runtime_outcome_json)),
        judge_outcome_json TEXT CHECK(judge_outcome_json IS NULL OR json_valid(judge_outcome_json)),
        labels_json TEXT NOT NULL CHECK(json_valid(labels_json)),
        reasons_json TEXT NOT NULL CHECK(json_valid(reasons_json)),
        artifact_ref_id TEXT REFERENCES artifact_refs(artifact_ref_id),
        created_at TEXT NOT NULL,
        PRIMARY KEY (run_id, term_event_id)
    ){strict}
    """,
    """
    CREATE TABLE IF NOT EXISTS query_rewrite_samples (
        sample_id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL REFERENCES tasks(task_id),
        run_id TEXT NOT NULL REFERENCES runs(run_id),
        source_query_instance_ids_json TEXT NOT NULL CHECK(json_valid(source_query_instance_ids_json)),
        sample_basis TEXT NOT NULL,
        input_json TEXT NOT NULL CHECK(json_valid(input_json)),
        target_json TEXT NOT NULL CHECK(json_valid(target_json)),
        reward_json TEXT NOT NULL CHECK(json_valid(reward_json)),
        schema_version TEXT NOT NULL,
        dataset_version TEXT NOT NULL,
        builder_version TEXT NOT NULL,
        builder_config_hash TEXT NOT NULL,
        artifact_ref_id TEXT REFERENCES artifact_refs(artifact_ref_id),
        created_at TEXT NOT NULL
    ){strict}
    """,
    """
    CREATE TABLE IF NOT EXISTS dataset_exports (
        export_id TEXT PRIMARY KEY,
        dataset_name TEXT NOT NULL,
        dataset_version TEXT NOT NULL,
        schema_version TEXT NOT NULL,
        builder_version TEXT NOT NULL,
        builder_config_hash TEXT NOT NULL,
        builder_config_json TEXT NOT NULL CHECK(json_valid(builder_config_json)),
        source_db_sha256 TEXT NOT NULL,
        source_run_ids_json TEXT NOT NULL CHECK(json_valid(source_run_ids_json)),
        source_query TEXT NOT NULL,
        source_artifact_refs_json TEXT NOT NULL CHECK(json_valid(source_artifact_refs_json)),
        git_sha TEXT,
        artifact_root TEXT NOT NULL,
        output_path TEXT NOT NULL,
        artifact_ref_id TEXT REFERENCES artifact_refs(artifact_ref_id),
        row_count INTEGER NOT NULL,
        sha256 TEXT NOT NULL,
        created_at TEXT NOT NULL
    ){strict}
    """,
]


class FlywheelStore:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self.path, timeout=5)
            self._conn.row_factory = sqlite3.Row
            self._configure(self._conn)
            self._ensure_schema(self._conn)
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _configure(self, conn: sqlite3.Connection) -> None:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 5000")

    def _strict_suffix(self, conn: sqlite3.Connection) -> str:
        try:
            conn.execute("CREATE TEMP TABLE __flywheel_strict_probe (value TEXT) STRICT")
            conn.execute("DROP TABLE __flywheel_strict_probe")
        except sqlite3.OperationalError:
            return ""
        return " STRICT"

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        if conn.execute("SELECT json_valid(?)", ("{}",)).fetchone()[0] != 1:
            raise RuntimeError("SQLite JSON1 support is required for FlywheelStore")
        conn.execute("PRAGMA user_version = 1")
        strict_suffix = self._strict_suffix(conn)
        for statement in _SCHEMA_STATEMENTS:
            conn.execute(statement.format(strict=strict_suffix))
        conn.execute(
            """
            INSERT INTO schema_meta (key, value) VALUES ('schema_version', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (FLYWHEEL_SCHEMA_VERSION,),
        )
        conn.commit()

    def upsert_task(self, *, job_title: str, jd_text: str, notes_text: str) -> str:
        task_id = task_sha256(job_title=job_title, jd=jd_text, notes=notes_text)
        now = utc_now()
        self.connect().execute(
            """
            INSERT INTO tasks (
                task_id, task_sha256, task_schema_version, jd_sha256,
                notes_sha256, job_title, jd_text, notes_text, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET
                job_title = excluded.job_title,
                jd_text = excluded.jd_text,
                notes_text = excluded.notes_text
            """,
            (
                task_id,
                task_id,
                FLYWHEEL_TASK_SCHEMA_VERSION,
                sha256(jd_text.encode("utf-8")).hexdigest(),
                sha256(notes_text.encode("utf-8")).hexdigest(),
                job_title,
                jd_text,
                notes_text,
                now,
            ),
        )
        self.connect().commit()
        return task_id

    def upsert_resume_snapshot(
        self,
        *,
        snapshot_sha256: str,
        source_resume_id: str | None,
        dedup_key: str | None,
        raw_payload: dict[str, Any],
        normalized_preview: dict[str, Any] | None = None,
    ) -> None:
        self.connect().execute(
            """
            INSERT INTO resume_snapshots (
                snapshot_sha256, source_resume_id, dedup_key, raw_json,
                normalized_preview_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(snapshot_sha256) DO UPDATE SET
                source_resume_id = excluded.source_resume_id,
                dedup_key = excluded.dedup_key,
                raw_json = excluded.raw_json,
                normalized_preview_json = excluded.normalized_preview_json
            """,
            (
                snapshot_sha256,
                source_resume_id,
                dedup_key,
                canonical_json(raw_payload),
                canonical_json(normalized_preview) if normalized_preview is not None else None,
                utc_now(),
            ),
        )
        self.connect().commit()

    def start_run(
        self,
        *,
        run_id: str,
        task_id: str,
        version: str | None,
        git_sha: str | None,
        artifact_ref_id: str | None,
        artifact_root: str,
        config_hash: str,
        config_payload: dict[str, Any],
        status: str,
        eval_enabled: bool,
        benchmark_id: str | None,
        benchmark_case_id: str | None,
    ) -> None:
        self.connect().execute(
            """
            INSERT INTO runs (
                run_id, task_id, version, git_sha, artifact_ref_id, artifact_root,
                config_hash, config_json, status, eval_enabled, benchmark_id,
                benchmark_case_id, started_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                status = excluded.status,
                config_hash = excluded.config_hash,
                config_json = excluded.config_json,
                eval_enabled = excluded.eval_enabled
            """,
            (
                run_id,
                task_id,
                version,
                git_sha,
                artifact_ref_id,
                artifact_root,
                config_hash,
                canonical_json(config_payload),
                status,
                int(eval_enabled),
                benchmark_id,
                benchmark_case_id,
                utc_now(),
            ),
        )
        self.connect().commit()

    def record_artifact_ref(
        self,
        *,
        artifact_kind: str,
        artifact_id: str,
        artifact_root: str,
        logical_name: str,
        relative_path: str | None,
        content_sha256: str | None,
        schema_version: str | None,
    ) -> str:
        artifact_ref_id = sha256(
            canonical_json(
                {
                    "artifact_kind": artifact_kind,
                    "artifact_id": artifact_id,
                    "logical_name": logical_name,
                }
            ).encode("utf-8")
        ).hexdigest()
        self.connect().execute(
            """
            INSERT INTO artifact_refs (
                artifact_ref_id, artifact_kind, artifact_id, artifact_root,
                logical_name, relative_path, content_sha256, schema_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(artifact_kind, artifact_id, logical_name) DO UPDATE SET
                artifact_root = excluded.artifact_root,
                relative_path = excluded.relative_path,
                content_sha256 = excluded.content_sha256,
                schema_version = excluded.schema_version
            """,
            (
                artifact_ref_id,
                artifact_kind,
                artifact_id,
                artifact_root,
                logical_name,
                relative_path,
                content_sha256,
                schema_version,
                utc_now(),
            ),
        )
        self.connect().commit()
        return artifact_ref_id

    def record_judge_label(
        self,
        *,
        task_id: str,
        snapshot_sha256: str,
        judge_model_id: str,
        judge_protocol_family: str,
        judge_provider_label: str,
        judge_endpoint_kind: str,
        structured_output_mode: str,
        judge_prompt_hash: str,
        judge_contract_hash: str,
        judge_policy_version: str,
        label_schema_version: str,
        judge_output_schema_hash: str,
        reasoning_effort: str | None,
        temperature: float | None,
        score: int,
        rationale: str,
        label_payload: dict[str, Any],
        judge_prompt_text: str | None,
        latency_ms: int | None = None,
    ) -> None:
        expected_contract = build_judge_contract_hash(
            judge_model_id=judge_model_id,
            judge_protocol_family=judge_protocol_family,
            judge_provider_label=judge_provider_label,
            judge_endpoint_kind=judge_endpoint_kind,
            structured_output_mode=structured_output_mode,
            judge_prompt_hash=judge_prompt_hash,
            judge_policy_version=judge_policy_version,
            label_schema_version=label_schema_version,
            judge_output_schema_hash=judge_output_schema_hash,
            reasoning_effort=reasoning_effort,
            temperature=temperature,
        )
        if judge_contract_hash != expected_contract:
            raise ValueError("judge_contract_hash does not match judge label contract fields")
        now = utc_now()
        self.connect().execute(
            """
            INSERT INTO judge_labels (
                task_id, snapshot_sha256, judge_model_id, judge_prompt_hash,
                judge_contract_hash, judge_protocol_family, judge_provider_label,
                judge_endpoint_kind, structured_output_mode, judge_policy_version,
                label_schema_version, judge_output_schema_hash, reasoning_effort, temperature,
                score, rationale, label_json, judge_prompt_text, latency_ms,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(task_id, snapshot_sha256, judge_contract_hash, label_schema_version) DO UPDATE SET
                score = excluded.score,
                rationale = excluded.rationale,
                label_json = excluded.label_json,
                judge_prompt_text = excluded.judge_prompt_text,
                latency_ms = excluded.latency_ms,
                updated_at = excluded.updated_at
            """,
            (
                task_id,
                snapshot_sha256,
                judge_model_id,
                judge_prompt_hash,
                judge_contract_hash,
                judge_protocol_family,
                judge_provider_label,
                judge_endpoint_kind,
                structured_output_mode,
                judge_policy_version,
                label_schema_version,
                judge_output_schema_hash,
                reasoning_effort,
                temperature,
                score,
                rationale,
                canonical_json(label_payload),
                judge_prompt_text,
                latency_ms,
                now,
                now,
            ),
        )
        self.connect().commit()

    def get_cached_judge_label(
        self,
        *,
        task_id: str,
        snapshot_sha256: str,
        judge_contract_hash: str,
        label_schema_version: str,
    ) -> dict[str, Any] | None:
        row = self.connect().execute(
            """
            SELECT label_json
            FROM judge_labels
            WHERE task_id = ?
              AND snapshot_sha256 = ?
              AND judge_contract_hash = ?
              AND label_schema_version = ?
            """,
            (task_id, snapshot_sha256, judge_contract_hash, label_schema_version),
        ).fetchone()
        if row is None:
            return None
        return json.loads(str(row["label_json"]))

    def judge_cache_summary(self, *, task_id: str, judge_contract_hash: str) -> dict[str, object]:
        row = self.connect().execute(
            """
            SELECT COUNT(*) AS hits
            FROM judge_labels
            WHERE task_id = ?
              AND judge_contract_hash = ?
            """,
            (task_id, judge_contract_hash),
        ).fetchone()
        return {"hits": int(row["hits"]), "contract_hash": judge_contract_hash}
