# Target Company Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit target-company sourcing and bounded Bocha/Qwen web discovery to SeekTalent, with auditable artifacts and readable TUI trace blocks.

**Architecture:** Keep feature flags at `WorkflowRuntime` orchestration boundaries. Put company extraction, web discovery, query-term injection, and scheduling in a small isolated `seektalent.company_discovery` package. Reuse the existing controller, query-term pool, retrieval plan, CTS execution, scoring, reflection, artifacts, and TUI `progress_callback`.

**Tech Stack:** Python 3.12, Pydantic v2, Pydantic AI with OpenAI-compatible Bailian/Qwen, `httpx`, existing Rich/prompt-toolkit TUI, pytest.

---

## Scope Check

This plan implements one feature across related surfaces:

- target-company source modeling,
- explicit target bootstrap,
- bounded web discovery,
- query injection and scheduling,
- runtime orchestration,
- TUI progress rendering,
- docs and tests.

These pieces are coupled by a single approved spec: `docs/superpowers/specs/2026-04-22-target-company-discovery-design.md`. Do not split this into unrelated feature branches. Do not implement a local company knowledge pack or a second web provider in this plan.

## File Structure

Create:

- `src/seektalent/company_discovery/__init__.py`  
  Public exports for the small company discovery package.
- `src/seektalent/company_discovery/models.py`  
  Pydantic models for company evidence, target-company plans, web results, page reads, and model-step outputs.
- `src/seektalent/company_discovery/explicit.py`  
  Deterministic extraction from existing requirement fields plus simple JD/notes target/exclude labels.
- `src/seektalent/company_discovery/query_injection.py`  
  Pure function that turns accepted target companies into admitted `QueryTermCandidate` entries.
- `src/seektalent/company_discovery/scheduler.py`  
  Pure function that picks one untried target-company query for a runtime override.
- `src/seektalent/company_discovery/bocha_provider.py`  
  Minimal Bocha Web Search API adapter using `httpx`.
- `src/seektalent/company_discovery/page_reader.py`  
  Bounded HTML/text reader with simple cleanup and hard character limits.
- `src/seektalent/company_discovery/model_steps.py`  
  Pydantic AI calls for search planning, triage, evidence extraction, and reduction.
- `src/seektalent/company_discovery/service.py`  
  Orchestrates explicit bootstrap and bounded web discovery using injected provider/page/model dependencies.
- `tests/test_company_discovery.py`  
  Unit tests for pure package behavior and provider normalization.
- `tests/test_company_discovery_config.py`  
  Defaults and key validation tests.

Modify:

- `src/seektalent/models.py`  
  Extend query term literals and `RetrievalState` company-discovery state fields.
- `src/seektalent/config.py`  
  Add high-level feature flags, Bocha key, Qwen model config, and budget settings.
- `src/seektalent/default.env`  
  Add documented env defaults.
- `src/seektalent/runtime/orchestrator.py`  
  High-level routing only: bootstrap explicit companies, trigger web discovery, force company-seed decisions, write artifacts, emit progress events.
- `src/seektalent/controller/react_controller.py` and `src/seektalent/prompts/controller.md`  
  Show target-company term metadata and add one prompt rule.
- `src/seektalent/tui.py`  
  Render company discovery progress events as business trace blocks and label target-company rounds.
- `docs/configuration.md`  
  Document target-company and company-discovery settings.
- `docs/outputs.md`  
  Document company discovery artifacts.
- `tach.toml`  
  Add `seektalent.company_discovery` as a module and allow `seektalent.runtime` to depend on it.
- Existing tests under `tests/test_query_compiler.py`, `tests/test_query_plan.py`, `tests/test_runtime_state_flow.py`, and `tests/test_tui.py`.

Do not modify:

- `src/seektalent/clients/cts_client.py`
- `src/seektalent/scoring/scorer.py`
- `src/seektalent/reflection/critic.py`
- `src/seektalent/finalize/finalizer.py`
- `apps/`
- `experiments/`

## Task 1: Config And Shared Query Surface

**Files:**
- Modify: `src/seektalent/config.py`
- Modify: `src/seektalent/models.py`
- Modify: `src/seektalent/default.env`
- Modify: `tach.toml`
- Create: `tests/test_company_discovery_config.py`

- [ ] **Step 1: Write failing config and literal tests**

Create `tests/test_company_discovery_config.py` with:

```python
from __future__ import annotations

import pytest

from seektalent.config import AppSettings
from seektalent.models import QueryTermCandidate, RetrievalState
from tests.settings_factory import make_settings


def test_company_discovery_settings_defaults() -> None:
    settings = make_settings()

    assert settings.target_company_enabled is True
    assert settings.company_discovery_enabled is False
    assert settings.company_discovery_provider == "bocha"
    assert settings.company_discovery_model == "openai-chat:qwen3.5-flash"
    assert settings.company_discovery_reasoning_effort == "off"
    assert settings.company_discovery_max_search_calls == 4
    assert settings.company_discovery_max_results_per_query == 30
    assert settings.company_discovery_max_open_pages == 8
    assert settings.company_discovery_max_llm_calls == 8
    assert settings.company_discovery_timeout_seconds == 25
    assert settings.company_discovery_accepted_company_limit == 8
    assert settings.company_discovery_min_confidence == 0.65


def test_company_discovery_settings_validate_ranges() -> None:
    with pytest.raises(ValueError, match="company_discovery_max_search_calls must be >= 1"):
        make_settings(company_discovery_max_search_calls=0)

    with pytest.raises(ValueError, match="company_discovery_min_confidence must be between 0 and 1"):
        make_settings(company_discovery_min_confidence=1.5)


def test_query_term_candidate_accepts_target_company_metadata() -> None:
    candidate = QueryTermCandidate(
        term="火山引擎",
        source="company_discovery",
        category="company",
        priority=20,
        evidence="web evidence",
        first_added_round=2,
        retrieval_role="target_company",
        queryability="admitted",
        family="company.volcengine",
    )

    assert candidate.source == "company_discovery"
    assert candidate.category == "company"
    assert candidate.retrieval_role == "target_company"
    assert candidate.family == "company.volcengine"


def test_retrieval_state_can_store_company_discovery_state() -> None:
    state = RetrievalState(
        current_plan_version=0,
        target_company_plan={"accepted_companies": []},
        company_discovery_attempted=True,
        forced_company_seed_families=["company.volcengine"],
    )

    assert state.target_company_plan == {"accepted_companies": []}
    assert state.company_discovery_attempted is True
    assert state.forced_company_seed_families == ["company.volcengine"]
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
uv run pytest tests/test_company_discovery_config.py -v
```

Expected: fail because settings fields, literal values, and `RetrievalState` fields do not exist.

- [ ] **Step 3: Extend model literals and retrieval state**

In `src/seektalent/models.py`, replace the three query literal aliases near the top with:

```python
QueryTermSource = Literal["job_title", "jd", "notes", "reflection", "target_company", "company_discovery"]
QueryTermCategory = Literal["role_anchor", "domain", "tooling", "expansion", "company"]
QueryRetrievalRole = Literal[
    "role_anchor",
    "core_skill",
    "framework_tool",
    "domain_context",
    "target_company",
    "filter_only",
    "score_only",
]
```

In `RetrievalState`, add fields without importing the new package:

```python
class RetrievalState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_plan_version: int = 0
    query_term_pool: list[QueryTermCandidate] = Field(default_factory=list)
    sent_query_history: list[SentQueryRecord] = Field(default_factory=list)
    reflection_keyword_advice_history: list[ReflectionKeywordAdvice] = Field(default_factory=list)
    reflection_filter_advice_history: list[ReflectionFilterAdvice] = Field(default_factory=list)
    last_projection_result: ConstraintProjectionResult | None = None
    target_company_plan: dict[str, Any] | None = None
    company_discovery_attempted: bool = False
    forced_company_seed_families: list[str] = Field(default_factory=list)
```

This keeps `seektalent.models` from depending on `seektalent.company_discovery`.

- [ ] **Step 4: Add settings fields and validation**

In `src/seektalent/config.py`, add `company_discovery_model` to `MODEL_FIELDS`:

```python
MODEL_FIELDS = (
    "requirements_model",
    "controller_model",
    "scoring_model",
    "finalize_model",
    "reflection_model",
    "judge_model",
    "tui_summary_model",
    "company_discovery_model",
)
```

Add fields to `AppSettings` near the other feature/runtime settings:

```python
    target_company_enabled: bool = True
    company_discovery_enabled: bool = False
    company_discovery_provider: str = "bocha"
    bocha_api_key: str | None = None
    company_discovery_model: str = "openai-chat:qwen3.5-flash"
    company_discovery_reasoning_effort: ReasoningEffort = "off"
    company_discovery_max_search_calls: int = 4
    company_discovery_max_results_per_query: int = 30
    company_discovery_max_open_pages: int = 8
    company_discovery_max_llm_calls: int = 8
    company_discovery_timeout_seconds: int = 25
    company_discovery_accepted_company_limit: int = 8
    company_discovery_min_confidence: float = 0.65
```

Add range validation inside `validate_ranges`:

```python
        if self.company_discovery_provider != "bocha":
            raise ValueError("company_discovery_provider must be 'bocha'")
        if self.company_discovery_max_search_calls < 1:
            raise ValueError("company_discovery_max_search_calls must be >= 1")
        if self.company_discovery_max_results_per_query < 1:
            raise ValueError("company_discovery_max_results_per_query must be >= 1")
        if self.company_discovery_max_open_pages < 0:
            raise ValueError("company_discovery_max_open_pages must be >= 0")
        if self.company_discovery_max_llm_calls < 1:
            raise ValueError("company_discovery_max_llm_calls must be >= 1")
        if self.company_discovery_timeout_seconds < 1:
            raise ValueError("company_discovery_timeout_seconds must be >= 1")
        if self.company_discovery_accepted_company_limit < 1:
            raise ValueError("company_discovery_accepted_company_limit must be >= 1")
        if not 0 <= self.company_discovery_min_confidence <= 1:
            raise ValueError("company_discovery_min_confidence must be between 0 and 1")
```

Add the company discovery model to `preflight_models` later in Task 7 only when web discovery is enabled. Do not preflight the model when the feature is disabled.

- [ ] **Step 5: Add default env entries**

Append this block to `src/seektalent/default.env`:

```dotenv

SEEKTALENT_TARGET_COMPANY_ENABLED=true
SEEKTALENT_COMPANY_DISCOVERY_ENABLED=false
SEEKTALENT_COMPANY_DISCOVERY_PROVIDER=bocha
SEEKTALENT_BOCHA_API_KEY=
SEEKTALENT_COMPANY_DISCOVERY_MODEL=openai-chat:qwen3.5-flash
SEEKTALENT_COMPANY_DISCOVERY_REASONING_EFFORT=off
SEEKTALENT_COMPANY_DISCOVERY_MAX_SEARCH_CALLS=4
SEEKTALENT_COMPANY_DISCOVERY_MAX_RESULTS_PER_QUERY=30
SEEKTALENT_COMPANY_DISCOVERY_MAX_OPEN_PAGES=8
SEEKTALENT_COMPANY_DISCOVERY_MAX_LLM_CALLS=8
SEEKTALENT_COMPANY_DISCOVERY_TIMEOUT_SECONDS=25
SEEKTALENT_COMPANY_DISCOVERY_ACCEPTED_COMPANY_LIMIT=8
SEEKTALENT_COMPANY_DISCOVERY_MIN_CONFIDENCE=0.65
```

- [ ] **Step 6: Add tach module boundary**

In `tach.toml`, add:

```toml
[[modules]]
path = "seektalent.company_discovery"
depends_on = []
```

Update the `seektalent.runtime` dependency list to include `"seektalent.company_discovery"`.

- [ ] **Step 7: Run tests**

Run:

```bash
uv run pytest tests/test_company_discovery_config.py -v
```

Expected: pass.

- [ ] **Step 8: Commit**

Run:

```bash
git add src/seektalent/config.py src/seektalent/models.py src/seektalent/default.env tach.toml tests/test_company_discovery_config.py
git commit -m "Add company discovery config surface"
```

