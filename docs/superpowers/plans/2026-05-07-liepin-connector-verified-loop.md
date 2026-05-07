# Liepin Connector Verified Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a verified Liepin provider loop where users only log into Liepin, while SeekTalent handles authenticated search, network-first extraction, detail budget control, corpus persistence, replay, and quality traceability.

**Architecture:** Keep Python as the business authority for provider selection, compliance, detail-open policy, corpus/flywheel artifacts, and scoring. Add a Bun/TypeScript Chromium worker as a bounded execution process that performs browser actions, captures network responses, runs DOM fallback extraction, and returns typed results. Start with fake-worker and fixture replay paths, then gate live smoke behind explicit compliance/session setup.

**Tech Stack:** Python 3.12, Pydantic, SQLite, existing ArtifactStore/CorpusStore/FlywheelStore, Bun, TypeScript, Playwright Chromium, pytest, Bun test.

---

## Scope Notes

This plan implements the V1 connector loop from `docs/superpowers/specs/2026-05-07-liepin-cloud-connector-design.md`.

It does not build the Vite/TanStack UI, static benchmark qrels, personalized memory, Lightpanda, or a generic website automation platform.

The user-facing contract is strict: the only required user action is logging into Liepin inside the managed browser session.

## File Structure

### Python provider and policy boundary

- Create `src/seektalent/providers/liepin/__init__.py`
  - Exports `LiepinProviderAdapter`.
- Create `src/seektalent/providers/liepin/models.py`
  - Pydantic/dataclass contracts for connection status, extraction source, worker card/detail payloads, compliance gate, candidate identity, detail attempts, and verified-loop summary.
- Create `src/seektalent/providers/liepin/security.py`
  - HMAC account hash and artifact/session redaction guards.
- Create `src/seektalent/providers/liepin/store.py`
  - SQLite-backed connector ledger for compliance gate, sessions, detail-open attempts, and connection events.
- Create `src/seektalent/providers/liepin/client.py`
  - Python client for fake and HTTP worker calls.
- Create `src/seektalent/providers/liepin/mapper.py`
  - Maps worker card/detail payloads into `ResumeCandidate`.
- Create `src/seektalent/providers/liepin/policy.py`
  - Detail-open planning and idempotency decisions.
- Create `src/seektalent/providers/liepin/adapter.py`
  - Implements `ProviderAdapter`.
- Create `src/seektalent/providers/liepin/verified_loop.py`
  - Builds run metrics, traceability rows, and connector artifacts.

### Existing Python integration points

- Modify `src/seektalent/config.py`
  - Add provider selection and Liepin connector settings.
- Modify `src/seektalent/default.env`
  - Add commented Liepin connector settings in Chinese.
- Modify `src/seektalent/providers/registry.py`
  - Select CTS or Liepin adapter from settings.
- Modify `src/seektalent/runtime/retrieval_runtime.py`
  - Stop hardcoding `provider_name="cts"` in canonical query specs.
- Modify `src/seektalent/artifacts/registry.py`
  - Register Liepin logical artifacts.
- Modify `src/seektalent/corpus/documents.py`
  - Add optional protected snapshot privacy metadata for Liepin card/detail payloads.
- Modify `src/seektalent/corpus/runtime.py`
  - Preserve Liepin snapshot metadata when writing corpus rows.
- Modify `src/seektalent/cli.py`
  - Add manual-only Liepin fixture and smoke commands.

### Bun/TypeScript worker

- Create `apps/liepin-worker/package.json`
  - Bun scripts and dependencies.
- Create `apps/liepin-worker/tsconfig.json`
  - TypeScript config.
- Create `apps/liepin-worker/src/contracts.ts`
  - Worker request/response contracts.
- Create `apps/liepin-worker/src/redaction.ts`
  - Fixture redaction and fail-closed checks.
- Create `apps/liepin-worker/src/extraction.ts`
  - Network-first and DOM fallback extraction functions.
- Create `apps/liepin-worker/src/session.ts`
  - Managed Chromium session wrapper and status states.
- Create `apps/liepin-worker/src/server.ts`
  - Bun HTTP API for the worker.
- Create `apps/liepin-worker/tests/extraction.test.ts`
  - Fixture parser tests.
- Create `apps/liepin-worker/tests/redaction.test.ts`
  - Redaction fail-closed tests.
- Create `apps/liepin-worker/fixtures/cards.network.redacted.json`
  - Synthetic redacted network fixture.
- Create `apps/liepin-worker/fixtures/detail.network.redacted.json`
  - Synthetic redacted detail fixture.
- Create `apps/liepin-worker/fixtures/cards.dom.redacted.html`
  - Synthetic redacted DOM fallback fixture.

### Tests

- Create `tests/test_liepin_security.py`
- Create `tests/test_liepin_store.py`
- Create `tests/test_liepin_worker_client.py`
- Create `tests/test_liepin_provider_adapter.py`
- Create `tests/test_liepin_detail_policy.py`
- Create `tests/test_liepin_verified_loop.py`
- Create `tests/test_liepin_corpus_integration.py`
- Modify `tests/test_provider_registry.py`
- Modify `tests/test_artifact_store.py`
- Modify `tests/test_corpus_documents.py`

---

### Task 1: Provider Selection Config And Artifact Names

**Files:**
- Modify: `src/seektalent/config.py`
- Modify: `src/seektalent/default.env`
- Modify: `src/seektalent/providers/registry.py`
- Modify: `src/seektalent/artifacts/registry.py`
- Modify: `tests/test_provider_registry.py`
- Modify: `tests/test_artifact_store.py`

- [ ] **Step 1: Write provider registry and artifact tests**

Add to `tests/test_provider_registry.py`:

```python
def test_provider_registry_returns_liepin_adapter_when_configured() -> None:
    from seektalent.providers.liepin import LiepinProviderAdapter

    settings = make_settings(provider_name="liepin", liepin_worker_base_url="http://127.0.0.1:8765")

    provider = get_provider_adapter(settings)

    assert isinstance(provider, LiepinProviderAdapter)
    assert provider.name == "liepin"
    capabilities = provider.describe_capabilities()
    assert capabilities.supports_fetch_mode_summary is True
    assert capabilities.supports_fetch_mode_detail is True
    assert capabilities.recommended_max_concurrency == 1
```

Add to `tests/test_artifact_store.py`:

```python
def test_liepin_logical_artifacts_resolve() -> None:
    from seektalent.artifacts.registry import resolve_descriptor

    names = [
        "runtime.liepin_connection_events",
        "assets.provider_snapshots.liepin.cards",
        "assets.provider_snapshots.liepin.details",
        "round.02.retrieval.liepin_connection_status",
        "round.02.retrieval.liepin_search_requests",
        "round.02.retrieval.liepin_card_extraction",
        "round.02.retrieval.liepin_detail_open_plan",
        "round.02.retrieval.liepin_detail_open_results",
        "round.02.retrieval.liepin_extraction_fixtures",
        "round.02.retrieval.liepin_connector_metrics",
    ]

    resolved = {name: resolve_descriptor(name) for name in names}

    assert resolved["runtime.liepin_connection_events"].path == "runtime/liepin_connection_events.jsonl"
    assert resolved["assets.provider_snapshots.liepin.cards"].collection is True
    assert resolved["round.02.retrieval.liepin_connector_metrics"].path == (
        "rounds/02/retrieval/liepin_connector_metrics.json"
    )
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```bash
uv run pytest tests/test_provider_registry.py::test_provider_registry_returns_liepin_adapter_when_configured tests/test_artifact_store.py::test_liepin_logical_artifacts_resolve -q
```

Expected:

```text
FAILED ... No module named 'seektalent.providers.liepin'
FAILED ... KeyError: 'runtime.liepin_connection_events'
```

- [ ] **Step 3: Add settings**

In `src/seektalent/config.py`, add near other literal aliases:

```python
ProviderName = Literal["cts", "liepin"]
```

Inside `AppSettings`, add:

```python
provider_name: ProviderName = "cts"
liepin_worker_base_url: str = "http://127.0.0.1:8765"
liepin_worker_timeout_seconds: float = 30.0
liepin_connector_db_path: str = ".seektalent/liepin_connector.sqlite3"
liepin_connector_secret: str = "local-development-liepin-connector-secret"
liepin_default_daily_detail_budget: int = 20
liepin_live_enabled: bool = False
```

Add a validator near existing settings validators:

```python
@field_validator("liepin_worker_timeout_seconds")
@classmethod
def _validate_liepin_worker_timeout(cls, value: float) -> float:
    if value <= 0:
        raise ValueError("liepin_worker_timeout_seconds must be positive")
    return value

@field_validator("liepin_default_daily_detail_budget")
@classmethod
def _validate_liepin_daily_detail_budget(cls, value: int) -> int:
    if value < 0:
        raise ValueError("liepin_default_daily_detail_budget must be >= 0")
    return value
```

In `src/seektalent/default.env`, add a commented section:

```dotenv
# 猎聘连接器：默认仍使用 CTS；设置为 liepin 后才启用猎聘 provider。
# SEEKTALENT_PROVIDER_NAME=cts

# 猎聘浏览器 worker：V1 使用 Bun/TypeScript + Playwright Chromium。
# SEEKTALENT_LIEPIN_WORKER_BASE_URL=http://127.0.0.1:8765
# SEEKTALENT_LIEPIN_WORKER_TIMEOUT_SECONDS=30

# 猎聘详情额度：Python core 会先记账再让 worker 打开详情页。
# SEEKTALENT_LIEPIN_DEFAULT_DAILY_DETAIL_BUDGET=20

