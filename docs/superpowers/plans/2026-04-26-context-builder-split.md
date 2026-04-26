# Context Builder Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split runtime context assembly into consumer-specific modules while keeping behavior and schemas unchanged.

**Architecture:** Move controller, reflection, finalize, and scoring context builders into separate runtime modules. Keep a thin `context_builder.py` facade for compatibility during this step, and isolate the few shared view projections into `context_views.py`.

**Tech Stack:** Python 3.12, Pydantic models, pytest, existing runtime/orchestrator test suite

---

## File Map

- Create: `src/seektalent/runtime/context_views.py`
  Purpose: hold the small shared projections used by multiple context builders.

- Create: `src/seektalent/runtime/scoring_context.py`
  Purpose: own `build_scoring_context`.

- Create: `src/seektalent/runtime/reflection_context.py`
  Purpose: own `build_reflection_context`.

- Create: `src/seektalent/runtime/finalize_context.py`
  Purpose: own `build_finalize_context`.

- Create: `src/seektalent/runtime/controller_context.py`
  Purpose: own `build_controller_context` and controller-only stop-guidance policy helpers.

- Modify: `src/seektalent/runtime/context_builder.py`
  Purpose: reduce it to a thin re-export facade with no real implementation logic.

- Modify: `src/seektalent/runtime/orchestrator.py`
  Purpose: import `build_*_context` from the new modules instead of the old bucket.

- Modify: `tests/test_context_builder.py`
  Purpose: cover the new modules directly and lock the facade behavior.

- Modify only if import drift appears during regression:
  - `tests/test_llm_input_prompts.py`
  - `tests/test_runtime_audit.py`
  - `tests/test_runtime_state_flow.py`

## Task 1: Extract Shared Views And The Small Builders

**Files:**
- Create: `src/seektalent/runtime/context_views.py`
- Create: `src/seektalent/runtime/scoring_context.py`
- Create: `src/seektalent/runtime/reflection_context.py`
- Create: `src/seektalent/runtime/finalize_context.py`
- Modify: `tests/test_context_builder.py`

- [ ] **Step 1: Write the failing direct-module tests**

In `tests/test_context_builder.py`, add direct imports for the new modules and one focused test that exercises them without touching controller policy:

```python
from seektalent.runtime.finalize_context import build_finalize_context as build_finalize_context_direct
from seektalent.runtime.reflection_context import build_reflection_context as build_reflection_context_direct
from seektalent.runtime.scoring_context import build_scoring_context as build_scoring_context_direct
```

```python
def test_split_modules_build_scoring_reflection_and_finalize_contexts() -> None:
    run_state = _run_state_for_stop_gate(
        candidates=[_scored_candidate("resume-1", round_no=1)],
        completed_rounds=1,
        include_untried_family=True,
    )
    round_state = run_state.round_history[0]

    scoring_context = build_scoring_context_direct(
        run_state=run_state,
        round_no=1,
        normalized_resume=NormalizedResume(resume_id="resume-1"),
        runtime_only_constraints=[],
    )
    reflection_context = build_reflection_context_direct(run_state=run_state, round_state=round_state)
    finalize_context = build_finalize_context_direct(
        run_state=run_state,
        rounds_executed=1,
        stop_reason="max_rounds",
        run_id="run-1",
        run_dir="/tmp/run-1",
    )

    assert scoring_context.round_no == 1
    assert reflection_context.current_retrieval_plan.plan_version == round_state.retrieval_plan.plan_version
    assert finalize_context.top_candidates[0].resume_id == "resume-1"
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```bash
/Users/frankqdwang/Agents/SeekTalent-0.2.4/.venv/bin/pytest tests/test_context_builder.py::test_split_modules_build_scoring_reflection_and_finalize_contexts -q
```

Expected: FAIL with `ModuleNotFoundError` for one or more of the new runtime modules.

- [ ] **Step 3: Create the shared views module**

Create `src/seektalent/runtime/context_views.py` with the moved shared projections:

```python
from __future__ import annotations

from seektalent.models import (
    ReflectionSummaryView,
    RoundState,
    RunState,
    ScoredCandidate,
    SearchObservationView,
    TopPoolEntryView,
)


def top_candidates(run_state: RunState) -> list[ScoredCandidate]:
    return [
        run_state.scorecards_by_resume_id[resume_id]
        for resume_id in run_state.top_pool_ids
        if resume_id in run_state.scorecards_by_resume_id
    ]


