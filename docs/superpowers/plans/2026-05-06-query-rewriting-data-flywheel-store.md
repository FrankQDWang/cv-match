# Query Rewriting Data Flywheel Store Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the active judge cache with a unified `FlywheelStore` that persists query, hit, judge label, outcome, term lineage, and export assets for Query Rewriting Data Flywheel.

**Architecture:** Keep `artifacts/runs`, `artifacts/benchmark-executions`, and `artifacts/exports` as immutable trajectory and dataset artifacts, and add `.seektalent/flywheel.sqlite3` as the queryable local index. Runtime writes canonical query and hit rows, eval writes judge labels and judge-consistent outcomes, and exporters materialize JSONL datasets through `ArtifactStore` manifests.

**Tech Stack:** Python 3.12, `sqlite3`, Pydantic, existing `ArtifactStore`, JSON/JSONL artifacts, pytest, existing SeekTalent runtime/eval modules.

---

## Scope Check

This is one connected data-pipeline change, not a set of independent products. It touches artifact registration, local SQLite schema, eval caching, runtime retrieval recording, outcome materialization, dataset export, and old judge-cache deletion. The tasks below keep those changes isolated by commit boundary.

## File Structure

- Create `src/seektalent/flywheel/__init__.py`: public exports for flywheel helpers.
- Create `src/seektalent/flywheel/store.py`: SQLite schema, connection pragmas, canonical JSON, row upserts, label cache API, export ledger writes.
- Create `src/seektalent/flywheel/runtime.py`: converts runtime objects into `FlywheelStore` rows and materializes flywheel run artifacts.
- Create `src/seektalent/flywheel/outcomes.py`: runtime query outcomes, judge query outcomes, term events, and term outcomes.
- Create `src/seektalent/flywheel/datasets.py`: deterministic dataset export builder.
- Create `src/seektalent/resumes/__init__.py`: resume package marker.
- Create `src/seektalent/resumes/snapshots.py`: neutral resume snapshot canonicalization and hash helpers shared by runtime and evaluation.
- Modify `src/seektalent/artifacts/models.py`: add `ArtifactKind.EXPORT`.
- Modify `src/seektalent/artifacts/store.py`: add `exports` root and `export_manifest.json`.
- Modify `src/seektalent/artifacts/registry.py`: register `flywheel.*` logical artifacts.
- Modify `src/seektalent/config.py`: add `flywheel_db_path` setting and `flywheel_path` property.
- Modify `src/seektalent/evaluation.py`: replace active `JudgeCache` with `FlywheelStore`.
- Modify `src/seektalent/runtime/orchestrator.py`: wire `FlywheelStore` at run start, round end, scoring end, and eval end.
- Modify `src/seektalent/runtime/retrieval_runtime.py`: include snapshot hash and hit sequence in query hit rows.
- Modify `src/seektalent/models.py`: extend `QueryResumeHit` if needed for snapshot/hash/sequence fields.
- Modify `src/seektalent/cli.py`: update eval/cache wording and add dataset export command if no existing command fits.
- Modify `docs/outputs.md`: document flywheel DB, artifacts, and export root.
- Create `tests/test_flywheel_store.py`: low-level schema and cache tests.
- Create `tests/test_flywheel_runtime.py`: runtime row-building and materialization tests.
- Create `tests/test_flywheel_datasets.py`: deterministic export tests.
- Modify `tests/test_artifact_store.py`: export artifact kind and flywheel logical artifact tests.
- Modify `tests/test_evaluation.py`: replace judge cache tests with flywheel label tests.
- Modify `tests/test_runtime_audit.py` and `tests/test_runtime_state_flow.py`: assert flywheel rows/artifacts are populated.
- Modify `tests/test_llm_lifecycle.py` and `tests/test_llm_fail_fast.py`: remove repo-root `.seektalent/cache-test-*` leakage.

---

### Task 1: Add Export Artifacts And Flywheel Logical Names

**Files:**
- Modify: `src/seektalent/artifacts/models.py`
- Modify: `src/seektalent/artifacts/store.py`
- Modify: `src/seektalent/artifacts/registry.py`
- Modify: `tests/test_artifact_store.py`

- [ ] **Step 1: Write failing tests for `export` artifact kind**

Add this case to `test_create_root_uses_kind_specific_manifest_names` in `tests/test_artifact_store.py`:

```python
("export", "exports", "export_manifest.json"),
```

Add this test:

```python
def test_export_root_registers_flywheel_dataset_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_time(monkeypatch)
    store = ArtifactStore(tmp_path / "artifacts")
    session = store.create_root(kind="export", display_name="query rewriting export", producer="FlywheelDatasetBuilder")

    session.write_jsonl("flywheel.query_outcomes", [{"run_id": "run-1", "query_instance_id": "q1"}])
    session.write_jsonl("flywheel.query_judge_outcomes", [{"run_id": "run-1", "query_instance_id": "q1"}])
    session.write_jsonl("flywheel.term_events", [{"run_id": "run-1", "term_event_id": "event-1"}])
    session.write_jsonl("flywheel.term_outcomes", [{"run_id": "run-1", "term_event_id": "event-1"}])
    session.write_jsonl("flywheel.query_rewrite_samples", [{"sample_id": "sample-1"}])
    session.write_json("flywheel.dataset_export_manifest", {"export_id": "export-1"})

    resolver = session.resolver()
    assert resolver.resolve("flywheel.query_outcomes") == session.root / "flywheel/query_outcomes.jsonl"
    assert resolver.resolve("flywheel.query_judge_outcomes") == session.root / "flywheel/query_judge_outcomes.jsonl"
    assert resolver.resolve("flywheel.term_events") == session.root / "flywheel/term_events.jsonl"
    assert resolver.resolve("flywheel.term_outcomes") == session.root / "flywheel/term_outcomes.jsonl"
    assert resolver.resolve("flywheel.query_rewrite_samples") == session.root / "flywheel/query_rewrite_samples.jsonl"
    assert resolver.resolve("flywheel.dataset_export_manifest") == session.root / "flywheel/dataset_export_manifest.json"
```

- [ ] **Step 2: Run artifact tests and verify failure**

Run:

```bash
uv run pytest tests/test_artifact_store.py::test_create_root_uses_kind_specific_manifest_names tests/test_artifact_store.py::test_export_root_registers_flywheel_dataset_artifacts -q
```

Expected: FAIL because `ArtifactKind("export")` is invalid or `flywheel.*` descriptors are missing.

- [ ] **Step 3: Add export artifact kind**

Modify `src/seektalent/artifacts/models.py`:

```python
class ArtifactKind(StrEnum):
    RUN = "run"
    BENCHMARK = "benchmark"
    REPLAY = "replay"
    DEBUG = "debug"
    IMPORT = "import"
    EXPORT = "export"
```

Modify `src/seektalent/artifacts/store.py`:

```python
def collection_root_for_kind(kind: ArtifactKind) -> str:
    return {
        ArtifactKind.RUN: "runs",
        ArtifactKind.BENCHMARK: "benchmark-executions",
        ArtifactKind.REPLAY: "replays",
        ArtifactKind.DEBUG: "debug",
        ArtifactKind.IMPORT: "imports",
        ArtifactKind.EXPORT: "exports",
    }[kind]
```

```python
MANIFEST_FILENAME_BY_KIND = {
    ArtifactKind.RUN: "run_manifest.json",
    ArtifactKind.BENCHMARK: "benchmark_manifest.json",
    ArtifactKind.REPLAY: "replay_manifest.json",
    ArtifactKind.DEBUG: "debug_manifest.json",
    ArtifactKind.IMPORT: "import_manifest.json",
    ArtifactKind.EXPORT: "export_manifest.json",
}
```

```python
SUMMARY_LOGICAL_ARTIFACT_BY_KIND = {
    ArtifactKind.RUN: "output.run_summary",
    ArtifactKind.BENCHMARK: "output.summary",
    ArtifactKind.EXPORT: "flywheel.dataset_export_manifest",
}
```

- [ ] **Step 4: Register flywheel logical artifacts**

Add to `STATIC_ENTRIES` in `src/seektalent/artifacts/registry.py`:

```python
    "flywheel.query_outcomes": LogicalArtifactEntry(
        path="flywheel/query_outcomes.jsonl",
        content_type="application/jsonl",
        schema_version="v1",
    ),
    "flywheel.query_judge_outcomes": LogicalArtifactEntry(
        path="flywheel/query_judge_outcomes.jsonl",
        content_type="application/jsonl",
        schema_version="v1",
    ),
    "flywheel.term_events": LogicalArtifactEntry(
        path="flywheel/term_events.jsonl",
        content_type="application/jsonl",
        schema_version="v1",
    ),
    "flywheel.term_outcomes": LogicalArtifactEntry(
        path="flywheel/term_outcomes.jsonl",
        content_type="application/jsonl",
        schema_version="v1",
    ),
    "flywheel.query_rewrite_samples": LogicalArtifactEntry(
        path="flywheel/query_rewrite_samples.jsonl",
        content_type="application/jsonl",
        schema_version="v1",
    ),
    "flywheel.dataset_export_manifest": LogicalArtifactEntry(
        path="flywheel/dataset_export_manifest.json",
        content_type="application/json",
        schema_version="v1",
    ),
```

- [ ] **Step 5: Run artifact tests**

Run:

```bash
uv run pytest tests/test_artifact_store.py::test_create_root_uses_kind_specific_manifest_names tests/test_artifact_store.py::test_export_root_registers_flywheel_dataset_artifacts -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/seektalent/artifacts/models.py src/seektalent/artifacts/store.py src/seektalent/artifacts/registry.py tests/test_artifact_store.py
git commit -m "feat: add flywheel export artifacts"
```

---

### Task 2: Add FlywheelStore Schema And Primitive APIs

**Files:**
- Create: `src/seektalent/flywheel/__init__.py`
- Create: `src/seektalent/flywheel/store.py`
- Modify: `src/seektalent/config.py`
- Create: `tests/test_flywheel_store.py`
- Modify: `.env.example`
- Modify: `src/seektalent/default.env`

