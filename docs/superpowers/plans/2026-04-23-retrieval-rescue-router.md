# Retrieval Rescue Router Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single runtime rescue router that orders recall repair as reserve broaden, candidate feedback, web company discovery, anchor-only search, then stop.

**Architecture:** Keep feature flags at runtime orchestration boundaries. Add a small `seektalent.candidate_feedback` package for one-shot relevance feedback, integrate the existing target-company branch as the third web-discovery rescue lane, and keep anchor-only as the final fallback. Write artifacts for every rescue decision so each lane can be audited and evaluated.

**Tech Stack:** Python, Pydantic, Pydantic AI, httpx, pytest, existing SeekTalent runtime/controller/retrieval/TUI modules.

---

## File Structure

- Create `src/seektalent/candidate_feedback/__init__.py`  
  Exports the small public API used by runtime.
- Create `src/seektalent/candidate_feedback/models.py`  
  Pydantic models for feedback seed snippets, extracted candidate terms, model ranking, and accepted feedback decisions.
- Create `src/seektalent/candidate_feedback/extraction.py`  
  Deterministic surface-form extraction, seed selection, runtime filtering, scoring, and query-term materialization.
- Create `src/seektalent/candidate_feedback/model_steps.py`  
  Bounded LLM ranking from deterministic candidate terms only.
- Create `src/seektalent/runtime/rescue_router.py`  
  Pure routing decision function. It inspects already-computed runtime state and returns a selected lane plus skipped-lane reasons.
- Modify `src/seektalent/config.py`  
  Adds candidate feedback and company discovery settings with approved defaults.
- Modify `src/seektalent/default.env` and `.env.example`  
  Adds feature flags and Bocha/company discovery settings.
- Modify `src/seektalent/models.py`  
  Adds query term sources/categories/roles and minimal retrieval state needed by the router.
- Modify `src/seektalent/llm.py`  
  Includes candidate feedback and company discovery models in preflight when enabled.
- Modify `src/seektalent/runtime/orchestrator.py`  
  Wires rescue router, candidate feedback, web company discovery, artifacts, forced decisions, and progress events.
- Modify `src/seektalent/tui.py`  
  Renders concise rescue lane progress events.
- Modify `tach.toml`  
  Adds module boundaries for `seektalent.candidate_feedback` and `seektalent.company_discovery`.
- Add/modify tests:
  - `tests/test_rescue_router_config.py`
  - `tests/test_candidate_feedback.py`
  - `tests/test_rescue_router.py`
  - `tests/test_runtime_state_flow.py`
  - `tests/test_company_discovery.py`
  - `tests/test_runtime_audit.py`
  - `tests/test_tui.py`
  - `tests/test_llm_provider_config.py`

---

## Task 1: Add Settings, Query Term Types, and Retrieval State

**Files:**
- Modify: `src/seektalent/config.py`
- Modify: `src/seektalent/default.env`
- Modify: `.env.example`
- Modify: `src/seektalent/models.py`
- Test: `tests/test_rescue_router_config.py`

- [ ] **Step 1: Write failing config and model tests**

Create `tests/test_rescue_router_config.py`:

```python
from seektalent.models import QueryTermCandidate, RetrievalState
from tests.settings_factory import make_settings


def test_rescue_feature_defaults() -> None:
    settings = make_settings()

    assert settings.candidate_feedback_enabled is True
    assert settings.candidate_feedback_model == "openai-chat:qwen3.5-flash"
    assert settings.candidate_feedback_reasoning_effort == "off"
    assert settings.target_company_enabled is False
    assert settings.company_discovery_enabled is True
    assert settings.company_discovery_provider == "bocha"
    assert settings.company_discovery_model == "openai-chat:qwen3.5-flash"


def test_candidate_feedback_query_term_source_is_valid() -> None:
    term = QueryTermCandidate(
        term="LangGraph",
        source="candidate_feedback",
        category="expansion",
        priority=30,
        evidence="Supported by two fit seed resumes.",
        first_added_round=4,
        retrieval_role="core_skill",
        queryability="admitted",
        family="feedback.langgraph",
    )

    assert term.source == "candidate_feedback"
    assert term.family == "feedback.langgraph"


def test_retrieval_state_tracks_rescue_attempts() -> None:
    state = RetrievalState(
        candidate_feedback_attempted=True,
        company_discovery_attempted=True,
        anchor_only_broaden_attempted=True,
        rescue_lane_history=[
            {
                "round_no": 4,
                "selected_lane": "candidate_feedback",
                "forced_query_terms": ["AI Agent", "LangGraph"],
            }
        ],
    )

    assert state.candidate_feedback_attempted is True
    assert state.company_discovery_attempted is True
    assert state.anchor_only_broaden_attempted is True
    assert state.rescue_lane_history[0]["selected_lane"] == "candidate_feedback"
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
uv run pytest tests/test_rescue_router_config.py -v
```

Expected: fail because `candidate_feedback_enabled`, `candidate_feedback_model`, `candidate_feedback_reasoning_effort`, new query term source, and rescue state fields do not exist.

- [ ] **Step 3: Update `src/seektalent/config.py`**

Add `candidate_feedback_model` and `company_discovery_model` to `MODEL_FIELDS`:

```python
MODEL_FIELDS = (
    "requirements_model",
    "controller_model",
    "scoring_model",
    "finalize_model",
    "reflection_model",
    "judge_model",
    "tui_summary_model",
    "candidate_feedback_model",
    "company_discovery_model",
)
```

Add these fields to `AppSettings` after `enable_reflection`:

```python
    candidate_feedback_enabled: bool = True
    candidate_feedback_model: str = "openai-chat:qwen3.5-flash"
    candidate_feedback_reasoning_effort: ReasoningEffort = "off"
    target_company_enabled: bool = False
    company_discovery_enabled: bool = True
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

Add range validation in `validate_ranges` after the existing search validation:

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

- [ ] **Step 4: Update `.env.example` and `src/seektalent/default.env`**

Add these lines after `SEEKTALENT_ENABLE_REFLECTION=true` in both files:

```env
SEEKTALENT_CANDIDATE_FEEDBACK_ENABLED=true
SEEKTALENT_CANDIDATE_FEEDBACK_MODEL=openai-chat:qwen3.5-flash
SEEKTALENT_CANDIDATE_FEEDBACK_REASONING_EFFORT=off
SEEKTALENT_TARGET_COMPANY_ENABLED=false
SEEKTALENT_COMPANY_DISCOVERY_ENABLED=true
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

- [ ] **Step 5: Update `src/seektalent/models.py`**

Change the query term literal definitions near the top:

```python
QueryTermSource = Literal[
    "job_title",
    "jd",
    "notes",
    "reflection",
    "candidate_feedback",
    "target_company",
    "company_discovery",
]
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

Add fields to `RetrievalState`:

```python
    candidate_feedback_attempted: bool = False
    company_discovery_attempted: bool = False
    anchor_only_broaden_attempted: bool = False
    rescue_lane_history: list[dict[str, object]] = Field(default_factory=list)
    target_company_plan: dict[str, Any] | None = None
```

- [ ] **Step 6: Run tests**

Run:

```bash
uv run pytest tests/test_rescue_router_config.py -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/seektalent/config.py src/seektalent/default.env .env.example src/seektalent/models.py tests/test_rescue_router_config.py
git commit -m "Add rescue router settings and state"
```

---

## Task 2: Build Candidate Feedback Deterministic Extraction

**Files:**
- Create: `src/seektalent/candidate_feedback/__init__.py`
- Create: `src/seektalent/candidate_feedback/models.py`
- Create: `src/seektalent/candidate_feedback/extraction.py`
- Test: `tests/test_candidate_feedback.py`

- [ ] **Step 1: Write failing extraction tests**

Create `tests/test_candidate_feedback.py`:

```python
from seektalent.candidate_feedback.extraction import (
    build_feedback_decision,
    extract_surface_terms,
    select_feedback_seed_resumes,
)
from seektalent.models import QueryTermCandidate, ScoredCandidate


