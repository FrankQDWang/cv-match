# Text LLM Dual-Protocol Support And DeepSeek V4 Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace provider-prefixed text-model configuration with one canonical dual-protocol text-LLM surface, move `requirements/controller/reflection/judge` to `deepseek-v4-pro`, move `scoring/finalize/structured_repair` to `deepseek-v4-flash`, and make benchmark/provider failures easier to diagnose and trace.

**Architecture:** Hard-cut the old config surface first, then introduce explicit protocol-family + endpoint-kind + endpoint-region runtime resolution in the existing LLM boundary, then migrate each text stage and judge onto that canonical surface, and finally tighten diagnostics plus benchmark child-run linkage so even preflight failures remain debuggable. Keep retrieval strategy unchanged, keep candidate-feedback phrase behavior unchanged, and do not preserve the old `openai-chat:` / `openai-responses:` compatibility layer.

**Tech Stack:** Python 3.12, Pydantic/Pydantic Settings, `pydantic_ai`, existing SeekTalent runtime split modules, ArtifactStore/ArtifactResolver, pytest, benchmark CLI.

---

## File Map

### Modify

- Modify: `src/seektalent/config.py`
  Purpose: Replace the old stage-model config keys with canonical protocol-family / endpoint / `*_model_id` settings, add raw env/config migration scanning, and remove judge-specific endpoint overrides.

- Modify: `pyproject.toml`
- Modify: `uv.lock`
  Purpose: Add the Anthropic provider dependency needed by the canonical dual-protocol boundary and keep the lockfile aligned with the new runtime imports.

- Modify: `src/seektalent/default.env`
- Modify: `.env.example`
  Purpose: Make checked-in defaults use the new canonical keys and DeepSeek V4 model defaults.

- Modify: `src/seektalent/llm.py`
  Purpose: Turn the existing LLM adapter into an explicit dual-protocol boundary that supports OpenAI Chat Completions-compatible and Anthropic Messages-compatible calls, stage policy resolution, reasoning policy resolution, capability preflight, and structured-output mode selection.

- Modify: `src/seektalent/requirements/extractor.py`
- Modify: `src/seektalent/controller/react_controller.py`
- Modify: `src/seektalent/reflection/critic.py`
- Modify: `src/seektalent/scoring/scorer.py`
- Modify: `src/seektalent/finalize/finalizer.py`
- Modify: `src/seektalent/repair.py`
- Modify: `src/seektalent/candidate_feedback/model_steps.py`
  Purpose: Route every active text-LLM stage through the new canonical stage/policy resolution helpers without changing business behavior.

- Modify: `src/seektalent/evaluation.py`
  Purpose: Move judge onto the same Bailian text-provider surface, remove `judge_openai_*` handling, and record judge lineage using the new canonical runtime metadata.

- Modify: `src/seektalent/runtime/orchestrator.py`
- Modify: `src/seektalent/runtime/runtime_diagnostics.py`
- Modify: `src/seektalent/runtime/runtime_reports.py`
- Modify: `src/seektalent/tracing.py`
- Modify: `src/seektalent/models.py`
  Purpose: Record canonical stage metadata, protocol family, reasoning mode, structured-output mode, and finer-grained failure taxonomy in run config, call artifacts, replay/export rows, and trace events.

- Modify: `src/seektalent/api.py`
- Modify: `src/seektalent/cli.py`
  Purpose: Precreate benchmark child runs before per-case settings/provider preflight, ensure failed rows always get run linkage, and surface migration/capability failures with explicit benchmark-facing metadata.

- Modify: `src/seektalent/artifacts/store.py`
  Purpose: Add the minimal child-session helper needed to attach benchmark case runs to the benchmark artifact root without creating dummy standalone roots.

- Modify: `tests/settings_factory.py`
- Modify: `tests/test_llm_provider_config.py`
- Modify: `tests/test_candidate_feedback.py`
- Modify: `tests/test_runtime_audit.py`
- Modify: `tests/test_evaluation.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_api.py`
- Modify: `tests/test_resume_quality.py`
- Modify: `tests/test_jd_text_baseline.py`
- Modify: `tests/test_openclaw_baseline.py`
- Modify: `tests/test_claude_code_baseline.py`
  Purpose: Rewrite config and provider-boundary expectations around the canonical surface and update benchmark/evaluation assertions.

- Modify: `docs/outputs.md`
  Purpose: Document the new runtime metadata, benchmark failure linkage, and dual-protocol runtime surface.

### Notes

- Do **not** change candidate-feedback phrase extraction behavior or PRF rollout defaults.
- Do **not** change stopping/exhaustion behavior.
- Do **not** preserve old prefixed model strings as a compatibility path.
- Do **not** mix in the current local benchmark-debug edits in `src/seektalent/runtime/orchestrator.py` and `tests/test_runtime_state_flow.py` until the implementation starts from a fresh worktree.

## Task 0: Clean Baseline And Fresh Worktree

**Files:**
- Modify: none
- Verify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4`

- [ ] **Step 1: Inventory the current repository state**

Run:

```bash
git status --short
git branch --list
git worktree list
```

Expected:

- the only dirty files in the main worktree are the known local benchmark-debug edits and untracked local tooling directories;
- the completed feature branch and stale worktrees are visible before implementation starts.

- [ ] **Step 2: Merge or otherwise resolve the completed branch before starting this feature**

Run:

```bash
git log --oneline --decorate --max-count=8
git branch --list 'codex/*' 'claude/*'
```

Expected:

- the engineer can identify which completed branch must be merged or explicitly retired before touching text-LLM code;
- if a branch still contains required work, stop and integrate it first instead of stacking this feature on an ambiguous baseline.

- [ ] **Step 3: Start implementation from a fresh worktree after the baseline is clean**

Run:

```bash
git status --short
git worktree add .worktrees/text-llm-dual-protocol -b codex/text-llm-dual-protocol main
git -C .worktrees/text-llm-dual-protocol status --short
```

Expected:

- the new worktree starts from a clean `main`;
- implementation happens in `.worktrees/text-llm-dual-protocol`, not in the dirty main worktree.

- [ ] **Step 4: Change into the fresh worktree and keep every later command scoped there**

Run:

```bash
cd .worktrees/text-llm-dual-protocol
pwd
git status --short
```

Expected:

- every later file path in this plan is interpreted relative to `.worktrees/text-llm-dual-protocol`;
- no later `pytest`, `git add`, or file edit in this plan touches the dirty main worktree.

## Task 1: Hard-Cut Config Surface And Raw Migration Scanner

**Files:**
- Modify: `src/seektalent/config.py`
- Modify: `src/seektalent/default.env`
- Modify: `.env.example`
- Modify: `tests/settings_factory.py`
- Modify: `tests/test_llm_provider_config.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests for the canonical settings surface and raw migration scanner**

