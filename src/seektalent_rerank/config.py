from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RerankSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SEEKTALENT_RERANK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "127.0.0.1"
    port: int = Field(default=8012, ge=1, le=65535)
    model_id: str = "mlx-community/Qwen3-Reranker-8B-mxfp8"
    batch_size: int = Field(default=4, ge=1)
    max_length: int = Field(default=8192, ge=1)

    def with_overrides(self, **overrides: object) -> "RerankSettings":
        filtered = {key: value for key, value in overrides.items() if value is not None}
        return type(self).model_validate({**self.model_dump(), **filtered})

