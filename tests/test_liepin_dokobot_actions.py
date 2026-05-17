from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json

import pytest

from seektalent.providers.liepin.dokobot_actions import (
    DokoBotActionReadiness,
    DokoBotLiepinSearchCardsExecutor,
    pi_failure_code_for_provider_state,
)
from seektalent.providers.liepin.worker_contracts import (
    LiepinCardSearchResponse,
    LiepinSafeCardSummary,
    LiepinWorkerCandidateCard,
)
from seektalent.providers.pi_agent.contracts import (
    PiAgentFailureCode,
    PiAgentResult,
    PiAgentResultStatus,
    PiArtifactRef,
    ProtectedArtifactClass,
)


def _artifact_ref(content: bytes, artifact_class: ProtectedArtifactClass, policy_id: str) -> PiArtifactRef:
    content_hash = sha256(content).hexdigest()
    return PiArtifactRef(
        artifact_class=artifact_class,
        artifact_ref=f"{artifact_class.value}:{content_hash}",
        content_sha256=content_hash,
        redaction_policy_id=policy_id
        if artifact_class in {ProtectedArtifactClass.REDACTED_EVIDENCE, ProtectedArtifactClass.SAFE_SUMMARY}
        else None,
        protection_policy_id=policy_id if artifact_class == ProtectedArtifactClass.PROTECTED_PROVIDER_SNAPSHOT else None,
    )


def _card(candidate_id: str, *, exhausted: bool = False) -> LiepinCardSearchResponse:
    return LiepinCardSearchResponse(
        cards=[
            LiepinWorkerCandidateCard(
                payload={"providerRank": int(candidate_id.rsplit("-", 1)[-1])},
                normalized_text=f"FastAPI ranking profile {candidate_id}",
                provider_subject_id=candidate_id,
                synthetic_candidate_fingerprint=f"liepin:{candidate_id}",
                identity_confidence="provider_subject_id",
                extraction_source="dom_fallback",
                extractor_version="dokobot-action-v1",
                pii_classification="no_direct_contact",
                retention_policy="provider_snapshot_7d",
                access_scope="local_run_only",
                redaction_state="redacted",
                safeCardSummary=LiepinSafeCardSummary(
                    current_or_recent_title="Backend Engineer",
                    skill_tags=("FastAPI",),
                    masked_name=True,
                ),
            )
        ],
        exhausted=exhausted,
        raw_candidate_count=1,
    )


@dataclass
class FakeActionSession:
    states: list[DokoBotActionReadiness]
    pages: list[LiepinCardSearchResponse] = field(default_factory=list)
    submitted: bool = False
    read_calls: list[dict[str, int]] = field(default_factory=list)
    traces: list[dict[str, object]] = field(default_factory=list)

    def submit_keyword_search(self, *, keyword_query: str, source_run_id: str) -> None:
        del keyword_query, source_run_id
        self.submitted = True

    def detect_provider_state(self) -> DokoBotActionReadiness:
        if self.states:
            return self.states.pop(0)
        return DokoBotActionReadiness(state="ready")

    def read_card_page(self, *, page_index: int, page_size: int, remaining_cards: int) -> LiepinCardSearchResponse:
        self.read_calls.append(
            {"page_index": page_index, "page_size": page_size, "remaining_cards": remaining_cards}
        )
        return self.pages.pop(0)

    def turn_page(self, *, page_index: int) -> None:
        del page_index

    def write_action_trace(
        self,
        *,
        source_run_id: str,
        result_code: str,
        failure_code: PiAgentFailureCode | None,
    ) -> PiAgentResult:
        self.traces.append({"source_run_id": source_run_id, "result_code": result_code, "failure_code": failure_code})
        status = {
            "ok": PiAgentResultStatus.SUCCEEDED,
            "blocked": PiAgentResultStatus.BLOCKED,
            "partial": PiAgentResultStatus.PARTIAL,
            "failed": PiAgentResultStatus.FAILED,
        }[result_code]
        return PiAgentResult(
            schema_version="pi-agent-result-v1",
            status=status,
            stop_reason=failure_code,
            action_trace_ref=_artifact_ref(
                json.dumps(self.traces[-1], sort_keys=True).encode(),
                ProtectedArtifactClass.REDACTED_EVIDENCE,
                "liepin-trace-redaction-v1",
            ),
        )


