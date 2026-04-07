from __future__ import annotations

from dataclasses import dataclass, field

from seektalent_rerank.engine import RerankEngine, format_instruction
from seektalent_rerank.models import RerankRequest


@dataclass
class FakeBackend:
    scores_by_batch: list[list[float]]
    model_id: str = "mlx-community/Qwen3-Reranker-8B-mxfp8"
    ready: bool = True
    seen_batches: list[list[str]] = field(default_factory=list)

    def score_pairs(self, pairs: list[str]) -> list[float]:
        self.seen_batches.append(pairs)
        return self.scores_by_batch[len(self.seen_batches) - 1]


def test_rerank_engine_batches_inputs_and_sorts_stably() -> None:
    backend = FakeBackend(scores_by_batch=[[0.2, 0.9], [0.9]])
    engine = RerankEngine(backend, batch_size=2)
    request = RerankRequest.model_validate(
        {
            "instruction": "Rank resumes for the JD.",
            "query": "Python agent engineer",
            "documents": [
                {"id": "resume-1", "text": "Document 1"},
                {"id": "resume-2", "text": "Document 2"},
                {"id": "resume-3", "text": "Document 3"},
            ],
        }
    )

    response = engine.rerank_request(request)

    assert backend.seen_batches == [
        [
            format_instruction("Rank resumes for the JD.", "Python agent engineer", "Document 1"),
            format_instruction("Rank resumes for the JD.", "Python agent engineer", "Document 2"),
        ],
        [format_instruction("Rank resumes for the JD.", "Python agent engineer", "Document 3")],
    ]
    assert [result.id for result in response.results] == ["resume-2", "resume-3", "resume-1"]
    assert [result.rank for result in response.results] == [1, 2, 3]
    assert [result.index for result in response.results] == [1, 2, 0]