def dropped_candidates(run_state: RunState, round_state: RoundState) -> list[ScoredCandidate]:
    if round_state.dropped_candidates:
        return round_state.dropped_candidates
    return [
        run_state.scorecards_by_resume_id[resume_id]
        for resume_id in round_state.dropped_candidate_ids
        if resume_id in run_state.scorecards_by_resume_id
    ]


def _top_pool_entry(candidate: ScoredCandidate) -> TopPoolEntryView:
    return TopPoolEntryView(
        resume_id=candidate.resume_id,
        fit_bucket=candidate.fit_bucket,
        overall_score=candidate.overall_score,
        must_have_match_score=candidate.must_have_match_score,
        risk_score=candidate.risk_score,
        matched_must_haves=candidate.matched_must_haves[:4],
        risk_flags=candidate.risk_flags[:4],
        reasoning_summary=candidate.reasoning_summary,
    )


def _search_observation_view(observation) -> SearchObservationView | None:
    if observation is None:
        return None
    return SearchObservationView(
        unique_new_count=observation.unique_new_count,
        shortage_count=observation.shortage_count,
        fetch_attempt_count=observation.fetch_attempt_count,
        exhausted_reason=observation.exhausted_reason,
        new_candidate_summaries=observation.new_candidate_summaries[:5],
        adapter_notes=observation.adapter_notes[:5],
        city_search_summaries=observation.city_search_summaries,
    )


def _reflection_summary(advice) -> ReflectionSummaryView | None:
    if advice is None:
        return None
    return ReflectionSummaryView(
        decision="stop" if advice.suggest_stop else "continue",
        stop_reason=advice.suggested_stop_reason,
        reflection_summary=advice.reflection_summary,
        reflection_rationale=advice.reflection_rationale,
    )
```

- [ ] **Step 4: Create the three small builder modules**

Create `src/seektalent/runtime/scoring_context.py`:

```python
from __future__ import annotations

from seektalent.models import RuntimeConstraint, RunState, ScoringContext
from seektalent.tracing import json_sha256


def build_scoring_context(
    *,
    run_state: RunState,
    round_no: int,
    normalized_resume,
    runtime_only_constraints: list[RuntimeConstraint] | None = None,
) -> ScoringContext:
    return ScoringContext(
        round_no=round_no,
        scoring_policy=run_state.scoring_policy,
        normalized_resume=normalized_resume,
        requirement_sheet_sha256=json_sha256(run_state.requirement_sheet.model_dump(mode="json")),
        runtime_only_constraints=list(runtime_only_constraints or []),
    )
```

Create `src/seektalent/runtime/reflection_context.py`:

```python
from __future__ import annotations

from seektalent.models import ReflectionContext, RoundState, RunState
from seektalent.runtime.context_views import dropped_candidates, top_candidates


def build_reflection_context(
    *,
    run_state: RunState,
    round_state: RoundState,
) -> ReflectionContext:
    if round_state.search_observation is None:
        raise ValueError("round_state.search_observation is required for reflection context")
    return ReflectionContext(
        round_no=round_state.round_no,
        full_jd=run_state.input_truth.jd,
        full_notes=run_state.input_truth.notes,
        requirement_sheet=run_state.requirement_sheet,
        current_retrieval_plan=round_state.retrieval_plan,
        search_observation=round_state.search_observation,
        search_attempts=round_state.search_attempts,
        top_candidates=round_state.top_candidates or top_candidates(run_state),
        dropped_candidates=dropped_candidates(run_state, round_state),
        scoring_failures=[],
        sent_query_history=run_state.retrieval_state.sent_query_history,
        query_term_pool=run_state.retrieval_state.query_term_pool,
    )
```

Create `src/seektalent/runtime/finalize_context.py`:

```python
from __future__ import annotations

from seektalent.models import FinalizeContext, RunState
from seektalent.requirements import build_requirement_digest
from seektalent.runtime.context_views import top_candidates


def build_finalize_context(
    *,
    run_state: RunState,
    rounds_executed: int,
    stop_reason: str,
    run_id: str,
    run_dir: str,
) -> FinalizeContext:
    return FinalizeContext(
        run_id=run_id,
        run_dir=run_dir,
        rounds_executed=rounds_executed,
        stop_reason=stop_reason,
        top_candidates=top_candidates(run_state),
        requirement_digest=build_requirement_digest(run_state.requirement_sheet),
        sent_query_history=run_state.retrieval_state.sent_query_history,
    )