- [ ] **Step 1: Write failing tests for schema, pragmas, JSON validity, and labels**

Create `tests/test_flywheel_store.py`:

```python
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

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
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest tests/test_flywheel_store.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'seektalent.flywheel'`.

- [ ] **Step 3: Add config setting**

Modify `src/seektalent/config.py`:

```python
    flywheel_db_path: str = ".seektalent/flywheel.sqlite3"
```

Add property near `llm_cache_path`:

```python
    @property
    def flywheel_path(self) -> Path:
        return resolve_path_from_root(self.flywheel_db_path, root=self.project_root)
```

Add to `.env.example` and `src/seektalent/default.env` near artifact/cache settings:

```dotenv
# Query Rewriting Data Flywheel 本地 SQLite 索引库；原始轨迹仍保存在 artifacts/。
SEEKTALENT_FLYWHEEL_DB_PATH=.seektalent/flywheel.sqlite3
```

- [ ] **Step 4: Implement FlywheelStore schema**

Create `src/seektalent/flywheel/__init__.py`:

```python
from seektalent.flywheel.store import (
    FLYWHEEL_LABEL_SCHEMA_VERSION,
    FlywheelStore,
    build_judge_contract_hash,
    canonical_json,
    task_sha256,
)

__all__ = [
    "FLYWHEEL_LABEL_SCHEMA_VERSION",
    "FlywheelStore",
    "build_judge_contract_hash",
    "canonical_json",
    "task_sha256",
]
```

Create `src/seektalent/flywheel/store.py` with these public constants and helpers:

```python
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
```

Add a `FlywheelStore` class in the same file. Use one `_SCHEMA_STATEMENTS` list with `CREATE TABLE IF NOT EXISTS` statements for every table in the spec. Keep JSON columns guarded, for example:

```python
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
```

Task 2 must create the full schema in one `_SCHEMA_STATEMENTS` list. Later tasks add methods and wiring only; they do not add tables. Keep DB transactions short and never perform artifact file IO, network IO, or judge calls inside a DB transaction. Use `STRICT` tables when the local SQLite version accepts a `STRICT` table suffix; otherwise use the same DDL without `STRICT` and rely on explicit column types, `CHECK(json_valid(column))`, foreign keys, and Python-side row construction.

In `_SCHEMA_STATEMENTS`, end each `CREATE TABLE` statement with `{strict}` after the closing parenthesis:

```python
_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS schema_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    ){strict}
    """,
]
```

The full DDL must include `schema_meta`, `tasks`, `resume_snapshots`, `artifact_refs`, `runs`, `run_queries`, `query_resume_hits`, `judge_labels`, `query_outcomes`, `query_judge_outcomes`, `term_events`, `term_outcomes`, `query_rewrite_samples`, and `dataset_exports`. These constraints are mandatory:

```sql
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
```

```sql
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
)
```

```sql
CREATE TABLE IF NOT EXISTS resume_snapshots (
    snapshot_sha256 TEXT PRIMARY KEY,
    source_resume_id TEXT,
    dedup_key TEXT,
    raw_json TEXT NOT NULL CHECK(json_valid(raw_json)),
    normalized_preview_json TEXT CHECK(normalized_preview_json IS NULL OR json_valid(normalized_preview_json)),
    created_at TEXT NOT NULL
)
```

```sql
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
)
```

```sql
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
)
```

```sql
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
)
```

```sql
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
)
```

```sql
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
    judge_call_artifact_ref_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (task_id, snapshot_sha256, judge_contract_hash, label_schema_version)
)
```

Create the remaining outcome/export tables in this same task with these column contracts:

```sql
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
)
```

```sql
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
)
```

```sql
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
)
```

```sql
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
)
```

```sql
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
)
```

```sql
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
)
```

- [ ] **Step 5: Add primitive upsert and label methods**

Add methods to `FlywheelStore`:

```python
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
```

```python
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
```

```python
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
```

```python
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
```

- [ ] **Step 6: Run store tests**

Run:

```bash
uv run pytest tests/test_flywheel_store.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/seektalent/flywheel src/seektalent/config.py .env.example src/seektalent/default.env tests/test_flywheel_store.py
git commit -m "feat: add flywheel sqlite store"
```

---

### Task 3: Replace JudgeCache In Evaluation

**Files:**
- Create: `src/seektalent/resumes/__init__.py`
- Create: `src/seektalent/resumes/snapshots.py`
- Modify: `src/seektalent/evaluation.py`
- Modify: `tests/test_evaluation.py`
- Modify: `src/seektalent/cli.py`
- Modify: `docs/outputs.md`

- [ ] **Step 1: Replace old cache tests with flywheel label tests**

In `tests/test_evaluation.py`, remove imports of `JudgeCache` and `migrate_judge_assets`. Add imports:

```python
from seektalent.flywheel.store import FLYWHEEL_LABEL_SCHEMA_VERSION, FlywheelStore, build_judge_contract_hash
```

Replace `test_judge_cache_round_trip` with:

```python
def test_resume_judge_cache_uses_flywheel_judge_contract(tmp_path: Path) -> None:
    store = FlywheelStore(tmp_path / ".seektalent" / "flywheel.sqlite3")
    task_id = store.upsert_task(job_title="Agent Engineer", jd_text="JD text", notes_text="Prefer agents")
    store.upsert_resume_snapshot(
        snapshot_sha256="snapshot-1",
        source_resume_id="resume-1",
        dedup_key="resume-1",
        raw_payload={"resume_id": "resume-1"},
        normalized_preview={"search_text": "agent"},
    )
    contract = build_judge_contract_hash(
        judge_model_id="deepseek-v4-pro",
        judge_protocol_family="openai_chat_completions_compatible",
        judge_provider_label="bailian",
        judge_endpoint_kind="openai-compatible",
        structured_output_mode="strict_native_schema",
        judge_prompt_hash="prompt-hash",
        judge_policy_version="resume-judge-v1",
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
        judge_prompt_hash="prompt-hash",
        judge_contract_hash=contract,
        judge_policy_version="resume-judge-v1",
        label_schema_version=FLYWHEEL_LABEL_SCHEMA_VERSION,
        judge_output_schema_hash="schema-hash",
        reasoning_effort=None,
        temperature=0.0,
        score=3,
        rationale="Strong direct match.",
        label_payload={"score": 3, "rationale": "Strong direct match."},
        judge_prompt_text="judge prompt",
    )

    assert store.get_cached_judge_label(
        task_id=task_id,
        snapshot_sha256="snapshot-1",
        judge_contract_hash=contract,
        label_schema_version=FLYWHEEL_LABEL_SCHEMA_VERSION,
    ) == {"score": 3, "rationale": "Strong direct match."}
    store.close()
```

Replace `test_resume_judge_cache_uses_task_and_resume_without_model` with a test that expects a miss when prompt hash changes. Add a cache metrics assertion in the same test file:

```python
def test_resume_judge_reports_flywheel_cache_hits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = FlywheelStore(tmp_path / "flywheel.sqlite3")
    task_id = store.upsert_task(job_title="Agent Engineer", jd_text="JD", notes_text="")
    store.upsert_resume_snapshot(
        snapshot_sha256="snapshot-1",
        source_resume_id="resume-1",
        dedup_key="resume-1",
        raw_payload={"resume_id": "resume-1"},
        normalized_preview={"search_text": "agent"},
    )
    contract = build_judge_contract_hash(
        judge_model_id="deepseek-v4-pro",
        judge_protocol_family="openai_chat_completions_compatible",
        judge_provider_label="bailian",
        judge_endpoint_kind="openai-compatible",
        structured_output_mode="strict_native_schema",
        judge_prompt_hash="prompt-hash",
        judge_policy_version="resume-judge-v1",
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
        judge_prompt_hash="prompt-hash",
        judge_contract_hash=contract,
        judge_policy_version="resume-judge-v1",
        label_schema_version=FLYWHEEL_LABEL_SCHEMA_VERSION,
        judge_output_schema_hash="schema-hash",
        reasoning_effort=None,
        temperature=0.0,
        score=3,
        rationale="Strong direct match.",
        label_payload={"score": 3, "rationale": "Strong direct match."},
        judge_prompt_text="judge prompt",
    )
    summary = store.judge_cache_summary(task_id=task_id, judge_contract_hash=contract)
    assert summary == {"hits": 1, "contract_hash": contract}
    store.close()
```

- [ ] **Step 2: Run focused eval tests and verify failure**

Run:

```bash
uv run pytest tests/test_evaluation.py::test_resume_judge_cache_uses_flywheel_judge_contract -q
```

Expected: FAIL until evaluation imports and APIs are updated.

- [ ] **Step 3: Update evaluation task hash and judge contract helpers**

Create `src/seektalent/resumes/__init__.py`:

```python
"""Resume source and snapshot helpers."""
```

Create `src/seektalent/resumes/snapshots.py` before changing evaluation:

```python
from __future__ import annotations

from hashlib import sha256
from typing import Any

from seektalent.flywheel.store import canonical_json


def canonical_resume_snapshot_payload(raw_payload: dict[str, Any]) -> dict[str, Any]:
    return raw_payload


def snapshot_sha256(raw_payload: dict[str, Any]) -> str:
    return sha256(canonical_json(canonical_resume_snapshot_payload(raw_payload)).encode("utf-8")).hexdigest()
```

In `src/seektalent/evaluation.py`, remove `JudgeCache`, `_cache_path`, `migrate_judge_assets`, and old cache schema helpers. Move snapshot hashing out of evaluation into `seektalent.resumes.snapshots`, then import it from there. Change `task_sha256` signature:

```python
from seektalent.flywheel.store import (
    FLYWHEEL_LABEL_SCHEMA_VERSION,
    FlywheelStore,
    build_judge_contract_hash,
    canonical_json,
    task_sha256 as flywheel_task_sha256,
)
from seektalent.llm import resolve_stage_model_config
from seektalent.resumes.snapshots import snapshot_sha256
```

