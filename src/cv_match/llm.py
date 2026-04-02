from __future__ import annotations

from pydantic_ai.models import Model, infer_model
from pydantic_ai.settings import ModelSettings

from cv_match.config import AppSettings


def model_provider(model_id: str) -> str:
    return model_id.split(":", 1)[0]


def build_model(model_id: str) -> Model:
    return infer_model(model_id)


def build_model_settings(settings: AppSettings, model_id: str) -> ModelSettings:
    model_settings: ModelSettings = {"thinking": settings.reasoning_effort}
    if not model_id.startswith("openai-responses:"):
        return model_settings

    return {
        "thinking": settings.reasoning_effort,
        "openai_reasoning_summary": "concise",
        "openai_text_verbosity": "low",
    }


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
        build_model(model_id)
        seen.add(model_id)
