# Runtime Audit Reporting Split Design

## Goal

Split the non-orchestration audit and reporting logic out of `WorkflowRuntime` so the runtime class is less concentrated and future flywheel-oriented artifact work has clearer homes.

This is a narrow structural cleanup step:

- extract diagnostics and audit builders
- extract human-readable review and summary renderers
- keep artifact schemas unchanged
- keep report wording unchanged
- leave LLM call snapshot wiring in `WorkflowRuntime`

## Why This Next

The recent refactors already moved retrieval execution and context assembly out of their original concentration points. The largest remaining non-core concentration inside `WorkflowRuntime` is now the reporting layer:

- context serialization for prompt artifacts
- judge packet assembly
- search diagnostics assembly
- term surface audit assembly
- run summary rendering
- round review rendering

This is high-value cleanup because the same area is also the natural landing zone for later flywheel asset work. If this logic stays inside `WorkflowRuntime`, every new query/term audit field will continue to expand the orchestrator class.

## Current State

`src/seektalent/runtime/orchestrator.py` still owns all of the following:

- `_slim_controller_context`
- `_slim_reflection_context`
- `_slim_finalize_context`
- `_slim_search_attempt`
- `_slim_scored_candidate`
- `_slim_top_pool_snapshot`
- `_build_judge_packet`
- `_build_search_diagnostics`
- `_build_term_surface_audit`
- `_collect_llm_schema_pressure`
- `_render_run_summary`
- `_render_run_finished_summary`
- `_render_round_review`

These functions read runtime state and produce artifacts, but they do not control round execution.

## Problem

The problem is not just file length. It is that `WorkflowRuntime` still owns too many responsibilities:

- orchestration
- stage calling
- rescue control
- artifact emission
- diagnostics shaping
- markdown report rendering

The diagnostics and reporting layer is especially awkward because:

- it is large
- it is mostly deterministic transformation logic
- it is exactly where future query/term audit work will land

That means future flywheel-supporting changes would keep growing the wrong host file unless this layer moves first.

## Recommended Approach

Split the reporting layer into two modules:

- `src/seektalent/runtime/runtime_diagnostics.py`
- `src/seektalent/runtime/runtime_reports.py`

Use plain module-level functions with explicit parameters. Do not create a reporting service object or pass the entire `WorkflowRuntime` into the new modules.

This is preferred over:

- leaving the logic in `orchestrator.py`
- extracting one giant `reporting.py`
- introducing service or manager classes for stateless logic

## Module Boundaries

### `runtime_diagnostics.py`

Own structured artifact shaping and diagnostic payload construction:

- `_slim_controller_context`
- `_slim_reflection_context`
- `_slim_finalize_context`
- `_slim_search_attempt`
- `_slim_scored_candidate`
- `_slim_top_pool_snapshot`
- `_build_judge_packet`
- `_build_search_diagnostics`
- `_build_term_surface_audit`
- `_collect_llm_schema_pressure`

Also own the small helper functions that only exist to support those outputs, such as:

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

The exact final split can stay pragmatic, but this module should own structured audit products rather than runtime control.

### `runtime_reports.py`

Own human-readable text rendering:

- `_render_run_summary`
- `_render_run_finished_summary`
- `_render_round_review`

This module should produce markdown/text only, not write files or emit tracer events.

## Input Boundary

The new modules should expose plain functions with explicit parameters.

Preferred style:

- `build_search_diagnostics(*, tracer, run_state, final_result, terminal_controller_round) -> dict[str, object]`
- `build_term_surface_audit(*, tracer, run_state, final_result, evaluation_result) -> dict[str, object]`
- `render_round_review(*, round_no, controller_decision, retrieval_plan, observation, ...) -> str`

Avoid:

- service classes that hold `self.settings` and `self.prompts`
- passing the whole `WorkflowRuntime`
- fake object wrappers around the current orchestrator state

The goal is real decoupling, not host-file relocation with hidden whole-runtime dependency.

## What Stays In `WorkflowRuntime`

This step intentionally leaves these in `orchestrator.py`:

- `_build_llm_call_snapshot`
- `_write_aux_llm_call_artifact`
- `_emit_llm_event`
- `_emit_progress`
- round loop and stage orchestration
- rescue logic
- scoring/retrieval/finalizer/reflection stage calls

That keeps this refactor narrower and avoids mixing reporting extraction with LLM call wiring.

## File Scope

Primary production files:

- `src/seektalent/runtime/orchestrator.py`
- `src/seektalent/runtime/runtime_diagnostics.py`
- `src/seektalent/runtime/runtime_reports.py`

Likely test files:

- `tests/test_runtime_audit.py`
- `tests/test_runtime_state_flow.py`
- `tests/test_llm_input_prompts.py`

If an import or helper path shifts, a small number of additional runtime tests may need updates, but the intended behavior should stay unchanged.

## Migration Strategy

Apply the split in this order:

1. extract structured diagnostics helpers and builders into `runtime_diagnostics.py`
2. update `orchestrator.py` to call the new diagnostics functions
3. extract report renderers into `runtime_reports.py`
4. update `orchestrator.py` to call the new renderers
5. run focused regression over runtime audit and state-flow tests

This order keeps failures local and prevents mixing the markdown rendering move with the structured diagnostics move too early.

## Non-Goals

This step does not:

- change `search_diagnostics.json` schema
- change `term_surface_audit.json` schema
- change `judge_packet.json` schema
- change `run_summary.md` or `round_review.md` wording intentionally
- move `RunTracer`
- change evaluation behavior
- change rescue logic
- add flywheel-specific fields such as `query_id`, `query_outcomes`, or `term_outcomes`
- change prompt payload semantics
- change retrieval, scoring, reflection, or finalization behavior

## Compatibility Policy

This should be a semantics-preserving move.

Acceptable:

- helper renaming inside the new modules
- small import updates in runtime and tests

Not acceptable:

- silent schema drift
- markdown output churn caused by accidental string changes
- mixing new flywheel data requirements into this refactor

## Testing Strategy

Primary goal: prove the split changes structure, not behavior.

Focus on:

- `tests/test_runtime_audit.py`
- `tests/test_runtime_state_flow.py`
- `tests/test_llm_input_prompts.py`

These tests already cover the most important effects of the extracted logic:

- structured runtime artifacts
- report payloads
- prompt-related context artifacts
- end-to-end runtime wiring

## Success Criteria

This step is successful if:

- `WorkflowRuntime` no longer owns the main diagnostics/reporting construction layer
- structured diagnostics live in `runtime_diagnostics.py`
- markdown/text renderers live in `runtime_reports.py`
- artifact schemas remain unchanged
- report wording remains effectively unchanged
- focused runtime regression stays green

## Likely Next Step

After this lands, the next structural choice should likely be:

- continue thinning `WorkflowRuntime` around rescue/force-decision logic
- or begin phase-zero flywheel asset work on top of the cleaner diagnostics boundary

That decision will be easier once reporting no longer lives inside the main orchestrator file.