```python
JUDGE_POLICY_VERSION = "resume-judge-v1"


def task_sha256(jd: str, notes: str = "", job_title: str = "") -> str:
    return flywheel_task_sha256(job_title=job_title, jd=jd, notes=notes)
```

Add:

```python
def _judge_contract_hash(settings: AppSettings, prompt: LoadedPrompt) -> str:
    config = resolve_stage_model_config(settings, stage="judge")
    output_schema_hash = sha256(canonical_json(ResumeJudgeResult.model_json_schema()).encode("utf-8")).hexdigest()
    return build_judge_contract_hash(
        judge_model_id=config.model_id,
        judge_protocol_family=config.protocol_family,
        judge_provider_label=config.provider_label,
        judge_endpoint_kind=config.endpoint_kind,
        structured_output_mode=config.structured_output_mode,
        judge_prompt_hash=prompt.sha256,
        judge_policy_version=JUDGE_POLICY_VERSION,
        label_schema_version=FLYWHEEL_LABEL_SCHEMA_VERSION,
        judge_output_schema_hash=output_schema_hash,
        reasoning_effort=config.reasoning_effort,
        temperature=0.0,
    )
```

- [ ] **Step 4: Update `ResumeJudge.judge_many` to use `FlywheelStore`**

Change signature:

```python
    async def judge_many(
        self,
        *,
        task_id: str,
        candidates: list[ResumeCandidate],
        store: FlywheelStore,
        judge_limiter: AsyncJudgeLimiter | None = None,
    ) -> tuple[dict[str, tuple[ResumeJudgeResult, bool, int]], list[JudgeLabelWrite]]:
```

Change cache lookup:

```python
contract_hash = _judge_contract_hash(self.settings, self.prompt)
cached_payload = store.get_cached_judge_label(
    task_id=task_id,
    snapshot_sha256=snapshot_hash,
    judge_contract_hash=contract_hash,
    label_schema_version=FLYWHEEL_LABEL_SCHEMA_VERSION,
)
if cached_payload is not None:
    cached = ResumeJudgeResult.model_validate(cached_payload)
    results[candidate.resume_id] = (cached, True, 0)
```

Change `JudgeLabelWrite` fields:

```python
@dataclass(frozen=True)
class JudgeLabelWrite:
    task_id: str
    snapshot_sha256: str
    judge_model_id: str
    judge_protocol_family: str
    judge_provider_label: str
    judge_endpoint_kind: str
    structured_output_mode: str
    judge_prompt_hash: str
    judge_contract_hash: str
    judge_output_schema_hash: str
    reasoning_effort: str | None
    temperature: float | None
    result: ResumeJudgeResult
    judge_prompt_text: str | None = None
    latency_ms: int | None = None
```

- [ ] **Step 5: Update `evaluate_run` to create and use `FlywheelStore`**

Replace:

```python
cache = JudgeCache(settings.project_root)
```

with:

```python
store = FlywheelStore(settings.flywheel_path)
```

After `job_title` is loaded:

```python
task_id = store.upsert_task(job_title=job_title or "", jd_text=jd, notes_text=notes)
```

For each unique candidate:

```python
store.upsert_resume_snapshot(
    snapshot_sha256=snapshot_hash,
    source_resume_id=candidate.source_resume_id or candidate.resume_id,
    dedup_key=candidate.dedup_key,
    raw_payload=candidate.raw,
    normalized_preview={"search_text": candidate.search_text},
)
```

Call judge:

```python
judged, pending_cache_writes = await ResumeJudge(settings, prompt).judge_many(
    task_id=task_id,
    candidates=list(unique_candidates.values()),
    store=store,
    judge_limiter=judge_limiter,
)
for write in pending_cache_writes:
    store.record_judge_label(
        task_id=write.task_id,
        snapshot_sha256=write.snapshot_sha256,
        judge_model_id=write.judge_model_id,
        judge_protocol_family=write.judge_protocol_family,
        judge_provider_label=write.judge_provider_label,
        judge_endpoint_kind=write.judge_endpoint_kind,
        structured_output_mode=write.structured_output_mode,
        judge_prompt_hash=write.judge_prompt_hash,
        judge_contract_hash=write.judge_contract_hash,
        judge_policy_version=JUDGE_POLICY_VERSION,
        label_schema_version=FLYWHEEL_LABEL_SCHEMA_VERSION,
        judge_output_schema_hash=write.judge_output_schema_hash,
        reasoning_effort=write.reasoning_effort,
        temperature=write.temperature,
        score=write.result.score,
        rationale=write.result.rationale,
        label_payload=write.result.model_dump(mode="json"),
        judge_prompt_text=write.judge_prompt_text,
        latency_ms=write.latency_ms,
    )
```

- [ ] **Step 6: Update tests and docs wording**

Replace visible `judge_cache` wording in CLI/docs with `flywheel.sqlite3`. Update tests that assert `.seektalent/judge_cache.sqlite3` exists to assert `.seektalent/flywheel.sqlite3` exists.

- [ ] **Step 7: Run eval tests**

Run:

```bash
uv run pytest tests/test_evaluation.py -q
```

Expected: PASS after removing old cache tests and replacing with flywheel tests.

- [ ] **Step 8: Commit**

```bash
git add src/seektalent/resumes src/seektalent/evaluation.py src/seektalent/cli.py docs/outputs.md tests/test_evaluation.py
git commit -m "refactor: replace judge cache with flywheel labels"
```

---

### Task 4: Persist Runs, Canonical Queries, Snapshots, And Query Hits

**Files:**
- Modify: `src/seektalent/flywheel/store.py`
- Create: `src/seektalent/flywheel/runtime.py`
- Modify: `src/seektalent/resumes/snapshots.py`
- Modify: `src/seektalent/models.py`
- Modify: `src/seektalent/runtime/retrieval_runtime.py`
- Modify: `src/seektalent/runtime/orchestrator.py`
- Create: `tests/test_flywheel_runtime.py`
- Modify: `tests/test_runtime_audit.py`

- [ ] **Step 1: Write failing runtime flywheel tests**

Create `tests/test_flywheel_runtime.py`:

```python
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
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest tests/test_flywheel_runtime.py -q
```

Expected: FAIL because `seektalent.flywheel.runtime` and new hit fields do not exist.

- [ ] **Step 3: Extend `QueryResumeHit`**

Modify `src/seektalent/models.py`:

```python
class QueryResumeHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    query_instance_id: str
    query_fingerprint: str
    hit_sequence_no: int
    snapshot_sha256: str | None = None
    snapshot_missing_reason: str | None = None
    resume_id: str
    round_no: int
    lane_type: LaneType
    location_key: str | None = None
    location_type: str | None = None
    batch_no: int
    rank_in_query: int
    rank_global_in_query: int | None = None
    provider_name: str
    provider_page_no: int | None = None
    provider_fetch_no: int | None = None
    provider_score_if_any: float | None = None
    dedup_key: str | None = None
    was_new_to_pool: bool
    was_duplicate: bool
    scored_fit_bucket: FitBucket | None = None
    overall_score: float | None = None
    must_have_match_score: float | None = None
    risk_score: float | None = None
    off_intent_reason_count: int = 0
    final_candidate_status: str | None = None
```

- [ ] **Step 4: Populate hit sequence and snapshot hash**

Modify `src/seektalent/runtime/retrieval_runtime.py` inside `_collect_page_candidates`. Add local sequence based on current hit count:

```python
hit_sequence_no = len(query_resume_hits) + 1 if record_resume_hit is not None else 0
snapshot_hash = candidate.snapshot_sha256 or snapshot_sha256(candidate.raw)
```

Import `snapshot_sha256` from the neutral resume snapshot module:

```python
from seektalent.resumes.snapshots import snapshot_sha256
```

Pass fields:

```python
hit_sequence_no=hit_sequence_no,
snapshot_sha256=snapshot_hash,
snapshot_missing_reason=None,
rank_global_in_query=rank_offset + rank_in_batch,
```

- [ ] **Step 5: Add runtime row builders**

Create `src/seektalent/flywheel/runtime.py`:

```python
from __future__ import annotations

from typing import Any

from seektalent.flywheel.store import canonical_json
from seektalent.models import QueryResumeHit, SentQueryRecord

QUERY_SPEC_SCHEMA_VERSION = "canonical-query-spec-v1"


def build_run_query_rows(
    *,
    run_id: str,
    artifact_id: str,
    sent_query_records: list[SentQueryRecord],
    canonical_query_specs: dict[str, dict[str, object]],
    job_intent_fingerprint: str,
    query_policy_version: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for record in sent_query_records:
        if record.query_instance_id is None or record.query_fingerprint is None:
            continue
        spec = canonical_query_specs.get(record.query_instance_id) or {
            "lane_type": record.lane_type,
            "query_terms": record.query_terms,
            "keyword_query": record.keyword_query,
        }
        rows.append(
            {
                "run_id": run_id,
                "round_no": record.round_no,
                "lane_type": record.lane_type,
                "query_instance_id": record.query_instance_id,
                "query_fingerprint": record.query_fingerprint,
                "query_role": record.query_role,
                "canonical_query_spec_json": canonical_json(spec),
                "query_spec_schema_version": QUERY_SPEC_SCHEMA_VERSION,
                "query_policy_version": query_policy_version,
                "job_intent_fingerprint": job_intent_fingerprint,
                "provider_name": str(spec.get("provider_name") or "cts"),
                "rendered_provider_query": str(spec.get("rendered_provider_query") or record.keyword_query),
                "keyword_query": record.keyword_query,
                "query_terms_json": canonical_json(record.query_terms),
                "filters_json": canonical_json(spec.get("provider_filters", {})) if isinstance(spec, dict) else "{}",
                "location_key": record.city,
                "batch_no": record.batch_no,
                "source_plan_version": str(record.source_plan_version),
                "selected_prf_expression": None,
                "accepted_prf_term_family_id": None,
                "fallback_reason": None,
                "artifact_ref_id": None,
            }
        )
    return rows


def query_hit_rows_from_hits(hits: list[QueryResumeHit]) -> list[dict[str, Any]]:
    return [hit.model_dump(mode="json") for hit in hits]
```

