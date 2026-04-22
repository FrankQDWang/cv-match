from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CompanySource = Literal["explicit_jd", "explicit_notes", "web_inferred", "candidate_backfill"]
CompanyIntent = Literal[
    "target",
    "similar_to_target",
    "competitor",
    "same_domain",
    "exclude",
    "client_company",
    "unknown",
]
CompanySearchUsage = Literal["keyword_term", "company_filter", "keyword_and_filter", "score_boost", "exclude", "holdout"]
CompanySourceType = Literal["web", "user_input", "local_pack"]


class CompanyEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    url: str
    snippet: str
    source_type: CompanySourceType


class TargetCompanyCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    aliases: list[str] = Field(default_factory=list)
    source: CompanySource
    intent: CompanyIntent
    confidence: float
    fit_axes: list[str] = Field(default_factory=list)
    search_usage: CompanySearchUsage
    evidence: list[CompanyEvidence] = Field(default_factory=list)
    rationale: str


class TargetCompanyPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    explicit_targets: list[TargetCompanyCandidate] = Field(default_factory=list)
    inferred_targets: list[TargetCompanyCandidate] = Field(default_factory=list)
    excluded_companies: list[str] = Field(default_factory=list)
    holdout_companies: list[str] = Field(default_factory=list)
    rejected_companies: list[str] = Field(default_factory=list)
    stop_reason: str | None = None
