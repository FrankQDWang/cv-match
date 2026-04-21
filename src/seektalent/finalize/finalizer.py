from __future__ import annotations

from typing import cast

from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import ModelRetry

from seektalent.config import AppSettings
from seektalent.llm import build_model, build_model_settings, build_output_spec
from seektalent.models import FinalCandidate, FinalResult, FinalResultDraft, FinalizeContext, ScoredCandidate
from seektalent.prompting import LoadedPrompt, json_block


class Finalizer:
    def __init__(self, settings: AppSettings, prompt: LoadedPrompt) -> None:
        self.settings = settings
        self.prompt = prompt
        self.last_validator_retry_count = 0
        self.last_draft_output: FinalResultDraft | None = None

    def _get_agent(self) -> Agent[FinalizeContext, FinalResultDraft]:
        model = build_model(self.settings.finalize_model)
        agent = cast(
            Agent[FinalizeContext, FinalResultDraft],
            Agent(
                model=model,
                output_type=build_output_spec(self.settings.finalize_model, model, FinalResultDraft),
                system_prompt=self.prompt.content,
                deps_type=FinalizeContext,
                model_settings=build_model_settings(self.settings, self.settings.finalize_model),
                retries=0,
                output_retries=2,
            ),
        )

        @agent.output_validator
        def validate_output(
            ctx: RunContext[FinalizeContext],
            output: FinalResultDraft,
        ) -> FinalResultDraft:
            allowed_ids = {candidate.resume_id for candidate in ctx.deps.top_candidates}
            expected_ids = [candidate.resume_id for candidate in ctx.deps.top_candidates]
            actual_ids: list[str] = []
            seen: set[str] = set()
            for candidate in output.candidates:
                if candidate.resume_id not in allowed_ids:
                    self.last_validator_retry_count += 1
                    raise ModelRetry(f"Unknown resume_id {candidate.resume_id!r} in final candidates.")
                if candidate.resume_id in seen:
                    self.last_validator_retry_count += 1
                    raise ModelRetry(f"Duplicate resume_id {candidate.resume_id!r} in final candidates.")
                seen.add(candidate.resume_id)
                actual_ids.append(candidate.resume_id)
            if len(actual_ids) != len(expected_ids):
                self.last_validator_retry_count += 1
                raise ModelRetry("Final candidates count must equal runtime top candidate count.")
            if actual_ids != expected_ids:
                self.last_validator_retry_count += 1
                raise ModelRetry("Final candidates must preserve runtime ranking order.")
            return output

        return agent

    async def finalize(
        self,
        *,
        run_id: str,
        run_dir: str,
        rounds_executed: int,
        stop_reason: str,
        ranked_candidates: list[ScoredCandidate],
    ) -> FinalResult:
        self.last_validator_retry_count = 0
        self.last_draft_output = None
        deps = FinalizeContext(
            run_id=run_id,
            run_dir=run_dir,
            rounds_executed=rounds_executed,
            stop_reason=stop_reason,
            top_candidates=ranked_candidates,
        )
        payload = {
            "run_id": run_id,
            "run_dir": run_dir,
            "rounds_executed": rounds_executed,
            "stop_reason": stop_reason,
            "ranked_candidates": [item.model_dump(mode="json") for item in ranked_candidates],
        }
        result = await self._get_agent().run(
            json_block("FINALIZATION_CONTEXT", payload),
            deps=deps,
        )
        self.last_draft_output = result.output
        return _materialize_final_result(
            draft=result.output,
            run_id=run_id,
            run_dir=run_dir,
            rounds_executed=rounds_executed,
            stop_reason=stop_reason,
            ranked_candidates=ranked_candidates,
        )


def _materialize_final_result(
    *,
    draft: FinalResultDraft,
    run_id: str,
    run_dir: str,
    rounds_executed: int,
    stop_reason: str,
    ranked_candidates: list[ScoredCandidate],
) -> FinalResult:
    candidates = [
        FinalCandidate(
            resume_id=source.resume_id,
            rank=rank,
            final_score=source.overall_score,
            fit_bucket=source.fit_bucket,
            match_summary=draft_candidate.match_summary,
            strengths=source.strengths,
            weaknesses=source.weaknesses,
            matched_must_haves=source.matched_must_haves,
            matched_preferences=source.matched_preferences,
            risk_flags=source.risk_flags,
            why_selected=draft_candidate.why_selected,
            source_round=source.source_round,
        )
        for rank, (source, draft_candidate) in enumerate(zip(ranked_candidates, draft.candidates, strict=True), start=1)
    ]
    return FinalResult(
        run_id=run_id,
        run_dir=run_dir,
        rounds_executed=rounds_executed,
        stop_reason=stop_reason,
        candidates=candidates,
        summary=draft.summary,
    )