- [ ] **Step 6: Extend `FlywheelStore` with run/query/hit methods**

Use the Task 2 DDL for `artifact_refs`, `runs`, `run_queries`, and `query_resume_hits`. Add methods:

```python
def record_artifact_ref(self, *, artifact_kind: str, artifact_id: str, artifact_root: str, logical_name: str, relative_path: str | None, content_sha256: str | None, schema_version: str | None) -> str
def start_run(self, *, run_id: str, task_id: str, version: str | None, git_sha: str | None, artifact_ref_id: str | None, artifact_root: str, config_hash: str, config_payload: dict[str, Any], status: str, eval_enabled: bool, benchmark_id: str | None, benchmark_case_id: str | None) -> None
def complete_run(self, *, run_id: str, status: str, failure_summary: str | None = None) -> None
def record_run_queries(self, rows: list[dict[str, object]]) -> None
def record_query_resume_hits(self, rows: list[dict[str, object]]) -> None
```

Use one transaction per list method:

```python
with self.connect():
    self.connect().executemany(sql, values)
```

Store-owned timestamps: row builders must not emit `created_at`. `FlywheelStore` fills `created_at`, `started_at`, `completed_at`, and `updated_at` inside write methods.

- [ ] **Step 7: Wire runtime start and round hit recording**

In `WorkflowRuntime.__init__`, add:

```python
from seektalent.flywheel.store import FlywheelStore

self.flywheel_store = FlywheelStore(settings.flywheel_path)
```

In run-state build or the first point where job title/JD/notes are available:

```python
task_id = self.flywheel_store.upsert_task(job_title=job_title, jd_text=jd, notes_text=notes)
```

At run start:

```python
manifest_ref_id = self.flywheel_store.record_artifact_ref(
    artifact_kind="run",
    artifact_id=tracer.run_id,
    artifact_root=str(tracer.run_dir),
    logical_name="manifest.run",
    relative_path="manifests/run_manifest.json",
    content_sha256=None,
    schema_version="v1",
)
self.flywheel_store.start_run(
    run_id=tracer.run_id,
    task_id=task_id,
    version=None,
    git_sha=None,
    artifact_ref_id=manifest_ref_id,
    artifact_root=str(tracer.run_dir),
    config_hash=json_sha256(self._build_public_run_config()),
    config_payload=self._build_public_run_config(),
    status="running",
    eval_enabled=self.settings.enable_eval,
    benchmark_id=None,
    benchmark_case_id=None,
)
```

At provider hit ingestion, upsert the resume snapshot before inserting the query hit:

```python
snapshot_payload = canonical_resume_snapshot_payload(candidate.raw)
snapshot_hash = candidate.snapshot_sha256 or snapshot_sha256(snapshot_payload)
self.flywheel_store.upsert_resume_snapshot(
    snapshot_sha256=snapshot_hash,
    source_resume_id=candidate.source_resume_id or candidate.resume_id,
    dedup_key=candidate.dedup_key,
    raw_payload=snapshot_payload,
    normalized_preview={"search_text": candidate.search_text},
)
```

At round end after `_write_query_resume_hits`, record query rows first, then query hit rows. Normal provider-returned hits must have `snapshot_sha256`; only hits without raw payload may set `snapshot_missing_reason`.

- [ ] **Step 8: Run focused tests**

Run:

```bash
uv run pytest tests/test_flywheel_store.py tests/test_flywheel_runtime.py tests/test_runtime_audit.py::test_query_resume_hits_are_enriched_after_scoring -q
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/seektalent/flywheel/store.py src/seektalent/flywheel/runtime.py src/seektalent/resumes/snapshots.py src/seektalent/models.py src/seektalent/runtime/retrieval_runtime.py src/seektalent/runtime/orchestrator.py tests/test_flywheel_runtime.py tests/test_runtime_audit.py
git commit -m "feat: persist flywheel query hits"
```

---

### Task 5: Persist Runtime Query Outcomes And Flywheel JSONL Artifacts

**Files:**
- Create: `src/seektalent/flywheel/outcomes.py`
- Modify: `src/seektalent/flywheel/store.py`
- Modify: `src/seektalent/flywheel/runtime.py`
- Modify: `src/seektalent/runtime/retrieval_runtime.py`
- Modify: `src/seektalent/runtime/orchestrator.py`
- Modify: `tests/test_flywheel_runtime.py`
- Modify: `tests/test_runtime_state_flow.py`

- [ ] **Step 1: Add failing outcome tests**

Add to `tests/test_flywheel_runtime.py`:

```python
from seektalent.artifacts import ArtifactStore
from seektalent.flywheel.outcomes import build_runtime_query_outcome_row
from seektalent.flywheel.runtime import materialize_flywheel_run_artifacts
from seektalent.flywheel.store import FlywheelStore
from seektalent.models import QueryOutcomeClassification


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
    store.record_query_outcomes([
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
            classification=QueryOutcomeClassification(primary_label="zero_recall", labels=["zero_recall"], reasons=[]),
            thresholds_payload={},
        )
    ])
    materialize_flywheel_run_artifacts(session=session, store=store, run_id=session.manifest.artifact_id)
    rows = store.rows_for_run("query_outcomes", run_id=session.manifest.artifact_id)
    assert rows[0]["artifact_ref_id"] is not None
    assert (session.root / "flywheel/query_outcomes.jsonl").exists()
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run pytest tests/test_flywheel_runtime.py::test_zero_recall_runtime_outcome_uses_null_precision_fields -q
```

Expected: FAIL because outcome builder is missing.

- [ ] **Step 3: Add outcome builder**

Create `src/seektalent/flywheel/outcomes.py`:

```python
from __future__ import annotations

from hashlib import sha256
from typing import Any

from seektalent.flywheel.store import canonical_json
from seektalent.models import QueryOutcomeClassification

QUERY_OUTCOME_SCHEMA_VERSION = "query-outcome-v1"
QUERY_OUTCOME_POLICY_VERSION = "query-outcome-policy-v1"
DEDUPE_VERSION = "dedupe-v1"


def _avg(values: list[int]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def build_runtime_query_outcome_row(
    *,
    run_id: str,
    query_instance_id: str,
    query_fingerprint: str,
    round_no: int,
    lane_type: str,
    provider_returned_count: int,
    new_unique_resume_count: int,
    duplicate_count: int,
    scored_resume_count: int,
    new_fit_count: int,
    must_have_match_scores: list[int],
    risk_scores: list[int],
    off_intent_reason_count: int,
    classification: QueryOutcomeClassification,
    thresholds_payload: dict[str, Any],
) -> dict[str, object]:
    thresholds_json = canonical_json(thresholds_payload)
    fit_rate = new_fit_count / scored_resume_count if scored_resume_count else None
    return {
        "run_id": run_id,
        "query_instance_id": query_instance_id,
        "query_fingerprint": query_fingerprint,
        "outcome_schema_version": QUERY_OUTCOME_SCHEMA_VERSION,
        "outcome_policy_version": QUERY_OUTCOME_POLICY_VERSION,
        "outcome_thresholds_hash": sha256(thresholds_json.encode("utf-8")).hexdigest(),
        "outcome_thresholds_json": thresholds_json,
        "scoring_policy_version": None,
        "dedupe_version": DEDUPE_VERSION,
        "outcome_basis": "runtime_score",
        "round_no": round_no,
        "lane_type": lane_type,
        "provider_returned_count": provider_returned_count,
        "new_unique_resume_count": new_unique_resume_count,
        "duplicate_count": duplicate_count,
        "scored_resume_count": scored_resume_count,
        "new_fit_count": new_fit_count,
        "new_near_fit_count": 0,
        "fit_rate_denominator": "scored_resume_count" if scored_resume_count else None,
        "fit_rate": fit_rate,
        "must_have_match_avg": _avg(must_have_match_scores),
        "risk_score_avg": _avg(risk_scores),
        "off_intent_reason_count": off_intent_reason_count,
        "primary_label": classification.primary_label,
        "labels_json": canonical_json(classification.labels),
        "reasons_json": canonical_json(classification.reasons),
        "latency_ms": None,
        "cost_estimate_usd": None,
        "artifact_ref_id": None,
    }
```

- [ ] **Step 4: Add store method for runtime outcomes**

The `query_outcomes` table already exists from Task 2. Add the store method:

```python
def record_query_outcomes(self, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    now = utc_now()
    values = []
    for row in rows:
        if "created_at" in row:
            raise ValueError("created_at is owned by FlywheelStore")
        values.append({**row, "created_at": now})
    with self.connect():
        self.connect().executemany(
            """
            INSERT INTO query_outcomes (
                run_id, query_instance_id, query_fingerprint, outcome_schema_version,
                outcome_policy_version, outcome_thresholds_hash, outcome_thresholds_json,
                scoring_policy_version, dedupe_version, outcome_basis, round_no, lane_type,
                provider_returned_count, new_unique_resume_count, duplicate_count,
                scored_resume_count, new_fit_count, new_near_fit_count, fit_rate_denominator,
                fit_rate, must_have_match_avg, risk_score_avg, off_intent_reason_count,
                primary_label, labels_json, reasons_json, latency_ms, cost_estimate_usd,
                artifact_ref_id, created_at
            ) VALUES (
                :run_id, :query_instance_id, :query_fingerprint, :outcome_schema_version,
                :outcome_policy_version, :outcome_thresholds_hash, :outcome_thresholds_json,
                :scoring_policy_version, :dedupe_version, :outcome_basis, :round_no, :lane_type,
                :provider_returned_count, :new_unique_resume_count, :duplicate_count,
                :scored_resume_count, :new_fit_count, :new_near_fit_count, :fit_rate_denominator,
                :fit_rate, :must_have_match_avg, :risk_score_avg, :off_intent_reason_count,
                :primary_label, :labels_json, :reasons_json, :latency_ms, :cost_estimate_usd,
                :artifact_ref_id, :created_at
            )
            ON CONFLICT(run_id, query_instance_id) DO UPDATE SET
                primary_label = excluded.primary_label,
                labels_json = excluded.labels_json,
                reasons_json = excluded.reasons_json
            """,
            values,
        )
```

