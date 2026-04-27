# Rescue Execution Runtime Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the remaining rescue execution logic out of `WorkflowRuntime` without changing rescue behavior, rescue artifacts, forced decision semantics, or query-term mutation semantics.

**Architecture:** Extract plain runtime functions into `rescue_execution_runtime.py` for candidate-feedback, reserve-broaden, and anchor-only rescue execution only. Keep `WorkflowRuntime` as the rescue coordinator and leave rescue routing plus shared runtime plumbing in `orchestrator.py`.

**Tech Stack:** Python 3.12, Pydantic models, pytest, existing runtime state-flow and audit tests

---

## File Map

- Create: `src/seektalent/runtime/rescue_execution_runtime.py`
  Purpose: own rescue execution helpers for candidate feedback, broaden, and anchor-only paths.

- Modify: `src/seektalent/runtime/orchestrator.py`
  Purpose: delegate rescue execution to the new runtime module.

- Modify only if a minimal boundary test is needed:
  - `tests/test_runtime_state_flow.py`

Primary validation should rely on existing rescue-oriented state-flow and audit coverage rather than wrapper-parity tests.

## Task 1: Extract Rescue Execution

**Files:**
- Create: `src/seektalent/runtime/rescue_execution_runtime.py`
- Modify: `src/seektalent/runtime/orchestrator.py`

- [ ] **Step 1: Read the current rescue execution implementation structurally**

Use the current implementation in `src/seektalent/runtime/orchestrator.py` as the source of truth. This is a behavior-preserving move.

Move together:

- `_force_candidate_feedback_decision(...)`
- `_force_anchor_only_decision(...)`
- `_force_broaden_decision(...)`
- `_active_admitted_anchor(...)`
- `_untried_admitted_non_anchor_reserve(...)`
- `_tried_query_families(...)`

Move `_query_term_key(...)` only if it becomes exclusive to this slice.

Do not change:

- rescue artifact names
- rescue artifact payload shapes
- `SearchControllerDecision` semantics
- rescue query-term mutation behavior
- broaden / anchor-only behavior

- [ ] **Step 2: Create `rescue_execution_runtime.py` with plain function entrypoints**

Create:

- `src/seektalent/runtime/rescue_execution_runtime.py`

Add plain functions shaped roughly like:

```python
def force_candidate_feedback_decision(
    *,
    run_state: RunState,
    round_no: int,
    reason: str,
    tracer: RunTracer,
    progress_callback: ProgressCallback | None,
    emit_progress,
) -> SearchControllerDecision | None:
    ...
```

```python
def force_anchor_only_decision(
    *,
    run_state: RunState,
    round_no: int,
    reason: str,
) -> SearchControllerDecision:
    ...
```

```python
def force_broaden_decision(
    *,
    run_state: RunState,
    round_no: int,
    reason: str,
) -> SearchControllerDecision:
    ...
```

Keep the direct helper functions in the same module.

Keep this module free of classes.

- [ ] **Step 3: Update `WorkflowRuntime` to thin rescue-execution delegates**

In `src/seektalent/runtime/orchestrator.py`, replace the current rescue execution bodies with thin calls into `rescue_execution_runtime`.

Keep these in `WorkflowRuntime`:

- `_choose_rescue_decision(...)`
- `_write_rescue_decision(...)`
- `_company_discovery_useful(...)`
- `_continue_after_empty_feedback(...)`
- round-loop dispatch on `rescue_decision.selected_lane`
- `_emit_progress(...)`

Do not broaden this into a rescue-router refactor.

- [ ] **Step 4: Run focused existing tests that already cover rescue behavior**

Run:

```bash
/Users/frankqdwang/Agents/SeekTalent-0.2.4/.venv/bin/pytest tests/test_runtime_state_flow.py tests/test_runtime_audit.py -q
```

Expected: PASS.

These files already cover:

- rescue-lane behavior
- round artifacts
- candidate-feedback path behavior
- anchor-only and broaden outcomes

- [ ] **Step 5: Add one minimal boundary test only if existing coverage is insufficient**

Only if needed, add a small test that checks host-boundary behavior, for example:

- `WorkflowRuntime` delegates rescue execution to the new runtime host

Do not add:

- `direct == wrapper` parity tests

- [ ] **Step 6: Commit**

```bash
git add src/seektalent/runtime/rescue_execution_runtime.py src/seektalent/runtime/orchestrator.py tests/test_runtime_state_flow.py tests/test_runtime_audit.py
git commit -m "refactor: extract rescue execution runtime"
```

## Task 2: Focused Regression And Drift Sweep

**Files:**
- Modify: only if a stale import or helper reference remains
- Test: `tests/test_runtime_state_flow.py`
- Test: `tests/test_runtime_audit.py`
- Test: `tests/test_api.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Run the planned focused regression set**

Run:

```bash
/Users/frankqdwang/Agents/SeekTalent-0.2.4/.venv/bin/pytest tests/test_runtime_state_flow.py tests/test_runtime_audit.py tests/test_api.py tests/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 2: Fix only stale import/helper drift if needed**

If a failure appears:

- inspect whether it is a stale import
- inspect whether a helper reference changed host modules
- fix the smallest thing necessary

Do not expand scope into rescue routing, company discovery, or `_run_rounds(...)`.

- [ ] **Step 3: Re-run the same regression command**

Run the same command again and confirm it passes before claiming completion.

- [ ] **Step 4: Commit follow-up only if needed**

If Task 2 required code changes:

```bash
git add src/seektalent/runtime/orchestrator.py src/seektalent/runtime/rescue_execution_runtime.py tests/test_runtime_state_flow.py tests/test_runtime_audit.py tests/test_api.py tests/test_cli.py
git commit -m "test: fix rescue execution runtime follow-ups"
```

If no changes were needed, do not create an extra commit.

## Notes For Reviewers

Reviewers should check:

- the remaining rescue execution bodies are no longer hosted in `WorkflowRuntime`
- `rescue_execution_runtime.py` owns the candidate-feedback / broaden / anchor-only execution helpers
- rescue artifact schemas remain unchanged
- no wrapper-parity seam test was introduced
- rescue routing remains in `rescue_router.py` and `WorkflowRuntime`

## Done Criteria

This plan is complete when:

- `rescue_execution_runtime.py` exists
- `WorkflowRuntime` delegates the remaining rescue execution to the new module
- runtime state-flow/audit/API/CLI focused regression passes
- rescue behavior, artifacts, and query-term mutations remain unchanged
