from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError

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
            "handoffToken": "handoff-token",
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
    assert handoff.handoff_token == "handoff-token"
    assert diagnostics.stdout == "[redacted]"


def test_worker_contract_decoders_reject_worker_internals() -> None:
    with pytest.raises(ValidationError):
        decode_worker_health({"status": "ok", "workerVersion": "fixture-worker", "browserDebugUrl": "ws://debug"})

    with pytest.raises(ValidationError):
        decode_session_status(
            {
                "connectionId": "conn-1",
                "status": "ready",
                "storageStatePath": "/tmp/storage-state.json",
            }
        )

    with pytest.raises(ValidationError):
        decode_login_handoff(
            {
                "connectionId": "conn-1",
                "handoffToken": "handoff-token",
                "loginUrl": "https://example.test/login",
                "expiresAt": "2026-05-07T12:00:00Z",
                "workerBaseUrl": "http://127.0.0.1:8123",
            }
        )


class RecordingHttpJson:
    def __init__(self, *responses: dict[str, object]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json_body: dict[str, object] | None,
        timeout: float,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "json_body": json_body,
                "timeout": timeout,
            }
        )
        return self.responses.pop(0)


def test_external_http_client_sends_worker_auth_and_decodes_health_status_and_handoff() -> None:
    settings = make_settings(
        liepin_worker_mode="external_http",
        liepin_worker_base_url="http://127.0.0.1:8123/internal-should-not-leak/..",
        liepin_api_token="worker-token",
    ).model_copy(update={"liepin_worker_base_url": "http://127.0.0.1:8123"})
    http_json = RecordingHttpJson(
        {"status": "ok", "workerVersion": "liepin-worker-v1"},
        {"connectionId": "conn-1", "status": "ready", "providerAccountHash": "acct-hash", "fixtureOnly": False},
        {
            "connectionId": "conn-1",
            "handoffToken": "handoff-token",
            "loginUrl": "https://www.liepin.com/",
            "expiresAt": "2026-05-08T12:05:00Z",
        },
    )
    client = ExternalHttpLiepinWorkerClient(settings, http_json=http_json)

    asyncio.run(client.ensure_ready())
    status = asyncio.run(client.session_status(connection_id="conn-1"))
    handoff = asyncio.run(client.login_handoff(connection_id="conn-1"))

    assert status.status == "ready"
    assert handoff.handoff_token == "handoff-token"
    assert http_json.calls == [
        {
            "method": "GET",
            "url": "http://127.0.0.1:8123/internal/health",
            "headers": {"Authorization": "Bearer worker-token"},
            "json_body": None,
            "timeout": settings.liepin_worker_timeout_seconds,
        },
        {
            "method": "GET",
            "url": "http://127.0.0.1:8123/internal/session/status?connectionId=conn-1",
            "headers": {"Authorization": "Bearer worker-token"},
            "json_body": None,
            "timeout": settings.liepin_worker_timeout_seconds,
        },
        {
            "method": "POST",
            "url": "http://127.0.0.1:8123/internal/session/login-handoff",
            "headers": {"Authorization": "Bearer worker-token"},
            "json_body": {"connectionId": "conn-1"},
            "timeout": settings.liepin_worker_timeout_seconds,
        },
    ]


def test_managed_local_client_uses_runtime_internal_base_url_for_http_calls() -> None:
    settings = make_settings(liepin_worker_mode="managed_local", liepin_api_token="worker-token")
    runtime = SimpleNamespace(
        ensure_started=lambda **_: SimpleNamespace(internal_base_url="http://127.0.0.1:4567")
    )
    http_json = RecordingHttpJson(
        {"connectionId": "conn-1", "status": "login_required", "fixtureOnly": False},
    )
    client = ManagedLocalLiepinWorkerClient(settings, runtime=runtime, http_json=http_json)

    status = asyncio.run(client.session_status(connection_id="conn-1"))

    assert status.status == "login_required"
    assert http_json.calls[0]["url"] == "http://127.0.0.1:4567/internal/session/status?connectionId=conn-1"
    assert http_json.calls[0]["headers"] == {"Authorization": "Bearer worker-token"}