def _score(
    resume_id: str,
    *,
    fit_bucket: str = "fit",
    overall: int = 86,
    must: int = 82,
    risk: int = 20,
    evidence: list[str] | None = None,
    matched: list[str] | None = None,
    strengths: list[str] | None = None,
    reasoning: str = "Built LangGraph workflow orchestration with RAG.",
) -> ScoredCandidate:
    return ScoredCandidate(
        resume_id=resume_id,
        fit_bucket=fit_bucket,
        overall_score=overall,
        must_have_match_score=must,
        preferred_match_score=60,
        risk_score=risk,
        risk_flags=[],
        reasoning_summary=reasoning,
        evidence=evidence or ["Used LangGraph for tool calling and RAG workflows."],
        confidence="high",
        matched_must_haves=matched or ["Agent workflow orchestration with LangGraph."],
        missing_must_haves=[],
        matched_preferences=[],
        negative_signals=[],
        strengths=strengths or ["RAG", "LangGraph", "tool calling"],
        weaknesses=[],
        source_round=1,
    )


def _anchor() -> QueryTermCandidate:
    return QueryTermCandidate(
        term="AI Agent",
        source="job_title",
        category="role_anchor",
        priority=1,
        evidence="title",
        first_added_round=0,
        retrieval_role="role_anchor",
        queryability="admitted",
        family="role.ai-agent",
    )


def test_select_feedback_seed_resumes_uses_strict_fit_thresholds() -> None:
    seeds = select_feedback_seed_resumes(
        [
            _score("good-1", overall=90, must=85, risk=10),
            _score("weak-score", overall=74, must=85, risk=10),
            _score("weak-must", overall=90, must=69, risk=10),
            _score("risky", overall=90, must=85, risk=46),
            _score("not-fit", fit_bucket="not_fit", overall=95, must=95, risk=10),
            _score("good-2", overall=88, must=83, risk=12),
        ]
    )

    assert [item.resume_id for item in seeds] == ["good-1", "good-2"]


def test_extract_surface_terms_preserves_shapes_without_technical_dictionary() -> None:
    terms = extract_surface_terms(
        [
            "Used LangGraph, RAG, tool calling, C++, Node.js, and Flink CDC.",
            "Built 实时数仓 and 任务编排 with ClickHouse.",
            "负责 平台 系统 开发 管理",
        ]
    )

    assert "LangGraph" in terms
    assert "RAG" in terms
    assert "tool calling" in terms
    assert "C++" in terms
    assert "Node.js" in terms
    assert "Flink CDC" in terms
    assert "实时数仓" in terms
    assert "任务编排" in terms
    assert "平台" not in terms
    assert "系统" not in terms
    assert "开发" not in terms


def test_build_feedback_decision_picks_one_supported_novel_term() -> None:
    decision = build_feedback_decision(
        seed_resumes=[
            _score("r1"),
            _score("r2", evidence=["LangGraph workflow orchestration and tool calling."]),
        ],
        negative_resumes=[
            _score(
                "n1",
                fit_bucket="not_fit",
                overall=35,
                must=20,
                risk=80,
                evidence=["Generic Python backend platform work."],
                matched=[],
                strengths=["Python"],
                reasoning="Generic backend platform.",
            )
        ],
        existing_terms=[_anchor()],
        sent_query_terms=["AI Agent", "RAG"],
        round_no=4,
    )

    assert decision.accepted_term is not None
    assert decision.accepted_term.term == "LangGraph"
    assert decision.accepted_term.source == "candidate_feedback"
    assert decision.accepted_term.family == "feedback.langgraph"
    assert decision.forced_query_terms == ["AI Agent", "LangGraph"]
    assert all(item.term != "RAG" for item in decision.accepted_candidates)
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
uv run pytest tests/test_candidate_feedback.py -v
```

Expected: fail because `seektalent.candidate_feedback` does not exist.

- [ ] **Step 3: Create `src/seektalent/candidate_feedback/models.py`**

```python
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from seektalent.models import QueryTermCandidate


class FeedbackCandidateTerm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    term: str
    supporting_resume_ids: list[str] = Field(default_factory=list)
    linked_requirements: list[str] = Field(default_factory=list)
    field_hits: dict[str, int] = Field(default_factory=dict)
    fit_support_rate: float = 0.0
    not_fit_support_rate: float = 0.0
    score: float = 0.0
    risk_flags: list[str] = Field(default_factory=list)
    rejection_reason: str | None = None


class CandidateFeedbackDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed_resume_ids: list[str] = Field(default_factory=list)
    candidate_terms: list[FeedbackCandidateTerm] = Field(default_factory=list)
    rejected_terms: list[FeedbackCandidateTerm] = Field(default_factory=list)
    accepted_candidates: list[FeedbackCandidateTerm] = Field(default_factory=list)
    accepted_term: QueryTermCandidate | None = None
    forced_query_terms: list[str] = Field(default_factory=list)
    skipped_reason: str | None = None
```

- [ ] **Step 4: Create `src/seektalent/candidate_feedback/extraction.py`**

Implement these functions and constants:

```python
from __future__ import annotations

import re
from hashlib import sha1

from seektalent.candidate_feedback.models import CandidateFeedbackDecision, FeedbackCandidateTerm
from seektalent.models import QueryTermCandidate, ScoredCandidate

GENERIC_TERMS = {
    "平台", "系统", "项目", "开发", "负责", "熟悉", "业务", "管理", "优化", "架构", "能力", "经验",
    "platform", "system", "project", "development", "business", "management", "optimization", "architecture",
}
FILTER_LIKE_RE = re.compile(r"(北京|上海|深圳|本科|硕士|博士|985|211|C9|\\d+年|\\d+岁|薪资|年龄|学历)", re.I)
ACRONYM_RE = re.compile(r"\\b[A-Z]{2,}(?:\\s+[A-Z]{2,})?\\b")
SYMBOL_TOKEN_RE = re.compile(r"\\b[A-Za-z][A-Za-z0-9]*(?:[.+#-][A-Za-z0-9]+)+\\b|\\bC\\+\\+\\b|\\bC#\\b")
CAMEL_RE = re.compile(r"\\b[A-Z][a-z]+(?:[A-Z][a-z0-9]+)+\\b")
EN_PHRASE_RE = re.compile(r"\\b[A-Za-z][A-Za-z0-9.+#-]*(?:\\s+[A-Za-z][A-Za-z0-9.+#-]*){1,3}\\b")
CN_PHRASE_RE = re.compile(r"[\\u4e00-\\u9fff]{2,8}")


def select_feedback_seed_resumes(candidates: list[ScoredCandidate], *, limit: int = 5) -> list[ScoredCandidate]:
    seeds = [
        item
        for item in candidates
        if item.fit_bucket == "fit"
        and item.overall_score >= 75
        and item.must_have_match_score >= 70
        and item.risk_score <= 45
    ]
    return sorted(seeds, key=lambda item: (-item.overall_score, -item.must_have_match_score, item.risk_score, item.resume_id))[:limit]


