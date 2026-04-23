# Run Latency Engineering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce total `seektalent run` wall time through engineering execution changes only: higher scoring concurrency, exact-input caches, cheap semantic repair before expensive thinking retries, prompt-cache observability, and Requirements Thinking control.

**Architecture:** Keep retrieval, stopping, candidate selection, scoring rubric, and ranking behavior unchanged. Move expensive semantic retries for requirements/controller/reflection out of Pydantic AI automatic `ModelRetry` loops so parsed-but-invalid outputs can be repaired before a full thinking call is repeated. Use small module-level helpers for exact caches and repairs, and record every cache/repair/prompt-cache decision in existing artifacts.

**Tech Stack:** Python, Pydantic, Pydantic AI, pytest, sqlite3, JSON/JSONL runtime artifacts.

---

## Source Spec

Implement the accepted spec in `docs/superpowers/specs/2026-04-23-run-latency-engineering-design.md`.

Do not change these behavior strategies:

- Retrieval target and refill logic.
- Stop policy and final controller authority.
- Which newly recalled candidates are scored.
- Scoring rubric, score materialization, ranking, and finalizer behavior.
- Model fallback strategy.

## File Map

- Modify `src/seektalent/config.py`: add Requirements Thinking, repair model, exact cache directory, prompt-cache settings, and default scoring concurrency 10.
- Modify `src/seektalent/default.env`: document new environment variables.
- Modify `src/seektalent/llm.py`: accept optional prompt-cache key/retention in `build_model_settings`.
- Modify `src/seektalent/tracing.py`: extend `LLMCallSnapshot` with cache, repair, prompt-cache, and full-retry metadata.
- Create `src/seektalent/runtime/exact_llm_cache.py`: sqlite exact JSON cache helpers.
- Create `src/seektalent/repair.py`: small repair helpers for requirements/controller/reflection semantic failures.
- Modify `src/seektalent/requirements/extractor.py`: pass Requirements Thinking, exact-cache requirements outputs, repair semantic normalization failures.
- Modify `src/seektalent/controller/react_controller.py`: replace Pydantic AI semantic `output_validator` with explicit post-parse validation and repair.
- Modify `src/seektalent/reflection/critic.py`: move reflection stop-field draft validation out of Pydantic model parsing and add deterministic/model repair.
- Modify `src/seektalent/models.py`: allow `ReflectionAdviceDraft` to parse stop-field inconsistencies so repair can run; keep final `ReflectionAdvice` strict.
- Modify `src/seektalent/scoring/scorer.py`: exact-cache scoring calls before provider calls, write normal snapshots on hits.
- Modify `src/seektalent/runtime/orchestrator.py`: pass cache/repair/prompt-cache metadata into call snapshots and run summaries.
- Modify `tools/audit_run_latency.py`: report cache hits, repair attempts, repair successes, and full retries.
- Modify tests under `tests/`: focused unit/contract tests and audit assertions.

---

### Task 1: Config And Snapshot Foundation

**Files:**
- Modify: `src/seektalent/config.py`
- Modify: `src/seektalent/default.env`
- Modify: `src/seektalent/tracing.py`
- Modify: `src/seektalent/runtime/orchestrator.py`
- Test: `tests/test_llm_provider_config.py`
- Test: `tests/test_runtime_audit.py`

- [ ] **Step 1: Write failing config and snapshot tests**

Add these tests to `tests/test_llm_provider_config.py`:

```python
def test_app_settings_enables_requirements_controller_and_reflection_thinking_by_default() -> None:
    settings = make_settings()

    assert settings.requirements_enable_thinking is True
    assert settings.controller_enable_thinking is True
    assert settings.reflection_enable_thinking is True


def test_app_settings_defaults_scoring_concurrency_to_recall_target() -> None:
    settings = make_settings()

    assert settings.scoring_max_concurrency == 10


def test_app_settings_accepts_repair_cache_and_prompt_cache_settings() -> None:
    settings = make_settings(
        structured_repair_model="openai-chat:qwen3.5-flash",
        structured_repair_reasoning_effort="off",
        llm_cache_dir=".custom-cache",
        openai_prompt_cache_enabled=True,
        openai_prompt_cache_retention="24h",
    )

    assert settings.structured_repair_model == "openai-chat:qwen3.5-flash"
    assert settings.structured_repair_reasoning_effort == "off"
    assert settings.llm_cache_dir == ".custom-cache"
    assert settings.openai_prompt_cache_enabled is True
    assert settings.openai_prompt_cache_retention == "24h"
```

Add this test to `tests/test_runtime_audit.py` near the existing `run_config` assertions:

```python
def test_run_config_records_latency_engineering_settings(tmp_path: Path) -> None:
    settings = make_settings(
        runs_dir=str(tmp_path),
        mock_cts=True,
        requirements_enable_thinking=True,
        controller_enable_thinking=True,
        reflection_enable_thinking=False,
        scoring_max_concurrency=10,
        structured_repair_model="openai-chat:qwen3.5-flash",
        structured_repair_reasoning_effort="off",
        llm_cache_dir=".cache/seektalent-llm",
        openai_prompt_cache_enabled=True,
        openai_prompt_cache_retention="24h",
    )
    runtime = WorkflowRuntime(settings)
    run_config = runtime._build_public_run_config()

    assert run_config["settings"]["requirements_enable_thinking"] is True
    assert run_config["settings"]["controller_enable_thinking"] is True
    assert run_config["settings"]["reflection_enable_thinking"] is False
    assert run_config["settings"]["scoring_max_concurrency"] == 10
    assert run_config["settings"]["structured_repair_model"] == "openai-chat:qwen3.5-flash"
    assert run_config["settings"]["structured_repair_reasoning_effort"] == "off"
    assert run_config["settings"]["llm_cache_dir"] == ".cache/seektalent-llm"
    assert run_config["settings"]["openai_prompt_cache_enabled"] is True
    assert run_config["settings"]["openai_prompt_cache_retention"] == "24h"
```

Add this test to `tests/test_runtime_audit.py` or a new `tests/test_tracing_snapshot.py`:

```python
from seektalent.tracing import LLMCallSnapshot


def test_llm_call_snapshot_accepts_cache_repair_and_prompt_cache_metadata() -> None:
    snapshot = LLMCallSnapshot(
        stage="controller",
        call_id="controller-r01",
        model_id="openai-chat:deepseek-v3.2",
        provider="openai-chat",
        prompt_hash="prompt-hash",
        prompt_snapshot_path="prompt_snapshots/controller.md",
        retries=0,
        output_retries=0,
        started_at="2026-04-23T12:00:00+08:00",
        latency_ms=12,
        status="succeeded",
        input_payload_sha256="input-hash",
        structured_output_sha256="output-hash",
        prompt_chars=100,
        input_payload_chars=200,
        output_chars=50,
        input_summary="round=1",
        cache_hit=True,
        cache_key="controller-cache-key",
        cache_lookup_latency_ms=2,
        prompt_cache_key="controller:abc",
        prompt_cache_retention="24h",
        cached_input_tokens=512,
        repair_attempt_count=1,
        repair_succeeded=True,
        repair_model="openai-chat:qwen3.5-flash",
        repair_reason="response_to_reflection is required when previous_reflection exists.",
        full_retry_count=0,
    )

    payload = snapshot.model_dump(mode="json")

    assert payload["cache_hit"] is True
    assert payload["cache_key"] == "controller-cache-key"
    assert payload["cache_lookup_latency_ms"] == 2
    assert payload["prompt_cache_key"] == "controller:abc"
    assert payload["prompt_cache_retention"] == "24h"
    assert payload["cached_input_tokens"] == 512
    assert payload["repair_attempt_count"] == 1
    assert payload["repair_succeeded"] is True
    assert payload["repair_model"] == "openai-chat:qwen3.5-flash"
    assert payload["full_retry_count"] == 0
```

- [ ] **Step 2: Run tests and confirm they fail**

Run:

```bash
uv run pytest tests/test_llm_provider_config.py::test_app_settings_enables_requirements_controller_and_reflection_thinking_by_default tests/test_llm_provider_config.py::test_app_settings_defaults_scoring_concurrency_to_recall_target tests/test_llm_provider_config.py::test_app_settings_accepts_repair_cache_and_prompt_cache_settings tests/test_runtime_audit.py::test_run_config_records_latency_engineering_settings -q
```

Expected: failures for missing settings and old default `scoring_max_concurrency == 5`.

- [ ] **Step 3: Add config fields and default scoring concurrency**

Modify `src/seektalent/config.py`:

```python
MODEL_FIELDS = (
    "requirements_model",
    "controller_model",
    "scoring_model",
    "finalize_model",
    "reflection_model",
    "judge_model",
    "tui_summary_model",
    "candidate_feedback_model",
    "company_discovery_model",
    "structured_repair_model",
)
```

In `AppSettings`, keep the existing model defaults and insert these fields with the nearby LLM settings:

```python
    reasoning_effort: ReasoningEffort = "medium"
    judge_reasoning_effort: ReasoningEffort | None = None
    requirements_enable_thinking: bool = True
    controller_enable_thinking: bool = True
    reflection_enable_thinking: bool = True
    structured_repair_model: str = "openai-chat:qwen3.5-flash"
    structured_repair_reasoning_effort: ReasoningEffort = "off"
    llm_cache_dir: str = ".seektalent/cache"
    openai_prompt_cache_enabled: bool = False
    openai_prompt_cache_retention: str | None = None
```

Change the scoring concurrency default:

```python
    scoring_max_concurrency: int = 10
```

Keep the existing `scoring_max_concurrency >= 1` validator unchanged.

- [ ] **Step 4: Add environment documentation**

Modify `src/seektalent/default.env` by adding these lines next to the related model and runtime settings:

```dotenv
SEEKTALENT_REQUIREMENTS_ENABLE_THINKING=true
SEEKTALENT_STRUCTURED_REPAIR_MODEL=openai-chat:qwen3.5-flash
SEEKTALENT_STRUCTURED_REPAIR_REASONING_EFFORT=off
SEEKTALENT_LLM_CACHE_DIR=.seektalent/cache
SEEKTALENT_OPENAI_PROMPT_CACHE_ENABLED=false
SEEKTALENT_OPENAI_PROMPT_CACHE_RETENTION=
SEEKTALENT_SCORING_MAX_CONCURRENCY=10
```

