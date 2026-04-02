from __future__ import annotations

import asyncio
from time import perf_counter

from pydantic_ai import Agent

from cv_match.config import AppSettings
from cv_match.llm import build_model, build_model_settings, build_output_spec
from cv_match.models import (
    ScoredCandidate,
    ScoringFailure,
    ScoringContext,
)
from cv_match.prompting import LoadedPrompt, json_block


class ResumeScorer:
    def __init__(self, settings: AppSettings, prompt: LoadedPrompt) -> None:
        self.settings = settings
        self.prompt = prompt
        self.agent: Agent[None, ScoredCandidate] | None = None

    def _get_agent(self) -> Agent[None, ScoredCandidate]:
        if self.agent is None:
            model = build_model(self.settings.scoring_model)
            self.agent = Agent(
                model=model,
                output_type=build_output_spec(self.settings.scoring_model, model, ScoredCandidate),
                system_prompt=self.prompt.content,
                model_settings=build_model_settings(self.settings, self.settings.scoring_model),
                retries=0,
                output_retries=1,
            )
        return self.agent

    def score_candidates_parallel(
        self,
        *,
        contexts: list[ScoringContext],
        tracer: object,
    ) -> tuple[list[ScoredCandidate], list[ScoringFailure]]:
        return asyncio.run(
            self._score_candidates_parallel(
                contexts=contexts,
                tracer=tracer,
            )
        )

    async def _score_candidates_parallel(
        self,
        *,
        contexts: list[ScoringContext],
        tracer: object,
    ) -> tuple[list[ScoredCandidate], list[ScoringFailure]]:
        semaphore = asyncio.Semaphore(self.settings.scoring_max_concurrency)
        scored: list[ScoredCandidate] = []
        failures: list[ScoringFailure] = []

        async def worker(index: int, context: ScoringContext) -> None:
            candidate = context.normalized_resume
            branch_id = f"r{context.round_no}-b{index + 1}-{candidate.resume_id}"
            tracer.emit(
                "score_branch_started",
                round_no=context.round_no,
                resume_id=candidate.resume_id,
                branch_id=branch_id,
                model=self.settings.scoring_model,
                summary=candidate.compact_summary(),
            )
            async with semaphore:
                result, failure = await self._score_one(
                    context=context,
                    branch_id=branch_id,
                    tracer=tracer,
                )
            if result is not None:
                scored.append(result)
            if failure is not None:
                failures.append(failure)

        await asyncio.gather(*(worker(index, context) for index, context in enumerate(contexts)))
        return scored, failures

    async def _score_one(
        self,
        *,
        context: ScoringContext,
        branch_id: str,
        tracer: object,
    ) -> tuple[ScoredCandidate | None, ScoringFailure | None]:
        candidate = context.normalized_resume
        started_at = perf_counter()
        try:
            result = await self._score_one_live(context=context)
            result = result.model_copy(
                update={
                    "resume_id": candidate.resume_id,
                    "source_round": candidate.source_round or context.round_no,
                }
            )
            latency_ms = max(1, int((perf_counter() - started_at) * 1000))
            tracer.emit(
                "score_branch_completed",
                round_no=context.round_no,
                resume_id=candidate.resume_id,
                branch_id=branch_id,
                model=self.settings.scoring_model,
                latency_ms=latency_ms,
                summary=result.reasoning_summary,
                payload={
                    "fit_bucket": result.fit_bucket,
                    "overall_score": result.overall_score,
                    "risk_score": result.risk_score,
                    "confidence": result.confidence,
                    "reasoning_summary": result.reasoning_summary,
                    "missing_must_haves": result.missing_must_haves,
                    "negative_signals": result.negative_signals,
                    "risk_flags": result.risk_flags,
                },
            )
            return result, None
        except Exception as exc:  # noqa: BLE001
            latency_ms = max(1, int((perf_counter() - started_at) * 1000))
            failure = ScoringFailure(
                resume_id=candidate.resume_id,
                branch_id=branch_id,
                round_no=context.round_no,
                attempts=1,
                error_message=str(exc),
                latency_ms=latency_ms,
            )
            tracer.emit(
                "score_branch_failed",
                round_no=context.round_no,
                resume_id=candidate.resume_id,
                branch_id=branch_id,
                model=self.settings.scoring_model,
                latency_ms=latency_ms,
                summary=str(exc),
                payload={"attempts": 1},
            )
            return None, failure

    async def _score_one_live(
        self,
        *,
        context: ScoringContext,
    ) -> ScoredCandidate:
        prompt = "\n\n".join(
            [
                json_block("SCORING_CONTEXT", context.model_dump(mode="json")),
                json_block("CALL_METADATA", {"attempt": 1}),
            ]
        )
        result = await self._get_agent().run(prompt)
        return result.output
