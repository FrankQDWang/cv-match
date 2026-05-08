from __future__ import annotations

import json
from typing import Any
from typing import Callable, Protocol
from urllib import parse
from urllib import request as urllib_request

from seektalent.config import AppSettings
from seektalent.core.retrieval.provider_contract import SearchRequest
from seektalent.core.retrieval.provider_contract import SearchResult
from seektalent.providers.liepin.worker_contracts import LiepinWorkerModeError
from seektalent.providers.liepin.worker_contracts import LoginHandoff
from seektalent.providers.liepin.worker_contracts import SessionStatus
from seektalent.providers.liepin.worker_contracts import decode_login_handoff
from seektalent.providers.liepin.worker_contracts import decode_session_status
from seektalent.providers.liepin.worker_contracts import decode_worker_health
from seektalent.providers.liepin.worker_runtime import ManagedLiepinWorkerRuntime


EventCallback = Callable[[str, dict[str, object]], None]


class LiepinWorkerClient(Protocol):
    async def ensure_ready(self, *, on_event: EventCallback | None = None) -> None: ...

    async def search(self, request: SearchRequest, *, round_no: int, trace_id: str) -> SearchResult: ...


class FakeLiepinWorkerClient:
    def __init__(self, settings: AppSettings) -> None:
        if settings.liepin_worker_mode != "fake_fixture" or not settings.liepin_allow_fake_fixture_worker:
            raise LiepinWorkerModeError(
                "Fake Liepin fixture worker requires liepin_worker_mode=fake_fixture "
                "and liepin_allow_fake_fixture_worker=True.",
                setup_status="fake_fixture_not_allowed",
            )
        if settings.liepin_live_enabled:
            raise LiepinWorkerModeError(
                "Fake Liepin fixture worker is not allowed when liepin_live_enabled=True.",
                setup_status="fake_fixture_live_rejected",
            )
        self.settings = settings

    async def ensure_ready(self, *, on_event: EventCallback | None = None) -> None:
        return None

    async def search(self, request: SearchRequest, *, round_no: int, trace_id: str) -> SearchResult:
        return SearchResult(
            candidates=[],
            diagnostics=["liepin fake fixture worker"],
            exhausted=True,
            request_payload={
                "fixture_only": True,
                "keyword_query": request.keyword_query,
                "round_no": round_no,
                "trace_id": trace_id,
            },
            raw_candidate_count=0,
        )


class ManagedLocalLiepinWorkerClient:
    def __init__(
        self,
        settings: AppSettings,
        *,
        runtime: ManagedLiepinWorkerRuntime | None = None,
        http_json: Callable[..., dict[str, object]] | None = None,
    ) -> None:
        if settings.liepin_worker_mode != "managed_local":
            raise LiepinWorkerModeError("Managed local Liepin worker requires liepin_worker_mode=managed_local.")
        self.settings = settings
        self.runtime = runtime or ManagedLiepinWorkerRuntime.shared(settings)
        self.http_json = http_json or _default_http_json

    async def ensure_ready(self, *, on_event: EventCallback | None = None) -> None:
        self.runtime.ensure_started(on_event=on_event)

    async def session_status(self, *, connection_id: str) -> SessionStatus:
        base_url = self._internal_base_url()
        return decode_session_status(
            self._request_json(
                "GET",
                f"{base_url}/internal/session/status?connectionId={parse.quote(connection_id)}",
            )
        )

    async def login_handoff(self, *, connection_id: str) -> LoginHandoff:
        base_url = self._internal_base_url()
        return decode_login_handoff(
            self._request_json(
                "POST",
                f"{base_url}/internal/session/login-handoff",
                json_body={"connectionId": connection_id},
            )
        )

    async def search(self, request: SearchRequest, *, round_no: int, trace_id: str) -> SearchResult:
        await self.ensure_ready()
        raise NotImplementedError("Liepin worker search is implemented in a later task.")

    def _internal_base_url(self) -> str:
        handle = self.runtime.ensure_started()
        return handle.internal_base_url.rstrip("/")

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        json_body: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return self.http_json(
            method,
            url,
            headers={"Authorization": f"Bearer {self.settings.liepin_api_token}"},
            json_body=json_body,
            timeout=self.settings.liepin_worker_timeout_seconds,
        )


class ExternalHttpLiepinWorkerClient:
    def __init__(
        self,
        settings: AppSettings,
        *,
        http_json: Callable[..., dict[str, object]] | None = None,
    ) -> None:
        if settings.liepin_worker_mode != "external_http":
            raise LiepinWorkerModeError("External Liepin worker requires liepin_worker_mode=external_http.")
        if settings.liepin_worker_base_url is None:
            raise LiepinWorkerModeError(
                "liepin_worker_base_url is required when liepin_worker_mode=external_http.",
                setup_status="missing_external_worker_url",
            )
        self.settings = settings
        self.base_url = settings.liepin_worker_base_url.rstrip("/")
        self.http_json = http_json or _default_http_json

    async def ensure_ready(self, *, on_event: EventCallback | None = None) -> None:
        health = decode_worker_health(self._request_json("GET", f"{self.base_url}/internal/health"))
        if health.status != "ok":
            raise LiepinWorkerModeError("Liepin external worker is not ready.", setup_status=health.status)

    async def session_status(self, *, connection_id: str) -> SessionStatus:
        return decode_session_status(
            self._request_json(
                "GET",
                f"{self.base_url}/internal/session/status?connectionId={parse.quote(connection_id)}",
            )
        )

    async def login_handoff(self, *, connection_id: str) -> LoginHandoff:
        return decode_login_handoff(
            self._request_json(
                "POST",
                f"{self.base_url}/internal/session/login-handoff",
                json_body={"connectionId": connection_id},
            )
        )

    async def search(self, request: SearchRequest, *, round_no: int, trace_id: str) -> SearchResult:
        raise NotImplementedError("External Liepin worker search is implemented in a later task.")

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        json_body: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return self.http_json(
            method,
            url,
            headers={"Authorization": f"Bearer {self.settings.liepin_api_token}"},
            json_body=json_body,
            timeout=self.settings.liepin_worker_timeout_seconds,
        )


def build_liepin_worker_client(settings: AppSettings) -> LiepinWorkerClient:
    if settings.liepin_worker_mode == "fake_fixture":
        return FakeLiepinWorkerClient(settings)
    if settings.liepin_worker_mode == "managed_local":
        return ManagedLocalLiepinWorkerClient(settings)
    if settings.liepin_worker_mode == "external_http":
        return ExternalHttpLiepinWorkerClient(settings)
    raise LiepinWorkerModeError(
        "Liepin worker mode is disabled; no worker client can be built.",
        setup_status="disabled",
    )


def _default_http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    json_body: dict[str, object] | None,
    timeout: float,
) -> dict[str, object]:
    data: bytes | None = None
    request_headers = dict(headers)
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    req = urllib_request.Request(url, data=data, headers=request_headers, method=method)
    with urllib_request.urlopen(req, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
    decoded: Any = json.loads(payload)
    if not isinstance(decoded, dict):
        raise ValueError("Liepin worker response must be a JSON object")
    return decoded
