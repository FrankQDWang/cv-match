from __future__ import annotations

import asyncio

from pydantic_ai import Agent

from cv_match.config import AppSettings
from cv_match.llm import build_model, build_model_settings
from cv_match.models import InputTruth, RequirementExtractionDraft, RequirementSheet
from cv_match.prompting import LoadedPrompt, json_block
from cv_match.requirements.normalization import normalize_requirement_draft


class RequirementExtractor:
    def __init__(self, settings: AppSettings, prompt: LoadedPrompt) -> None:
        self.settings = settings
        self.prompt = prompt
        self.agent: Agent[None, RequirementExtractionDraft] | None = None

    def _get_agent(self) -> Agent[None, RequirementExtractionDraft]:
        if self.agent is None:
            self.agent = Agent(
                model=build_model(self.settings.requirements_model),
                output_type=RequirementExtractionDraft,
                system_prompt=self.prompt.content,
                model_settings=build_model_settings(self.settings, self.settings.requirements_model),
            )
        return self.agent

    def extract(self, *, input_truth: InputTruth) -> RequirementSheet:
        return asyncio.run(self._extract_live(input_truth=input_truth))

    async def _extract_live(self, *, input_truth: InputTruth) -> RequirementSheet:
        result = await asyncio.wait_for(
            self._get_agent().run(json_block("INPUT_TRUTH", input_truth.model_dump(mode="json"))),
            timeout=90,
        )
        return normalize_requirement_draft(result.output)