- [ ] **Step 5: Extend LLM call snapshot metadata**

Modify `src/seektalent/tracing.py`:

```python
class LLMCallSnapshot(BaseModel):
    stage: str
    call_id: str
    round_no: int | None = None
    resume_id: str | None = None
    branch_id: str | None = None
    model_id: str
    provider: str
    prompt_hash: str
    prompt_snapshot_path: str
    output_mode: Literal["native_strict"] = "native_strict"
    retries: int
    output_retries: int
    started_at: str
    latency_ms: int | None = None
    status: Literal["succeeded", "failed"]
    input_artifact_refs: list[str] = Field(default_factory=list)
    output_artifact_refs: list[str] = Field(default_factory=list)
    input_payload_sha256: str
    structured_output_sha256: str | None = None
    prompt_chars: int
    input_payload_chars: int
    output_chars: int
    input_summary: str
    output_summary: str | None = None
    error_message: str | None = None
    validator_retry_count: int = 0
    validator_retry_reasons: list[str] = Field(default_factory=list)
    cache_hit: bool = False
    cache_key: str | None = None
    cache_lookup_latency_ms: int | None = None
    prompt_cache_key: str | None = None
    prompt_cache_retention: str | None = None
    cached_input_tokens: int | None = None
    repair_attempt_count: int = 0
    repair_succeeded: bool = False
    repair_model: str | None = None
    repair_reason: str | None = None
    full_retry_count: int = 0
```

- [ ] **Step 6: Record new settings in public run config**

Modify `WorkflowRuntime._build_public_run_config()` in `src/seektalent/runtime/orchestrator.py` so the `settings` dict includes:

```python
                "requirements_enable_thinking": self.settings.requirements_enable_thinking,
                "controller_enable_thinking": self.settings.controller_enable_thinking,
                "reflection_enable_thinking": self.settings.reflection_enable_thinking,
                "structured_repair_model": self.settings.structured_repair_model,
                "structured_repair_reasoning_effort": self.settings.structured_repair_reasoning_effort,
                "llm_cache_dir": self.settings.llm_cache_dir,
                "openai_prompt_cache_enabled": self.settings.openai_prompt_cache_enabled,
                "openai_prompt_cache_retention": self.settings.openai_prompt_cache_retention,
```

Keep existing sanitized secret handling unchanged.

- [ ] **Step 7: Run tests**

Run:

```bash
uv run pytest tests/test_llm_provider_config.py::test_app_settings_enables_requirements_controller_and_reflection_thinking_by_default tests/test_llm_provider_config.py::test_app_settings_defaults_scoring_concurrency_to_recall_target tests/test_llm_provider_config.py::test_app_settings_accepts_repair_cache_and_prompt_cache_settings tests/test_runtime_audit.py::test_run_config_records_latency_engineering_settings tests/test_runtime_audit.py::test_llm_call_snapshot_accepts_cache_repair_and_prompt_cache_metadata -q
```

Expected: all selected tests pass.

- [ ] **Step 8: Commit**

```bash
git add src/seektalent/config.py src/seektalent/default.env src/seektalent/tracing.py src/seektalent/runtime/orchestrator.py tests/test_llm_provider_config.py tests/test_runtime_audit.py
git commit -m "Add latency engineering settings"
```

---

### Task 2: Prompt-Cache Request Knobs

**Files:**
- Modify: `src/seektalent/llm.py`
- Modify: `src/seektalent/requirements/extractor.py`
- Modify: `src/seektalent/controller/react_controller.py`
- Modify: `src/seektalent/reflection/critic.py`
- Modify: `src/seektalent/scoring/scorer.py`
- Modify: `src/seektalent/runtime/orchestrator.py`
- Test: `tests/test_llm_provider_config.py`

- [ ] **Step 1: Write failing prompt-cache tests**

Add these tests to `tests/test_llm_provider_config.py`:

```python
def test_build_model_settings_adds_prompt_cache_fields_when_enabled() -> None:
    settings = make_settings(
        openai_prompt_cache_enabled=True,
        openai_prompt_cache_retention="24h",
    )

    model_settings = build_model_settings(
        settings,
        "openai-responses:gpt-5.4-mini",
        prompt_cache_key="requirements:abc",
    )

    assert model_settings["openai_prompt_cache_key"] == "requirements:abc"
    assert model_settings["openai_prompt_cache_retention"] == "24h"


def test_build_model_settings_omits_prompt_cache_fields_when_disabled() -> None:
    settings = make_settings(openai_prompt_cache_enabled=False)

    model_settings = build_model_settings(
        settings,
        "openai-responses:gpt-5.4-mini",
        prompt_cache_key="requirements:abc",
    )

    assert "openai_prompt_cache_key" not in model_settings
    assert "openai_prompt_cache_retention" not in model_settings


def test_build_model_settings_keeps_bailian_enable_thinking_extra_body_with_prompt_cache() -> None:
    settings = make_settings(
        openai_prompt_cache_enabled=True,
        openai_prompt_cache_retention="24h",
    )

    model_settings = build_model_settings(
        settings,
        "openai-chat:deepseek-v3.2",
        enable_thinking=True,
        prompt_cache_key="controller:abc",
    )

    assert model_settings["extra_body"] == {"enable_thinking": True}
    assert model_settings["openai_prompt_cache_key"] == "controller:abc"
    assert model_settings["openai_prompt_cache_retention"] == "24h"
```

- [ ] **Step 2: Run tests and confirm they fail**

Run:

```bash
uv run pytest tests/test_llm_provider_config.py::test_build_model_settings_adds_prompt_cache_fields_when_enabled tests/test_llm_provider_config.py::test_build_model_settings_omits_prompt_cache_fields_when_disabled tests/test_llm_provider_config.py::test_build_model_settings_keeps_bailian_enable_thinking_extra_body_with_prompt_cache -q
```

Expected: failure because `prompt_cache_key` is not accepted.

- [ ] **Step 3: Extend `build_model_settings`**

Modify `src/seektalent/llm.py`:

```python
def _add_prompt_cache_settings(
    *,
    settings: AppSettings,
    model_id: str,
    model_settings: ModelSettings,
    prompt_cache_key: str | None,
) -> ModelSettings:
    if not settings.openai_prompt_cache_enabled or not prompt_cache_key:
        return model_settings
    if not model_id.startswith(("openai:", "openai-chat:", "openai-responses:")):
        return model_settings
    model_settings["openai_prompt_cache_key"] = prompt_cache_key
    if settings.openai_prompt_cache_retention:
        model_settings["openai_prompt_cache_retention"] = settings.openai_prompt_cache_retention
    return model_settings
```

Update the function signature and return paths:

```python
def build_model_settings(
    settings: AppSettings,
    model_id: str,
    *,
    reasoning_effort: ReasoningEffort | None = None,
    enable_thinking: bool | None = None,
    prompt_cache_key: str | None = None,
) -> ModelSettings:
    effective_effort = reasoning_effort or settings.reasoning_effort
    if effective_effort == "off":
        thinking = False
    else:
        thinking = effective_effort
    model_settings: ModelSettings = {"thinking": thinking}
    if model_id in BAILIAN_THINKING_MODELS and enable_thinking is not None:
        model_settings["extra_body"] = {"enable_thinking": enable_thinking}
    if not model_id.startswith("openai-responses:"):
        return _add_prompt_cache_settings(
            settings=settings,
            model_id=model_id,
            model_settings=model_settings,
            prompt_cache_key=prompt_cache_key,
        )

    openai_settings: dict[str, object] = {
        "thinking": thinking,
        "openai_text_verbosity": "low",
    }
    if thinking is not False:
        openai_settings["openai_reasoning_summary"] = "concise"
    return cast(
        ModelSettings,
        _add_prompt_cache_settings(
            settings=settings,
            model_id=model_id,
            model_settings=cast(ModelSettings, openai_settings),
            prompt_cache_key=prompt_cache_key,
        ),
    )
```

- [ ] **Step 4: Add stage key helper**

Add this helper near `_build_llm_call_snapshot` in `src/seektalent/runtime/orchestrator.py`:

```python
    def _prompt_cache_key(self, *, stage: str, model_id: str, input_hash: str) -> str | None:
        if not self.settings.openai_prompt_cache_enabled:
            return None
        return f"{stage}:{model_id}:{input_hash}"
```

Use the same helper in stage code when building requirements/controller/reflection/scoring agents in later tasks. In this task, no stage behavior changes are needed beyond the model settings tests.

- [ ] **Step 5: Run tests**

Run:

```bash
uv run pytest tests/test_llm_provider_config.py::test_build_model_settings_adds_prompt_cache_fields_when_enabled tests/test_llm_provider_config.py::test_build_model_settings_omits_prompt_cache_fields_when_disabled tests/test_llm_provider_config.py::test_build_model_settings_keeps_bailian_enable_thinking_extra_body_with_prompt_cache -q
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/seektalent/llm.py src/seektalent/runtime/orchestrator.py tests/test_llm_provider_config.py
git commit -m "Add prompt cache model settings"
```

---

### Task 3: Exact LLM Cache Helpers

**Files:**
- Create: `src/seektalent/runtime/exact_llm_cache.py`
- Test: `tests/test_exact_llm_cache.py`

- [ ] **Step 1: Write failing exact-cache tests**

Create `tests/test_exact_llm_cache.py`:

