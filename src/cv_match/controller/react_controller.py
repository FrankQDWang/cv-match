from __future__ import annotations

import asyncio

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings

from cv_match.config import AppSettings
from cv_match.controller.strategy_bootstrap import build_cts_query_from_strategy
from cv_match.models import ControllerDecision, ControllerStateView
from cv_match.prompting import LoadedPrompt, json_block


class ReActController:
    def __init__(self, settings: AppSettings, prompt: LoadedPrompt) -> None:
        self.settings = settings
        self.prompt = prompt
        self.use_mock_backend = settings.llm_backend_mode != "openai-responses"
        self.agent: Agent[None, ControllerDecision] | None = None
        if not self.use_mock_backend:
            self.agent = Agent(
                model=OpenAIResponsesModel(settings.strategy_model),
                output_type=ControllerDecision,
                system_prompt=prompt.content,
                model_settings=OpenAIResponsesModelSettings(
                    openai_reasoning_effort=settings.reasoning_effort,
                    openai_reasoning_summary="concise",
                    openai_text_verbosity="low",
                ),
            )

    def decide(self, *, state_view: ControllerStateView) -> ControllerDecision:
        if self.use_mock_backend:
            return self._decide_mock(state_view=state_view)
        try:
            return asyncio.run(self._decide_live(state_view=state_view))
        except Exception:
            fallback = self._decide_mock(state_view=state_view)
            return fallback.model_copy(
                update={
                    "thought_summary": f"[runtime fallback] {fallback.thought_summary}",
                    "decision_rationale": (
                        f"Live controller failed; deterministic fallback used. {fallback.decision_rationale}"
                    ),
                }
            )

    async def _decide_live(self, *, state_view: ControllerStateView) -> ControllerDecision:
        assert self.agent is not None
        result = await asyncio.wait_for(
            self.agent.run(json_block("STATE_VIEW", state_view.model_dump(mode="json"))),
            timeout=90,
        )
        return result.output

    def _decide_mock(self, *, state_view: ControllerStateView) -> ControllerDecision:
        fit_count = sum(1 for item in state_view.current_top_pool if item.fit_bucket == "fit")
        if state_view.round_no > state_view.min_rounds and fit_count >= 5:
            return ControllerDecision(
                thought_summary="Top pool already contains enough fit candidates.",
                action="stop",
                decision_rationale="Current pool has at least five fit resumes, so more retrieval is low value.",
                working_strategy=state_view.current_strategy,
                stop_reason="enough_high_fit_candidates",
            )
        if state_view.round_no > state_view.min_rounds and state_view.consecutive_shortage_rounds >= 2:
            return ControllerDecision(
                thought_summary="Recent rounds produced sustained shortage after refill.",
                action="stop",
                decision_rationale="Repeated exhausted retrieval suggests low incremental recall from the current search surface.",
                working_strategy=state_view.current_strategy,
                stop_reason="insufficient_new_candidates",
            )

        query = build_cts_query_from_strategy(
            strategy=state_view.current_strategy,
            target_new=state_view.target_new,
            exclude_ids=[],
        )
        return ControllerDecision(
            thought_summary="Continue retrieval with the current structured search strategy.",
            action="search_cts",
            decision_rationale="Need more candidates before finalizing the pool.",
            working_strategy=state_view.current_strategy,
            cts_query=query,
        )
