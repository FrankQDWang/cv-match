from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from seektalent.config import AppSettings
from seektalent.core.retrieval.provider_contract import SearchResult
from seektalent.core.retrieval.service import RetrievalService
from seektalent.models import CTSQuery, QueryRole, RuntimeConstraint
from seektalent.tracing import RunTracer


def _provider_query_role(query_role: QueryRole) -> Literal["primary", "expansion"]:
    if query_role == "exploit":
        return "primary"
    return "expansion"


@dataclass(frozen=True)
class RetrievalRuntime:
    settings: AppSettings
    retrieval_service: RetrievalService

    async def search_once(
        self,
        *,
        attempt_query: CTSQuery,
        runtime_constraints: list[RuntimeConstraint],
        round_no: int,
        attempt_no: int,
        tracer: RunTracer,
    ) -> SearchResult:
        return await self.retrieval_service.search(
            query_terms=attempt_query.query_terms,
            query_role=_provider_query_role(attempt_query.query_role),
            keyword_query=attempt_query.keyword_query,
            adapter_notes=attempt_query.adapter_notes,
            provider_filters=attempt_query.native_filters,
            runtime_constraints=runtime_constraints,
            page_size=attempt_query.page_size,
            round_no=round_no,
            trace_id=f"{tracer.run_id}-r{round_no}-a{attempt_no}",
            cursor=str(attempt_query.page),
        )