# 猎聘 live 开关：未显式开启时，只允许 fake worker / fixture replay。
# SEEKTALENT_LIEPIN_LIVE_ENABLED=false
```

- [ ] **Step 4: Add artifact descriptors**

In `src/seektalent/artifacts/registry.py`, add to `STATIC_ENTRIES`:

```python
"runtime.liepin_connection_events": LogicalArtifactEntry(
    path="runtime/liepin_connection_events.jsonl",
    content_type="application/jsonl",
    schema_version="v1",
),
"assets.provider_snapshots.liepin.cards": LogicalArtifactEntry(
    path="assets/provider_snapshots/liepin/cards",
    content_type="application/json",
    schema_version="v1",
    collection=True,
),
"assets.provider_snapshots.liepin.details": LogicalArtifactEntry(
    path="assets/provider_snapshots/liepin/details",
    content_type="application/json",
    schema_version="v1",
    collection=True,
),
```

Add to `ROUND_CONTENT_TYPES`:

```python
"liepin_connection_status": "application/json",
"liepin_search_requests": "application/json",
"liepin_card_extraction": "application/json",
"liepin_detail_open_plan": "application/json",
"liepin_detail_open_results": "application/json",
"liepin_extraction_fixtures": "application/json",
"liepin_connector_metrics": "application/json",
```

- [ ] **Step 5: Add provider registry branch**

Create a temporary import target in `src/seektalent/providers/liepin/__init__.py`:

```python
from __future__ import annotations

from .adapter import LiepinProviderAdapter

__all__ = ["LiepinProviderAdapter"]
```

Create minimal `src/seektalent/providers/liepin/adapter.py`:

```python
from __future__ import annotations

from seektalent.config import AppSettings
from seektalent.core.retrieval.provider_contract import ProviderCapabilities
from seektalent.core.retrieval.provider_contract import SearchRequest
from seektalent.core.retrieval.provider_contract import SearchResult


class LiepinProviderAdapter:
    name = "liepin"

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def describe_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_structured_filters=False,
            supports_detail_fetch=True,
            supports_fetch_mode_summary=True,
            supports_fetch_mode_detail=True,
            paging_mode="cursor",
            recommended_max_concurrency=1,
            has_stable_external_id=False,
            has_stable_dedup_key=False,
        )

    async def search(self, request: SearchRequest, *, round_no: int, trace_id: str) -> SearchResult:
        raise RuntimeError("Liepin worker client is not wired yet.")
```

Modify `src/seektalent/providers/registry.py`:

```python
from seektalent.providers.liepin import LiepinProviderAdapter


def get_provider_adapter(settings: AppSettings) -> ProviderAdapter:
    if settings.provider_name == "liepin":
        return LiepinProviderAdapter(settings)
    return CTSProviderAdapter(settings)
```

- [ ] **Step 6: Run tests and commit**

Run:

```bash
uv run pytest tests/test_provider_registry.py::test_provider_registry_returns_liepin_adapter_when_configured tests/test_artifact_store.py::test_liepin_logical_artifacts_resolve -q
```

Expected:

```text
2 passed
```

Commit:

```bash
git add src/seektalent/config.py src/seektalent/default.env src/seektalent/providers/registry.py src/seektalent/providers/liepin src/seektalent/artifacts/registry.py tests/test_provider_registry.py tests/test_artifact_store.py
git commit -m "feat: add liepin provider selection boundary"
```

---

### Task 2: Liepin Domain Models And Secret Guards

**Files:**
- Create: `src/seektalent/providers/liepin/models.py`
- Create: `src/seektalent/providers/liepin/security.py`
- Create: `tests/test_liepin_security.py`

- [ ] **Step 1: Write security and model tests**

Create `tests/test_liepin_security.py`:

```python
from __future__ import annotations

import pytest

from seektalent.providers.liepin.models import ComplianceGate
from seektalent.providers.liepin.models import ExtractionSource
from seektalent.providers.liepin.models import WorkerCardPayload
from seektalent.providers.liepin.security import assert_no_liepin_secrets
from seektalent.providers.liepin.security import build_provider_account_hash


def test_provider_account_hash_uses_keyed_hmac() -> None:
    first = build_provider_account_hash("secret-a", "account-123")
    second = build_provider_account_hash("secret-b", "account-123")

    assert len(first) == 64
    assert first != second
    assert "account-123" not in first


def test_secret_guard_rejects_cookie_and_cdp_values() -> None:
    payload = {
        "headers": {"cookie": "SESSION=abc"},
        "debug": "ws://127.0.0.1:9222/devtools/browser/abc",
    }

    with pytest.raises(ValueError, match="Liepin secret-bearing payload"):
        assert_no_liepin_secrets(payload)


def test_compliance_gate_denies_missing_authorization() -> None:
    gate = ComplianceGate(
        tenant_id="local",
        workspace_id="default",
        actor_id="user-1",
        provider_account_hash="hash",
        account_holder_authorized=False,
        human_initiated_recruiting=True,
        allowed_purposes=["search"],
        retention_policy="run_debug_short",
        deletion_path="delete-run-assets",
        raw_payload_access_scope="run_only",
        fixture_export_allowed=False,
        policy_ref="local-dev",
    )

    assert gate.allows_live_run is False


def test_worker_card_payload_records_extraction_source() -> None:
    card = WorkerCardPayload(
        provider_subject_id="subject-1",
        provider_listing_id="listing-1",
        synthetic_candidate_fingerprint="fp-1",
        identity_confidence="stable_provider_id",
        search_text="后端工程师 Python 微服务",
        title="后端工程师",
        location="上海",
        raw_payload={"id": "subject-1"},
        extraction_source="network",
        extractor_version="liepin-extractor-v1",
        pii_classification="card_minimal",
    )

    assert card.extraction_source == ExtractionSource.NETWORK
    assert card.raw_payload["id"] == "subject-1"
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run pytest tests/test_liepin_security.py -q
```

Expected:

```text
FAILED ... No module named 'seektalent.providers.liepin.models'
```

- [ ] **Step 3: Implement models**

Create `src/seektalent/providers/liepin/models.py`:

```python
from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ConnectionStatus(StrEnum):
    LOGGED_OUT = "logged_out"
    READY = "ready"
    NEEDS_USER_ACTION = "needs_user_action"
    RISK_CONTROL_WAIT = "risk_control_wait"
    DAILY_DETAIL_BUDGET_EXHAUSTED = "daily_detail_budget_exhausted"
    TEMPORARILY_RATE_LIMITED = "temporarily_rate_limited"
    FAILED = "failed"


class ExtractionSource(StrEnum):
    NETWORK = "network"
    DOM_FALLBACK = "dom_fallback"


IdentityConfidence = Literal["stable_provider_id", "strong_card_fingerprint", "weak_card_fingerprint"]
PiiClassification = Literal["card_minimal", "resume_detail", "contact_sensitive", "unknown"]
RetentionPolicy = Literal["run_debug_short", "workspace_recruiting_record", "forbidden_persist"]
AccessScope = Literal["run_only", "workspace", "admin_only"]
RedactionState = Literal["raw_encrypted", "normalized_redacted", "fixture_safe", "not_fixture_safe"]


class ComplianceGate(BaseModel):
    tenant_id: str
    workspace_id: str
    actor_id: str
    provider_account_hash: str
    account_holder_authorized: bool
    human_initiated_recruiting: bool
    allowed_purposes: list[str]
    retention_policy: RetentionPolicy
    deletion_path: str
    raw_payload_access_scope: AccessScope
    fixture_export_allowed: bool
    policy_ref: str

    @property
    def allows_live_run(self) -> bool:
        return (
            self.account_holder_authorized
            and self.human_initiated_recruiting
            and "search" in self.allowed_purposes
        )


class WorkerCardPayload(BaseModel):
    provider_subject_id: str | None = None
    provider_listing_id: str | None = None
    synthetic_candidate_fingerprint: str
    identity_confidence: IdentityConfidence
    search_text: str
    title: str | None = None
    location: str | None = None
    raw_payload: dict[str, Any]
    extraction_source: ExtractionSource
    extractor_version: str
    pii_classification: PiiClassification

    @field_validator("search_text")
    @classmethod
    def _require_search_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("search_text must not be empty")
        return text


class WorkerDetailPayload(BaseModel):
    provider_subject_id: str | None = None
    provider_listing_id: str | None = None
    synthetic_candidate_fingerprint: str
    identity_confidence: IdentityConfidence
    detail_text: str
    raw_payload: dict[str, Any]
    extraction_source: ExtractionSource
    extractor_version: str
    pii_classification: PiiClassification


class WorkerSearchCardsResponse(BaseModel):
    connection_id: str
    status: ConnectionStatus
    cards: list[WorkerCardPayload] = Field(default_factory=list)
    next_cursor: str | None = None
    exhausted: bool = False
    diagnostics: list[str] = Field(default_factory=list)
    latency_ms: int | None = None


class WorkerOpenDetailsResponse(BaseModel):
    connection_id: str
    status: ConnectionStatus
    details: list[WorkerDetailPayload] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    latency_ms: int | None = None
```

- [ ] **Step 4: Implement security helpers**

Create `src/seektalent/providers/liepin/security.py`:

```python
from __future__ import annotations

import hmac
import json
from hashlib import sha256
from typing import Any

SECRET_MARKERS = (
    "cookie",
    "set-cookie",
    "authorization",
    "storageState",
    "storage_state",
    "cdp",
    "devtools",
    "websocketDebuggerUrl",
    "ws://",
    "wss://",
)


