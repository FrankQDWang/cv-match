from __future__ import annotations

import asyncio
from typing import Protocol

from seektalent.core.retrieval.provider_contract import SearchRequest, SearchResult
from seektalent.providers.liepin.client import liepin_card_search_response_to_search_result
from seektalent.providers.liepin.pi_runner import LiepinPiRunner
from seektalent.providers.liepin.worker_contracts import (
    LiepinDetailOpenRequest,
    LiepinDetailOpenResponse,
    LiepinWorkerModeError,
    LiepinWorkerPartialSearchError,
    LoginHandoff,
    LoginRelayCompleteResult,
    LoginRelayInputResult,
    LoginRelaySnapshot,
    SessionStatus,
)
from seektalent.providers.pi_agent.contracts import PiAgentFailureCode, PiAgentResultStatus


class PiWorkerSessionProbe(Protocol):
    def session_status(
        self,
        *,
        connection_id: str,
        tenant: str | None = None,
        workspace: str | None = None,
        provider_account_hash: str | None = None,
    ) -> SessionStatus: ...

    def login_handoff(
        self,
        *,
        connection_id: str,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        provider_account_hash: str | None = None,
    ) -> LoginHandoff: ...

    def complete_login_relay(self, *, connection_id: str) -> LoginRelayCompleteResult: ...


class LiepinPiWorkerClient:
    def __init__(
        self,
        runner: LiepinPiRunner,
        *,
        session_id: str,
        connection_id: str,
        provider_account_lock_key: str,
        session_probe: PiWorkerSessionProbe | None = None,
    ) -> None:
        self._runner = runner
        self._session_id = session_id
        self._connection_id = connection_id
        self._provider_account_lock_key = provider_account_lock_key
        self._session_probe = session_probe

    async def ensure_ready(self, *, on_event=None) -> None:
        del on_event

    async def search(
        self,
        request: SearchRequest,
        *,
        round_no: int,
        trace_id: str,
        provider_account_hash: str | None = None,
    ) -> SearchResult:
        del round_no
        connection_id = _context_string(request.provider_context.get("liepin_connection_id")) or self._connection_id
        lock_key = (
            _context_string(request.provider_context.get("liepin_provider_account_hash"))
            or provider_account_hash
            or self._provider_account_lock_key
        )
        result = await asyncio.to_thread(
            self._runner.search_cards,
            session_id=self._session_id,
            source_run_id=trace_id,
            connection_id=connection_id,
            provider_account_lock_key=lock_key,
            keyword_query=request.keyword_query or " ".join(request.query_terms),
            query_terms=list(request.query_terms),
            max_pages=_positive_int(request.provider_context.get("liepin_max_pages"), default=1),
            page_size=request.page_size,
            max_cards=_positive_int(request.provider_context.get("liepin_max_cards"), default=request.page_size),
        )
        if result.status == PiAgentResultStatus.SUCCEEDED and result.card_search is not None:
            return liepin_card_search_response_to_search_result(result.card_search)
        if result.status == PiAgentResultStatus.PARTIAL and result.card_search is not None:
            partial_search = liepin_card_search_response_to_search_result(result.card_search)
            raise LiepinWorkerPartialSearchError(
                "Liepin PI card search returned partial cards.",
                code=_worker_error_code_from_pi_stop_reason(result.stop_reason),
                partial_search_result=partial_search,
                cards_collected=len(partial_search.candidates),
            )
        raise LiepinWorkerModeError(
            "Liepin PI card search blocked.",
            code=_worker_error_code_from_pi_stop_reason(result.stop_reason),
        )

    async def session_status(
        self,
        *,
        connection_id: str,
        tenant: str | None = None,
        workspace: str | None = None,
        provider_account_hash: str | None = None,
    ) -> SessionStatus:
        probe = self._require_session_probe()
        try:
            status = await asyncio.to_thread(
                probe.session_status,
                connection_id=connection_id,
                tenant=tenant,
                workspace=workspace,
                provider_account_hash=provider_account_hash,
            )
        except Exception as exc:
            raise LiepinWorkerModeError(
                "Liepin PI worker session probe is unavailable.",
                code="dokobot_action_capability_unavailable",
            ) from exc
        if status.status == "ready":
            if not status.provider_account_hash:
                return SessionStatus(connectionId=connection_id, status="login_required", providerAccountHash=None)
            if provider_account_hash is not None and status.provider_account_hash != provider_account_hash:
                return SessionStatus(connectionId=connection_id, status="login_required", providerAccountHash=None)
        return status

    async def login_handoff(
        self,
        *,
        connection_id: str,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        provider_account_hash: str | None = None,
    ) -> LoginHandoff:
        probe = self._require_session_probe()
        try:
            return await asyncio.to_thread(
                probe.login_handoff,
                connection_id=connection_id,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                provider_account_hash=provider_account_hash,
            )
        except Exception as exc:
            raise LiepinWorkerModeError(
                "Liepin PI worker login handoff is unavailable.",
                code="dokobot_action_capability_unavailable",
            ) from exc

    async def complete_login_relay(self, *, connection_id: str) -> LoginRelayCompleteResult:
        probe = self._require_session_probe()
        try:
            return await asyncio.to_thread(probe.complete_login_relay, connection_id=connection_id)
        except Exception as exc:
            raise LiepinWorkerModeError(
                "Liepin PI worker login relay is unavailable.",
                code="dokobot_action_capability_unavailable",
            ) from exc

    async def login_relay_snapshot(self, *, connection_id: str) -> LoginRelaySnapshot:
        del connection_id
        raise LiepinWorkerModeError("Liepin PI worker client does not expose frame login snapshots.")

    async def submit_login_relay_input(
        self,
        *,
        connection_id: str,
        action: str,
        x: float | None = None,
        y: float | None = None,
        text: str | None = None,
        key: str | None = None,
    ) -> LoginRelayInputResult:
        del connection_id, action, x, y, text, key
        raise LiepinWorkerModeError("Liepin PI worker client does not accept frame login input.")

    async def open_details(self, request: LiepinDetailOpenRequest) -> LiepinDetailOpenResponse:
        del request
        raise LiepinWorkerModeError("Liepin PI worker client does not open detail pages through card search.")

    def _require_session_probe(self) -> PiWorkerSessionProbe:
        if self._session_probe is None:
            raise LiepinWorkerModeError("Liepin PI worker session probe is not configured.", code="session_probe_missing")
        return self._session_probe


def _worker_error_code_from_pi_stop_reason(stop_reason: object) -> str:
    if isinstance(stop_reason, PiAgentFailureCode):
        return stop_reason.value
    return "failed_provider_error"


def _positive_int(value: object, *, default: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _context_string(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None