```python
# tests/test_llm_provider_config.py
from pathlib import Path

import pytest

from seektalent.config import AppSettings, TextLLMConfigMigrationError
from tests.settings_factory import make_settings


def test_canonical_text_llm_defaults_use_dual_protocol_surface() -> None:
    settings = make_settings()

    assert settings.text_llm_protocol_family == "anthropic_messages_compatible"
    assert settings.text_llm_provider_label == "bailian"
    assert settings.text_llm_endpoint_kind == "bailian_anthropic_messages"
    assert settings.text_llm_endpoint_region == "beijing"
    assert settings.requirements_model_id == "deepseek-v4-pro"
    assert settings.controller_model_id == "deepseek-v4-pro"
    assert settings.reflection_model_id == "deepseek-v4-pro"
    assert settings.judge_model_id == "deepseek-v4-pro"
    assert settings.scoring_model_id == "deepseek-v4-flash"
    assert settings.finalize_model_id == "deepseek-v4-flash"
    assert settings.structured_repair_model_id == "deepseek-v4-flash"


def test_legacy_stage_key_in_dotenv_fails_with_migration_error(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SEEKTALENT_REQUIREMENTS_MODEL=openai-chat:deepseek-v3.2\n",
        encoding="utf-8",
    )

    with pytest.raises(TextLLMConfigMigrationError, match="legacy text-llm config"):
        AppSettings(_env_file=env_file)


def test_prefixed_value_on_new_model_id_key_fails_with_migration_error(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SEEKTALENT_REQUIREMENTS_MODEL_ID=openai-responses:gpt-5.4-mini\n",
        encoding="utf-8",
    )

    with pytest.raises(TextLLMConfigMigrationError, match="provider-prefixed model string"):
        AppSettings(_env_file=env_file)


def test_candidate_feedback_model_key_is_hard_cut_if_present(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SEEKTALENT_CANDIDATE_FEEDBACK_MODEL=openai-chat:qwen3.5-flash\n",
        encoding="utf-8",
    )

    with pytest.raises(TextLLMConfigMigrationError, match="legacy text-llm config"):
        AppSettings(_env_file=env_file)


def test_stage_model_id_init_kwarg_with_prefixed_value_fails_fast() -> None:
    with pytest.raises(TextLLMConfigMigrationError, match="provider-prefixed model string"):
        AppSettings(requirements_model_id="openai-chat:deepseek-v3.2")


def test_checked_in_env_templates_use_new_keys() -> None:
    for path in [
        Path(".env.example"),
        Path("src/seektalent/default.env"),
    ]:
        text = path.read_text(encoding="utf-8")
        assert "SEEKTALENT_TEXT_LLM_PROTOCOL_FAMILY=" in text
        assert "SEEKTALENT_REQUIREMENTS_MODEL_ID=deepseek-v4-pro" in text
        assert "SEEKTALENT_JUDGE_MODEL_ID=deepseek-v4-pro" in text
        assert "SEEKTALENT_REQUIREMENTS_MODEL=" not in text
        assert "SEEKTALENT_JUDGE_OPENAI_BASE_URL=" not in text
```

```python
# tests/test_cli.py
from seektalent.cli import OPTIONAL_RUNTIME_ENV_VARS


def test_optional_runtime_env_vars_use_new_text_llm_keys() -> None:
    assert "SEEKTALENT_TEXT_LLM_PROTOCOL_FAMILY" in OPTIONAL_RUNTIME_ENV_VARS
    assert "SEEKTALENT_REQUIREMENTS_MODEL_ID" in OPTIONAL_RUNTIME_ENV_VARS
    assert "SEEKTALENT_JUDGE_MODEL_ID" in OPTIONAL_RUNTIME_ENV_VARS
    assert "SEEKTALENT_REQUIREMENTS_MODEL" not in OPTIONAL_RUNTIME_ENV_VARS
    assert "SEEKTALENT_JUDGE_OPENAI_BASE_URL" not in OPTIONAL_RUNTIME_ENV_VARS
```

- [ ] **Step 2: Run the targeted tests and confirm they fail on the old config surface**

Run:

```bash
uv run pytest -q \
  tests/test_llm_provider_config.py \
  tests/test_cli.py
```

Expected: FAIL because `AppSettings` still exposes `requirements_model`, `judge_openai_base_url`, `candidate_feedback_model`, and the checked-in env templates still use prefixed model strings.

- [ ] **Step 3: Replace the old settings with the new canonical surface and raw scanner**

```python
# src/seektalent/config.py
TextLLMProtocolFamily = Literal[
    "openai_chat_completions_compatible",
    "anthropic_messages_compatible",
]
TextLLMEndpointKind = Literal[
    "bailian_openai_chat_completions",
    "bailian_anthropic_messages",
]
TextLLMEndpointRegion = Literal["beijing", "singapore"]


class TextLLMConfigMigrationError(ValueError):
    """Raised when removed text-LLM keys or prefixed values are still present."""

LEGACY_TEXT_LLM_KEYS = {
    "SEEKTALENT_REQUIREMENTS_MODEL",
    "SEEKTALENT_CONTROLLER_MODEL",
    "SEEKTALENT_SCORING_MODEL",
    "SEEKTALENT_FINALIZE_MODEL",
    "SEEKTALENT_REFLECTION_MODEL",
    "SEEKTALENT_STRUCTURED_REPAIR_MODEL",
    "SEEKTALENT_JUDGE_MODEL",
    "SEEKTALENT_TUI_SUMMARY_MODEL",
    "SEEKTALENT_CANDIDATE_FEEDBACK_MODEL",
    "SEEKTALENT_JUDGE_OPENAI_BASE_URL",
    "SEEKTALENT_JUDGE_OPENAI_API_KEY",
}
LEGACY_TEXT_LLM_PREFIXES = ("openai-chat:", "openai-responses:", "anthropic:")


def _read_env_kv_pairs(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip("'").strip('"')
    return data


def _legacy_text_llm_error(reasons: list[str]) -> ValueError:
    joined = "; ".join(reasons)
    return ValueError(
        "legacy text-llm config detected: "
        f"{joined}. Replace old provider-prefixed stage settings with "
        "SEEKTALENT_TEXT_LLM_PROTOCOL_FAMILY, SEEKTALENT_TEXT_LLM_ENDPOINT_KIND, "
        "SEEKTALENT_TEXT_LLM_ENDPOINT_REGION, and bare *_MODEL_ID values."
    )


def _scan_legacy_text_llm_inputs(
    *,
    env_file: str | Path | None,
    init_data: Mapping[str, object],
    include_default_env_file: bool,
) -> None:
    reasons: list[str] = []
    raw_sources: list[dict[str, str]] = [dict(os.environ)]
    if include_default_env_file:
        raw_sources.append(_read_env_kv_pairs(Path(".env")))
    if env_file is not None:
        raw_sources.append(_read_env_kv_pairs(Path(env_file)))
    raw_sources.append({str(key): str(value) for key, value in init_data.items() if value is not None})
    for source in raw_sources:
        for key in sorted(LEGACY_TEXT_LLM_KEYS):
            if key in source:
                reasons.append(f"deprecated key {key}")
        for key, value in source.items():
            if key.endswith("_MODEL_ID") and value.startswith(LEGACY_TEXT_LLM_PREFIXES):
                reasons.append(f"{key} uses provider-prefixed model string {value!r}")
    if reasons:
        raise TextLLMConfigMigrationError(str(_legacy_text_llm_error(reasons)))


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SEEKTALENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self, **data: Any) -> None:
        env_file = data.get("_env_file", self.model_config.get("env_file"))
        _scan_legacy_text_llm_inputs(
            env_file=env_file,
            init_data=data,
            include_default_env_file=True,
        )
        super().__init__(**data)

    text_llm_protocol_family: TextLLMProtocolFamily = "anthropic_messages_compatible"
    text_llm_provider_label: str = "bailian"
    text_llm_endpoint_kind: TextLLMEndpointKind = "bailian_anthropic_messages"
    text_llm_endpoint_region: TextLLMEndpointRegion = "beijing"
    text_llm_base_url_override: str | None = None
    text_llm_api_key: str | None = None

    requirements_model_id: str = "deepseek-v4-pro"
    controller_model_id: str = "deepseek-v4-pro"
    scoring_model_id: str = "deepseek-v4-flash"
    finalize_model_id: str = "deepseek-v4-flash"
    reflection_model_id: str = "deepseek-v4-pro"
    structured_repair_model_id: str = "deepseek-v4-flash"
    judge_model_id: str = "deepseek-v4-pro"
    tui_summary_model_id: str | None = None
    candidate_feedback_model_id: str = "qwen3.5-flash"
```

