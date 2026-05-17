from __future__ import annotations

import asyncio
from hashlib import sha256
import json
import threading
from types import SimpleNamespace

import pytest

from seektalent.core.retrieval.provider_contract import SearchRequest
from seektalent.providers.liepin.pi_runner import LiepinPiCardSearchResult
from seektalent.providers.liepin.pi_worker_client import LiepinPiWorkerClient
from seektalent.providers.liepin.worker_contracts import (
    LiepinCardSearchResponse,
    LiepinWorkerCandidateCard,
    LiepinWorkerModeError,
    LiepinWorkerPartialSearchError,
    LoginRelayCompleteResult,
    SessionStatus,
)
from seektalent.providers.pi_agent.contracts import (
    PiAgentFailureCode,
    PiAgentResult,
    PiAgentResultStatus,
    PiArtifactRef,
    ProtectedArtifactClass,
)


def _request() -> SearchRequest:
    return SearchRequest(
        query_terms=["python"],
        query_role="primary",
        keyword_query="python",
        adapter_notes=[],
        runtime_constraints=[],
        fetch_mode="summary",
        page_size=10,
        provider_context={"liepin_max_pages": "2", "liepin_max_cards": "15"},
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


def _pi_result(status: PiAgentResultStatus, *, stop_reason: PiAgentFailureCode | None = None) -> PiAgentResult:
    return PiAgentResult(
        schema_version="pi-agent-result-v1",
        status=status,
        stop_reason=stop_reason,
        action_trace_ref=_artifact_ref(
            json.dumps({"status": status, "stop_reason": stop_reason}, sort_keys=True).encode(),
            ProtectedArtifactClass.REDACTED_EVIDENCE,
            "liepin-trace-redaction-v1",
        ),
    )


def _card_response(candidate_id: str = "candidate-1") -> LiepinCardSearchResponse:
    return LiepinCardSearchResponse(
        cards=[
            LiepinWorkerCandidateCard(
                payload={"providerRank": 1},
                normalized_text="Python Engineer",
                provider_subject_id=candidate_id,
                provider_listing_id="listing-1",
                synthetic_candidate_fingerprint=f"liepin:{candidate_id}",
                identity_confidence="provider_subject_id",
                extraction_source="dom_fallback",
                extractor_version="dokobot-action-v1",
                pii_classification="no_direct_contact",
                retention_policy="provider_snapshot_7d",
                access_scope="local_run_only",
                redaction_state="redacted",
            )
        ],
        raw_candidate_count=1,
    )


def test_pi_worker_client_maps_successful_card_response_to_search_result() -> None:
    runner = SimpleNamespace(
        search_cards=lambda **kwargs: LiepinPiCardSearchResult(
            pi_result=_pi_result(PiAgentResultStatus.SUCCEEDED),
            card_search=_card_response(),
        )
    )
    client = LiepinPiWorkerClient(
        runner,
        session_id="session-1",
        connection_id="connection-1",
        provider_account_lock_key="account-1",
    )

    result = asyncio.run(client.search(_request(), round_no=1, trace_id="trace-1"))

    assert result.candidates[0].resume_id == "candidate-1"
    assert result.provider_snapshots[0].payload_kind == "card"
    assert result.raw_candidate_count == 1


def test_blocked_pi_result_becomes_safe_worker_mode_error_with_structured_code() -> None:
    runner = SimpleNamespace(
        search_cards=lambda **kwargs: LiepinPiCardSearchResult(
            pi_result=_pi_result(
                PiAgentResultStatus.BLOCKED,
                stop_reason=PiAgentFailureCode.RISK_CONTROL,
            )
        )
    )
    client = LiepinPiWorkerClient(
        runner,
        session_id="session-1",
        connection_id="connection-1",
        provider_account_lock_key="account-1",
    )

    with pytest.raises(LiepinWorkerModeError) as error:
        asyncio.run(client.search(_request(), round_no=1, trace_id="trace-1"))

    assert error.value.code == "risk_control"
    assert str(error.value) == "Liepin PI card search blocked."


def test_partial_pi_result_raises_partial_worker_error_with_mapped_search_result() -> None:
    runner = SimpleNamespace(
        search_cards=lambda **kwargs: LiepinPiCardSearchResult(
            pi_result=_pi_result(
                PiAgentResultStatus.PARTIAL,
                stop_reason=PiAgentFailureCode.PAGE_TIMEOUT,
            ),
            card_search=_card_response("candidate-partial"),
        )
    )
    client = LiepinPiWorkerClient(
        runner,
        session_id="session-1",
        connection_id="connection-1",
        provider_account_lock_key="account-1",
    )

    with pytest.raises(LiepinWorkerPartialSearchError) as error:
        asyncio.run(client.search(_request(), round_no=1, trace_id="trace-1"))

    assert error.value.code == "page_timeout"
    assert error.value.cards_collected == 1
    assert error.value.partial_search_result.candidates[0].resume_id == "candidate-partial"


def test_pi_worker_client_search_does_not_block_event_loop_with_sync_runner() -> None:
    async def run_search() -> None:
        entered = threading.Event()
        release = threading.Event()

        def search_cards(**kwargs: object) -> LiepinPiCardSearchResult:
            del kwargs
            entered.set()
            release.wait(timeout=1.0)
            return LiepinPiCardSearchResult(
                pi_result=_pi_result(PiAgentResultStatus.SUCCEEDED),
                card_search=_card_response(),
            )

        client = LiepinPiWorkerClient(
            SimpleNamespace(search_cards=search_cards),
            session_id="session-1",
            connection_id="connection-1",
            provider_account_lock_key="account-1",
        )
        task = asyncio.create_task(client.search(_request(), round_no=1, trace_id="trace-1"))
        await asyncio.sleep(0.05)
        assert entered.is_set()
        assert not task.done()
        release.set()
        await task

    asyncio.run(run_search())


def test_complete_login_relay_returns_ready_provider_account_hash() -> None:
    probe = SimpleNamespace(
        complete_login_relay=lambda **kwargs: LoginRelayCompleteResult(
            connectionId=kwargs["connection_id"],
            status="ready",
            providerAccountHash="acct-hash",
            fixtureOnly=False,
        )
    )
    client = LiepinPiWorkerClient(
        SimpleNamespace(search_cards=lambda **kwargs: None),
        session_id="session-1",
        connection_id="connection-1",
        provider_account_lock_key="account-1",
        session_probe=probe,
    )

    result = asyncio.run(client.complete_login_relay(connection_id="connection-1"))

    assert result.status == "ready"
    assert result.provider_account_hash == "acct-hash"


def test_session_status_rejects_mismatched_provider_account_hash() -> None:
    probe = SimpleNamespace(
        session_status=lambda **kwargs: SessionStatus(
            connectionId=kwargs["connection_id"],
            status="ready",
            providerAccountHash="other-acct",
            fixtureOnly=False,
        )
    )
    client = LiepinPiWorkerClient(
        SimpleNamespace(search_cards=lambda **kwargs: None),
        session_id="session-1",
        connection_id="connection-1",
        provider_account_lock_key="account-1",
        session_probe=probe,
    )

    result = asyncio.run(
        client.session_status(connection_id="connection-1", provider_account_hash="expected-acct")
    )

    assert result.status == "login_required"
    assert result.provider_account_hash is None