- [ ] **Step 5: Materialize flywheel JSONL artifacts**

Add to `src/seektalent/flywheel/runtime.py`:

```python
from hashlib import sha256

RUN_MATERIALIZED_TABLES = {
    "query_outcomes": "flywheel.query_outcomes",
    "query_judge_outcomes": "flywheel.query_judge_outcomes",
    "term_events": "flywheel.term_events",
    "term_outcomes": "flywheel.term_outcomes",
}


def materialize_flywheel_run_artifacts(*, session, store, run_id: str) -> None:
    for table, logical_name in RUN_MATERIALIZED_TABLES.items():
        rows = store.rows_for_run(table, run_id=run_id)
        if not rows:
            continue
        path = session.write_jsonl(logical_name, rows)
        content_sha = sha256(path.read_bytes()).hexdigest()
        artifact_ref_id = store.record_artifact_ref(
            artifact_kind=session.manifest.artifact_kind,
            artifact_id=session.manifest.artifact_id,
            artifact_root=str(session.root),
            logical_name=logical_name,
            relative_path=str(path.relative_to(session.root)),
            content_sha256=content_sha,
            schema_version="v1",
        )
        store.attach_artifact_ref_to_run_rows(table=table, run_id=run_id, artifact_ref_id=artifact_ref_id)
```

Add `rows_for_run(self, table: str, run_id: str) -> list[dict[str, object]]` to `FlywheelStore`, with a whitelist:

```python
ALLOWED_RUN_ROW_TABLES = {
    "query_outcomes",
    "query_judge_outcomes",
    "term_events",
    "term_outcomes",
}
```

Add `attach_artifact_ref_to_run_rows(self, *, table: str, run_id: str, artifact_ref_id: str) -> None` using the same table whitelist.

- [ ] **Step 6: Wire runtime outcome persistence**

Compute `query_outcomes` from persisted `query_resume_hits` after scoring enrichment. Runtime classification may provide the label decision, but denominator counts must come from the hit ledger:

```python
hits = self.flywheel_store.query_hits_for_run_round(run_id=tracer.run_id, round_no=round_no)
outcome_rows = build_runtime_query_outcome_rows_from_hits(
    run_id=tracer.run_id,
    hits=hits,
    classifications=latest_dispatch_outcomes,
    thresholds_payload=self.settings.query_outcome_thresholds_payload(),
)
self.flywheel_store.record_query_outcomes(outcome_rows)
```

- [ ] **Step 7: Run focused tests**

Run:

```bash
uv run pytest tests/test_flywheel_runtime.py tests/test_runtime_state_flow.py::test_query_outcome_scoring_noop_tracer_exposes_session_contract -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/seektalent/flywheel/outcomes.py src/seektalent/flywheel/store.py src/seektalent/flywheel/runtime.py src/seektalent/runtime/retrieval_runtime.py src/seektalent/runtime/orchestrator.py tests/test_flywheel_runtime.py tests/test_runtime_state_flow.py
git commit -m "feat: persist runtime query outcomes"
```

---

### Task 6: Persist Judge-Consistent Query Outcomes After Eval

**Files:**
- Modify: `src/seektalent/flywheel/outcomes.py`
- Modify: `src/seektalent/flywheel/store.py`
- Modify: `src/seektalent/evaluation.py`
- Modify: `tests/test_evaluation.py`

- [ ] **Step 1: Write failing judge outcome test**

Add to `tests/test_evaluation.py`:

```python
def test_evaluate_run_writes_query_judge_outcomes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("seektalent.evaluation._log_to_wandb", lambda **kwargs: None)
    monkeypatch.setattr("seektalent.evaluation._log_to_weave", lambda **kwargs: None)

    async def fake_judge_many(self, *, task_id, candidates, store, judge_limiter=None):  # noqa: ANN001
        result = ResumeJudgeResult(score=3, rationale="Strong fit")
        return ({candidate.resume_id: (result, False, 1) for candidate in candidates}, [])

    monkeypatch.setattr("seektalent.evaluation.ResumeJudge.judge_many", fake_judge_many)
    settings = make_settings(runs_dir=str(tmp_path / "runs"), enable_eval=True, flywheel_db_path=str(tmp_path / "flywheel.sqlite3"))
    prompt = LoadedPrompt(name="judge", path=tmp_path / "judge.md", content="judge prompt", sha256="prompt-hash")
    candidate = ResumeCandidate(
        resume_id="resume-1",
        source_resume_id="resume-1",
        snapshot_sha256="snapshot-1",
        dedup_key="resume-1",
        search_text="agent",
        raw={"resume_id": "resume-1", "skill": "agent"},
    )
    store = ArtifactStore(tmp_path / "artifacts")
    session = store.create_root(kind="run", display_name="seek talent workflow run", producer="WorkflowRuntime")
    session.write_json("input.input_truth", {"job_title": "Agent Engineer", "jd": "JD text", "notes": ""})
    session.write_json(
        "round.01.retrieval.query_resume_hits",
        [
            {
                "run_id": session.manifest.artifact_id,
                "query_instance_id": "query-1",
                "query_fingerprint": "fingerprint-1",
                "hit_sequence_no": 1,
                "snapshot_sha256": "snapshot-1",
                "resume_id": "resume-1",
                "round_no": 1,
                "lane_type": "exploit",
                "batch_no": 1,
                "rank_in_query": 1,
                "provider_name": "cts",
                "was_new_to_pool": True,
                "was_duplicate": False,
                "final_candidate_status": "fit",
            }
        ],
    )
    flywheel = FlywheelStore(tmp_path / "flywheel.sqlite3")
    task_id = flywheel.upsert_task(job_title="Agent Engineer", jd_text="JD text", notes_text="")
    flywheel.upsert_resume_snapshot(
        snapshot_sha256="snapshot-1",
        source_resume_id="resume-1",
        dedup_key="resume-1",
        raw_payload={"resume_id": "resume-1", "skill": "agent"},
        normalized_preview={"search_text": "agent"},
    )
    flywheel.start_run(
        run_id=session.manifest.artifact_id,
        task_id=task_id,
        version="0.6.2",
        git_sha="abc123",
        artifact_ref_id=None,
        artifact_root=str(session.root),
        config_hash="config",
        config_payload={},
        status="completed",
        eval_enabled=True,
        benchmark_id=None,
        benchmark_case_id=None,
    )
    flywheel.record_run_queries([
        {
            "run_id": session.manifest.artifact_id,
            "round_no": 1,
            "lane_type": "exploit",
            "query_instance_id": "query-1",
            "query_fingerprint": "fingerprint-1",
            "query_role": "exploit",
            "canonical_query_spec_json": "{}",
            "query_spec_schema_version": "canonical-query-spec-v1",
            "query_policy_version": "query-policy-v1",
            "job_intent_fingerprint": "intent-1",
            "provider_name": "cts",
            "rendered_provider_query": "agent",
            "keyword_query": "agent",
            "query_terms_json": "[]",
            "filters_json": "{}",
            "artifact_ref_id": None,
        }
    ])
    flywheel.record_query_resume_hits([
        {
            "run_id": session.manifest.artifact_id,
            "query_instance_id": "query-1",
            "query_fingerprint": "fingerprint-1",
            "hit_sequence_no": 1,
            "snapshot_sha256": "snapshot-1",
            "snapshot_missing_reason": None,
            "resume_id": "resume-1",
            "round_no": 1,
            "lane_type": "exploit",
            "batch_no": 1,
            "rank_in_query": 1,
            "provider_name": "cts",
            "was_new_to_pool": True,
            "was_duplicate": False,
            "final_candidate_status": "fit",
        }
    ])
    flywheel.close()

    asyncio.run(
        evaluate_run(
            settings=settings,
            prompt=prompt,
            run_id=session.manifest.artifact_id,
            run_dir=session.root,
            jd="JD text",
            round_01_candidates=[candidate],
            final_candidates=[candidate],
            rounds_executed=1,
        )
    )

    conn = sqlite3.connect(tmp_path / "flywheel.sqlite3")
    try:
        count = conn.execute("SELECT COUNT(*) FROM query_judge_outcomes").fetchone()[0]
    finally:
        conn.close()
    assert count >= 1
```

Add a pure outcome test to `tests/test_flywheel_runtime.py`:

```python
from seektalent.flywheel.outcomes import build_query_judge_outcome_rows


def test_query_judge_outcome_counts_only_new_hits_as_gain() -> None:
    rows = build_query_judge_outcome_rows(
        run_id="run-1",
        task_id="task-1",
        query_hits=[
            {
                "query_instance_id": "query-1",
                "query_fingerprint": "fingerprint-1",
                "snapshot_sha256": "snapshot-old",
                "was_new_to_pool": False,
                "was_duplicate": True,
            },
            {
                "query_instance_id": "query-1",
                "query_fingerprint": "fingerprint-1",
                "snapshot_sha256": "snapshot-new",
                "was_new_to_pool": True,
                "was_duplicate": False,
            },
        ],
        judged_by_snapshot={
            "snapshot-old": {"score": 3},
            "snapshot-new": {"score": 1},
        },
        judge_contract_hash="contract",
        judge_model_id="deepseek-v4-pro",
        judge_prompt_hash="prompt",
        label_schema_version="judge-label-v1",
        thresholds_payload={},
    )
    assert rows[0]["new_judge_positive_count"] == 0
    assert rows[0]["judged_resume_count"] == 1
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run pytest tests/test_evaluation.py::test_evaluate_run_writes_query_judge_outcomes -q
```