```dotenv
# src/seektalent/default.env
SEEKTALENT_TEXT_LLM_PROTOCOL_FAMILY=anthropic_messages_compatible
SEEKTALENT_TEXT_LLM_PROVIDER_LABEL=bailian
SEEKTALENT_TEXT_LLM_ENDPOINT_KIND=bailian_anthropic_messages
SEEKTALENT_TEXT_LLM_ENDPOINT_REGION=beijing
SEEKTALENT_REQUIREMENTS_MODEL_ID=deepseek-v4-pro
SEEKTALENT_CONTROLLER_MODEL_ID=deepseek-v4-pro
SEEKTALENT_SCORING_MODEL_ID=deepseek-v4-flash
SEEKTALENT_FINALIZE_MODEL_ID=deepseek-v4-flash
SEEKTALENT_REFLECTION_MODEL_ID=deepseek-v4-pro
SEEKTALENT_STRUCTURED_REPAIR_MODEL_ID=deepseek-v4-flash
SEEKTALENT_JUDGE_MODEL_ID=deepseek-v4-pro
```

- [ ] **Step 4: Re-run the config tests until the hard-cut surface passes**

Run:

```bash
uv run pytest -q \
  tests/test_llm_provider_config.py \
  tests/test_cli.py
```

Expected: PASS, with failures now reporting a clear migration error when old keys or prefixed values are present.

- [ ] **Step 5: Commit the config migration boundary**

```bash
git add \
  pyproject.toml \
  uv.lock \
  src/seektalent/config.py \
  src/seektalent/default.env \
  .env.example \
  tests/settings_factory.py \
  tests/test_llm_provider_config.py \
  tests/test_cli.py
git commit -m "feat: hard-cut canonical text llm config surface"
```

## Task 2: Dual-Protocol Provider Boundary, Endpoint Resolution, Capability Matrix, And Structured Output Policy

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `src/seektalent/llm.py`
- Modify: `tests/test_llm_provider_config.py`

- [ ] **Step 1: Write failing tests for protocol-family precision, region-gated preflight, and structured-output policy**

```python
# tests/test_llm_provider_config.py
import pytest
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel

from seektalent.llm import (
    build_model,
    build_model_settings,
    build_provider_request_policy,
    preflight_models,
    resolve_text_llm_base_url,
    resolve_stage_model_config,
    resolve_structured_output_mode,
)
from tests.settings_factory import make_settings


def test_openai_protocol_family_means_chat_completions_not_responses() -> None:
    settings = make_settings(
        text_llm_protocol_family="openai_chat_completions_compatible",
        text_llm_endpoint_kind="bailian_openai_chat_completions",
        text_llm_endpoint_region="beijing",
    )

    stage = resolve_stage_model_config(settings, stage="requirements")

    assert stage.protocol_family == "openai_chat_completions_compatible"
    assert stage.endpoint_kind == "bailian_openai_chat_completions"
    assert stage.model_id == "deepseek-v4-pro"


def test_bailian_anthropic_deepseek_v4_requires_beijing_region() -> None:
    settings = make_settings(
        text_llm_protocol_family="anthropic_messages_compatible",
        text_llm_endpoint_kind="bailian_anthropic_messages",
        text_llm_endpoint_region="singapore",
    )

    with pytest.raises(ValueError, match="beijing"):
        preflight_models(settings)


def test_bailian_openai_chat_base_url_resolves_for_beijing() -> None:
    settings = make_settings(
        text_llm_protocol_family="openai_chat_completions_compatible",
        text_llm_endpoint_kind="bailian_openai_chat_completions",
        text_llm_endpoint_region="beijing",
    )

    assert resolve_text_llm_base_url(settings) == "https://dashscope.aliyuncs.com/compatible-mode/v1"


def test_bailian_anthropic_base_url_resolves_for_beijing() -> None:
    settings = make_settings(
        text_llm_protocol_family="anthropic_messages_compatible",
        text_llm_endpoint_kind="bailian_anthropic_messages",
        text_llm_endpoint_region="beijing",
    )

    assert resolve_text_llm_base_url(settings) == "https://dashscope.aliyuncs.com/apps/anthropic"


def test_bailian_deepseek_v4_defaults_to_prompted_json_mode() -> None:
    settings = make_settings()

    stage = resolve_stage_model_config(settings, stage="controller")

    assert resolve_structured_output_mode(stage) == "prompted_json"


def test_stage_reasoning_policy_defaults_are_explicit() -> None:
    settings = make_settings()

    requirements_stage = resolve_stage_model_config(settings, stage="requirements")
    scoring_stage = resolve_stage_model_config(settings, stage="scoring")
    judge_stage = resolve_stage_model_config(settings, stage="judge")

    assert requirements_stage.reasoning_effort == "high"
    assert requirements_stage.thinking_mode is True
    assert scoring_stage.reasoning_effort == "off"
    assert scoring_stage.thinking_mode is False
    assert judge_stage.reasoning_effort == "high"
    assert judge_stage.model_id == "deepseek-v4-pro"


def test_openai_path_builds_chat_model_not_responses_model() -> None:
    stage = resolve_stage_model_config(
        make_settings(
            text_llm_protocol_family="openai_chat_completions_compatible",
            text_llm_endpoint_kind="bailian_openai_chat_completions",
            text_llm_endpoint_region="beijing",
        ),
        stage="requirements",
    )

    model = build_model(stage)

    assert isinstance(model, OpenAIChatModel)
    assert not isinstance(model, OpenAIResponsesModel)


def test_anthropic_path_preserves_bare_model_id() -> None:
    stage = resolve_stage_model_config(make_settings(), stage="requirements")
    model = build_model(stage)

    assert getattr(model, "model_name", None) == "deepseek-v4-pro"


def test_openai_scoring_policy_disables_thinking_in_provider_request_controls() -> None:
    stage = resolve_stage_model_config(
        make_settings(
            text_llm_protocol_family="openai_chat_completions_compatible",
            text_llm_endpoint_kind="bailian_openai_chat_completions",
            text_llm_endpoint_region="beijing",
        ),
        stage="scoring",
    )

    policy = build_provider_request_policy(stage)

    assert policy.extra_body == {"enable_thinking": False}
```

