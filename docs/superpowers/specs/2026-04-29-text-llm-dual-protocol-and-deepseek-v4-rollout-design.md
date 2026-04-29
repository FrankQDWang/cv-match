# Text LLM Dual-Protocol Support And DeepSeek V4 Rollout Design

Date: 2026-04-29

## Context

The repository currently uses a text-LLM boundary that packs too much meaning into one string field:

- protocol shape
- provider adapter
- model name
- sometimes endpoint expectations

Examples in the current config include:

- `openai-chat:deepseek-v3.2`
- `openai-responses:gpt-5.4-mini`

That boundary was workable during earlier experimentation, but it is now causing three real productization problems:

1. protocol choice is implicit instead of explicit
2. model-routing decisions are harder to reason about and harder to audit
3. failures in benchmark and runtime traces do not cleanly tell us which protocol boundary failed

At the same time, the current benchmark/debug cycle exposed two additional operational issues that are separate from phrase-quality work:

- failed benchmark rows do not always carry `run_id`, `run_dir`, and `trace_log_path`
- timeout/provider failures are still too weakly classified for fast postmortem work

There is also a product-direction change in model selection:

- `requirements`, `controller`, `reflection`, and `judge` should move to `deepseek-v4-pro`
- `scoring`, `finalize`, and `structured_repair` should move to `deepseek-v4-flash`
- `judge` should no longer use a separate local URL / separate API key path
- `candidate_feedback` extraction quality is intentionally out of scope for this change

Finally, implementation must not start from the current mixed local state. The current repository still has an unmerged completed feature branch and dirty local benchmark-debug edits in the main worktree. This work should start only after those are integrated or discarded and a new clean worktree is created.

## Problem

The current text-LLM boundary is too implicit for the next stage of productization.

Specifically:

- the system does not treat `openai-compatible` and `anthropic-compatible` as first-class long-lived runtime choices
- model configuration still depends on old provider-prefixed model strings
- `judge` still has a separate endpoint/key surface that no longer matches the intended deployment model
- benchmark failure records remain incomplete for failed cases
- timeout/provider failures remain harder to classify than they should be

If we keep growing from the current boundary, we will accumulate more special-case parsing, more stage-specific exceptions, and more ambiguity in traces and run config.

## Goals

1. Make the repository a long-term dual-protocol text-LLM runtime that supports:
   - `openai_compatible`
   - `anthropic_compatible`

2. Make protocol choice explicit instead of encoded in provider-prefixed model strings.

3. Make stage model routing explicit and simple:
   - `requirements` -> `deepseek-v4-pro`
   - `controller` -> `deepseek-v4-pro`
   - `reflection` -> `deepseek-v4-pro`
   - `judge` -> `deepseek-v4-pro`
   - `scoring` -> `deepseek-v4-flash`
   - `finalize` -> `deepseek-v4-flash`
   - `structured_repair` -> `deepseek-v4-flash`

4. Move `judge` onto the same Bailian endpoint family and API key surface as the other text stages.

5. Improve runtime/benchmark observability so failures clearly identify:
   - stage
   - call id
   - protocol family
   - model id
   - provider failure kind

6. Ensure failed benchmark rows always carry enough linkage for postmortem:
   - `run_id`
   - `run_dir`
   - `trace_log_path`

7. Start implementation from a clean git baseline:
   - merge or dispose of the current completed feature branch first
   - clean its worktree and stale review/worktree leftovers
   - create a fresh dedicated worktree for this feature

## Non-Goals

- Do not change candidate-feedback phrase extraction behavior in this change.
- Do not promote PRF v1.5 mainline in this change.
- Do not redesign stopping / exhaustion behavior in this change.
- Do not change CTS/provider search protocol behavior in this change.
- Do not keep compatibility parsing for the old provider-prefixed model string format.
- Do not preserve separate `judge_openai_base_url` / `judge_openai_api_key` behavior.

## External Assumptions

This design assumes the following deployment facts:

- the team will continue using Bailian-hosted text models
- Bailian endpoint base URLs remain the active deployment target
- DeepSeek V4 models are available in the team's Bailian environment
- the team wants both `openai-compatible` and `anthropic-compatible` text interfaces to remain supported code paths

The public DeepSeek documentation explicitly states that `deepseek-v4-pro` and `deepseek-v4-flash` support both OpenAI ChatCompletions and Anthropic APIs. The public Bailian Anthropic compatibility documentation currently lags that exact DeepSeek V4 statement, so this design treats Bailian Anthropic support for DeepSeek V4 as an environment-backed deployment assumption rather than a public-doc guarantee.

## Approaches Considered

### Option A: Keep old model-string format and add more parsing

Examples:

- `openai-chat:deepseek-v4-pro`
- `anthropic:deepseek-v4-pro`
- `openai-responses:...`

Pros:

- smaller immediate diff
- fewer config file changes up front

