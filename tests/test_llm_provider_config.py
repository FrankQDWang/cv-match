from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from cv_match.config import AppSettings
from cv_match.controller.react_controller import ReActController
from cv_match.finalize.finalizer import Finalizer
from cv_match.llm import (
    build_model,
    build_model_settings,
    build_output_spec,
    model_provider,
    preflight_models,
)
from cv_match.prompting import LoadedPrompt
from cv_match.reflection.critic import ReflectionCritic
from cv_match.requirements.extractor import RequirementExtractor
from cv_match.scoring.scorer import ResumeScorer


def _prompt(name: str) -> LoadedPrompt:
    return LoadedPrompt(name=name, path=Path(f"{name}.md"), content=f"{name} prompt", sha256="hash")


def test_app_settings_rejects_unqualified_model_ids() -> None:
    with pytest.raises(ValidationError, match="provider:model"):
        AppSettings(_env_file=None, requirements_model="gpt-5.4-mini")


def test_app_settings_accepts_fully_qualified_model_ids() -> None:
    settings = AppSettings(
        _env_file=None,
        requirements_model="openai-responses:gpt-5.4-mini",
        controller_model="openai-responses:gpt-5.4-mini",
        scoring_model="anthropic:claude-sonnet-4-5",
        finalize_model="google-gla:gemini-2.5-flash",
        reflection_model="openai-responses:gpt-5.4",
    )

    assert settings.requirements_model == "openai-responses:gpt-5.4-mini"
    assert settings.controller_model == "openai-responses:gpt-5.4-mini"
    assert settings.scoring_model == "anthropic:claude-sonnet-4-5"
    assert settings.finalize_model == "google-gla:gemini-2.5-flash"


def test_model_provider_returns_prefix() -> None:
    assert model_provider("openai-responses:gpt-5.4-mini") == "openai-responses"
    assert model_provider("anthropic:claude-sonnet-4-5") == "anthropic"


def test_build_model_routes_through_infer_model(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_infer_model(model_id: str) -> object:
        calls.append(model_id)
        return object()

    monkeypatch.setattr("cv_match.llm.infer_model", fake_infer_model)

    build_model("openai-responses:gpt-5.4-mini")

    assert calls == ["openai-responses:gpt-5.4-mini"]


def test_build_output_spec_uses_native_output_for_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    model = build_model("openai-responses:gpt-5.4-mini")

    spec = build_output_spec("openai-responses:gpt-5.4-mini", model, dict[str, str])

    assert type(spec).__name__ == "NativeOutput"
    assert spec.strict is True


def test_build_model_settings_keeps_openai_only_knobs_for_openai_models() -> None:
    settings = AppSettings(_env_file=None)

    model_settings = build_model_settings(settings, "openai-responses:gpt-5.4-mini")

    assert model_settings["thinking"] == "medium"
    assert model_settings["openai_reasoning_summary"] == "concise"
    assert model_settings["openai_text_verbosity"] == "low"


def test_build_model_settings_omits_openai_only_knobs_for_other_providers() -> None:
    settings = AppSettings(_env_file=None)

    model_settings = build_model_settings(settings, "anthropic:claude-sonnet-4-5")

    assert model_settings == {"thinking": "medium"}


def test_preflight_models_fails_when_native_structured_output_is_unsupported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProfile:
        supports_json_schema_output = False

    class FakeModel:
        profile = FakeProfile()

    monkeypatch.setattr("cv_match.llm.build_model", lambda model_id: FakeModel())
    settings = AppSettings(_env_file=None)

    with pytest.raises(ValueError, match="native structured output"):
        preflight_models(settings)


@pytest.mark.parametrize(
    ("model_id", "env_var"),
    [
        ("openai-responses:gpt-5.4-mini", "OPENAI_API_KEY"),
        ("anthropic:claude-sonnet-4-5", "ANTHROPIC_API_KEY"),
        ("google-gla:gemini-2.5-pro", "GOOGLE_API_KEY"),
    ],
)
def test_preflight_models_surfaces_provider_credential_errors(
    monkeypatch: pytest.MonkeyPatch,
    model_id: str,
    env_var: str,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    settings = AppSettings(_env_file=None).with_overrides(
        requirements_model=model_id,
        controller_model=model_id,
        scoring_model=model_id,
        reflection_model=model_id,
        finalize_model=model_id,
    )

    with pytest.raises(Exception, match=env_var):
        preflight_models(settings)


@pytest.mark.parametrize(
    ("builder", "prompt_name"),
    [
        (RequirementExtractor, "requirements"),
        (ReActController, "controller"),
        (ResumeScorer, "scoring"),
        (ReflectionCritic, "reflection"),
        (Finalizer, "finalize"),
    ],
)
def test_all_agents_use_one_output_retry_and_no_generic_retries(
    monkeypatch: pytest.MonkeyPatch,
    builder,
    prompt_name: str,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    settings = AppSettings(_env_file=None)
    component = builder(settings, _prompt(prompt_name))
    agent = component._get_agent()

    assert agent._max_tool_retries == 0
    assert agent._max_result_retries == 1
    assert type(agent._output_type).__name__ == "NativeOutput"
    assert agent._output_type.strict is True
