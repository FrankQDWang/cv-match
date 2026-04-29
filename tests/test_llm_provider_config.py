from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from seektalent.candidate_feedback.proposal_runtime import model_dependency_gate_allows_mainline
from seektalent.config import AppSettings, TextLLMConfigMigrationError, load_process_env
from tests.settings_factory import make_settings


ROOT = Path(__file__).resolve().parents[1]
ENV_TEMPLATES = [
    ROOT / ".env.example",
    ROOT / "src" / "seektalent" / "default.env",
]


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
    assert settings.candidate_feedback_model_id == "qwen3.5-flash"


def test_legacy_stage_key_in_dotenv_fails_with_migration_error(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SEEKTALENT_REQUIREMENTS_MODEL=openai-chat:deepseek-v3.2\n",
        encoding="utf-8",
    )

    with pytest.raises(TextLLMConfigMigrationError, match="legacy text-llm config"):
        AppSettings(_env_file=env_file)  # ty: ignore[unknown-argument]


def test_prefixed_value_on_new_model_id_key_fails_with_migration_error(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SEEKTALENT_REQUIREMENTS_MODEL_ID=openai-responses:gpt-5.4-mini\n",
        encoding="utf-8",
    )

    with pytest.raises(TextLLMConfigMigrationError, match="provider-prefixed model string"):
        AppSettings(_env_file=env_file)  # ty: ignore[unknown-argument]


def test_candidate_feedback_legacy_model_key_is_hard_cut(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SEEKTALENT_CANDIDATE_FEEDBACK_MODEL=openai-chat:qwen3.5-flash\n",
        encoding="utf-8",
    )

    with pytest.raises(TextLLMConfigMigrationError, match="legacy text-llm config"):
        AppSettings(_env_file=env_file)  # ty: ignore[unknown-argument]


def test_stage_model_id_init_kwarg_with_prefixed_value_fails_fast() -> None:
    with pytest.raises(TextLLMConfigMigrationError, match="provider-prefixed model string"):
        AppSettings(requirements_model_id="openai-chat:deepseek-v3.2", _env_file=None)  # ty: ignore[unknown-argument]


def test_protocol_family_and_endpoint_kind_must_match() -> None:
    with pytest.raises(ValidationError, match="text_llm_endpoint_kind"):
        make_settings(
            text_llm_protocol_family="anthropic_messages_compatible",
            text_llm_endpoint_kind="bailian_openai_chat_completions",
        )


def test_settings_scan_default_dotenv_when_not_overridden(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SEEKTALENT_REQUIREMENTS_MODEL=openai-chat:deepseek-v3.2\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(TextLLMConfigMigrationError, match="legacy text-llm config"):
        AppSettings()


def test_explicit_env_file_none_skips_default_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SEEKTALENT_REQUIREMENTS_MODEL=openai-chat:deepseek-v3.2\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    settings = AppSettings(_env_file=None)  # ty: ignore[unknown-argument]

    assert settings.requirements_model_id == "deepseek-v4-pro"


def test_checked_in_env_templates_use_new_text_llm_keys() -> None:
    for path in ENV_TEMPLATES:
        text = path.read_text(encoding="utf-8")
        assert "SEEKTALENT_TEXT_LLM_PROTOCOL_FAMILY=" in text
        assert "SEEKTALENT_TEXT_LLM_ENDPOINT_KIND=" in text
        assert "SEEKTALENT_TEXT_LLM_ENDPOINT_REGION=" in text
        assert "SEEKTALENT_REQUIREMENTS_MODEL_ID=deepseek-v4-pro" in text
        assert "SEEKTALENT_JUDGE_MODEL_ID=deepseek-v4-pro" in text
        assert "SEEKTALENT_REQUIREMENTS_MODEL=" not in text
        assert "SEEKTALENT_JUDGE_OPENAI_BASE_URL=" not in text


def test_prf_defaults_preserve_shadow_mode_and_legacy_backend() -> None:
    settings = make_settings()

    assert settings.prf_v1_5_mode == "shadow"
    assert settings.prf_model_backend == "legacy"


def test_sidecar_default_settings_remain_exposed() -> None:
    settings = make_settings()

    assert settings.prf_sidecar_profile == "host-local"
    assert settings.prf_sidecar_bind_host == "127.0.0.1"
    assert settings.prf_sidecar_endpoint == "http://127.0.0.1:8741"
    assert settings.prf_sidecar_serve_mode == "dev-bootstrap"
    assert settings.prf_sidecar_bakeoff_promoted is False


def test_mainline_mode_requires_pinned_model_revisions() -> None:
    settings = make_settings(prf_v1_5_mode="mainline")

    assert model_dependency_gate_allows_mainline(settings) is False


def test_runtime_mode_defaults_to_dev_paths() -> None:
    settings = make_settings()

    assert settings.runtime_mode == "dev"
    assert settings.artifacts_dir == "artifacts"
    assert settings.runs_dir == "runs"
    assert settings.llm_cache_dir == ".seektalent/cache"


def test_with_overrides_preserves_runtime_default_resolution() -> None:
    settings = make_settings().with_overrides(runtime_mode="prod")

    assert settings.runtime_mode == "prod"
    assert settings.artifacts_dir == "~/.seektalent/artifacts"
    assert settings.runs_dir == "~/.seektalent/runs"
    assert settings.llm_cache_dir == "~/.seektalent/cache"


def test_load_process_env_only_imports_provider_boundary_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "OPENAI_API_KEY=openai-key",
                "ANTHROPIC_API_KEY=anthropic-key",
                "SEEKTALENT_REQUIREMENTS_MODEL_ID=deepseek-v4-pro",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("SEEKTALENT_REQUIREMENTS_MODEL_ID", raising=False)

    load_process_env(env_file)

    assert os.environ["OPENAI_API_KEY"] == "openai-key"
    assert os.environ["ANTHROPIC_API_KEY"] == "anthropic-key"
    assert "SEEKTALENT_REQUIREMENTS_MODEL_ID" not in os.environ