```python
from pathlib import Path

from seektalent.runtime.exact_llm_cache import get_cached_json, put_cached_json, stable_cache_key
from tests.settings_factory import make_settings


def test_stable_cache_key_hashes_sorted_json_parts() -> None:
    key_a = stable_cache_key({"b": 2, "a": 1})
    key_b = stable_cache_key({"a": 1, "b": 2})

    assert key_a == key_b
    assert len(key_a) == 64


def test_exact_cache_round_trips_json_payload(tmp_path: Path) -> None:
    settings = make_settings(llm_cache_dir=str(tmp_path / "cache"))
    key = stable_cache_key({"model": "openai-chat:qwen3.5-flash", "input": "abc"})
    payload = {"fit_bucket": "fit", "overall_score": 88}

    put_cached_json(settings, namespace="scoring", key=key, payload=payload)

    assert get_cached_json(settings, namespace="scoring", key=key) == payload


def test_exact_cache_keeps_namespaces_separate(tmp_path: Path) -> None:
    settings = make_settings(llm_cache_dir=str(tmp_path / "cache"))
    key = stable_cache_key({"input": "abc"})

    put_cached_json(settings, namespace="requirements", key=key, payload={"stage": "requirements"})

    assert get_cached_json(settings, namespace="scoring", key=key) is None
```

- [ ] **Step 2: Run tests and confirm they fail**

Run:

```bash
uv run pytest tests/test_exact_llm_cache.py -q
```

Expected: import failure for missing `seektalent.runtime.exact_llm_cache`.

- [ ] **Step 3: Implement sqlite exact-cache functions**

Create `src/seektalent/runtime/exact_llm_cache.py`:

```python
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from seektalent.config import AppSettings
from seektalent.resources import resolve_user_path
from seektalent.tracing import json_sha256, jsonable


def stable_cache_key(parts: Any) -> str:
    return json_sha256(parts)


def _database_path(settings: AppSettings) -> Path:
    cache_dir = resolve_user_path(settings.llm_cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "exact_llm_cache.sqlite3"


def _connect(settings: AppSettings) -> sqlite3.Connection:
    connection = sqlite3.connect(_database_path(settings), timeout=30)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS entries (
            namespace TEXT NOT NULL,
            key TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (namespace, key)
        )
        """
    )
    return connection


def get_cached_json(settings: AppSettings, *, namespace: str, key: str) -> dict[str, Any] | None:
    with _connect(settings) as connection:
        row = connection.execute(
            "SELECT payload FROM entries WHERE namespace = ? AND key = ?",
            (namespace, key),
        ).fetchone()
    if row is None:
        return None
    return json.loads(row[0])


def put_cached_json(settings: AppSettings, *, namespace: str, key: str, payload: dict[str, Any]) -> None:
    text = json.dumps(jsonable(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    with _connect(settings) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO entries(namespace, key, payload, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (namespace, key, text, datetime.now().astimezone().isoformat(timespec="seconds")),
        )
```

- [ ] **Step 4: Run tests**

Run:

```bash
uv run pytest tests/test_exact_llm_cache.py -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/seektalent/runtime/exact_llm_cache.py tests/test_exact_llm_cache.py
git commit -m "Add exact LLM cache helpers"
```

---

### Task 4: Requirements Thinking, Cache, And Repair

**Files:**
- Modify: `src/seektalent/requirements/extractor.py`
- Modify: `src/seektalent/repair.py`
- Modify: `src/seektalent/runtime/orchestrator.py`
- Test: `tests/test_llm_provider_config.py`
- Test: `tests/test_requirement_extraction.py`

- [ ] **Step 1: Write failing Requirements Thinking test**

Add this test to `tests/test_llm_provider_config.py`:

```python
def test_requirement_extractor_passes_requirements_thinking_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object | None]] = []

    def fake_build_model_settings(settings, model_id, *, reasoning_effort=None, enable_thinking=None, prompt_cache_key=None):  # noqa: ANN001
        calls.append({"enable_thinking": enable_thinking, "prompt_cache_key": prompt_cache_key})
        return {}

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("seektalent.requirements.extractor.build_model_settings", fake_build_model_settings)

    extractor = RequirementExtractor(
        make_settings(requirements_model="openai-chat:deepseek-v3.2", requirements_enable_thinking=True),
        _prompt("requirements"),
    )

    extractor._get_agent(prompt_cache_key="requirements:abc")

    assert calls == [{"enable_thinking": True, "prompt_cache_key": "requirements:abc"}]
```

- [ ] **Step 2: Write failing requirements repair and cache tests**

Add these tests to `tests/test_requirement_extraction.py`:

```python
from pathlib import Path

import pytest

from seektalent.models import RequirementExtractionDraft
from seektalent.prompting import LoadedPrompt
from seektalent.requirements.extractor import RequirementExtractor, requirement_cache_key
from seektalent.requirements.normalization import build_input_truth
from seektalent.runtime.exact_llm_cache import put_cached_json
from tests.settings_factory import make_settings


def _valid_requirement_draft() -> RequirementExtractionDraft:
    return RequirementExtractionDraft(
        title_anchor_term="Python工程师",
        role_summary="Build backend and retrieval services.",
        must_have_capabilities=["Python", "后端"],
        preferred_capabilities=["检索"],
        exclusion_signals=[],
        locations=["上海"],
        preferred_locations=[],
        school_names=[],
        degree_requirement=None,
        school_type_requirement=[],
        experience_requirement=None,
        gender_requirement=None,
        age_requirement=None,
        company_names=[],
        preferred_companies=[],
        preferred_domains=[],
        preferred_backgrounds=[],
        preferred_query_terms=[],
        jd_query_terms=["后端"],
        notes_query_terms=[],
        scoring_rationale="Score Python backend fit first.",
    )


@pytest.mark.asyncio
async def test_requirement_cache_hit_skips_provider_and_normalizes_current_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = make_settings(llm_cache_dir=str(tmp_path / "cache"))
    input_truth = build_input_truth(job_title="Python工程师", jd="需要 Python 后端经验", notes="")
    prompt = LoadedPrompt(name="requirements", path=Path("requirements.md"), content="requirements prompt", sha256="prompt-hash")
    extractor = RequirementExtractor(settings, prompt)
    draft = _valid_requirement_draft()
    key = requirement_cache_key(settings=settings, prompt=prompt, input_truth=input_truth)
    put_cached_json(settings, namespace="requirements", key=key, payload=draft.model_dump(mode="json"))
    provider_calls = 0

    async def fake_live_extract(*, input_truth, prompt_cache_key=None):  # noqa: ANN001
        nonlocal provider_calls
        provider_calls += 1
        return draft

    monkeypatch.setattr(extractor, "_extract_live", fake_live_extract)

    cached_draft, sheet = await extractor.extract_with_draft(input_truth=input_truth)

    assert provider_calls == 0
    assert cached_draft == draft
    assert sheet.role_title == "Python工程师"


@pytest.mark.asyncio
async def test_requirement_repair_fixes_empty_non_anchor_jd_terms(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = make_settings()
    prompt = LoadedPrompt(name="requirements", path=Path("requirements.md"), content="requirements prompt", sha256="prompt-hash")
    extractor = RequirementExtractor(settings, prompt)
    input_truth = build_input_truth(job_title="Python工程师", jd="需要 Python 后端经验", notes="")
    bad_draft = _valid_requirement_draft().model_copy(update={"jd_query_terms": ["Python工程师"]})
    repaired_draft = bad_draft.model_copy(update={"jd_query_terms": ["后端"]})

    async def fake_live_extract(*, input_truth, prompt_cache_key=None):  # noqa: ANN001
        return bad_draft

    async def fake_repair_requirement_draft(*, settings, prompt, input_truth, draft, reason):  # noqa: ANN001
        assert "jd_query_terms must contain at least one non-anchor term" in reason
        return repaired_draft

    monkeypatch.setattr(extractor, "_extract_live", fake_live_extract)
    monkeypatch.setattr("seektalent.requirements.extractor.repair_requirement_draft", fake_repair_requirement_draft)

    draft, sheet = await extractor.extract_with_draft(input_truth=input_truth)

    assert draft == repaired_draft
    assert sheet.initial_query_term_pool
    assert extractor.last_repair_attempt_count == 1
    assert extractor.last_repair_succeeded is True
    assert extractor.last_repair_reason == "jd_query_terms must contain at least one non-anchor term after normalization"
```

- [ ] **Step 3: Run tests and confirm they fail**

Run:

```bash
uv run pytest tests/test_llm_provider_config.py::test_requirement_extractor_passes_requirements_thinking_flag tests/test_requirement_extraction.py::test_requirement_cache_hit_skips_provider_and_normalizes_current_code tests/test_requirement_extraction.py::test_requirement_repair_fixes_empty_non_anchor_jd_terms -q
```

Expected: missing cache key helper, missing `_extract_live`, missing repair fields, and thinking flag not passed.

- [ ] **Step 4: Implement repair helper for requirements**

Create or modify `src/seektalent/repair.py`:

```python
from __future__ import annotations

from typing import TypeVar, cast

from pydantic_ai import Agent

from seektalent.config import AppSettings
from seektalent.llm import build_model, build_model_settings, build_output_spec
from seektalent.models import (
    ControllerContext,
    ControllerDecision,
    InputTruth,
    ReflectionAdviceDraft,
    RequirementExtractionDraft,
)
from seektalent.prompting import LoadedPrompt, json_block

T = TypeVar("T")


async def _repair_with_model(
    *,
    settings: AppSettings,
    output_type: type[T],
    system_prompt: str,
    user_prompt: str,
) -> T:
    model = build_model(settings.structured_repair_model)
    agent = cast(Agent[None, T], Agent(
        model=model,
        output_type=build_output_spec(settings.structured_repair_model, model, output_type),
        system_prompt=system_prompt,
        model_settings=build_model_settings(
            settings,
            settings.structured_repair_model,
            reasoning_effort=settings.structured_repair_reasoning_effort,
        ),
        retries=0,
        output_retries=1,
    ))
    result = await agent.run(user_prompt)
    return result.output


async def repair_requirement_draft(
    *,
    settings: AppSettings,
    prompt: LoadedPrompt,
    input_truth: InputTruth,
    draft: RequirementExtractionDraft,
    reason: str,
) -> RequirementExtractionDraft:
    user_prompt = "\n\n".join(
        [
            "Repair this RequirementExtractionDraft so it passes the stated validation reason.",
            "Return the complete corrected RequirementExtractionDraft. Preserve valid existing fields.",
            f"VALIDATION REASON\n{reason}",
            json_block("INPUT_TRUTH", input_truth.model_dump(mode="json")),
            json_block("CURRENT_DRAFT", draft.model_dump(mode="json")),
        ]
    )
    return await _repair_with_model(
        settings=settings,
        output_type=RequirementExtractionDraft,
        system_prompt=prompt.content,
        user_prompt=user_prompt,
    )
```

