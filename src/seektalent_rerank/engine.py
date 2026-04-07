from __future__ import annotations

import math
import platform
import threading
from dataclasses import dataclass
from typing import Protocol

from seektalent_rerank.models import HealthResponse, RerankRequest, RerankResponse, RerankResult

SYSTEM_PROMPT = (
    'Judge whether the Document meets the requirements based on the Query and the '
    'Instruct provided. Note that the answer can only be "yes" or "no".'
)
PREFIX_TEMPLATE = f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n<|im_start|>user\n"
SUFFIX_TEMPLATE = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"


class ModelNotReadyError(RuntimeError):
    pass


class RerankBackend(Protocol):
    model_id: str
    ready: bool

    def score_pairs(self, pairs: list[str]) -> list[float]:
        raise NotImplementedError


def format_instruction(instruction: str, query: str, document: str) -> str:
    return (
        f"<Instruct>: {instruction}\n"
        f"<Query>: {query}\n"
        f"<Document>: {document}"
    )


def _batched(values: list[str], batch_size: int) -> list[list[str]]:
    return [values[index:index + batch_size] for index in range(0, len(values), batch_size)]


def _binary_probability(false_logit: float, true_logit: float) -> float:
    diff = true_logit - false_logit
    if diff >= 0:
        return 1.0 / (1.0 + math.exp(-diff))
    exp_diff = math.exp(diff)
    return exp_diff / (1.0 + exp_diff)


def _require_single_token(tokenizer, text: str) -> int:
    token_ids = tokenizer.encode(text, add_special_tokens=False)
    if len(token_ids) != 1:
        raise ValueError(f"{text!r} must map to exactly one token, got {token_ids!r}.")
    return token_ids[0]


def _load_mlx_lm_model(model_id: str):
    from mlx_lm import load as load_model

    try:
        return load_model(model_id)
    except ValueError as exc:
        # Some MLX community reranker repos ship tied embeddings but a broken
        # safetensors index that still references a missing lm_head shard.
        if "lm_head.weight" not in str(exc):
            raise
        return load_model(model_id, model_config={"tie_word_embeddings": True})


@dataclass
class MlxLmBackend:
    model: object
    tokenizer: object
    model_id: str
    max_length: int
    prefix_tokens: list[int]
    suffix_tokens: list[int]
    token_false_id: int
    token_true_id: int
    mx: object
    ready: bool = True

    @classmethod
    def load(cls, *, model_id: str, max_length: int) -> "MlxLmBackend":
        if platform.system() != "Darwin" or platform.machine() != "arm64":
            raise RuntimeError("Qwen rerank service requires macOS on Apple Silicon (Darwin arm64).")

        import mlx.core as mx

        model, tokenizer = _load_mlx_lm_model(model_id)
        tokenizer = getattr(tokenizer, "_tokenizer", tokenizer)
        tokenizer.padding_side = "left"
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        return cls(
            model=model,
            tokenizer=tokenizer,
            model_id=model_id,
            max_length=max_length,
            prefix_tokens=tokenizer.encode(PREFIX_TEMPLATE, add_special_tokens=False),
            suffix_tokens=tokenizer.encode(SUFFIX_TEMPLATE, add_special_tokens=False),
            token_false_id=_require_single_token(tokenizer, "no"),
            token_true_id=_require_single_token(tokenizer, "yes"),
            mx=mx,
        )

    def score_pairs(self, pairs: list[str]) -> list[float]:
        if not pairs:
            return []

        inputs = self.tokenizer(
            pairs,
            padding=False,
            truncation="longest_first",
            return_attention_mask=False,
            max_length=self.max_length - len(self.prefix_tokens) - len(self.suffix_tokens),
        )
        for index, token_ids in enumerate(inputs["input_ids"]):
            inputs["input_ids"][index] = self.prefix_tokens + token_ids + self.suffix_tokens

        padded = self.tokenizer.pad(
            inputs,
            padding=True,
            return_tensors="np",
        )
        input_ids = self.mx.array(padded["input_ids"])
        attention_mask = self.mx.array(padded["attention_mask"])
        logits = self._forward(input_ids=input_ids, attention_mask=attention_mask)
        pair_logits = logits[:, -1, [self.token_false_id, self.token_true_id]]
        self.mx.eval(pair_logits)
        return [
            _binary_probability(false_logit, true_logit)
            for false_logit, true_logit in pair_logits.tolist()
        ]

    def _forward(self, *, input_ids, attention_mask):
        hidden = self.model.model.embed_tokens(input_ids)
        mask = self._attention_mask(attention_mask=attention_mask, dtype=hidden.dtype)
        for layer in self.model.model.layers:
            hidden = layer(hidden, mask, None)
        hidden = self.model.model.norm(hidden)
        if self.model.args.tie_word_embeddings:
            return self.model.model.embed_tokens.as_linear(hidden)
        return self.model.lm_head(hidden)

    def _attention_mask(self, *, attention_mask, dtype):
        sequence_length = attention_mask.shape[1]
        causal_mask = self.mx.tril(self.mx.ones((sequence_length, sequence_length), dtype=self.mx.bool_))
        causal_mask = self.mx.where(causal_mask, 0.0, -self.mx.inf).astype(dtype)
        causal_mask = self.mx.expand_dims(causal_mask, axis=(0, 1))
        padding_mask = attention_mask[:, None, None, :]
        padding_mask = self.mx.where(padding_mask == 0, -self.mx.inf, 0.0).astype(dtype)
        return causal_mask + padding_mask


class RerankEngine:
    def __init__(self, backend: RerankBackend, *, batch_size: int) -> None:
        self.backend = backend
        self.batch_size = batch_size
        self._lock = threading.Lock()

    @classmethod
    def load(
        cls,
        *,
        model_id: str,
        batch_size: int,
        max_length: int,
    ) -> "RerankEngine":
        backend = MlxLmBackend.load(model_id=model_id, max_length=max_length)
        return cls(backend, batch_size=batch_size)

    @property
    def model_id(self) -> str:
        return self.backend.model_id

    @property
    def ready(self) -> bool:
        return self.backend.ready

    def health(self) -> HealthResponse:
        return HealthResponse(
            status="ok" if self.ready else "unavailable",
            ready=self.ready,
            model=self.model_id,
        )

    def rerank_request(self, request: RerankRequest) -> RerankResponse:
        if not self.ready:
            raise ModelNotReadyError(f"Model {self.model_id} is not ready.")

        pair_texts = [
            format_instruction(request.instruction, request.query, document.text)
            for document in request.documents
        ]

        with self._lock:
            scores: list[float] = []
            for batch in _batched(pair_texts, self.batch_size):
                scores.extend(self.backend.score_pairs(batch))

        if len(scores) != len(request.documents):
            raise RuntimeError(
                f"Expected {len(request.documents)} scores from backend, got {len(scores)}."
            )

        ranked = sorted(
            [
                {
                    "id": document.id,
                    "index": index,
                    "score": score,
                }
                for index, (document, score) in enumerate(zip(request.documents, scores))
            ],
            key=lambda item: (-item["score"], item["index"]),
        )
        results = [
            RerankResult(
                id=item["id"],
                index=item["index"],
                score=item["score"],
                rank=rank,
            )
            for rank, item in enumerate(ranked, start=1)
        ]
        return RerankResponse(model=self.model_id, results=results)