Cons:

- keeps protocol/provider/model conflated in one field
- keeps the same cleanup debt that already exists
- encourages more compatibility parsing later
- directly conflicts with the requirement to stop preserving old config shapes

### Option B: Hard-cut to explicit protocol + explicit model fields

Pros:

- cleanest long-term boundary
- runtime/audit/trace semantics become explicit
- no old parsing debt remains
- matches the productization direction

Cons:

- larger one-time config migration
- requires stronger tests around settings and diagnostics

### Option C: Separate per-stage protocol selection from day one

Pros:

- maximally flexible
- could mix Anthropic and OpenAI-compatible stages in one run

Cons:

- more complexity than we need right now
- introduces many combinations with little current payoff
- makes runtime behavior harder to reason about

## Decision

Choose **Option B**, with one simplifying constraint:

- the codebase must support both protocol families long-term
- but each run uses one canonical text-LLM protocol family unless a future design explicitly introduces stage-level protocol overrides

This gives us long-term dual support without turning protocol selection into a combinatorial routing system.

## Canonical Runtime Model

After this change, text-LLM runtime behavior is defined by two orthogonal choices:

1. **Run-level text protocol family**
   - `openai_compatible`
   - `anthropic_compatible`

2. **Stage-level model id**
   - `deepseek-v4-pro`
   - `deepseek-v4-flash`
   - future model ids if deliberately configured later

The repository supports both protocol families as stable product capabilities, but a single run should normally pick one protocol family for all text stages.

This keeps runtime behavior explainable and avoids unnecessary cross-protocol mixing.

## Configuration Design

### New Canonical Settings Surface

Introduce a canonical text-LLM config surface that separates protocol from model.

#### Run-level provider settings

- `text_llm_protocol_family`
  - allowed values: `openai_compatible`, `anthropic_compatible`
- `text_llm_provider_label`
  - default: `bailian`
- `text_llm_base_url`
- `text_llm_api_key`
  - or an equivalent single-key settings surface already resolved from env

These settings define the protocol shape and endpoint family for all text stages in the run.

#### Stage-level model settings

Canonical stage settings become bare model ids:

- `requirements_model_id`
- `controller_model_id`
- `scoring_model_id`
- `finalize_model_id`
- `reflection_model_id`
- `structured_repair_model_id`
- `judge_model_id`
- `tui_summary_model_id` if the repository still wants a stage-local override

The checked-in defaults should be:

- `requirements_model_id=deepseek-v4-pro`
- `controller_model_id=deepseek-v4-pro`
- `reflection_model_id=deepseek-v4-pro`
- `judge_model_id=deepseek-v4-pro`
- `scoring_model_id=deepseek-v4-flash`
- `finalize_model_id=deepseek-v4-flash`
- `structured_repair_model_id=deepseek-v4-flash`

If `tui_summary` continues to inherit from the scoring stage today, that inheritance may stay, but it must inherit through the new canonical model-id surface rather than through old prefixed strings.

### Removed Settings

Remove old canonical settings that encode provider/protocol into the model id string.

At minimum, active settings construction must stop accepting these as canonical stage inputs:

- `requirements_model`
- `controller_model`
- `scoring_model`
- `finalize_model`
- `reflection_model`
- `structured_repair_model`
- `judge_model`
- `tui_summary_model`

Remove judge-specific endpoint/key settings as active runtime settings:

- `judge_openai_base_url`
- `judge_openai_api_key`

### Hard Decommission Rule

There is no backward-compatibility parser for old provider-prefixed model strings.

If a checked-in or local env file still provides old stage model values such as:

- `openai-chat:deepseek-v3.2`
- `openai-responses:gpt-5.4-mini`

settings construction must fail with a clear migration error.

That error should say:

- which old keys or values are no longer accepted
- which new canonical keys should be used instead

This is a deliberate hard cut to avoid long-lived compatibility garbage.

## Provider Boundary Design

The text-LLM adapter layer should stop treating the model id string as a protocol selector.

Instead, provider construction should take:

- `protocol_family`
- `base_url`
- `api_key`
- `model_id`

and build the correct client/request shape from those inputs.

### OpenAI-compatible path

This path continues to use OpenAI-compatible request formatting against the configured Bailian base URL.

### Anthropic-compatible path

This path uses Anthropic-compatible `messages` request formatting against the configured Bailian Anthropic-style base URL.

### Structured-output behavior

Structured-output selection remains stage-aware and model-aware, but protocol family becomes an explicit input to that decision.

The implementation should not assume that “OpenAI-compatible” automatically means one output mode and “Anthropic-compatible” automatically means another. Instead, the runtime should explicitly decide whether the configured stage/protocol/model combination supports:

- native structured output
- prompted structured output
- repair pass behavior

That decision should be visible in diagnostics and call artifacts.

## Judge Boundary

