# Run Latency Engineering Design

Date: 2026-04-23

## Context

Recent latency audit work showed that whole-run time is dominated by model stages, not CTS HTTP latency. In the latest 12 sampled runs, controller and reflection averaged about 92s and 81s per call respectively. Scoring also contributes materially through many parallel calls, but its wall-clock impact is bounded by concurrency. CTS tool latency was usually a few seconds per run.

Controller and reflection thinking are considered quality-positive and should stay enabled. Requirements extraction may also use thinking. The goal for this design is therefore not to disable thinking or change candidate-selection behavior. The goal is to reduce engineering overhead around expensive thinking calls, scoring execution, and repeated identical work.

## Goals

- Reduce end-to-end `seektalent run` latency without changing retrieval, stop, ranking, or candidate-selection semantics.
- Keep thinking enabled for requirements, controller, and reflection.
- Avoid full thinking-model retries when a cheaper repair can fix a structurally parsed but semantically invalid output.
- Score each newly recalled candidate as today, but raise default scoring concurrency to match the per-round recall target.
- Add exact-input caches for scoring and requirements extraction.
- Add provider prompt-cache observability and request knobs where supported.
- Keep every optimization observable in artifacts.

## Non-Goals

- No disabling controller/reflection thinking.
- No early-stop policy change.
- No candidate pre-filtering before LLM scoring.
- No change to scoring rubric or ranking semantics.
- No model fallback chain.
- No speculative approximate cache hits.
- No reliance on provider KV-cache unless artifacts prove it is supported.

## Current Behavior

### Retrieval And Scoring

Each round sets `target_new = TOP_K`, and `TOP_K = 10`. The runtime attempts CTS retrieval until it has 10 new deduplicated candidates or hits page/attempt/exhaustion limits.

Every newly recalled candidate is sent to LLM scoring. Already-seen candidates are deduplicated before scoring, but there is no lightweight pre-filter among the new candidates. Scoring currently uses `scoring_max_concurrency = 5`.

### Thinking Stages

Requirements, controller, and reflection are single serial model calls in the run flow:

1. requirements extraction before retrieval rounds;
2. controller before each round's search;
3. reflection after each round's scoring.

Controller and reflection currently support Bailian `enable_thinking` for `openai-chat:deepseek-v3.2`. Requirements uses normal model settings today and should be made compatible with thinking control.

### Retry Semantics

Pydantic AI output retries are full model retries. When an output validator raises `ModelRetry`, Pydantic AI appends a retry prompt such as "Validation feedback: ... Fix the errors and try again" and sends the message history back to the model. It does not patch only the failing field. For thinking models, this means a semantic retry can pay another full thinking-model call.

Current local semantic retry sources include:

- controller missing `proposed_query_terms`;
- controller query terms rejected by query canonicalization;
- controller missing `response_to_reflection` after a previous reflection;
- requirements normalization rejecting an empty non-anchor `jd_query_terms`;
- reflection draft validation rejecting inconsistent stop fields.

Finalizer also has semantic validators, but finalizer is not the primary expensive thinking target for this design.

## Design

### 1. Thinking Output Repair

Add an explicit repair path for requirements, controller, and reflection outputs.

The normal path remains a thinking model call with native structured output. If the output parses successfully but fails local semantic validation, the runtime should first try a cheap repair before allowing a full thinking retry.

For requirements, controller, and reflection, local semantic validators must run outside Pydantic AI's automatic `output_validator` retry loop. Otherwise `ModelRetry` would trigger another full thinking-model request before the runtime can repair. Schema parsing can still use Pydantic AI native structured output. Post-parse semantic validation should be a plain function that returns either a valid object or a concrete reason.

The repair contract:

- input: original structured output, exact validator reason, minimal constraint data, and the target schema name;
- output: complete replacement structured output of the same type;
- validation: run the same local semantic validator after repair;
- fallback: if repair fails, use the existing full retry behavior.

Preferred repair order:

1. deterministic repair when the fix is obvious and semantics are preserved;
2. non-thinking repair model for cases that need language generation;
3. original thinking-model retry only if repair cannot produce a valid output.

Examples:

- Controller missing `response_to_reflection`: if previous reflection exists, a non-thinking repair model can add a concise acknowledgement while preserving the action and query terms.
- Controller query terms over budget or duplicated: deterministic repair may canonicalize, deduplicate, and trim only when the existing terms already identify the same admitted families. Otherwise use repair model.
- Requirements `jd_query_terms` empty after normalization: repair model gets the job title, JD, original draft, and reason, and returns a corrected full `RequirementExtractionDraft`.
- Reflection inconsistent stop fields: deterministic repair can null `suggested_stop_reason` when `suggest_stop=false`, or ask repair model to generate a reason when `suggest_stop=true`.

Artifacts should record:

- `validator_retry_count`;
- `validator_retry_reasons`;
- `repair_attempt_count`;
- `repair_succeeded`;
- `repair_model`;
- `repair_reason`;
- `full_retry_count`.

This preserves behavior because the same final semantic validators remain authoritative.

The expensive thinking stages should not hide full retries inside Pydantic AI. Configure them so semantic retries are managed by this runtime repair path. If a native schema/parse failure leaves no structured object to repair, the stage may use the existing full retry limit, but that retry must be counted as `full_retry_count` in the call snapshot.

### 2. Scoring Concurrency 10

Change the default `scoring_max_concurrency` from 5 to 10.

Rationale:

