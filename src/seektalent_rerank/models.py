from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _strip_required_text(value: str, *, field_name: str) -> str:
    clean = value.strip()
    if not clean:
        raise ValueError(f"{field_name} must not be empty.")
    return clean


class RerankDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str

    @field_validator("id", "text")
    @classmethod
    def validate_text(cls, value: str, info) -> str:
        return _strip_required_text(value, field_name=info.field_name)


class RerankRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instruction: str
    query: str
    documents: list[RerankDocument] = Field(min_length=1)

    @field_validator("instruction", "query")
    @classmethod
    def validate_text(cls, value: str, info) -> str:
        return _strip_required_text(value, field_name=info.field_name)


class RerankResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    index: int
    score: float
    rank: int


class RerankResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    results: list[RerankResult] = Field(default_factory=list)


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "unavailable"]
    ready: bool
    model: str

