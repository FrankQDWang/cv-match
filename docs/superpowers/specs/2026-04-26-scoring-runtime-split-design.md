# Scoring Runtime Split Design

## Goal

Split scoring-stage execution out of `WorkflowRuntime` so the orchestrator owns less stage-specific logic while preserving current scoring behavior, artifacts, and result shapes.

This is a narrow structural refactor:

- move `_score_round(...)`
- move its direct scoring-stage helpers
- keep round-loop behavior unchanged
- keep scoring artifacts unchanged
- keep scoring models and scorer interface unchanged

## Why This Next

After the recent refactors, `WorkflowRuntime` is thinner but still owns several thick stage bodies.

The best next target is `_score_round(...)` because it is:

- a single, bounded stage
- mostly deterministic stage execution logic
- already protected by existing runtime/state-flow/audit tests
- much lower-risk than touching `_run_rounds(...)` directly

Compared with rescue logic or company discovery, the scoring path has a cleaner start/end boundary and fewer cross-stage concerns.

## Current State

`src/seektalent/runtime/orchestrator.py` currently owns:

- `_score_round(...)`
- `_build_scoring_pool(...)`
- `_normalize_scoring_pool(...)`
- `_build_pool_decisions(...)`
- `_scoring_input_ref(...)`

Inside `_score_round(...)`, `WorkflowRuntime` currently handles:

- selecting new resumes that still need scoring
- normalization and writing normalized resume artifacts
- writing `scoring_input_refs.jsonl`
- building scoring contexts
- calling `resume_scorer.score_candidates_parallel(...)`
- updating `run_state.scorecards_by_resume_id`
- deriving current top pool
- deriving pool decisions and dropped candidates
- writing `scorecards.jsonl`
- writing `top_pool_snapshot.json`

## Problem

This logic is not orchestration shell logic. It is a self-contained scoring execution stage that still lives inside the same class as:

- requirements bootstrap
- controller loop orchestration
- rescue lanes
- provider/retrieval coordination
- progress/event shell helpers

As a result, `WorkflowRuntime` remains more concentrated than it needs to be.

## Recommended Approach

Create a new module:

- `src/seektalent/runtime/scoring_runtime.py`

Use plain module-level functions, centered on:

- `score_round(...)`

Do not introduce a `ScoringRuntime` class. This stage does not need long-lived mutable state.

## Module Boundary

### New module: `scoring_runtime.py`

Own:

- `score_round(...)`
- `build_scoring_pool(...)`
- `normalize_scoring_pool(...)`
- `build_pool_decisions(...)`
- `scoring_input_ref(...)`

These functions are tightly coupled to scoring-stage execution and artifacts, so they should move together.

### Keep in `WorkflowRuntime`

Keep these in `orchestrator.py`:

- `_format_scoring_failure_message(...)`
- `_materialize_candidates(...)`
- round-loop decisions about when scoring runs
- post-scoring flow into reflection/finalizer/progress payloads

These either belong to orchestrator shell flow or are broader than the scoring stage itself.

## Function Boundary

Preferred shape:

```python
async def score_round(
    *,
    round_no: int,
    new_candidates: list[ResumeCandidate],
    run_state: RunState,
    tracer: RunTracer,
    runtime_only_constraints: list[RuntimeConstraint],
    resume_scorer,
    build_scoring_context,
    format_scoring_failure_message,
    slim_top_pool_snapshot,
) -> tuple[list[ScoredCandidate], list[PoolDecision], list[ScoredCandidate]]:
    ...
```

Helper functions should live in the same module and be called directly.

Key rules:

- do not pass the whole `WorkflowRuntime`
- keep the current tuple result shape
- preserve scoring artifact names and payload shapes

## What This Step Does Not Do

This step does not:

- change `resume_scorer.score_candidates_parallel(...)`
- change scoring prompts or scoring context schema
- change `ScoredCandidate`, `ScoringFailure`, or `PoolDecision`
- change `scorecards.jsonl` or `top_pool_snapshot.json`
- change round-completed scoring payload semantics
- move resume quality comment handling
- change reflection or finalizer behavior
- touch `_run_rounds(...)`
- introduce a generic stage framework

## Testing Strategy

Do not add `direct == wrapper` seam tests.

Primary protection should come from existing tests:

- [tests/test_runtime_state_flow.py](/Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_state_flow.py)
  Directly exercises `_score_round(...)` behavior.
- [tests/test_runtime_audit.py](/Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_audit.py)
  Locks `scorecards.jsonl`, `top_pool_snapshot.json`, and related downstream artifacts.

If an extra test is needed, prefer:

- a boundary test that `WorkflowRuntime` delegates to the new scoring host
- or a direct-output test that checks observable scoring artifacts/results

Avoid wrapper-parity tests.

## Success Criteria

This step is successful if:

- `WorkflowRuntime` no longer owns the scoring execution stage body
- `scoring_runtime.py` becomes the single host for scoring-stage execution helpers
- tuple results, scoring artifacts, and behavior remain unchanged
- existing runtime/state-flow/audit coverage remains green
