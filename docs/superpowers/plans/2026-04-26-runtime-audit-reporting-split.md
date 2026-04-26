# Runtime Audit Reporting Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move runtime diagnostics/audit builders and markdown report renderers out of `WorkflowRuntime` without changing artifact schemas or report wording.

**Architecture:** Extract two plain-function modules: `runtime_diagnostics.py` for structured payload shaping and `runtime_reports.py` for human-readable markdown/text rendering. Keep `WorkflowRuntime` responsible for orchestration, tracer writes, and LLM call artifact wiring.

**Tech Stack:** Python 3.12, Pydantic models, pytest, existing runtime audit/state-flow tests

---

## File Map

- Create: `src/seektalent/runtime/runtime_diagnostics.py`
  Purpose: own structured audit helpers and artifact payload builders.

- Create: `src/seektalent/runtime/runtime_reports.py`
  Purpose: own markdown/text renderers for run and round summaries.

- Modify: `src/seektalent/runtime/orchestrator.py`
  Purpose: call the extracted diagnostics/reporting functions instead of owning their implementations.

- Modify: `tests/test_runtime_audit.py`
  Purpose: add direct-module seam coverage and keep artifact expectations stable.

- Modify only if import drift appears:
  - `tests/test_runtime_state_flow.py`
  - `tests/test_llm_input_prompts.py`

## Task 1: Extract Structured Diagnostics Helpers

**Files:**
- Create: `src/seektalent/runtime/runtime_diagnostics.py`
- Modify: `tests/test_runtime_audit.py`

- [ ] **Step 1: Write a failing direct-module test for diagnostics helpers**

In `tests/test_runtime_audit.py`, add a direct import and one focused test that exercises the extracted helper surface without touching `WorkflowRuntime` orchestration:

```python
from seektalent.runtime.runtime_diagnostics import (
    slim_controller_context as slim_controller_context_direct,
    slim_finalize_context as slim_finalize_context_direct,
    slim_reflection_context as slim_reflection_context_direct,
)
```

```python
def test_runtime_diagnostics_direct_helpers_match_legacy_outputs() -> None:
    runtime = WorkflowRuntime(make_settings())
    run_state = _build_run_state_fixture()
    round_state = run_state.round_history[0]
    controller_context = build_controller_context(
        run_state=run_state,
        round_no=1,
        min_rounds=1,
        max_rounds=4,
        target_new=10,
    )
    reflection_context = build_reflection_context(run_state=run_state, round_state=round_state)
    finalize_context = build_finalize_context(
        run_state=run_state,
        rounds_executed=1,
        stop_reason="max_rounds_reached",
        run_id="run-1",
        run_dir="/tmp/run-1",
    )

    assert slim_controller_context_direct(
        context=controller_context,
        input_text_refs_builder=runtime._input_text_refs,
    ) == runtime._slim_controller_context(controller_context)
    assert slim_reflection_context_direct(
        context=reflection_context,
        input_text_refs_builder=runtime._input_text_refs,
        slim_search_attempt=runtime._slim_search_attempt,
        slim_scored_candidate=runtime._slim_scored_candidate,
    ) == runtime._slim_reflection_context(reflection_context)
    assert slim_finalize_context_direct(
        context=finalize_context,
        slim_scored_candidate=runtime._slim_scored_candidate,
    ) == runtime._slim_finalize_context(finalize_context)
```

- [ ] **Step 2: Run the direct helper test to verify it fails**

Run:

```bash
/Users/frankqdwang/Agents/SeekTalent-0.2.4/.venv/bin/pytest tests/test_runtime_audit.py::test_runtime_diagnostics_direct_helpers_match_legacy_outputs -q
```

Expected: FAIL with `ModuleNotFoundError` for `seektalent.runtime.runtime_diagnostics`.

- [ ] **Step 3: Create `runtime_diagnostics.py` with the slim helpers**

Create `src/seektalent/runtime/runtime_diagnostics.py` and move these helpers from `orchestrator.py` into it:

```python
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
from typing import Any, Callable, Collection

from seektalent.models import (
    ControllerContext,
    EvaluationResult,
    FinalResult,
    FinalizeContext,
    LocationExecutionPhase,
    NormalizedResume,
    QueryRole,
    QueryTermCandidate,
    ReflectionAdvice,
    ReflectionContext,
    RunState,
    ScoredCandidate,
    SearchAttempt,
    SearchObservation,
    SearchControllerDecision,
    SentQueryRecord,
    TerminalControllerRound,
)
from seektalent.requirements import build_requirement_digest
from seektalent.scoring.models import scored_candidate_sort_key
from seektalent.tracing import json_char_count, json_sha256
```

Move, without behavior changes:

- `slim_controller_context(...)`
- `slim_reflection_context(...)`
- `slim_finalize_context(...)`
- `slim_search_attempt(...)`
- `slim_scored_candidate(...)`
- `slim_top_pool_snapshot(...)`