The controller and reflection imports are used by later tasks in the same file.

- [ ] **Step 5: Implement requirements cache key and extraction flow**

Modify `src/seektalent/requirements/extractor.py`:

```python
from time import perf_counter

from seektalent.repair import repair_requirement_draft
from seektalent.runtime.exact_llm_cache import get_cached_json, put_cached_json, stable_cache_key
```

Add cache schema and key helper:

```python
REQUIREMENTS_CACHE_SCHEMA_VERSION = "requirement_extraction_draft.v1"


def requirement_cache_key(
    *,
    settings: AppSettings,
    prompt: LoadedPrompt,
    input_truth: InputTruth,
) -> str:
    return stable_cache_key(
        {
            "schema": REQUIREMENTS_CACHE_SCHEMA_VERSION,
            "model_id": settings.requirements_model,
            "prompt_hash": prompt.sha256,
            "job_title_sha256": input_truth.job_title_sha256,
            "jd_sha256": input_truth.jd_sha256,
            "notes_sha256": input_truth.notes_sha256,
        }
    )
```

Update `RequirementExtractor` state:

```python
class RequirementExtractor:
    def __init__(self, settings: AppSettings, prompt: LoadedPrompt) -> None:
        self.settings = settings
        self.prompt = prompt
        self.last_cache_hit = False
        self.last_cache_key: str | None = None
        self.last_cache_lookup_latency_ms: int | None = None
        self.last_repair_attempt_count = 0
        self.last_repair_succeeded = False
        self.last_repair_reason: str | None = None
        self.last_full_retry_count = 0
```

Change `_get_agent` and add `_extract_live`:

```python
    def _get_agent(self, *, prompt_cache_key: str | None = None) -> Agent[None, RequirementExtractionDraft]:
        model = build_model(self.settings.requirements_model)
        return cast(Agent[None, RequirementExtractionDraft], Agent(
            model=model,
            output_type=build_output_spec(self.settings.requirements_model, model, RequirementExtractionDraft),
            system_prompt=self.prompt.content,
            model_settings=build_model_settings(
                self.settings,
                self.settings.requirements_model,
                enable_thinking=self.settings.requirements_enable_thinking,
                prompt_cache_key=prompt_cache_key,
            ),
            retries=0,
            output_retries=2,
        ))

    async def _extract_live(
        self,
        *,
        input_truth: InputTruth,
        prompt_cache_key: str | None = None,
    ) -> RequirementExtractionDraft:
        result = await self._get_agent(prompt_cache_key=prompt_cache_key).run(render_requirements_prompt(input_truth))
        return result.output
```

Replace `extract_with_draft`:

```python
    async def extract_with_draft(self, *, input_truth: InputTruth) -> tuple[RequirementExtractionDraft, RequirementSheet]:
        self.last_cache_hit = False
        self.last_cache_key = requirement_cache_key(settings=self.settings, prompt=self.prompt, input_truth=input_truth)
        self.last_cache_lookup_latency_ms = None
        self.last_repair_attempt_count = 0
        self.last_repair_succeeded = False
        self.last_repair_reason = None
        self.last_full_retry_count = 0

        cache_started = perf_counter()
        cached = get_cached_json(self.settings, namespace="requirements", key=self.last_cache_key)
        self.last_cache_lookup_latency_ms = max(0, int((perf_counter() - cache_started) * 1000))
        if cached is not None:
            draft = RequirementExtractionDraft.model_validate(cached)
            self.last_cache_hit = True
            return draft, normalize_requirement_draft(draft, job_title=input_truth.job_title)

        draft = await self._extract_live(
            input_truth=input_truth,
            prompt_cache_key=f"requirements:{self.settings.requirements_model}:{self.last_cache_key}",
        )
        try:
            sheet = normalize_requirement_draft(draft, job_title=input_truth.job_title)
        except ValueError as exc:
            self.last_repair_attempt_count = 1
            self.last_repair_reason = str(exc)
            repaired = await repair_requirement_draft(
                settings=self.settings,
                prompt=self.prompt,
                input_truth=input_truth,
                draft=draft,
                reason=str(exc),
            )
            sheet = normalize_requirement_draft(repaired, job_title=input_truth.job_title)
            draft = repaired
            self.last_repair_succeeded = True

        put_cached_json(
            self.settings,
            namespace="requirements",
            key=self.last_cache_key,
            payload=draft.model_dump(mode="json"),
        )
        return draft, sheet
```

- [ ] **Step 6: Add requirements metadata to orchestrator snapshots**

In `_build_run_state`, pass these fields into the success and failure requirements snapshots:

```python
                    cache_hit=self.requirement_extractor.last_cache_hit,
                    cache_key=self.requirement_extractor.last_cache_key,
                    cache_lookup_latency_ms=self.requirement_extractor.last_cache_lookup_latency_ms,
                    prompt_cache_key=(
                        f"requirements:{self.settings.requirements_model}:{self.requirement_extractor.last_cache_key}"
                        if self.requirement_extractor.last_cache_key
                        else None
                    ),
                    prompt_cache_retention=self.settings.openai_prompt_cache_retention,
                    repair_attempt_count=self.requirement_extractor.last_repair_attempt_count,
                    repair_succeeded=self.requirement_extractor.last_repair_succeeded,
                    repair_model=(
                        self.settings.structured_repair_model
                        if self.requirement_extractor.last_repair_attempt_count
                        else None
                    ),
                    repair_reason=self.requirement_extractor.last_repair_reason,
                    full_retry_count=self.requirement_extractor.last_full_retry_count,
```

Add matching optional parameters to `_build_llm_call_snapshot` and forward them to `LLMCallSnapshot`.

- [ ] **Step 7: Run tests**

Run:

```bash
uv run pytest tests/test_llm_provider_config.py::test_requirement_extractor_passes_requirements_thinking_flag tests/test_requirement_extraction.py::test_requirement_cache_hit_skips_provider_and_normalizes_current_code tests/test_requirement_extraction.py::test_requirement_repair_fixes_empty_non_anchor_jd_terms -q
```

Expected: all selected tests pass.

- [ ] **Step 8: Commit**

```bash
git add src/seektalent/repair.py src/seektalent/requirements/extractor.py src/seektalent/runtime/orchestrator.py tests/test_llm_provider_config.py tests/test_requirement_extraction.py
git commit -m "Add requirements cache and repair path"
```

---

### Task 5: Controller Semantic Repair Outside Pydantic AI Retries

**Files:**
- Modify: `src/seektalent/controller/react_controller.py`
- Modify: `src/seektalent/repair.py`
- Modify: `src/seektalent/runtime/orchestrator.py`
- Test: `tests/test_controller_contract.py`

- [ ] **Step 1: Replace validator tests with explicit semantic validation tests**

In `tests/test_controller_contract.py`, replace direct `_output_validators[0]` tests with tests for a new function `validate_controller_decision`:

```python
from seektalent.controller.react_controller import ReActController, validate_controller_decision
```

Use this test shape for missing reflection response:

```python
def test_validate_controller_decision_rejects_missing_response_to_reflection() -> None:
    context = _controller_context(
        round_no=2,
        previous_reflection=ReflectionSummaryView(decision="continue", reflection_summary="Add one term."),
    )
    decision = SearchControllerDecision(
        thought_summary="Search again.",
        action="search_cts",
        decision_rationale="Add one more term.",
        proposed_query_terms=["python", "resume matching", "trace"],
        proposed_filter_plan=ProposedFilterPlan(),
    )

    reason = validate_controller_decision(context=context, decision=decision)

    assert reason == "response_to_reflection is required when previous_reflection exists."
```

Use this shape for empty terms:

```python
def test_validate_controller_decision_rejects_empty_query_terms() -> None:
    context = _controller_context()
    decision = SearchControllerDecision(
        thought_summary="Search again.",
        action="search_cts",
        decision_rationale="Need recall.",
        proposed_query_terms=[],
        proposed_filter_plan=ProposedFilterPlan(),
    )

    reason = validate_controller_decision(context=context, decision=decision)

    assert reason == "proposed_query_terms must contain at least one term."
```

Use this shape for accepted query terms:

```python
def test_validate_controller_decision_accepts_compiled_anchor_alias_without_literal_title_anchor() -> None:
    requirement_sheet = _agent_requirement_sheet()
    context = _controller_context(requirement_sheet=requirement_sheet)
    decision = SearchControllerDecision(
        thought_summary="Search.",
        action="search_cts",
        decision_rationale="Need Agent recall.",
        proposed_query_terms=["AI Agent", "LangChain"],
        proposed_filter_plan=ProposedFilterPlan(),
    )

    assert validate_controller_decision(context=context, decision=decision) is None
```

- [ ] **Step 2: Add controller repair test**

Add this async test to `tests/test_controller_contract.py`:

```python
@pytest.mark.asyncio
async def test_controller_repair_avoids_pydantic_output_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    context = _controller_context(
        round_no=2,
        previous_reflection=ReflectionSummaryView(decision="continue", reflection_summary="Add one term."),
    )
    bad_decision = SearchControllerDecision(
        thought_summary="Search again.",
        action="search_cts",
        decision_rationale="Need one more search.",
        proposed_query_terms=["python", "resume matching"],
        proposed_filter_plan=ProposedFilterPlan(),
    )
    repaired_decision = bad_decision.model_copy(update={"response_to_reflection": "Acknowledged; searching one more focused term."})
    controller = ReActController(make_settings(), LoadedPrompt(name="controller", path=Path("controller.md"), content="controller prompt", sha256="hash"))

    async def fake_decide_live(*, context, prompt_cache_key=None):  # noqa: ANN001
        return bad_decision

    async def fake_repair_controller_decision(*, settings, prompt, context, decision, reason):  # noqa: ANN001
        assert reason == "response_to_reflection is required when previous_reflection exists."
        return repaired_decision

    monkeypatch.setattr(controller, "_decide_live", fake_decide_live)
    monkeypatch.setattr("seektalent.controller.react_controller.repair_controller_decision", fake_repair_controller_decision)

    decision = await controller.decide(context=context)

    assert decision == repaired_decision
    assert controller.last_validator_retry_count == 1
    assert controller.last_validator_retry_reasons == ["response_to_reflection is required when previous_reflection exists."]
    assert controller.last_repair_attempt_count == 1
    assert controller.last_repair_succeeded is True
    assert controller.last_full_retry_count == 0
```

