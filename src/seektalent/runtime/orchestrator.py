from __future__ import annotations

import asyncio
from typing import Any

import httpx

from seektalent.bootstrap import bootstrap_round0_async
from seektalent.bootstrap_assets import BootstrapAssets, default_bootstrap_assets
from seektalent.clients.cts_client import CTSClient, CTSClientProtocol, MockCTSClient
from seektalent.config import AppSettings
from seektalent.controller_llm import request_search_controller_decision_draft
from seektalent.frontier_ops import (
    carry_forward_frontier_state,
    generate_search_controller_decision,
    select_active_frontier_node,
)
from seektalent.models import FrontierState_t, RuntimeRoundState, SearchRunResult
from seektalent.runtime_llm import (
    request_branch_evaluation_draft,
    request_search_run_summary_draft,
)
from seektalent.runtime_ops import (
    compute_node_reward_breakdown,
    evaluate_branch_outcome,
    evaluate_stop_condition,
    finalize_search_run,
    update_frontier_state,
)
from seektalent.search_ops import (
    AsyncRerankRequest,
    execute_search_plan,
    materialize_search_execution_plan,
    score_search_results,
)
from seektalent_rerank.models import RerankRequest, RerankResponse


class WorkflowRuntime:
    def __init__(
        self,
        settings: AppSettings,
        *,
        assets: BootstrapAssets | None = None,
        cts_client: CTSClientProtocol | None = None,
        rerank_request: AsyncRerankRequest | None = None,
        requirement_extraction_model: Any | None = None,
        grounding_generation_model: Any | None = None,
        search_controller_decision_model: Any | None = None,
        branch_outcome_evaluation_model: Any | None = None,
        search_run_finalization_model: Any | None = None,
    ) -> None:
        self.settings = settings
        self.assets = assets
        self.cts_client = cts_client
        self.rerank_request = rerank_request
        self.requirement_extraction_model = requirement_extraction_model
        self.grounding_generation_model = grounding_generation_model
        self.search_controller_decision_model = search_controller_decision_model
        self.branch_outcome_evaluation_model = branch_outcome_evaluation_model
        self.search_run_finalization_model = search_run_finalization_model

    def run(self, *, job_description: str, hiring_notes: str = "") -> SearchRunResult:
        return asyncio.run(
            self.run_async(
                job_description=job_description,
                hiring_notes=hiring_notes,
            )
        )

    async def run_async(
        self,
        *,
        job_description: str,
        hiring_notes: str = "",
    ) -> SearchRunResult:
        active_assets = self.assets or default_bootstrap_assets()
        active_cts_client = self.cts_client or _default_cts_client(self.settings)
        active_rerank_request = self.rerank_request or _build_http_rerank_request(
            self.settings
        )
        bootstrap_artifacts = await bootstrap_round0_async(
            job_description=job_description,
            hiring_notes=hiring_notes,
            assets=active_assets,
            requirement_extraction_model=self.requirement_extraction_model,
            grounding_generation_model=self.grounding_generation_model,
        )
        frontier_state = bootstrap_artifacts.frontier_state
        runtime_round_state = RuntimeRoundState(runtime_round_index=0)

        while True:
            controller_context = select_active_frontier_node(
                frontier_state,
                bootstrap_artifacts.requirement_sheet,
                bootstrap_artifacts.scoring_policy,
                active_assets.crossover_guard_thresholds,
                active_assets.runtime_term_budget_policy,
            )
            controller_draft, _ = await request_search_controller_decision_draft(
                controller_context,
                model=self.search_controller_decision_model,
            )
            controller_decision = generate_search_controller_decision(
                controller_context,
                controller_draft,
            )
            if controller_decision.action == "stop":
                frontier_state_t1 = carry_forward_frontier_state(frontier_state)
                stop_reason, continue_flag = evaluate_stop_condition(
                    frontier_state_t1,
                    controller_decision.action,
                    None,
                    None,
                    active_assets.stop_guard_thresholds,
                    runtime_round_state,
                )
            else:
                execution_plan = materialize_search_execution_plan(
                    frontier_state,
                    bootstrap_artifacts.requirement_sheet,
                    controller_decision,
                    active_assets.runtime_term_budget_policy,
                    active_assets.runtime_search_budget,
                    active_assets.crossover_guard_thresholds,
                )
                execution_result = await execute_search_plan(
                    execution_plan,
                    active_cts_client,
                )
                scoring_result = await score_search_results(
                    execution_result,
                    bootstrap_artifacts.scoring_policy,
                    active_rerank_request,
                )
                branch_evaluation_draft, _ = await request_branch_evaluation_draft(
                    bootstrap_artifacts.requirement_sheet,
                    frontier_state,
                    execution_plan,
                    execution_result,
                    scoring_result,
                    model=self.branch_outcome_evaluation_model,
                )
                branch_evaluation = evaluate_branch_outcome(
                    bootstrap_artifacts.requirement_sheet,
                    frontier_state,
                    execution_plan,
                    execution_result,
                    scoring_result,
                    branch_evaluation_draft,
                )
                reward_breakdown = compute_node_reward_breakdown(
                    frontier_state,
                    execution_plan,
                    execution_result,
                    scoring_result,
                    branch_evaluation,
                )
                frontier_state_t1 = update_frontier_state(
                    frontier_state,
                    execution_plan,
                    scoring_result,
                    branch_evaluation,
                    reward_breakdown,
                )
                stop_reason, continue_flag = evaluate_stop_condition(
                    frontier_state_t1,
                    controller_decision.action,
                    branch_evaluation,
                    reward_breakdown,
                    active_assets.stop_guard_thresholds,
                    runtime_round_state,
                )
            if continue_flag:
                frontier_state = FrontierState_t.model_validate(
                    frontier_state_t1.model_dump(mode="python")
                )
                runtime_round_state = RuntimeRoundState(
                    runtime_round_index=runtime_round_state.runtime_round_index + 1
                )
                continue
            if stop_reason is None:
                raise ValueError("stop_reason must not be null when continue_flag is false")
            run_summary_draft, _ = await request_search_run_summary_draft(
                bootstrap_artifacts.requirement_sheet,
                frontier_state_t1,
                stop_reason,
                model=self.search_run_finalization_model,
            )
            return finalize_search_run(
                bootstrap_artifacts.requirement_sheet,
                frontier_state_t1,
                stop_reason,
                run_summary_draft,
            )


def _default_cts_client(settings: AppSettings) -> CTSClientProtocol:
    if settings.mock_cts:
        return MockCTSClient(settings)
    return CTSClient(settings)


def _build_http_rerank_request(settings: AppSettings) -> AsyncRerankRequest:
    async def _request(request: RerankRequest) -> RerankResponse:
        async with httpx.AsyncClient(
            base_url=settings.rerank_base_url,
            timeout=settings.rerank_timeout_seconds,
        ) as client:
            response = await client.post(
                "/api/rerank",
                json=request.model_dump(mode="json"),
            )
        if response.status_code != 200:
            raise RuntimeError(
                f"rerank_request_failed: status={response.status_code}, body={response.text}"
            )
        return RerankResponse.model_validate(response.json())

    return _request