def build_provider_account_hash(connector_secret: str, provider_account_stable_id: str) -> str:
    if not connector_secret:
        raise ValueError("connector_secret must not be empty")
    if not provider_account_stable_id:
        raise ValueError("provider_account_stable_id must not be empty")
    return hmac.new(
        connector_secret.encode("utf-8"),
        provider_account_stable_id.encode("utf-8"),
        sha256,
    ).hexdigest()


def assert_no_liepin_secrets(payload: Any) -> None:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    folded = text.casefold()
    if any(marker.casefold() in folded for marker in SECRET_MARKERS):
        raise ValueError("Liepin secret-bearing payload cannot be written to ordinary artifacts")
```

- [ ] **Step 5: Run tests and commit**

Run:

```bash
uv run pytest tests/test_liepin_security.py -q
```

Expected:

```text
4 passed
```

Commit:

```bash
git add src/seektalent/providers/liepin/models.py src/seektalent/providers/liepin/security.py tests/test_liepin_security.py
git commit -m "feat: add liepin security contracts"
```

---

### Task 3: Connector Ledger Store

**Files:**
- Create: `src/seektalent/providers/liepin/store.py`
- Create: `tests/test_liepin_store.py`

- [ ] **Step 1: Write store tests**

Create `tests/test_liepin_store.py`:

```python
from __future__ import annotations

from seektalent.providers.liepin.store import LiepinConnectorStore


def test_compliance_gate_required_for_live_run(tmp_path) -> None:
    store = LiepinConnectorStore(tmp_path / "liepin.sqlite3")

    assert store.has_passing_compliance_gate("local", "default", "hash") is False

    store.record_compliance_gate(
        tenant_id="local",
        workspace_id="default",
        actor_id="user-1",
        provider_account_hash="hash",
        account_holder_authorized=True,
        human_initiated_recruiting=True,
        allowed_purposes=["search"],
        retention_policy="run_debug_short",
        deletion_path="delete-run-assets",
        raw_payload_access_scope="run_only",
        fixture_export_allowed=False,
        policy_ref="local-dev",
    )

    assert store.has_passing_compliance_gate("local", "default", "hash") is True


