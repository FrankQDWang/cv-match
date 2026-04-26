# Company Discovery Runtime Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the company-discovery rescue-lane execution out of `WorkflowRuntime` without changing rescue behavior, company discovery artifacts, forced decision semantics, or anchor-only fallback behavior.

**Architecture:** Extract plain runtime functions into `company_discovery_runtime.py` for the company-discovery lane only. Keep `WorkflowRuntime` as the rescue coordinator and retain generic rescue selection and shared runtime plumbing in `orchestrator.py`.

**Tech Stack:** Python 3.12, Pydantic models, pytest, existing runtime state-flow and audit tests

---

## File Map

- Create: `src/seektalent/runtime/company_discovery_runtime.py`
  Purpose: own company-discovery lane execution and its direct helper functions.

- Modify: `src/seektalent/runtime/orchestrator.py`
  Purpose: delegate company-discovery lane execution to the new runtime module.

- Modify only if a minimal boundary test is needed:
  - `tests/test_runtime_state_flow.py`

Primary validation should rely on existing runtime/state-flow/audit coverage rather than wrapper-parity tests.

## Task 1: Extract Company Discovery Lane Execution

**Files:**
- Create: `src/seektalent/runtime/company_discovery_runtime.py`
- Modify: `src/seektalent/runtime/orchestrator.py`

- [ ] **Step 1: Read the current lane implementation structurally**

Use the current implementation in `src/seektalent/runtime/orchestrator.py` as the source of truth. This is a behavior-preserving move.

Move together:

- `_continue_after_empty_feedback(...)`
- `_company_discovery_skip_reason(...)`
- `_select_anchor_only_after_failed_company_discovery(...)`
- `_force_company_discovery_decision(...)`

Do not change:

- company discovery artifact names
- company discovery artifact payload shapes
- `SearchControllerDecision` semantics
- `RescueDecision` semantics
- anchor-only fallback behavior

- [ ] **Step 2: Create `company_discovery_runtime.py` with plain function entrypoints**

Create:

- `src/seektalent/runtime/company_discovery_runtime.py`

Add a plain async function shaped roughly like:

```python
async def continue_after_empty_feedback(
    *,
    settings: AppSettings,
    company_discovery: CompanyDiscoveryService,
    run_state: RunState,
    controller_context: ControllerContext,
    round_no: int,
    tracer: RunTracer,
    rescue_decision: RescueDecision,
    progress_callback: ProgressCallback | None,
    emit_progress,
    write_aux_llm_call_artifact,
    company_discovery_useful,
    force_anchor_only_decision,
) -> tuple[RescueDecision, SearchControllerDecision]:
    ...
```

Keep these helpers in the same module:

- `company_discovery_skip_reason(...)`
- `select_anchor_only_after_failed_company_discovery(...)`
- `force_company_discovery_decision(...)`

Keep this module free of classes.

- [ ] **Step 3: Update `WorkflowRuntime` to a thin lane delegate**

In `src/seektalent/runtime/orchestrator.py`, replace the current company-discovery lane bodies with thin calls into `company_discovery_runtime`.

Keep these in `WorkflowRuntime`:

- `_choose_rescue_decision(...)`
- `_company_discovery_useful(...)`
- `_force_anchor_only_decision(...)`
- `_emit_progress(...)`
- `_write_aux_llm_call_artifact(...)`

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
- company discovery lane side effects
- anchor-only fallback behavior

- [ ] **Step 5: Add one minimal boundary test only if existing coverage is insufficient**

Only if needed, add a small test that checks host-boundary behavior, for example:

- `WorkflowRuntime` delegates this lane to the new company-discovery runtime host

Do not add:

- `direct == wrapper` parity tests

- [ ] **Step 6: Commit**

```bash
git add src/seektalent/runtime/company_discovery_runtime.py src/seektalent/runtime/orchestrator.py tests/test_runtime_state_flow.py tests/test_runtime_audit.py
git commit -m "refactor: extract company discovery runtime"
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

Do not expand scope into rescue routing, candidate feedback, or `_run_rounds(...)`.

- [ ] **Step 3: Re-run the same regression command**

Run the same command again and confirm it passes before claiming completion.

- [ ] **Step 4: Commit follow-up only if needed**

If Task 2 required code changes:

```bash
git add src/seektalent/runtime/orchestrator.py src/seektalent/runtime/company_discovery_runtime.py tests/test_runtime_state_flow.py tests/test_runtime_audit.py tests/test_api.py tests/test_cli.py
git commit -m "test: fix company discovery runtime follow-ups"
```

If no changes were needed, do not create an extra commit.

## Notes For Reviewers

Reviewers should check:

- the company-discovery lane body is no longer hosted in `WorkflowRuntime`
- `company_discovery_runtime.py` owns the lane execution helpers
- company discovery artifact schemas remain unchanged
- anchor-only fallback semantics remain unchanged
- no wrapper-parity seam test was introduced

## Done Criteria

This plan is complete when:

- `company_discovery_runtime.py` exists
- `WorkflowRuntime` delegates this lane to the new module
- runtime state-flow/audit/API/CLI focused regression passes
- company discovery rescue behavior and artifacts remain unchanged
