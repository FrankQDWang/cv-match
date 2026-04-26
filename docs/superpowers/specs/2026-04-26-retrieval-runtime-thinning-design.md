# Retrieval Runtime Thinning Design

## Goal

Make `WorkflowRuntime` thinner by moving the retrieval execution hot path and location dispatch logic into a dedicated runtime module, while preserving current CTS behavior and focused regression coverage.

This design is intentionally phase-one:

- keep the current provider seam
- keep CTS/page-number paging behavior
- keep existing round semantics, artifacts, and audit outputs
- do not expand into cursor-generalization, scoring/reflection refactors, or tracing redesign

## Problem

`WorkflowRuntime` still directly owns the thickest retrieval execution path even after the provider seam landed. The main concentration is the chain around:

- round retrieval execution
- dual-query coordination
- city dispatch
- paginated provider calls
- search attempt aggregation
- search observation construction

That makes the runtime harder to change locally. The provider seam is now in place, so this is the natural next extraction point.

## Recommended Approach

Use a thin execution module with a small dataclass host:

- create `src/seektalent/runtime/retrieval_runtime.py`
- add a small `RetrievalRuntime` dataclass that owns only real retrieval execution dependencies
- move search execution and location dispatch into that module
- keep `WorkflowRuntime` responsible for round-level orchestration only

This is preferred over:

- pure module-function extraction, which would leave very long parameter lists and weaker ownership
- a large sub-orchestrator, which would recreate the same boundary problem in a second class

## Target Boundary

### `WorkflowRuntime` keeps

- controller invocation
- filter projection and retrieval plan creation
- calling retrieval execution
- scoring
- reflection
- finalization
- evaluation
- rescue lanes
- top-level artifact flow

### `RetrievalRuntime` owns

- executing one round's retrieval plan
- dual-query execution coordination
- city-based dispatch
- provider search call routing through `RetrievalService`
- search attempt aggregation
- search observation construction
- local dedup within retrieval execution

## Module Shape

Create:

- `src/seektalent/runtime/retrieval_runtime.py`

Recommended shape:

```python
@dataclass
class RetrievalRuntime:
    settings: AppSettings
    retrieval_service: RetrievalService

    async def execute_round_search(...) -> RetrievalExecutionResult:
        ...
```

The class should stay thin:

- only hold `settings` and `retrieval_service`
- no global `RunState`
- no scoring/reflection/finalization dependencies
- no hidden dependency on the whole `WorkflowRuntime`

Small private helpers inside the module are expected where they improve readability, especially for:

- city dispatch
- single provider search attempt
- attempt/result aggregation

## Execution Interface

The retrieval module should take explicit inputs, not the whole runtime or run state.

### Inputs

- `round_no`
- `retrieval_plan`
- `query_states`
- `target_new`
- `seen_resume_ids`
- `seen_dedup_keys`
- `tracer`

If a helper needs additional local execution context, pass it explicitly.

### Output

Return one focused result object, not a large runtime state mutation. The result should preserve the current business shape:

- `cts_queries`
- `sent_query_records`
- `new_candidates`
- `search_observation`
- `search_attempts`

A small typed result dataclass is preferred over a raw tuple if it improves readability without adding ceremony.

## Internal Data Model Policy

For this step, keep `CTSQuery` as an internal retrieval-execution object.

Reason:

- it minimizes migration risk
- it preserves current CTS-shaped audit and query artifacts
- it avoids mixing this refactor with the later cursor-generalization/provider-normalization work

This means phase one still allows:

- retrieval execution to build `CTSQuery`
- provider seam mapping to happen at the search dispatch edge

This step does **not** attempt to eliminate `CTSQuery` from runtime-adjacent code.

## Data Flow

Target flow after refactor:

1. `WorkflowRuntime` builds `projection_result`
2. `WorkflowRuntime` builds `retrieval_plan`
3. `WorkflowRuntime` builds `query_states`
4. `WorkflowRuntime` calls `RetrievalRuntime.execute_round_search(...)`
5. `RetrievalRuntime` executes:
   - query split handling
   - city dispatch
   - paginated retrieval through `RetrievalService`
   - local dedup / attempt aggregation
6. `RetrievalRuntime` returns one structured execution result
7. `WorkflowRuntime` continues with scoring and later stages unchanged

## Migration Scope

Move the current logic around these responsibilities out of `WorkflowRuntime`:

- `_execute_location_search_plan`
- `_run_city_dispatch`
- `_execute_search_tool`
- `_search_once`
- tightly coupled helper logic used only by that path

Keep in `WorkflowRuntime`:

- plan creation
- progress events before/after retrieval
- exception normalization at the round boundary

## Error Handling

Preserve current fail-fast behavior.

- provider search exceptions should still surface as search-stage failures
- no new retry layers
- no fallback chains
- no speculative recovery logic

The extraction should not change semantics, only ownership.

## Testing Strategy

Primary regression targets:

- `tests/test_location_execution_plan.py`
- `tests/test_runtime_audit.py`
- `tests/test_runtime_state_flow.py`

Add focused tests for the new boundary only where they lock a real contract, for example:

- `WorkflowRuntime` constructs and uses `RetrievalRuntime`
- `RetrievalRuntime` returns the same search result shape expected by runtime

The existing retrieval/provider tests should continue to cover:

- provider registry
- CTS provider adapter
- retrieval service request shaping

## Non-Goals

This design explicitly does **not** do the following:

- cursor-generalization
- opaque cursor support
- changing the provider contract again unless implementation forces a tiny consistency fix
- moving scoring, reflection, or finalization out of `WorkflowRuntime`
- redesigning trace/event writing
- removing all CTS-shaped concepts from runtime-adjacent code
- introducing a generalized stage framework

## Success Criteria

This refactor is successful if:

- `WorkflowRuntime` loses the thick retrieval execution block
- retrieval execution and location dispatch have a dedicated host
- focused regression coverage remains green
- behavior stays unchanged for CTS
- the next cursor-generalization step has a cleaner landing zone

## Known Remaining Limitation

After this refactor, pagination can still remain CTS/page-number shaped.

That is acceptable for this step because:

- CTS is still the only real provider
- provider seam correctness already landed
- the current goal is structural thinning, not pagination generalization

The next likely follow-up after this refactor is to make runtime consume provider-owned `next_cursor` and `exhausted` semantics instead of locally driving page numbers.