```

- [ ] **Step 5: Run the focused test to verify it passes**

Run:

```bash
/Users/frankqdwang/Agents/SeekTalent-0.2.4/.venv/bin/pytest tests/test_context_builder.py::test_split_modules_build_scoring_reflection_and_finalize_contexts -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/seektalent/runtime/context_views.py src/seektalent/runtime/scoring_context.py src/seektalent/runtime/reflection_context.py src/seektalent/runtime/finalize_context.py tests/test_context_builder.py
git commit -m "refactor: extract runtime context view modules"
```

## Task 2: Move Controller Context And Stop Guidance

**Files:**
- Create: `src/seektalent/runtime/controller_context.py`
- Modify: `tests/test_context_builder.py`

- [ ] **Step 1: Write the failing controller-module test**

In `tests/test_context_builder.py`, add a direct import and one controller-specific assertion:

```python
from seektalent.runtime.controller_context import build_controller_context as build_controller_context_direct
```

```python
def test_controller_context_direct_module_preserves_stop_guidance() -> None:
    run_state = _run_state_for_stop_gate(
        candidates=[_scored_candidate("resume-1", round_no=1)],
        completed_rounds=1,
        include_untried_family=True,
    )

    context = build_controller_context_direct(
        run_state=run_state,
        round_no=2,
        min_rounds=1,
        max_rounds=4,
        target_new=10,
    )

    assert context.stop_guidance.can_stop is False
    assert context.stop_guidance.untried_admitted_families
    assert context.latest_search_observation is not None
```

- [ ] **Step 2: Run the direct controller test to verify it fails**

Run:

```bash
/Users/frankqdwang/Agents/SeekTalent-0.2.4/.venv/bin/pytest tests/test_context_builder.py::test_controller_context_direct_module_preserves_stop_guidance -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'seektalent.runtime.controller_context'`.

- [ ] **Step 3: Create `controller_context.py` with controller-only policy**

Create `src/seektalent/runtime/controller_context.py` by moving the existing controller code out of `context_builder.py`:

```python
from __future__ import annotations

from math import ceil

from seektalent.models import (
    ControllerContext,
    QueryTermCandidate,
    RunState,
    ScoredCandidate,
    StopGuidance,
    TopPoolStrength,
    unique_strings,
    is_title_anchor_role,
)
from seektalent.requirements import build_requirement_digest
from seektalent.runtime.context_views import (
    _reflection_summary,
    _search_observation_view,
    _top_pool_entry,
    top_candidates,
)

BUDGET_STOP_RATIO = 0.8
STRONG_FIT_STOP_MIN = 3
HIGH_RISK_FIT_THRESHOLD = 70


def build_controller_context(
    *,
    run_state: RunState,
    round_no: int,
    min_rounds: int,
    max_rounds: int,
    target_new: int,
) -> ControllerContext:
    ...


def _build_stop_guidance(...) -> StopGuidance:
    ...


def _budget_reminder(...) -> str:
    ...


def _tried_families(
    query_term_pool: list[QueryTermCandidate],
    sent_query_history,
) -> list[str]:
    ...


def _untried_admitted_families(...) -> list[str]:
    ...


def _broadening_attempted(...) -> bool:
    ...


def _term_key(term: str) -> str:
    return " ".join(term.strip().split()).casefold()
```

Use the current implementations from `context_builder.py` verbatim. Do not change thresholds, sort order, or broadening detection.

- [ ] **Step 4: Run the direct controller test to verify it passes**

Run:

```bash
/Users/frankqdwang/Agents/SeekTalent-0.2.4/.venv/bin/pytest tests/test_context_builder.py::test_controller_context_direct_module_preserves_stop_guidance -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/seektalent/runtime/controller_context.py tests/test_context_builder.py
git commit -m "refactor: split controller context policy"
```

## Task 3: Reduce `context_builder.py` To A Thin Facade And Migrate Imports

**Files:**
- Modify: `src/seektalent/runtime/context_builder.py`
- Modify: `src/seektalent/runtime/orchestrator.py`
- Modify: `tests/test_context_builder.py`

- [ ] **Step 1: Write the failing facade test**

In `tests/test_context_builder.py`, add one test that locks the thin-facade behavior:

```python
from seektalent.runtime.context_builder import build_controller_context
from seektalent.runtime.controller_context import build_controller_context as build_controller_context_direct
from seektalent.runtime.finalize_context import build_finalize_context as build_finalize_context_direct
from seektalent.runtime.reflection_context import build_reflection_context as build_reflection_context_direct
from seektalent.runtime.scoring_context import build_scoring_context as build_scoring_context_direct
```

```python
def test_context_builder_is_a_thin_reexport_facade() -> None:
    assert build_controller_context is build_controller_context_direct
    assert build_scoring_context is build_scoring_context_direct
    assert build_reflection_context is build_reflection_context_direct
    assert build_finalize_context is build_finalize_context_direct