- The per-round target is 10 new candidates.
- If fewer than 10 candidates are recalled, only that many tasks exist.
- The existing semaphore already caps concurrency, so this is a config default change, not a scoring behavior change.

The env and CLI overrides remain available. Artifacts should continue to include the effective `scoring_max_concurrency` in `run_config.json`.

### 3. Exact Scoring Cache

Add an exact scorecard cache for LLM scoring.

A cache hit is allowed only when all key inputs match exactly:

- scoring model id;
- scoring prompt hash;
- scoring policy hash;
- requirement sheet hash;
- normalized resume hash;
- output schema version.

On hit:

- materialize the cached `ScoredCandidate`;
- write the normal scorecard artifact;
- append an LLM call snapshot with `cache_hit=true`, `latency_ms=0` or measured cache lookup latency, and no provider call.

On miss:

- call the scoring model exactly as today;
- write the result into the cache after successful validation.

This does not change which candidates are scored or how scores rank. It only avoids repeating identical scoring work across runs.

### 4. Exact Requirements Cache

Add an exact cache for requirements extraction.

Cache key:

- requirements model id;
- requirements prompt hash;
- job title hash;
- JD hash;
- notes hash;
- output schema version.

On hit:

- reuse the cached `RequirementExtractionDraft`;
- normalize it into `RequirementSheet` using the current normalization code;
- record `cache_hit=true` in the requirements call snapshot.

On miss:

- call the requirements model as today;
- normalize the draft;
- store only after successful normalization.

This is especially useful for repeated experiments and evaluation loops.

### 5. Provider Prompt Cache Probe

Add request-level prompt-cache knobs and observability, but treat them as optional.

For OpenAI-compatible model settings, allow:

- stable `openai_prompt_cache_key`;
- `openai_prompt_cache_retention` when supported.

Suggested cache key grouping:

- requirements: prompt name, model id, and input hash;
- controller: prompt name, model id, and requirement sheet hash;
- reflection: prompt name, model id, and requirement sheet hash;
- scoring: prompt name, model id, requirement sheet hash, and scoring policy hash.

Do not assume Bailian supports OpenAI prompt cache parameters. The implementation should make this observable:

- record configured prompt cache key and retention in snapshots;
- record provider usage cached token counts when available;
- if a provider rejects these parameters, fail fast during a dedicated probe or leave the setting disabled by default.

Do not restructure prompts for cache hits in this first pass. Prompt prefix stabilization can be a later design because it may affect model behavior.

### 6. Requirements Thinking Control

Add requirements-stage thinking control alongside controller and reflection.

Configuration:

- `requirements_enable_thinking: bool = True`;
- env var `SEEKTALENT_REQUIREMENTS_ENABLE_THINKING`;
- pass this to `build_model_settings(..., enable_thinking=...)` for requirements extraction.

This keeps requirements thinking explicit and observable in `run_config.json`.

## Data Flow

1. Runtime builds input truth.
2. Requirements cache lookup runs first.
3. On miss, requirements thinking model extracts a draft.
4. Requirements semantic normalization validates the draft.
5. If semantic validation fails, repair path attempts to fix the draft.
6. If repair succeeds, runtime proceeds; if not, existing full retry/failure path applies.
7. Each retrieval round proceeds normally.
8. Controller thinking call produces a decision.
9. Controller semantic validation may repair before full retry.
10. Search retrieves up to the existing target and limits.
11. Each new candidate is scored, with exact cache lookup before provider call and concurrency up to 10.
12. Reflection thinking call produces advice.
13. Reflection semantic validation may repair before full retry.
14. Finalization proceeds as today.

## Error Handling

- Cache corruption or schema mismatch is a miss, not a fallback chain.
- Repair failures are recorded and then defer to existing full retry semantics.
- Provider prompt-cache parameter rejection should be discovered by a probe or disabled setting, not silently retried through provider-specific fallbacks.
- Scoring cache writes happen only after successful score materialization.
- Requirements cache writes happen only after successful normalization.

## Testing

Add focused tests for:

- scoring default concurrency is 10 while override still works;
- scoring cache hit skips provider call and writes normal artifacts;
- scoring cache miss calls provider and stores result;
- requirements cache hit skips provider call and still normalizes the draft;
- requirements thinking setting is passed into model settings;
- requirements/controller/reflection semantic validators run outside automatic `ModelRetry` full retry handling;
- controller repair avoids full thinking retry for a semantic validator failure;
- requirements repair fixes empty non-anchor `jd_query_terms` when possible;
- reflection repair fixes inconsistent stop fields;
- artifacts record cache and repair metadata.

Run full test suite after implementation.

## Acceptance Criteria

- Candidate retrieval, stop, scoring, and ranking semantics are unchanged.
- Default scoring concurrency is 10.
- Exact scorecard cache and requirements cache are available and observable.
- Requirements thinking can be enabled and is represented in config artifacts.
- Requirements, controller, and reflection semantic failures try repair before full thinking retry.
- Prompt cache knobs are observable and disabled or harmless when unsupported.
- Existing latency audit can report cache hits, repair attempts, and full retries.

## Open Implementation Notes

- The repair implementation should be small and explicit. Avoid generic agent frameworks.
- If recovering raw invalid schema output from Pydantic AI is difficult, repair can start with post-parse semantic failures only. Native schema/parse failures can remain full retries in the first implementation.
- Finalizer repair may reuse the same helper later, but it is not the critical path for this design.
