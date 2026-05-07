from __future__ import annotations

from typing import Callable, Protocol

from seektalent.config import AppSettings
from seektalent.core.retrieval.provider_contract import SearchRequest
from seektalent.core.retrieval.provider_contract import SearchResult
from seektalent.providers.liepin.worker_contracts import LiepinWorkerModeError
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
    def __init__(self, settings: AppSettings, *, runtime: ManagedLiepinWorkerRuntime | None = None) -> None:
        if settings.liepin_worker_mode != "managed_local":
            raise LiepinWorkerModeError("Managed local Liepin worker requires liepin_worker_mode=managed_local.")
        self.settings = settings
        self.runtime = runtime or ManagedLiepinWorkerRuntime.shared(settings)

    async def ensure_ready(self, *, on_event: EventCallback | None = None) -> None:
        self.runtime.ensure_started(on_event=on_event)

    async def search(self, request: SearchRequest, *, round_no: int, trace_id: str) -> SearchResult:
        await self.ensure_ready()
        raise NotImplementedError("Liepin worker search is implemented in a later task.")


class ExternalHttpLiepinWorkerClient:
    def __init__(self, settings: AppSettings) -> None:
        if settings.liepin_worker_mode != "external_http":
            raise LiepinWorkerModeError("External Liepin worker requires liepin_worker_mode=external_http.")
        if settings.liepin_worker_base_url is None:
            raise LiepinWorkerModeError(
                "liepin_worker_base_url is required when liepin_worker_mode=external_http.",
                setup_status="missing_external_worker_url",
            )
        self.settings = settings
        self.base_url = settings.liepin_worker_base_url.rstrip("/")

    async def ensure_ready(self, *, on_event: EventCallback | None = None) -> None:
        return None

    async def search(self, request: SearchRequest, *, round_no: int, trace_id: str) -> SearchResult:
        raise NotImplementedError("External Liepin worker search is implemented in a later task.")


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