- [ ] **Step 3: Run tests and confirm they fail**

Run:

```bash
uv run pytest tests/test_controller_contract.py::test_validate_controller_decision_rejects_missing_response_to_reflection tests/test_controller_contract.py::test_validate_controller_decision_rejects_empty_query_terms tests/test_controller_contract.py::test_validate_controller_decision_accepts_compiled_anchor_alias_without_literal_title_anchor tests/test_controller_contract.py::test_controller_repair_avoids_pydantic_output_retry -q
```

Expected: missing function and controller repair attributes.

- [ ] **Step 4: Implement semantic validation function and live call split**

Modify `src/seektalent/controller/react_controller.py`:

```python
from seektalent.repair import repair_controller_decision
```

Add a plain validator above the class:

```python
def validate_controller_decision(
    *,
    context: ControllerContext,
    decision: ControllerDecision,
) -> str | None:
    if isinstance(decision, SearchControllerDecision) and not decision.proposed_query_terms:
        return "proposed_query_terms must contain at least one term."
    if isinstance(decision, SearchControllerDecision):
        try:
            canonicalize_controller_query_terms(
                decision.proposed_query_terms,
                round_no=context.round_no,
                title_anchor_term=context.requirement_sheet.title_anchor_term,
                query_term_pool=context.query_term_pool,
            )
        except ValueError as exc:
            return str(exc)
    if context.previous_reflection is not None and not (decision.response_to_reflection or "").strip():
        return "response_to_reflection is required when previous_reflection exists."
    return None
```

In `ReActController.__init__`, add:

```python
        self.last_repair_attempt_count = 0
        self.last_repair_succeeded = False
        self.last_repair_reason: str | None = None
        self.last_full_retry_count = 0
```

Remove `_record_retry` and the `@agent.output_validator` block from `_get_agent`. Keep `output_retries=2` for schema parse retries only.

Add `_decide_live`:

```python
    async def _decide_live(
        self,
        *,
        context: ControllerContext,
        prompt_cache_key: str | None = None,
    ) -> ControllerDecision:
        result = await self._get_agent(prompt_cache_key=prompt_cache_key).run(
            render_controller_prompt(context),
            deps=context,
        )
        return result.output
```

Update `_get_agent` to accept `prompt_cache_key` and pass it through:

```python
    def _get_agent(self, *, prompt_cache_key: str | None = None) -> Agent[ControllerContext, ControllerDecision]:
        model = build_model(self.settings.controller_model)
        return cast(Agent[ControllerContext, ControllerDecision], Agent(
            model=model,
            output_type=build_output_spec(self.settings.controller_model, model, ControllerDecision),
            system_prompt=self.prompt.content,
            deps_type=ControllerContext,
            model_settings=build_model_settings(
                self.settings,
                self.settings.controller_model,
                enable_thinking=self.settings.controller_enable_thinking,
                prompt_cache_key=prompt_cache_key,
            ),
            retries=0,
            output_retries=2,
        ))
```

Replace `decide`:

```python
    async def decide(self, *, context: ControllerContext) -> ControllerDecision:
        self.last_validator_retry_count = 0
        self.last_validator_retry_reasons = []
        self.last_repair_attempt_count = 0
        self.last_repair_succeeded = False
        self.last_repair_reason = None
        self.last_full_retry_count = 0

        prompt_cache_key = f"controller:{self.settings.controller_model}:{json_sha256(context.requirement_sheet.model_dump(mode='json'))}"
        decision = await self._decide_live(context=context, prompt_cache_key=prompt_cache_key)
        reason = validate_controller_decision(context=context, decision=decision)
        if reason is None:
            return decision

        self.last_validator_retry_count = 1
        self.last_validator_retry_reasons = [reason]
        self.last_repair_attempt_count = 1
        self.last_repair_reason = reason
        repaired = await repair_controller_decision(
            settings=self.settings,
            prompt=self.prompt,
            context=context,
            decision=decision,
            reason=reason,
        )
        repaired_reason = validate_controller_decision(context=context, decision=repaired)
        if repaired_reason is None:
            self.last_repair_succeeded = True
            return repaired

        self.last_full_retry_count = 1
        feedback_context = context.model_copy()
        retry_decision = await self._decide_live(
            context=feedback_context,
            prompt_cache_key=prompt_cache_key,
        )
        retry_reason = validate_controller_decision(context=context, decision=retry_decision)
        if retry_reason is not None:
            raise ValueError(retry_reason)
        return retry_decision
```

- [ ] **Step 5: Add controller model repair helper**

Add to `src/seektalent/repair.py`:

```python
async def repair_controller_decision(
    *,
    settings: AppSettings,
    prompt: LoadedPrompt,
    context: ControllerContext,
    decision: ControllerDecision,
    reason: str,
) -> ControllerDecision:
    user_prompt = "\n\n".join(
        [
            "Repair this ControllerDecision so it passes the stated validation reason.",
            "Return the complete corrected ControllerDecision. Preserve the action unless the validation reason requires changing it.",
            f"VALIDATION REASON\n{reason}",
            json_block("CONTROLLER_CONTEXT", context.model_dump(mode="json")),
            json_block("CURRENT_DECISION", decision.model_dump(mode="json")),
        ]
    )
    return await _repair_with_model(
        settings=settings,
        output_type=ControllerDecision,
        system_prompt=prompt.content,
        user_prompt=user_prompt,
    )
```

- [ ] **Step 6: Record controller repair metadata in snapshots**

In controller success/failure `_build_llm_call_snapshot(...)` calls in `src/seektalent/runtime/orchestrator.py`, add:

```python
                    repair_attempt_count=self.controller.last_repair_attempt_count,
                    repair_succeeded=self.controller.last_repair_succeeded,
                    repair_model=(
                        self.settings.structured_repair_model
                        if self.controller.last_repair_attempt_count
                        else None
                    ),
                    repair_reason=self.controller.last_repair_reason,
                    full_retry_count=self.controller.last_full_retry_count,
```

Keep existing `validator_retry_count` and `validator_retry_reasons` fields.

- [ ] **Step 7: Run controller tests**

Run:

```bash
uv run pytest tests/test_controller_contract.py -q
```

Expected: all controller tests pass after updating old validator assertions to the new plain validator contract.

- [ ] **Step 8: Commit**

```bash
git add src/seektalent/controller/react_controller.py src/seektalent/repair.py src/seektalent/runtime/orchestrator.py tests/test_controller_contract.py
git commit -m "Repair controller semantic validation before full retry"
```

---

### Task 6: Reflection Draft Repair Outside Schema Validation

**Files:**
- Modify: `src/seektalent/models.py`
- Modify: `src/seektalent/reflection/critic.py`
- Modify: `src/seektalent/repair.py`
- Modify: `src/seektalent/runtime/orchestrator.py`
- Test: `tests/test_reflection_contract.py`

- [ ] **Step 1: Write failing reflection draft validation tests**

In `tests/test_reflection_contract.py`, replace the draft stop-field rejection test with:

```python
from seektalent.reflection.critic import materialize_reflection_advice, repair_reflection_stop_fields, validate_reflection_draft
```

```python
def test_reflection_advice_draft_allows_invalid_stop_fields_for_repair() -> None:
    draft = ReflectionAdviceDraft(
        keyword_advice=ReflectionKeywordAdviceDraft(),
        filter_advice=ReflectionFilterAdviceDraft(),
        suggest_stop=True,
        reflection_rationale="Top pool is good enough to stop.",
    )

    assert validate_reflection_draft(draft) == "suggested_stop_reason is required when suggest_stop is true"
```

Add deterministic repair tests:

```python
def test_repair_reflection_stop_fields_nulls_reason_when_continue() -> None:
    draft = ReflectionAdviceDraft(
        keyword_advice=ReflectionKeywordAdviceDraft(),
        filter_advice=ReflectionFilterAdviceDraft(),
        suggest_stop=False,
        suggested_stop_reason="Search is saturated.",
        reflection_rationale="Continue because more terms remain.",
    )

    repaired = repair_reflection_stop_fields(draft)

    assert repaired.suggest_stop is False
    assert repaired.suggested_stop_reason is None
    assert validate_reflection_draft(repaired) is None


def test_repair_reflection_stop_fields_keeps_missing_stop_reason_for_model_repair() -> None:
    draft = ReflectionAdviceDraft(
        keyword_advice=ReflectionKeywordAdviceDraft(),
        filter_advice=ReflectionFilterAdviceDraft(),
        suggest_stop=True,
        reflection_rationale="Top pool is strong enough.",
    )

    assert repair_reflection_stop_fields(draft) == draft
```

Add async critic repair test:

