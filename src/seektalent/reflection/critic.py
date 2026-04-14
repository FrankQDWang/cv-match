from __future__ import annotations

from pydantic_ai import Agent

from seektalent.config import AppSettings
from seektalent.llm import build_model, build_model_settings, build_output_spec
from seektalent.models import ReflectionAdvice, ReflectionContext
from seektalent.prompting import LoadedPrompt, json_block


class ReflectionCritic:
    def __init__(self, settings: AppSettings, prompt: LoadedPrompt) -> None:
        self.settings = settings
        self.prompt = prompt

    def _get_agent(self) -> Agent[None, ReflectionAdvice]:
        model = build_model(self.settings.reflection_model)
        return Agent(
            model=model,
            output_type=build_output_spec(self.settings.reflection_model, model, ReflectionAdvice),
            system_prompt=self.prompt.content,
            model_settings=build_model_settings(self.settings, self.settings.reflection_model),
            retries=0,
            output_retries=1,
        )

    async def reflect(self, *, context: ReflectionContext) -> ReflectionAdvice:
        result = await self._get_agent().run(
            json_block("REFLECTION_CONTEXT", context.model_dump(mode="json")),
        )
        return result.output