## Task 2: Company Plan Models, Injection, And Scheduler

**Files:**
- Create: `src/seektalent/company_discovery/__init__.py`
- Create: `src/seektalent/company_discovery/models.py`
- Create: `src/seektalent/company_discovery/query_injection.py`
- Create: `src/seektalent/company_discovery/scheduler.py`
- Create/Modify: `tests/test_company_discovery.py`
- Modify: `src/seektalent/retrieval/query_plan.py`

- [ ] **Step 1: Write failing model/injection/scheduler tests**

Create `tests/test_company_discovery.py` with this initial content:

```python
from __future__ import annotations

from seektalent.company_discovery.models import CompanyEvidence, TargetCompanyCandidate, TargetCompanyPlan
from seektalent.company_discovery.query_injection import inject_target_company_terms
from seektalent.company_discovery.scheduler import select_company_seed_terms
from seektalent.models import QueryTermCandidate, SentQueryRecord


def _anchor() -> QueryTermCandidate:
    return QueryTermCandidate(
        term="大模型",
        source="job_title",
        category="role_anchor",
        priority=1,
        evidence="title",
        first_added_round=0,
        retrieval_role="role_anchor",
        queryability="admitted",
        family="role.llm",
    )


def _skill() -> QueryTermCandidate:
    return QueryTermCandidate(
        term="vLLM",
        source="jd",
        category="tooling",
        priority=2,
        evidence="jd",
        first_added_round=0,
        retrieval_role="framework_tool",
        queryability="admitted",
        family="framework.vllm",
    )


def _plan() -> TargetCompanyPlan:
    evidence = CompanyEvidence(
        source="explicit_notes",
        title="notes",
        url=None,
        snippet="目标公司：火山引擎、阿里云",
    )
    return TargetCompanyPlan(
        accepted_companies=[
            TargetCompanyCandidate(
                name="火山引擎",
                aliases=["Volcengine"],
                source="explicit",
                intent="target",
                confidence=0.95,
                evidence=[evidence],
                search_usage="keyword",
            ),
            TargetCompanyCandidate(
                name="阿里云",
                aliases=["Aliyun", "阿里巴巴云"],
                source="explicit",
                intent="target",
                confidence=0.9,
                evidence=[evidence],
                search_usage="keyword",
            ),
        ],
        holdout_companies=[],
        rejected_companies=[],
        explicit_company_count=2,
        web_discovery_attempted=False,
    )


def test_inject_target_company_terms_adds_admitted_company_terms_once() -> None:
    pool = [_anchor(), _skill()]

    injected = inject_target_company_terms(pool, _plan(), round_no=1, source="target_company")
    reinjected = inject_target_company_terms(injected, _plan(), round_no=2, source="target_company")

    company_terms = [item for item in reinjected if item.retrieval_role == "target_company"]
    assert [item.term for item in company_terms] == ["火山引擎", "阿里云"]
    assert [item.family for item in company_terms] == ["company.火山引擎", "company.阿里云"]
    assert all(item.category == "company" for item in company_terms)
    assert all(item.queryability == "admitted" for item in company_terms)
    assert all(item.active for item in company_terms)


def test_scheduler_selects_one_untried_company_with_anchor() -> None:
    pool = inject_target_company_terms([_anchor(), _skill()], _plan(), round_no=1, source="target_company")

    terms = select_company_seed_terms(
        query_term_pool=pool,
        sent_query_history=[],
        round_no=1,
        include_skill=False,
    )

    assert terms == ["大模型", "火山引擎"]


def test_scheduler_can_include_one_skill_after_round_one() -> None:
    pool = inject_target_company_terms([_anchor(), _skill()], _plan(), round_no=2, source="target_company")

    terms = select_company_seed_terms(
        query_term_pool=pool,
        sent_query_history=[],
        round_no=3,
        include_skill=True,
    )

    assert terms == ["大模型", "火山引擎", "vLLM"]


def test_scheduler_skips_tried_company_families() -> None:
    pool = inject_target_company_terms([_anchor(), _skill()], _plan(), round_no=1, source="target_company")
    history = [
        SentQueryRecord(
            round_no=1,
            batch_no=1,
            requested_count=10,
            query_terms=["大模型", "火山引擎"],
            keyword_query="大模型 火山引擎",
            source_plan_version=1,
            rationale="company seed",
        )
    ]

    terms = select_company_seed_terms(
        query_term_pool=pool,
        sent_query_history=history,
        round_no=2,
        include_skill=False,
    )

    assert terms == ["大模型", "阿里云"]
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
uv run pytest tests/test_company_discovery.py -v
```

Expected: fail because package and functions do not exist.

- [ ] **Step 3: Add package exports**

Create `src/seektalent/company_discovery/__init__.py`:

```python
from seektalent.company_discovery.models import CompanyEvidence, TargetCompanyCandidate, TargetCompanyPlan
from seektalent.company_discovery.query_injection import inject_target_company_terms
from seektalent.company_discovery.scheduler import select_company_seed_terms

__all__ = [
    "CompanyEvidence",
    "TargetCompanyCandidate",
    "TargetCompanyPlan",
    "inject_target_company_terms",
    "select_company_seed_terms",
]
```

- [ ] **Step 4: Add models**

Create `src/seektalent/company_discovery/models.py`:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


EvidenceSource = Literal["explicit_notes", "explicit_jd", "web_search", "page_read"]
CompanySource = Literal["explicit", "web_inferred"]
CompanyIntent = Literal["target", "preferred_source", "exclude", "client_company", "holdout"]
SearchUsage = Literal["keyword", "keyword_and_skill", "holdout", "exclude"]
DiscoveryStopReason = Literal[
    "not_started",
    "completed",
    "timeout_partial_plan",
    "timeout_no_accepted_companies",
    "no_accepted_companies",
]


class CompanyEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: EvidenceSource
    title: str
    url: str | None = None
    snippet: str


class TargetCompanyCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    aliases: list[str] = Field(default_factory=list)
    source: CompanySource
    intent: CompanyIntent
    confidence: float = Field(ge=0, le=1)
    evidence: list[CompanyEvidence] = Field(default_factory=list)
    search_usage: SearchUsage = "keyword"


class TargetCompanyPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accepted_companies: list[TargetCompanyCandidate] = Field(default_factory=list)
    holdout_companies: list[TargetCompanyCandidate] = Field(default_factory=list)
    rejected_companies: list[TargetCompanyCandidate] = Field(default_factory=list)
    explicit_company_count: int = 0
    web_discovery_attempted: bool = False
    stop_reason: DiscoveryStopReason = "not_started"
    duplicate_company_names: list[str] = Field(default_factory=list)

    @property
    def has_accepted_companies(self) -> bool:
        return bool(self.accepted_companies)
```

- [ ] **Step 5: Add query injection**

Create `src/seektalent/company_discovery/query_injection.py`:

```python
from __future__ import annotations

from typing import Literal

from seektalent.company_discovery.models import TargetCompanyPlan
from seektalent.models import QueryTermCandidate


CompanyTermSource = Literal["target_company", "company_discovery"]


def canonical_company_key(name: str) -> str:
    return "".join(char for char in name.strip() if char.isalnum()) or "unknown"


def inject_target_company_terms(
    pool: list[QueryTermCandidate],
    plan: TargetCompanyPlan,
    *,
    round_no: int,
    source: CompanyTermSource,
) -> list[QueryTermCandidate]:
    output = list(pool)
    seen = {_term_key(item.term) for item in output}
    next_priority = _next_company_priority(output)
    for company in plan.accepted_companies:
        if company.search_usage in {"holdout", "exclude"} or company.intent in {"exclude", "client_company", "holdout"}:
            continue
        clean = " ".join(company.name.split()).strip()
        if not clean:
            continue
        key = _term_key(clean)
        if key in seen:
            continue
        seen.add(key)
        output.append(
            QueryTermCandidate(
                term=clean,
                source=source,
                category="company",
                priority=next_priority,
                evidence=_evidence_text(company.name, company.confidence),
                first_added_round=round_no,
                active=True,
                retrieval_role="target_company",
                queryability="admitted",
                family=f"company.{canonical_company_key(clean)}",
            )
        )
        next_priority += 1
    return output


def _term_key(term: str) -> str:
    return " ".join(term.split()).casefold()


def _next_company_priority(pool: list[QueryTermCandidate]) -> int:
    company_priorities = [item.priority for item in pool if item.retrieval_role == "target_company"]
    return max(company_priorities, default=19) + 1


def _evidence_text(name: str, confidence: float) -> str:
    return f"Target company candidate: {name}; confidence={confidence:.2f}."
```

- [ ] **Step 6: Add scheduler**

Create `src/seektalent/company_discovery/scheduler.py`:

```python
from __future__ import annotations

from seektalent.models import QueryTermCandidate, SentQueryRecord


def select_company_seed_terms(
    *,
    query_term_pool: list[QueryTermCandidate],
    sent_query_history: list[SentQueryRecord],
    round_no: int,
    include_skill: bool,
) -> list[str] | None:
    anchor = _first_anchor(query_term_pool)
    if anchor is None:
        return None
    tried_families = _tried_families(query_term_pool, sent_query_history)
    company = _first_untried_company(query_term_pool, tried_families)
    if company is None:
        return None
    terms = [anchor.term, company.term]
    if include_skill and round_no > 1:
        skill = _first_skill(query_term_pool, excluded_families={anchor.family, company.family})
        if skill is not None:
            terms.append(skill.term)
    return terms


def _first_anchor(pool: list[QueryTermCandidate]) -> QueryTermCandidate | None:
    anchors = [
        item
        for item in pool
        if item.active and item.queryability == "admitted" and item.retrieval_role == "role_anchor"
    ]
    return min(anchors, key=lambda item: (item.priority, item.first_added_round, item.term.casefold()), default=None)


def _first_untried_company(
    pool: list[QueryTermCandidate],
    tried_families: set[str],
) -> QueryTermCandidate | None:
    companies = [
        item
        for item in pool
        if item.active
        and item.queryability == "admitted"
        and item.retrieval_role == "target_company"
        and item.family not in tried_families
    ]
    return min(companies, key=lambda item: (item.priority, item.first_added_round, item.term.casefold()), default=None)


def _first_skill(
    pool: list[QueryTermCandidate],
    *,
    excluded_families: set[str],
) -> QueryTermCandidate | None:
    skills = [
        item
        for item in pool
        if item.active
        and item.queryability == "admitted"
        and item.retrieval_role in {"core_skill", "framework_tool", "domain_context"}
        and item.family not in excluded_families
    ]
    return min(skills, key=lambda item: (_skill_rank(item), item.priority, item.first_added_round), default=None)


def _skill_rank(item: QueryTermCandidate) -> int:
    if item.retrieval_role == "core_skill":
        return 0
    if item.retrieval_role == "framework_tool":
        return 1
    return 2


def _tried_families(
    pool: list[QueryTermCandidate],
    history: list[SentQueryRecord],
) -> set[str]:
    term_index = {_term_key(item.term): item for item in pool}
    return {
        candidate.family
        for record in history
        for term in record.query_terms
        if (candidate := term_index.get(_term_key(term))) is not None
    }


def _term_key(term: str) -> str:
    return " ".join(term.split()).casefold()
```

- [ ] **Step 7: Confirm query plan accepts target-company terms**

Run:

```bash
uv run pytest tests/test_company_discovery.py tests/test_query_plan.py -v
```

Expected: `tests/test_company_discovery.py` passes. Existing `tests/test_query_plan.py` should still pass because company terms are admitted non-anchor terms.

- [ ] **Step 8: Add a duplicate-family query-plan test**

Append to `tests/test_query_plan.py`:

```python
def test_query_plan_rejects_duplicate_company_families() -> None:
    pool = [
        QueryTermCandidate(
            term="大模型",
            source="job_title",
            category="role_anchor",
            priority=1,
            evidence="title",
            first_added_round=0,
            retrieval_role="role_anchor",
            queryability="admitted",
            family="role.llm",
        ),
        QueryTermCandidate(
            term="火山引擎",
            source="company_discovery",
            category="company",
            priority=20,
            evidence="company",
            first_added_round=1,
            retrieval_role="target_company",
            queryability="admitted",
            family="company.volcengine",
        ),
        QueryTermCandidate(
            term="Volcengine",
            source="company_discovery",
            category="company",
            priority=21,
            evidence="company alias",
            first_added_round=1,
            retrieval_role="target_company",
            queryability="admitted",
            family="company.volcengine",
        ),
    ]

    with pytest.raises(ValueError, match="must not repeat compiler families"):
        canonicalize_controller_query_terms(
            ["大模型", "火山引擎", "Volcengine"],
            round_no=2,
            title_anchor_term="大模型",
            query_term_pool=pool,
        )