```python
@pytest.mark.asyncio
async def test_reflection_critic_repairs_stop_reason_with_model(monkeypatch: pytest.MonkeyPatch) -> None:
    context = cast(Any, _context(round_no=3, unique_new_count=10))
    bad_draft = ReflectionAdviceDraft(
        keyword_advice=ReflectionKeywordAdviceDraft(),
        filter_advice=ReflectionFilterAdviceDraft(),
        suggest_stop=True,
        reflection_rationale="The top pool is strong enough.",
    )
    repaired_draft = bad_draft.model_copy(update={"suggested_stop_reason": "Top pool is strong enough to stop."})
    critic = ReflectionCritic(make_settings(), LoadedPrompt(name="reflection", path=Path("reflection.md"), content="reflection prompt", sha256="hash"))

    async def fake_reflect_live(*, context, prompt_cache_key=None):  # noqa: ANN001
        return bad_draft

    async def fake_repair_reflection_draft(*, settings, prompt, context, draft, reason):  # noqa: ANN001
        assert reason == "suggested_stop_reason is required when suggest_stop is true"
        return repaired_draft

    monkeypatch.setattr(critic, "_reflect_live", fake_reflect_live)
    monkeypatch.setattr("seektalent.reflection.critic.repair_reflection_draft", fake_repair_reflection_draft)

    advice = await critic.reflect(context=context)

    assert advice.suggest_stop is True
    assert advice.suggested_stop_reason == "Top pool is strong enough to stop."
    assert critic.last_repair_attempt_count == 1
    assert critic.last_repair_succeeded is True
    assert critic.last_full_retry_count == 0
```

- [ ] **Step 2: Run tests and confirm they fail**

Run:

```bash
uv run pytest tests/test_reflection_contract.py::test_reflection_advice_draft_allows_invalid_stop_fields_for_repair tests/test_reflection_contract.py::test_repair_reflection_stop_fields_nulls_reason_when_continue tests/test_reflection_contract.py::test_repair_reflection_stop_fields_keeps_missing_stop_reason_for_model_repair tests/test_reflection_contract.py::test_reflection_critic_repairs_stop_reason_with_model -q
```

Expected: draft still rejects invalid stop fields and helpers are missing.

- [ ] **Step 3: Let draft parse and add plain validation**

Modify `ReflectionAdviceDraft` in `src/seektalent/models.py` by removing its `@model_validator(mode="after")` method only. Do not remove the strict validator on final `ReflectionAdvice`.

Add to `src/seektalent/reflection/critic.py`:

```python
from seektalent.repair import repair_reflection_draft
from seektalent.tracing import json_sha256
```

Add helpers:

```python
def validate_reflection_draft(draft: ReflectionAdviceDraft) -> str | None:
    if draft.suggest_stop and not draft.suggested_stop_reason:
        return "suggested_stop_reason is required when suggest_stop is true"
    if not draft.suggest_stop and draft.suggested_stop_reason is not None:
        return "suggested_stop_reason must be null when suggest_stop is false"
    return None


def repair_reflection_stop_fields(draft: ReflectionAdviceDraft) -> ReflectionAdviceDraft:
    if not draft.suggest_stop and draft.suggested_stop_reason is not None:
        return draft.model_copy(update={"suggested_stop_reason": None})
    return draft
```

- [ ] **Step 4: Split live reflection call and add repair flow**

Update `ReflectionCritic.__init__`:

```python
        self.last_validator_retry_count = 0
        self.last_validator_retry_reasons: list[str] = []
        self.last_repair_attempt_count = 0
        self.last_repair_succeeded = False
        self.last_repair_reason: str | None = None
        self.last_full_retry_count = 0
```

Update `_get_agent`:

```python
    def _get_agent(self, *, prompt_cache_key: str | None = None) -> Agent[None, ReflectionAdviceDraft]:
        model = build_model(self.settings.reflection_model)
        return cast(Agent[None, ReflectionAdviceDraft], Agent(
            model=model,
            output_type=build_output_spec(self.settings.reflection_model, model, ReflectionAdviceDraft),
            system_prompt=self.prompt.content,
            model_settings=build_model_settings(
                self.settings,
                self.settings.reflection_model,
                enable_thinking=self.settings.reflection_enable_thinking,
                prompt_cache_key=prompt_cache_key,
            ),
            retries=0,
            output_retries=2,
        ))
```

Add `_reflect_live` and replace `reflect`:

```python
    async def _reflect_live(
        self,
        *,
        context: ReflectionContext,
        prompt_cache_key: str | None = None,
    ) -> ReflectionAdviceDraft:
        result = await self._get_agent(prompt_cache_key=prompt_cache_key).run(render_reflection_prompt(context))
        return result.output

    async def reflect(self, *, context: ReflectionContext) -> ReflectionAdvice:
        self.last_validator_retry_count = 0
        self.last_validator_retry_reasons = []
        self.last_repair_attempt_count = 0
        self.last_repair_succeeded = False
        self.last_repair_reason = None
        self.last_full_retry_count = 0

        prompt_cache_key = f"reflection:{self.settings.reflection_model}:{json_sha256(context.requirement_sheet.model_dump(mode='json'))}"
        draft = await self._reflect_live(context=context, prompt_cache_key=prompt_cache_key)
        reason = validate_reflection_draft(draft)
        if reason is None:
            return materialize_reflection_advice(context=context, draft=draft)

        self.last_validator_retry_count = 1
        self.last_validator_retry_reasons = [reason]
        self.last_repair_attempt_count = 1
        self.last_repair_reason = reason
        repaired = repair_reflection_stop_fields(draft)
        repaired_reason = validate_reflection_draft(repaired)
        if repaired_reason is not None:
            repaired = await repair_reflection_draft(
                settings=self.settings,
                prompt=self.prompt,
                context=context,
                draft=draft,
                reason=reason,
            )
            repaired_reason = validate_reflection_draft(repaired)
        if repaired_reason is None:
            self.last_repair_succeeded = True
            return materialize_reflection_advice(context=context, draft=repaired)

        self.last_full_retry_count = 1
        retry_draft = await self._reflect_live(context=context, prompt_cache_key=prompt_cache_key)
        retry_reason = validate_reflection_draft(retry_draft)
        if retry_reason is not None:
            raise ValueError(retry_reason)
        return materialize_reflection_advice(context=context, draft=retry_draft)
```

- [ ] **Step 5: Add reflection model repair helper**

Add to `src/seektalent/repair.py`:

```python
async def repair_reflection_draft(
    *,
    settings: AppSettings,
    prompt: LoadedPrompt,
    context: ReflectionContext,
    draft: ReflectionAdviceDraft,
    reason: str,
) -> ReflectionAdviceDraft:
    user_prompt = "\n\n".join(
        [
            "Repair this ReflectionAdviceDraft so it passes the stated validation reason.",
            "Return the complete corrected ReflectionAdviceDraft. Preserve keyword and filter advice.",
            f"VALIDATION REASON\n{reason}",
            json_block("REFLECTION_CONTEXT", context.model_dump(mode="json")),
            json_block("CURRENT_DRAFT", draft.model_dump(mode="json")),
        ]
    )
    return await _repair_with_model(
        settings=settings,
        output_type=ReflectionAdviceDraft,
        system_prompt=prompt.content,
        user_prompt=user_prompt,
    )
```

Ensure `ReflectionContext` is imported in `src/seektalent/repair.py`.

- [ ] **Step 6: Record reflection repair metadata in snapshots**

In reflection success/failure `_build_llm_call_snapshot(...)` calls in `src/seektalent/runtime/orchestrator.py`, add:

```python
                    validator_retry_count=self.reflection_critic.last_validator_retry_count,
                    validator_retry_reasons=self.reflection_critic.last_validator_retry_reasons,
                    repair_attempt_count=self.reflection_critic.last_repair_attempt_count,
                    repair_succeeded=self.reflection_critic.last_repair_succeeded,
                    repair_model=(
                        self.settings.structured_repair_model
                        if self.reflection_critic.last_repair_attempt_count
                        else None
                    ),
                    repair_reason=self.reflection_critic.last_repair_reason,
                    full_retry_count=self.reflection_critic.last_full_retry_count,
```

Use the existing `WorkflowRuntime` `ReflectionCritic` instance name from the current constructor when adding these fields.

- [ ] **Step 7: Run reflection tests**

Run:

```bash
uv run pytest tests/test_reflection_contract.py -q
```

Expected: all reflection tests pass.

- [ ] **Step 8: Commit**

```bash
git add src/seektalent/models.py src/seektalent/reflection/critic.py src/seektalent/repair.py src/seektalent/runtime/orchestrator.py tests/test_reflection_contract.py
git commit -m "Repair reflection semantic validation before full retry"
```

---

### Task 7: Scoring Exact Cache With Concurrency 10

**Files:**
- Modify: `src/seektalent/models.py`
- Modify: `src/seektalent/scoring/scorer.py`
- Modify: `src/seektalent/runtime/orchestrator.py`
- Test: `tests/test_scoring_cache.py`
- Test: `tests/test_evaluation.py`

- [ ] **Step 1: Write failing scoring cache tests**

Create `tests/test_scoring_cache.py`:

