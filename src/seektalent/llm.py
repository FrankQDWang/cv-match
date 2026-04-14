from __future__ import annotations

from typing import Any

import httpx
from pydantic_ai import NativeOutput, PromptedOutput
from pydantic_ai.models import DEFAULT_HTTP_TIMEOUT, Model, get_user_agent, infer_model
from pydantic_ai.providers import infer_provider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from seektalent.config import AppSettings, load_process_env


def model_provider(model_id: str) -> str:
    return model_id.split(":", 1)[0]


def _fresh_openai_provider() -> OpenAIProvider:
    return OpenAIProvider(
        http_client=httpx.AsyncClient(
            timeout=httpx.Timeout(timeout=DEFAULT_HTTP_TIMEOUT, connect=5),
            headers={"User-Agent": get_user_agent()},
        )
    )


def build_model(model_id: str) -> Model:
    load_process_env()

    def provider_factory(provider_name: str):
        if provider_name in {"openai", "openai-chat", "openai-responses"}:
            return _fresh_openai_provider()
        return infer_provider(provider_name)

    return infer_model(model_id, provider_factory=provider_factory)


def ensure_native_structured_output(model_id: str, model: Model) -> None:
    profile = model.profile
    if getattr(profile, "supports_json_schema_output", False):
        return
    raise ValueError(f"{model_id} does not support native structured output via JSON Schema.")


def build_output_spec(model_id: str, model: Model, output_type: Any) -> Any:
    if model_id.startswith("openai-chat:"):
        return PromptedOutput(output_type)
    ensure_native_structured_output(model_id, model)
    return NativeOutput(output_type, strict=True)


def build_model_settings(settings: AppSettings, model_id: str) -> ModelSettings:
    thinking = False if settings.reasoning_effort == "off" else settings.reasoning_effort
    model_settings: ModelSettings = {"thinking": thinking}
    if not model_id.startswith("openai-responses:"):
        return model_settings

    openai_settings: ModelSettings = {
        "thinking": thinking,
        "openai_text_verbosity": "low",
    }
    if thinking is not False:
        openai_settings["openai_reasoning_summary"] = "concise"
    return openai_settings


def preflight_models(settings: AppSettings) -> None:
    seen: set[str] = set()
    for model_id in (
        settings.requirements_model,
        settings.controller_model,
        settings.scoring_model,
        settings.reflection_model,
        settings.finalize_model,
    ):
        if model_id in seen:
            continue
        model = build_model(model_id)
        if not model_id.startswith("openai-chat:"):
            ensure_native_structured_output(model_id, model)
        seen.add(model_id)
