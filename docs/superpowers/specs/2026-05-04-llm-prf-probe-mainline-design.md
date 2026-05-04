# LLM PRF Probe Mainline Design

## Summary

Replace the current rule-heavy PRF candidate-expression proposal for the 30% typed second lane with a DeepSeek V4 Flash LLM extractor. The LLM proposes grounded candidate phrases from high-quality top-pool resumes, but deterministic runtime validation and the existing PRF gate remain the only acceptance boundary.

This change targets the `prf_probe` second lane, not the low-quality rescue `candidate_feedback` lane.

## Motivation

The existing `prf_probe` route is the 30% side of the round 2+ typed second-lane search budget. Its runtime shape is already right:

- run one `exploit` lane from the controller query;
- run one second lane using `prf_probe` when PRF has a safe expression;
- fall back to `generic_explore` when PRF has no safe expression;
- keep 70/30 fetch allocation in retrieval execution.

The weak part is candidate-expression proposal. The current rule/regex path in `candidate_feedback/extraction.py` is brittle across domains, especially for Chinese and mixed-language resumes. Maintaining domain rules, phrase lists, or industry-specific dictionaries is not viable because JD and resume domains vary widely.

The intended product behavior is general pseudo relevance feedback:

1. inspect the best scored resumes;
2. extract explicit common query material;
3. search the 30% side lane with one safe expansion phrase;
4. avoid free-form query rewriting and domain-specific rule growth.

## Decisions

1. Use DeepSeek V4 Flash for PRF phrase proposal.
2. Make the LLM extractor the direct mainline source for `prf_probe` candidate expressions.
3. Supersede PRF v1.5 sidecar-backed span proposal as the default active `prf_probe` proposal backend.
4. Keep extraction strictly grounded in top-pool seed resume evidence.
5. Treat LLM candidate type labels and risk flags as advisory only.
6. Keep deterministic grounding validation and `build_prf_policy_decision(...)` as the final acceptance boundary.
7. If LLM extraction fails or no safe candidate survives, fall back to `generic_explore`.
8. Use prompted JSON plus Pydantic validation; do not assume provider-native strict JSON Schema for Bailian-hosted DeepSeek V4.
9. Use `output_retries=2` for structured-output parse/schema failures, matching the repository's structured-output retry discipline.
10. Add both deterministic CI harness coverage and a non-CI live DeepSeek bakeoff harness.

## Current State

### Typed second lane

The active 70/30 path lives in:

- `src/seektalent/runtime/second_lane_runtime.py`
- `src/seektalent/runtime/retrieval_runtime.py`
- `src/seektalent/runtime/orchestrator.py`

For round 2+, runtime builds:

- an `exploit` logical query from the controller retrieval plan;
- a second logical query from `build_second_lane_decision(...)`.

If PRF gate passes, the second query is `prf_probe`. Otherwise it is `generic_explore`.

### Existing PRF proposal

The current PRF policy input is produced by:

- selecting seed resumes with `select_feedback_seed_resumes(...)`;
- extracting candidate expressions from structured scoring fields with regex/rule logic;
- passing those expressions into `build_prf_policy_decision(...)`.

The gate is useful and should remain. The proposal layer is the part being replaced.

### Low-quality rescue lane

The low-quality rescue lane still exists in:

- `src/seektalent/runtime/rescue_router.py`
- `src/seektalent/runtime/rescue_execution_runtime.py`

That path is separate from the 70/30 typed second lane. This design does not remove or change it.

## Design

### 1. Runtime boundary

Keep the current round-level retrieval shape:

```text
controller query
  -> exploit lane
  -> LLM PRF proposal
  -> grounding validation
  -> deterministic PRF gate
  -> prf_probe if safe else generic_explore
  -> 70/30 search execution
```

The LLM extractor only replaces candidate-expression proposal. It must not own:

- 70/30 lane allocation;
- CTS query execution;
- scoring;
- second-lane fallback selection;
- deterministic acceptance policy.