- [ ] **Step 2: Run the provider-boundary tests and confirm they fail under the old `llm.py`**

Run:

```bash
uv run pytest -q tests/test_llm_provider_config.py
```

Expected: FAIL because `llm.py` still keys off `openai-chat:` / `openai-responses:` prefixes, still assumes native structured output for several paths, has no endpoint-region preflight, and cannot yet build an Anthropic-backed canonical model without reintroducing prefixed IDs.

- [ ] **Step 3: Rebuild the existing LLM boundary around explicit stage resolution**

```python
# src/seektalent/llm.py
from dataclasses import dataclass

from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.openai import OpenAIProvider

from seektalent.config import AppSettings


@dataclass(frozen=True)
class ResolvedTextModelConfig:
    stage: str
    protocol_family: str
    provider_label: str
    endpoint_kind: str
    endpoint_region: str
    base_url: str
    api_key: str | None
    model_id: str
    structured_output_mode: str
    thinking_mode: bool
    reasoning_effort: str


STAGE_MODEL_ATTR = {
    "requirements": "requirements_model_id",
    "controller": "controller_model_id",
    "scoring": "scoring_model_id",
    "finalize": "finalize_model_id",
    "reflection": "reflection_model_id",
    "structured_repair": "structured_repair_model_id",
    "judge": "judge_model_id",
    "candidate_feedback": "candidate_feedback_model_id",
}
STAGE_REASONING_POLICY = {
    "requirements": (True, "high"),
    "controller": (True, "high"),
    "reflection": (True, "high"),
    "judge": (True, "high"),
    "scoring": (False, "off"),
    "finalize": (False, "off"),
    "structured_repair": (False, "off"),
    "candidate_feedback": (False, "off"),
}


@dataclass(frozen=True)
class TextLLMCapability:
    structured_output_mode: str
    supports_thinking: bool
    supports_reasoning_effort: bool
    allowed_reasoning_efforts: frozenset[str]


TEXT_LLM_CAPABILITIES = {
    (
        "bailian",
        "openai_chat_completions_compatible",
        "bailian_openai_chat_completions",
        "beijing",
        "deepseek-v4-pro",
    ): TextLLMCapability(
        structured_output_mode="prompted_json",
        supports_thinking=True,
        supports_reasoning_effort=True,
        allowed_reasoning_efforts=frozenset({"high", "max"}),
    ),
    (
        "bailian",
        "anthropic_messages_compatible",
        "bailian_anthropic_messages",
        "beijing",
        "deepseek-v4-pro",
    ): TextLLMCapability(
        structured_output_mode="prompted_json",
        supports_thinking=True,
        supports_reasoning_effort=True,
        allowed_reasoning_efforts=frozenset({"high", "max"}),
    ),
    # Mirror deepseek-v4-flash the same way.
}


def resolve_text_llm_base_url(settings: AppSettings) -> str:
    if settings.text_llm_base_url_override:
        return settings.text_llm_base_url_override
    mapping = {
        ("openai_chat_completions_compatible", "bailian_openai_chat_completions", "beijing"): "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ("anthropic_messages_compatible", "bailian_anthropic_messages", "beijing"): "https://dashscope.aliyuncs.com/apps/anthropic",
        ("anthropic_messages_compatible", "bailian_anthropic_messages", "singapore"): "https://dashscope-intl.aliyuncs.com/apps/anthropic",
    }
    return mapping[(settings.text_llm_protocol_family, settings.text_llm_endpoint_kind, settings.text_llm_endpoint_region)]


def resolve_text_llm_api_key(settings: AppSettings) -> str | None:
    return settings.text_llm_api_key


def resolve_stage_model_config(settings: AppSettings, *, stage: str) -> ResolvedTextModelConfig:
    model_id = getattr(settings, STAGE_MODEL_ATTR[stage])
    thinking_mode, reasoning_effort = STAGE_REASONING_POLICY[stage]
    config = ResolvedTextModelConfig(
        stage=stage,
        protocol_family=settings.text_llm_protocol_family,
        provider_label=settings.text_llm_provider_label,
        endpoint_kind=settings.text_llm_endpoint_kind,
        endpoint_region=settings.text_llm_endpoint_region,
        base_url=resolve_text_llm_base_url(settings),
        api_key=resolve_text_llm_api_key(settings),
        model_id=model_id,
        structured_output_mode="prompted_json",
        thinking_mode=thinking_mode,
        reasoning_effort=reasoning_effort,
    )
    validate_protocol_endpoint_region_model_matrix(config)
    return config


def validate_protocol_endpoint_region_model_matrix(config: ResolvedTextModelConfig) -> None:
    if (
        config.protocol_family == "anthropic_messages_compatible"
        and config.provider_label == "bailian"
        and config.model_id.startswith("deepseek-v4")
        and config.endpoint_region != "beijing"
    ):
        raise ValueError(
            "Bailian Anthropic-compatible DeepSeek V4 is region-gated to the Beijing endpoint."
        )


def resolve_structured_output_mode(config: ResolvedTextModelConfig) -> str:
    capability = TEXT_LLM_CAPABILITIES.get(
        (
            config.provider_label,
            config.protocol_family,
            config.endpoint_kind,
            config.endpoint_region,
            config.model_id,
        )
    )
    if capability is None and config.provider_label == "bailian":
        return "prompted_json"
    return capability.structured_output_mode if capability is not None else "native_json_schema"


def build_model(config: ResolvedTextModelConfig) -> Model:
    if config.protocol_family == "openai_chat_completions_compatible":
        return OpenAIChatModel(
            config.model_id,
            provider=OpenAIProvider(
                base_url=config.base_url,
                api_key=config.api_key,
                http_client=_http_client(),
            ),
            settings=build_model_settings(config),
        )
    return AnthropicModel(
        config.model_id,
        provider=AnthropicProvider(
            base_url=config.base_url,
            api_key=config.api_key,
            http_client=_http_client(),
        ),
        settings=build_model_settings(config),
    )


def build_output_spec(config: ResolvedTextModelConfig, model: Model, output_type: Any) -> Any:
    if resolve_structured_output_mode(config) == "native_json_schema":
        ensure_native_structured_output(config.model_id, model)
        return NativeOutput(output_type, strict=True)
    return PromptedOutput(output_type)


def build_provider_request_policy(config: ResolvedTextModelConfig) -> ProviderRequestPolicy:
    if config.protocol_family == "openai_chat_completions_compatible":
        return ProviderRequestPolicy(
            extra_body={"enable_thinking": config.thinking_mode} | (
                {} if config.reasoning_effort == "off" else {"reasoning_effort": config.reasoning_effort}
            )
        )
    return ProviderRequestPolicy(
        extra_body={
            "thinking": {"type": "enabled" if config.thinking_mode else "disabled"},
            "reasoning_effort": None if config.reasoning_effort == "off" else config.reasoning_effort,
        }
    )


def build_model_settings(config: ResolvedTextModelConfig, *, prompt_cache_key: str | None = None) -> ModelSettings:
    policy = build_provider_request_policy(config)
    payload: dict[str, object] = {"extra_body": policy.extra_body}
    if prompt_cache_key is not None and config.protocol_family == "openai_chat_completions_compatible":
        payload["openai_prompt_cache_key"] = prompt_cache_key
    return cast(ModelSettings, payload)
```

