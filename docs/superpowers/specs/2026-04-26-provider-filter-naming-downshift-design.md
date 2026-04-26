# Provider Filter Naming Downshift Design

## Goal

Rename the most visible CTS-specific filter field names in shared runtime-facing models and contexts so they become provider-neutral, without changing behavior, action names, or top-level architecture.

This is a narrow cleanup step:

- rename `cts_native_filters` to `provider_filters`
- rename `projected_cts_filters` to `projected_provider_filters`
- update downstream context, reflection, audit, and tests to match
- do not change `search_cts`
- do not remove `CTSQuery`
- do not change provider contract shape or paging behavior

## Current State

The last few refactors moved a large amount of CTS-specific behavior into `providers/cts`, including query assembly. That improved ownership, but the shared model and context layer still exposes CTS-specific filter names in places that are no longer truly CTS-only.

The most visible remaining examples are:

- `ConstraintProjectionResult.cts_native_filters`
- `RoundRetrievalPlan.projected_cts_filters`

These names now leak into:

- retrieval plan construction
- runtime execution
- reflection context
- audit output
- multiple tests

That is a naming and semantic boundary problem more than a behavior problem.

## Problem

These field names make shared runtime structures look more CTS-specific than they actually are.

After the CTS query-assembly downshift:

- runtime no longer directly assembles CTS query shape
- provider-local code owns more of the CTS-specific request shape
- but shared objects still say “CTS filters” instead of “provider filters”

This has two concrete costs:

1. it keeps provider-specific terminology alive in generic planning/runtime paths
2. it makes future non-CTS provider work look more invasive than it needs to be

## Recommended Approach

Do a narrow provider-neutral naming pass on the filter-projection path only.

Use these names:

- `ConstraintProjectionResult.provider_filters`
- `RoundRetrievalPlan.projected_provider_filters`

Also update related context and artifact wording so shared layers describe these values as provider filters or projected filters, not CTS filters.

This is preferred over:

- a superficial rename with no context changes
- a broader rename that also changes action names like `search_cts`
- a larger rewrite that tries to eliminate `CTSQuery` at the same time

## Target Scope

### Change

- shared model field names for projected provider filters
- construction sites
- consumption sites
- reflection/context wording that reads those fields
- test assertions and serialized artifact expectations affected by the rename

### Do not change

- `search_cts`
- `CTSQuery`
- provider contract `SearchRequest.provider_filters`
- cursor or paging behavior
- `_context_builder` structure
- top-level directory layout

## File Scope

Primary production files:

- `src/seektalent/models.py`
- `src/seektalent/providers/cts/filter_projection.py`
- `src/seektalent/retrieval/query_plan.py`
- `src/seektalent/runtime/orchestrator.py`
- `src/seektalent/runtime/retrieval_runtime.py`
- `src/seektalent/reflection/critic.py`

Likely test updates:

- `tests/test_runtime_audit.py`
- `tests/test_runtime_state_flow.py`
- `tests/test_query_plan.py`
- `tests/test_v02_models.py`
- `tests/test_context_builder.py`
- `tests/test_controller_contract.py`
- `tests/test_llm_input_prompts.py`
- any other test asserting the old field names in serialized output

## Rename Map

### Models

- `ConstraintProjectionResult.cts_native_filters`
  -> `provider_filters`

- `RoundRetrievalPlan.projected_cts_filters`
  -> `projected_provider_filters`

### Construction and usage

Every direct reference to those model fields should move to the new names.

Examples include:

- `projection_result.cts_native_filters`
  -> `projection_result.provider_filters`

- `retrieval_plan.projected_cts_filters`
  -> `retrieval_plan.projected_provider_filters`

### Wording

Shared-layer wording should also move away from CTS-specific phrasing where it is describing these renamed fields.

Examples:

- “CTS filters” in shared context or reflection copy
  -> “provider filters” or “projected filters”

This is especially important in reflection and audit-facing text where the field name is part of the operator-facing semantics.

## Migration Strategy

Apply the rename in this order:

1. models
2. constructors
3. consumers
4. tests and serialized artifact assertions

This order keeps failures legible. The primary risk in this step is not algorithmic behavior; it is incomplete propagation of the renamed fields through serialization, context rendering, and tests.

## Compatibility Policy

Do not keep both old and new field names alive.

This repo is internal and test-controlled, so adding a compatibility layer would only keep old CTS-specific semantics alive longer and make later cleanup messier.

Use one clean cut:

- rename once
- fix all call sites
- fix all tests

## Data Flow After This Step

After the rename:

- provider-local code still owns CTS-specific mapping behavior
- shared planning/runtime structures talk about provider filters instead of CTS filters
- CTS-specific request models and action names remain in place where they are still genuinely CTS-shaped

This is intentionally a partial cleanup, not a full provider-neutral rewrite.

## Known Deliberate Residue

This step intentionally leaves these CTS-specific concepts in place:

- `CTSQuery`
- `search_cts`
- CTS-specific provider slice files under `providers/cts`
- CTS-shaped artifact names such as `cts_queries.json`

These remain because changing them now would widen the scope too much relative to the value of this step.

## Testing Strategy

Primary goal: prove this is a semantics-preserving rename.

Focus on:

- model serialization tests
- retrieval plan tests
- reflection/context rendering tests
- runtime audit tests
- prompt/input tests that assert serialized field names

The key regression risk is stale assertions against old keys, not broken business logic.

## Non-Goals

This design does **not**:

- rename `search_cts`
- remove `CTSQuery`
- redesign the retrieval provider contract
- generalize paging
- split `_context_builder`
- change top-level package structure

## Success Criteria

This step is successful if:

- shared models no longer expose `cts_native_filters`
- shared plans no longer expose `projected_cts_filters`
- reflection/audit/context wording no longer treats these renamed values as inherently CTS-specific
- focused tests and serialized artifact assertions are green
- behavior is otherwise unchanged

## Likely Next Step

After this rename, the next structural choice is likely either:

- continue removing CTS-specific residue from shared layers in small steps
- or switch focus to `_context_builder` thinning

That decision should happen after this naming pass lands and the remaining residue is easier to see clearly.
