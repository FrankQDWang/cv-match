from __future__ import annotations

import threading

import httpx

from seektalent_rerank.engine import ModelNotReadyError
from seektalent_rerank.models import HealthResponse, RerankResponse, RerankResult
from seektalent_rerank.server import create_server


class FakeEngine:
    def __init__(self, *, ready: bool = True, error: Exception | None = None) -> None:
        self.ready = ready
        self.error = error
        self.model_id = "mlx-community/Qwen3-Reranker-8B-mxfp8"
        self.seen_requests = []

    def health(self) -> HealthResponse:
        return HealthResponse(
            status="ok" if self.ready else "unavailable",
            ready=self.ready,
            model=self.model_id,
        )

    def rerank_request(self, request):
        self.seen_requests.append(request)
        if self.error is not None:
            raise self.error
        return RerankResponse(
            model=self.model_id,
            results=[
                RerankResult(id="resume-2", index=1, score=0.9, rank=1),
                RerankResult(id="resume-1", index=0, score=0.1, rank=2),
            ],
        )


def _start_server(engine: FakeEngine):
    server = create_server("127.0.0.1", 0, engine)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, thread, f"http://{host}:{port}"


def test_rerank_api_serves_health_and_results() -> None:
    engine = FakeEngine()
    server, thread, base_url = _start_server(engine)

    try:
        with httpx.Client(base_url=base_url, timeout=2.0) as client:
            health = client.get("/healthz")
            assert health.status_code == 200
            assert health.json() == {
                "status": "ok",
                "ready": True,
                "model": "mlx-community/Qwen3-Reranker-8B-mxfp8",
            }

            rerank = client.post(
                "/api/rerank",
                json={
                    "instruction": "Rank resumes for the JD.",
                    "query": "Python agent engineer",
                    "documents": [
                        {"id": "resume-1", "text": "Document 1"},
                        {"id": "resume-2", "text": "Document 2"},
                    ],
                },
            )
            assert rerank.status_code == 200
            payload = rerank.json()
            assert payload["results"][0] == {
                "id": "resume-2",
                "index": 1,
                "score": 0.9,
                "rank": 1,
            }
            assert engine.seen_requests[0].documents[0].id == "resume-1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_rerank_api_rejects_invalid_request() -> None:
    engine = FakeEngine()
    server, thread, base_url = _start_server(engine)

    try:
        with httpx.Client(base_url=base_url, timeout=2.0) as client:
            response = client.post(
                "/api/rerank",
                json={
                    "instruction": "Rank resumes for the JD.",
                    "query": "Python agent engineer",
                    "documents": [],
                },
            )
            assert response.status_code == 400
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_rerank_api_returns_503_when_model_is_not_ready() -> None:
    engine = FakeEngine(error=ModelNotReadyError("model unavailable"))
    server, thread, base_url = _start_server(engine)

    try:
        with httpx.Client(base_url=base_url, timeout=2.0) as client:
            response = client.post(
                "/api/rerank",
                json={
                    "instruction": "Rank resumes for the JD.",
                    "query": "Python agent engineer",
                    "documents": [{"id": "resume-1", "text": "Document 1"}],
                },
            )
            assert response.status_code == 503
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_rerank_api_returns_500_on_engine_failure() -> None:
    engine = FakeEngine(error=RuntimeError("boom"))
    server, thread, base_url = _start_server(engine)

    try:
        with httpx.Client(base_url=base_url, timeout=2.0) as client:
            response = client.post(
                "/api/rerank",
                json={
                    "instruction": "Rank resumes for the JD.",
                    "query": "Python agent engineer",
                    "documents": [{"id": "resume-1", "text": "Document 1"}],
                },
            )
            assert response.status_code == 500
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