```

- [ ] **Step 9: Run tests**

Run:

```bash
uv run pytest tests/test_company_discovery.py tests/test_query_plan.py -v
```

Expected: pass.

- [ ] **Step 10: Commit**

Run:

```bash
git add src/seektalent/company_discovery tests/test_company_discovery.py tests/test_query_plan.py
git commit -m "Add target company query injection and scheduling"
```

## Task 3: Explicit Target Company Bootstrap

**Files:**
- Create: `src/seektalent/company_discovery/explicit.py`
- Modify: `src/seektalent/company_discovery/service.py`
- Modify: `tests/test_company_discovery.py`

- [ ] **Step 1: Add failing explicit extraction tests**

Append to `tests/test_company_discovery.py`:

```python
from seektalent.company_discovery.explicit import build_explicit_company_plan
from seektalent.models import HardConstraintSlots, PreferenceSlots, RequirementSheet


def _requirement_sheet_for_companies() -> RequirementSheet:
    return RequirementSheet(
        role_title="大模型平台工程师",
        title_anchor_term="大模型",
        role_summary="负责大模型平台工程。",
        must_have_capabilities=["推理服务", "Kubernetes"],
        hard_constraints=HardConstraintSlots(company_names=["必须来自公司A"]),
        preferences=PreferenceSlots(preferred_companies=["火山引擎", "阿里云"]),
        initial_query_term_pool=[_anchor(), _skill()],
        scoring_rationale="优先看平台工程经验。",
    )


def test_build_explicit_company_plan_uses_requirement_preferences_and_notes() -> None:
    plan = build_explicit_company_plan(
        requirement_sheet=_requirement_sheet_for_companies(),
        jd="目标公司：腾讯云、百度智能云。",
        notes="不要：客户公司A。对标公司：华为云、MiniMax。",
    )

    accepted_names = [item.name for item in plan.accepted_companies]
    rejected_names = [item.name for item in plan.rejected_companies]
    assert accepted_names == ["火山引擎", "阿里云", "腾讯云", "百度智能云", "华为云", "MiniMax"]
    assert rejected_names == ["客户公司A"]
    assert plan.explicit_company_count == 6
    assert plan.web_discovery_attempted is False


def test_build_explicit_company_plan_dedupes_and_limits_noise() -> None:
    plan = build_explicit_company_plan(
        requirement_sheet=_requirement_sheet_for_companies(),
        jd="目标公司：火山引擎、火山引擎、阿里云。",
        notes="",
    )

    assert [item.name for item in plan.accepted_companies] == ["火山引擎", "阿里云"]
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
uv run pytest tests/test_company_discovery.py::test_build_explicit_company_plan_uses_requirement_preferences_and_notes tests/test_company_discovery.py::test_build_explicit_company_plan_dedupes_and_limits_noise -v
```

Expected: fail because `explicit.py` does not exist.

- [ ] **Step 3: Implement explicit extraction**

Create `src/seektalent/company_discovery/explicit.py`:

```python
from __future__ import annotations

import re

from seektalent.company_discovery.models import CompanyEvidence, TargetCompanyCandidate, TargetCompanyPlan
from seektalent.models import RequirementSheet, unique_strings

TARGET_LABELS = ("目标公司", "目标企业", "来源公司", "竞品公司", "对标公司", "优先公司")
EXCLUDE_LABELS = ("排除公司", "不要", "不考虑", "禁止")
SEGMENT_STOP_RE = re.compile(r"[\n。；;]")
SPLIT_RE = re.compile(r"[、,，/|｜]+")


def build_explicit_company_plan(
    *,
    requirement_sheet: RequirementSheet,
    jd: str,
    notes: str,
) -> TargetCompanyPlan:
    accepted: list[TargetCompanyCandidate] = []
    rejected: list[TargetCompanyCandidate] = []

    for name in requirement_sheet.preferences.preferred_companies:
        _append_candidate(accepted, name=name, evidence_source="explicit_notes", source_title="Requirement preferences")

    for name in _labeled_companies(jd, TARGET_LABELS):
        _append_candidate(accepted, name=name, evidence_source="explicit_jd", source_title="JD target-company label")

    for name in _labeled_companies(notes, TARGET_LABELS):
        _append_candidate(accepted, name=name, evidence_source="explicit_notes", source_title="Notes target-company label")

    for name in _labeled_companies(notes, EXCLUDE_LABELS):
        _append_candidate(
            rejected,
            name=name,
            evidence_source="explicit_notes",
            source_title="Notes exclude-company label",
            intent="exclude",
            search_usage="exclude",
        )

    accepted = _dedupe_candidates(accepted)
    rejected = _dedupe_candidates(rejected)
    rejected_keys = {_company_key(item.name) for item in rejected}
    accepted = [item for item in accepted if _company_key(item.name) not in rejected_keys]

    return TargetCompanyPlan(
        accepted_companies=accepted,
        holdout_companies=[],
        rejected_companies=rejected,
        explicit_company_count=len(accepted),
        web_discovery_attempted=False,
        stop_reason="completed",
    )


def _append_candidate(
    output: list[TargetCompanyCandidate],
    *,
    name: str,
    evidence_source: str,
    source_title: str,
    intent: str = "target",
    search_usage: str = "keyword",
) -> None:
    clean = _clean_company_name(name)
    if not clean:
        return
    output.append(
        TargetCompanyCandidate(
            name=clean,
            aliases=[],
            source="explicit",
            intent=intent,
            confidence=0.95 if intent != "exclude" else 1.0,
            evidence=[
                CompanyEvidence(
                    source=evidence_source,
                    title=source_title,
                    url=None,
                    snippet=clean,
                )
            ],
            search_usage=search_usage,
        )
    )


def _labeled_companies(text: str, labels: tuple[str, ...]) -> list[str]:
    values: list[str] = []
    for label in labels:
        for match in re.finditer(re.escape(label), text or ""):
            tail = text[match.end():]
            tail = tail.lstrip(" ：:为是包括包含")
            segment = SEGMENT_STOP_RE.split(tail, maxsplit=1)[0]
            values.extend(_split_company_segment(segment))
    return unique_strings(values)


def _split_company_segment(segment: str) -> list[str]:
    return [_clean_company_name(item) for item in SPLIT_RE.split(segment) if _clean_company_name(item)]


def _clean_company_name(name: str) -> str:
    clean = " ".join(str(name).split()).strip(" ：:，,。；;、")
    return clean if 1 < len(clean) <= 40 else ""


def _dedupe_candidates(candidates: list[TargetCompanyCandidate]) -> list[TargetCompanyCandidate]:
    seen: set[str] = set()
    output: list[TargetCompanyCandidate] = []
    for candidate in candidates:
        key = _company_key(candidate.name)
        if key in seen:
            continue
        seen.add(key)
        output.append(candidate)
    return output


def _company_key(name: str) -> str:
    return "".join(char.casefold() for char in name if char.isalnum())
```

Use `# type: ignore[arg-type]` only if the type checker objects to passing string literals into Pydantic literal fields. Prefer narrowing variables to the literal values if that is enough.

- [ ] **Step 4: Add service shell for explicit bootstrap**

Create `src/seektalent/company_discovery/service.py`:

```python
from __future__ import annotations

from seektalent.company_discovery.explicit import build_explicit_company_plan
from seektalent.company_discovery.models import TargetCompanyPlan
from seektalent.config import AppSettings
from seektalent.models import RequirementSheet


class CompanyDiscoveryService:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    async def bootstrap_explicit(
        self,
        *,
        requirement_sheet: RequirementSheet,
        jd: str,
        notes: str,
    ) -> TargetCompanyPlan:
        return build_explicit_company_plan(requirement_sheet=requirement_sheet, jd=jd, notes=notes)
```

- [ ] **Step 5: Run tests**

Run:

```bash
uv run pytest tests/test_company_discovery.py -v
```

Expected: pass.

- [ ] **Step 6: Commit**

Run:

```bash
git add src/seektalent/company_discovery tests/test_company_discovery.py
git commit -m "Add explicit target company extraction"
```

## Task 4: Bocha Provider And Bounded Page Reader

**Files:**
- Create: `src/seektalent/company_discovery/bocha_provider.py`
- Create: `src/seektalent/company_discovery/page_reader.py`
- Modify: `src/seektalent/company_discovery/models.py`
- Modify: `tests/test_company_discovery.py`

- [ ] **Step 1: Add failing provider and page reader tests**

Append to `tests/test_company_discovery.py`:

```python
import httpx

from seektalent.company_discovery.bocha_provider import BochaWebSearchProvider
from seektalent.company_discovery.page_reader import PageReader, clean_page_text
from tests.settings_factory import make_settings


def test_bocha_provider_normalizes_web_search_results() -> None:
    captured_requests: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(
            {
                "url": str(request.url),
                "authorization": request.headers.get("Authorization"),
                "json": request.read().decode("utf-8"),
            }
        )
        return httpx.Response(
            200,
            json={
                "data": {
                    "webPages": {
                        "value": [
                            {
                                "name": "火山引擎大模型服务平台",
                                "url": "https://example.com/volc",
                                "siteName": "火山引擎",
                                "snippet": "提供大模型推理服务",
                                "summary": "火山引擎提供模型服务和推理平台。",
                                "datePublished": "2026-04-01",
                            }
                        ]
                    }
                }
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = make_settings(bocha_api_key="bocha-test-key")
    provider = BochaWebSearchProvider(settings, http_client=client)

    results = asyncio.run(provider.search("大模型 推理 平台 公司", count=10))
    asyncio.run(client.aclose())

    assert captured_requests[0]["url"] == "https://api.bochaai.com/v1/web-search"
    assert captured_requests[0]["authorization"] == "Bearer bocha-test-key"
    assert '"query":"大模型 推理 平台 公司"' in str(captured_requests[0]["json"])
    assert '"count":10' in str(captured_requests[0]["json"])
    assert results[0].title == "火山引擎大模型服务平台"
    assert results[0].url == "https://example.com/volc"
    assert results[0].site_name == "火山引擎"
    assert results[0].summary == "火山引擎提供模型服务和推理平台。"


def test_bocha_provider_requires_key() -> None:
    provider = BochaWebSearchProvider(make_settings(bocha_api_key=None))

    with pytest.raises(ValueError, match="SEEKTALENT_BOCHA_API_KEY"):
        asyncio.run(provider.search("query", count=10))


def test_page_reader_cleans_and_truncates_html() -> None:
    html = "<html><head><script>bad()</script></head><body><h1>标题</h1><p>正文内容</p></body></html>"
    cleaned = clean_page_text(html, max_chars=6)

    assert cleaned == "标题 正文"


def test_page_reader_records_failed_reads_without_raising() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(404, text="missing")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    reader = PageReader(http_client=client)

    result = asyncio.run(reader.read("https://example.com/missing", timeout_s=1))
    asyncio.run(client.aclose())

    assert result.read_success is False
    assert result.url == "https://example.com/missing"
    assert "404" in result.error_message
```

Add imports at the top of `tests/test_company_discovery.py`:

```python
import asyncio
import pytest
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
uv run pytest tests/test_company_discovery.py -v
```

Expected: fail because provider/page models and files do not exist.

- [ ] **Step 3: Add web and page models**

Append to `src/seektalent/company_discovery/models.py`:

```python
class WebSearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: int
    title: str
    url: str
    site_name: str = ""
    snippet: str = ""
    summary: str = ""
    published_at: str | None = None


class PageReadResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    title: str = ""
    text: str = ""
    read_success: bool
    error_message: str | None = None
```

- [ ] **Step 4: Implement Bocha provider**

Create `src/seektalent/company_discovery/bocha_provider.py`:

```python
from __future__ import annotations

from typing import Any

import httpx

from seektalent.company_discovery.models import WebSearchResult
from seektalent.config import AppSettings

BOCHA_WEB_SEARCH_URL = "https://api.bochaai.com/v1/web-search"


class BochaWebSearchProvider:
    def __init__(self, settings: AppSettings, *, http_client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self.http_client = http_client

    async def search(self, query: str, *, count: int) -> list[WebSearchResult]:
        if not self.settings.bocha_api_key:
            raise ValueError("SEEKTALENT_BOCHA_API_KEY is required when company web discovery runs.")
        payload = {
            "query": query,
            "count": count,
            "summary": True,
        }
        headers = {"Authorization": f"Bearer {self.settings.bocha_api_key}"}
        if self.http_client is not None:
            response = await self.http_client.post(BOCHA_WEB_SEARCH_URL, json=payload, headers=headers)
            return _results_from_response(response)
        async with httpx.AsyncClient(timeout=self.settings.company_discovery_timeout_seconds) as client:
            response = await client.post(BOCHA_WEB_SEARCH_URL, json=payload, headers=headers)
            return _results_from_response(response)


def _results_from_response(response: httpx.Response) -> list[WebSearchResult]:
    response.raise_for_status()
    payload = response.json()
    raw_results = _result_items(payload)
    results: list[WebSearchResult] = []
    for index, item in enumerate(raw_results, start=1):
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        title = str(item.get("name") or item.get("title") or "").strip()
        if not url or not title:
            continue
        results.append(
            WebSearchResult(
                rank=index,
                title=title,
                url=url,
                site_name=str(item.get("siteName") or "").strip(),
                snippet=str(item.get("snippet") or "").strip(),
                summary=str(item.get("summary") or "").strip(),
                published_at=str(item.get("datePublished") or "").strip() or None,
            )
        )
    return results


def _result_items(payload: dict[str, Any]) -> list[Any]:
    data = payload.get("data")
    if not isinstance(data, dict):
        return []
    web_pages = data.get("webPages")
    if isinstance(web_pages, dict) and isinstance(web_pages.get("value"), list):
        return web_pages["value"]
    if isinstance(data.get("results"), list):
        return data["results"]
    return []
```

- [ ] **Step 5: Implement page reader**

Create `src/seektalent/company_discovery/page_reader.py`:

```python
from __future__ import annotations

import re

import httpx

from seektalent.company_discovery.models import PageReadResult

SCRIPT_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


class PageReader:
    def __init__(self, *, http_client: httpx.AsyncClient | None = None, max_chars: int = 12000) -> None:
        self.http_client = http_client
        self.max_chars = max_chars

    async def read(self, url: str, *, timeout_s: float) -> PageReadResult:
        try:
            if self.http_client is not None:
                response = await self.http_client.get(url, timeout=timeout_s)
            else:
                async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True) as client:
                    response = await client.get(url)
            response.raise_for_status()
        except Exception as exc:
            return PageReadResult(url=url, read_success=False, error_message=str(exc))
        text = response.text
        return PageReadResult(
            url=url,
            title=_extract_title(text),
            text=clean_page_text(text, max_chars=self.max_chars),
            read_success=True,
            error_message=None,
        )


def clean_page_text(html: str, *, max_chars: int) -> str:
    without_scripts = SCRIPT_RE.sub(" ", html)
    without_tags = TAG_RE.sub(" ", without_scripts)
    cleaned = SPACE_RE.sub(" ", without_tags).strip()
    return cleaned[:max_chars].rstrip()


def _extract_title(html: str) -> str:
    match = TITLE_RE.search(html)
    if not match:
        return ""
    return SPACE_RE.sub(" ", TAG_RE.sub(" ", match.group(1))).strip()
```

- [ ] **Step 6: Run tests**

Run:

```bash
uv run pytest tests/test_company_discovery.py -v
```

Expected: pass.

- [ ] **Step 7: Commit**

Run:

```bash
git add src/seektalent/company_discovery tests/test_company_discovery.py
git commit -m "Add Bocha search provider and page reader"
```

## Task 5: Qwen Model Steps And Bounded Web Discovery Service

**Files:**
- Create: `src/seektalent/company_discovery/model_steps.py`
- Modify: `src/seektalent/company_discovery/models.py`
- Modify: `src/seektalent/company_discovery/service.py`
- Modify: `tests/test_company_discovery.py`

- [ ] **Step 1: Add failing web discovery service tests with stubs**

Append to `tests/test_company_discovery.py`:

```python
from seektalent.company_discovery.models import (
    CompanyDiscoveryInput,
    CompanySearchTask,
    PageReadResult,
    PageTriageResult,
    WebSearchResult,
)
from seektalent.company_discovery.service import CompanyDiscoveryService


class StubProvider:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def search(self, query: str, *, count: int) -> list[WebSearchResult]:
        self.queries.append(query)
        return [
            WebSearchResult(
                rank=1,
                title="火山引擎大模型服务平台",
                url="https://example.com/volc",
                site_name="火山引擎",
                snippet="大模型服务平台",
                summary="火山引擎提供推理服务和模型平台。",
            )
        ]


class StubReader:
    async def read(self, url: str, *, timeout_s: float):
        del timeout_s
        return PageReadResult(url=url, title="火山引擎", text="火山引擎 大模型 推理平台 GPU", read_success=True)


class StubSteps:
    async def plan_search_queries(self, discovery_input: CompanyDiscoveryInput) -> list[CompanySearchTask]:
        assert discovery_input.role_title == "大模型平台工程师"
        return [
            CompanySearchTask(
                query_id="q1",
                query="大模型 推理平台 GPU 公司",
                intent="market_map",
                rationale="找相似人才来源公司",
            )
        ]

    async def triage_search_results(self, results: list[WebSearchResult]) -> PageTriageResult:
        return PageTriageResult(selected_urls=[results[0].url], rationale="官方产品页相关")

    async def extract_company_evidence(self, page_reads, search_results):
        del page_reads, search_results
        evidence = CompanyEvidence(
            source="page_read",
            title="火山引擎",
            url="https://example.com/volc",
            snippet="火山引擎提供推理服务和模型平台。",
        )
        return [
            TargetCompanyCandidate(
                name="火山引擎",
                aliases=["Volcengine"],
                source="web_inferred",
                intent="target",
                confidence=0.88,
                evidence=[evidence],
                search_usage="keyword",
            )
        ]

    async def reduce_company_plan(self, candidates, discovery_input, *, stop_reason):
        del discovery_input
        return TargetCompanyPlan(
            accepted_companies=candidates,
            holdout_companies=[],
            rejected_companies=[],
            explicit_company_count=0,
            web_discovery_attempted=True,
            stop_reason=stop_reason,
        )


def test_company_discovery_service_runs_bounded_web_flow() -> None:
    provider = StubProvider()
    service = CompanyDiscoveryService(
        make_settings(company_discovery_enabled=True, bocha_api_key="key"),
        search_provider=provider,
        page_reader=StubReader(),
        model_steps=StubSteps(),
    )
    requirement_sheet = _requirement_sheet_for_companies().model_copy(update={"preferences": PreferenceSlots()})

    result = asyncio.run(
        service.discover_web(
            requirement_sheet=requirement_sheet,
            round_no=2,
            trigger_reason="low recall",
        )
    )

    assert provider.queries == ["大模型 推理平台 GPU 公司"]
    assert [item.name for item in result.plan.accepted_companies] == ["火山引擎"]
    assert result.plan.web_discovery_attempted is True
    assert result.discovery_input is not None
    assert result.triage is not None
    assert [item.name for item in result.evidence_candidates] == ["火山引擎"]
    assert result.search_result_count == 1
    assert result.opened_page_count == 1


def test_company_discovery_service_timeout_reduces_partial_evidence(monkeypatch) -> None:
    service = CompanyDiscoveryService(
        make_settings(company_discovery_timeout_seconds=1, bocha_api_key="key"),
        search_provider=StubProvider(),
        page_reader=StubReader(),
        model_steps=StubSteps(),
    )
    monkeypatch.setattr(service, "_deadline_reached", lambda deadline: True)

    result = asyncio.run(
        service.discover_web(
            requirement_sheet=_requirement_sheet_for_companies(),
            round_no=2,
            trigger_reason="low recall",
        )
    )

    assert result.plan.web_discovery_attempted is True
    assert result.plan.stop_reason == "timeout_no_accepted_companies"
    assert result.plan.accepted_companies == []
```

- [ ] **Step 2: Run failing service tests**

Run:

```bash
uv run pytest tests/test_company_discovery.py::test_company_discovery_service_runs_bounded_web_flow tests/test_company_discovery.py::test_company_discovery_service_timeout_reduces_partial_evidence -v
```

Expected: fail because service web discovery models and methods do not exist.

- [ ] **Step 3: Add discovery workflow models**

Append to `src/seektalent/company_discovery/models.py`:

```python
SearchIntent = Literal["market_map", "competitor_map", "role_evidence", "industry_list"]


class CompanyDiscoveryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_title: str
    title_anchor_term: str
    must_have_capabilities: list[str] = Field(default_factory=list)
    preferred_domains: list[str] = Field(default_factory=list)
    preferred_backgrounds: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)


class CompanySearchTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str
    query: str
    intent: SearchIntent
    rationale: str


class PageTriageResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selected_urls: list[str] = Field(default_factory=list)
    rationale: str = ""


class CompanySearchPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tasks: list[CompanySearchTask] = Field(default_factory=list)


class CompanyEvidenceExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates: list[TargetCompanyCandidate] = Field(default_factory=list)


class CompanyDiscoveryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan: TargetCompanyPlan
    discovery_input: CompanyDiscoveryInput | None = None
    search_tasks: list[CompanySearchTask] = Field(default_factory=list)
    search_results: list[WebSearchResult] = Field(default_factory=list)
    triage: PageTriageResult | None = None
    page_reads: list[PageReadResult] = Field(default_factory=list)
    evidence_candidates: list[TargetCompanyCandidate] = Field(default_factory=list)
    search_result_count: int = 0
    opened_page_count: int = 0
    trigger_reason: str
```

- [ ] **Step 4: Implement Qwen model steps**

Create `src/seektalent/company_discovery/model_steps.py`:

```python
from __future__ import annotations

from typing import cast

from pydantic_ai import Agent

from seektalent.company_discovery.models import (
    CompanyDiscoveryInput,
    CompanyEvidenceExtraction,
    CompanySearchPlan,
    CompanySearchTask,
    PageReadResult,
    PageTriageResult,
    TargetCompanyCandidate,
    TargetCompanyPlan,
    WebSearchResult,
)
from seektalent.config import AppSettings
from seektalent.llm import build_model, build_model_settings, build_output_spec


class CompanyDiscoveryModelSteps:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    async def plan_search_queries(self, discovery_input: CompanyDiscoveryInput) -> list[CompanySearchTask]:
        agent = self._agent(CompanySearchPlan, "You generate bounded target-company web search tasks.")
        result = await agent.run(_planner_prompt(discovery_input))
        plan = cast(CompanySearchPlan, result.output)
        return plan.tasks[: self.settings.company_discovery_max_search_calls]

    async def triage_search_results(self, results: list[WebSearchResult]) -> PageTriageResult:
        agent = self._agent(PageTriageResult, "You select web pages worth opening for target-company discovery.")
        result = await agent.run(_triage_prompt(results))
        return result.output

    async def extract_company_evidence(
        self,
        page_reads: list[PageReadResult],
        search_results: list[WebSearchResult],
    ) -> list[TargetCompanyCandidate]:
        agent = self._agent(CompanyEvidenceExtraction, "You extract evidenced target-company candidates.")
        result = await agent.run(_evidence_prompt(page_reads, search_results))
        extraction = cast(CompanyEvidenceExtraction, result.output)
        return extraction.candidates

    async def reduce_company_plan(
        self,
        candidates: list[TargetCompanyCandidate],
        discovery_input: CompanyDiscoveryInput,
        *,
        stop_reason: str,
    ) -> TargetCompanyPlan:
        agent = self._agent(TargetCompanyPlan, "You merge company aliases and return an evidence-based plan.")
        result = await agent.run(_reducer_prompt(candidates, discovery_input, stop_reason=stop_reason))
        return result.output

    def _agent(self, output_type, system_prompt: str):
        model = build_model(self.settings.company_discovery_model)
        return cast(
            Agent[None, object],
            Agent(
                model=model,
                output_type=build_output_spec(self.settings.company_discovery_model, model, output_type),
                system_prompt=system_prompt,
                model_settings=build_model_settings(
                    self.settings,
                    self.settings.company_discovery_model,
                    reasoning_effort=self.settings.company_discovery_reasoning_effort,
                ),
                retries=0,
                output_retries=2,
            ),
        )


def _planner_prompt(discovery_input: CompanyDiscoveryInput) -> str:
    return (
        "Generate 3-4 web search tasks for discovering target source companies. "
        "Do not output company conclusions.\n"
        f"INPUT\n{discovery_input.model_dump_json()}"
    )


def _triage_prompt(results: list[WebSearchResult]) -> str:
    compact = [item.model_dump(mode="json") for item in results[:50]]
    return (
        "Select at most 8 URLs worth opening. Prefer industry lists, recruiting pages, official product pages, "
        "and technical blogs. Avoid generic SEO pages.\n"
        f"RESULTS\n{compact}"
    )


def _evidence_prompt(page_reads: list[PageReadResult], search_results: list[WebSearchResult]) -> str:
    pages = [item.model_dump(mode="json") for item in page_reads]
    snippets = [item.model_dump(mode="json") for item in search_results[:20]]
    return (
        "Extract target-company candidates only when evidence supports similar teams or talent-source value. "
        "Do not accept companies merely because they use a technology.\n"
        f"PAGES\n{pages}\nSEARCH_SNIPPETS\n{snippets}"
    )


def _reducer_prompt(
    candidates: list[TargetCompanyCandidate],
    discovery_input: CompanyDiscoveryInput,
    *,
    stop_reason: str,
) -> str:
    payload = {
        "input": discovery_input.model_dump(mode="json"),
        "candidates": [item.model_dump(mode="json") for item in candidates],
        "stop_reason": stop_reason,
    }
    return (
        "Merge aliases, remove duplicates, reject weak evidence, and return TargetCompanyPlan. "
        "Accepted companies must have evidence and confidence >= configured threshold when possible.\n"
        f"PAYLOAD\n{payload}"
    )
```

- [ ] **Step 5: Implement bounded web discovery service**

Replace `src/seektalent/company_discovery/service.py` with:

```python
from __future__ import annotations

from time import perf_counter

from seektalent.company_discovery.bocha_provider import BochaWebSearchProvider
from seektalent.company_discovery.explicit import build_explicit_company_plan
from seektalent.company_discovery.model_steps import CompanyDiscoveryModelSteps
from seektalent.company_discovery.models import (
    CompanyDiscoveryInput,
    CompanyDiscoveryResult,
    TargetCompanyPlan,
    WebSearchResult,
)
from seektalent.company_discovery.page_reader import PageReader
from seektalent.config import AppSettings
from seektalent.models import RequirementSheet


class CompanyDiscoveryService:
    def __init__(
        self,
        settings: AppSettings,
        *,
        search_provider=None,
        page_reader=None,
        model_steps=None,
    ) -> None:
        self.settings = settings
        self.search_provider = search_provider or BochaWebSearchProvider(settings)
        self.page_reader = page_reader or PageReader()
        self.model_steps = model_steps or CompanyDiscoveryModelSteps(settings)

    async def bootstrap_explicit(
        self,
        *,
        requirement_sheet: RequirementSheet,
        jd: str,
        notes: str,
    ) -> TargetCompanyPlan:
        return build_explicit_company_plan(requirement_sheet=requirement_sheet, jd=jd, notes=notes)

    async def discover_web(
        self,
        *,
        requirement_sheet: RequirementSheet,
        round_no: int,
        trigger_reason: str,
    ) -> CompanyDiscoveryResult:
        del round_no
        if not self.settings.bocha_api_key:
            raise ValueError("SEEKTALENT_BOCHA_API_KEY is required when company web discovery runs.")
        deadline = perf_counter() + self.settings.company_discovery_timeout_seconds
        discovery_input = build_discovery_input(requirement_sheet)
        search_tasks = []
        search_results: list[WebSearchResult] = []
        triage = None
        page_reads = []
        candidates = []

        if self._deadline_reached(deadline):
            return _empty_timeout_result(trigger_reason=trigger_reason)

        search_tasks = await self.model_steps.plan_search_queries(discovery_input)
        for task in search_tasks[: self.settings.company_discovery_max_search_calls]:
            if self._deadline_reached(deadline):
                break
            results = await self.search_provider.search(
                task.query,
                count=self.settings.company_discovery_max_results_per_query,
            )
            search_results.extend(results)
        search_results = _dedupe_results(search_results)

        if self._deadline_reached(deadline):
            plan = await self.model_steps.reduce_company_plan(
                candidates,
                discovery_input,
                stop_reason="timeout_no_accepted_companies",
            )
            return _result(
                plan,
                search_tasks,
                search_results,
                page_reads,
                trigger_reason,
                discovery_input=discovery_input,
                evidence_candidates=candidates,
            )

        triage = await self.model_steps.triage_search_results(search_results)
        selected_urls = triage.selected_urls[: self.settings.company_discovery_max_open_pages]
        for url in selected_urls:
            if self._deadline_reached(deadline):
                break
            page_reads.append(await self.page_reader.read(url, timeout_s=4))

        if not self._deadline_reached(deadline):
            candidates = await self.model_steps.extract_company_evidence(page_reads, search_results)
            stop_reason = "completed"
        else:
            stop_reason = "timeout_no_accepted_companies"

        plan = await self.model_steps.reduce_company_plan(
            candidates,
            discovery_input,
            stop_reason=stop_reason,
        )
        if stop_reason == "timeout_no_accepted_companies" and plan.accepted_companies:
            plan = plan.model_copy(update={"stop_reason": "timeout_partial_plan"})
        return _result(
            plan,
            search_tasks,
            search_results,
            page_reads,
            trigger_reason,
            discovery_input=discovery_input,
            triage=triage,
            evidence_candidates=candidates,
        )

    def _deadline_reached(self, deadline: float) -> bool:
        return perf_counter() >= deadline


def build_discovery_input(requirement_sheet: RequirementSheet) -> CompanyDiscoveryInput:
    return CompanyDiscoveryInput(
        role_title=requirement_sheet.role_title,
        title_anchor_term=requirement_sheet.title_anchor_term,
        must_have_capabilities=requirement_sheet.must_have_capabilities[:6],
        preferred_domains=requirement_sheet.preferences.preferred_domains[:4],
        preferred_backgrounds=requirement_sheet.preferences.preferred_backgrounds[:4],
        locations=requirement_sheet.hard_constraints.locations[:6],
        exclusions=requirement_sheet.exclusion_signals[:6],
    )


def _dedupe_results(results: list[WebSearchResult]) -> list[WebSearchResult]:
    seen: set[str] = set()
    output: list[WebSearchResult] = []
    for result in results:
        key = result.url.strip().casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(result)
    return output


def _empty_timeout_result(*, trigger_reason: str) -> CompanyDiscoveryResult:
    return CompanyDiscoveryResult(
        plan=TargetCompanyPlan(web_discovery_attempted=True, stop_reason="timeout_no_accepted_companies"),
        trigger_reason=trigger_reason,
    )


def _result(
    plan: TargetCompanyPlan,
    search_tasks,
    search_results: list[WebSearchResult],
    page_reads,
    trigger_reason: str,
    discovery_input: CompanyDiscoveryInput | None = None,
    triage=None,
    evidence_candidates=None,
) -> CompanyDiscoveryResult:
    return CompanyDiscoveryResult(
        plan=plan,
        discovery_input=discovery_input,
        search_tasks=list(search_tasks),
        search_results=search_results,
        triage=triage,
        page_reads=list(page_reads),
        evidence_candidates=list(evidence_candidates or []),
        search_result_count=len(search_results),
        opened_page_count=len(page_reads),
        trigger_reason=trigger_reason,
    )
```

Remove unused imports after running Ruff or test collection. If `unique_strings` is unused, delete that import.

- [ ] **Step 6: Run tests**

Run:

```bash
uv run pytest tests/test_company_discovery.py -v
```

Expected: pass.

- [ ] **Step 7: Commit**

Run:

```bash
git add src/seektalent/company_discovery tests/test_company_discovery.py
git commit -m "Add bounded company web discovery workflow"
```

## Task 6: Runtime Explicit Bootstrap And Company Seed Override

**Files:**
- Modify: `src/seektalent/runtime/orchestrator.py`
- Modify: `src/seektalent/runtime/context_builder.py` if needed for term details
- Modify: `tests/test_runtime_state_flow.py`

- [ ] **Step 1: Add failing runtime explicit bootstrap test**

Append to `tests/test_runtime_state_flow.py`:

```python
class CompanyRequirementExtractor:
    async def extract_with_draft(self, *, input_truth) -> tuple[RequirementExtractionDraft, RequirementSheet]:
        del input_truth
        draft = RequirementExtractionDraft(
            role_title="大模型平台工程师",
            title_anchor_term="大模型",
            jd_query_terms=["vLLM"],
            role_summary="Build LLM platform.",
            must_have_capabilities=["大模型", "vLLM"],
            preferred_companies=["火山引擎"],
            scoring_rationale="Score LLM platform first.",
        )
        return draft, RequirementSheet(
            role_title="大模型平台工程师",
            title_anchor_term="大模型",
            role_summary="Build LLM platform.",
            must_have_capabilities=["大模型", "vLLM"],
            preferences=PreferenceSlots(preferred_companies=["火山引擎"]),
            initial_query_term_pool=[
                QueryTermCandidate(
                    term="大模型",
                    source="job_title",
                    category="role_anchor",
                    priority=1,
                    evidence="title",
                    first_added_round=0,
                    retrieval_role="role_anchor",
                    queryability="admitted",
                    family="role.llm",
                ),
                QueryTermCandidate(
                    term="vLLM",
                    source="jd",
                    category="tooling",
                    priority=2,
                    evidence="jd",
                    first_added_round=0,
                    retrieval_role="framework_tool",
                    queryability="admitted",
                    family="framework.vllm",
                ),
            ],
            scoring_rationale="Score LLM platform first.",
        )


class GenericFirstController:
    last_validator_retry_count = 0

    async def decide(self, *, context):
        return SearchControllerDecision(
            thought_summary="Generic search.",
            action="search_cts",
            decision_rationale="Controller chose generic skill search.",
            proposed_query_terms=["大模型", "vLLM"],
            proposed_filter_plan=ProposedFilterPlan(),
        )


def test_runtime_bootstraps_explicit_company_and_forces_seed_round(tmp_path: Path) -> None:
    settings = make_settings(
        runs_dir=str(tmp_path / "runs"),
        mock_cts=True,
        min_rounds=1,
        max_rounds=1,
        target_company_enabled=True,
    )
    runtime = WorkflowRuntime(settings)
    runtime_any = cast(Any, runtime)
    runtime_any.requirement_extractor = CompanyRequirementExtractor()
    runtime_any.controller = GenericFirstController()
    runtime_any.reflection_critic = SequenceReflection()
    runtime_any.resume_scorer = StubScorer()
    runtime_any.finalizer = StubFinalizer()
    tracer = RunTracer(tmp_path / "trace-runs")
    progress_events = []

    try:
        run_state = asyncio.run(
            runtime._build_run_state(
                job_title="大模型平台工程师",
                jd="目标公司：火山引擎。",
                notes="",
                tracer=tracer,
                progress_callback=progress_events.append,
            )
        )
        asyncio.run(runtime._run_rounds(run_state=run_state, tracer=tracer, progress_callback=progress_events.append))
    finally:
        tracer.close()

    company_terms = [item for item in run_state.retrieval_state.query_term_pool if item.retrieval_role == "target_company"]
    assert [item.term for item in company_terms] == ["火山引擎"]
    assert run_state.round_history[0].controller_decision.proposed_query_terms == ["大模型", "火山引擎"]
    assert any(event.type == "company_explicit_bootstrap_completed" for event in progress_events)
```