Expected: FAIL because `query_judge_outcomes` is not created or populated.

- [ ] **Step 3: Add judge outcome builder**

In `src/seektalent/flywheel/outcomes.py`, add `build_query_judge_outcome_rows`:

```python
JUDGE_QUERY_OUTCOME_SCHEMA_VERSION = "query-judge-outcome-v1"


def build_query_judge_outcome_rows(
    *,
    run_id: str,
    task_id: str,
    query_hits: list[dict[str, object]],
    judged_by_snapshot: dict[str, dict[str, object]],
    judge_contract_hash: str,
    judge_model_id: str,
    judge_prompt_hash: str,
    label_schema_version: str,
    thresholds_payload: dict[str, Any],
) -> list[dict[str, object]]:
    rows_by_query: dict[str, list[dict[str, object]]] = {}
    for hit in query_hits:
        snapshot = hit.get("snapshot_sha256")
        if not snapshot:
            continue
        rows_by_query.setdefault(str(hit["query_instance_id"]), []).append(hit)

    thresholds_json = canonical_json(thresholds_payload)
    threshold_hash = sha256(thresholds_json.encode("utf-8")).hexdigest()
    rows: list[dict[str, object]] = []
    for query_instance_id, hits in rows_by_query.items():
        new_hits = [hit for hit in hits if hit.get("was_new_to_pool")]
        judged_new_hits = [
            judged_by_snapshot[str(hit["snapshot_sha256"])]
            for hit in new_hits
            if str(hit["snapshot_sha256"]) in judged_by_snapshot
        ]
        positive_count = sum(1 for item in judged_new_hits if int(item["score"]) >= 2)
        positive_rate = positive_count / len(judged_new_hits) if judged_new_hits else None
        if not judged_new_hits:
            labels = ["judge_coverage_missing"]
            reasons = ["no new query hits had judge labels"]
        elif positive_count:
            labels = ["marginal_gain"]
            reasons = ["new judge-positive resumes joined to query hits"]
        else:
            labels = ["low_recall_high_precision"]
            reasons = ["new query hits were judged but no positive label was found"]
        rows.append(
            {
                "run_id": run_id,
                "query_instance_id": query_instance_id,
                "query_fingerprint": str(hits[0]["query_fingerprint"]),
                "task_id": task_id,
                "judge_contract_hash": judge_contract_hash,
                "judge_model_id": judge_model_id,
                "judge_prompt_hash": judge_prompt_hash,
                "label_schema_version": label_schema_version,
                "outcome_schema_version": JUDGE_QUERY_OUTCOME_SCHEMA_VERSION,
                "outcome_policy_version": "query-judge-outcome-policy-v1",
                "outcome_thresholds_hash": threshold_hash,
                "outcome_thresholds_json": thresholds_json,
                "provider_returned_count": len(hits),
                "new_unique_resume_count": sum(1 for hit in hits if hit.get("was_new_to_pool")),
                "judged_resume_count": len(judged_new_hits),
                "new_judge_positive_count": positive_count,
                "new_judge_near_positive_count": sum(1 for item in judged_new_hits if int(item["score"]) == 2),
                "judge_positive_rate": positive_rate,
                "duplicate_count": sum(1 for hit in hits if hit.get("was_duplicate")),
                "primary_label": labels[0],
                "labels_json": canonical_json(labels),
                "reasons_json": canonical_json(reasons),
                "artifact_ref_id": None,
            }
        )
    return rows
```

- [ ] **Step 4: Add store method for judge outcomes**

The `query_judge_outcomes` table already exists from Task 2. Add `record_query_judge_outcomes(rows)` to `FlywheelStore`; the store fills `created_at`.

- [ ] **Step 5: Wire eval**

After judge labels are recorded in `evaluate_run`, load query hits from `FlywheelStore.rows_for_run("query_resume_hits", run_id=run_id)` rather than reparsing run artifact files. Build `judged_by_snapshot`, call `build_query_judge_outcome_rows`, and write rows to store.

- [ ] **Step 6: Materialize JSONL**

Call `materialize_flywheel_run_artifacts(session=session, store=store, run_id=run_id)` after eval writes judge outcomes.

- [ ] **Step 7: Run tests**

Run:

```bash
uv run pytest tests/test_evaluation.py::test_evaluate_run_writes_query_judge_outcomes tests/test_flywheel_store.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/seektalent/flywheel/outcomes.py src/seektalent/flywheel/store.py src/seektalent/evaluation.py tests/test_evaluation.py
git commit -m "feat: persist judge query outcomes"
```

---

### Task 7: Persist Term Events And Term Outcomes

**Files:**
- Modify: `src/seektalent/flywheel/outcomes.py`
- Modify: `src/seektalent/flywheel/store.py`
- Modify: `src/seektalent/runtime/orchestrator.py`
- Modify: `tests/test_flywheel_runtime.py`
- Modify: `tests/test_runtime_state_flow.py`

- [ ] **Step 1: Write failing PRF term event test**

Add to `tests/test_flywheel_runtime.py`:

```python
from seektalent.flywheel.outcomes import build_rejected_prf_term_event


def test_rejected_prf_term_event_is_not_bound_to_generic_query() -> None:
    event = build_rejected_prf_term_event(
        run_id="run-1",
        proposal_id="proposal-1",
        prf_decision_id="decision-1",
        prf_candidate_artifact_ref_id="artifact-candidates",
        prf_policy_decision_artifact_ref_id="artifact-policy",
        prf_proposal_extractor_version="llm-prf-v1",
        prf_familying_version="conservative-family-v1",
        prf_gate_version="prf-gate-v1",
        term_surface="Agent工作流",
        term_family_id="feedback.agent-workflow",
        round_no=2,
        reject_reasons=["generic_phrase"],
        supporting_resume_ids=["r1", "r2"],
        negative_resume_ids=[],
    )
    assert event["executed_query_instance_id"] is None
    assert event["selected_query_instance_id"] is None
    assert event["source"] == "llm_prf_candidate"
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run pytest tests/test_flywheel_runtime.py::test_rejected_prf_term_event_is_not_bound_to_generic_query -q
```

Expected: FAIL because builder is missing.

- [ ] **Step 3: Add term event builders**

In `src/seektalent/flywheel/outcomes.py`:

```python
TERM_OUTCOME_SCHEMA_VERSION = "term-outcome-v1"


def build_rejected_prf_term_event(
    *,
    run_id: str,
    proposal_id: str,
    prf_decision_id: str,
    prf_candidate_artifact_ref_id: str | None,
    prf_policy_decision_artifact_ref_id: str | None,
    prf_proposal_extractor_version: str,
    prf_familying_version: str,
    prf_gate_version: str,
    term_surface: str,
    term_family_id: str,
    round_no: int,
    reject_reasons: list[str],
    supporting_resume_ids: list[str],
    negative_resume_ids: list[str],
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "term_event_id": f"{proposal_id}:{term_family_id}",
        "proposal_id": proposal_id,
        "prf_decision_id": prf_decision_id,
        "prf_candidate_artifact_ref_id": prf_candidate_artifact_ref_id,
        "prf_policy_decision_artifact_ref_id": prf_policy_decision_artifact_ref_id,
        "prf_proposal_extractor_version": prf_proposal_extractor_version,
        "prf_familying_version": prf_familying_version,
        "prf_gate_version": prf_gate_version,
        "candidate_query_fingerprint": None,
        "executed_query_instance_id": None,
        "selected_query_instance_id": None,
        "term_surface": term_surface,
        "term_family_id": term_family_id,
        "term_role": "prf_candidate",
        "source": "llm_prf_candidate",
        "round_no": round_no,
        "lane_type": "prf_probe",
        "accepted_by_prf_gate": 0,
        "prf_reject_reasons_json": canonical_json(reject_reasons),
        "supporting_resume_ids_json": canonical_json(supporting_resume_ids),
        "negative_resume_ids_json": canonical_json(negative_resume_ids),
        "artifact_ref_id": None,
    }
```

Add `build_term_outcome_rows(term_events, runtime_outcomes, judge_outcomes)` that sets `execution_status` to `not_executed`, `executed_runtime`, or `executed_judge_joined`.

- [ ] **Step 4: Add store methods for term lineage**

The term lineage tables already exist from Task 2. They must include PRF lineage columns for proposal artifacts and version vector:

```text
prf_candidate_artifact_ref_id
prf_policy_decision_artifact_ref_id
prf_proposal_extractor_version
prf_familying_version
prf_gate_version
```

Add:

```python
def record_term_events(self, rows: list[dict[str, object]]) -> None
def record_term_outcomes(self, rows: list[dict[str, object]]) -> None
```

- [ ] **Step 5: Wire PRF decision events**

In `orchestrator.py`, after `_select_prf_backend_decision`, build events from:

- grounded LLM PRF candidates;
- accepted PRF expression if any;
- reject reasons from `prf_policy_decision`;
- selected query if PRF passes.

Do not bind rejected PRF terms to the fallback generic query.

- [ ] **Step 6: Wire executed query terms**

For every executed query in `sent_query_history`, record term events with:

```python
source="controller_query" or "generic_explore" or "accepted_prf_expression"
executed_query_instance_id=record.query_instance_id
selected_query_instance_id=record.query_instance_id
```

- [ ] **Step 7: Run focused tests**

Run:

```bash
uv run pytest tests/test_flywheel_runtime.py tests/test_runtime_state_flow.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/seektalent/flywheel/outcomes.py src/seektalent/flywheel/store.py src/seektalent/runtime/orchestrator.py tests/test_flywheel_runtime.py tests/test_runtime_state_flow.py
git commit -m "feat: persist flywheel term lineage"
```

---

### Task 8: Add Deterministic Dataset Export Builder

