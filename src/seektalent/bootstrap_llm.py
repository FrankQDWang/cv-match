from __future__ import annotations

import json
from typing import Any

from pydantic_ai import Agent

from seektalent.models import (
    GroundingDraft,
    KnowledgeRetrievalResult,
    RequirementExtractionDraft,
    RequirementSheet,
    SearchInputTruth,
)


REQUIREMENT_EXTRACTION_INSTRUCTIONS = """
Extract a strict structured requirement draft from the hiring input.
Only use evidence from the provided job description and hiring notes.
Return structured fields only.
""".strip()

GROUNDING_GENERATION_INSTRUCTIONS = """
Generate a strict structured grounding draft for round-0 bootstrap.
Use only the provided requirement sheet and retrieved knowledge cards.
Do not invent domain packs, cards, or unsupported operators.
""".strip()


def build_requirement_extraction_agent(model: Any | None = None) -> Agent:
    return Agent(
        model,
        output_type=RequirementExtractionDraft,
        retries=0,
        output_retries=1,
        builtin_tools=(),
        toolsets=(),
        system_prompt=(),
    )


def build_grounding_generation_agent(model: Any | None = None) -> Agent:
    return Agent(
        model,
        output_type=GroundingDraft,
        retries=0,
        output_retries=1,
        builtin_tools=(),
        toolsets=(),
        system_prompt=(),
    )


async def request_requirement_extraction_draft(
    input_truth: SearchInputTruth,
    *,
    agent: Agent | None = None,
    model: Any | None = None,
    instructions: str = REQUIREMENT_EXTRACTION_INSTRUCTIONS,
) -> RequirementExtractionDraft:
    active_agent = agent or build_requirement_extraction_agent(model=model)
    result = await active_agent.run(
        input_truth.model_dump_json(),
        output_type=RequirementExtractionDraft,
        message_history=None,
        instructions=instructions,
        builtin_tools=(),
        toolsets=(),
        infer_name=False,
    )
    return RequirementExtractionDraft.model_validate(result.output)


async def request_grounding_draft(
    requirement_sheet: RequirementSheet,
    knowledge_retrieval_result: KnowledgeRetrievalResult,
    *,
    agent: Agent | None = None,
    model: Any | None = None,
    instructions: str = GROUNDING_GENERATION_INSTRUCTIONS,
) -> GroundingDraft:
    active_agent = agent or build_grounding_generation_agent(model=model)
    packet = json.dumps(
        {
            "requirement_sheet": requirement_sheet.model_dump(mode="json"),
            "knowledge_retrieval_result": knowledge_retrieval_result.model_dump(mode="json"),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    result = await active_agent.run(
        packet,
        output_type=GroundingDraft,
        message_history=None,
        instructions=instructions,
        builtin_tools=(),
        toolsets=(),
        infer_name=False,
    )
    return GroundingDraft.model_validate(result.output)


__all__ = [
    "GROUNDING_GENERATION_INSTRUCTIONS",
    "REQUIREMENT_EXTRACTION_INSTRUCTIONS",
    "build_grounding_generation_agent",
    "build_requirement_extraction_agent",
    "request_grounding_draft",
    "request_requirement_extraction_draft",
]