Add missing imports:

```python
from seektalent.models import PreferenceSlots
```

- [ ] **Step 2: Run failing test**

Run:

```bash
uv run pytest tests/test_runtime_state_flow.py::test_runtime_bootstraps_explicit_company_and_forces_seed_round -v
```

Expected: fail because runtime does not instantiate service, inject terms, or force company seed.

- [ ] **Step 3: Wire service into runtime**

In `src/seektalent/runtime/orchestrator.py`, add imports:

```python
from seektalent.company_discovery import inject_target_company_terms, select_company_seed_terms
from seektalent.company_discovery.models import TargetCompanyPlan
from seektalent.company_discovery.service import CompanyDiscoveryService
```

In `WorkflowRuntime.__init__`, add:

```python
        self.company_discovery = CompanyDiscoveryService(settings)
```

- [ ] **Step 4: Add explicit bootstrap helper**

Add this method to `WorkflowRuntime`:

```python
    async def _bootstrap_target_companies(
        self,
        *,
        run_state: RunState,
        tracer: RunTracer,
        jd: str,
        notes: str,
        progress_callback: ProgressCallback | None,
    ) -> None:
        if not self.settings.target_company_enabled:
            return
        plan = await self.company_discovery.bootstrap_explicit(
            requirement_sheet=run_state.requirement_sheet,
            jd=jd,
            notes=notes,
        )
        run_state.retrieval_state.target_company_plan = plan.model_dump(mode="json")
        run_state.retrieval_state.query_term_pool = inject_target_company_terms(
            run_state.retrieval_state.query_term_pool,
            plan,
            round_no=0,
            source="target_company",
        )
        tracer.write_json("company_discovery/bootstrap_plan.json", plan.model_dump(mode="json"))
        if plan.accepted_companies or plan.rejected_companies:
            self._emit_progress(
                progress_callback,
                "company_explicit_bootstrap_completed",
                self._company_bootstrap_message(plan),
                payload={
                    "stage": "company_discovery",
                    "accepted_companies": [item.name for item in plan.accepted_companies],
                    "rejected_companies": [item.name for item in plan.rejected_companies],
                    "next_query_terms": self._next_company_seed_terms(run_state, round_no=1) or [],
                },
            )
```

Add helpers:

```python
    def _company_bootstrap_message(self, plan: TargetCompanyPlan) -> str:
        accepted = ", ".join(item.name for item in plan.accepted_companies) or "none"
        rejected = ", ".join(item.name for item in plan.rejected_companies) or "none"
        return f"Target company bootstrap completed; accepted={accepted}; rejected={rejected}."

    def _target_company_plan(self, run_state: RunState) -> TargetCompanyPlan | None:
        payload = run_state.retrieval_state.target_company_plan
        if payload is None:
            return None
        return TargetCompanyPlan.model_validate(payload)

    def _next_company_seed_terms(self, run_state: RunState, *, round_no: int) -> list[str] | None:
        return select_company_seed_terms(
            query_term_pool=run_state.retrieval_state.query_term_pool,
            sent_query_history=run_state.retrieval_state.sent_query_history,
            round_no=round_no,
            include_skill=round_no > 1,
        )
```

Call `_bootstrap_target_companies` inside `_build_run_state` after `run_state` is created and before writing `requirement_sheet.json`:

```python
        if self.settings.target_company_enabled:
            await self._bootstrap_target_companies(
                run_state=run_state,
                tracer=tracer,
                jd=jd,
                notes=notes,
                progress_callback=progress_callback,
            )
```

- [ ] **Step 5: Add company seed override**

Add method:

```python
    def _force_company_seed_decision(
        self,
        *,
        run_state: RunState,
        round_no: int,
        reason: str,
    ) -> SearchControllerDecision | None:
        query_terms = self._next_company_seed_terms(run_state, round_no=round_no)
        if query_terms is None:
            return None
        family = self._company_family_for_terms(run_state, query_terms)
        if family is not None and family not in run_state.retrieval_state.forced_company_seed_families:
            run_state.retrieval_state.forced_company_seed_families.append(family)
        return SearchControllerDecision(
            thought_summary="Runtime override: target company seed search.",
            action="search_cts",
            decision_rationale=f"Runtime target-company seed: {reason}",
            proposed_query_terms=query_terms,
            proposed_filter_plan=build_default_filter_plan(run_state.requirement_sheet),
            response_to_reflection=f"Runtime override: {reason}" if run_state.round_history else None,
        )

    def _company_family_for_terms(self, run_state: RunState, terms: list[str]) -> str | None:
        index = {self._query_term_key(item.term): item for item in run_state.retrieval_state.query_term_pool}
        for term in terms:
            candidate = index.get(self._query_term_key(term))
            if candidate is not None and candidate.retrieval_role == "target_company":
                return candidate.family
        return None
```

In `_run_rounds`, after the existing `controller_decision` sanitize/force-continue branch and before writing `controller_decision.json`, add:

```python
            company_seed_decision = self._maybe_force_company_seed_before_search(
                run_state=run_state,
                round_no=round_no,
                controller_decision=controller_decision,
            )
            if company_seed_decision is not None:
                controller_decision = company_seed_decision
```

Add helper:

```python
    def _maybe_force_company_seed_before_search(
        self,
        *,
        run_state: RunState,
        round_no: int,
        controller_decision: ControllerDecision,
    ) -> SearchControllerDecision | None:
        if not self.settings.target_company_enabled:
            return None
        if isinstance(controller_decision, SearchControllerDecision) and self._decision_uses_target_company(
            run_state,
            controller_decision,
        ):
            return None
        plan = self._target_company_plan(run_state)
        if plan is None or not plan.accepted_companies:
            return None
        if round_no != 1 and run_state.retrieval_state.company_discovery_attempted is False:
            return None
        query_terms = self._next_company_seed_terms(run_state, round_no=round_no)
        if query_terms is None:
            return None
        family = self._company_family_for_terms(run_state, query_terms)
        if family is not None and family in run_state.retrieval_state.forced_company_seed_families:
            return None
        return self._force_company_seed_decision(
            run_state=run_state,
            round_no=round_no,
            reason="target companies are available and need one validation search.",
        )

    def _decision_uses_target_company(self, run_state: RunState, decision: SearchControllerDecision) -> bool:
        index = {self._query_term_key(item.term): item for item in run_state.retrieval_state.query_term_pool}
        return any(
            (candidate := index.get(self._query_term_key(term))) is not None
            and candidate.retrieval_role == "target_company"
            for term in decision.proposed_query_terms
        )
```

The `forced_company_seed_families` check keeps the runtime override from forcing the same company family twice.

- [ ] **Step 6: Run focused runtime test**

Run:

```bash
uv run pytest tests/test_runtime_state_flow.py::test_runtime_bootstraps_explicit_company_and_forces_seed_round -v
```

Expected: pass.

- [ ] **Step 7: Run broader runtime state tests**

Run:

```bash
uv run pytest tests/test_runtime_state_flow.py -v
```

Expected: pass.

- [ ] **Step 8: Commit**

Run:

```bash
git add src/seektalent/runtime/orchestrator.py tests/test_runtime_state_flow.py
git commit -m "Integrate explicit target company seed search"
```

## Task 7: Runtime Web Discovery Trigger, Artifacts, And Timeout Semantics

**Files:**
- Modify: `src/seektalent/runtime/orchestrator.py`
- Modify: `src/seektalent/llm.py`
- Modify: `tests/test_runtime_state_flow.py`

- [ ] **Step 1: Add failing runtime web discovery trigger test**

Append to `tests/test_runtime_state_flow.py`:

```python
class EmptyCTSClient:
    async def search(self, query, *, round_no, trace_id):
        del query, round_no, trace_id
        return CTSFetchResult(request_payload={}, candidates=[], raw_candidate_count=0, adapter_notes=[])


class WebDiscoveryServiceStub:
    def __init__(self) -> None:
        self.calls = 0

    async def bootstrap_explicit(self, *, requirement_sheet, jd, notes):
        return TargetCompanyPlan(
            accepted_companies=[],
            holdout_companies=[],
            rejected_companies=[],
            explicit_company_count=0,
            web_discovery_attempted=False,
            stop_reason="completed",
        )

    async def discover_web(self, *, requirement_sheet, round_no, trigger_reason):
        self.calls += 1
        evidence = CompanyEvidence(source="web_search", title="web", url="https://example.com", snippet="火山引擎")
        plan = TargetCompanyPlan(
            accepted_companies=[
                TargetCompanyCandidate(
                    name="火山引擎",
                    aliases=[],
                    source="web_inferred",
                    intent="target",
                    confidence=0.8,
                    evidence=[evidence],
                    search_usage="keyword",
                )
            ],
            holdout_companies=[],
            rejected_companies=[],
            explicit_company_count=0,
            web_discovery_attempted=True,
            stop_reason="completed",
        )
        return CompanyDiscoveryResult(
            plan=plan,
            discovery_input=None,
            search_result_count=12,
            opened_page_count=4,
            trigger_reason=trigger_reason,
        )


def test_runtime_triggers_web_company_discovery_after_low_recall(tmp_path: Path) -> None:
    settings = make_settings(
        runs_dir=str(tmp_path / "runs"),
        mock_cts=True,
        min_rounds=1,
        max_rounds=2,
        target_company_enabled=True,
        company_discovery_enabled=True,
        bocha_api_key="key",
    )
    runtime = WorkflowRuntime(settings)
    runtime_any = cast(Any, runtime)
    runtime_any.requirement_extractor = SingleFamilyRequirementExtractor(include_reserve=False)
    runtime_any.controller = SearchThenStopController()
    runtime_any.reflection_critic = SequenceReflection()
    runtime_any.resume_scorer = LowQualityScorer()
    runtime_any.finalizer = StubFinalizer()
    runtime_any.cts_client = EmptyCTSClient()
    discovery_stub = WebDiscoveryServiceStub()
    runtime_any.company_discovery = discovery_stub
    tracer = RunTracer(tmp_path / "trace-runs")
    progress_events = []

    try:
        run_state = asyncio.run(
            runtime._build_run_state(
                job_title="Senior Python Engineer",
                jd="Python retrieval",
                notes="",
                tracer=tracer,
                progress_callback=progress_events.append,
            )
        )
        asyncio.run(runtime._run_rounds(run_state=run_state, tracer=tracer, progress_callback=progress_events.append))
    finally:
        tracer.close()

    assert discovery_stub.calls == 1
    assert run_state.retrieval_state.company_discovery_attempted is True
    assert any(item.term == "火山引擎" for item in run_state.retrieval_state.query_term_pool)
    assert any(event.type == "company_discovery_completed" for event in progress_events)
```

Add imports:

```python
from seektalent.company_discovery.models import (
    CompanyDiscoveryResult,
    CompanyEvidence,
    TargetCompanyCandidate,
    TargetCompanyPlan,
)
from seektalent.clients.cts_client import CTSFetchResult
```

- [ ] **Step 2: Run failing test**

Run:

```bash
uv run pytest tests/test_runtime_state_flow.py::test_runtime_triggers_web_company_discovery_after_low_recall -v
```

Expected: fail because runtime does not trigger web discovery.

- [ ] **Step 3: Preflight company discovery model only when enabled**

In `src/seektalent/llm.py`, update `preflight_models`:

```python
    if settings.company_discovery_enabled:
        model_specs.append((settings.company_discovery_model, None, None))
```

This keeps disabled web discovery from requiring the Qwen model path.

- [ ] **Step 4: Add discovery gate helpers**