```toml
# pyproject.toml
dependencies = [
  "pydantic-ai-slim[openai,anthropic]>=1.76.0",
]
```

- [ ] **Step 4: Re-run the provider-boundary tests**

Run:

```bash
uv run pytest -q tests/test_llm_provider_config.py
```

Expected: PASS, with the OpenAI path resolved as chat-completions-compatible, the Anthropic Bailian DeepSeek V4 path failing outside Beijing, and Bailian DeepSeek V4 defaulting to prompted JSON.

- [ ] **Step 5: Commit the protocol and capability boundary**

```bash
git add \
  pyproject.toml \
  uv.lock \
  src/seektalent/llm.py \
  tests/test_llm_provider_config.py
git commit -m "feat: add canonical dual-protocol text llm boundary"
```

## Task 3: Migrate Stage Call Sites, Judge, And Candidate-Feedback Model Surface

**Files:**
- Modify: `src/seektalent/requirements/extractor.py`
- Modify: `src/seektalent/controller/react_controller.py`
- Modify: `src/seektalent/reflection/critic.py`
- Modify: `src/seektalent/scoring/scorer.py`
- Modify: `src/seektalent/finalize/finalizer.py`
- Modify: `src/seektalent/repair.py`
- Modify: `src/seektalent/candidate_feedback/model_steps.py`
- Modify: `src/seektalent/evaluation.py`
- Modify: `src/seektalent/runtime/runtime_reports.py`
- Modify: `tests/test_candidate_feedback.py`
- Modify: `tests/test_evaluation.py`
- Modify: `tests/test_resume_quality.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write failing tests that lock the new stage routing and judge boundary**

```python
# tests/test_evaluation.py
from tests.settings_factory import make_settings


def test_judge_uses_same_canonical_text_provider_surface_as_runtime() -> None:
    settings = make_settings()

    assert settings.judge_model_id == "deepseek-v4-pro"
    assert settings.text_llm_provider_label == "bailian"
    assert settings.text_llm_protocol_family == "anthropic_messages_compatible"


def test_evaluation_outputs_record_judge_lineage() -> None:
    evaluation = _evaluation_result()
    payload = evaluation.model_dump(mode="json")

    assert payload["judge_model"] == "deepseek-v4-pro"
    assert payload["judge_protocol_family"] == "anthropic_messages_compatible"
    assert payload["judge_prompt_hash"]
```

```python
# tests/test_candidate_feedback.py
from tests.settings_factory import make_settings


def test_candidate_feedback_active_model_setting_uses_bare_model_id() -> None:
    settings = make_settings()

    assert settings.candidate_feedback_model_id == "qwen3.5-flash"
    assert not settings.candidate_feedback_model_id.startswith("openai-")


def test_candidate_feedback_stubbed_ranking_contract_is_unchanged() -> None:
    ranking = _candidate_feedback_result_with_stubbed_model()

    assert ranking.ordered_resume_ids
    assert ranking.reasoning_summary
```

```python
# tests/test_resume_quality.py
from tests.settings_factory import make_settings


def test_tui_summary_inherits_scoring_model_id_by_default() -> None:
    settings = make_settings()

    assert settings.effective_tui_summary_model_id == settings.scoring_model_id
```

- [ ] **Step 2: Run the stage-routing tests and confirm they fail**

Run:

```bash
uv run pytest -q \
  tests/test_candidate_feedback.py \
  tests/test_evaluation.py \
  tests/test_resume_quality.py
```

Expected: FAIL because stage call sites, evaluation, and candidate-feedback model settings still read the old `*_model` strings and judge still supports the special local endpoint surface.

- [ ] **Step 3: Replace per-stage string lookups with canonical stage resolution**

```python
# src/seektalent/requirements/extractor.py
stage_config = resolve_stage_model_config(self.settings, stage="requirements")
model = build_model(stage_config)
agent = Agent(
    model=model,
    output_type=build_output_spec(stage_config, model, RequirementExtractionDraft),
    system_prompt=self.prompt.content,
    model_settings=build_model_settings(stage_config, prompt_cache_key=prompt_cache_key),
    retries=0,
    output_retries=2,
)
```

```python
# src/seektalent/controller/react_controller.py
stage_config = resolve_stage_model_config(self.settings, stage="controller")
model = build_model(stage_config)
...
model_settings=build_model_settings(stage_config, prompt_cache_key=prompt_cache_key)
```

```python
# src/seektalent/repair.py
stage_config = resolve_stage_model_config(settings, stage="structured_repair")
model = build_model(stage_config)
...
model_settings=build_model_settings(stage_config)
```

```python
# src/seektalent/candidate_feedback/model_steps.py
stage_config = resolve_stage_model_config(self.settings, stage="candidate_feedback")
model = build_model(stage_config)
...
build_output_spec(stage_config, model, CandidateFeedbackRanking)
```

```python
# src/seektalent/evaluation.py
judge_config = resolve_stage_model_config(self.settings, stage="judge")
model = build_model(judge_config)
agent = Agent(
    model=model,
    output_type=build_output_spec(judge_config, model, ResumeJudgeResult),
    system_prompt=prompt.content,
    model_settings=build_model_settings(judge_config),
    retries=0,
    output_retries=2,
)
```

```python
# src/seektalent/runtime/runtime_reports.py
return "\n".join(
    [
        f"- Protocol: `{settings.text_llm_protocol_family}`",
        f"- Endpoint: `{settings.text_llm_endpoint_kind}` / `{settings.text_llm_endpoint_region}`",
        f"- Models: requirements=`{settings.requirements_model_id}`, controller=`{settings.controller_model_id}`, scoring=`{settings.scoring_model_id}`, reflection=`{settings.reflection_model_id}`, finalize=`{settings.finalize_model_id}`, judge=`{settings.judge_model_id}`",
    ]
)
```

- [ ] **Step 4: Re-run the stage-routing and evaluation tests**

Run:

```bash
uv run pytest -q \
  tests/test_candidate_feedback.py \
  tests/test_evaluation.py \
  tests/test_resume_quality.py \
  tests/test_api.py