```

- [ ] **Step 2: Run the facade test to verify it fails**

Run:

```bash
/Users/frankqdwang/Agents/SeekTalent-0.2.4/.venv/bin/pytest tests/test_context_builder.py::test_context_builder_is_a_thin_reexport_facade -q
```

Expected: FAIL because `context_builder.py` still defines its own functions.

- [ ] **Step 3: Replace `context_builder.py` with a pure re-export layer**

Update `src/seektalent/runtime/context_builder.py` to:

```python
from seektalent.runtime.controller_context import build_controller_context
from seektalent.runtime.finalize_context import build_finalize_context
from seektalent.runtime.reflection_context import build_reflection_context
from seektalent.runtime.scoring_context import build_scoring_context

__all__ = [
    "build_controller_context",
    "build_finalize_context",
    "build_reflection_context",
    "build_scoring_context",
]
```

- [ ] **Step 4: Update orchestrator imports to the new modules**

In `src/seektalent/runtime/orchestrator.py`, replace:

```python
from seektalent.runtime.context_builder import (
    build_controller_context,
    build_finalize_context,
    build_reflection_context,
    build_scoring_context,
)
```

with:

```python
from seektalent.runtime.controller_context import build_controller_context
from seektalent.runtime.finalize_context import build_finalize_context
from seektalent.runtime.reflection_context import build_reflection_context
from seektalent.runtime.scoring_context import build_scoring_context
```

- [ ] **Step 5: Run the context-builder slice**

Run:

```bash
/Users/frankqdwang/Agents/SeekTalent-0.2.4/.venv/bin/pytest tests/test_context_builder.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/seektalent/runtime/context_builder.py src/seektalent/runtime/orchestrator.py tests/test_context_builder.py
git commit -m "refactor: thin runtime context builder facade"
```

## Task 4: Focused Regression And Import Sweep

**Files:**
- Modify: only if a stale import or stale helper reference remains
- Test: `tests/test_context_builder.py`
- Test: `tests/test_llm_input_prompts.py`
- Test: `tests/test_runtime_audit.py`
- Test: `tests/test_runtime_state_flow.py`

- [ ] **Step 1: Run the focused regression suite**

Run:

```bash
/Users/frankqdwang/Agents/SeekTalent-0.2.4/.venv/bin/pytest tests/test_context_builder.py tests/test_llm_input_prompts.py tests/test_runtime_audit.py tests/test_runtime_state_flow.py -q
```

Expected: PASS.

- [ ] **Step 2: If a failure appears, fix only import drift or misplaced helper references**

Allowed changes:

- import path updates
- helper imports from `context_views.py`
- direct calls to the moved `build_*_context` functions

Not allowed:

- prompt wording changes
- schema changes
- stop-guidance logic changes
- provider/runtime behavior changes

- [ ] **Step 3: Re-run the focused regression suite**

Run:

```bash
/Users/frankqdwang/Agents/SeekTalent-0.2.4/.venv/bin/pytest tests/test_context_builder.py tests/test_llm_input_prompts.py tests/test_runtime_audit.py tests/test_runtime_state_flow.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/seektalent/runtime/context_builder.py src/seektalent/runtime/context_views.py src/seektalent/runtime/controller_context.py src/seektalent/runtime/reflection_context.py src/seektalent/runtime/finalize_context.py src/seektalent/runtime/scoring_context.py src/seektalent/runtime/orchestrator.py tests/test_context_builder.py
git commit -m "test: verify context builder split"
```

## Self-Review

### Spec coverage

- Split `context_builder.py` by consumer: covered by Tasks 1-3.
- Keep controller-only policy local: covered by Task 2.
- Isolate shared projections in a small support module: covered by Task 1.
- Keep a thin `context_builder.py` facade for this step: covered by Task 3.
- Avoid schema, prompt, and runtime behavior changes: enforced by Task 4 constraints.

### Placeholder scan

- No `TODO`, `TBD`, or deferred placeholders remain.
- Every code-changing step includes exact file paths, code snippets, commands, and expected outcomes.

### Type consistency

- The plan consistently uses `build_controller_context`, `build_scoring_context`, `build_reflection_context`, and `build_finalize_context`.
- Shared helpers are consistently placed in `context_views.py`.
- The plan keeps `context_builder.py` as a re-export facade rather than a second logic host.
