# Company Discovery Runtime Split Design

## Goal

Split the company-discovery rescue-lane execution out of `WorkflowRuntime` so the orchestrator owns less lane-specific logic while preserving current rescue behavior, artifacts, and decision shapes.

This is a narrow structural refactor:

- move the company-discovery rescue execution path
- keep rescue routing behavior unchanged
- keep company discovery artifacts unchanged
- keep `SearchControllerDecision` and `RescueDecision` semantics unchanged

## Why This Next

After extracting requirements bootstrap, scoring, retrieval execution, context building, and diagnostics/reporting, `WorkflowRuntime` is thinner but still owns one thick rescue-lane body.

The next best target is the company-discovery lane because it is:

- bounded to one rescue path
- already backed by an existing `CompanyDiscoveryService`
- easier to isolate than `_run_rounds(...)`
- less risky than restructuring the full rescue router

## Current State

`src/seektalent/runtime/orchestrator.py` currently owns:

- `_continue_after_empty_feedback(...)`
- `_company_discovery_skip_reason(...)`
- `_select_anchor_only_after_failed_company_discovery(...)`
- `_force_company_discovery_decision(...)`

That path currently does all of the following:

- decide whether company discovery can run after failed candidate feedback
- execute `company_discovery.discover_web(...)`
- write company discovery artifacts and auxiliary LLM call artifacts
- mutate `run_state.retrieval_state` for company-discovery state
- inject accepted company terms into the query-term pool
- choose forced company seed terms for the next search
- fall back to anchor-only rescue when company discovery cannot yield a usable query

## Problem

This is no longer orchestration shell logic. It is a self-contained rescue-lane execution path that still lives inside the same class as:

- controller loop orchestration
- round-state transitions
- scoring/finalization handoff
- generic progress/event plumbing

That keeps `WorkflowRuntime` more concentrated than necessary.

## Recommended Approach

Create a new module:

- `src/seektalent/runtime/company_discovery_runtime.py`

Use plain module-level functions, not a class.

The company-discovery service already owns the long-lived execution dependencies. The runtime split only needs explicit functions that consume current round state and collaborators.

## Module Boundary

### New module: `company_discovery_runtime.py`

Own:

- `continue_after_empty_feedback(...)`
- `company_discovery_skip_reason(...)`
- `select_anchor_only_after_failed_company_discovery(...)`
- `force_company_discovery_decision(...)`

These functions are one contiguous data flow and should move together.

### Keep in `WorkflowRuntime`

Keep these in `orchestrator.py`:

- `_choose_rescue_decision(...)`
- `_company_discovery_useful(...)`
- `_force_anchor_only_decision(...)`
- `_emit_progress(...)`
- `_write_aux_llm_call_artifact(...)`

These belong either to generic rescue selection or to shared runtime plumbing that other stages also use.

## Function Boundary

Preferred shape:

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

Internal helpers should remain in the same module and be called directly.

Key rules:

- do not pass the whole `WorkflowRuntime`
- keep current return shapes
- preserve current artifact names and payload schemas
- preserve `None` semantics from `force_company_discovery_decision(...)`

## What This Step Does Not Do

This step does not:

- restructure the full rescue router
- move candidate feedback lane logic
- change `CompanyDiscoveryService`
- change company discovery prompts, planning, extraction, or reduction
- change company discovery artifact schemas
- change `SearchControllerDecision` or `RescueDecision`
- change `search_cts` action naming
- touch `_run_rounds(...)`
- introduce a generic rescue framework

## Testing Strategy

Do not add `direct == wrapper` seam tests.

Primary protection should come from existing tests that already cover rescue behavior and runtime artifacts.

If an extra test is needed, prefer:

- a boundary test that `WorkflowRuntime` delegates this lane to the new module
- or a direct-output test that checks observable rescue results and artifact writes

Avoid tautological wrapper-parity tests.

## Success Criteria

This step is successful if:

- `WorkflowRuntime` no longer owns the company-discovery rescue execution body
- `company_discovery_runtime.py` becomes the single host for this lane's execution helpers
- rescue behavior, artifacts, and fallback semantics remain unchanged
- existing runtime/state-flow/audit coverage remains green