```

Expected: PASS, with judge now on the same canonical provider surface and candidate-feedback preserving behavior while using the canonical model-id surface.

- [ ] **Step 5: Commit the stage migration**

```bash
git add \
  src/seektalent/requirements/extractor.py \
  src/seektalent/controller/react_controller.py \
  src/seektalent/reflection/critic.py \
  src/seektalent/scoring/scorer.py \
  src/seektalent/finalize/finalizer.py \
  src/seektalent/repair.py \
  src/seektalent/candidate_feedback/model_steps.py \
  src/seektalent/evaluation.py \
  src/seektalent/runtime/runtime_reports.py \
  tests/test_candidate_feedback.py \
  tests/test_evaluation.py \
  tests/test_resume_quality.py \
  tests/test_api.py
git commit -m "feat: route text stages through canonical deepseek v4 surface"
```

## Task 4: Runtime Diagnostics, Failure Taxonomy, And Run Config Metadata

**Files:**
- Modify: `src/seektalent/models.py`
- Modify: `src/seektalent/tracing.py`
- Modify: `src/seektalent/runtime/runtime_diagnostics.py`
- Modify: `src/seektalent/runtime/orchestrator.py`
- Modify: `tests/test_runtime_audit.py`

- [ ] **Step 1: Write failing tests for protocol metadata and failure taxonomy**

```python
# tests/test_runtime_audit.py
from tests.settings_factory import make_settings


def test_public_run_config_emits_canonical_text_llm_settings() -> None:
    settings = make_settings()
    runtime = WorkflowRuntime(settings)
    run_config = runtime._build_public_run_config()

    run_settings = run_config["settings"]
    assert run_settings["text_llm_protocol_family"] == "anthropic_messages_compatible"
    assert run_settings["text_llm_endpoint_kind"] == "bailian_anthropic_messages"
    assert run_settings["requirements_model_id"] == "deepseek-v4-pro"
    assert "requirements_model" not in run_settings
    assert "judge_openai_base_url" not in run_settings


def test_llm_call_snapshot_records_protocol_reasoning_and_failure_kinds() -> None:
    snapshot = LLMCallSnapshot(
        stage="controller",
        call_id="controller-r01-call",
        model_id="deepseek-v4-pro",
        provider="bailian",
        protocol_family="anthropic_messages_compatible",
        endpoint_kind="bailian_anthropic_messages",
        endpoint_region="beijing",
        structured_output_mode="prompted_json",
        thinking_mode=True,
        reasoning_effort="high",
        failure_kind="provider_error",
        provider_failure_kind="provider_invalid_request",
        provider_status_code=400,
        provider_error_type="invalid_parameter_error",
        prompt_hash="prompt",
        prompt_snapshot_path="assets/prompts/controller.md",
        retries=0,
        output_retries=2,
        started_at="2026-04-29T10:00:00+08:00",
        status="failed",
        input_payload_sha256="abc",
        prompt_chars=10,
        input_payload_chars=10,
        output_chars=0,
        input_summary="controller payload",
        error_message="bad request",
    )

    payload = snapshot.model_dump(mode="json")
    assert payload["protocol_family"] == "anthropic_messages_compatible"
    assert payload["provider_failure_kind"] == "provider_invalid_request"
    assert payload["provider_status_code"] == 400
    assert payload["provider_error_type"] == "invalid_parameter_error"
    assert payload["structured_output_mode"] == "prompted_json"
```

- [ ] **Step 2: Run runtime-audit tests and confirm they fail**

Run:

```bash
uv run pytest -q tests/test_runtime_audit.py
```

Expected: FAIL because `run_config` still exposes old keys, `LLMCallSnapshot` does not yet carry protocol/endpoint/reasoning fields, and failure kinds are still too coarse.

- [ ] **Step 3: Extend artifact models and runtime metadata**

```python
# src/seektalent/tracing.py
class LLMCallSnapshot(BaseModel):
    stage: str
    call_id: str
    model_id: str
    provider: str
    protocol_family: Literal[
        "openai_chat_completions_compatible",
        "anthropic_messages_compatible",
    ]
    endpoint_kind: str
    endpoint_region: str
    structured_output_mode: Literal["native_json_schema", "prompted_json"]
    thinking_mode: bool
    reasoning_effort: Literal["off", "low", "medium", "high", "xhigh", "max"]
    failure_kind: Literal[
        "timeout",
        "transport_error",
        "provider_error",
        "response_validation_error",
        "structured_output_parse_error",
        "settings_migration_error",
        "unsupported_capability",
    ] | None = None
    provider_failure_kind: Literal[
        "provider_auth_error",
        "provider_access_denied",
        "provider_quota_exceeded",
        "provider_rate_limited",
        "provider_model_not_found",
        "provider_endpoint_mismatch",
        "provider_invalid_request",
        "provider_unsupported_parameter",
        "provider_content_safety_block",
        "provider_schema_error",
        "provider_timeout",
        "provider_unknown_error",
    ] | None = None
    provider_status_code: int | None = None
    provider_error_type: str | None = None
    provider_error_code: str | None = None
    provider_request_id: str | None = None
```

```python
# src/seektalent/runtime/runtime_diagnostics.py
def classify_text_llm_failure(exc: Exception) -> ProviderFailureInfo:
    ...
```

```python
# src/seektalent/runtime/orchestrator.py
def _build_public_run_config(self) -> dict[str, object]:
    return {
        "settings": {
            "text_llm_protocol_family": self.settings.text_llm_protocol_family,
            "text_llm_provider_label": self.settings.text_llm_provider_label,
            "text_llm_endpoint_kind": self.settings.text_llm_endpoint_kind,
            "text_llm_endpoint_region": self.settings.text_llm_endpoint_region,
            "requirements_model_id": self.settings.requirements_model_id,
            "controller_model_id": self.settings.controller_model_id,
            "scoring_model_id": self.settings.scoring_model_id,
            "finalize_model_id": self.settings.finalize_model_id,
            "reflection_model_id": self.settings.reflection_model_id,
            "structured_repair_model_id": self.settings.structured_repair_model_id,
            "judge_model_id": self.settings.judge_model_id,
            "candidate_feedback_model_id": self.settings.candidate_feedback_model_id,
        },
        "configured_providers": [self.settings.text_llm_endpoint_kind],
    }