In `WorkflowRuntime`, add:

```python
    async def _maybe_run_company_discovery_before_controller(
        self,
        *,
        run_state: RunState,
        controller_context: ControllerContext,
        round_no: int,
        tracer: RunTracer,
        progress_callback: ProgressCallback | None,
    ) -> bool:
        if not self._should_trigger_company_discovery(run_state, controller_context, round_no=round_no):
            return False
        await self._run_company_web_discovery(
            run_state=run_state,
            round_no=round_no,
            trigger_reason=controller_context.stop_guidance.reason,
            tracer=tracer,
            progress_callback=progress_callback,
        )
        return True

    def _should_trigger_company_discovery(
        self,
        run_state: RunState,
        controller_context: ControllerContext,
        *,
        round_no: int,
    ) -> bool:
        if not self.settings.company_discovery_enabled:
            return False
        if run_state.retrieval_state.company_discovery_attempted:
            return False
        if self._has_untried_target_company(run_state):
            return False
        latest = controller_context.latest_search_observation
        if latest is None or round_no < 2 or controller_context.rounds_remaining_after_current < 1:
            return False
        return (
            latest.unique_new_count <= 1
            or latest.shortage_count >= controller_context.target_new - 1
            or controller_context.stop_guidance.top_pool_strength in {"empty", "weak"}
            or controller_context.stop_guidance.zero_gain_round_count >= 1
        )

    def _has_untried_target_company(self, run_state: RunState) -> bool:
        return self._next_company_seed_terms(
            run_state,
            round_no=max(1, len(run_state.round_history) + 1),
        ) is not None
```

- [ ] **Step 5: Add web discovery runner and artifacts**

Add:

```python
    async def _run_company_web_discovery(
        self,
        *,
        run_state: RunState,
        round_no: int,
        trigger_reason: str,
        tracer: RunTracer,
        progress_callback: ProgressCallback | None,
    ) -> None:
        self._emit_progress(
            progress_callback,
            "company_discovery_started",
            f"Company discovery started: {trigger_reason}",
            round_no=round_no,
            payload={"stage": "company_discovery", "trigger_reason": trigger_reason},
        )
        result = await self.company_discovery.discover_web(
            requirement_sheet=run_state.requirement_sheet,
            round_no=round_no,
            trigger_reason=trigger_reason,
        )
        run_state.retrieval_state.company_discovery_attempted = True
        run_state.retrieval_state.target_company_plan = result.plan.model_dump(mode="json")
        run_state.retrieval_state.query_term_pool = inject_target_company_terms(
            run_state.retrieval_state.query_term_pool,
            result.plan,
            round_no=round_no,
            source="company_discovery",
        )
        round_dir = f"rounds/round_{round_no:02d}"
        if result.discovery_input is not None:
            tracer.write_json(
                f"{round_dir}/company_discovery_input.json",
                result.discovery_input.model_dump(mode="json"),
            )
        tracer.write_json(f"{round_dir}/company_discovery_plan.json", result.plan.model_dump(mode="json"))
        tracer.write_json(
            f"{round_dir}/company_search_queries.json",
            [item.model_dump(mode="json") for item in result.search_tasks],
        )
        tracer.write_json(
            f"{round_dir}/company_search_results.json",
            [item.model_dump(mode="json") for item in result.search_results],
        )
        if result.triage is not None:
            tracer.write_json(f"{round_dir}/company_search_triage.json", result.triage.model_dump(mode="json"))
        tracer.write_json(
            f"{round_dir}/company_page_reads.json",
            [item.model_dump(mode="json") for item in result.page_reads],
        )
        tracer.write_json(
            f"{round_dir}/company_evidence_cards.json",
            [item.model_dump(mode="json") for item in result.evidence_candidates],
        )
        event_type = (
            "company_discovery_timeout"
            if str(result.plan.stop_reason).startswith("timeout")
            else "company_discovery_completed"
        )
        self._emit_progress(
            progress_callback,
            event_type,
            self._company_discovery_message(result.plan),
            round_no=round_no,
            payload={
                "stage": "company_discovery",
                "trigger_reason": result.trigger_reason,
                "search_result_count": result.search_result_count,
                "opened_page_count": result.opened_page_count,
                "accepted_companies": [item.name for item in result.plan.accepted_companies],
                "holdout_companies": [item.name for item in result.plan.holdout_companies],
                "rejected_companies": [item.name for item in result.plan.rejected_companies],
                "stop_reason": result.plan.stop_reason,
                "page_titles": [item.title or item.url for item in result.page_reads if item.read_success][:6],
                "next_query_terms": self._next_company_seed_terms(run_state, round_no=round_no) or [],
            },
        )

    def _company_discovery_message(self, plan: TargetCompanyPlan) -> str:
        accepted = ", ".join(item.name for item in plan.accepted_companies) or "none"
        return f"Company discovery {plan.stop_reason}; accepted={accepted}."
```

This helper writes every company-discovery artifact listed in the design when the corresponding structured payload exists.

- [ ] **Step 6: Call the gate before controller writes context**

In `_run_rounds`, immediately after building `controller_context` and before writing `controller_context.json`, add:

```python
            if await self._maybe_run_company_discovery_before_controller(
                run_state=run_state,
                controller_context=controller_context,
                round_no=round_no,
                tracer=tracer,
                progress_callback=progress_callback,
            ):
                controller_context = build_controller_context(
                    run_state=run_state,
                    round_no=round_no,
                    min_rounds=self.settings.min_rounds,
                    max_rounds=self.settings.max_rounds,
                    target_new=target_new,
                )
```

This ensures the persisted controller context sees injected company terms.

- [ ] **Step 7: Add stop rescue**

After `controller_decision = self._sanitize_controller_decision(...)` and before forcing continue on `can_stop=false`, add:

```python
                if isinstance(controller_decision, StopControllerDecision) and self._should_rescue_stop_with_company_discovery(
                    run_state,
                    controller_context,
                    round_no=round_no,
                ):
                    await self._run_company_web_discovery(
                        run_state=run_state,
                        round_no=round_no,
                        trigger_reason=f"stop rescue: {controller_context.stop_guidance.reason}",
                        tracer=tracer,
                        progress_callback=progress_callback,
                    )
                    company_seed = self._force_company_seed_decision(
                        run_state=run_state,
                        round_no=round_no,
                        reason="web discovery found target companies before stop.",
                    )
                    if company_seed is not None:
                        controller_decision = company_seed
```

Add helper:

```python
    def _should_rescue_stop_with_company_discovery(
        self,
        run_state: RunState,
        controller_context: ControllerContext,
        *,
        round_no: int,
    ) -> bool:
        if not isinstance(controller_context.stop_guidance.top_pool_strength, str):
            return False
        return (
            self.settings.company_discovery_enabled
            and not run_state.retrieval_state.company_discovery_attempted
            and round_no >= 2
            and controller_context.stop_guidance.top_pool_strength in {"empty", "weak"}
        )
```

- [ ] **Step 8: Run focused web discovery runtime test**

Run:

```bash
uv run pytest tests/test_runtime_state_flow.py::test_runtime_triggers_web_company_discovery_after_low_recall -v
```

Expected: pass.

- [ ] **Step 9: Run runtime and config tests**

Run:

```bash
uv run pytest tests/test_runtime_state_flow.py tests/test_company_discovery_config.py -v
```

Expected: pass.

- [ ] **Step 10: Commit**

Run:

```bash
git add src/seektalent/runtime/orchestrator.py src/seektalent/llm.py tests/test_runtime_state_flow.py
git commit -m "Trigger web company discovery from runtime"
```

## Task 8: Controller Prompt And TUI Company Trace Rendering

**Files:**
- Modify: `src/seektalent/controller/react_controller.py`
- Modify: `src/seektalent/prompts/controller.md`
- Modify: `src/seektalent/runtime/orchestrator.py`
- Modify: `src/seektalent/tui.py`
- Modify: `tests/test_tui.py`
- Modify: `tests/test_llm_input_prompts.py` if controller prompt snapshots are asserted there.

- [ ] **Step 1: Add failing TUI rendering tests**

Append to `tests/test_tui.py`:

```python
def test_tui_renders_explicit_company_bootstrap_block() -> None:
    from seektalent.tui import _render_progress_lines

    event = ProgressEvent(
        type="company_explicit_bootstrap_completed",
        message="Target company bootstrap completed.",
        payload={
            "accepted_companies": ["阿里云", "火山引擎"],
            "rejected_companies": ["客户公司A"],
            "next_query_terms": ["大模型", "阿里云"],
        },
    )

    rendered = "\n".join(_render_progress_lines(event))

    assert "目标公司线索 · 来自 JD/Notes" in rendered
    assert "识别到 2 家目标/偏好公司：阿里云、火山引擎。" in rendered
    assert "已排除 1 家：客户公司A。" in rendered
    assert "第 1 轮会先验证目标公司来源：大模型、阿里云。" in rendered


def test_tui_renders_web_discovery_trace_block() -> None:
    from seektalent.tui import _render_progress_lines

    event = ProgressEvent(
        type="company_discovery_completed",
        message="Company discovery completed.",
        round_no=3,
        payload={
            "trigger_reason": "top pool is weak",
            "search_result_count": 47,
            "opened_page_count": 6,
            "page_titles": ["火山引擎大模型服务平台", "阿里云百炼平台介绍"],
            "accepted_companies": ["火山引擎", "阿里云"],
            "holdout_companies": ["商汤科技"],
            "rejected_companies": ["某媒体"],
            "next_query_terms": ["大模型", "火山引擎"],
            "stop_reason": "completed",
        },
    )

    rendered = "\n".join(_render_progress_lines(event))

    assert "公司发现 · 低召回触发" in rendered
    assert "Found 47 web pages" in rendered
    assert "Read 6 pages" in rendered
    assert "- 火山引擎大模型服务平台 ↗" in rendered
    assert "接受 2 家：火山引擎、阿里云。" in rendered
    assert "保留观察 1 家：商汤科技。" in rendered
    assert "拒绝 1 家：某媒体。" in rendered
    assert "第 3 轮会验证目标公司来源：大模型、火山引擎。" in rendered


def test_tui_renders_company_discovery_timeout_without_accepted_companies() -> None:
    from seektalent.tui import _render_progress_lines

    event = ProgressEvent(
        type="company_discovery_timeout",
        message="timeout",
        payload={
            "search_result_count": 38,
            "opened_page_count": 4,
            "accepted_companies": [],
            "next_query_terms": [],
            "stop_reason": "timeout_no_accepted_companies",
        },
    )

    rendered = "\n".join(_render_progress_lines(event))

    assert "公司发现 · 达到 25 秒预算" in rendered
    assert "已搜索到 38 个网页，阅读 4 页。" in rendered
    assert "没有足够证据接受目标公司，回到常规技能检索。" in rendered


def test_round_completed_labels_target_company_lane() -> None:
    from seektalent.tui import _render_progress_lines

    event = ProgressEvent(
        type="round_completed",
        message="round completed",
        round_no=1,
        payload={
            "query_terms": ["大模型", "火山引擎"],
            "query_term_details": [
                {"term": "大模型", "retrieval_role": "role_anchor"},
                {"term": "火山引擎", "retrieval_role": "target_company"},
            ],
            "raw_candidate_count": 10,
            "unique_new_count": 6,
            "newly_scored_count": 6,
            "fit_count": 3,
            "not_fit_count": 3,
        },
    )

    rendered = "\n".join(_render_progress_lines(event))

    assert rendered.startswith("[bold]第 1 轮 · 目标公司检索")
```

- [ ] **Step 2: Run failing TUI tests**

Run:

```bash
uv run pytest tests/test_tui.py::test_tui_renders_explicit_company_bootstrap_block tests/test_tui.py::test_tui_renders_web_discovery_trace_block tests/test_tui.py::test_tui_renders_company_discovery_timeout_without_accepted_companies tests/test_tui.py::test_round_completed_labels_target_company_lane -v
```

Expected: fail because TUI does not render company events and round label.

- [ ] **Step 3: Add query term details to round progress payload**