Use public names in the new module. For example:

```python
def slim_controller_context(
    *,
    context: ControllerContext,
    input_text_refs_builder: Callable[..., dict[str, object]],
) -> dict[str, object]:
    ...
```

```python
def slim_reflection_context(
    *,
    context: ReflectionContext,
    input_text_refs_builder: Callable[..., dict[str, object]],
    slim_search_attempt: Callable[[SearchAttempt], dict[str, object]],
    slim_scored_candidate: Callable[..., dict[str, object]],
) -> dict[str, object]:
    ...
```

Keep the returned payloads byte-for-byte compatible with the existing tests.

- [ ] **Step 4: Run the direct helper test to verify it passes**

Run:

```bash
/Users/frankqdwang/Agents/SeekTalent-0.2.4/.venv/bin/pytest tests/test_runtime_audit.py::test_runtime_diagnostics_direct_helpers_match_legacy_outputs -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/seektalent/runtime/runtime_diagnostics.py tests/test_runtime_audit.py
git commit -m "refactor: extract runtime diagnostics helpers"
```

## Task 2: Extract Artifact Builders Into `runtime_diagnostics.py`

**Files:**
- Modify: `src/seektalent/runtime/runtime_diagnostics.py`
- Modify: `src/seektalent/runtime/orchestrator.py`
- Modify: `tests/test_runtime_audit.py`

- [ ] **Step 1: Write a failing diagnostics-builder seam test**

In `tests/test_runtime_audit.py`, add one direct-module test for a higher-level builder:

```python
from seektalent.runtime.runtime_diagnostics import build_search_diagnostics as build_search_diagnostics_direct
```

```python
def test_runtime_diagnostics_builder_matches_legacy_search_diagnostics() -> None:
    runtime = WorkflowRuntime(make_settings())
    artifacts, run_state, final_result, terminal_controller_round = _build_audit_fixture(runtime)

    direct = build_search_diagnostics_direct(
        tracer=artifacts.tracer,
        run_state=run_state,
        final_result=final_result,
        terminal_controller_round=terminal_controller_round,
        collect_llm_schema_pressure=runtime._collect_llm_schema_pressure,
        build_round_search_diagnostics=runtime._build_round_search_diagnostics,
        reflection_advice_application_for_decision=runtime._reflection_advice_application_for_decision,
    )

    legacy = runtime._build_search_diagnostics(
        tracer=artifacts.tracer,
        run_state=run_state,
        final_result=final_result,
        terminal_controller_round=terminal_controller_round,
    )

    assert direct == legacy
```

- [ ] **Step 2: Run the direct builder test to verify it fails**

Run:

```bash
/Users/frankqdwang/Agents/SeekTalent-0.2.4/.venv/bin/pytest tests/test_runtime_audit.py::test_runtime_diagnostics_builder_matches_legacy_search_diagnostics -q
```

Expected: FAIL because `build_search_diagnostics` does not yet exist in `runtime_diagnostics.py`.

- [ ] **Step 3: Move the structured builders**

In `src/seektalent/runtime/runtime_diagnostics.py`, move and expose:

- `build_judge_packet(...)`
- `build_search_diagnostics(...)`
- `build_term_surface_audit(...)`
- `collect_llm_schema_pressure(...)`

Also move the helper stack they depend on:

- `_query_containing_term_stats`
- `_sent_query_key`
- `_positive_final_candidate_ids`
- `_build_surface_audit_rows`
- `_candidate_surface_rule`
- `_reflection_advice_application`
- `_reflection_advice_application_for_decision`
- `_build_round_search_diagnostics`
- `_round_audit_labels`
- `_query_term_details`
- `_llm_schema_pressure_item`

The extracted functions should take explicit helper callables where that avoids passing the whole runtime, for example:

```python
def build_search_diagnostics(
    *,
    tracer,
    run_state: RunState,
    final_result: FinalResult,
    terminal_controller_round: TerminalControllerRound | None,
    collect_llm_schema_pressure: Callable[[Path], list[dict[str, object]]],
    build_round_search_diagnostics: Callable[..., dict[str, object]],
    reflection_advice_application_for_decision: Callable[..., dict[str, object]],
) -> dict[str, object]:
    ...
```

Then update `src/seektalent/runtime/orchestrator.py` to import and call these new functions instead of the local methods where possible, but do not touch the LLM call snapshot helpers yet.

- [ ] **Step 4: Run the targeted diagnostics tests**

Run:

```bash
/Users/frankqdwang/Agents/SeekTalent-0.2.4/.venv/bin/pytest tests/test_runtime_audit.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/seektalent/runtime/runtime_diagnostics.py src/seektalent/runtime/orchestrator.py tests/test_runtime_audit.py
git commit -m "refactor: move runtime audit builders"
```

## Task 3: Extract Markdown/Text Report Renderers

