from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ReasoningEffort = Literal["low", "medium", "high"]
MODEL_FIELDS = (
    "requirements_model",
    "controller_model",
    "scoring_model",
    "finalize_model",
    "reflection_model",
)


def _is_qualified_model_id(model_id: str) -> bool:
    if ":" not in model_id:
        return False
    provider, name = model_id.split(":", 1)
    return bool(provider and name)


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CVMATCH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    cts_base_url: str = "https://link.hewa.cn"
    cts_tenant_key: str | None = None
    cts_tenant_secret: str | None = None
    cts_timeout_seconds: float = 20.0
    cts_spec_path: str = "cts.validated.yaml"

    requirements_model: str = "openai-responses:gpt-5.4-mini"
    controller_model: str = "openai-responses:gpt-5.4-mini"
    scoring_model: str = "openai-responses:gpt-5.4-mini"
    finalize_model: str = "openai-responses:gpt-5.4-mini"
    reflection_model: str = "openai-responses:gpt-5.4"
    reasoning_effort: ReasoningEffort = "medium"

    min_rounds: int = 3
    max_rounds: int = 5
    scoring_max_concurrency: int = 5
    search_max_pages_per_round: int = 3
    search_max_attempts_per_round: int = 3
    search_no_progress_limit: int = 2
    mock_cts: bool = True
    enable_reflection: bool = True

    runs_dir: str = "runs"

    @field_validator(*MODEL_FIELDS)
    @classmethod
    def validate_model_id(cls, value: str, info: ValidationInfo) -> str:
        if _is_qualified_model_id(value):
            return value
        raise ValueError(
            f"{info.field_name} must use the provider:model format, got {value!r}."
        )

    @model_validator(mode="after")
    def validate_ranges(self) -> "AppSettings":
        if self.min_rounds < 1:
            raise ValueError("min_rounds must be >= 1")
        if self.max_rounds < self.min_rounds:
            raise ValueError("max_rounds must be >= min_rounds")
        if self.scoring_max_concurrency < 1:
            raise ValueError("scoring_max_concurrency must be >= 1")
        if self.search_max_pages_per_round < 1:
            raise ValueError("search_max_pages_per_round must be >= 1")
        if self.search_max_attempts_per_round < 1:
            raise ValueError("search_max_attempts_per_round must be >= 1")
        if self.search_no_progress_limit < 1:
            raise ValueError("search_no_progress_limit must be >= 1")
        return self

    @property
    def project_root(self) -> Path:
        return Path.cwd()

    @property
    def prompt_dir(self) -> Path:
        return self.project_root / "src" / "cv_match" / "prompts"

    @property
    def spec_file(self) -> Path:
        return self.project_root / self.cts_spec_path

    @property
    def runs_path(self) -> Path:
        return self.project_root / self.runs_dir

    def require_cts_credentials(self) -> None:
        if self.mock_cts:
            return
        if not self.cts_tenant_key or not self.cts_tenant_secret:
            raise ValueError(
                "Real CTS mode requires CVMATCH_CTS_TENANT_KEY and CVMATCH_CTS_TENANT_SECRET."
            )

    def with_overrides(self, **overrides: object) -> "AppSettings":
        filtered = {key: value for key, value in overrides.items() if value is not None}
        return type(self).model_validate({**self.model_dump(), **filtered})
