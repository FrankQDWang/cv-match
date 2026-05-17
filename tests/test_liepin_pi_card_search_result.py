from __future__ import annotations

from hashlib import sha256
import json

import pytest

from seektalent.providers.liepin.pi_runner import LiepinPiCardSearchResult, LiepinPiRunner
from seektalent.providers.liepin.worker_contracts import LiepinCardSearchResponse, LiepinWorkerCandidateCard
from seektalent.providers.pi_agent.capabilities import DokoBotCapabilities
from seektalent.providers.pi_agent.contracts import (
    PiAgentFailureCode,
    PiAgentResult,
    PiAgentResultStatus,
    PiArtifactRef,
    PiBackendMode,
    ProtectedArtifactClass,
)
from seektalent.providers.pi_agent.locks import InMemoryPiConnectionLock


SEARCH_KWARGS = {
    "session_id": "session_1",
    "source_run_id": "source_run_1",
    "connection_id": "connection_1",
    "provider_account_lock_key": "provider_account_1",
    "keyword_query": "Python",
    "query_terms": ["Python"],
    "max_pages": 1,
    "page_size": 10,
    "max_cards": 10,
}


def _trace_writer(
    content: bytes,
    artifact_class: ProtectedArtifactClass,
    policy_id: str,
) -> PiArtifactRef:
    payload = json.loads(content.decode("utf-8"))
    assert payload["schema_version"] == "pi-agent-action-trace-v1"
    content_hash = sha256(content).hexdigest()
    return PiArtifactRef(
        artifact_class=artifact_class,
        artifact_ref=f"trace:{content_hash}",
        content_sha256=content_hash,
        redaction_policy_id=policy_id,
    )


def _capabilities() -> DokoBotCapabilities:
    return DokoBotCapabilities(
        cli_version="2.11.0",
        supports_read=True,
        supports_click=True,
        supports_type=True,
        supports_navigation=True,
        supports_pagination_action=True,
        action_manifest_id="manifest_1",
        action_manifest_version="1",
        action_manifest_transport="local_only",
        action_manifest_trust_source="preconfigured_admin",
        action_manifest_tools=("click", "type_text", "navigate", "pagination"),
    )


def _card_response() -> LiepinCardSearchResponse:
    return LiepinCardSearchResponse(
        cards=[
            LiepinWorkerCandidateCard(
                payload={"safe_summary_ref": "artifact://summary/liepin/card-1"},
                normalized_text="FastAPI ranking platform",
                provider_subject_id="provider-1",
                synthetic_candidate_fingerprint="fingerprint-1",
                identity_confidence="provider_subject_id",
                extraction_source="dom_fallback",
                extractor_version="test",
                pii_classification="no_direct_contact",
                retention_policy="provider_snapshot_7d",
                access_scope="local_run_only",
                redaction_state="redacted",
            )
        ],
        raw_candidate_count=1,
    )


def _pi_result(status: PiAgentResultStatus, *, stop_reason: PiAgentFailureCode | None = None) -> PiAgentResult:
    return PiAgentResult(
        schema_version="pi-agent-result-v1",
        status=status,
        stop_reason=stop_reason,
        action_trace_ref=_trace_writer(
            b'{"schema_version":"pi-agent-action-trace-v1","interaction_id":"trace_ok"}',
            ProtectedArtifactClass.REDACTED_EVIDENCE,
            "liepin-trace-redaction-v1",
        ),
    )


def test_successful_pi_card_search_requires_card_response() -> None:
    with pytest.raises(ValueError, match="card_search is required"):
        LiepinPiCardSearchResult(pi_result=_pi_result(PiAgentResultStatus.SUCCEEDED))


def test_dokobot_action_search_cards_returns_pi_result_and_typed_cards() -> None:
    def dokobot_search_cards(**kwargs: object) -> LiepinPiCardSearchResult:
        assert kwargs["page_size"] == 10
        return LiepinPiCardSearchResult(
            pi_result=_pi_result(PiAgentResultStatus.SUCCEEDED),
            card_search=_card_response(),
        )

    runner = LiepinPiRunner(
        backend_mode=PiBackendMode.DOKOBOT_ACTION,
        dokobot_capabilities=_capabilities(),
        connection_lock=InMemoryPiConnectionLock(),
        trace_artifact_writer=_trace_writer,
        dokobot_search_cards=dokobot_search_cards,
    )

    result = runner.search_cards(**SEARCH_KWARGS)

    assert result.status == PiAgentResultStatus.SUCCEEDED
    assert result.card_search is not None
    assert result.card_search.cards[0].normalized_text == "FastAPI ranking platform"
