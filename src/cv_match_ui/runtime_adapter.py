from __future__ import annotations

from cv_match.config import AppSettings
from cv_match.models import NormalizedResume, ResumeCandidate
from cv_match.runtime import WorkflowRuntime
from cv_match.tracing import RunTracer


class UiWorkflowRuntime(WorkflowRuntime):
    def __init__(self, settings: AppSettings) -> None:
        super().__init__(settings)
        self.candidate_store: dict[str, ResumeCandidate] = {}
        self.normalized_store: dict[str, NormalizedResume] = {}

    def _execute_search_tool(
        self,
        *,
        round_no: int,
        query,
        target_new: int,
        seen_resume_ids: set[str],
        seen_dedup_keys: set[str],
        tracer: RunTracer,
    ):
        new_candidates, search_observation, attempts, duplicate_count = super()._execute_search_tool(
            round_no=round_no,
            query=query,
            target_new=target_new,
            seen_resume_ids=seen_resume_ids,
            seen_dedup_keys=seen_dedup_keys,
            tracer=tracer,
        )
        for candidate in new_candidates:
            self.candidate_store[candidate.resume_id] = candidate
        return new_candidates, search_observation, attempts, duplicate_count

    def _normalize_scoring_pool(
        self,
        *,
        round_no: int,
        scoring_pool: list[ResumeCandidate],
        tracer: RunTracer,
        normalized_store: dict[str, NormalizedResume],
    ) -> list[NormalizedResume]:
        normalized = super()._normalize_scoring_pool(
            round_no=round_no,
            scoring_pool=scoring_pool,
            tracer=tracer,
            normalized_store=normalized_store,
        )
        for item in normalized:
            self.normalized_store[item.resume_id] = item
        return normalized