### 2. Proposal backend precedence

This design supersedes sidecar-backed PRF v1.5 span proposal as the default active `prf_probe` proposal path.

Add an explicit proposal backend setting:

```text
prf_probe_proposal_backend = "llm_deepseek_v4_flash"
```

Supported backend values:

- `llm_deepseek_v4_flash`
- `legacy_regex`
- `sidecar_span`

Default for this rollout:

```text
llm_deepseek_v4_flash
```

Backend semantics:

- `llm_deepseek_v4_flash` is the active mainline proposal backend for `prf_probe`.
- `legacy_regex` remains available for deterministic tests, explicit rollback, and compatibility diagnostics.
- `sidecar_span` remains available only when explicitly configured; it is not part of this rollout's active default path.
- The low-quality rescue `candidate_feedback` lane does not use this backend and is unchanged.

The implementation must not create a fourth independent PRF route. All proposal backends feed the same grounded `FeedbackCandidateExpression` and `PRFPolicyDecision` path.

### 3. LLM extractor

Add a focused PRF LLM extractor boundary under `seektalent.candidate_feedback`:

- `llm_prf.py`
- `llm_prf_bakeoff.py`

The extractor uses a dedicated canonical text-LLM stage:

```text
stage = "prf_probe_phrase_proposal"
```

Default model setting:

```text
prf_probe_phrase_proposal_model_id = deepseek-v4-flash
prf_probe_phrase_proposal_reasoning_effort = off
```

This stage may share the same model id value as the low-quality rescue candidate-feedback configuration, but the invocation path must remain separate. The low-quality rescue `candidate_feedback` lane must not import, instantiate, or call `llm_prf.py` unless a separate design explicitly changes that lane.

If the OpenAI-default restoration branch has not landed yet, this feature must still set the dedicated PRF proposal model default to:

```text
deepseek-v4-flash
```

The extractor should use a new schema for phrase proposals, not the current dormant `CandidateFeedbackModelRanking` shape. The current ranking helper ranks already-generated terms; this feature needs proposals from seed evidence.

### 4. Structured-output policy

The LLM extractor must not assume native strict JSON Schema support.

Default behavior:

- use the repository's resolved structured-output mode for `stage="prf_probe_phrase_proposal"`;
- for Bailian-hosted DeepSeek V4, use prompted JSON and Pydantic validation;
- optionally request `response_format={"type":"json_object"}` only when the resolved endpoint and protocol support it;
- include the word `json` and a compact schema/example in the prompt when using JSON output mode;
- parse JSON locally;
- validate the parsed payload with Pydantic;
- use `output_retries=2` for empty, invalid, truncated, or schema-invalid model output.

Provider capability failure, network failure, timeout, and tool failure are not output-retry conditions.

The acceptance boundary is local schema validation plus deterministic grounding and PRF gate behavior, not provider-native schema enforcement.

### 5. Input contract

The LLM input should be compact and replayable.

Include:

- `role_title`
- `role_summary`
- `must_have_capabilities`
- current round `retrieval_plan.query_terms`
- existing active/inactive query terms
- sent query terms and tried term families
- up to five high-quality seed resumes from `select_feedback_seed_resumes(...)`
- deterministic negative evidence summaries used to avoid noisy shared phrases

If fewer than two high-quality seed resumes are available, do not call the LLM. Record `insufficient_prf_seed_support` and let the second lane fall back to `generic_explore`.

For each seed resume, include bounded structured fields:

- `evidence`
- `matched_must_haves`
- `matched_preferences`
- `strengths`

Each evidence item in the frozen input artifact must carry:

- `resume_id`
- `source_field`
- `source_text_index`
- `source_text_raw`
- `source_text_hash`

`strengths` may guide proposal, but it must not be the only grounding source for an accepted phrase because it is derived scoring prose.

Raw full resumes are out of scope for this change.

Negative examples must be selected deterministically from already-scored candidates using these fixed rules:

- candidates with `fit_bucket != "fit"` or high risk score;
- sorted by risk score descending, then overall score ascending, then resume id;
- capped at five.

The LLM may see negative evidence as context, but negative support counting remains deterministic in runtime.

Model sampling must be deterministic for proposal calls. Use temperature `0` or the repository's equivalent deterministic model setting.

### 6. Output contract

The LLM returns candidate phrase proposals, not final search query terms.

Each candidate should include:

- `surface`
- `normalized_surface`
- `candidate_term_type`
- `source_evidence_refs`
- `source_resume_ids`
- `linked_requirements`
- `rationale`
- `risk_flags`

Each `source_evidence_ref` must identify:

- `resume_id`
- `source_field`
- `source_text_index`
- `source_text_hash`

The LLM must not be allowed to invent source references. Runtime rejects references that do not map to the frozen LLM PRF input payload.

`candidate_term_type` should support the current PRF policy vocabulary:

- `skill`
- `tool_or_framework`
- `product_or_platform`
- `technical_phrase`
- `responsibility_phrase`
- `company_entity`
- `location`
- `degree`
- `compensation`
- `administrative`
- `generic`
- `unknown_high_risk`
- `unknown`

The extractor must be prompted to:

- return only phrases visible in seed evidence;
- prefer common phrases supported by multiple fit seed resumes;
- avoid company, location, school, degree, salary, age, title-only, and generic boilerplate phrases;
- avoid rewriting the query;
- avoid inventing implied capabilities that do not appear in seed evidence.

`candidate_term_type`, `rationale`, and `risk_flags` are advisory fields for diagnostics and downstream deterministic classification. They must not be trusted as safety decisions.

### 7. Grounding validation

Runtime must not trust the LLM's candidate list directly.

For each candidate:

1. Resolve every `source_evidence_ref` against the frozen `llm_prf_input` artifact.
2. Verify the referenced `source_text_hash`.
3. Try an exact raw substring match for `surface` in `source_text_raw`.
4. If exact raw match fails, try NFKC-normalized matching only through an offset map that maps the normalized span back to raw source text offsets.
5. When multiple matches exist, use deterministic tie-break order:
   - referenced `source_field`;
   - earliest `source_text_index`;
   - earliest raw start offset.
6. Reject matches that are only unsafe substrings inside a larger conflicting token or family.
7. Record aligned source field, source text index, source text hash, raw start/end offsets, raw surface, normalized surface, and resume id.
8. Reject unaligned candidates with `non_extractive_or_unmatched_surface`.

Substring safety examples:

- `Java` must not be accepted from `JavaScript`.
- `React` must not be accepted from `React Native` unless the family and evidence explicitly support `React` itself.
- `算法` must not be accepted from a title-only or generic phrase such as `推荐算法工程师`.
- `阿里` must not be accepted from `阿里云` when deterministic classification marks it as company/entity or ambiguous company/product material.

Acceptance eligibility requires:

- support from at least two seed resumes;
- support from non-`strengths` fields;
- no existing query term, sent query term, or tried term family conflict;
- no high negative-support signal;
- no rejected entity/filter/generic type.

Grounding failures do not trigger LLM retries. They are unsafe candidate outputs, not structured-output failures.

### 8. Classification and familying

LLM candidate classification is advisory.

Before constructing `FeedbackCandidateExpression`, runtime must reclassify or override high-risk types deterministically. The deterministic classifier and PRF gate are authoritative for:

- company/entity risk;
- location, degree, compensation, administrative, and title-only material;
- generic boilerplate;
- responsibility-only phrases;
- unknown or ambiguous high-risk phrases.

Grounded LLM candidates must be converted into the existing phrase-family path before support and conflict checks.

Support and conflict checks are computed at phrase-family level, not raw string level:

- positive seed support;
- negative support;
- existing query-term conflict;
- sent query-term conflict;
- tried-family conflict.

This rollout should use conservative surface familying:

- exact normalized match;
- case variant;
- separator variant;
- slash variant;
- hyphen/underscore/dot variant;
- CamelCase variant.

Do not use broad embedding merges in the LLM rollout. Embedding familying remains part of explicit sidecar configuration, not the default LLM PRF path.

Examples that should be treated as one conservative family:

- `Flink CDC`
- `flink-cdc`
- `FlinkCDC`

Examples that should not merge by broad semantic similarity alone:

- `React` and `React Native`
- `推荐算法` and `搜索算法`
- `云平台` and `阿里云`

### 9. PRF gate integration

Convert grounded LLM candidates into `FeedbackCandidateExpression` objects and pass them through `build_prf_policy_decision(...)`.

The existing deterministic gate remains responsible for:

- minimum seed support;
- negative-support rejection;
- tried-family rejection;
- company/entity rejection;
- strengths-only rejection;
- responsibility-phrase shadow-only rejection;
- selecting at most one accepted expression.

If one expression survives, `build_second_lane_decision(...)` produces `prf_probe` as today.

If no expression survives, second lane falls back to `generic_explore` as today.

### 10. Timeout and scheduling

The exploit logical query must not depend on the LLM PRF result.

Use the pragmatic scheduling model for this rollout:

1. Build the exploit logical query immediately.
2. Start LLM PRF proposal before final second-lane bundle selection.
3. Apply an independent hard timeout:

```text
prf_probe_phrase_proposal_timeout_seconds
```

4. If timeout is reached, record `llm_prf_timeout` and build `generic_explore` for the second lane.
5. Continue normal 70/30 retrieval execution.

This keeps implementation smaller than fully concurrent lane execution while making the non-blocking promise operational.

### 11. Error handling

Use the same disciplined failure behavior as the rest of the codebase:

- transport/network/provider failure: no retry chain; record failure and fall back to `generic_explore`;
- structured-output parse/schema validation failure: allow `output_retries=2`;
- exhausted structured-output retries: record `llm_prf_structured_output_failed` and fall back to `generic_explore`;
- LLM timeout: record `llm_prf_timeout` and fall back to `generic_explore`;
- grounding failure: reject the candidate, do not retry the model;
- PRF gate rejection: reject the candidate, do not retry the model;
- all candidates rejected: record `no_safe_llm_prf_expression` and fall back to `generic_explore`.

The LLM path must never prevent exploit-lane construction or fail the current round. Any PRF proposal delay is capped by `prf_probe_phrase_proposal_timeout_seconds`.

### 12. Artifacts

Persist enough data to diagnose and replay the PRF decision.

Required artifacts:

- `round.XX.retrieval.llm_prf_input`
- `round.XX.retrieval.llm_prf_call`
- `round.XX.retrieval.llm_prf_candidates`
- `round.XX.retrieval.llm_prf_grounding`
- `round.XX.retrieval.prf_policy_decision`
- `round.XX.retrieval.second_lane_decision`

All artifacts must be registered through the existing logical artifact registry/resolver. Do not write ad hoc paths outside the active typed artifact taxonomy.

Each LLM PRF artifact must include or reference:

- `schema_version`
- `llm_prf_extractor_version`
- `prompt_name`
- `prompt_hash`
- `grounding_validator_version`
- `proposal_backend`
- `model_id`
- `protocol_family`
- `endpoint_kind`
- `endpoint_region`
- `structured_output_mode`
- `output_retry_count`
- `failure_kind` when applicable

`llm_prf_candidates` should preserve raw LLM candidates.

`llm_prf_grounding` should preserve candidate-level validation status and reject reasons.

`prf_policy_decision` remains the final deterministic acceptance artifact.

`second_lane_decision` remains the routing artifact.

`llm_prf_call` must never store API keys or secrets. If raw request/response bodies are stored, headers and provider credentials must be redacted, and raw response content should be bounded to the structured output payload needed for replay.

### 13. Live bakeoff harness

Add a non-CI harness that can run real DeepSeek V4 Flash extraction on fixed slices.