```python
from pathlib import Path

import pytest

from seektalent.models import HardConstraintSlots, NormalizedResume, ScoredCandidate, ScoredCandidateDraft, ScoringContext, ScoringPolicy
from seektalent.prompting import LoadedPrompt
from seektalent.runtime.exact_llm_cache import get_cached_json, put_cached_json
from seektalent.scoring.scorer import ResumeScorer, scoring_cache_key
from seektalent.tracing import RunTracer
from tests.settings_factory import make_settings


def _scoring_context() -> ScoringContext:
    return ScoringContext(
        round_no=1,
        requirement_sheet_sha256="requirement-hash",
        scoring_policy=ScoringPolicy(
            role_title="Python Engineer",
            role_summary="Build backend systems.",
            must_have_capabilities=["Python"],
            preferred_capabilities=["retrieval"],
            exclusion_signals=[],
            hard_constraints=HardConstraintSlots(),
            scoring_rationale="Score Python backend fit first.",
        ),
        normalized_resume=NormalizedResume(
            resume_id="resume-1",
            dedup_key="resume-1",
            current_title="Python Engineer",
            current_company="Acme",
            skills=["Python"],
            completeness_score=90,
        ),
    )


def _prompt() -> LoadedPrompt:
    return LoadedPrompt(name="scoring", path=Path("scoring.md"), content="scoring prompt", sha256="prompt-hash")


def _draft() -> ScoredCandidateDraft:
    return ScoredCandidateDraft(
        fit_bucket="fit",
        overall_score=88,
        must_have_match_score=90,
        preferred_match_score=70,
        risk_score=10,
        risk_flags=[],
        reasoning_summary="Strong Python backend match.",
        matched_must_haves=["Python"],
        missing_must_haves=[],
        matched_preferences=["retrieval"],
        negative_signals=[],
    )


def _scored_candidate() -> ScoredCandidate:
    return ScoredCandidate(
        resume_id="resume-1",
        fit_bucket="fit",
        overall_score=88,
        must_have_match_score=90,
        preferred_match_score=70,
        risk_score=10,
        risk_flags=[],
        reasoning_summary="Strong Python backend match.",
        evidence=["Python", "retrieval"],
        confidence="high",
        matched_must_haves=["Python"],
        missing_must_haves=[],
        matched_preferences=["retrieval"],
        negative_signals=[],
        strengths=["Matched must-have: Python"],
        weaknesses=[],
        source_round=1,
    )


@pytest.mark.asyncio
async def test_scoring_cache_miss_calls_provider_and_stores_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = make_settings(llm_cache_dir=str(tmp_path / "cache"), scoring_max_concurrency=10)
    scorer = ResumeScorer(settings, _prompt())
    tracer = RunTracer(tmp_path / "runs")
    provider_calls = 0

    async def fake_score_one_live(*, prompt, agent):  # noqa: ANN001
        nonlocal provider_calls
        provider_calls += 1
        return _draft()

    monkeypatch.setattr(scorer, "_score_one_live", fake_score_one_live)

    scored, failures = await scorer._score_candidates_parallel(contexts=[_scoring_context()], tracer=tracer, agent=object())

    key = scoring_cache_key(settings=settings, prompt=scorer.prompt, context=_scoring_context(), user_prompt=scorer.rendered_prompt_for_cache(_scoring_context()))
    assert provider_calls == 1
    assert failures == []
    assert scored[0].resume_id == "resume-1"
    assert get_cached_json(settings, namespace="scoring", key=key) is not None
    tracer.close()


@pytest.mark.asyncio
async def test_scoring_cache_hit_skips_provider_and_writes_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = make_settings(llm_cache_dir=str(tmp_path / "cache"), scoring_max_concurrency=10)
    scorer = ResumeScorer(settings, _prompt())
    context = _scoring_context()
    tracer = RunTracer(tmp_path / "runs")
    user_prompt = scorer.rendered_prompt_for_cache(context)
    key = scoring_cache_key(settings=settings, prompt=scorer.prompt, context=context, user_prompt=user_prompt)
    put_cached_json(settings, namespace="scoring", key=key, payload=_scored_candidate().model_dump(mode="json"))

    async def fail_if_provider_called(*, prompt, agent):  # noqa: ANN001
        raise AssertionError("provider should not be called on exact scoring cache hit")

    monkeypatch.setattr(scorer, "_score_one_live", fail_if_provider_called)

    scored, failures = await scorer._score_candidates_parallel(contexts=[context], tracer=tracer, agent=object())
    scoring_calls = (tracer.run_dir / "rounds" / "round_01" / "scoring_calls.jsonl").read_text(encoding="utf-8")

    assert failures == []
    assert scored[0].resume_id == "resume-1"
    assert f'"cache_key": "{key}"' in scoring_calls
    assert '"cache_hit": true' in scoring_calls
    tracer.close()
```

- [ ] **Step 2: Run tests and confirm they fail**

Run:

```bash
uv run pytest tests/test_scoring_cache.py -q
```

Expected: missing `requirement_sheet_sha256`, missing `scoring_cache_key`, and no cache behavior.

- [ ] **Step 3: Add requirement sheet hash to scoring context**

Modify `src/seektalent/models.py`:

```python
class ScoringContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    round_no: int
    requirement_sheet_sha256: str = ""
    scoring_policy: ScoringPolicy
    normalized_resume: NormalizedResume
```

Modify runtime construction of `ScoringContext` in `src/seektalent/runtime/orchestrator.py` so each context includes:

```python
requirement_sheet_sha256=json_sha256(run_state.requirement_sheet.model_dump(mode="json")),
```

- [ ] **Step 4: Add scoring cache key and prompt test seam**

Modify `src/seektalent/scoring/scorer.py` imports:

```python
from time import perf_counter

from seektalent.runtime.exact_llm_cache import get_cached_json, put_cached_json, stable_cache_key
```

Add:

```python
SCORING_CACHE_SCHEMA_VERSION = "scored_candidate.v1"


def scoring_cache_key(
    *,
    settings: AppSettings,
    prompt: LoadedPrompt,
    context: ScoringContext,
    user_prompt: str,
) -> str:
    return stable_cache_key(
        {
            "schema": SCORING_CACHE_SCHEMA_VERSION,
            "model_id": settings.scoring_model,
            "prompt_hash": prompt.sha256,
            "scoring_policy_hash": json_sha256(context.scoring_policy.model_dump(mode="json")),
            "requirement_sheet_hash": context.requirement_sheet_sha256,
            "normalized_resume_hash": json_sha256(context.normalized_resume.model_dump(mode="json")),
            "input_payload_hash": text_sha256(user_prompt),
        }
    )
```

Add a small method for tests:

```python
    def rendered_prompt_for_cache(self, context: ScoringContext) -> str:
        return render_scoring_prompt(context)
```

- [ ] **Step 5: Integrate scoring cache in `_score_one`**

Inside `_score_one`, after `user_prompt = render_scoring_prompt(context)` and before provider call:

```python
        cache_key = scoring_cache_key(
            settings=self.settings,
            prompt=self.prompt,
            context=context,
            user_prompt=user_prompt,
        )
        cache_started = perf_counter()
        cached = get_cached_json(self.settings, namespace="scoring", key=cache_key)
        cache_lookup_latency_ms = max(0, int((perf_counter() - cache_started) * 1000))
        if cached is not None:
            result = ScoredCandidate.model_validate(cached)
            tracer.append_jsonl(
                f"rounds/round_{context.round_no:02d}/scoring_calls.jsonl",
                LLMCallSnapshot(
                    stage="scoring",
                    call_id=call_id,
                    round_no=context.round_no,
                    resume_id=candidate.resume_id,
                    branch_id=branch_id,
                    model_id=self.settings.scoring_model,
                    provider=model_provider(self.settings.scoring_model),
                    prompt_hash=self.prompt.sha256,
                    prompt_snapshot_path="prompt_snapshots/scoring.md",
                    retries=0,
                    output_retries=2,
                    started_at=started_at_iso,
                    latency_ms=cache_lookup_latency_ms,
                    status="succeeded",
                    input_artifact_refs=[
                        f"rounds/round_{context.round_no:02d}/scoring_input_refs.jsonl",
                        f"resumes/{candidate.resume_id}.json",
                        "scoring_policy.json",
                    ],
                    output_artifact_refs=[
                        f"rounds/round_{context.round_no:02d}/scorecards.jsonl#resume_id={candidate.resume_id}"
                    ],
                    input_payload_sha256=text_sha256(user_prompt),
                    structured_output_sha256=json_sha256(result.model_dump(mode="json")),
                    prompt_chars=len(self.prompt.content),
                    input_payload_chars=text_char_count(user_prompt),
                    output_chars=json_char_count(result.model_dump(mode="json")),
                    input_summary=(
                        f"round={context.round_no}; resume_id={candidate.resume_id}; "
                        f"summary={candidate.compact_summary()}"
                    ),
                    output_summary=(
                        f"fit_bucket={result.fit_bucket}; score={result.overall_score}; "
                        f"risk={result.risk_score}"
                    ),
                    cache_hit=True,
                    cache_key=cache_key,
                    cache_lookup_latency_ms=cache_lookup_latency_ms,
                ),
            )
            tracer.emit(
                "score_branch_completed",
                round_no=context.round_no,
                resume_id=candidate.resume_id,
                branch_id=branch_id,
                model=self.settings.scoring_model,
                call_id=call_id,
                status="succeeded",
                latency_ms=cache_lookup_latency_ms,
                summary=result.reasoning_summary,
                artifact_paths=artifact_paths,
                payload={"cache_hit": True},
            )
            return result, None
```

After live result materialization succeeds, store it:

```python
            put_cached_json(
                self.settings,
                namespace="scoring",
                key=cache_key,
                payload=result.model_dump(mode="json"),
            )
```

Also pass `cache_hit=False`, `cache_key=cache_key`, and `cache_lookup_latency_ms=cache_lookup_latency_ms` into the existing live success and failure snapshots.

- [ ] **Step 6: Pass prompt-cache key to scoring agent**

Update `_build_agent` to accept `prompt_cache_key`:

```python
    def _build_agent(self, *, prompt_cache_key: str | None = None) -> Agent[None, ScoredCandidateDraft]:
        model = build_model(self.settings.scoring_model)
        return cast(Agent[None, ScoredCandidateDraft], Agent(
            model=model,
            output_type=build_output_spec(self.settings.scoring_model, model, ScoredCandidateDraft),
            system_prompt=self.prompt.content,
            model_settings=build_model_settings(
                self.settings,
                self.settings.scoring_model,
                prompt_cache_key=prompt_cache_key,
            ),
            retries=0,
            output_retries=2,
        ))
```

In `score_candidates_parallel`, compute one key for the batch:

```python
        batch_hash = json_sha256(
            {
                "model_id": self.settings.scoring_model,
                "prompt_hash": self.prompt.sha256,
                "policy_hashes": [
                    json_sha256(context.scoring_policy.model_dump(mode="json"))
                    for context in contexts
                ],
                "requirement_sheet_hashes": [context.requirement_sheet_sha256 for context in contexts],
            }
        )
        agent = self._build_agent(prompt_cache_key=f"scoring:{self.settings.scoring_model}:{batch_hash}")
```

- [ ] **Step 7: Run scoring tests and concurrency-related tests**

Run:

```bash
uv run pytest tests/test_scoring_cache.py tests/test_evaluation.py::test_evaluation_uses_judge_and_scoring_concurrency_overrides -q
```

Expected: selected tests pass. If `tests/test_evaluation.py` uses a different test name, run `uv run pytest tests/test_evaluation.py -q`.

