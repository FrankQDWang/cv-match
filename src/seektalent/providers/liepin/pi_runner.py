from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, Protocol

from seektalent.providers.liepin.pi_skills import get_liepin_pi_skill
from seektalent.providers.pi_agent.capabilities import DokoBotCapabilities
from seektalent.providers.pi_agent.contracts import (
    PiAgentActionTraceEntry,
    PiAgentActionType,
    PiAgentCompletionReason,
    PiAgentFailureCode,
    PiAgentResult,
    PiAgentResultStatus,
    PiArtifactRef,
    PiBackendMode,
    PiAgentTaskType,
    ProtectedArtifactClass,
)
from seektalent.providers.liepin.worker_contracts import LiepinCardSearchResponse
from seektalent.providers.pi_agent.locks import InMemoryPiConnectionLock


TraceArtifactWriter = Callable[[bytes, ProtectedArtifactClass, str], PiArtifactRef]
SEARCH_CARDS_SKILL_ID = get_liepin_pi_skill(PiAgentTaskType.LIEPIN_SEARCH_CARDS).skill_id


@dataclass(frozen=True, kw_only=True)
class LiepinPiCardSearchResult:
    pi_result: PiAgentResult
    card_search: LiepinCardSearchResponse | None = None

    def __post_init__(self) -> None:
        if self.pi_result.status == PiAgentResultStatus.SUCCEEDED and self.card_search is None:
            raise ValueError("card_search is required for successful Liepin PI card search")

    @property
    def status(self) -> PiAgentResultStatus:
        return self.pi_result.status

    @property
    def stop_reason(self) -> PiAgentFailureCode | PiAgentCompletionReason | None:
        return self.pi_result.stop_reason

    @property
    def action_trace_ref(self) -> PiArtifactRef:
        return self.pi_result.action_trace_ref


class SearchCardsExecutor(Protocol):
    def __call__(
        self,
        *,
        session_id: str,
        source_run_id: str,
        connection_id: str,
        provider_account_lock_key: str,
        keyword_query: str,
        query_terms: list[str],
        max_pages: int,
        page_size: int,
        max_cards: int,
    ) -> LiepinPiCardSearchResult: ...