`judge` becomes a normal text stage on the same provider surface as the rest of runtime text LLMs.

After this change:

- `judge` uses the same Bailian endpoint family as the rest of the run
- `judge` uses the same API-key surface as the rest of the run
- `judge` defaults to `deepseek-v4-pro`

This removes the special local-URL/local-key path that previously pointed at GPT-5.4.

## Runtime Diagnostics And Artifact Changes

Every text-LLM call artifact and runtime event should record enough information to make protocol-family failures obvious.

### Required new metadata

At minimum, each text-stage call artifact should include:

- `protocol_family`
- `provider_label`
- `base_url_family`
- `model_id`
- `stage`
- `call_id`
- `failure_kind` when failed
- `provider_status_code` when available
- `provider_error_type` when available

### Failure taxonomy

Use explicit failure categories such as:

- `timeout`
- `provider_invalid_request`
- `provider_schema_error`
- `transport_error`
- `response_validation_error`

This taxonomy should flow into:

- stage call artifacts
- runtime events
- benchmark summaries where relevant

The goal is to avoid opaque failures like a bare `TimeoutError` without stage or provider context.

## Benchmark Failure Linkage

Failed benchmark rows must always carry stable run linkage.

Required fields for failed rows:

- `run_id`
- `run_dir`
- `trace_log_path`

Benchmark execution manifests should also attach child-run references for failed cases, not only successful ones.

This change is explicitly in scope because the current failed summary shape is too weak for postmortem work.

## What Stays Unchanged

- candidate-feedback phrase quality logic
- PRF v1.5 shadow/mainline status
- CTS retrieval transport behavior
- stopping/exhaustion logic
- PRF sidecar deployment architecture

This is intentionally a protocol/model-boundary and diagnostics change, not a retrieval-strategy redesign.

## Implementation Preconditions

Implementation must not start directly from the current main worktree state.

Before feature coding begins:

1. Merge or otherwise resolve the current completed feature branch that is still open.
2. Remove stale feature worktrees/branches that are no longer needed.
3. Avoid mixing in the current main-worktree benchmark-debug edits.
4. Start the actual implementation in a fresh dedicated worktree from a clean `main` baseline.

This precondition is part of the design, not a convenience suggestion.

## Testing Expectations

### Settings tests

- new canonical settings load correctly
- old prefixed model-string values fail with clear migration errors
- removed judge-specific endpoint/key settings are no longer active runtime surface

### Provider-boundary tests

- OpenAI-compatible path builds the expected client/request shape
- Anthropic-compatible path builds the expected client/request shape
- call artifacts record the correct `protocol_family` and `model_id`

### Stage-routing tests

- `requirements/controller/reflection/judge` default to `deepseek-v4-pro`
- `scoring/finalize/structured_repair` default to `deepseek-v4-flash`
- runtime audit and run config reflect those defaults

### Benchmark/diagnostic tests

- failed benchmark rows include `run_id`, `run_dir`, and `trace_log_path`
- failed benchmark manifest includes failed child run refs
- timeout and provider failures classify into the explicit failure taxonomy

### Regression tests

- existing successful text-stage flows still run under `openai_compatible`
- equivalent flows run under `anthropic_compatible`
- the company-removal branch boundaries remain absent

## Rollout

The rollout should proceed in this order:

1. integrate or close the currently completed feature branch and clean stale worktrees
2. create a fresh implementation worktree
3. introduce the new canonical config surface and hard-cut the old one
4. implement dual protocol support in the provider boundary
5. switch checked-in defaults to DeepSeek V4 stage routing
6. move judge onto the same Bailian text provider surface
7. enhance diagnostics and benchmark failure linkage
8. verify both protocol families in tests

## Risks

1. Anthropic-compatible behavior on Bailian may have product quirks not obvious from public docs.
2. Hard-cut config migration will break stale local env files until they are updated.
3. Structured-output behavior may differ subtly between the two protocol paths and must be tested explicitly.

## Acceptance Criteria

This change is complete when all of the following are true:

1. The repository has one canonical text-LLM config surface that separates protocol from model.
2. The repository supports both `openai_compatible` and `anthropic_compatible` text-LLM runtime paths.
3. The checked-in defaults use:
   - `deepseek-v4-pro` for `requirements`, `controller`, `reflection`, `judge`
   - `deepseek-v4-flash` for `scoring`, `finalize`, `structured_repair`
4. `judge` no longer depends on a separate local URL/key path.
5. Old prefixed model-string config is rejected rather than silently parsed.
6. Failed benchmark rows always include `run_id`, `run_dir`, and `trace_log_path`.
7. Timeout/provider failures are clearly classified in runtime artifacts and benchmark-facing outputs.
8. Candidate-feedback phrase extraction behavior is unchanged by this rollout.
9. Stopping/exhaustion behavior is unchanged by this rollout.