**Files:**
- Create: `src/seektalent/flywheel/datasets.py`
- Modify: `src/seektalent/flywheel/store.py`
- Modify: `src/seektalent/cli.py`
- Create: `tests/test_flywheel_datasets.py`

- [ ] **Step 1: Write failing deterministic export test**

Create `tests/test_flywheel_datasets.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from seektalent.artifacts import ArtifactStore
from seektalent.flywheel.datasets import export_query_rewriting_dataset
from seektalent.flywheel.store import FlywheelStore


def test_dataset_export_is_deterministic(tmp_path: Path) -> None:
    db_path = tmp_path / "flywheel.sqlite3"
    store = FlywheelStore(db_path)
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
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run pytest tests/test_flywheel_datasets.py -q
```

Expected: FAIL because dataset builder is missing.

- [ ] **Step 3: Add dataset builder**

Create `src/seektalent/flywheel/datasets.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from seektalent.artifacts import ArtifactStore
from seektalent.flywheel.store import FlywheelStore, canonical_json

DATASET_BUILDER_VERSION = "query-rewrite-builder-v1"
QUERY_REWRITE_SAMPLE_SCHEMA_VERSION = "query-rewrite-sample-v1"


@dataclass(frozen=True)
class DatasetExportResult:
    export_id: str
    root: object
    sha256: str
    row_count: int


def _sample_id(payload: dict[str, object]) -> str:
    return sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def export_query_rewriting_dataset(
    *,
    store: FlywheelStore,
    artifact_store: ArtifactStore,
    dataset_version: str,
    builder_config: dict[str, Any],
    run_ids: list[str],
) -> DatasetExportResult:
    rows = store.query_rewrite_source_rows(run_ids=run_ids)
    builder_config_hash = sha256(canonical_json(builder_config).encode("utf-8")).hexdigest()
    samples = []
    for row in rows:
        sample_payload = {
            "task_id": row["task_id"],
            "source_query_instance_ids": [row["query_instance_id"]],
            "dataset_version": dataset_version,
            "schema_version": QUERY_REWRITE_SAMPLE_SCHEMA_VERSION,
            "builder_version": DATASET_BUILDER_VERSION,
            "builder_config_hash": builder_config_hash,
            "sample_basis": "judge_outcome",
        }
        input_payload = {
            "job_title": row.get("job_title"),
            "requirement_digest": row.get("task_sha256"),
            "query_history": row.get("query_history", []),
            "failed_terms": row.get("failed_terms", []),
            "successful_terms": row.get("successful_terms", []),
            "prf_evidence_summaries": row.get("prf_evidence_summaries", []),
            "top_positive_signals": row.get("top_positive_signals", []),
            "top_negative_signals": row.get("top_negative_signals", []),
        }
        target_payload = {
            "select_terms": row.get("select_terms", []),
            "suppress_terms": row.get("suppress_terms", []),
            "rank_terms": row.get("rank_terms", []),
            "primary_label": row["primary_label"],
        }
        reward_payload = {
            "high_score_gain": row["new_judge_positive_count"],
            "precision_gain": row["judge_positive_rate"],
            "zero_recall_recovery": 1 if row["primary_label"] == "zero_recall_recovered" else 0,
            "duplicate_penalty": row["duplicate_count"],
            "broad_noise_penalty": 1 if row["primary_label"] == "broad_noise" else 0,
            "drift_penalty": 1 if row["primary_label"] == "off_intent" else 0,
        }
        samples.append(
            {
                "sample_id": _sample_id(sample_payload),
                "task_id": row["task_id"],
                "run_id": row["run_id"],
                "source_query_instance_ids_json": canonical_json([row["query_instance_id"]]),
                "sample_basis": "judge_outcome",
                "input_json": canonical_json(input_payload),
                "target_json": canonical_json(target_payload),
                "reward_json": canonical_json(reward_payload),
                "schema_version": QUERY_REWRITE_SAMPLE_SCHEMA_VERSION,
                "dataset_version": dataset_version,
                "builder_version": DATASET_BUILDER_VERSION,
                "builder_config_hash": builder_config_hash,
            }
        )
    samples = sorted(samples, key=lambda item: item["sample_id"])
    session = artifact_store.create_root(
        kind="export",
        display_name="query rewriting dataset export",
        producer="FlywheelDatasetBuilder",
    )
    source_artifact_refs = store.source_artifact_refs_for_runs(run_ids=run_ids)
    for table, logical_name in {
        "query_outcomes": "flywheel.query_outcomes",
        "query_judge_outcomes": "flywheel.query_judge_outcomes",
        "term_events": "flywheel.term_events",
        "term_outcomes": "flywheel.term_outcomes",
    }.items():
        session.write_jsonl(logical_name, store.rows_for_runs(table, run_ids=run_ids))
    session.write_jsonl("flywheel.query_rewrite_samples", samples)
    store.record_query_rewrite_samples(samples)
    content = "\n".join(canonical_json(item) for item in samples) + ("\n" if samples else "")
    digest = sha256(content.encode("utf-8")).hexdigest()
    manifest = {
        "dataset_version": dataset_version,
        "builder_version": DATASET_BUILDER_VERSION,
        "builder_config_hash": builder_config_hash,
        "row_count": len(samples),
        "sha256": digest,
    }
    manifest_path = session.write_json("flywheel.dataset_export_manifest", manifest)
    session.finalize(status="completed")
    manifest_ref_id = store.record_artifact_ref(
        artifact_kind="export",
        artifact_id=session.manifest.artifact_id,
        artifact_root=str(session.root),
        logical_name="flywheel.dataset_export_manifest",
        relative_path=str(manifest_path.relative_to(session.root)),
        content_sha256=sha256(manifest_path.read_bytes()).hexdigest(),
        schema_version="v1",
    )
    store.record_dataset_export(
        export_id=session.manifest.artifact_id,
        dataset_name="query_rewriting",
        dataset_version=dataset_version,
        schema_version=QUERY_REWRITE_SAMPLE_SCHEMA_VERSION,
        builder_version=DATASET_BUILDER_VERSION,
        builder_config=builder_config,
        source_run_ids=run_ids,
        source_query="query_judge_outcomes",
        source_db_sha256=sha256(store.path.read_bytes()).hexdigest(),
        source_artifact_refs=source_artifact_refs,
        git_sha=None,
        artifact_root=str(session.root),
        output_path=str(session.root / "flywheel"),
        artifact_ref_id=manifest_ref_id,
        row_count=len(samples),
        sha256_value=digest,
    )
    return DatasetExportResult(export_id=session.manifest.artifact_id, root=session.root, sha256=digest, row_count=len(samples))
```

- [ ] **Step 4: Add store query/export methods**

Add:

```python
def query_rewrite_source_rows(self, *, run_ids: list[str]) -> list[dict[str, object]]
def rows_for_runs(self, table: str, *, run_ids: list[str]) -> list[dict[str, object]]
def source_artifact_refs_for_runs(self, *, run_ids: list[str]) -> list[str]
def record_query_rewrite_samples(self, rows: list[dict[str, object]]) -> None
def record_dataset_export(self, *, export_id: str, dataset_name: str, dataset_version: str, schema_version: str, builder_version: str, builder_config: dict[str, Any], source_run_ids: list[str], source_query: str, source_db_sha256: str, source_artifact_refs: list[str], git_sha: str | None, artifact_root: str, output_path: str, artifact_ref_id: str | None, row_count: int, sha256_value: str) -> None
```

`query_rewrite_source_rows` must join `query_judge_outcomes`, `runs`, `tasks`, `run_queries`, and term outcome summaries so each row includes `job_title`, `task_sha256`, `query_history`, `failed_terms`, `successful_terms`, `prf_evidence_summaries`, `top_positive_signals`, `top_negative_signals`, `select_terms`, `suppress_terms`, and `rank_terms`. Sort by `run_id`, `query_instance_id`, `judge_contract_hash`.

- [ ] **Step 5: Add CLI command**

If `src/seektalent/cli.py` uses argparse subcommands, add:

```text
seektalent flywheel-export --dataset-version dataset-v1 --run-id run_01TEST00000000000000000000
```

The command instantiates `FlywheelStore(settings.flywheel_path)` and `ArtifactStore(settings.artifacts_path)`, then calls `export_query_rewriting_dataset`.

- [ ] **Step 6: Run tests**

Run:

```bash
uv run pytest tests/test_flywheel_datasets.py tests/test_artifact_store.py::test_export_root_registers_flywheel_dataset_artifacts -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/seektalent/flywheel/datasets.py src/seektalent/flywheel/store.py src/seektalent/cli.py tests/test_flywheel_datasets.py
git commit -m "feat: export query rewriting datasets"
```

---

### Task 9: Delete Old Judge Cache Code And Repo-Root Cache Leakage

**Files:**
- Modify: `src/seektalent/evaluation.py`
- Modify: `src/seektalent/cli.py`
- Modify: `tests/test_evaluation.py`
- Modify: `tests/test_llm_lifecycle.py`
- Modify: `tests/test_llm_fail_fast.py`
- Modify: `docs/outputs.md`

- [ ] **Step 1: Add cleanup guard test**

Add to `tests/test_flywheel_store.py`:

```python
def test_active_code_no_longer_mentions_judge_cache() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    offenders = []
    for root in [repo_root / "src", repo_root / "tests"]:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if path.name == "test_flywheel_store.py":
                continue
            if "JudgeCache" in text or "judge_cache.sqlite3" in text:
                offenders.append(str(path.relative_to(repo_root)))
    assert offenders == []
```

Add:

```python
def test_tests_do_not_write_repo_root_cache_test_dirs() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    offenders = []
    for path in (repo_root / "tests").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "cache-test-" in text:
            offenders.append(str(path.relative_to(repo_root)))
    assert offenders == []
```

- [ ] **Step 2: Run guard and verify failure**

Run:

```bash
uv run pytest tests/test_flywheel_store.py::test_active_code_no_longer_mentions_judge_cache tests/test_flywheel_store.py::test_tests_do_not_write_repo_root_cache_test_dirs -q
```

