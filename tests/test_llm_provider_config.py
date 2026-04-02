from __future__ import annotations

import pytest
from pydantic import ValidationError

from cv_match.config import AppSettings
from cv_match.llm import build_model, build_model_settings, model_provider, preflight_models


def test_app_settings_rejects_unqualified_model_ids() -> None:
    with pytest.raises(ValidationError, match="provider:model"):
        AppSettings(_env_file=None, strategy_model="gpt-5.4-mini")


def test_app_settings_accepts_fully_qualified_model_ids() -> None:
    settings = AppSettings(
        _env_file=None,
        strategy_model="openai-responses:gpt-5.4-mini",
        scoring_model="anthropic:claude-sonnet-4-5",
        finalize_model="google-gla:gemini-2.5-flash",
        reflection_model="openai-responses:gpt-5.4",
    )

    assert settings.strategy_model == "openai-responses:gpt-5.4-mini"
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
        strategy_model=model_id,
        scoring_model=model_id,
        reflection_model=model_id,
        finalize_model=model_id,
    )

    with pytest.raises(Exception, match=env_var):
        preflight_models(settings)