```

```python
# src/seektalent/models.py
class ReplaySnapshot(BaseModel):
    ...
    text_llm_protocol_family: str | None = None
    text_llm_endpoint_kind: str | None = None
    text_llm_endpoint_region: str | None = None
    judge_protocol_family: str | None = None
    judge_prompt_hash: str | None = None
    judge_policy_version: str | None = None
```

- [ ] **Step 4: Re-run runtime-audit tests**

Run:

```bash
uv run pytest -q tests/test_runtime_audit.py
```

Expected: PASS, with the run config, call snapshots, and replay rows all reflecting the canonical protocol-family and failure taxonomy, including `provider_status_code` / `provider_error_type` when the provider returns them.

- [ ] **Step 5: Commit the diagnostics and artifact metadata changes**

```bash
git add \
  src/seektalent/models.py \
  src/seektalent/tracing.py \
  src/seektalent/runtime/runtime_diagnostics.py \
  src/seektalent/runtime/orchestrator.py \
  tests/test_runtime_audit.py
git commit -m "feat: record canonical text llm diagnostics metadata"
```

## Task 5: Benchmark Child-Run Precreation And Failed-Row Linkage

**Files:**
- Modify: `src/seektalent/api.py`
- Modify: `src/seektalent/cli.py`
- Modify: `src/seektalent/tracing.py`
- Modify: `src/seektalent/runtime/orchestrator.py`
- Modify: `src/seektalent/artifacts/store.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_runtime_state_flow.py`

- [ ] **Step 1: Write failing tests for benchmark failure linkage**

```python
# tests/test_cli.py
import json
from pathlib import Path

from seektalent.artifacts import ArtifactResolver
from seektalent.cli import main