Expected: FAIL with current old references.

- [ ] **Step 3: Delete old evaluation cache code**

Remove from `src/seektalent/evaluation.py`:

- `sqlite3` import if no longer used there;
- `_cache_path`;
- `JudgeCache`;
- old `migrate_judge_assets` helpers;
- old tests and helper imports tied only to `jd_assets`, `resume_assets`, and old `judge_labels`.

- [ ] **Step 4: Replace repo-root cache-test settings**

In `tests/test_llm_lifecycle.py` and `tests/test_llm_fail_fast.py`, replace:

```python
return make_settings(llm_cache_dir=f".seektalent/cache-test-{uuid4().hex}")
```

with:

```python
return make_settings(llm_cache_dir=str(tmp_path / "cache"))
```

Change `_settings` signatures to accept `tmp_path`:

```python
def _settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> AppSettings:
    monkeypatch.setenv("SEEKTALENT_TEXT_LLM_API_KEY", "test-key")
    return make_settings(llm_cache_dir=str(tmp_path / "cache"))
```

Update callers to pass `tmp_path`.

- [ ] **Step 5: Update docs and CLI wording**

Replace `.seektalent/judge_cache.sqlite3` references with `.seektalent/flywheel.sqlite3` only where active behavior is documented. Delete migration help text for old judge cache.

- [ ] **Step 6: Run cleanup guards**

Run:

```bash
uv run pytest tests/test_flywheel_store.py::test_active_code_no_longer_mentions_judge_cache tests/test_flywheel_store.py::test_tests_do_not_write_repo_root_cache_test_dirs -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/seektalent/evaluation.py src/seektalent/cli.py tests/test_evaluation.py tests/test_llm_lifecycle.py tests/test_llm_fail_fast.py tests/test_flywheel_store.py docs/outputs.md
git commit -m "refactor: delete old judge cache"
```

---

### Task 10: End-To-End Runtime, Eval, And Manifest Verification

**Files:**
- Modify: `tests/test_runtime_audit.py`
- Modify: `tests/test_runtime_state_flow.py`
- Modify: `tests/test_evaluation.py`
- Modify: `docs/outputs.md`

- [ ] **Step 1: Add runtime e2e assertion**

In `tests/test_runtime_audit.py`, add:

```python
def test_run_populates_flywheel_store_and_artifacts(tmp_path: Path) -> None:
    settings = make_settings(
        runs_dir=str(tmp_path / "runs"),
        artifacts_dir=str(tmp_path / "artifacts"),
        flywheel_db_path=str(tmp_path / "flywheel.sqlite3"),
        mock_cts=True,
        min_rounds=1,
        max_rounds=1,
    )
    runtime = WorkflowRuntime(settings)
    _install_runtime_stubs(runtime, controller=SearchTwiceController(), resume_scorer=StubScorer())
    tracer = RunTracer(settings.artifacts_path)
    try:
        job_title, jd, notes = _sample_inputs()
        run_state = asyncio.run(runtime._build_run_state(job_title=job_title, jd=jd, notes=notes, tracer=tracer))
        asyncio.run(runtime._run_rounds(run_state=run_state, tracer=tracer, progress_callback=None))
    finally:
        tracer.close()

    conn = sqlite3.connect(tmp_path / "flywheel.sqlite3")
    try:
        assert conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM run_queries").fetchone()[0] >= 1
        assert conn.execute("SELECT COUNT(*) FROM query_resume_hits").fetchone()[0] >= 1
        assert conn.execute("SELECT COUNT(*) FROM query_outcomes").fetchone()[0] >= 1
    finally:
        conn.close()

    manifest = json.loads((tracer.run_dir / "manifests/run_manifest.json").read_text(encoding="utf-8"))
    assert "flywheel.query_outcomes" in manifest["logical_artifacts"]
    assert "flywheel.term_events" in manifest["logical_artifacts"]
```

- [ ] **Step 2: Run and verify failure or pass**

Run:

```bash
uv run pytest tests/test_runtime_audit.py::test_run_populates_flywheel_store_and_artifacts -q
```

Expected: PASS if prior runtime tasks are complete. If it fails, fix only the missing runtime wire from previous tasks.

- [ ] **Step 3: Add eval e2e assertion**

In `tests/test_evaluation.py`, add an assertion to the eval test from Task 6:

```python
session.write_jsonl("evaluation.replay_rows", [{"resume_id": "resume-1", "score": 3}])
manifest = json.loads((session.root / "manifests/run_manifest.json").read_text(encoding="utf-8"))
assert "evaluation.evaluation" in manifest["logical_artifacts"]
assert "evaluation.replay_rows" in manifest["logical_artifacts"]
assert "flywheel.query_judge_outcomes" in manifest["logical_artifacts"]
```

Add a benchmark metadata test to `tests/test_runtime_state_flow.py` using two small cases:

```python
def test_benchmark_case_runs_populate_flywheel_case_ids(tmp_path: Path) -> None:
    store = FlywheelStore(tmp_path / "flywheel.sqlite3")
    task_id = store.upsert_task(job_title="Agent Engineer", jd_text="JD", notes_text="")
    for case_id in ["case-1", "case-2"]:
        store.start_run(
            run_id=f"run-{case_id}",
            task_id=task_id,
            version="0.6.2",
            git_sha="abc123",
            artifact_ref_id=None,
            artifact_root=str(tmp_path / f"artifacts/runs/run-{case_id}"),
            config_hash="config",
            config_payload={},
            status="completed",
            eval_enabled=True,
            benchmark_id="benchmark-0.6.2",
            benchmark_case_id=case_id,
        )
    rows = store.rows_for_runs("runs", run_ids=["run-case-1", "run-case-2"])
    assert {row["benchmark_case_id"] for row in rows} == {"case-1", "case-2"}
    store.close()
```

- [ ] **Step 4: Update outputs docs**

In `docs/outputs.md`, add:

```markdown
## Flywheel Store

Active flywheel runs write queryable data to `.seektalent/flywheel.sqlite3`.
The database indexes tasks, resume snapshots, runs, queries, query hits, judge labels,
runtime query outcomes, judge query outcomes, term events, term outcomes, and dataset exports.
Full run trajectory remains under `artifacts/`.

Flywheel JSONL artifacts include:

- `flywheel/query_outcomes.jsonl`
- `flywheel/query_judge_outcomes.jsonl`
- `flywheel/term_events.jsonl`
- `flywheel/term_outcomes.jsonl`
- `flywheel/query_rewrite_samples.jsonl`
```

- [ ] **Step 5: Run integration slices**

Run:

```bash
uv run pytest tests/test_flywheel_store.py tests/test_flywheel_runtime.py tests/test_flywheel_datasets.py tests/test_artifact_store.py tests/test_evaluation.py tests/test_runtime_audit.py::test_run_populates_flywheel_store_and_artifacts -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/test_runtime_audit.py tests/test_runtime_state_flow.py tests/test_evaluation.py docs/outputs.md
git commit -m "test: verify flywheel runtime outputs"
```

---

### Task 11: Full Cleanup Guard And Full Test Suite

**Files:**
- Modify only files needed to satisfy failing tests.

- [ ] **Step 1: Run search guards**

Run:

```bash
rg -n "JudgeCache|judge_cache|judge_cache.sqlite3" src tests docs
```

Expected: no output except historical design/plan documents under `docs/superpowers/`.

Run:

```bash
rg -n "cache-test-" tests src
```

Expected: no output.

Run:

```bash
rg -n "flywheel/(query_outcomes|query_judge_outcomes|term_events|term_outcomes|query_rewrite_samples)" src tests
```

Expected: references only in `src/seektalent/artifacts/registry.py`, `src/seektalent/flywheel/`, and tests that assert registry behavior. Runtime code uses logical names, not hand-built filesystem paths.

Run:

```bash
rg -n "run_dir / \"flywheel\"|session.root / \"flywheel\"|Path\\([^)]*flywheel" src/seektalent tests
```

Expected: references only in tests that inspect generated files, not in runtime or evaluation write paths.

- [ ] **Step 2: Run focused test suite**

Run:

```bash
uv run pytest tests/test_flywheel_store.py tests/test_flywheel_runtime.py tests/test_flywheel_datasets.py tests/test_artifact_store.py tests/test_evaluation.py tests/test_runtime_audit.py tests/test_runtime_state_flow.py tests/test_llm_lifecycle.py tests/test_llm_fail_fast.py -q
```

Expected: PASS.

- [ ] **Step 3: Run full test suite**

Run:

```bash
uv run pytest -q
```

Expected: PASS.

- [ ] **Step 4: Inspect local generated files**

Run:

```bash
find .seektalent -maxdepth 2 -type d -name 'cache-test-*' -print
```

Expected: no output.

Run:

```bash
find .seektalent -maxdepth 2 -type f -name 'judge_cache.sqlite3' -print
```

Expected: no output from active tests. If an old local file exists from prior manual runs, remove it manually only after confirming it is not created by this test run.

- [ ] **Step 5: Commit final fixes**

If Step 1-4 required changes:

```bash
git add src tests docs .env.example src/seektalent/default.env
git commit -m "test: complete flywheel store rollout"
```

If no files changed:

```bash
git status --short
```

Expected: clean working tree.

---

## Plan Self-Review Checklist

- Spec coverage: This plan covers FlywheelStore, removal of active JudgeCache, canonical query specs, snapshot join discipline, runtime and judge outcomes, term events, term outcomes, artifact refs, export artifact kind, deterministic dataset exports, cleanup guards, and full test verification.
- Placeholder scan: This plan avoids unresolved marker text and vague edge-case instructions.
- Type consistency: The plan uses `FlywheelStore`, `build_judge_contract_hash`, `canonical_json`, `task_sha256`, `query_outcomes`, `query_judge_outcomes`, `term_events`, and `term_outcomes` consistently across tasks.
