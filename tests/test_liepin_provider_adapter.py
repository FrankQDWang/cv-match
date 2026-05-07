from __future__ import annotations

import asyncio

import pytest

from seektalent.core.retrieval.provider_contract import SearchRequest
from seektalent.providers.liepin.adapter import LiepinProviderAdapter
from seektalent.providers.liepin.client import LiepinWorkerModeError
from tests.settings_factory import make_settings


class RecordingWorkerClient:
    def __init__(self, *, fail_ready: bool = False) -> None:
        self.fail_ready = fail_ready
        self.ready_called = False
        self.search_called = False

    async def ensure_ready(self, *, on_event=None) -> None:
        self.ready_called = True
        if self.fail_ready:
            if on_event is not None:
                on_event("worker_start_timeout", {"mode": "managed_local", "setup_status": "timeout"})
            raise LiepinWorkerModeError("worker_start_timeout")

    async def search(self, request: SearchRequest, *, round_no: int, trace_id: str):
        self.search_called = True
        raise AssertionError("search dispatch should not happen")


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


def test_adapter_never_substitutes_fake_worker_when_no_client_is_passed() -> None:
    settings = make_settings(
        provider_name="liepin",
        liepin_worker_mode="fake_fixture",
        liepin_allow_fake_fixture_worker=True,
    )
    adapter = LiepinProviderAdapter(settings)

    with pytest.raises(LiepinWorkerModeError, match="worker client"):
        asyncio.run(adapter.search(_request(), round_no=1, trace_id="trace-1"))


def test_adapter_records_worker_start_timeout_and_does_not_dispatch_search() -> None:
    settings = make_settings(provider_name="liepin", liepin_worker_mode="managed_local")
    events: list[tuple[str, dict[str, object]]] = []
    worker = RecordingWorkerClient(fail_ready=True)
    adapter = LiepinProviderAdapter(
        settings,
        worker_client=worker,
        worker_event_callback=lambda name, payload: events.append((name, payload)),
    )

    with pytest.raises(LiepinWorkerModeError, match="worker_start_timeout"):
        asyncio.run(adapter.search(_request(), round_no=1, trace_id="trace-1"))

    assert worker.ready_called is True
    assert worker.search_called is False
    assert events == [("worker_start_timeout", {"mode": "managed_local", "setup_status": "timeout"})]
