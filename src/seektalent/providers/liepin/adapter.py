from __future__ import annotations

from seektalent.config import AppSettings
from seektalent.core.retrieval.provider_contract import ProviderCapabilities
from seektalent.core.retrieval.provider_contract import SearchRequest
from seektalent.core.retrieval.provider_contract import SearchResult
from seektalent.providers.liepin.client import EventCallback
from seektalent.providers.liepin.client import LiepinWorkerClient
from seektalent.providers.liepin.client import LiepinWorkerModeError


class LiepinProviderAdapter:
    name = "liepin"

    def __init__(
        self,
        settings: AppSettings,
        *,
        worker_client: LiepinWorkerClient | None = None,
        worker_event_callback: EventCallback | None = None,
    ) -> None:
        self.settings = settings
        self.worker_client = worker_client
        self.worker_event_callback = worker_event_callback

    def describe_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_structured_filters=True,
            supports_detail_fetch=True,
            supports_fetch_mode_summary=True,
            supports_fetch_mode_detail=True,
            paging_mode="cursor",
            recommended_max_concurrency=1,
            has_stable_external_id=True,
            has_stable_dedup_key=True,
        )

    async def search(self, request: SearchRequest, *, round_no: int, trace_id: str) -> SearchResult:
        if self.worker_client is None:
            raise LiepinWorkerModeError("Liepin provider search requires an explicit worker client.")
        await self.worker_client.ensure_ready(on_event=self.worker_event_callback)
        return await self.worker_client.search(request, round_no=round_no, trace_id=trace_id)
