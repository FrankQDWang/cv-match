# Context Builder Split Design

## Goal

Split the current runtime context-building concentration into consumer-specific modules so future runtime work does not keep accumulating in a single file.

This is a narrow structural cleanup step:

- split `context_builder.py` by consumer
- keep context schemas unchanged
- keep prompt semantics unchanged
- keep runtime behavior unchanged
- avoid introducing new framework-shaped abstractions

## Why This Next

The repo now has cleaner retrieval and provider boundaries than before, but context assembly is still concentrated in one runtime file:

- [src/seektalent/runtime/context_builder.py](/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/context_builder.py)

That file currently mixes:

- controller-specific policy and stop guidance
- reflection context assembly
- finalize context assembly
- scoring context assembly
- shared projection helpers for top-pool and observation views

This is not yet a correctness problem, but it is an obvious growth point. If left in place, later work on flywheel assets, multi-provider support, and runtime thinning will keep expanding the same boundary again.

## Current State

`context_builder.py` currently exports:

- `build_controller_context`
- `build_scoring_context`
- `build_reflection_context`
- `build_finalize_context`

It also contains:

- controller-specific rules such as `_build_stop_guidance`
- helper functions for tried/untried families and broadening detection
- shared view projections such as `top_candidates`, `dropped_candidates`, `_search_observation_view`, `_reflection_summary`

The public API is simple, but the file is acting as a mixed ownership bucket rather than a clear runtime boundary.

## Problem

The main issue is not file length alone. It is ownership concentration.

Right now one file owns:

- controller policy
- reflection assembly
- finalize assembly
- scoring assembly
- shared views

That makes future edits cheaper in the short term but harder to review and reason about. It also weakens the next round of `WorkflowRuntime` thinning, because runtime-adjacent logic still has no consumer-specific homes.

## Recommended Approach

Split context-building by consumer, with one very small shared views module.

Recommended modules:

- `src/seektalent/runtime/controller_context.py`
- `src/seektalent/runtime/reflection_context.py`
- `src/seektalent/runtime/finalize_context.py`
- `src/seektalent/runtime/scoring_context.py`
- `src/seektalent/runtime/context_views.py`

This is preferred over:

- keeping one large `context_builder.py`
- introducing a `BaseContextBuilder`, `ContextFactory`, or similar abstraction
- mixing prompt rendering into this refactor

## Module Boundaries

### `controller_context.py`

Own:

- `build_controller_context`
- `_build_stop_guidance`
- `_budget_reminder`
- `_tried_families`
- `_untried_admitted_families`
- `_broadening_attempted`
- `_term_key`
- controller-only constants such as `BUDGET_STOP_RATIO`

Do not move unrelated shared view code here.

### `reflection_context.py`

Own:

- `build_reflection_context`

It may consume shared helpers from `context_views.py`, but it should not own controller policy.

### `finalize_context.py`

Own:

- `build_finalize_context`

### `scoring_context.py`

Own:

- `build_scoring_context`

This stays intentionally tiny. It does not need to be merged into a larger shared module.

### `context_views.py`

Own only shared projections and thin derived views:

- `top_candidates`
- `dropped_candidates`
- `_top_pool_entry`
- `_search_observation_view`
- `_reflection_summary`

This module should stay lightweight and should not become a second policy bucket.

## Sharing Rules

The guiding rule is:

- share view projections
- do not share control policy unless it is already used in multiple places

That means:

- stop guidance logic remains controller-local
- top-pool and observation view shaping may be shared
- scoring context remains separate rather than forced into a generic abstraction

## Migration Strategy

Apply the split in this order:

1. create the new modules and move logic into them
2. temporarily keep `context_builder.py` as a thin re-export layer
3. update `orchestrator.py` and tests to import from the new modules
4. decide whether to keep or delete the thin facade after the branch is stable

The key constraint is that `context_builder.py` must not remain a real logic host after this change. A short transitional re-export layer is acceptable; a second mixed implementation layer is not.

## File Scope

Primary production files:

- `src/seektalent/runtime/context_builder.py`
- `src/seektalent/runtime/controller_context.py`
- `src/seektalent/runtime/reflection_context.py`
- `src/seektalent/runtime/finalize_context.py`
- `src/seektalent/runtime/scoring_context.py`
- `src/seektalent/runtime/context_views.py`
- `src/seektalent/runtime/orchestrator.py`

Primary tests:

- `tests/test_context_builder.py`

Likely touch points if they import the old module directly:

- prompt/input tests
- runtime tests

The intention is minimal behavior churn, so most test changes should be import-path adjustments rather than changed assertions.

## Non-Goals

This step does not:

- change `ControllerContext`, `ReflectionContext`, `FinalizeContext`, or `ScoringContext` schemas
- change prompt wording or prompt payload semantics
- change stop-guidance thresholds or policy
- change `WorkflowRuntime` round behavior
- split `ReflectionCritic`, `Finalizer`, or `ReActController`
- touch provider contracts, paging, or flywheel data collection
- introduce a context-building framework

## Compatibility Policy

Short-term compatibility is allowed only as a thin import facade.

Acceptable:

- `context_builder.py` re-exporting the new `build_*_context` functions during the migration

Not acceptable:

- duplicating logic in both old and new modules
- leaving shared policy split ambiguously across both places

## Testing Strategy

Primary goal: prove this is a semantics-preserving relocation.

Focus on:

- `tests/test_context_builder.py`
- any direct import users of the old module
- focused runtime tests that exercise controller, reflection, scoring, and finalize context assembly

This refactor should fail, if it fails at all, because of import drift or misplaced helper ownership, not because runtime behavior changed.

## Success Criteria

This step is successful if:

- `context_builder.py` no longer acts as the main implementation bucket
- controller, reflection, finalize, and scoring context builders each have clear homes
- shared view logic is isolated in one small support module
- runtime behavior and prompt inputs remain unchanged
- focused tests pass with minimal assertion churn

## Likely Next Step

After this split lands, the next structural choice should be one of:

- further `WorkflowRuntime` thinning
- a small additional CTS residue cleanup
- phase-zero flywheel asset work such as stable query attribution

That decision will be easier once context assembly no longer shares one mixed host file.