def test_ready_session_returns_typed_cards_and_safe_summaries() -> None:
    session = FakeActionSession(
        states=[DokoBotActionReadiness(state="ready"), DokoBotActionReadiness(state="ready")],
        pages=[_card("candidate-1", exhausted=True)],
    )

    result = DokoBotLiepinSearchCardsExecutor(session=session)(
        session_id="session-1",
        source_run_id="run-1",
        connection_id="connection-1",
        provider_account_lock_key="account-1",
        keyword_query="FastAPI",
        query_terms=["FastAPI"],
        max_pages=1,
        page_size=10,
        max_cards=10,
    )

    assert result.status == PiAgentResultStatus.SUCCEEDED
    assert result.card_search is not None
    assert result.card_search.cards[0].safe_card_summary is not None
    assert session.traces[-1]["result_code"] == "ok"


def test_login_required_before_safe_cards_returns_blocked_without_submitting_search() -> None:
    session = FakeActionSession(states=[DokoBotActionReadiness(state="login_required")])

    result = DokoBotLiepinSearchCardsExecutor(session=session)(
        session_id="session-1",
        source_run_id="run-1",
        connection_id="connection-1",
        provider_account_lock_key="account-1",
        keyword_query="FastAPI",
        query_terms=["FastAPI"],
        max_pages=1,
        page_size=10,
        max_cards=10,
    )

    assert result.status == PiAgentResultStatus.BLOCKED
    assert result.stop_reason == PiAgentFailureCode.LOGIN_EXPIRED
    assert result.card_search is None
    assert session.submitted is False
    assert session.traces[-1]["result_code"] == "blocked"


def test_state_change_after_collected_page_returns_partial_with_cards() -> None:
    session = FakeActionSession(
        states=[
            DokoBotActionReadiness(state="ready"),
            DokoBotActionReadiness(state="ready"),
            DokoBotActionReadiness(state="timeout"),
        ],
        pages=[_card("candidate-1")],
    )

    result = DokoBotLiepinSearchCardsExecutor(session=session)(
        session_id="session-1",
        source_run_id="run-1",
        connection_id="connection-1",
        provider_account_lock_key="account-1",
        keyword_query="FastAPI",
        query_terms=["FastAPI"],
        max_pages=2,
        page_size=10,
        max_cards=10,
    )

    assert result.status == PiAgentResultStatus.PARTIAL
    assert result.stop_reason == PiAgentFailureCode.PAGE_TIMEOUT
    assert result.card_search is not None
    assert [card.provider_subject_id for card in result.card_search.cards] == ["candidate-1"]
    assert session.traces[-1]["result_code"] == "partial"


@pytest.mark.parametrize(
    ("state", "failure_code"),
    [
        ("login_required", PiAgentFailureCode.LOGIN_EXPIRED),
        ("verification_required", PiAgentFailureCode.VERIFICATION_REQUIRED),
        ("risk_control", PiAgentFailureCode.RISK_CONTROL),
        ("unsupported_route", PiAgentFailureCode.SELECTOR_DRIFT),
        ("timeout", PiAgentFailureCode.PAGE_TIMEOUT),
        ("capability_unavailable", PiAgentFailureCode.DOKOBOT_ACTION_CAPABILITY_UNAVAILABLE),
    ],
)
def test_provider_states_map_to_distinct_pi_failure_codes(
    state: str,
    failure_code: PiAgentFailureCode,
) -> None:
    assert pi_failure_code_for_provider_state(state) == failure_code


def test_executor_respects_page_size_max_pages_and_max_cards() -> None:
    session = FakeActionSession(
        states=[
            DokoBotActionReadiness(state="ready"),
            DokoBotActionReadiness(state="ready"),
            DokoBotActionReadiness(state="ready"),
        ],
        pages=[
            LiepinCardSearchResponse(cards=[_card("candidate-1").cards[0], _card("candidate-2").cards[0]]),
            LiepinCardSearchResponse(cards=[_card("candidate-3").cards[0], _card("candidate-4").cards[0]]),
        ],
    )

    result = DokoBotLiepinSearchCardsExecutor(session=session)(
        session_id="session-1",
        source_run_id="run-1",
        connection_id="connection-1",
        provider_account_lock_key="account-1",
        keyword_query="FastAPI",
        query_terms=["FastAPI"],
        max_pages=2,
        page_size=2,
        max_cards=3,
    )

    assert result.card_search is not None
    assert [card.provider_subject_id for card in result.card_search.cards] == [
        "candidate-1",
        "candidate-2",
        "candidate-3",
    ]
    assert session.read_calls == [
        {"page_index": 1, "page_size": 2, "remaining_cards": 3},
        {"page_index": 2, "page_size": 2, "remaining_cards": 1},
    ]
