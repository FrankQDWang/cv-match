from __future__ import annotations

import asyncio

import pytest

from seektalent.core.retrieval.provider_contract import SearchRequest
from seektalent.providers.liepin.client import (
    ExternalHttpLiepinWorkerClient,
    FakeLiepinWorkerClient,
    LiepinWorkerModeError,
    ManagedLocalLiepinWorkerClient,
    build_liepin_worker_client,
)
from seektalent.providers.liepin.worker_contracts import (
    LoginHandoff,
    RedactedWorkerDiagnostics,
    SessionStatus,
    WorkerHealth,
    decode_login_handoff,
    decode_redacted_diagnostics,
    decode_session_status,
    decode_worker_health,
)
from tests.settings_factory import make_settings


def _request() -> SearchRequest:
    return SearchRequest(
        query_terms=["python"],
        query_role="primary",
        keyword_query="python",
        adapter_notes=[],
        runtime_constraints=[],
        fetch_mode="summary",
        page_size=10,
    )


def test_fake_fixture_client_requires_mode_and_explicit_allow_flag() -> None:
    settings = make_settings(
        liepin_worker_mode="fake_fixture",
        liepin_allow_fake_fixture_worker=True,
    )

    assert isinstance(build_liepin_worker_client(settings), FakeLiepinWorkerClient)

    managed_settings = make_settings(
        liepin_worker_mode="managed_local",
        liepin_allow_fake_fixture_worker=True,
    )
    with pytest.raises(LiepinWorkerModeError, match="fake_fixture"):
        FakeLiepinWorkerClient(managed_settings)


def test_fake_fixture_search_is_deterministic_and_labeled_fixture_only() -> None:
    settings = make_settings(
        liepin_worker_mode="fake_fixture",
        liepin_allow_fake_fixture_worker=True,
    )
    client = FakeLiepinWorkerClient(settings)

    first = asyncio.run(client.search(_request(), round_no=1, trace_id="trace-1"))
    second = asyncio.run(client.search(_request(), round_no=1, trace_id="trace-1"))

    assert first == second
    assert first.request_payload["fixture_only"] is True
    assert first.diagnostics == ["liepin fake fixture worker"]


def test_fake_fixture_mode_is_rejected_when_live_enabled() -> None:
    settings = make_settings(
        liepin_worker_mode="fake_fixture",
        liepin_allow_fake_fixture_worker=True,
        liepin_live_enabled=True,
    )

    with pytest.raises(LiepinWorkerModeError, match="live"):
        build_liepin_worker_client(settings)


def test_build_managed_local_client_for_live_capable_local_mode() -> None:
    settings = make_settings(liepin_worker_mode="managed_local")

    client = build_liepin_worker_client(settings)

    assert isinstance(client, ManagedLocalLiepinWorkerClient)


def test_external_http_client_requires_external_mode() -> None:
    settings = make_settings(
        liepin_worker_mode="external_http",
        liepin_worker_base_url="http://127.0.0.1:8123",
    )

    assert isinstance(build_liepin_worker_client(settings), ExternalHttpLiepinWorkerClient)

    managed_settings = make_settings(liepin_worker_mode="managed_local")
    with pytest.raises(LiepinWorkerModeError, match="external_http"):
        ExternalHttpLiepinWorkerClient(managed_settings)


def test_missing_external_http_worker_url_fails_before_search_dispatch() -> None:
    settings = make_settings(liepin_worker_mode="managed_local").model_copy(
        update={"liepin_worker_mode": "external_http", "liepin_worker_base_url": None}
    )

    with pytest.raises(LiepinWorkerModeError, match="liepin_worker_base_url"):
        build_liepin_worker_client(settings)


def test_worker_contracts_decode_internal_payloads() -> None:
    health = decode_worker_health({"status": "ok", "workerVersion": "fixture-worker"})
    session = decode_session_status(
        {
            "connectionId": "conn-1",
            "status": "ready",
            "providerAccountHash": "acct-hash",
            "fixtureOnly": False,
        }
    )
    handoff = decode_login_handoff(
        {
            "connectionId": "conn-1",
            "loginUrl": "https://example.test/login",
            "expiresAt": "2026-05-07T12:00:00Z",
        }
    )
    diagnostics = decode_redacted_diagnostics(
        {
            "code": "worker_failed",
            "message": "worker exited",
            "stdout": "[redacted]",
            "stderr": "[redacted]",
        }
    )

    assert isinstance(health, WorkerHealth)
    assert isinstance(session, SessionStatus)
    assert isinstance(handoff, LoginHandoff)
    assert isinstance(diagnostics, RedactedWorkerDiagnostics)
    assert health.worker_version == "fixture-worker"
    assert session.fixture_only is False
    assert diagnostics.stdout == "[redacted]"
