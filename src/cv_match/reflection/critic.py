from __future__ import annotations

import asyncio

from pydantic_ai import Agent

from cv_match.config import AppSettings
from cv_match.llm import build_model, build_model_settings, build_output_spec
from cv_match.models import ReflectionAdvice, ReflectionContext
from cv_match.prompting import LoadedPrompt, json_block


class ReflectionCritic:
    def __init__(self, settings: AppSettings, prompt: LoadedPrompt) -> None:
        self.settings = settings
        self.prompt = prompt
        self.agent: Agent[None, ReflectionAdvice] | None = None

    def _get_agent(self) -> Agent[None, ReflectionAdvice]:
        if self.agent is None:
            model = build_model(self.settings.reflection_model)
            self.agent = Agent(
                model=model,
                output_type=build_output_spec(self.settings.reflection_model, model, ReflectionAdvice),
                system_prompt=self.prompt.content,
                model_settings=build_model_settings(self.settings, self.settings.reflection_model),
                retries=0,
                output_retries=1,
            )
        return self.agent

    def reflect(self, *, context: ReflectionContext) -> ReflectionAdvice:
        return asyncio.run(self._reflect_live(context=context))

    async def _reflect_live(self, *, context: ReflectionContext) -> ReflectionAdvice:
        result = await asyncio.wait_for(
            self._get_agent().run(json_block("REFLECTION_CONTEXT", context.model_dump(mode="json"))),
            timeout=120,
        )
        return result.output