In `WorkflowRuntime._build_round_progress_payload`, add:

```python
            "query_term_details": self._query_term_details(
                run_state=run_state,
                query_terms=retrieval_plan.query_terms,
            ),
```

Add helper:

```python
    def _query_term_details(self, *, run_state: RunState, query_terms: list[str]) -> list[dict[str, object]]:
        index = {self._query_term_key(item.term): item for item in run_state.retrieval_state.query_term_pool}
        details: list[dict[str, object]] = []
        for term in query_terms:
            candidate = index.get(self._query_term_key(term))
            if candidate is None:
                details.append({"term": term})
                continue
            details.append(
                {
                    "term": candidate.term,
                    "source": candidate.source,
                    "category": candidate.category,
                    "retrieval_role": candidate.retrieval_role,
                    "family": candidate.family,
                }
            )
        return details
```

In `_run_company_web_discovery`, include page titles in the progress payload:

```python
                "page_titles": [item.title or item.url for item in result.page_reads if item.read_success][:6],
```

- [ ] **Step 4: Add controller prompt rule**

In `src/seektalent/prompts/controller.md`, add under hard rules:

```markdown
- When explicit target-company terms are visible and runtime has not already executed a target-company search, prefer one early target-company-backed query unless the target-company family already produced zero gain.
```

In `src/seektalent/controller/react_controller.py`, keep `TERM BANK` as-is because it already prints `retrieval_role`; target-company terms will be visible.

- [ ] **Step 5: Implement TUI company renderers**

In `src/seektalent/tui.py`, update `_render_progress_lines` before generic dim event handling:

```python
    if event.type == "company_explicit_bootstrap_completed":
        return _render_company_explicit_bootstrap(payload)
    if event.type == "company_discovery_completed":
        return _render_company_discovery_completed(event, payload)
    if event.type == "company_discovery_timeout":
        return _render_company_discovery_timeout(payload)
```

Add helpers:

```python
def _render_company_explicit_bootstrap(payload: dict[str, Any]) -> list[str]:
    accepted = _list_text(payload.get("accepted_companies"))
    rejected = _list_text(payload.get("rejected_companies"))
    next_terms = _list_text(payload.get("next_query_terms"))
    lines = ["[bold]目标公司线索 · 来自 JD/Notes[/]"]
    if accepted:
        lines.append(f"识别到 {len(accepted)} 家目标/偏好公司：{escape(_join_list(accepted))}。")
    if rejected:
        lines.append(f"已排除 {len(rejected)} 家：{escape(_join_list(rejected))}。")
    if next_terms:
        lines.extend(["", "下一步搜索", f"第 1 轮会先验证目标公司来源：{escape(_join_list(next_terms))}。"])
    return lines


def _render_company_discovery_completed(event: ProgressEvent, payload: dict[str, Any]) -> list[str]:
    accepted = _list_text(payload.get("accepted_companies"))
    holdout = _list_text(payload.get("holdout_companies"))
    rejected = _list_text(payload.get("rejected_companies"))
    next_terms = _list_text(payload.get("next_query_terms"))
    page_titles = _list_text(payload.get("page_titles"))[:6]
    round_no = event.round_no or 0
    lines = ["[bold]公司发现 · 低召回触发[/]"]
    trigger = str(payload.get("trigger_reason") or "").strip()
    if trigger:
        lines.append(f"{escape(trigger)}。开始搜索相似人才来源公司。")
    lines.extend(["", f"Found {int(payload.get('search_result_count') or 0)} web pages"])
    lines.append("筛选相关页面，优先阅读行业列表、招聘页、官方产品页和技术博客。")
    lines.extend(["", f"Read {int(payload.get('opened_page_count') or 0)} pages"])
    lines.extend(f"- {escape(title)} ↗" for title in page_titles)
    lines.extend(["", "发现目标公司"])
    if accepted:
        lines.append(f"接受 {len(accepted)} 家：{escape(_join_list(accepted))}。")
    if holdout:
        lines.append(f"保留观察 {len(holdout)} 家：{escape(_join_list(holdout))}。")
    if rejected:
        lines.append(f"拒绝 {len(rejected)} 家：{escape(_join_list(rejected))}。")
    if next_terms:
        lines.extend(["", "下一步搜索", f"第 {round_no} 轮会验证目标公司来源：{escape(_join_list(next_terms))}。"])
    return lines


def _render_company_discovery_timeout(payload: dict[str, Any]) -> list[str]:
    accepted = _list_text(payload.get("accepted_companies"))
    lines = ["[bold]公司发现 · 达到 25 秒预算[/]"]
    lines.append(
        "已搜索到 "
        f"{int(payload.get('search_result_count') or 0)} 个网页，"
        f"阅读 {int(payload.get('opened_page_count') or 0)} 页。"
    )
    if accepted:
        lines.append(f"证据足够，先使用 partial plan：{escape(_join_list(accepted))}。")
    else:
        lines.append("没有足够证据接受目标公司，回到常规技能检索。")
    return lines
```

Update `_render_round_completed` first line:

```python
    title = "目标公司检索" if _has_target_company_query(payload) else "摘要"
    lines = [f"[bold]第 {round_no} 轮 · {title}[/]"]
```

Add:

```python
def _has_target_company_query(payload: dict[str, Any]) -> bool:
    details = payload.get("query_term_details")
    if not isinstance(details, list):
        return False
    return any(
        isinstance(item, Mapping) and item.get("retrieval_role") == "target_company"
        for item in details
    )
```

Keep existing tests expecting `"[bold]第 2 轮"` valid because the string still starts with that prefix.

- [ ] **Step 6: Run TUI tests**

Run:

```bash
uv run pytest tests/test_tui.py -v
```

Expected: pass.

- [ ] **Step 7: Run controller prompt input tests**

Run:

```bash
uv run pytest tests/test_llm_input_prompts.py tests/test_controller_contract.py -v
```

Expected: pass. If a snapshot-style assertion checks prompt text, update only the expected string to include the new target-company rule.

- [ ] **Step 8: Commit**

Run:

```bash
git add src/seektalent/tui.py src/seektalent/runtime/orchestrator.py src/seektalent/prompts/controller.md src/seektalent/controller/react_controller.py tests/test_tui.py tests/test_llm_input_prompts.py tests/test_controller_contract.py
git commit -m "Render company discovery trace in TUI"
```

## Task 9: Documentation, Outputs, And Final Validation

**Files:**
- Modify: `docs/configuration.md`
- Modify: `docs/outputs.md`
- Modify: `docs/superpowers/plans/2026-04-22-target-company-discovery-implementation.md` if implementation discoveries required plan correction.

- [ ] **Step 1: Update configuration docs**

Add to `docs/configuration.md` after the Agent variables section:

```markdown
## Target company discovery variables

| Variable | Default | Notes |
| --- | --- | --- |
| `SEEKTALENT_TARGET_COMPANY_ENABLED` | `true` | Enables explicit target-company bootstrap from JD/notes. Does not call web search. |
| `SEEKTALENT_COMPANY_DISCOVERY_ENABLED` | `false` | Enables bounded Bocha web discovery after low recall or weak quality. |
| `SEEKTALENT_COMPANY_DISCOVERY_PROVIDER` | `bocha` | Only `bocha` is supported. |
| `SEEKTALENT_BOCHA_API_KEY` | empty | Required when web discovery runs. |
| `SEEKTALENT_COMPANY_DISCOVERY_MODEL` | `openai-chat:qwen3.5-flash` | OpenAI-compatible Bailian/Qwen model used for planner, triage, extraction, and reducer. |
| `SEEKTALENT_COMPANY_DISCOVERY_REASONING_EFFORT` | `off` | Reasoning setting for lightweight company discovery calls. |
| `SEEKTALENT_COMPANY_DISCOVERY_MAX_SEARCH_CALLS` | `4` | Maximum Bocha search calls per discovery run. |
| `SEEKTALENT_COMPANY_DISCOVERY_MAX_RESULTS_PER_QUERY` | `30` | Maximum Bocha results requested per search query. |
| `SEEKTALENT_COMPANY_DISCOVERY_MAX_OPEN_PAGES` | `8` | Maximum pages read after triage. |
| `SEEKTALENT_COMPANY_DISCOVERY_MAX_LLM_CALLS` | `8` | Guardrail for company discovery model calls. |
| `SEEKTALENT_COMPANY_DISCOVERY_TIMEOUT_SECONDS` | `25` | Wall-clock discovery budget. Timeout reduces partial evidence rather than failing the whole run. |
| `SEEKTALENT_COMPANY_DISCOVERY_ACCEPTED_COMPANY_LIMIT` | `8` | Maximum accepted target companies injected for scheduling. |
| `SEEKTALENT_COMPANY_DISCOVERY_MIN_CONFIDENCE` | `0.65` | Minimum confidence expected for accepted web-discovered companies. |
```

- [ ] **Step 2: Update output docs**

Add to `docs/outputs.md` top-level files:

```markdown
| `company_discovery/bootstrap_plan.json` | Explicit target-company plan derived from JD/notes when target-company bootstrap is enabled. |
```

Add to per-round files:

```markdown
| `company_discovery_input.json` | Redacted role digest used for web target-company discovery. |
| `company_search_queries.json` | Planned web search tasks for company discovery. |
| `company_search_results.json` | Normalized Bocha web search results. |
| `company_search_triage.json` | URLs selected for page reading and the triage rationale. |
| `company_page_reads.json` | Bounded page-read results with success flags and cleaned text. |
| `company_evidence_cards.json` | Structured company evidence extracted from search results and page reads. |
| `company_discovery_plan.json` | Accepted, holdout, rejected, duplicate, and timeout state for company discovery. |
```

Task 7 writes these per-round files when the corresponding structured payload exists.

- [ ] **Step 3: Run focused test suite**

Run:

```bash
uv run pytest tests/test_company_discovery_config.py tests/test_company_discovery.py tests/test_query_plan.py tests/test_runtime_state_flow.py tests/test_tui.py -v
```

Expected: pass.

- [ ] **Step 4: Run related regression tests**

Run:

```bash
uv run pytest tests/test_filter_projection.py tests/test_requirement_extraction.py tests/test_controller_contract.py tests/test_llm_input_prompts.py tests/test_runtime_audit.py -v
```

Expected: pass.

- [ ] **Step 5: Run architecture and lint checks**

Run:

```bash
uv run tach check
uv run ruff check src tests
```

Expected: both pass. If `ruff` reports import ordering or unused imports from snippets above, fix only those local issues.

- [ ] **Step 6: Run full test suite**

Run:

```bash
uv run pytest
```

Expected: pass. If unrelated pre-existing tests fail, record the failure, confirm it is unrelated, and do not hide it.

- [ ] **Step 7: Commit docs and final fixes**

Run:

```bash
git add docs/configuration.md docs/outputs.md src tests tach.toml
git commit -m "Document target company discovery workflow"
```

## Implementation Notes

- Keep feature flags only in `WorkflowRuntime` orchestration and config presentation.
- Do not read target-company flags inside `company_discovery` package functions.
- Do not apply target companies as CTS `company` filters unless a future task adds explicit mandatory-company intent.
- Do not add Bocha fallback providers.
- Do not retry Bocha network failures.
- Keep page read failures non-fatal.
- Treat whole discovery timeout as a bounded stop condition and reduce partial evidence.
- Keep TUI output business-readable; raw URLs and full page text belong in artifacts.

## Self-Review Checklist

- Spec coverage:
  - Explicit bootstrap: Tasks 2, 3, 6.
  - Web discovery: Tasks 4, 5, 7.
  - Query scheduling: Task 2 and Task 6.
  - Runtime high-level flags only: Tasks 1, 6, 7.
  - TUI trace: Task 8.
  - Docs/artifacts: Task 9.
- Red-flag scan:
  - This plan contains no unfinished markers, no unspecified test command, and no intentionally blank implementation step.
- Type consistency:
  - `TargetCompanyPlan`, `CompanyDiscoveryResult`, `WebSearchResult`, `PageReadResult`, `QueryTermCandidate`, and `RetrievalState` names match the planned code snippets.
