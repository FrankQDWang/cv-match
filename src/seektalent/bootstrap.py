from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent

from seektalent.bootstrap_assets import BootstrapAssets, default_bootstrap_assets
from seektalent.bootstrap_llm import request_grounding_draft, request_requirement_extraction_draft
from seektalent.bootstrap_ops import (
    freeze_scoring_policy,
    generate_grounding_output,
    initialize_frontier_state,
    retrieve_grounding_knowledge,
)
from seektalent.models import (
    FrontierState_t,
    GroundingOutput,
    KnowledgeRetrievalResult,
    RequirementSheet,
    ScoringPolicy,
    SearchInputTruth,
)
from seektalent.requirements import build_input_truth, normalize_requirement_draft


@dataclass(frozen=True)
class BootstrapArtifacts:
    input_truth: SearchInputTruth
    requirement_sheet: RequirementSheet
    knowledge_retrieval_result: KnowledgeRetrievalResult
    scoring_policy: ScoringPolicy
    grounding_output: GroundingOutput
    frontier_state: FrontierState_t


async def bootstrap_round0_async(
    *,
    job_description: str,
    hiring_notes: str = "",
    assets: BootstrapAssets | None = None,
    requirement_extraction_agent: Agent | None = None,
    grounding_generation_agent: Agent | None = None,
    requirement_extraction_model: Any | None = None,
    grounding_generation_model: Any | None = None,
) -> BootstrapArtifacts:
    active_assets = assets or default_bootstrap_assets()
    input_truth = build_input_truth(job_description=job_description, hiring_notes=hiring_notes)
    requirement_draft = await request_requirement_extraction_draft(
        input_truth,
        agent=requirement_extraction_agent,
        model=requirement_extraction_model,
    )
    requirement_sheet = normalize_requirement_draft(requirement_draft, input_truth=input_truth)
    knowledge_retrieval_result = retrieve_grounding_knowledge(
        requirement_sheet,
        active_assets.business_policy_pack,
        active_assets.knowledge_base_snapshot,
        active_assets.knowledge_retrieval_budget,
        knowledge_cards=active_assets.knowledge_cards,
    )
    scoring_policy = freeze_scoring_policy(
        requirement_sheet,
        active_assets.business_policy_pack,
        active_assets.reranker_calibration,
    )
    grounding_draft = await request_grounding_draft(
        requirement_sheet,
        knowledge_retrieval_result,
        agent=grounding_generation_agent,
        model=grounding_generation_model,
    )
    grounding_output = generate_grounding_output(
        requirement_sheet,
        knowledge_retrieval_result,
        grounding_draft,
    )
    frontier_state = initialize_frontier_state(
        grounding_output,
        active_assets.runtime_search_budget,
        active_assets.operator_catalog,
    )
    return BootstrapArtifacts(
        input_truth=input_truth,
        requirement_sheet=requirement_sheet,
        knowledge_retrieval_result=knowledge_retrieval_result,
        scoring_policy=scoring_policy,
        grounding_output=grounding_output,
        frontier_state=frontier_state,
    )


def bootstrap_round0(
    *,
    job_description: str,
    hiring_notes: str = "",
    assets: BootstrapAssets | None = None,
    requirement_extraction_agent: Agent | None = None,
    grounding_generation_agent: Agent | None = None,
    requirement_extraction_model: Any | None = None,
    grounding_generation_model: Any | None = None,
) -> BootstrapArtifacts:
    return asyncio.run(
        bootstrap_round0_async(
            job_description=job_description,
            hiring_notes=hiring_notes,
            assets=assets,
            requirement_extraction_agent=requirement_extraction_agent,
            grounding_generation_agent=grounding_generation_agent,
            requirement_extraction_model=requirement_extraction_model,
            grounding_generation_model=grounding_generation_model,
        )
    )


__all__ = ["BootstrapArtifacts", "bootstrap_round0", "bootstrap_round0_async"]