- [ ] **Step 8: Commit**

```bash
git add src/seektalent/models.py src/seektalent/scoring/scorer.py src/seektalent/runtime/orchestrator.py tests/test_scoring_cache.py tests/test_evaluation.py
git commit -m "Cache exact scoring results"
```

---

### Task 8: Audit Cache, Repair, And Full Retry Metadata

**Files:**
- Modify: `tools/audit_run_latency.py`
- Modify: `src/seektalent/runtime/orchestrator.py`
- Test: `tests/test_run_latency_audit_tool.py`
- Test: `tests/test_runtime_audit.py`

- [ ] **Step 1: Write failing audit tests**

Add this test to `tests/test_run_latency_audit_tool.py`:

```python
def test_audit_run_dir_reads_cache_and_repair_metadata(tmp_path: Path) -> None:
    run_dir = tmp_path / "20260423_120000_cache"
    _write_jsonl(
        run_dir / "events.jsonl",
        [
            {"timestamp": "2026-04-23T12:00:00+08:00", "event_type": "run_started"},
            {"timestamp": "2026-04-23T12:01:00+08:00", "event_type": "run_finished"},
        ],
    )
    _write_json(
        run_dir / "requirements_call.json",
        {
            "stage": "requirements",
            "call_id": "requirements",
            "latency_ms": 4,
            "cache_hit": True,
            "cache_lookup_latency_ms": 4,
            "repair_attempt_count": 0,
            "repair_succeeded": False,
            "full_retry_count": 0,
        },
    )
    _write_json(
        run_dir / "rounds" / "round_01" / "controller_call.json",
        {
            "stage": "controller",
            "call_id": "controller-r01",
            "latency_ms": 90000,
            "validator_retry_count": 1,
            "validator_retry_reasons": ["response_to_reflection is required when previous_reflection exists."],
            "repair_attempt_count": 1,
            "repair_succeeded": True,
            "repair_model": "openai-chat:qwen3.5-flash",
            "repair_reason": "response_to_reflection is required when previous_reflection exists.",
            "full_retry_count": 0,
        },
    )
    _write_jsonl(
        run_dir / "rounds" / "round_01" / "scoring_calls.jsonl",
        [
            {
                "stage": "scoring",
                "call_id": "scoring-r01-a",
                "latency_ms": 2,
                "cache_hit": True,
                "cache_lookup_latency_ms": 2,
                "repair_attempt_count": 0,
                "full_retry_count": 0,
            }
        ],
    )

    summary = audit_run_dir(run_dir)

    assert summary["llm_calls"]["requirements"]["cache_hits"] == 1
    assert summary["llm_calls"]["scoring"]["cache_hits"] == 1
    assert summary["llm_calls"]["controller"]["repair_attempt_count"] == 1
    assert summary["llm_calls"]["controller"]["repair_succeeded_count"] == 1
    assert summary["llm_calls"]["controller"]["full_retry_count"] == 0
```

Add this assertion to the runtime schema pressure test or create one in `tests/test_runtime_audit.py`:

```python
def test_llm_schema_pressure_includes_cache_repair_and_full_retry(tmp_path: Path) -> None:
    runtime = WorkflowRuntime(make_settings(runs_dir=str(tmp_path), mock_cts=True))
    snapshot = {
        "stage": "controller",
        "call_id": "controller-r01",
        "output_retries": 2,
        "validator_retry_count": 1,
        "repair_attempt_count": 1,
        "repair_succeeded": True,
        "full_retry_count": 0,
        "cache_hit": False,
        "cache_lookup_latency_ms": 3,
        "prompt_chars": 100,
        "input_payload_chars": 200,
        "output_chars": 50,
    }

    item = runtime._llm_schema_pressure_item(snapshot)

    assert item["cache_hit"] is False
    assert item["cache_lookup_latency_ms"] == 3
    assert item["repair_attempt_count"] == 1
    assert item["repair_succeeded"] is True
    assert item["full_retry_count"] == 0
```

- [ ] **Step 2: Run tests and confirm they fail**

Run:

```bash
uv run pytest tests/test_run_latency_audit_tool.py::test_audit_run_dir_reads_cache_and_repair_metadata tests/test_runtime_audit.py::test_llm_schema_pressure_includes_cache_repair_and_full_retry -q
```

Expected: missing summary fields.

- [ ] **Step 3: Extend audit aggregation**

Modify `tools/audit_run_latency.py` wherever per-stage LLM call summaries are aggregated. Add these counters with default zero:

```python
stage_summary["cache_hits"] += int(bool(snapshot.get("cache_hit", False)))
stage_summary["cache_lookup_latency_ms"] += int(snapshot.get("cache_lookup_latency_ms") or 0)
stage_summary["repair_attempt_count"] += int(snapshot.get("repair_attempt_count") or 0)
stage_summary["repair_succeeded_count"] += int(bool(snapshot.get("repair_succeeded", False)))
stage_summary["full_retry_count"] += int(snapshot.get("full_retry_count") or 0)
```

If the tool uses a factory function for stage summaries, add fields:

```python
{
    "count": 0,
    "total_latency_ms": 0,
    "max_latency_ms": 0,
    "retry_count": 0,
    "retry_reasons": [],
    "cache_hits": 0,
    "cache_lookup_latency_ms": 0,
    "repair_attempt_count": 0,
    "repair_succeeded_count": 0,
    "full_retry_count": 0,
}
```

- [ ] **Step 4: Extend runtime schema pressure items**

Modify `_llm_schema_pressure_item` in `src/seektalent/runtime/orchestrator.py`:

```python
    def _llm_schema_pressure_item(self, snapshot: dict[str, object]) -> dict[str, object]:
        return {
            "stage": snapshot["stage"],
            "call_id": snapshot["call_id"],
            "output_retries": snapshot["output_retries"],
            "validator_retry_count": snapshot.get("validator_retry_count", 0),
            "validator_retry_reasons": snapshot.get("validator_retry_reasons", []),
            "repair_attempt_count": snapshot.get("repair_attempt_count", 0),
            "repair_succeeded": snapshot.get("repair_succeeded", False),
            "repair_reason": snapshot.get("repair_reason"),
            "full_retry_count": snapshot.get("full_retry_count", 0),
            "cache_hit": snapshot.get("cache_hit", False),
            "cache_lookup_latency_ms": snapshot.get("cache_lookup_latency_ms"),
            "prompt_cache_key": snapshot.get("prompt_cache_key"),
            "prompt_cache_retention": snapshot.get("prompt_cache_retention"),
            "cached_input_tokens": snapshot.get("cached_input_tokens"),
            "prompt_chars": snapshot.get("prompt_chars", 0),
            "input_payload_chars": snapshot.get("input_payload_chars", 0),
            "output_chars": snapshot.get("output_chars", 0),
            "input_payload_sha256": snapshot.get("input_payload_sha256"),
            "structured_output_sha256": snapshot.get("structured_output_sha256"),
        }
```

- [ ] **Step 5: Run audit tests**

Run:

```bash
uv run pytest tests/test_run_latency_audit_tool.py tests/test_runtime_audit.py::test_llm_schema_pressure_includes_cache_repair_and_full_retry -q
```

Expected: selected tests pass.

- [ ] **Step 6: Commit**

```bash
git add tools/audit_run_latency.py src/seektalent/runtime/orchestrator.py tests/test_run_latency_audit_tool.py tests/test_runtime_audit.py
git commit -m "Report cache and repair latency metadata"
```

---

### Task 9: End-To-End Verification

**Files:**
- No new implementation files.
- Verify: full repository tests and latency audit smoke.

- [ ] **Step 1: Run full test suite**

Run:

```bash
uv run pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run audit smoke on existing runs if present**

Run:

```bash
uv run python tools/audit_run_latency.py --limit 1 runs
```

Expected: command completes. If `runs/` has no run directories, expected output should state that no runs were found.

- [ ] **Step 3: Inspect behavior-strategy diff**

Run:

```bash
git diff -- src/seektalent/runtime/orchestrator.py src/seektalent/controller/react_controller.py src/seektalent/reflection/critic.py src/seektalent/scoring/scorer.py
```

Verify manually:

- Retrieval loop still uses `target_new = TOP_K`.
- No pre-score candidate filtering was added.
- Ranking/finalizer behavior is unchanged.
- Controller/reflection/requirements thinking flags remain enabled by default.
- Full thinking retry happens only after repair fails for semantic validation.

- [ ] **Step 4: Run focused test set for latency engineering**

Run:

```bash
uv run pytest tests/test_llm_provider_config.py tests/test_exact_llm_cache.py tests/test_requirement_extraction.py tests/test_controller_contract.py tests/test_reflection_contract.py tests/test_scoring_cache.py tests/test_run_latency_audit_tool.py -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit verification-only adjustments**

When Step 1-4 required small test or implementation corrections, commit them:

```bash
git add src tests tools
git commit -m "Stabilize latency engineering tests"
```

When there were no corrections, do not create an empty commit.

---

## Self-Review Checklist

- Requirements Thinking: Task 1 adds setting, Task 4 passes it into requirements model settings.
- Scoring concurrency 10: Task 1 changes default and keeps override validation.
- Exact scoring cache: Task 7 keys by model, prompt, policy, requirement hash, resume hash, schema version, and rendered prompt hash.
- Exact requirements cache: Task 4 keys by model, prompt, job title, JD, notes, and schema version.
- Controller semantic retry: Task 5 removes automatic semantic `ModelRetry` and repairs before full retry.
- Requirements semantic retry: Task 4 repairs normalization failures before failing or retrying.
- Reflection semantic retry: Task 6 moves stop-field semantic validation out of `ReflectionAdviceDraft` parsing and repairs before full retry.
- Prompt-cache probe knobs: Task 2 adds request keys and retention; later tasks pass stage keys.
- Artifact observability: Tasks 1, 4, 5, 6, 7, and 8 record cache/repair/full-retry/prompt-cache metadata.
- Behavior constraints: No task changes retrieval target, stop policy, candidate selection, scoring rubric, ranking, or finalizer semantics.