def test_benchmark_failure_rows_keep_child_run_linkage(monkeypatch, tmp_path: Path) -> None:
    benchmark_file = tmp_path / "bench.jsonl"
    benchmark_file.write_text(
        json.dumps(
            {
                "jd_id": "case-1",
                "job_title": "Python Engineer",
                "job_description": "JD",
                "hiring_notes": "",
                "input_index": 0,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    def _fail_run_match(**_: object):
        raise ValueError("legacy text-llm config detected")

    monkeypatch.setattr("seektalent.cli.run_match", _fail_run_match)

    exit_code = main(
        [
            "benchmark",
            "--jds-file",
            str(benchmark_file),
            "--json",
            "--artifacts-dir",
            str(tmp_path / "artifacts"),
        ]
    )

    assert exit_code == 1
    benchmark_root = next((tmp_path / "artifacts").glob("benchmark-executions/*/*/*/benchmark_*"))
    summary_path = ArtifactResolver.for_root(benchmark_root).resolve("output.summary")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    row = summary["runs"][0]
    assert row["status"] == "failed"
    assert row["run_id"]
    assert row["run_dir"]
    assert row["trace_log_path"]


def test_benchmark_settings_migration_failure_still_creates_child_run(monkeypatch, tmp_path: Path) -> None:
    benchmark_file = tmp_path / "bench.jsonl"
    benchmark_file.write_text(
        json.dumps(
            {
                "jd_id": "case-legacy",
                "job_title": "Python Engineer",
                "job_description": "JD",
                "hiring_notes": "",
                "input_index": 0,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SEEKTALENT_REQUIREMENTS_MODEL", "openai-chat:deepseek-v3.2")

    exit_code = main(
        [
            "benchmark",
            "--jds-file",
            str(benchmark_file),
            "--json",
            "--artifacts-dir",
            str(tmp_path / "artifacts"),
        ]
    )

    assert exit_code == 1
    benchmark_root = next((tmp_path / "artifacts").glob("benchmark-executions/*/*/*/benchmark_*"))
    manifest = ArtifactResolver.for_root(benchmark_root).manifest
    assert manifest.child_artifacts
```

- [ ] **Step 2: Run benchmark CLI tests and confirm they fail**

Run:

```bash
uv run pytest -q tests/test_cli.py
```

Expected: FAIL because benchmark failures currently happen before a child run is guaranteed, failed rows only carry `error`/`attempts`, and there is no way to attach a precreated case-run session to the real runtime.

- [ ] **Step 3: Create real benchmark child-run sessions and inject them into runtime/preflight**

```python
# src/seektalent/artifacts/store.py
def create_child_run(
    self,
    *,
    parent: ArtifactSession,
    display_name: str,
    producer: str,
    case_id: str,
) -> ArtifactSession:
    session = self.create_root(kind="run", display_name=display_name, producer=producer)
    parent.set_child_artifacts(
        [
            *[entry.model_dump(mode="json") for entry in parent.manifest.child_artifacts],
            {
                "artifact_kind": "run",
                "artifact_id": session.manifest.artifact_id,
                "role": "case_run",
                "case_id": case_id,
            },
        ]
    )
    return session
```

```python
# src/seektalent/tracing.py
@classmethod
def from_session(cls, *, artifacts_root: Path, session: ArtifactSession) -> RunTracer:
    tracer = cls.__new__(cls)
    tracer.store = ArtifactStore(artifacts_root)
    tracer.session = session
    tracer.run_id = session.manifest.artifact_id
    tracer.run_dir = session.root
    tracer.trace_log_path, tracer._trace_handle = session.open_text_stream("runtime.trace_log")
    tracer.events_path, tracer._events_handle = session.open_text_stream("runtime.events")
    tracer._lock = threading.Lock()
    return tracer
```

```python
# src/seektalent/runtime/orchestrator.py
async def run_async(..., artifact_session: ArtifactSession | None = None) -> RunArtifacts:
    tracer = (
        RunTracer.from_session(artifacts_root=self.settings.artifacts_path, session=artifact_session)
        if artifact_session is not None
        else RunTracer(self.settings.artifacts_path)
    )
```

```python
# src/seektalent/cli.py
def _prepare_benchmark_case_run(
    *,
    benchmark_session: ArtifactSession,
    settings: AppSettings,
    case_id: str,
) -> ArtifactSession:
    session = ArtifactStore(settings.artifacts_path).create_child_run(
        parent=benchmark_session,
        display_name=f"benchmark case {case_id}",
        producer="BenchmarkCLI",
        case_id=case_id,
    )
    trace_log_path, handle = session.open_text_stream("runtime.trace_log")
    handle.write(f"[{_now_iso()}] benchmark_case_precreated | case_id={case_id}\n")
    handle.close()
    return session


def _failed_benchmark_result_row(
    row: dict[str, object],
    *,
    attempt: BenchmarkAttempt,
    completed_at: str,
    completion_index: int,
    error: str,
    run_id: str,
    run_dir: Path,
    trace_log_path: Path,
) -> dict[str, object]:
    return {
        "jd_id": row["jd_id"],
        "status": "failed",
        "attempts": attempt.attempt,
        "completed_at": completed_at,
        "completion_index": completion_index,
        "error": error,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "trace_log_path": str(trace_log_path),
    }
```

- [ ] **Step 4: Re-run benchmark CLI tests**

Run:

```bash
uv run pytest -q tests/test_cli.py
```

Expected: PASS, with failed rows and benchmark manifests now referencing the same real child run session that settings preflight, provider preflight, and runtime execution use.

- [ ] **Step 5: Commit the benchmark linkage fix**

```bash
git add \
  src/seektalent/api.py \
  src/seektalent/artifacts/store.py \
  src/seektalent/cli.py \
  src/seektalent/tracing.py \
  src/seektalent/runtime/orchestrator.py \
  tests/test_cli.py \
  tests/test_runtime_state_flow.py
git commit -m "feat: preserve benchmark failure run linkage"
```

## Task 6: Final Regression, Docs, And DeepSeek V4 Default Verification

**Files:**
- Modify: `docs/outputs.md`
- Modify: `tests/test_jd_text_baseline.py`
- Modify: `tests/test_openclaw_baseline.py`
- Modify: `tests/test_claude_code_baseline.py`

- [ ] **Step 1: Update docs and baseline tests to the new canonical runtime vocabulary**

```markdown
# docs/outputs.md
- `runtime.run_config.json` now records:
  - `text_llm_protocol_family`
  - `text_llm_endpoint_kind`
  - `text_llm_endpoint_region`
  - bare `*_model_id` stage settings
- text-stage call artifacts now record:
  - `structured_output_mode`
  - `thinking_mode`
  - `reasoning_effort`
  - `failure_kind`
  - `provider_failure_kind`
- benchmark failure rows always include:
  - `run_id`
  - `run_dir`
  - `trace_log_path`
```

```python
# tests/test_jd_text_baseline.py
def test_jd_text_baseline_uses_deepseek_v4_pro_for_judge() -> None:
    settings = make_settings()
    assert settings.judge_model_id == "deepseek-v4-pro"
    assert settings.text_llm_protocol_family == "anthropic_messages_compatible"


def test_judge_lineage_fields_are_concrete() -> None:
    evaluation = _evaluation_result()
    payload = evaluation.model_dump(mode="json")
    assert payload["judge_model"] == "deepseek-v4-pro"
    assert payload["judge_protocol_family"] == "anthropic_messages_compatible"
    assert payload["judge_prompt_hash"]
    assert payload["judge_policy_version"]
```

- [ ] **Step 2: Run the focused regression suite**

Run:

```bash
uv run pytest -q \
  tests/test_llm_provider_config.py \
  tests/test_candidate_feedback.py \
  tests/test_runtime_audit.py \
  tests/test_runtime_state_flow.py \
  tests/test_evaluation.py \
  tests/test_cli.py \
  tests/test_api.py \
  tests/test_resume_quality.py \
  tests/test_jd_text_baseline.py \
  tests/test_openclaw_baseline.py \
  tests/test_claude_code_baseline.py
```

Expected: PASS, with no remaining references to `openai-responses:` or `judge_openai_*` in active settings/tests.

- [ ] **Step 3: Run one real smoke under each supported protocol family and then the three benchmark-family smokes on the default protocol**

Run:

```bash
mkdir -p /tmp/seektalent-text-llm-smoke
python - <<'PY'
import json
from pathlib import Path

root = Path("artifacts/benchmarks")
out = Path("/tmp/seektalent-text-llm-smoke")
mapping = {
    "agent": root / "agent_jds.jsonl",
    "bigdata": root / "bigdata_jds.jsonl",
    "llm_training": root / "llm_training_jds.jsonl",
}
for name, path in mapping.items():
    first = path.read_text(encoding="utf-8").splitlines()[0]
    (out / f"{name}.jsonl").write_text(first + "\n", encoding="utf-8")
PY
SEEKTALENT_TEXT_LLM_PROTOCOL_FAMILY=openai_chat_completions_compatible \
SEEKTALENT_TEXT_LLM_ENDPOINT_KIND=bailian_openai_chat_completions \
SEEKTALENT_TEXT_LLM_ENDPOINT_REGION=beijing \
uv run seektalent benchmark --jds-file /tmp/seektalent-text-llm-smoke/agent.jsonl
SEEKTALENT_TEXT_LLM_PROTOCOL_FAMILY=anthropic_messages_compatible \
SEEKTALENT_TEXT_LLM_ENDPOINT_KIND=bailian_anthropic_messages \
SEEKTALENT_TEXT_LLM_ENDPOINT_REGION=beijing \
uv run seektalent benchmark --jds-file /tmp/seektalent-text-llm-smoke/agent.jsonl
uv run seektalent benchmark --jds-file /tmp/seektalent-text-llm-smoke/agent.jsonl
uv run seektalent benchmark --jds-file /tmp/seektalent-text-llm-smoke/bigdata.jsonl
uv run seektalent benchmark --jds-file /tmp/seektalent-text-llm-smoke/llm_training.jsonl
```

Expected:

- both supported protocol families can execute at least one provider-backed smoke on Bailian;
- no run fails because of missing `run_id/run_dir/trace_log_path`;
- any provider/config failure is classified into the new failure taxonomy;
- benchmark summaries show the canonical protocol/model surface rather than old prefixed model strings.

- [ ] **Step 4: Commit docs and final verification updates**

```bash
git add \
  docs/outputs.md \
  tests/test_jd_text_baseline.py \
  tests/test_openclaw_baseline.py \
  tests/test_claude_code_baseline.py
git commit -m "docs: document canonical text llm runtime surface"
```

## Self-Review

- **Spec coverage:** The tasks cover the hard-cut config surface, region/capability preflight, judge migration, candidate-feedback config boundary, reasoning policy, runtime diagnostics, and benchmark child-run linkage. Candidate-feedback phrase quality and stopping/exhaustion remain untouched by design.
- **Execution fidelity:** The snippets are illustrative, but the blocking seams are now explicit: fresh-worktree-only execution, resolved endpoint URLs, explicit OpenAIChatModel/AnthropicModel construction, real child-run injection into runtime, and failure classification rather than empty metadata shells.
- **Type consistency:** The plan consistently uses `text_llm_protocol_family`, `text_llm_endpoint_kind`, `text_llm_endpoint_region`, bare `*_model_id` fields, `ResolvedTextModelConfig`, `failure_kind`, and `provider_failure_kind`. No later task reverts to the old prefixed model-string surface.