The harness should:

- require explicit API configuration;
- never run in CI by default;
- use fixed sanitized JD/seed slices for English, Chinese, and mixed-language cases;
- write raw candidate proposals, grounding results, PRF gate results, accepted expression, fallback reason, and metrics;
- make model quality inspectable without changing runtime code.

Primary blocker conditions:

- accepted non-extractive phrase;
- accepted company/entity/location/degree/salary leakage;
- accepted generic boilerplate;
- accepted phrase supported by fewer than two seed resumes;
- accepted phrase grounded only in `strengths`.

Primary metrics:

- accepted phrase precision;
- grounding pass rate;
- structured-output failure rate;
- no-safe-expression rate;
- generic fallback rate;
- blocker count;
- per-language slice pass/fail counts.

The implementation path is mainline, not shadow. The live bakeoff does not block code implementation, but it must run before treating `llm_deepseek_v4_flash` as production-ready in benchmark or broader evaluation runs. Blocker count must be zero. High `generic_explore` fallback rate is not unsafe, but it is a product-quality failure signal because it means the LLM PRF path is not adding recall value.

### 14. CI harness

CI tests should use fake LLM outputs and deterministic fixtures.

Required fixture coverage:

- English technical phrase;
- Chinese technical phrase;
- mixed Chinese-English phrase;
- valid grounded candidate accepted into `prf_probe`;
- all rejected candidates falling back to `generic_explore`;
- unmatched LLM surface rejected;
- single-seed support rejected;
- strengths-only grounding rejected;
- existing/sent/tried term rejected;
- company, location, degree, salary, and generic boilerplate rejected;
- structured-output failure attempts two output retries before fallback;
- LLM timeout falls back to `generic_explore`;
- seed count below two skips the LLM call;
- LLM candidate type labels are advisory and deterministic classifier overrides unsafe labels;
- family-level support and tried-family conflicts are used;
- artifacts contain input, call, candidates, grounding, PRF policy, and second-lane decision refs.

## Non-Goals

Do not change:

- 70/30 second-lane budget allocation;
- exploit lane behavior;
- CTS query execution;
- scoring, finalization, controller, reflection, or judge behavior;
- low-quality rescue `candidate_feedback` lane;
- PRF sidecar deployment;
- PRF embedding sidecar behavior;
- low-quality rescue `candidate_feedback` text stage behavior;
- top-pool scoring policy;
- stopping policy.

Do not add:

- maintained domain vocabularies;
- industry dictionaries;
- company knowledge bases;
- broad ontology layers;
- LLM free-form query rewriting;
- fallback model chains;
- network retry scaffolding beyond the existing structured-output retry exception.

## Acceptance Criteria

This design is complete when implementation can prove:

1. when round `>= 2`, enough high-quality seeds exist, and `prf_probe_proposal_backend == "llm_deepseek_v4_flash"`, second-lane PRF candidate proposal uses DeepSeek V4 Flash LLM extraction;
2. accepted `prf_probe` expressions are grounded in seed resume evidence;
3. LLM output never directly becomes a query term without deterministic validation and PRF gate acceptance;
4. unsafe, ungrounded, or unsupported candidates fall back to `generic_explore`;
5. structured-output/schema failures use two output retries before fallback;
6. timeout, insufficient seed support, and provider failure record deterministic failure reasons and fall back to `generic_explore`;
7. LLM candidate labels are advisory and runtime deterministic classification is authoritative;
8. support and conflict checks happen at phrase-family level;
9. CI covers English, Chinese, and mixed-language deterministic fixtures;
10. live bakeoff can call the real model and emit quality metrics;
11. existing 70/30 lane allocation remains unchanged;
12. low-quality rescue behavior remains unchanged.

## Sources

- [DeepSeek JSON Output](https://api-docs.deepseek.com/guides/json_mode)
- [Alibaba Cloud Model Studio text generation model capabilities](https://help.aliyun.com/zh/model-studio/text-generation-model/)
