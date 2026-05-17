from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from seektalent.providers.liepin.pi_runner import LiepinPiCardSearchResult
from seektalent.providers.liepin.worker_contracts import LiepinCardSearchResponse
from seektalent.providers.pi_agent.contracts import PiAgentFailureCode, PiAgentResult


DokoBotActionProviderState = Literal[
    "ready",
    "login_required",
    "verification_required",
    "risk_control",
    "unsupported_route",
    "timeout",
    "capability_unavailable",
]


@dataclass(frozen=True, kw_only=True)
class DokoBotActionReadiness:
    state: DokoBotActionProviderState
    failure_code: PiAgentFailureCode | None = None

    @property
    def is_ready(self) -> bool:
        return self.state == "ready"


def pi_failure_code_for_provider_state(state: DokoBotActionProviderState) -> PiAgentFailureCode:
    if state == "login_required":
        return PiAgentFailureCode.LOGIN_EXPIRED
    if state == "verification_required":
        return PiAgentFailureCode.VERIFICATION_REQUIRED
    if state == "risk_control":
        return PiAgentFailureCode.RISK_CONTROL
    if state == "unsupported_route":
        return PiAgentFailureCode.SELECTOR_DRIFT
    if state == "timeout":
        return PiAgentFailureCode.PAGE_TIMEOUT
    if state == "capability_unavailable":
        return PiAgentFailureCode.DOKOBOT_ACTION_CAPABILITY_UNAVAILABLE
    raise ValueError(f"ready provider state has no failure code: {state}")


class DokoBotLiepinActionSession(Protocol):
    def submit_keyword_search(self, *, keyword_query: str, source_run_id: str) -> None: ...

    def read_card_page(self, *, page_index: int, page_size: int, remaining_cards: int) -> LiepinCardSearchResponse: ...

    def turn_page(self, *, page_index: int) -> None: ...

    def detect_provider_state(self) -> DokoBotActionReadiness: ...

    def write_action_trace(
        self,
        *,
        source_run_id: str,
        result_code: str,
        failure_code: PiAgentFailureCode | None,
    ) -> PiAgentResult: ...


@dataclass(frozen=True, kw_only=True)
class DokoBotLiepinSearchCardsExecutor:
    session: DokoBotLiepinActionSession

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
    ) -> LiepinPiCardSearchResult:
        del session_id, connection_id, provider_account_lock_key, query_terms
        initial_state = self.session.detect_provider_state()
        if not initial_state.is_ready:
            return self._blocked(source_run_id=source_run_id, provider_state=initial_state)

        remaining_cards = max_cards
        pages: list[LiepinCardSearchResponse] = []
        self.session.submit_keyword_search(keyword_query=keyword_query, source_run_id=source_run_id)
        for page_index in range(1, max_pages + 1):
            if page_index > 1:
                self.session.turn_page(page_index=page_index)
            provider_state = self.session.detect_provider_state()
            if not provider_state.is_ready:
                return self._blocked_or_partial(
                    source_run_id=source_run_id,
                    provider_state=provider_state,
                    pages=pages,
                    max_cards=max_cards,
                )
            page = self.session.read_card_page(
                page_index=page_index,
                page_size=page_size,
                remaining_cards=remaining_cards,
            )
            pages.append(page)
            remaining_cards -= len(page.cards)
            if remaining_cards <= 0 or page.exhausted:
                break

        cards = merge_liepin_card_pages(pages, max_cards=max_cards)
        return LiepinPiCardSearchResult(
            pi_result=self.session.write_action_trace(
                source_run_id=source_run_id,
                result_code="ok",
                failure_code=None,
            ),
            card_search=cards,
        )

    def _blocked(
        self,
        *,
        source_run_id: str,
        provider_state: DokoBotActionReadiness,
    ) -> LiepinPiCardSearchResult:
        failure_code = provider_state.failure_code or pi_failure_code_for_provider_state(provider_state.state)
        return LiepinPiCardSearchResult(
            pi_result=self.session.write_action_trace(
                source_run_id=source_run_id,
                result_code="blocked",
                failure_code=failure_code,
            )
        )

    def _blocked_or_partial(
        self,
        *,
        source_run_id: str,
        provider_state: DokoBotActionReadiness,
        pages: list[LiepinCardSearchResponse],
        max_cards: int,
    ) -> LiepinPiCardSearchResult:
        failure_code = provider_state.failure_code or pi_failure_code_for_provider_state(provider_state.state)
        if any(page.cards for page in pages):
            return LiepinPiCardSearchResult(
                pi_result=self.session.write_action_trace(
                    source_run_id=source_run_id,
                    result_code="partial",
                    failure_code=failure_code,
                ),
                card_search=merge_liepin_card_pages(pages, max_cards=max_cards),
            )
        return LiepinPiCardSearchResult(
            pi_result=self.session.write_action_trace(
                source_run_id=source_run_id,
                result_code="blocked",
                failure_code=failure_code,
            )
        )


def merge_liepin_card_pages(
    pages: list[LiepinCardSearchResponse],
    *,
    max_cards: int,
) -> LiepinCardSearchResponse:
    cards = []
    diagnostics: list[str] = []
    raw_candidate_count = 0
    for page in pages:
        diagnostics.extend(page.diagnostics)
        raw_candidate_count += page.raw_candidate_count if page.raw_candidate_count is not None else len(page.cards)
        for card in page.cards:
            if len(cards) >= max_cards:
                break
            if card.safe_card_summary is None:
                raise ValueError("DokoBot action cards must include safeCardSummary")
            cards.append(card)
    exhausted = bool(pages and pages[-1].exhausted and len(cards) < max_cards)
    next_cursor = pages[-1].next_cursor if pages else None
    return LiepinCardSearchResponse(
        cards=cards,
        diagnostics=diagnostics,
        exhausted=exhausted,
        nextCursor=next_cursor,
        requestPayload={},
        rawCandidateCount=raw_candidate_count,
    )