def extract_surface_terms(texts: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for text in texts:
        for pattern in (ACRONYM_RE, SYMBOL_TOKEN_RE, CAMEL_RE, EN_PHRASE_RE, CN_PHRASE_RE):
            for match in pattern.finditer(text):
                term = _clean_term(match.group(0))
                if not _is_allowed_surface_term(term):
                    continue
                key = term.casefold()
                if key in seen:
                    continue
                seen.add(key)
                output.append(term)
    return output


def build_feedback_decision(
    *,
    seed_resumes: list[ScoredCandidate],
    negative_resumes: list[ScoredCandidate],
    existing_terms: list[QueryTermCandidate],
    sent_query_terms: list[str],
    round_no: int,
) -> CandidateFeedbackDecision:
    if len(seed_resumes) < 2:
        return CandidateFeedbackDecision(skipped_reason="fewer_than_two_feedback_seed_resumes")
    anchor = _active_anchor(existing_terms)
    if anchor is None:
        return CandidateFeedbackDecision(skipped_reason="missing_active_anchor")
    existing_keys = {_term_key(item.term) for item in existing_terms}
    sent_keys = {_term_key(item) for item in sent_query_terms}
    candidate_terms = _score_terms(seed_resumes, negative_resumes, existing_keys | sent_keys)
    accepted = [item for item in candidate_terms if item.rejection_reason is None and item.score >= 8]
    accepted.sort(key=lambda item: (-item.score, -len(item.supporting_resume_ids), item.term.casefold()))
    accepted_term = _materialize_term(accepted[0], round_no=round_no) if accepted else None
    return CandidateFeedbackDecision(
        seed_resume_ids=[item.resume_id for item in seed_resumes],
        candidate_terms=candidate_terms,
        rejected_terms=[item for item in candidate_terms if item.rejection_reason is not None],
        accepted_candidates=accepted,
        accepted_term=accepted_term,
        forced_query_terms=[anchor.term, accepted_term.term] if accepted_term is not None else [],
        skipped_reason=None if accepted_term is not None else "no_safe_feedback_term",
    )
```

In the same file, add helper functions `_score_terms`, `_resume_texts`, `_field_hit_counts`, `_support_ids`, `_fit_rate`, `_negative_rate`, `_materialize_term`, `_slug`, `_active_anchor`, `_clean_term`, `_is_allowed_surface_term`, and `_term_key`. Keep them module-private. Use `FeedbackCandidateTerm` for every candidate and set `rejection_reason` to one of:

```text
existing_or_tried
insufficient_seed_support
generic_or_filter_like
negative_support_too_high
```

- [ ] **Step 5: Create `src/seektalent/candidate_feedback/__init__.py`**

```python
from seektalent.candidate_feedback.extraction import (
    build_feedback_decision,
    extract_surface_terms,
    select_feedback_seed_resumes,
)
from seektalent.candidate_feedback.models import CandidateFeedbackDecision, FeedbackCandidateTerm

__all__ = [
    "CandidateFeedbackDecision",
    "FeedbackCandidateTerm",
    "build_feedback_decision",
    "extract_surface_terms",
    "select_feedback_seed_resumes",
]
```

- [ ] **Step 6: Run extraction tests**

Run:

```bash
uv run pytest tests/test_candidate_feedback.py -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/seektalent/candidate_feedback tests/test_candidate_feedback.py
git commit -m "Add candidate feedback extraction"
```

---

## Task 3: Add Constrained Candidate Feedback Model Step

**Files:**
- Create: `src/seektalent/candidate_feedback/model_steps.py`
- Modify: `src/seektalent/candidate_feedback/models.py`
- Modify: `tests/test_candidate_feedback.py`

- [ ] **Step 1: Add failing model-step tests**

Append to `tests/test_candidate_feedback.py`:

```python
from seektalent.candidate_feedback.models import CandidateFeedbackModelRanking, FeedbackCandidateTerm


def test_candidate_feedback_model_ranking_forbids_unknown_terms() -> None:
    ranking = CandidateFeedbackModelRanking(
        accepted_terms=["LangGraph", "InventedTerm"],
        rejected_terms={"平台": "generic"},
        rationale="LangGraph is supported by seed resumes.",
    )
    terms = [
        FeedbackCandidateTerm(term="LangGraph", supporting_resume_ids=["r1", "r2"]),
        FeedbackCandidateTerm(term="平台", supporting_resume_ids=["r1", "r2"]),
    ]

    assert ranking.accepted_from(terms) == ["LangGraph"]
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
uv run pytest tests/test_candidate_feedback.py::test_candidate_feedback_model_ranking_forbids_unknown_terms -v
```

Expected: fail because `CandidateFeedbackModelRanking` does not exist.

- [ ] **Step 3: Extend `src/seektalent/candidate_feedback/models.py`**

Add:

```python
class CandidateFeedbackModelRanking(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accepted_terms: list[str] = Field(default_factory=list)
    rejected_terms: dict[str, str] = Field(default_factory=dict)
    rationale: str

    def accepted_from(self, candidates: list[FeedbackCandidateTerm]) -> list[str]:
        allowed = {item.term.casefold(): item.term for item in candidates}
        output: list[str] = []
        for term in self.accepted_terms:
            original = allowed.get(term.casefold())
            if original is not None and original not in output:
                output.append(original)
        return output
```

- [ ] **Step 4: Create `src/seektalent/candidate_feedback/model_steps.py`**

```python
from __future__ import annotations

from typing import Any, cast

from pydantic_ai import Agent

from seektalent.candidate_feedback.models import CandidateFeedbackModelRanking, FeedbackCandidateTerm
from seektalent.config import AppSettings
from seektalent.llm import build_model, build_model_settings, build_output_spec


class CandidateFeedbackModelSteps:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    async def rank_terms(
        self,
        *,
        role_title: str,
        must_have_capabilities: list[str],
        existing_terms: list[str],
        candidates: list[FeedbackCandidateTerm],
    ) -> CandidateFeedbackModelRanking:
        result = await self._agent().run(
            _rank_prompt(
                role_title=role_title,
                must_have_capabilities=must_have_capabilities,
                existing_terms=existing_terms,
                candidates=candidates,
            )
        )
        ranking = cast(CandidateFeedbackModelRanking, result.output)
        accepted = ranking.accepted_from(candidates)
        return ranking.model_copy(update={"accepted_terms": accepted})

    def _agent(self) -> Agent[None, CandidateFeedbackModelRanking]:
        model = build_model(self.settings.candidate_feedback_model)
        return cast(
            Agent[None, CandidateFeedbackModelRanking],
            Agent(
                model=model,
                output_type=build_output_spec(self.settings.candidate_feedback_model, model, CandidateFeedbackModelRanking),
                system_prompt=(
                    "Rank candidate-derived retrieval expansion terms. "
                    "Only select terms from the provided candidate list. "
                    "Do not invent terms. Reject generic, company, school, location, degree, age, salary, and title-only terms."
                ),
                model_settings=build_model_settings(
                    self.settings,
                    self.settings.candidate_feedback_model,
                    reasoning_effort=self.settings.candidate_feedback_reasoning_effort,
                ),
                retries=0,
                output_retries=2,
            ),
        )
```

In the same file add `_rank_prompt(...)` that serializes:

```python
{
    "role_title": role_title,
    "must_have_capabilities": must_have_capabilities,
    "existing_terms": existing_terms,
    "candidate_terms": [item.model_dump(mode="json") for item in candidates],
}
```

and states that `accepted_terms` must be copied exactly from `candidate_terms[*].term`.

- [ ] **Step 5: Run candidate feedback tests**

Run:

```bash
uv run pytest tests/test_candidate_feedback.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/seektalent/candidate_feedback tests/test_candidate_feedback.py
git commit -m "Add constrained feedback term ranking"
```

---

## Task 4: Add Pure Rescue Router

**Files:**
- Create: `src/seektalent/runtime/rescue_router.py`
- Test: `tests/test_rescue_router.py`

- [ ] **Step 1: Write failing router tests**

Create `tests/test_rescue_router.py`:

```python
from seektalent.models import StopGuidance
from seektalent.runtime.rescue_router import RescueInputs, choose_rescue_lane


def _guidance(status: str = "broaden_required", *, top_pool_strength: str = "weak") -> StopGuidance:
    return StopGuidance(
        can_stop=False,
        reason="top pool weak",
        top_pool_strength=top_pool_strength,
        quality_gate_status=status,
    )


def test_rescue_router_prefers_reserve_broaden() -> None:
    decision = choose_rescue_lane(
        RescueInputs(
            stop_guidance=_guidance(),
            has_untried_reserve_family=True,
            has_feedback_seed_resumes=True,
            candidate_feedback_enabled=True,
            candidate_feedback_attempted=False,
            company_discovery_enabled=True,
            company_discovery_attempted=False,
            company_discovery_useful=True,
            anchor_only_broaden_attempted=False,
        )
    )

    assert decision.selected_lane == "reserve_broaden"
    assert decision.skipped_lanes == []


def test_rescue_router_uses_feedback_before_company_discovery() -> None:
    decision = choose_rescue_lane(
        RescueInputs(
            stop_guidance=_guidance(),
            has_untried_reserve_family=False,
            has_feedback_seed_resumes=True,
            candidate_feedback_enabled=True,
            candidate_feedback_attempted=False,
            company_discovery_enabled=True,
            company_discovery_attempted=False,
            company_discovery_useful=True,
            anchor_only_broaden_attempted=False,
        )
    )

    assert decision.selected_lane == "candidate_feedback"
    assert decision.skipped_lanes[0].lane == "reserve_broaden"


def test_rescue_router_uses_company_discovery_before_anchor_only() -> None:
    decision = choose_rescue_lane(
        RescueInputs(
            stop_guidance=_guidance(),
            has_untried_reserve_family=False,
            has_feedback_seed_resumes=False,
            candidate_feedback_enabled=True,
            candidate_feedback_attempted=False,
            company_discovery_enabled=True,
            company_discovery_attempted=False,
            company_discovery_useful=True,
            anchor_only_broaden_attempted=False,
        )
    )

    assert decision.selected_lane == "web_company_discovery"


def test_rescue_router_falls_back_to_anchor_only() -> None:
    decision = choose_rescue_lane(
        RescueInputs(
            stop_guidance=_guidance(),
            has_untried_reserve_family=False,
            has_feedback_seed_resumes=False,
            candidate_feedback_enabled=True,
            candidate_feedback_attempted=True,
            company_discovery_enabled=True,
            company_discovery_attempted=True,
            company_discovery_useful=True,
            anchor_only_broaden_attempted=False,
        )
    )

    assert decision.selected_lane == "anchor_only"


def test_rescue_router_allows_stop_outside_rescue_window() -> None:
    decision = choose_rescue_lane(
        RescueInputs(
            stop_guidance=_guidance(status="pass"),
            has_untried_reserve_family=True,
            has_feedback_seed_resumes=True,
            candidate_feedback_enabled=True,
            candidate_feedback_attempted=False,
            company_discovery_enabled=True,
            company_discovery_attempted=False,
            company_discovery_useful=True,
            anchor_only_broaden_attempted=False,
        )
    )

    assert decision.selected_lane == "allow_stop"
```

- [ ] **Step 2: Run failing router tests**

Run:

```bash
uv run pytest tests/test_rescue_router.py -v
```

Expected: fail because `seektalent.runtime.rescue_router` does not exist.

- [ ] **Step 3: Create `src/seektalent/runtime/rescue_router.py`**

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from seektalent.models import StopGuidance

RescueLane = Literal["reserve_broaden", "candidate_feedback", "web_company_discovery", "anchor_only", "allow_stop"]
RESCUE_STATUSES = {"broaden_required", "low_quality_exhausted"}


class SkippedRescueLane(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lane: str
    reason: str


class RescueInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stop_guidance: StopGuidance
    has_untried_reserve_family: bool
    has_feedback_seed_resumes: bool
    candidate_feedback_enabled: bool
    candidate_feedback_attempted: bool
    company_discovery_enabled: bool
    company_discovery_attempted: bool
    company_discovery_useful: bool
    anchor_only_broaden_attempted: bool


class RescueDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selected_lane: RescueLane
    skipped_lanes: list[SkippedRescueLane] = Field(default_factory=list)


def choose_rescue_lane(inputs: RescueInputs) -> RescueDecision:
    if inputs.stop_guidance.quality_gate_status not in RESCUE_STATUSES:
        return RescueDecision(selected_lane="allow_stop")

    skipped: list[SkippedRescueLane] = []
    if inputs.has_untried_reserve_family:
        return RescueDecision(selected_lane="reserve_broaden")
    skipped.append(SkippedRescueLane(lane="reserve_broaden", reason="no_untried_reserve_family"))

    if not inputs.candidate_feedback_enabled:
        skipped.append(SkippedRescueLane(lane="candidate_feedback", reason="disabled"))
    elif inputs.candidate_feedback_attempted:
        skipped.append(SkippedRescueLane(lane="candidate_feedback", reason="already_attempted"))
    elif not inputs.has_feedback_seed_resumes:
        skipped.append(SkippedRescueLane(lane="candidate_feedback", reason="no_feedback_seed_resumes"))
    else:
        return RescueDecision(selected_lane="candidate_feedback", skipped_lanes=skipped)

    if not inputs.company_discovery_enabled:
        skipped.append(SkippedRescueLane(lane="web_company_discovery", reason="disabled"))
    elif inputs.company_discovery_attempted:
        skipped.append(SkippedRescueLane(lane="web_company_discovery", reason="already_attempted"))
    elif not inputs.company_discovery_useful:
        skipped.append(SkippedRescueLane(lane="web_company_discovery", reason="not_useful"))
    else:
        return RescueDecision(selected_lane="web_company_discovery", skipped_lanes=skipped)

    if inputs.anchor_only_broaden_attempted:
        skipped.append(SkippedRescueLane(lane="anchor_only", reason="already_attempted"))
        return RescueDecision(selected_lane="allow_stop", skipped_lanes=skipped)

    return RescueDecision(selected_lane="anchor_only", skipped_lanes=skipped)
```

- [ ] **Step 4: Run router tests**

Run:

```bash
uv run pytest tests/test_rescue_router.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/seektalent/runtime/rescue_router.py tests/test_rescue_router.py
git commit -m "Add retrieval rescue router"
```

---

## Task 5: Wire Candidate Feedback and Router into Runtime

**Files:**
- Modify: `src/seektalent/runtime/orchestrator.py`
- Modify: `tests/test_runtime_state_flow.py`
- Test artifacts under temporary run dirs

- [ ] **Step 1: Add failing runtime tests**

Append to `tests/test_runtime_state_flow.py`:

```python
def test_runtime_uses_candidate_feedback_before_anchor_only(tmp_path: Path) -> None:
    settings = make_settings(
        runs_dir=str(tmp_path / "runs"),
        mock_cts=True,
        min_rounds=1,
        max_rounds=10,
        candidate_feedback_enabled=True,
        company_discovery_enabled=False,
    )
    runtime = WorkflowRuntime(settings)
    _install_broaden_stubs(runtime, include_reserve=False)
    tracer = RunTracer(tmp_path / "trace-runs")
    job_title, jd, notes = _sample_inputs()

    try:
        run_state = asyncio.run(runtime._build_run_state(job_title=job_title, jd=jd, notes=notes, tracer=tracer))
        run_state.scorecards_by_resume_id = {
            "fit-1": ScoredCandidate(
                resume_id="fit-1",
                fit_bucket="fit",
                overall_score=90,
                must_have_match_score=82,
                preferred_match_score=60,
                risk_score=15,
                risk_flags=[],
                reasoning_summary="Built LangGraph workflow orchestration.",
                evidence=["LangGraph workflow orchestration and tool calling."],
                confidence="high",
                matched_must_haves=["Agent workflow orchestration with LangGraph"],
                missing_must_haves=[],
                matched_preferences=[],
                negative_signals=[],
                strengths=["LangGraph", "tool calling"],
                weaknesses=[],
                source_round=1,
            ),
            "fit-2": ScoredCandidate(
                resume_id="fit-2",
                fit_bucket="fit",
                overall_score=88,
                must_have_match_score=80,
                preferred_match_score=55,
                risk_score=18,
                risk_flags=[],
                reasoning_summary="Used LangGraph for Agent workflow.",
                evidence=["LangGraph and RAG workflow implementation."],
                confidence="high",
                matched_must_haves=["Agent workflow orchestration with LangGraph"],
                missing_must_haves=[],
                matched_preferences=[],
                negative_signals=[],
                strengths=["LangGraph"],
                weaknesses=[],
                source_round=1,
            ),
        }
        run_state.top_pool_ids = ["fit-1", "fit-2"]
        _, stop_reason, rounds_executed, terminal_controller_round = asyncio.run(
            runtime._run_rounds(run_state=run_state, tracer=tracer)
        )
    finally:
        tracer.close()

    round_02_decision = json.loads(
        (tracer.run_dir / "rounds" / "round_02" / "controller_decision.json").read_text(encoding="utf-8")
    )
    rescue_decision = json.loads(
        (tracer.run_dir / "rounds" / "round_02" / "rescue_decision.json").read_text(encoding="utf-8")
    )
    feedback_terms = json.loads(
        (tracer.run_dir / "rounds" / "round_02" / "candidate_feedback_terms.json").read_text(encoding="utf-8")
    )

    assert rescue_decision["selected_lane"] == "candidate_feedback"
    assert round_02_decision["proposed_query_terms"] == ["python", "LangGraph"]
    assert feedback_terms["accepted_term"]["term"] == "LangGraph"
    assert run_state.retrieval_state.candidate_feedback_attempted is True
    assert stop_reason == "controller_stop"
    assert rounds_executed == 2
    assert terminal_controller_round is not None
```

- [ ] **Step 2: Run failing runtime test**

Run:

```bash
uv run pytest tests/test_runtime_state_flow.py::test_runtime_uses_candidate_feedback_before_anchor_only -v
```

Expected: fail because runtime still goes straight to anchor-only when no reserve term exists.

- [ ] **Step 3: Update imports in `src/seektalent/runtime/orchestrator.py`**

Add:

```python
from seektalent.candidate_feedback import build_feedback_decision, select_feedback_seed_resumes
from seektalent.runtime.rescue_router import RescueDecision, RescueInputs, choose_rescue_lane
```

- [ ] **Step 4: Add runtime helper methods**

Add methods near `_force_broaden_decision`:

```python
    def _choose_rescue_decision(self, *, run_state: RunState, controller_context, round_no: int) -> RescueDecision:
        reserve = self._untried_admitted_non_anchor_reserve(run_state.retrieval_state)
        seeds = select_feedback_seed_resumes(
            [run_state.scorecards_by_resume_id[item] for item in run_state.top_pool_ids if item in run_state.scorecards_by_resume_id]
        )
        decision = choose_rescue_lane(
            RescueInputs(
                stop_guidance=controller_context.stop_guidance,
                has_untried_reserve_family=reserve is not None,
                has_feedback_seed_resumes=len(seeds) >= 2,
                candidate_feedback_enabled=self.settings.candidate_feedback_enabled,
                candidate_feedback_attempted=run_state.retrieval_state.candidate_feedback_attempted,
                company_discovery_enabled=self.settings.company_discovery_enabled,
                company_discovery_attempted=run_state.retrieval_state.company_discovery_attempted,
                company_discovery_useful=self._company_discovery_useful(controller_context),
                anchor_only_broaden_attempted=run_state.retrieval_state.anchor_only_broaden_attempted,
            )
        )
        run_state.retrieval_state.rescue_lane_history.append(
            {"round_no": round_no, "selected_lane": decision.selected_lane}
        )
        return decision

    def _company_discovery_useful(self, controller_context) -> bool:
        if controller_context.rounds_remaining_after_current < 2:
            return False
        latest = controller_context.latest_search_observation
        poor_recall = latest is not None and (latest.unique_new_count == 0 or latest.shortage_count > 0)
        weak_pool = controller_context.stop_guidance.top_pool_strength in {"empty", "weak"}
        repeated_zero_gain = controller_context.stop_guidance.zero_gain_round_count >= 1
        return weak_pool or poor_recall or repeated_zero_gain
```

Add `_write_rescue_decision`:

```python
    def _write_rescue_decision(
        self,
        *,
        tracer: RunTracer,
        round_no: int,
        controller_context,
        decision: RescueDecision,
        forced_query_terms: list[str],
    ) -> None:
        tracer.write_json(
            f"rounds/round_{round_no:02d}/rescue_decision.json",
            {
                "trigger_status": controller_context.stop_guidance.quality_gate_status,
                "selected_lane": decision.selected_lane,
                "skipped_lanes": [item.model_dump(mode="json") for item in decision.skipped_lanes],
                "forced_query_terms": forced_query_terms,
            },
        )
```

- [ ] **Step 5: Add `_force_candidate_feedback_decision`**

Add:

```python
    def _force_candidate_feedback_decision(
        self,
        *,
        run_state: RunState,
        round_no: int,
        reason: str,
        tracer: RunTracer,
    ) -> SearchControllerDecision | None:
        seeds = select_feedback_seed_resumes(
            [run_state.scorecards_by_resume_id[item] for item in run_state.top_pool_ids if item in run_state.scorecards_by_resume_id]
        )
        negatives = [
            item
            for item in run_state.scorecards_by_resume_id.values()
            if item.fit_bucket == "not_fit" or item.risk_score > 60
        ]
        sent_terms = [term for record in run_state.retrieval_state.sent_query_history for term in record.query_terms]
        feedback = build_feedback_decision(
            seed_resumes=seeds,
            negative_resumes=negatives,
            existing_terms=run_state.retrieval_state.query_term_pool,
            sent_query_terms=sent_terms,
            round_no=round_no,
        )
        tracer.write_json(
            f"rounds/round_{round_no:02d}/candidate_feedback_input.json",
            {
                "seed_resume_ids": [item.resume_id for item in seeds],
                "negative_resume_ids": [item.resume_id for item in negatives],
                "sent_query_terms": sent_terms,
            },
        )
        tracer.write_json(
            f"rounds/round_{round_no:02d}/candidate_feedback_terms.json",
            feedback.model_dump(mode="json"),
        )
        run_state.retrieval_state.candidate_feedback_attempted = True
        if feedback.accepted_term is None:
            return None
        run_state.retrieval_state.query_term_pool.append(feedback.accepted_term)
        tracer.write_json(
            f"rounds/round_{round_no:02d}/candidate_feedback_decision.json",
            {
                "accepted_term": feedback.accepted_term.model_dump(mode="json"),
                "forced_query_terms": feedback.forced_query_terms,
            },
        )
        return SearchControllerDecision(
            thought_summary="Runtime rescue: candidate feedback expansion.",
            action="search_cts",
            decision_rationale=f"Runtime rescue: candidate feedback term {feedback.accepted_term.term}; {reason}",
            proposed_query_terms=feedback.forced_query_terms,
            proposed_filter_plan=build_default_filter_plan(run_state.requirement_sheet),
            response_to_reflection=f"Runtime rescue: {reason}",
        )
```

- [ ] **Step 6: Replace direct broaden override with router dispatch**

In `_run_rounds`, replace:

```python
            if controller_context.stop_guidance.quality_gate_status == "broaden_required":
                controller_decision = self._force_broaden_decision(
                    run_state=run_state,
                    round_no=round_no,
                    reason=controller_context.stop_guidance.reason,
                )
```

with:

```python
            rescue_decision = self._choose_rescue_decision(
                run_state=run_state,
                controller_context=controller_context,
                round_no=round_no,
            )
            if rescue_decision.selected_lane == "reserve_broaden":
                controller_decision = self._force_broaden_decision(
                    run_state=run_state,
                    round_no=round_no,
                    reason=controller_context.stop_guidance.reason,
                )
            elif rescue_decision.selected_lane == "candidate_feedback":
                feedback_decision = self._force_candidate_feedback_decision(
                    run_state=run_state,
                    round_no=round_no,
                    reason=controller_context.stop_guidance.reason,
                    tracer=tracer,
                )
                if feedback_decision is None:
                    run_state.retrieval_state.anchor_only_broaden_attempted = True
                    controller_decision = self._force_anchor_only_decision(
                        run_state=run_state,
                        round_no=round_no,
                        reason=controller_context.stop_guidance.reason,
                    )
                else:
                    controller_decision = feedback_decision
            elif rescue_decision.selected_lane == "anchor_only":
                run_state.retrieval_state.anchor_only_broaden_attempted = True
                controller_decision = self._force_anchor_only_decision(
                    run_state=run_state,
                    round_no=round_no,
                    reason=controller_context.stop_guidance.reason,
                )
            elif rescue_decision.selected_lane == "allow_stop":
                controller_decision = self._sanitize_controller_decision(
                    decision=controller_decision,
                    run_state=run_state,
                    round_no=round_no,
                )
            else:
                controller_decision = self._sanitize_controller_decision(
                    decision=controller_decision,
                    run_state=run_state,
                    round_no=round_no,
                )
```

Add `_force_anchor_only_decision`:

```python
    def _force_anchor_only_decision(self, *, run_state: RunState, round_no: int, reason: str) -> SearchControllerDecision:
        anchor = self._active_admitted_anchor(run_state.retrieval_state.query_term_pool)
        return SearchControllerDecision(
            thought_summary="Runtime rescue: final anchor-only broaden.",
            action="search_cts",
            decision_rationale=f"Runtime rescue: anchor-only search; {reason}",
            proposed_query_terms=[anchor.term],
            proposed_filter_plan=build_default_filter_plan(run_state.requirement_sheet),
            response_to_reflection=f"Runtime rescue: {reason}",
        )
```

After controller decision is selected and before writing `controller_decision.json`, call `_write_rescue_decision` when `rescue_decision.selected_lane != "allow_stop"`:

```python
            if rescue_decision.selected_lane != "allow_stop" and isinstance(controller_decision, SearchControllerDecision):
                self._write_rescue_decision(
                    tracer=tracer,
                    round_no=round_no,
                    controller_context=controller_context,
                    decision=rescue_decision,
                    forced_query_terms=controller_decision.proposed_query_terms,
                )
```

- [ ] **Step 7: Allow anchor-only planning after router-selected anchor-only**

Change `allow_anchor_only_query` in `build_round_retrieval_plan` call to:

```python
                allow_anchor_only_query=(
                    controller_context.stop_guidance.quality_gate_status == "broaden_required"
                    or run_state.retrieval_state.anchor_only_broaden_attempted
                ),
```

- [ ] **Step 8: Run runtime tests**

Run:

```bash
uv run pytest tests/test_runtime_state_flow.py::test_runtime_forces_broaden_with_inactive_admitted_reserve_term tests/test_runtime_state_flow.py::test_runtime_uses_candidate_feedback_before_anchor_only tests/test_runtime_state_flow.py::test_runtime_forces_anchor_only_broaden_when_no_reserve_term_remains -v
```

Expected: all tests pass after adjusting any stale assertions to expect `rescue_decision.json`.

- [ ] **Step 9: Commit**

```bash
git add src/seektalent/runtime/orchestrator.py tests/test_runtime_state_flow.py
git commit -m "Route low recall through candidate feedback"
```

---

## Task 6: Integrate Target Company Web Discovery as the Third Rescue Lane

**Files:**
- Create/modify: `src/seektalent/company_discovery/*.py`
- Modify: `src/seektalent/runtime/orchestrator.py`
- Modify: `src/seektalent/llm.py`
- Modify: `tach.toml`
- Test: `tests/test_company_discovery.py`
- Test: `tests/test_runtime_state_flow.py`

- [ ] **Step 1: Bring branch company discovery files into main**

Copy the company discovery files from the feature worktree:

```bash
rsync -a /Users/frankqdwang/.config/superpowers/worktrees/SeekTalent-0.2.4/target-company-discovery/src/seektalent/company_discovery/ /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/company_discovery/
```

Then inspect the copied files:

```bash
rg -n "target_company_enabled|company_discovery_enabled|AI六小龙|local_pack|fallback provider|PageTriageResult" src/seektalent/company_discovery
```

Expected: no local knowledge base is introduced; `PageTriageResult` is absent because Bocha rerank replaces snippet triage.

- [ ] **Step 2: Copy branch tests and config integration points**

Copy relevant branch tests:

```bash
rsync -a /Users/frankqdwang/.config/superpowers/worktrees/SeekTalent-0.2.4/target-company-discovery/tests/test_company_discovery.py /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_company_discovery.py
rsync -a /Users/frankqdwang/.config/superpowers/worktrees/SeekTalent-0.2.4/target-company-discovery/tests/test_company_discovery_config.py /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_company_discovery_config.py
```

Adjust expected defaults in `tests/test_company_discovery_config.py`:

```python
assert settings.target_company_enabled is False
assert settings.company_discovery_enabled is True
```

- [ ] **Step 3: Update `src/seektalent/llm.py` preflight**

In `preflight_models`, append:

```python
    if settings.candidate_feedback_enabled:
        model_specs.append((settings.candidate_feedback_model, None, None))
    if settings.company_discovery_enabled:
        model_specs.append((settings.company_discovery_model, None, None))
```

- [ ] **Step 4: Update `tach.toml`**

Add modules:

```toml
[[modules]]
path = "seektalent.candidate_feedback"
depends_on = []

[[modules]]
path = "seektalent.company_discovery"
depends_on = []
```

Update runtime deps:

```toml
  "seektalent.candidate_feedback",
  "seektalent.company_discovery",
```

- [ ] **Step 5: Add runtime web discovery rescue test**

Append to `tests/test_runtime_state_flow.py`:

```python
class StubCompanyDiscovery:
    async def discover_web(self, *, requirement_sheet, round_no, trigger_reason):
        from seektalent.company_discovery.models import CompanyEvidence, CompanyDiscoveryResult, TargetCompanyCandidate, TargetCompanyPlan

        evidence = CompanyEvidence(source="web", title="source", url="https://example.com", snippet="Concrete company evidence")
        company = TargetCompanyCandidate(
            name="火山引擎",
            aliases=["Volcengine"],
            source="web_inferred",
            intent="target",
            confidence=0.91,
            evidence=[evidence],
            search_usage="keyword",
        )
        plan = TargetCompanyPlan(accepted_companies=[company], web_discovery_attempted=True, stop_reason="completed")
        return CompanyDiscoveryResult(
            plan=plan,
            search_tasks=[],
            search_results=[],
            reranked_results=[],
            page_reads=[],
            trigger_reason=trigger_reason,
            evidence_candidates=[company],
        )


def test_runtime_uses_company_discovery_after_feedback_unavailable(tmp_path: Path) -> None:
    settings = make_settings(
        runs_dir=str(tmp_path / "runs"),
        mock_cts=True,
        min_rounds=1,
        max_rounds=10,
        candidate_feedback_enabled=True,
        company_discovery_enabled=True,
        bocha_api_key="bocha-key",
    )
    runtime = WorkflowRuntime(settings)
    _install_broaden_stubs(runtime, include_reserve=False)
    runtime.company_discovery = StubCompanyDiscovery()
    tracer = RunTracer(tmp_path / "trace-runs")
    job_title, jd, notes = _sample_inputs()

    try:
        run_state = asyncio.run(runtime._build_run_state(job_title=job_title, jd=jd, notes=notes, tracer=tracer))
        _, stop_reason, rounds_executed, terminal_controller_round = asyncio.run(
            runtime._run_rounds(run_state=run_state, tracer=tracer)
        )
    finally:
        tracer.close()

    rescue_decision = json.loads(
        (tracer.run_dir / "rounds" / "round_02" / "rescue_decision.json").read_text(encoding="utf-8")
    )
    controller_decision = json.loads(
        (tracer.run_dir / "rounds" / "round_02" / "controller_decision.json").read_text(encoding="utf-8")
    )

    assert rescue_decision["selected_lane"] == "web_company_discovery"
    assert controller_decision["proposed_query_terms"] == ["python", "火山引擎"]
    assert run_state.retrieval_state.company_discovery_attempted is True
    assert stop_reason == "controller_stop"
    assert rounds_executed == 2
    assert terminal_controller_round is not None
```

- [ ] **Step 6: Wire `CompanyDiscoveryService` into runtime**

In `WorkflowRuntime.__init__`, add:

```python
from seektalent.company_discovery import CompanyDiscoveryService, inject_target_company_terms, select_company_seed_terms

self.company_discovery = CompanyDiscoveryService(settings)
```

Add `_force_company_discovery_decision` that:

1. calls `self.company_discovery.discover_web(...)`;
2. sets `run_state.retrieval_state.company_discovery_attempted = True`;
3. writes company artifacts;
4. injects accepted companies with `inject_target_company_terms`;
5. selects `[anchor, company]` with `select_company_seed_terms`;
6. returns a `SearchControllerDecision`.

Use this decision only when `rescue_decision.selected_lane == "web_company_discovery"`.

- [ ] **Step 7: Keep explicit target company bootstrap disabled by default**

If branch code bootstraps explicit companies in `_build_run_state`, guard it only at the runtime top level:

```python
        if self.settings.target_company_enabled:
            plan = await self.company_discovery.bootstrap_explicit(
                requirement_sheet=requirement_sheet,
                jd=jd,
                notes=notes,
            )
            retrieval_state.target_company_plan = plan.model_dump(mode="json")
            retrieval_state.query_term_pool = inject_target_company_terms(
                retrieval_state.query_term_pool,
                plan,
                first_added_round=0,
            )
            tracer.write_json("company_discovery/bootstrap_plan.json", plan.model_dump(mode="json"))
```

Do not add flag checks inside extraction or query injection functions.

- [ ] **Step 8: Run company discovery tests**

Run:

```bash
uv run pytest tests/test_company_discovery.py tests/test_company_discovery_config.py tests/test_runtime_state_flow.py::test_runtime_uses_company_discovery_after_feedback_unavailable -v
```

Expected: all tests pass.

- [ ] **Step 9: Commit**

```bash
git add src/seektalent/company_discovery src/seektalent/runtime/orchestrator.py src/seektalent/llm.py tach.toml tests/test_company_discovery.py tests/test_company_discovery_config.py tests/test_runtime_state_flow.py
git commit -m "Add web company discovery rescue lane"
```

---

## Task 7: Render Rescue Lanes in TUI

**Files:**
- Modify: `src/seektalent/runtime/orchestrator.py`
- Modify: `src/seektalent/tui.py`
- Test: `tests/test_tui.py`

- [ ] **Step 1: Add failing TUI tests**

Append to `tests/test_tui.py`:

```python
def test_tui_renders_candidate_feedback_rescue() -> None:
    from seektalent.tui import _render_progress_lines

    lines = _render_progress_lines(
        ProgressEvent(
            type="rescue_lane_completed",
            message="Recall repair: extracted feedback term LangGraph from 3 fit seed resumes.",
            payload={
                "stage": "rescue",
                "selected_lane": "candidate_feedback",
                "accepted_term": "LangGraph",
                "seed_resume_count": 3,
            },
        )
    )

    rendered = "\n".join(lines)
    assert "召回修复：从 3 位高匹配候选人中提取扩展词：LangGraph" in rendered


def test_tui_renders_web_company_discovery_rescue() -> None:
    from seektalent.tui import _render_progress_lines

    lines = _render_progress_lines(
        ProgressEvent(
            type="company_discovery_completed",
            message="Target company discovery completed.",
            payload={
                "stage": "company_discovery",
                "search_result_count": 118,
                "reranked_result_count": 8,
                "opened_page_count": 6,
                "accepted_company_count": 5,
            },
        )
    )

    rendered = "\n".join(lines)
    assert "目标公司发现：找到 118 个网页，重排 8 个，阅读 6 页，接受 5 家。" in rendered
```

- [ ] **Step 2: Run failing TUI tests**

Run:

```bash
uv run pytest tests/test_tui.py::test_tui_renders_candidate_feedback_rescue tests/test_tui.py::test_tui_renders_web_company_discovery_rescue -v
```

Expected: fail because rescue/company discovery rendering is not implemented in main.

- [ ] **Step 3: Update runtime progress emission**

After candidate feedback decision succeeds, emit:

```python
        self._emit_progress(
            progress_callback,
            "rescue_lane_completed",
            f"Recall repair: extracted feedback term {feedback.accepted_term.term} from {len(seeds)} fit seed resumes.",
            round_no=round_no,
            payload={
                "stage": "rescue",
                "selected_lane": "candidate_feedback",
                "accepted_term": feedback.accepted_term.term,
                "seed_resume_count": len(seeds),
            },
        )
```

After company discovery completes, emit:

```python
        self._emit_progress(
            progress_callback,
            "company_discovery_completed",
            self._company_discovery_message(result.plan),
            round_no=round_no,
            payload={
                "stage": "company_discovery",
                "search_result_count": len(result.search_results),
                "reranked_result_count": len(result.reranked_results),
                "opened_page_count": len(result.page_reads),
                "accepted_company_count": len(result.plan.accepted_companies),
            },
        )
```

- [ ] **Step 4: Update `src/seektalent/tui.py`**

In `_render_progress_lines`, add:

```python
    if event.type == "rescue_lane_completed":
        return _render_rescue_lane_completed(payload)
    if event.type == "company_discovery_completed":
        return _render_company_discovery_completed(payload)
```

Add helpers:

```python
def _render_rescue_lane_completed(payload: dict[str, Any]) -> list[str]:
    if payload.get("selected_lane") == "candidate_feedback":
        term = str(payload.get("accepted_term") or "")
        count = int(payload.get("seed_resume_count") or 0)
        return [f"召回修复：从 {count} 位高匹配候选人中提取扩展词：{term}"]
    return ["召回修复：执行了一次受控扩展。"]


def _render_company_discovery_completed(payload: dict[str, Any]) -> list[str]:
    found = int(payload.get("search_result_count") or 0)
    reranked = int(payload.get("reranked_result_count") or 0)
    opened = int(payload.get("opened_page_count") or 0)
    accepted = int(payload.get("accepted_company_count") or 0)
    return [f"目标公司发现：找到 {found} 个网页，重排 {reranked} 个，阅读 {opened} 页，接受 {accepted} 家。"]
```

- [ ] **Step 5: Run TUI tests**

Run:

```bash
uv run pytest tests/test_tui.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/seektalent/runtime/orchestrator.py src/seektalent/tui.py tests/test_tui.py
git commit -m "Render rescue lanes in TUI"
```

---

## Task 8: Add Audit Coverage for Run Config and Artifacts

**Files:**
- Modify: `src/seektalent/runtime/orchestrator.py`
- Test: `tests/test_runtime_audit.py`
- Test: `tests/test_llm_provider_config.py`

- [ ] **Step 1: Add failing audit tests**

Append to `tests/test_runtime_audit.py`:

```python
def test_run_config_records_rescue_settings_without_secrets(tmp_path: Path) -> None:
    settings = make_settings(
        runs_dir=str(tmp_path / "runs"),
        mock_cts=True,
        bocha_api_key="secret-bocha-key",
        candidate_feedback_enabled=True,
        target_company_enabled=False,
        company_discovery_enabled=True,
    )
    runtime = WorkflowRuntime(settings)
    tracer = RunTracer(tmp_path / "trace-runs")

    try:
        runtime._write_run_config(tracer)
    finally:
        tracer.close()

    config = json.loads((tracer.run_dir / "run_config.json").read_text(encoding="utf-8"))
    text = json.dumps(config, ensure_ascii=False)

    assert config["settings"]["candidate_feedback_enabled"] is True
    assert config["settings"]["target_company_enabled"] is False
    assert config["settings"]["company_discovery_enabled"] is True
    assert "secret-bocha-key" not in text
    assert config["settings"]["has_bocha_key"] is True
```

- [ ] **Step 2: Run failing audit test**

Run:

```bash
uv run pytest tests/test_runtime_audit.py::test_run_config_records_rescue_settings_without_secrets -v
```

Expected: fail if run config does not include sanitized rescue settings.

- [ ] **Step 3: Update run config serialization**

In `_safe_settings_snapshot` or equivalent run-config helper in `src/seektalent/runtime/orchestrator.py`, include:

```python
        "candidate_feedback_enabled": self.settings.candidate_feedback_enabled,
        "candidate_feedback_model": self.settings.candidate_feedback_model,
        "candidate_feedback_reasoning_effort": self.settings.candidate_feedback_reasoning_effort,
        "target_company_enabled": self.settings.target_company_enabled,
        "company_discovery_enabled": self.settings.company_discovery_enabled,
        "company_discovery_provider": self.settings.company_discovery_provider,
        "has_bocha_key": bool(self.settings.bocha_api_key),
        "company_discovery_model": self.settings.company_discovery_model,
        "company_discovery_reasoning_effort": self.settings.company_discovery_reasoning_effort,
        "company_discovery_max_search_calls": self.settings.company_discovery_max_search_calls,
        "company_discovery_max_results_per_query": self.settings.company_discovery_max_results_per_query,
        "company_discovery_max_open_pages": self.settings.company_discovery_max_open_pages,
        "company_discovery_timeout_seconds": self.settings.company_discovery_timeout_seconds,
        "company_discovery_accepted_company_limit": self.settings.company_discovery_accepted_company_limit,
```

Do not serialize `bocha_api_key`.

- [ ] **Step 4: Add LLM preflight tests**

Append to `tests/test_llm_provider_config.py`:

```python
def test_preflight_includes_feedback_and_company_models_when_enabled(monkeypatch) -> None:
    from seektalent import llm

    seen: list[str] = []

    class FakeProfile:
        supports_json_schema_output = True

    class FakeModel:
        profile = FakeProfile()

    def fake_build_model(model_id, *, openai_base_url=None, openai_api_key=None):
        seen.append(model_id)
        return FakeModel()

    monkeypatch.setattr(llm, "build_model", fake_build_model)

    settings = make_settings(
        candidate_feedback_enabled=True,
        company_discovery_enabled=True,
        candidate_feedback_model="openai-chat:qwen3.5-flash",
        company_discovery_model="openai-chat:qwen3.5-flash",
    )
    llm.preflight_models(settings)

    assert "openai-chat:qwen3.5-flash" in seen
```

- [ ] **Step 5: Run audit/provider tests**

Run:

```bash
uv run pytest tests/test_runtime_audit.py tests/test_llm_provider_config.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/seektalent/runtime/orchestrator.py src/seektalent/llm.py tests/test_runtime_audit.py tests/test_llm_provider_config.py
git commit -m "Audit rescue settings and models"
```

---

## Task 9: Final Verification and Real TUI Smoke

**Files:**
- No planned source edits.
- Uses existing benchmark artifacts and real `.env`.

- [ ] **Step 1: Run focused tests**

Run:

```bash
uv run pytest tests/test_rescue_router_config.py tests/test_candidate_feedback.py tests/test_rescue_router.py tests/test_company_discovery.py tests/test_runtime_state_flow.py tests/test_runtime_audit.py tests/test_tui.py -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run full tests**

Run:

```bash
uv run pytest -q
```

Expected: all tests pass.

- [ ] **Step 3: Run lint and whitespace checks**

Run:

```bash
uv run ruff check .
git diff --check
```

Expected: ruff reports no errors; `git diff --check` exits with no output.

- [ ] **Step 4: Prepare `agent_jd_002` smoke input**

Run:

```bash
python - <<'PY'
import json
from pathlib import Path

row = next(
    json.loads(line)
    for line in Path("artifacts/benchmarks/agent_jds.jsonl").read_text(encoding="utf-8").splitlines()
    if json.loads(line)["jd_id"] == "agent_jd_002"
)
base = Path("/tmp/seektalent-agent-jd-002")
base.mkdir(parents=True, exist_ok=True)
(base / "job_title.txt").write_text(row["job_title"], encoding="utf-8")
(base / "jd.txt").write_text(row["job_description"], encoding="utf-8")
(base / "notes.txt").write_text(row.get("hiring_notes", ""), encoding="utf-8")
print(base)
PY
```

Expected: `/tmp/seektalent-agent-jd-002` exists with `job_title.txt`, `jd.txt`, and `notes.txt`.

- [ ] **Step 5: Run real CLI/TUI smoke with `agent_jd_002`**

Run with real `.env` keys loaded:

```bash
SEEKTALENT_CANDIDATE_FEEDBACK_ENABLED=true \
SEEKTALENT_TARGET_COMPANY_ENABLED=false \
SEEKTALENT_COMPANY_DISCOVERY_ENABLED=true \
uv run seektalent exec run \
  --job-title-file /tmp/seektalent-agent-jd-002/job_title.txt \
  --jd-file /tmp/seektalent-agent-jd-002/jd.txt \
  --notes-file /tmp/seektalent-agent-jd-002/notes.txt \
  --env-file .env \
  --output-dir runs \
  --json
```

Expected:

- run completes without exception;
- `run_config.json` records candidate feedback enabled, target company disabled, company discovery enabled;
- if rescue triggers, `rescue_decision.json` exists in the triggering round;
- if web discovery triggers, company discovery artifacts exist and no Bocha key is written to artifacts.

- [ ] **Step 6: Prepare `bigdata_jd_001` smoke input**

Run:

```bash
python - <<'PY'
import json
from pathlib import Path

row = next(
    json.loads(line)
    for line in Path("artifacts/benchmarks/bigdata.jsonl").read_text(encoding="utf-8").splitlines()
    if json.loads(line)["jd_id"] == "bigdata_jd_001"
)
base = Path("/tmp/seektalent-bigdata-jd-001")
base.mkdir(parents=True, exist_ok=True)
(base / "job_title.txt").write_text(row["job_title"], encoding="utf-8")
(base / "jd.txt").write_text(row["job_description"], encoding="utf-8")
(base / "notes.txt").write_text(row.get("hiring_notes", ""), encoding="utf-8")
print(base)
PY
```

Expected: `/tmp/seektalent-bigdata-jd-001` exists with `job_title.txt`, `jd.txt`, and `notes.txt`.

- [ ] **Step 7: Run real CLI/TUI smoke with `bigdata_jd_001`**

Run:

```bash
SEEKTALENT_CANDIDATE_FEEDBACK_ENABLED=true \
SEEKTALENT_TARGET_COMPANY_ENABLED=false \
SEEKTALENT_COMPANY_DISCOVERY_ENABLED=true \
uv run seektalent exec run \
  --job-title-file /tmp/seektalent-bigdata-jd-001/job_title.txt \
  --jd-file /tmp/seektalent-bigdata-jd-001/jd.txt \
  --notes-file /tmp/seektalent-bigdata-jd-001/notes.txt \
  --env-file .env \
  --output-dir runs \
  --json
```

Expected:

- run completes without exception;
- normal productive retrieval can finish without triggering web discovery;
- if rescue triggers, TUI shows the executed rescue lane.

- [ ] **Step 8: Summarize smoke results**

Write a short note in the final implementation response with:

```text
agent_jd_002 run directory:
stop reason:
rounds executed:
whether candidate feedback triggered:
whether web discovery triggered:
fit count:
average score:

bigdata_jd_001 run directory:
stop reason:
rounds executed:
whether candidate feedback triggered:
whether web discovery triggered:
fit count:
average score:
```

- [ ] **Step 9: Commit any final fixes**

If final verification required edits, stage only the files changed for those fixes from this expected file set, then commit:

```bash
git status --short
git add src/seektalent/candidate_feedback src/seektalent/company_discovery src/seektalent/runtime/rescue_router.py src/seektalent/runtime/orchestrator.py src/seektalent/config.py src/seektalent/default.env src/seektalent/llm.py src/seektalent/models.py src/seektalent/tui.py .env.example tach.toml tests/test_rescue_router_config.py tests/test_candidate_feedback.py tests/test_rescue_router.py tests/test_runtime_state_flow.py tests/test_company_discovery.py tests/test_runtime_audit.py tests/test_tui.py tests/test_llm_provider_config.py
git commit -m "Stabilize retrieval rescue router"
```

If no edits were required, do not create an empty commit.

---

## Self-Review

Spec coverage:

- Product defaults are covered in Task 1.
- Candidate feedback extraction, no dictionary, no Jieba/spaCy, one-shot query, and artifacts are covered in Tasks 2, 3, and 5.
- Rescue priority order is covered in Tasks 4 and 5.
- Web discovery as third lane and explicit bootstrap disabled by default are covered in Task 6.
- TUI trace is covered in Task 7.
- Audit, secret safety, and model preflight are covered in Task 8.
- Real run verification is covered in Task 9.

Placeholder scan:

- The plan does not contain placeholder markers or unnamed files.
- Each task lists exact files, commands, expected failures, expected passing conditions, and commit boundaries.

Type consistency:

- Candidate feedback uses `CandidateFeedbackDecision`, `FeedbackCandidateTerm`, and existing `QueryTermCandidate` consistently.
- Router uses `RescueInputs`, `RescueDecision`, and `selected_lane` consistently.
- Runtime state uses `candidate_feedback_attempted`, `company_discovery_attempted`, `anchor_only_broaden_attempted`, `rescue_lane_history`, and `target_company_plan`.