**Files:**
- Create: `src/seektalent/runtime/runtime_reports.py`
- Modify: `src/seektalent/runtime/orchestrator.py`
- Modify: `tests/test_runtime_state_flow.py`

- [ ] **Step 1: Write a failing renderer seam test**

In `tests/test_runtime_state_flow.py`, add a direct import and one focused renderer test:

```python
from seektalent.runtime.runtime_reports import render_round_review as render_round_review_direct
```

```python
def test_runtime_reports_round_review_matches_legacy_renderer() -> None:
    runtime = WorkflowRuntime(make_settings())
    payload = _round_review_fixture(runtime)

    direct = render_round_review_direct(**payload)
    legacy = runtime._render_round_review(**payload)

    assert direct == legacy
```

- [ ] **Step 2: Run the direct renderer test to verify it fails**

Run:

```bash
/Users/frankqdwang/Agents/SeekTalent-0.2.4/.venv/bin/pytest tests/test_runtime_state_flow.py::test_runtime_reports_round_review_matches_legacy_renderer -q
```

Expected: FAIL with `ModuleNotFoundError` for `seektalent.runtime.runtime_reports`.

- [ ] **Step 3: Create `runtime_reports.py` and move the renderers**

Create `src/seektalent/runtime/runtime_reports.py` and move, unchanged:

- `render_run_summary(...)`
- `render_run_finished_summary(...)`
- `render_round_review(...)`

These should remain plain functions that return strings. If the code needs helper inputs such as `preview_text`, pass them explicitly as callables instead of importing the whole runtime.

Example shape:

```python
def render_round_review(
    *,
    round_no: int,
    controller_decision,
    retrieval_plan,
    observation,
    newly_scored_count: int,
    pool_decisions,
    top_candidates,
    dropped_candidates,
    reflection,
    next_step: str,
) -> str:
    ...
```

Update `src/seektalent/runtime/orchestrator.py` to call the new renderers.

- [ ] **Step 4: Run the targeted renderer test**

Run:

```bash
/Users/frankqdwang/Agents/SeekTalent-0.2.4/.venv/bin/pytest tests/test_runtime_state_flow.py::test_runtime_reports_round_review_matches_legacy_renderer -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/seektalent/runtime/runtime_reports.py src/seektalent/runtime/orchestrator.py tests/test_runtime_state_flow.py
git commit -m "refactor: extract runtime report renderers"
```

## Task 4: Focused Regression And Import Sweep

**Files:**
- Modify: only if a stale import or helper reference remains
- Test: `tests/test_runtime_audit.py`
- Test: `tests/test_runtime_state_flow.py`
- Test: `tests/test_llm_input_prompts.py`

- [ ] **Step 1: Run the focused regression suite**

Run:

```bash
/Users/frankqdwang/Agents/SeekTalent-0.2.4/.venv/bin/pytest tests/test_runtime_audit.py tests/test_runtime_state_flow.py tests/test_llm_input_prompts.py -q
```

Expected: PASS.

- [ ] **Step 2: If any failure appears, fix only import drift or helper-path wiring**

Allowed changes:

- import path updates
- helper wiring between `orchestrator.py`, `runtime_diagnostics.py`, and `runtime_reports.py`
- direct calls to the moved builders and renderers

Not allowed:

- artifact schema changes
- markdown wording changes
- LLM call snapshot refactors
- flywheel field additions
- runtime behavioral changes unrelated to the split

- [ ] **Step 3: Re-run the focused regression suite**

Run:

```bash
/Users/frankqdwang/Agents/SeekTalent-0.2.4/.venv/bin/pytest tests/test_runtime_audit.py tests/test_runtime_state_flow.py tests/test_llm_input_prompts.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/seektalent/runtime/runtime_diagnostics.py src/seektalent/runtime/runtime_reports.py src/seektalent/runtime/orchestrator.py tests/test_runtime_audit.py tests/test_runtime_state_flow.py tests/test_llm_input_prompts.py
git commit -m "test: verify runtime audit reporting split"
```

## Self-Review

### Spec coverage

- Extract diagnostics/audit builders: covered by Tasks 1-2.
- Extract markdown/text renderers: covered by Task 3.
- Keep artifact schemas and wording unchanged: enforced by Task 4 constraints and direct-vs-legacy seam tests.
- Leave LLM call snapshot wiring in `WorkflowRuntime`: preserved by Tasks 2-4 non-goals.

### Placeholder scan

- No `TODO`, `TBD`, or deferred placeholders remain.
- Each code-changing step includes explicit files, code direction, commands, and expected outcomes.

### Type consistency

- The plan consistently uses `runtime_diagnostics.py` for structured artifact builders and `runtime_reports.py` for text renderers.
- It consistently keeps `orchestrator.py` as the caller/writer, not the builder host.
- It consistently excludes `_build_llm_call_snapshot` and `_write_aux_llm_call_artifact` from this refactor.