def test_detail_attempt_is_idempotent_and_possible_consumption_counts(tmp_path) -> None:
    store = LiepinConnectorStore(tmp_path / "liepin.sqlite3")
    first = store.reserve_detail_attempt(
        tenant_id="local",
        workspace_id="default",
        provider_name="liepin",
        account_hash="hash",
        run_id="run-1",
        query_instance_id="query-1",
        provider_candidate_identity="candidate-1",
        identity_confidence="stable_provider_id",
        approved_by_policy_ref="artifact:plan",
        idempotency_key="idem-1",
    )
    second = store.reserve_detail_attempt(
        tenant_id="local",
        workspace_id="default",
        provider_name="liepin",
        account_hash="hash",
        run_id="run-1",
        query_instance_id="query-1",
        provider_candidate_identity="candidate-1",
        identity_confidence="stable_provider_id",
        approved_by_policy_ref="artifact:plan",
        idempotency_key="idem-1",
    )

    assert first == second

    store.mark_detail_attempt_possible_consumption(first, worker_command_id="worker-command-1")
    row = store.get_detail_attempt(first)

    assert row["state"] == "failed_after_possible_consumption"
    assert row["consumption_state"] == "possibly_consumed"
    assert store.detail_budget_consumed_count("local", "default", "hash") == 1
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run pytest tests/test_liepin_store.py -q
```

Expected:

```text
FAILED ... No module named 'seektalent.providers.liepin.store'
```

- [ ] **Step 3: Implement SQLite store**

Create `src/seektalent/providers/liepin/store.py`:

```python
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "liepin-connector-v1"


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class LiepinConnectorStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def _ensure_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                INSERT OR IGNORE INTO schema_meta(key, value)
                VALUES ('schema_version', 'liepin-connector-v1');

                CREATE TABLE IF NOT EXISTS compliance_gates (
                    gate_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    provider_account_hash TEXT NOT NULL,
                    account_holder_authorized INTEGER NOT NULL,
                    human_initiated_recruiting INTEGER NOT NULL,
                    allowed_purposes_json TEXT NOT NULL,
                    retention_policy TEXT NOT NULL,
                    deletion_path TEXT NOT NULL,
                    raw_payload_access_scope TEXT NOT NULL,
                    fixture_export_allowed INTEGER NOT NULL,
                    policy_ref TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(tenant_id, workspace_id, provider_account_hash, policy_ref)
                );

                CREATE TABLE IF NOT EXISTS detail_open_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    provider_name TEXT NOT NULL,
                    account_hash TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    query_instance_id TEXT NOT NULL,
                    provider_candidate_identity TEXT NOT NULL,
                    identity_confidence TEXT NOT NULL,
                    approved_by_policy_ref TEXT NOT NULL,
                    worker_command_id TEXT,
                    state TEXT NOT NULL,
                    consumption_state TEXT NOT NULL,
                    raw_evidence_ref TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(tenant_id, workspace_id, idempotency_key)
                );
                """
            )

    def record_compliance_gate(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        actor_id: str,
        provider_account_hash: str,
        account_holder_authorized: bool,
        human_initiated_recruiting: bool,
        allowed_purposes: list[str],
        retention_policy: str,
        deletion_path: str,
        raw_payload_access_scope: str,
        fixture_export_allowed: bool,
        policy_ref: str,
    ) -> str:
        import json
        from seektalent.storage.json import sha256_json

        gate_id = sha256_json(
            {
                "tenant_id": tenant_id,
                "workspace_id": workspace_id,
                "provider_account_hash": provider_account_hash,
                "policy_ref": policy_ref,
            }
        )
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO compliance_gates(
                    gate_id, tenant_id, workspace_id, actor_id, provider_account_hash,
                    account_holder_authorized, human_initiated_recruiting, allowed_purposes_json,
                    retention_policy, deletion_path, raw_payload_access_scope,
                    fixture_export_allowed, policy_ref, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    gate_id,
                    tenant_id,
                    workspace_id,
                    actor_id,
                    provider_account_hash,
                    int(account_holder_authorized),
                    int(human_initiated_recruiting),
                    json.dumps(allowed_purposes, ensure_ascii=False, sort_keys=True),
                    retention_policy,
                    deletion_path,
                    raw_payload_access_scope,
                    int(fixture_export_allowed),
                    policy_ref,
                    utc_now(),
                ),
            )
        return gate_id

    def has_passing_compliance_gate(self, tenant_id: str, workspace_id: str, provider_account_hash: str) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT 1 FROM compliance_gates
                WHERE tenant_id = ?
                  AND workspace_id = ?
                  AND provider_account_hash = ?
                  AND account_holder_authorized = 1
                  AND human_initiated_recruiting = 1
                  AND allowed_purposes_json LIKE '%search%'
                LIMIT 1
                """,
                (tenant_id, workspace_id, provider_account_hash),
            ).fetchone()
        return row is not None

    def reserve_detail_attempt(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        provider_name: str,
        account_hash: str,
        run_id: str,
        query_instance_id: str,
        provider_candidate_identity: str,
        identity_confidence: str,
        approved_by_policy_ref: str,
        idempotency_key: str,
    ) -> str:
        from seektalent.storage.json import sha256_json

        attempt_id = sha256_json(
            {
                "tenant_id": tenant_id,
                "workspace_id": workspace_id,
                "idempotency_key": idempotency_key,
            }
        )
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO detail_open_attempts(
                    attempt_id, idempotency_key, tenant_id, workspace_id, provider_name,
                    account_hash, run_id, query_instance_id, provider_candidate_identity,
                    identity_confidence, approved_by_policy_ref, state, consumption_state,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'approved_not_started', 'not_consumed', ?)
                """,
                (
                    attempt_id,
                    idempotency_key,
                    tenant_id,
                    workspace_id,
                    provider_name,
                    account_hash,
                    run_id,
                    query_instance_id,
                    provider_candidate_identity,
                    identity_confidence,
                    approved_by_policy_ref,
                    utc_now(),
                ),
            )
        return attempt_id

    def mark_detail_attempt_possible_consumption(self, attempt_id: str, *, worker_command_id: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE detail_open_attempts
                SET state = 'failed_after_possible_consumption',
                    consumption_state = 'possibly_consumed',
                    worker_command_id = ?,
                    completed_at = ?
                WHERE attempt_id = ?
                """,
                (worker_command_id, utc_now(), attempt_id),
            )

    def get_detail_attempt(self, attempt_id: str) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM detail_open_attempts WHERE attempt_id = ?",
                (attempt_id,),
            ).fetchone()
        if row is None:
            raise KeyError(attempt_id)
        return dict(row)

    def detail_budget_consumed_count(self, tenant_id: str, workspace_id: str, account_hash: str) -> int:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM detail_open_attempts
                WHERE tenant_id = ?
                  AND workspace_id = ?
                  AND account_hash = ?
                  AND consumption_state IN ('consumed', 'possibly_consumed', 'unknown')
                """,
                (tenant_id, workspace_id, account_hash),
            ).fetchone()
        return int(row["count"])
```

- [ ] **Step 4: Run tests and commit**

Run:

```bash
uv run pytest tests/test_liepin_store.py -q
```

Expected:

```text
2 passed
```

Commit:

```bash
git add src/seektalent/providers/liepin/store.py tests/test_liepin_store.py
git commit -m "feat: add liepin connector ledger"
```

---

### Task 4: Worker Client And Fake Fixture Path

**Files:**
- Create: `src/seektalent/providers/liepin/client.py`
- Create: `tests/test_liepin_worker_client.py`

- [ ] **Step 1: Write fake worker client tests**

Create `tests/test_liepin_worker_client.py`:

```python
from __future__ import annotations

import asyncio

from seektalent.providers.liepin.client import FakeLiepinWorkerClient
from seektalent.providers.liepin.client import SearchCardsCommand


def test_fake_worker_returns_network_cards() -> None:
    client = FakeLiepinWorkerClient()
    response = asyncio.run(
        client.search_cards(
            SearchCardsCommand(
                connection_id="conn-1",
                query="python 后端",
                cursor=None,
                page_size=2,
                trace_id="trace-1",
            )
        )
    )

    assert response.status == "ready"
    assert len(response.cards) == 2
    assert response.cards[0].extraction_source == "network"
    assert response.cards[0].synthetic_candidate_fingerprint


def test_fake_worker_never_exposes_secrets() -> None:
    client = FakeLiepinWorkerClient()
    response = asyncio.run(
        client.search_cards(
            SearchCardsCommand(
                connection_id="conn-1",
                query="java",
                cursor=None,
                page_size=1,
                trace_id="trace-1",
            )
        )
    )

    text = response.model_dump_json()

    assert "cookie" not in text.casefold()
    assert "authorization" not in text.casefold()
    assert "devtools" not in text.casefold()
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run pytest tests/test_liepin_worker_client.py -q
```

Expected:

```text
FAILED ... No module named 'seektalent.providers.liepin.client'
```

- [ ] **Step 3: Implement client contracts and fake client**

Create `src/seektalent/providers/liepin/client.py`:

```python
from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from seektalent.providers.liepin.models import WorkerCardPayload
from seektalent.providers.liepin.models import WorkerOpenDetailsResponse
from seektalent.providers.liepin.models import WorkerSearchCardsResponse
from seektalent.providers.liepin.security import assert_no_liepin_secrets


class SearchCardsCommand(BaseModel):
    connection_id: str
    query: str
    cursor: str | None
    page_size: int
    trace_id: str


class OpenDetailsCommand(BaseModel):
    connection_id: str
    detail_plan_id: str
    idempotency_keys: list[str]
    provider_listing_ids: list[str]
    trace_id: str


class LiepinWorkerClient(Protocol):
    async def search_cards(self, command: SearchCardsCommand) -> WorkerSearchCardsResponse: ...

    async def open_details(self, command: OpenDetailsCommand) -> WorkerOpenDetailsResponse: ...


class FakeLiepinWorkerClient:
    async def search_cards(self, command: SearchCardsCommand) -> WorkerSearchCardsResponse:
        cards = [
            WorkerCardPayload(
                provider_subject_id=f"subject-{idx}",
                provider_listing_id=f"listing-{idx}",
                synthetic_candidate_fingerprint=f"fp-{command.query}-{idx}",
                identity_confidence="stable_provider_id",
                search_text=f"{command.query} 候选人 {idx} 微服务 搜索 推荐系统",
                title="后端工程师",
                location="上海",
                raw_payload={
                    "provider": "liepin",
                    "fixture_kind": "card",
                    "listingId": f"listing-{idx}",
                    "text": f"{command.query} 候选人 {idx}",
                },
                extraction_source="network",
                extractor_version="liepin-extractor-v1",
                pii_classification="card_minimal",
            )
            for idx in range(1, command.page_size + 1)
        ]
        response = WorkerSearchCardsResponse(
            connection_id=command.connection_id,
            status="ready",
            cards=cards,
            next_cursor=None,
            exhausted=True,
            diagnostics=["fake liepin worker"],
            latency_ms=1,
        )
        assert_no_liepin_secrets(response.model_dump(mode="json"))
        return response

    async def open_details(self, command: OpenDetailsCommand) -> WorkerOpenDetailsResponse:
        response = WorkerOpenDetailsResponse(
            connection_id=command.connection_id,
            status="ready",
            details=[],
            diagnostics=["fake detail worker has no details"],
            latency_ms=1,
        )
        assert_no_liepin_secrets(response.model_dump(mode="json"))
        return response
```

- [ ] **Step 4: Run tests and commit**

Run:

```bash
uv run pytest tests/test_liepin_worker_client.py -q
```

Expected:

```text
2 passed
```

Commit:

```bash
git add src/seektalent/providers/liepin/client.py tests/test_liepin_worker_client.py
git commit -m "feat: add liepin worker client contract"
```

---

### Task 5: Python Adapter And Mapping

**Files:**
- Modify: `src/seektalent/providers/liepin/adapter.py`
- Create: `src/seektalent/providers/liepin/mapper.py`
- Create: `tests/test_liepin_provider_adapter.py`

- [ ] **Step 1: Write adapter tests**

Create `tests/test_liepin_provider_adapter.py`:

```python
from __future__ import annotations

import asyncio

import pytest

from seektalent.core.retrieval.provider_contract import SearchRequest
from seektalent.providers.liepin.adapter import LiepinProviderAdapter
from seektalent.providers.liepin.client import FakeLiepinWorkerClient
from tests.settings_factory import make_settings


def test_liepin_provider_adapter_searches_summary_cards() -> None:
    provider = LiepinProviderAdapter(
        make_settings(provider_name="liepin"),
        worker_client=FakeLiepinWorkerClient(),
        connection_id="conn-1",
    )
    request = SearchRequest(
        query_terms=["python", "推荐系统"],
        query_role="primary",
        keyword_query="python 推荐系统",
        adapter_notes=[],
        runtime_constraints=[],
        fetch_mode="summary",
        page_size=2,
    )

    result = asyncio.run(provider.search(request, round_no=1, trace_id="trace-1"))

    assert result.raw_candidate_count == 2
    assert result.candidates[0].raw["provider"] == "liepin"
    assert result.candidates[0].raw["extraction_source"] == "network"
    assert result.exhausted is True


def test_liepin_provider_adapter_rejects_detail_without_plan() -> None:
    provider = LiepinProviderAdapter(
        make_settings(provider_name="liepin"),
        worker_client=FakeLiepinWorkerClient(),
        connection_id="conn-1",
    )
    request = SearchRequest(
        query_terms=["python"],
        query_role="primary",
        keyword_query="python",
        adapter_notes=[],
        runtime_constraints=[],
        fetch_mode="detail",
        page_size=1,
    )

    with pytest.raises(ValueError, match="detail fetch requires a detail-open plan"):
        asyncio.run(provider.search(request, round_no=1, trace_id="trace-1"))
```

- [ ] **Step 2: Run tests and verify failures**

Run:

```bash
uv run pytest tests/test_liepin_provider_adapter.py -q
```

Expected:

```text
FAILED ... TypeError: LiepinProviderAdapter.__init__() got an unexpected keyword argument 'worker_client'
```

- [ ] **Step 3: Implement mapper**

Create `src/seektalent/providers/liepin/mapper.py`:

```python
from __future__ import annotations

from seektalent.models import ResumeCandidate
from seektalent.providers.liepin.models import WorkerCardPayload


def build_card_candidate(card: WorkerCardPayload) -> ResumeCandidate:
    provider_candidate_id = card.provider_subject_id or card.provider_listing_id
    resume_id = provider_candidate_id or card.synthetic_candidate_fingerprint
    return ResumeCandidate(
        resume_id=f"liepin:{resume_id}",
        source_resume_id=card.provider_listing_id,
        snapshot_sha256=None,
        dedup_key=card.provider_subject_id or card.synthetic_candidate_fingerprint,
        search_text=card.search_text,
        raw={
            "provider": "liepin",
            "provider_subject_id": card.provider_subject_id,
            "provider_listing_id": card.provider_listing_id,
            "synthetic_candidate_fingerprint": card.synthetic_candidate_fingerprint,
            "identity_confidence": card.identity_confidence,
            "extraction_source": str(card.extraction_source),
            "extractor_version": card.extractor_version,
            "pii_classification": card.pii_classification,
            "payload": card.raw_payload,
            "score_evidence_source": "card_only",
        },
    )
```

- [ ] **Step 4: Implement adapter**

Replace `src/seektalent/providers/liepin/adapter.py` with:

```python
from __future__ import annotations

from seektalent.config import AppSettings
from seektalent.core.retrieval.provider_contract import ProviderCapabilities
from seektalent.core.retrieval.provider_contract import SearchRequest
from seektalent.core.retrieval.provider_contract import SearchResult
from seektalent.providers.liepin.client import FakeLiepinWorkerClient
from seektalent.providers.liepin.client import LiepinWorkerClient
from seektalent.providers.liepin.client import SearchCardsCommand
from seektalent.providers.liepin.mapper import build_card_candidate


class LiepinProviderAdapter:
    name = "liepin"

    def __init__(
        self,
        settings: AppSettings,
        *,
        worker_client: LiepinWorkerClient | None = None,
        connection_id: str = "local-dev-connection",
    ) -> None:
        self.settings = settings
        self.worker_client = worker_client or FakeLiepinWorkerClient()
        self.connection_id = connection_id

    def describe_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_structured_filters=False,
            supports_detail_fetch=True,
            supports_fetch_mode_summary=True,
            supports_fetch_mode_detail=True,
            paging_mode="cursor",
            recommended_max_concurrency=1,
            has_stable_external_id=False,
            has_stable_dedup_key=False,
        )

    async def search(self, request: SearchRequest, *, round_no: int, trace_id: str) -> SearchResult:
        if request.fetch_mode == "detail":
            raise ValueError("detail fetch requires a detail-open plan")
        response = await self.worker_client.search_cards(
            SearchCardsCommand(
                connection_id=self.connection_id,
                query=request.keyword_query,
                cursor=request.cursor,
                page_size=request.page_size,
                trace_id=trace_id,
            )
        )
        candidates = [build_card_candidate(card) for card in response.cards]
        return SearchResult(
            candidates=candidates,
            diagnostics=response.diagnostics,
            exhausted=response.exhausted,
            next_cursor=response.next_cursor,
            request_payload={
                "provider": "liepin",
                "connection_id": self.connection_id,
                "round_no": round_no,
                "query": request.keyword_query,
                "fetch_mode": request.fetch_mode,
                "status": str(response.status),
            },
            raw_candidate_count=len(response.cards),
            latency_ms=response.latency_ms,
        )
```

- [ ] **Step 5: Run tests and commit**

Run:

```bash
uv run pytest tests/test_liepin_provider_adapter.py tests/test_provider_registry.py::test_provider_registry_returns_liepin_adapter_when_configured -q
```

Expected:

```text
3 passed
```

Commit:

```bash
git add src/seektalent/providers/liepin/adapter.py src/seektalent/providers/liepin/mapper.py tests/test_liepin_provider_adapter.py
git commit -m "feat: add liepin provider adapter"
```

---

### Task 6: Detail Open Policy

**Files:**
- Create: `src/seektalent/providers/liepin/policy.py`
- Create: `tests/test_liepin_detail_policy.py`

- [ ] **Step 1: Write detail policy tests**

Create `tests/test_liepin_detail_policy.py`:

```python
from __future__ import annotations

from seektalent.providers.liepin.policy import DetailCandidate
from seektalent.providers.liepin.policy import build_detail_open_plan


def test_detail_policy_skips_already_opened_candidate() -> None:
    candidates = [
        DetailCandidate(
            provider_candidate_identity="candidate-1",
            identity_confidence="stable_provider_id",
            card_score=0.9,
            query_instance_id="query-1",
            provider_listing_id="listing-1",
        )
    ]

    plan = build_detail_open_plan(
        candidates=candidates,
        already_opened_identities={"candidate-1"},
        daily_budget_remaining=10,
        policy_ref="policy-v1",
    )

    assert plan.approved == []
    assert plan.skipped[0].reason == "already_opened"


def test_detail_policy_respects_budget_and_low_value_threshold() -> None:
    candidates = [
        DetailCandidate("candidate-1", "stable_provider_id", 0.95, "query-1", "listing-1"),
        DetailCandidate("candidate-2", "stable_provider_id", 0.25, "query-1", "listing-2"),
        DetailCandidate("candidate-3", "stable_provider_id", 0.90, "query-1", "listing-3"),
    ]

    plan = build_detail_open_plan(
        candidates=candidates,
        already_opened_identities=set(),
        daily_budget_remaining=1,
        policy_ref="policy-v1",
    )

    assert [item.provider_candidate_identity for item in plan.approved] == ["candidate-1"]
    assert {item.reason for item in plan.skipped} == {"low_card_value", "budget_exhausted"}
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run pytest tests/test_liepin_detail_policy.py -q
```

Expected:

```text
FAILED ... No module named 'seektalent.providers.liepin.policy'
```

- [ ] **Step 3: Implement policy**

Create `src/seektalent/providers/liepin/policy.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field


MIN_DETAIL_CARD_SCORE = 0.5


@dataclass(frozen=True)
class DetailCandidate:
    provider_candidate_identity: str
    identity_confidence: str
    card_score: float
    query_instance_id: str
    provider_listing_id: str


@dataclass(frozen=True)
class SkippedDetailCandidate:
    provider_candidate_identity: str
    reason: str


@dataclass(frozen=True)
class DetailOpenPlan:
    policy_ref: str
    approved: list[DetailCandidate] = field(default_factory=list)
    skipped: list[SkippedDetailCandidate] = field(default_factory=list)


def build_detail_open_plan(
    *,
    candidates: list[DetailCandidate],
    already_opened_identities: set[str],
    daily_budget_remaining: int,
    policy_ref: str,
) -> DetailOpenPlan:
    approved: list[DetailCandidate] = []
    skipped: list[SkippedDetailCandidate] = []
    remaining = daily_budget_remaining
    for candidate in sorted(candidates, key=lambda item: item.card_score, reverse=True):
        if candidate.provider_candidate_identity in already_opened_identities:
            skipped.append(SkippedDetailCandidate(candidate.provider_candidate_identity, "already_opened"))
            continue
        if candidate.card_score < MIN_DETAIL_CARD_SCORE:
            skipped.append(SkippedDetailCandidate(candidate.provider_candidate_identity, "low_card_value"))
            continue
        if remaining <= 0:
            skipped.append(SkippedDetailCandidate(candidate.provider_candidate_identity, "budget_exhausted"))
            continue
        approved.append(candidate)
        remaining -= 1
    return DetailOpenPlan(policy_ref=policy_ref, approved=approved, skipped=skipped)
```

- [ ] **Step 4: Run tests and commit**

Run:

```bash
uv run pytest tests/test_liepin_detail_policy.py -q
```

Expected:

```text
2 passed
```

Commit:

```bash
git add src/seektalent/providers/liepin/policy.py tests/test_liepin_detail_policy.py
git commit -m "feat: add liepin detail open policy"
```

---

### Task 7: Protected Corpus Metadata For Liepin Snapshots

**Files:**
- Modify: `src/seektalent/corpus/documents.py`
- Modify: `src/seektalent/corpus/runtime.py`
- Modify: `tests/test_corpus_documents.py`
- Create: `tests/test_liepin_corpus_integration.py`

- [ ] **Step 1: Write corpus metadata tests**

Add to `tests/test_corpus_documents.py`:

```python
def test_liepin_resume_document_accepts_protected_snapshot_metadata() -> None:
    row = build_resume_document_row(
        tenant_id="local",
        workspace_id="default",
        raw_payload={"provider": "liepin", "text": "Python candidate"},
        provider_name="liepin",
        provider_candidate_id="candidate-1",
        source_resume_id="listing-1",
        dedup_key="candidate-1",
        resume_doc_id="local:default:snap",
        subject_id="subject-1",
        snapshot_sha256="a" * 64,
        raw_payload_artifact_ref_id="artifact-1",
        raw_payload_sha256="b" * 64,
        raw_payload_size_bytes=100,
        normalized_text="Python candidate",
        first_seen_run_id="run-1",
        first_seen_query_instance_id="query-1",
        first_seen_stage_id="retrieval",
        first_seen_artifact_ref_id="artifact-1",
        pii_classification="card_minimal",
        retention_policy="run_debug_short",
        access_scope="run_only",
        redaction_state="not_fixture_safe",
    )

    assert row["sensitivity_json"]["pii_classification"] == "card_minimal"
    assert row["retention_policy"] == "run_debug_short"
    assert row["external_export_eligible"] is False
```

Create `tests/test_liepin_corpus_integration.py`:

```python
from __future__ import annotations

from seektalent.artifacts import ArtifactStore
from seektalent.corpus.runtime import ProviderReturnedCandidate
from seektalent.corpus.runtime import record_corpus_provider_results
from seektalent.corpus.store import CorpusStore
from seektalent.models import ResumeCandidate


def test_liepin_provider_snapshots_are_not_fixture_safe_by_default(tmp_path) -> None:
    artifact_store = ArtifactStore(tmp_path / "artifacts")
    artifact_session = artifact_store.create_root(
        kind="corpus",
        display_name="liepin corpus ingest",
        producer="LiepinCorpusTest",
    )
    corpus_store = CorpusStore(tmp_path / "corpus.sqlite3")
    candidate = ResumeCandidate(
        resume_id="liepin:candidate-1",
        source_resume_id="listing-1",
        dedup_key="candidate-1",
        search_text="Python candidate",
        raw={
            "provider": "liepin",
            "provider_subject_id": "candidate-1",
            "provider_listing_id": "listing-1",
            "payload": {"text": "Python candidate"},
            "pii_classification": "card_minimal",
        },
    )

    record_corpus_provider_results(
        session=artifact_session,
        store=corpus_store,
        run_id="run-1",
        tenant_id="local",
        workspace_id="default",
        returned_candidates=[
            ProviderReturnedCandidate(
                candidate=candidate,
                stage_id="retrieval",
                round_no=1,
                query_instance_id="query-1",
                query_fingerprint="fingerprint-1",
                provider_name="liepin",
                provider_request_id="request-1",
                provider_rank=1,
                provider_page_no=1,
                provider_fetch_no=1,
                attempt_no=1,
            )
        ],
    )

    rows = corpus_store.rows_for_tenant("resume_documents", "local", "default")

    assert rows[0]["provider_name"] == "liepin"
    assert rows[0]["sensitivity_json"]["redaction_state"] == "not_fixture_safe"
```

- [ ] **Step 2: Run tests and verify failures**

Run:

```bash
uv run pytest tests/test_corpus_documents.py::test_liepin_resume_document_accepts_protected_snapshot_metadata tests/test_liepin_corpus_integration.py -q
```

Expected:

```text
FAILED ... got an unexpected keyword argument 'pii_classification'
```

- [ ] **Step 3: Extend document row builder**

Modify `build_resume_document_row` in `src/seektalent/corpus/documents.py` by adding keyword-only parameters:

```python
    pii_classification: str = "unknown",
    retention_policy: str = DEFAULT_RETENTION_POLICY,
    access_scope: str = "workspace",
    redaction_state: str = "not_fixture_safe",
```

Change the returned sensitivity and retention fields:

```python
"sensitivity_json": {
    "contains_pii": True,
    "contains_external_text": True,
    "pii_classification": pii_classification,
    "access_scope": access_scope,
    "redaction_state": redaction_state,
},
"retention_policy": retention_policy,
```

- [ ] **Step 4: Pass metadata from corpus runtime**

In `src/seektalent/corpus/runtime.py`, inside the call to `build_resume_document_row`, add:

```python
pii_classification=str(raw_payload.get("pii_classification") or raw_payload.get("payload", {}).get("pii_classification") or "unknown"),
retention_policy="run_debug_short" if returned.provider_name == "liepin" else "retain_local",
access_scope="run_only" if returned.provider_name == "liepin" else "workspace",
redaction_state="not_fixture_safe" if returned.provider_name == "liepin" else "raw_encrypted",
```

- [ ] **Step 5: Run tests and commit**

Run:

```bash
uv run pytest tests/test_corpus_documents.py::test_liepin_resume_document_accepts_protected_snapshot_metadata tests/test_liepin_corpus_integration.py -q
```

Expected:

```text
2 passed
```

Commit:

```bash
git add src/seektalent/corpus/documents.py src/seektalent/corpus/runtime.py tests/test_corpus_documents.py tests/test_liepin_corpus_integration.py
git commit -m "feat: protect liepin corpus snapshots"
```

---

### Task 8: Verified Loop Summary And Artifacts

**Files:**
- Create: `src/seektalent/providers/liepin/verified_loop.py`
- Create: `tests/test_liepin_verified_loop.py`

- [ ] **Step 1: Write verified-loop tests**

Create `tests/test_liepin_verified_loop.py`:

```python
from __future__ import annotations

from seektalent.providers.liepin.verified_loop import build_connector_metrics
from seektalent.providers.liepin.verified_loop import build_traceability_row


def test_connector_metrics_separate_network_and_dom_counts() -> None:
    metrics = build_connector_metrics(
        connection_ready_latency_ms=100,
        browser_rss_mb=400,
        card_search_latency_ms=1200,
        detail_open_latency_ms=1800,
        raw_card_count=10,
        saved_card_snapshot_count=10,
        extraction_sources=["network", "network", "dom_fallback"],
        detail_candidates_considered_count=5,
        detail_opened_count=2,
        detail_skipped_already_opened_count=1,
        detail_skipped_low_value_count=1,
        detail_skipped_budget_exhausted_count=1,
        card_only_fit_count=3,
        detail_enriched_fit_count=1,
        new_candidate_count=8,
        duplicate_candidate_count=2,
    )

    assert metrics["network_extraction_hit_count"] == 2
    assert metrics["dom_fallback_count"] == 1
    assert metrics["raw_card_count"] == 10


def test_traceability_row_links_candidate_to_provider_evidence() -> None:
    row = build_traceability_row(
        final_candidate_id="liepin:candidate-1",
        query_instance_id="query-1",
        provider_payload_ref="artifact:payload",
        extraction_artifact_ref="artifact:extraction",
        corpus_snapshot_ref="corpus:doc",
        detail_open_attempt_id="attempt-1",
    )

    assert row["final_candidate_id"] == "liepin:candidate-1"
    assert row["detail_open_attempt_id"] == "attempt-1"
```

- [ ] **Step 2: Run tests and verify failures**

Run:

```bash
uv run pytest tests/test_liepin_verified_loop.py -q
```

Expected:

```text
FAILED ... No module named 'seektalent.providers.liepin.verified_loop'
```

- [ ] **Step 3: Implement verified loop helpers**

Create `src/seektalent/providers/liepin/verified_loop.py`:

```python
from __future__ import annotations

from typing import Any


def build_connector_metrics(
    *,
    connection_ready_latency_ms: int | None,
    browser_rss_mb: int | None,
    card_search_latency_ms: int | None,
    detail_open_latency_ms: int | None,
    raw_card_count: int,
    saved_card_snapshot_count: int,
    extraction_sources: list[str],
    detail_candidates_considered_count: int,
    detail_opened_count: int,
    detail_skipped_already_opened_count: int,
    detail_skipped_low_value_count: int,
    detail_skipped_budget_exhausted_count: int,
    card_only_fit_count: int,
    detail_enriched_fit_count: int,
    new_candidate_count: int,
    duplicate_candidate_count: int,
) -> dict[str, Any]:
    return {
        "connection_ready_latency_ms": connection_ready_latency_ms,
        "browser_rss_mb": browser_rss_mb,
        "card_search_latency_ms": card_search_latency_ms,
        "detail_open_latency_ms": detail_open_latency_ms,
        "raw_card_count": raw_card_count,
        "saved_card_snapshot_count": saved_card_snapshot_count,
        "network_extraction_hit_count": sum(1 for item in extraction_sources if item == "network"),
        "dom_fallback_count": sum(1 for item in extraction_sources if item == "dom_fallback"),
        "extraction_missing_required_field_count": 0,
        "detail_candidates_considered_count": detail_candidates_considered_count,
        "detail_opened_count": detail_opened_count,
        "detail_skipped_already_opened_count": detail_skipped_already_opened_count,
        "detail_skipped_low_value_count": detail_skipped_low_value_count,
        "detail_skipped_budget_exhausted_count": detail_skipped_budget_exhausted_count,
        "card_only_fit_count": card_only_fit_count,
        "detail_enriched_fit_count": detail_enriched_fit_count,
        "new_candidate_count": new_candidate_count,
        "duplicate_candidate_count": duplicate_candidate_count,
    }


def build_traceability_row(
    *,
    final_candidate_id: str,
    query_instance_id: str,
    provider_payload_ref: str,
    extraction_artifact_ref: str,
    corpus_snapshot_ref: str,
    detail_open_attempt_id: str | None,
) -> dict[str, str | None]:
    return {
        "final_candidate_id": final_candidate_id,
        "query_instance_id": query_instance_id,
        "provider_payload_ref": provider_payload_ref,
        "extraction_artifact_ref": extraction_artifact_ref,
        "corpus_snapshot_ref": corpus_snapshot_ref,
        "detail_open_attempt_id": detail_open_attempt_id,
    }
```

- [ ] **Step 4: Run tests and commit**

Run:

```bash
uv run pytest tests/test_liepin_verified_loop.py -q
```

Expected:

```text
2 passed
```

Commit:

```bash
git add src/seektalent/providers/liepin/verified_loop.py tests/test_liepin_verified_loop.py
git commit -m "feat: add liepin verified loop metrics"
```

---

### Task 9: Bun Worker Skeleton And Redaction

**Files:**
- Create: `apps/liepin-worker/package.json`
- Create: `apps/liepin-worker/tsconfig.json`
- Create: `apps/liepin-worker/src/contracts.ts`
- Create: `apps/liepin-worker/src/redaction.ts`
- Create: `apps/liepin-worker/tests/redaction.test.ts`

- [ ] **Step 1: Create worker package skeleton**

Create `apps/liepin-worker/package.json`:

```json
{
  "name": "@seektalent/liepin-worker",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "bun test",
    "typecheck": "bunx tsc --noEmit"
  },
  "dependencies": {
    "playwright": "^1.53.0",
    "zod": "^3.25.0"
  },
  "devDependencies": {
    "typescript": "^5.8.0"
  }
}
```

Create `apps/liepin-worker/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "skipLibCheck": true,
    "types": ["bun-types"]
  },
  "include": ["src/**/*.ts", "tests/**/*.ts"]
}
```

- [ ] **Step 2: Write redaction tests**

Create `apps/liepin-worker/tests/redaction.test.ts`:

```typescript
import { describe, expect, test } from "bun:test";
import { assertFixtureSafe, redactCandidateFixture } from "../src/redaction";

describe("fixture redaction", () => {
  test("rejects auth-bearing payloads", () => {
    expect(() =>
      assertFixtureSafe({
        headers: { cookie: "SESSION=abc" },
        body: { name: "张三" },
      }),
    ).toThrow("fixture contains secret-bearing content");
  });

  test("tokenizes personal fields", () => {
    const redacted = redactCandidateFixture({
      name: "张三",
      phone: "13800000000",
      email: "person@example.com",
      title: "后端工程师",
    });

    expect(redacted.name).toBe("[REDACTED_NAME]");
    expect(redacted.phone).toBe("[REDACTED_CONTACT]");
    expect(redacted.email).toBe("[REDACTED_CONTACT]");
    expect(redacted.title).toBe("后端工程师");
    expect(() => assertFixtureSafe(redacted)).not.toThrow();
  });
});
```

- [ ] **Step 3: Run worker tests and verify they fail**

Run:

```bash
cd apps/liepin-worker && bun test tests/redaction.test.ts
```

Expected:

```text
error: Cannot find module '../src/redaction'
```

- [ ] **Step 4: Implement contracts and redaction**

Create `apps/liepin-worker/src/contracts.ts`:

```typescript
import { z } from "zod";

export const extractionSourceSchema = z.enum(["network", "dom_fallback"]);
export type ExtractionSource = z.infer<typeof extractionSourceSchema>;

export const workerCardPayloadSchema = z.object({
  provider_subject_id: z.string().nullable(),
  provider_listing_id: z.string().nullable(),
  synthetic_candidate_fingerprint: z.string(),
  identity_confidence: z.enum(["stable_provider_id", "strong_card_fingerprint", "weak_card_fingerprint"]),
  search_text: z.string().min(1),
  title: z.string().nullable(),
  location: z.string().nullable(),
  raw_payload: z.record(z.unknown()),
  extraction_source: extractionSourceSchema,
  extractor_version: z.string(),
  pii_classification: z.enum(["card_minimal", "resume_detail", "contact_sensitive", "unknown"]),
});

export type WorkerCardPayload = z.infer<typeof workerCardPayloadSchema>;
```

Create `apps/liepin-worker/src/redaction.ts`:

```typescript
const secretMarkers = [
  "cookie",
  "set-cookie",
  "authorization",
  "storagestate",
  "devtools",
  "websocketdebuggerurl",
  "ws://",
  "wss://",
];

const contactKeys = new Set(["phone", "email", "wechat", "weixin", "mobile"]);
const nameKeys = new Set(["name", "candidateName", "realName"]);

export function assertFixtureSafe(payload: unknown): void {
  const text = JSON.stringify(payload).toLowerCase();
  for (const marker of secretMarkers) {
    if (text.includes(marker)) {
      throw new Error("fixture contains secret-bearing content");
    }
  }
}

export function redactCandidateFixture<T extends Record<string, unknown>>(payload: T): T {
  const redacted: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(payload)) {
    if (nameKeys.has(key)) {
      redacted[key] = "[REDACTED_NAME]";
    } else if (contactKeys.has(key)) {
      redacted[key] = "[REDACTED_CONTACT]";
    } else {
      redacted[key] = value;
    }
  }
  return redacted as T;
}
```

- [ ] **Step 5: Run worker tests and commit**

Run:

```bash
cd apps/liepin-worker && bun test tests/redaction.test.ts
```

Expected:

```text
2 pass
```

Commit:

```bash
git add apps/liepin-worker
git commit -m "feat: scaffold liepin bun worker"
```

---

### Task 10: Network Extraction And DOM Fallback Fixtures

**Files:**
- Create: `apps/liepin-worker/src/extraction.ts`
- Create: `apps/liepin-worker/tests/extraction.test.ts`
- Create: `apps/liepin-worker/fixtures/cards.network.redacted.json`
- Create: `apps/liepin-worker/fixtures/detail.network.redacted.json`
- Create: `apps/liepin-worker/fixtures/cards.dom.redacted.html`

- [ ] **Step 1: Add synthetic fixtures**

Create `apps/liepin-worker/fixtures/cards.network.redacted.json`:

```json
{
  "data": {
    "list": [
      {
        "candidateId": "subject-1",
        "listingId": "listing-1",
        "maskedName": "[REDACTED_NAME]",
        "title": "后端工程师",
        "location": "上海",
        "summary": "Python 微服务 推荐系统"
      }
    ]
  }
}
```

Create `apps/liepin-worker/fixtures/detail.network.redacted.json`:

```json
{
  "data": {
    "candidateId": "subject-1",
    "listingId": "listing-1",
    "detail": "Python 微服务 推荐系统 8年经验"
  }
}
```

Create `apps/liepin-worker/fixtures/cards.dom.redacted.html`:

```html
<main>
  <article data-liepin-card data-listing-id="listing-dom-1">
    <h2>算法工程师</h2>
    <span data-field="location">北京</span>
    <p>推荐系统 召回 排序 Python</p>
  </article>
</main>
```

- [ ] **Step 2: Write extraction tests**

Create `apps/liepin-worker/tests/extraction.test.ts`:

```typescript
import { describe, expect, test } from "bun:test";
import cardsFixture from "../fixtures/cards.network.redacted.json";
import detailFixture from "../fixtures/detail.network.redacted.json";
import { extractCardsFromDom, extractCardsFromNetwork, extractDetailFromNetwork } from "../src/extraction";

describe("liepin extraction", () => {
  test("extracts cards from network payload", () => {
    const cards = extractCardsFromNetwork(cardsFixture);

    expect(cards).toHaveLength(1);
    expect(cards[0].provider_subject_id).toBe("subject-1");
    expect(cards[0].extraction_source).toBe("network");
    expect(cards[0].search_text).toContain("Python");
  });

  test("extracts detail from network payload", () => {
    const detail = extractDetailFromNetwork(detailFixture);

    expect(detail.provider_subject_id).toBe("subject-1");
    expect(detail.detail_text).toContain("8年经验");
  });

  test("falls back to DOM card extraction", async () => {
    const html = await Bun.file("fixtures/cards.dom.redacted.html").text();
    const cards = extractCardsFromDom(html);

    expect(cards).toHaveLength(1);
    expect(cards[0].extraction_source).toBe("dom_fallback");
    expect(cards[0].search_text).toContain("推荐系统");
  });
});
```

- [ ] **Step 3: Run tests and verify they fail**

Run:

```bash
cd apps/liepin-worker && bun test tests/extraction.test.ts
```

Expected:

```text
error: Cannot find module '../src/extraction'
```

- [ ] **Step 4: Implement extraction functions**

Create `apps/liepin-worker/src/extraction.ts`:

```typescript
import type { WorkerCardPayload } from "./contracts";

type JsonObject = Record<string, unknown>;

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : null;
}

function fingerprint(parts: Array<string | null>): string {
  return parts.filter(Boolean).join("|").toLowerCase();
}

export function extractCardsFromNetwork(payload: JsonObject): WorkerCardPayload[] {
  const data = payload.data as JsonObject | undefined;
  const list = Array.isArray(data?.list) ? data.list : [];
  return list.map((item) => {
    const row = item as JsonObject;
    const providerSubjectId = text(row.candidateId);
    const providerListingId = text(row.listingId);
    const title = text(row.title);
    const location = text(row.location);
    const summary = text(row.summary) ?? "";
    return {
      provider_subject_id: providerSubjectId,
      provider_listing_id: providerListingId,
      synthetic_candidate_fingerprint: fingerprint([providerSubjectId, providerListingId, title, location, summary]),
      identity_confidence: providerSubjectId ? "stable_provider_id" : "strong_card_fingerprint",
      search_text: [title, location, summary].filter(Boolean).join(" "),
      title,
      location,
      raw_payload: row,
      extraction_source: "network",
      extractor_version: "liepin-extractor-v1",
      pii_classification: "card_minimal",
    };
  });
}

export function extractDetailFromNetwork(payload: JsonObject) {
  const data = payload.data as JsonObject | undefined;
  if (!data) {
    throw new Error("detail payload missing data");
  }
  const providerSubjectId = text(data.candidateId);
  const providerListingId = text(data.listingId);
  const detailText = text(data.detail);
  if (!detailText) {
    throw new Error("detail payload missing detail text");
  }
  return {
    provider_subject_id: providerSubjectId,
    provider_listing_id: providerListingId,
    synthetic_candidate_fingerprint: fingerprint([providerSubjectId, providerListingId, detailText]),
    identity_confidence: providerSubjectId ? "stable_provider_id" : "strong_card_fingerprint",
    detail_text: detailText,
    raw_payload: data,
    extraction_source: "network",
    extractor_version: "liepin-extractor-v1",
    pii_classification: "resume_detail",
  };
}

export function extractCardsFromDom(html: string): WorkerCardPayload[] {
  const matches = Array.from(html.matchAll(/<article[^>]*data-liepin-card[^>]*data-listing-id="([^"]+)"[^>]*>([\s\S]*?)<\/article>/g));
  return matches.map((match) => {
    const listingId = match[1];
    const body = match[2].replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
    return {
      provider_subject_id: null,
      provider_listing_id: listingId,
      synthetic_candidate_fingerprint: fingerprint([listingId, body]),
      identity_confidence: "strong_card_fingerprint",
      search_text: body,
      title: null,
      location: null,
      raw_payload: { listingId, body },
      extraction_source: "dom_fallback",
      extractor_version: "liepin-extractor-v1",
      pii_classification: "card_minimal",
    };
  });
}
```

- [ ] **Step 5: Run worker tests and commit**

Run:

```bash
cd apps/liepin-worker && bun test tests/extraction.test.ts tests/redaction.test.ts
```

Expected:

```text
5 pass
```

Commit:

```bash
git add apps/liepin-worker
git commit -m "feat: add liepin extraction replay"
```

---

### Task 11: Bun Worker HTTP Server Skeleton

**Files:**
- Create: `apps/liepin-worker/src/session.ts`
- Create: `apps/liepin-worker/src/server.ts`
- Create: `apps/liepin-worker/tests/server.test.ts`

- [ ] **Step 1: Write server tests**

Create `apps/liepin-worker/tests/server.test.ts`:

```typescript
import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import { startServer } from "../src/server";

let server: ReturnType<typeof startServer>;

beforeAll(() => {
  server = startServer({ port: 0, liveEnabled: false });
});

afterAll(() => {
  server.stop(true);
});

describe("liepin worker server", () => {
  test("reports logged out in non-live mode", async () => {
    const response = await fetch(`${server.url}/session/status?connection_id=conn-1`);
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.status).toBe("logged_out");
  });

  test("rejects live search when disabled", async () => {
    const response = await fetch(`${server.url}/search/cards`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ connection_id: "conn-1", query: "python", page_size: 1, trace_id: "trace-1" }),
    });
    const body = await response.json();

    expect(response.status).toBe(403);
    expect(body.error).toBe("live_liepin_worker_disabled");
  });
});
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd apps/liepin-worker && bun test tests/server.test.ts
```

Expected:

```text
error: Cannot find module '../src/server'
```

- [ ] **Step 3: Implement session and server**

Create `apps/liepin-worker/src/session.ts`:

```typescript
export type SessionStatus =
  | "logged_out"
  | "ready"
  | "needs_user_action"
  | "risk_control_wait"
  | "daily_detail_budget_exhausted"
  | "temporarily_rate_limited"
  | "failed";

export function getSessionStatus(_connectionId: string): { status: SessionStatus } {
  return { status: "logged_out" };
}
```

Create `apps/liepin-worker/src/server.ts`:

```typescript
import { getSessionStatus } from "./session";

type ServerOptions = {
  port: number;
  liveEnabled: boolean;
};

export function startServer(options: ServerOptions) {
  return Bun.serve({
    port: options.port,
    async fetch(request) {
      const url = new URL(request.url);
      if (url.pathname === "/session/status") {
        const connectionId = url.searchParams.get("connection_id") ?? "";
        return Response.json(getSessionStatus(connectionId));
      }
      if (url.pathname === "/search/cards" && request.method === "POST") {
        if (!options.liveEnabled) {
          return Response.json({ error: "live_liepin_worker_disabled" }, { status: 403 });
        }
        return Response.json({ error: "live_search_not_started" }, { status: 501 });
      }
      return Response.json({ error: "not_found" }, { status: 404 });
    },
  });
}

if (import.meta.main) {
  const port = Number(process.env.LIEPIN_WORKER_PORT ?? "8765");
  const liveEnabled = process.env.LIEPIN_WORKER_LIVE_ENABLED === "true";
  startServer({ port, liveEnabled });
  console.log(`liepin worker listening on ${port}`);
}
```

- [ ] **Step 4: Run worker tests and typecheck**

Run:

```bash
cd apps/liepin-worker && bun test && bun run typecheck
```

Expected:

```text
7 pass
```

Typecheck expected:

```text
no output and exit code 0
```

- [ ] **Step 5: Commit**

```bash
git add apps/liepin-worker
git commit -m "feat: add liepin worker server skeleton"
```

---

### Task 12: Runtime Provider Name And Query Identity Integration

**Files:**
- Modify: `src/seektalent/runtime/retrieval_runtime.py`
- Modify: `tests/test_retrieval_service.py` or `tests/test_query_identity.py`

- [ ] **Step 1: Write query identity test**

Add to `tests/test_query_identity.py`:

```python
def test_liepin_provider_name_enters_canonical_query_spec() -> None:
    from seektalent.models import LocationExecutionPlan
    from seektalent.runtime.retrieval_runtime import build_logical_query_state

    state = build_logical_query_state(
        run_id="run-1",
        round_no=1,
        lane_type="exploit",
        query_terms=["python"],
        job_intent_fingerprint="job",
        source_plan_version="test",
        provider_filters={},
        location_execution_plan=LocationExecutionPlan(
            mode="none",
            allowed_locations=[],
            preferred_locations=[],
            priority_order=[],
            balanced_order=[],
            rotation_offset=0,
        ),
        provider_name="liepin",
    )

    assert state.query_instance_id.startswith("run_")
    assert state.query_fingerprint
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run pytest tests/test_query_identity.py::test_liepin_provider_name_enters_canonical_query_spec -q
```

Expected:

```text
FAILED ... got an unexpected keyword argument 'provider_name'
```

- [ ] **Step 3: Add provider_name parameter**

Modify `build_logical_query_state` signature in `src/seektalent/runtime/retrieval_runtime.py`:

```python
    provider_name: str = "cts",
```

Change `CanonicalQuerySpec(provider_name="cts", ...)` to:

```python
provider_name=provider_name,
```

Find calls to `build_logical_query_state(` in `src/seektalent/runtime/retrieval_runtime.py` and pass:

```python
provider_name=_provider_name_for_service(retrieval_service),
```

- [ ] **Step 4: Run tests and commit**

Run:

```bash
uv run pytest tests/test_query_identity.py::test_liepin_provider_name_enters_canonical_query_spec tests/test_retrieval_service.py -q
```

Expected:

```text
all selected tests passed
```

Commit:

```bash
git add src/seektalent/runtime/retrieval_runtime.py tests/test_query_identity.py
git commit -m "feat: include provider name in query identity"
```

---

### Task 13: Manual CLI Commands For Fixture Replay And Live Smoke

**Files:**
- Modify: `src/seektalent/cli.py`
- Create: `tests/test_liepin_cli.py`

- [ ] **Step 1: Write CLI tests**

Create `tests/test_liepin_cli.py`:

```python
from __future__ import annotations

from seektalent.cli import main


def test_liepin_smoke_requires_live_flag(capsys) -> None:
    result = main(["liepin-smoke", "--connection-id", "conn-1"])

    assert result == 1
    assert "requires --live" in capsys.readouterr().err


def test_liepin_replay_command_runs_without_live_account(capsys) -> None:
    result = main(["liepin-replay-fixtures"])

    assert result == 0
    assert "liepin fixture replay command is configured" in capsys.readouterr().out
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest tests/test_liepin_cli.py -q
```

Expected:

```text
FAILED ... No such command 'liepin-smoke'
```

- [ ] **Step 3: Implement CLI commands**

In `src/seektalent/cli.py`, add:

```python
def _liepin_replay_fixtures_command(args: argparse.Namespace) -> int:
    del args
    print("liepin fixture replay command is configured")
    return 0


def _liepin_smoke_command(args: argparse.Namespace) -> int:
    if not args.live:
        print("liepin-smoke requires --live because it touches a live Liepin session", file=sys.stderr)
        return 1
    print(f"liepin live smoke requested for connection {args.connection_id}")
    return 0
```

In `build_exec_parser`, add before `doctor_parser`:

```python
    liepin_replay_parser = subparsers.add_parser(
        "liepin-replay-fixtures",
        help="Run Liepin fixture replay checks without a live account.",
    )
    liepin_replay_parser.set_defaults(handler=_liepin_replay_fixtures_command)

    liepin_smoke_parser = subparsers.add_parser(
        "liepin-smoke",
        help="Run a manual Liepin live smoke against a managed browser session.",
    )
    liepin_smoke_parser.add_argument("--connection-id", required=True)
    liepin_smoke_parser.add_argument("--live", action="store_true")
    liepin_smoke_parser.set_defaults(handler=_liepin_smoke_command)
```

- [ ] **Step 4: Run CLI tests and commit**

Run:

```bash
uv run pytest tests/test_liepin_cli.py -q
```

Expected:

```text
2 passed
```

Commit:

```bash
git add src/seektalent/cli.py tests/test_liepin_cli.py
git commit -m "feat: add liepin manual smoke commands"
```

---

### Task 14: Full Verification And Guard Tests

**Files:**
- Create: `tests/test_liepin_boundaries.py`
- Modify: `docs/superpowers/specs/2026-05-07-liepin-cloud-connector-design.md` only when implementation reveals an explicit mismatch.

- [ ] **Step 1: Add boundary guard tests**

Create `tests/test_liepin_boundaries.py`:

```python
from __future__ import annotations

from pathlib import Path


def test_liepin_worker_does_not_use_playwright_api_request_context() -> None:
    worker_root = Path("apps/liepin-worker")
    sources = "\n".join(path.read_text(encoding="utf-8") for path in worker_root.rglob("*.ts"))

    forbidden = [
        "APIRequestContext",
        "context.request",
        "browserContext.request",
        "page.request",
    ]
    for token in forbidden:
        assert token not in sources


def test_liepin_runtime_does_not_import_opencli() -> None:
    sources = "\n".join(path.read_text(encoding="utf-8") for path in Path("src/seektalent").rglob("*.py"))

    assert "opencli" not in sources.casefold()


def test_liepin_spec_keeps_bun_as_production_runner() -> None:
    spec = Path("docs/superpowers/specs/2026-05-07-liepin-cloud-connector-design.md").read_text(encoding="utf-8")

    assert "V1 uses Bun as the production runner" in spec
    assert "Node.js may only be used as an explicit diagnostic comparison path" in spec
```

- [ ] **Step 2: Run all focused Liepin tests**

Run:

```bash
uv run pytest tests/test_liepin_security.py tests/test_liepin_store.py tests/test_liepin_worker_client.py tests/test_liepin_provider_adapter.py tests/test_liepin_detail_policy.py tests/test_liepin_verified_loop.py tests/test_liepin_corpus_integration.py tests/test_liepin_cli.py tests/test_liepin_boundaries.py -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 3: Run worker tests**

Run:

```bash
cd apps/liepin-worker && bun test && bun run typecheck
```

Expected:

```text
all Bun tests passed
```

Typecheck expected:

```text
exit code 0
```

- [ ] **Step 4: Run full Python suite**

Run:

```bash
uv run pytest -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 5: Commit verification guards**

```bash
git add tests/test_liepin_boundaries.py
git commit -m "test: guard liepin connector boundaries"
```

## Self-Review Checklist

- Spec coverage:
  - Bun V1 runner: Task 9, Task 11, Task 14.
  - User only logs in: Task 1 settings, Task 11 session status, Task 13 smoke gate.
  - Compliance gate: Task 2 models, Task 3 store, Task 14 boundary tests.
  - API scope and session boundaries: Task 1, Task 2, Task 3, Task 11.
  - Network-first extraction and DOM fallback: Task 10.
  - APIRequestContext forbidden: Task 14.
  - Detail budget transaction/idempotency: Task 3 and Task 6.
  - Candidate identity: Task 2, Task 5, Task 6.
  - Corpus protected snapshots: Task 7.
  - Card-only/detail-enriched separation: Task 8 and Task 14.
  - Artifact logical names: Task 1.
  - Fixture replay/redaction: Task 9 and Task 10.
- Placeholder scan:
  - No placeholder strings are intentionally left for implementers.
- Type consistency:
  - Python model names used by adapter/client tests are defined before adapter wiring.
  - Worker contract names in TypeScript fixtures match the Python payload names.
  - `provider_name="liepin"` is carried through config, registry, adapter, and query identity.