@dataclass
class LiepinPiRunner:
    backend_mode: PiBackendMode
    dokobot_capabilities: DokoBotCapabilities | None
    connection_lock: InMemoryPiConnectionLock
    trace_artifact_writer: TraceArtifactWriter
    dokobot_search_cards: SearchCardsExecutor | None = None
    legacy_search_cards: SearchCardsExecutor | None = None

    def search_cards(
        self,
        *,
        session_id: str,
        source_run_id: str,
        connection_id: str,
        provider_account_lock_key: str,
        keyword_query: str,
        query_terms: list[str],
        max_pages: int,
        page_size: int,
        max_cards: int,
    ) -> LiepinPiCardSearchResult:
        if not self.connection_lock.acquire(
            connection_id=connection_id,
            provider_account_lock_key=provider_account_lock_key,
            source_run_id=source_run_id,
        ):
            return self._blocked_result(
                source_run_id=source_run_id,
                connection_id=connection_id,
                failure_code=PiAgentFailureCode.PROVIDER_CONNECTION_LOCKED,
            )

        try:
            return self._search_cards_locked(
                session_id=session_id,
                source_run_id=source_run_id,
                connection_id=connection_id,
                provider_account_lock_key=provider_account_lock_key,
                keyword_query=keyword_query,
                query_terms=query_terms,
                max_pages=max_pages,
                page_size=page_size,
                max_cards=max_cards,
            )
        finally:
            self.connection_lock.release(
                connection_id=connection_id,
                provider_account_lock_key=provider_account_lock_key,
                source_run_id=source_run_id,
            )

    def _search_cards_locked(
        self,
        *,
        session_id: str,
        source_run_id: str,
        connection_id: str,
        provider_account_lock_key: str,
        keyword_query: str,
        query_terms: list[str],
        max_pages: int,
        page_size: int,
        max_cards: int,
    ) -> LiepinPiCardSearchResult:
        if self.backend_mode in {PiBackendMode.DISABLED, PiBackendMode.DOKOBOT_READ_ONLY}:
            return self._blocked_result(
                source_run_id=source_run_id,
                connection_id=connection_id,
                failure_code=PiAgentFailureCode.DOKOBOT_ACTION_CAPABILITY_UNAVAILABLE,
            )
        if self.backend_mode == PiBackendMode.DOKOBOT_ACTION:
            capabilities = self.dokobot_capabilities
            if capabilities is None or not capabilities.can_execute_liepin_actions:
                return self._blocked_result(
                    source_run_id=source_run_id,
                    connection_id=connection_id,
                    failure_code=PiAgentFailureCode.DOKOBOT_ACTION_CAPABILITY_UNAVAILABLE,
                )
            if self.dokobot_search_cards is None:
                raise RuntimeError("DokoBot action mode requires an explicit action executor")
            return self.dokobot_search_cards(
                session_id=session_id,
                source_run_id=source_run_id,
                connection_id=connection_id,
                provider_account_lock_key=provider_account_lock_key,
                keyword_query=keyword_query,
                query_terms=query_terms,
                max_pages=max_pages,
                page_size=page_size,
                max_cards=max_cards,
            )
        if self.backend_mode == PiBackendMode.LEGACY_WORKER_COMPAT:
            if self.legacy_search_cards is None:
                return self._blocked_result(
                    source_run_id=source_run_id,
                    connection_id=connection_id,
                    failure_code=PiAgentFailureCode.DOKOBOT_ACTION_CAPABILITY_UNAVAILABLE,
                )
            return self.legacy_search_cards(
                session_id=session_id,
                source_run_id=source_run_id,
                connection_id=connection_id,
                provider_account_lock_key=provider_account_lock_key,
                keyword_query=keyword_query,
                query_terms=query_terms,
                max_pages=max_pages,
                page_size=page_size,
                max_cards=max_cards,
            )
        if self.backend_mode == PiBackendMode.FAKE_FIXTURE:
            return LiepinPiCardSearchResult(
                pi_result=PiAgentResult(
                    schema_version="pi-agent-result-v1",
                    status=PiAgentResultStatus.SUCCEEDED,
                    action_trace_ref=self._write_trace(
                        source_run_id=source_run_id,
                        connection_id=connection_id,
                        result_code="ok",
                        failure_code=None,
                    ),
                ),
                card_search=LiepinCardSearchResponse(cards=[], exhausted=True, raw_candidate_count=0),
            )
        raise ValueError(f"unsupported PI backend mode: {self.backend_mode}")

    def _blocked_result(
        self,
        *,
        source_run_id: str,
        connection_id: str,
        failure_code: PiAgentFailureCode,
    ) -> LiepinPiCardSearchResult:
        return LiepinPiCardSearchResult(
            pi_result=PiAgentResult(
                schema_version="pi-agent-result-v1",
                status=PiAgentResultStatus.BLOCKED,
                stop_reason=failure_code,
                action_trace_ref=self._write_trace(
                    source_run_id=source_run_id,
                    connection_id=connection_id,
                    result_code="blocked",
                    failure_code=failure_code,
                ),
            ),
        )

    def _write_trace(
        self,
        *,
        source_run_id: str,
        connection_id: str,
        result_code: Literal["ok", "blocked", "failed", "partial"],
        failure_code: PiAgentFailureCode | None,
    ) -> PiArtifactRef:
        trace = PiAgentActionTraceEntry(
            schema_version="pi-agent-action-trace-v1",
            timestamp=datetime.now(UTC),
            provider_skill_id=SEARCH_CARDS_SKILL_ID,
            interaction_id=f"{source_run_id}:search_cards:1",
            source_run_id=source_run_id,
            connection_id=connection_id,
            action_sequence=1,
            action_type=PiAgentActionType.LIEPIN_SUBMIT_KEYWORD_SEARCH,
            backend_mode=self.backend_mode,
            capability_version=_capability_version(self.dokobot_capabilities),
            safe_target_descriptor="liepin keyword search",
            result_code=result_code,
            duration_ms=0,
            retry_count=0,
            redaction_policy_id="liepin-trace-redaction-v1",
            failure_code=failure_code,
        )
        return self.trace_artifact_writer(
            json.dumps(trace.model_dump(mode="json"), sort_keys=True).encode("utf-8"),
            ProtectedArtifactClass.REDACTED_EVIDENCE,
            "liepin-trace-redaction-v1",
        )


def _capability_version(capabilities: DokoBotCapabilities | None) -> str:
    if capabilities is None:
        return "none"
    if capabilities.action_manifest_id and capabilities.action_manifest_version:
        return f"{capabilities.action_manifest_id}@{capabilities.action_manifest_version}"
    return capabilities.cli_version or "unknown"
