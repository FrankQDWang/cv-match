# Retrieval Flywheel And Typed Second Lane Design

## Goal

Define the next productization-phase retrieval architecture for SeekTalent so the system can learn from retrieval outcomes without turning the runtime into an open-ended agent.

The first milestone is not a trained query rewriter. The first milestone is a clean retrieval flywheel that can:

- identify each logical query
- attribute each newly found resume to its first effective query
- retain full query-to-resume visibility for policy comparison
- compare second-lane policies with replayable evidence
- upgrade the current `candidate_feedback` rescue feature into a bounded `PRF v1` probe

## Decision Summary

This design fixes six decisions:

1. Keep the runtime as a controlled workflow, not an open-ended agent.
2. Make retrieval learning the mainline and keep company handling separate.
3. Keep two logical retrieval lanes from round 2 onward, but type the second lane.
4. Make the second lane `prf_probe if safe else generic_explore`.
5. Keep the initial budget split at `exploit 70 / second_lane 30`.
6. Keep web company discovery only as late-rescue company hypothesis generation.

## Current Shape

The repository already has the right backbone for a retrieval flywheel:

- deterministic runtime orchestration in [`src/seektalent/runtime/orchestrator.py`](/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/orchestrator.py)
- structured query and retrieval records in [`src/seektalent/models.py`](/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/models.py)
- per-run diagnostics and term audit artifacts documented in [`docs/outputs.md`](/Users/frankqdwang/Agents/SeekTalent-0.2.4/docs/outputs.md)
- an existing two-lane retrieval topology from round 2 onward through `_build_round_query_states()`
- an existing internal-feedback extractor in [`src/seektalent/candidate_feedback/extraction.py`](/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/candidate_feedback/extraction.py)

The current weakness is not lack of components. The weakness is that the second lane is still semantically loose, `candidate_feedback` is still treated as a late rescue feature, and query-term-resume attribution is not yet strong enough to support a retrieval learning loop.

## Long-Term Architecture

SeekTalent should stabilize around two separate adaptive layers.

### 1. Retrieval Flywheel

This is the mainline learning loop for term-level retrieval improvement.

Responsibilities:

- baseline exploit retrieval
- second-lane policy selection
- PRF candidate generation from internal results
- generic exploration fallback
- query and term attribution
- replay and promotion gates

Non-responsibilities:

- company entity interpretation
- web-derived company alias expansion
- direct entity-to-keyword rewriting

### 2. Company Evidence Layer

This is an entity-level side channel, not a query rewrite system.

Responsibilities:

- extract company mentions from inputs when needed
- build company hypotheses from web evidence during rescue
- expose company evidence to scoring, reranking, explanations, and diagnostics
- gate any company-based rescue retrieval behind explicit rescue rules

Non-responsibilities:

- PRF term promotion
- second-lane identity selection
- default query rewrite

## Phase 1 Boundary

Phase 1 is intentionally narrow.

Included:

- query identity, first-hit attribution, and query-to-resume hit logging
- typed second-lane routing
- `PRF v1` from current `candidate_feedback`
- forced and shadow replay for second-lane comparison
- experiment harness updates to compare baseline and candidate retrieval policies
- keeping web company discovery alive only as a rescue-only company hypothesis path

Excluded:

- training a standalone query rewriter
- reviving explicit target company as a mainline retrieval feature
- building a full company entity platform
- adding a third always-on retrieval lane
- giving the controller agentic control over second-lane identity

## Mainline Retrieval Policy

### Round Topology

Round 1:

- one logical lane only: `exploit`

Round 2 and later:

- always attempt to construct two logical lanes
- lane one is always `exploit`
- lane two is runtime-owned and typed:
  - `prf_probe` if safe
  - else `generic_explore`

This preserves the current dual-lane topology while making the second lane explainable and comparable.

### Lane Identity

Add an explicit lane identity separate from current `query_role`.

Recommended values:

- `exploit`
- `prf_probe`
- `generic_explore`
- `late_rescue`
- `company_rescue`

`query_role` can continue to describe provider-facing intent if needed. `lane_type` becomes the retrieval-learning identity used by diagnostics, replay, and attribution.

### Second-Lane Decision Artifact

Round 2 and later should always attempt to construct a second lane, but the runtime must persist the decision even when no second lane executes.

Recommended artifact fields:

- `round_no`
- `attempted_prf`
- `prf_gate_passed`
- `reject_reasons`
- `fallback_lane_type`
- `fallback_query_fingerprint`
- `no_fetch_reason`

This avoids losing evidence about why `prf_probe` did not run.

### Budget Policy

Phase 1 budget split:

- `exploit`: 70
- `second_lane`: 30

Refill discipline:

- initial allocation uses `70/30`
- second lane should still respect provider paging minimums and runtime target caps
- refill prefers `exploit`
- refill decisions are made only after dedupe and scoring for the current batch or page
- second lane continues to consume refill budget only when it shows positive gain in the current round
- a second lane that is `zero_gain`, `duplicate_only`, `broad_noise`, or `drift_suspected` should stop receiving additional refill within that round

The second lane is a probe, not a co-equal always-on search budget peer.

## Data Contract

Phase 1 needs a minimal but strict retrieval data contract.

### Logical Query Identity

Each executed logical query must persist both:

- `query_instance_id`
- `query_fingerprint`

`query_instance_id` is stable within a run. `query_fingerprint` is stable across replay and benchmark comparison.

`query_instance_id` should be attached to the logical query, not each CTS page fetch. One logical query corresponds to one round-level lane with one canonical query specification and one plan version.

Recommended fields for `query_instance_id`:

- `run_id`
- `round_no`
- `lane_type`
- `query_fingerprint`
- `source_plan_version`

Recommended fields for `query_fingerprint`:

- `job_intent_fingerprint`
- `lane_type`
- `canonical_query_spec`
- `policy_version`

### Canonical Query Specification

The system must persist a canonical query specification, not just a normalized term list.

Recommended minimal shape:

```python
class CanonicalQuerySpec:
    lane_type: str
    anchors: list[str]
    expansion_terms: list[str]
    promoted_prf_expression: str | None
    generic_explore_terms: list[str]
    required_terms: list[str]
    optional_terms: list[str]
    excluded_terms: list[str]
    location_key: str | None
    provider_filters: dict[str, object]
    boolean_template: str
    rendered_provider_query: str
    provider_name: str
    source_plan_version: str
```

Phase 1 does not need a full provider-agnostic query AST platform. It does need enough canonical structure to ensure that replay and comparison are joining semantically equivalent queries rather than only equal term bags.

### Resume First-Hit Attribution

Each new resume entering the candidate pool should persist:

- `first_query_instance_id`
- `first_query_fingerprint`
- `first_round_no`
- `first_lane_type`
- `first_location_key`
- `first_location_type`
- `first_batch_no`

This is the minimum needed to tell whether a strong candidate came from the exploit lane, a PRF probe, or a fallback explore path.

### Query-Resume Hit Ledger

First-hit attribution is necessary for product explanation, but insufficient for policy evaluation. Phase 1 should therefore add a `query_resume_hits` artifact or table.

Recommended fields:

- `run_id`
- `query_instance_id`
- `query_fingerprint`
- `resume_id`
- `round_no`
- `lane_type`
- `location_key`
- `batch_no`
- `rank_in_query`
- `provider_score_if_any`
- `was_new_to_pool`
- `was_duplicate`
- `scored_fit_bucket`
- `final_candidate_status`

This preserves full lane visibility and avoids over-crediting whichever lane happened to run first.

### Query Outcome Labels

Offline evaluation should produce at least these query outcome labels:

- `marginal_gain`
- `duplicate_only`
- `zero_recall`
- `broad_noise`
- `low_recall_high_precision`
- `drift_suspected`

These are evaluation labels, not online agent thoughts.

### Outcome Label Definitions

Phase 1 should define outcome labels with artifact-recomputable rules rather than free-form judgment.

Recommended initial definitions:

- `zero_recall`
  - `provider_returned_count == 0`
- `duplicate_only`
  - `provider_returned_count > 0`
  - and `new_unique_resume_count == 0`
- `marginal_gain`
  - `new_unique_resume_count > 0`
  - and `new_fit_or_near_fit_count >= 1`
- `low_recall_high_precision`
  - `new_unique_resume_count <= low_recall_threshold`
  - and `fit_rate >= high_precision_threshold`
- `broad_noise`
  - `new_unique_resume_count >= min_sample`
  - and `fit_or_near_fit_rate <= noise_threshold`
  - and `must_have_match_avg <= must_have_threshold`
- `drift_suspected`
  - promoted probe present
  - and `new_unique_resume_count > 0`
  - and `must_have_match_avg` drops materially versus exploit baseline
  - and off-intent reason count exceeds threshold

Thresholds should be configurable rather than baked into code comments.

### Term Outcome Labels

Term-level judgments should remain conservative in Phase 1. The system should not claim exact online marginal lift for each term. Exact term promotion should come from replay or probe evidence.

Recommended term-level labels:

- `safe_candidate`
- `existing_or_tried`
- `generic_or_filter_like`
- `insufficient_seed_support`
- `negative_support_too_high`
- `replay_promotable`
- `replay_rejectable`

Recommended per-term lineage fields:

- `term_family_id`
- `canonical_expression`
- `surface_forms`
- `candidate_term_type`
- `source_seed_resume_ids`
- `positive_seed_support_count`
- `negative_support_count`
- `tried_query_fingerprints`
- `reject_reasons`

`existing_or_tried` should be computed at the family level, not only the exact string level.

### Replay Units

Add replay rows specifically for second-lane comparison.

Each row should preserve:

- round-1 retrieval and scoring state
- the selected seed resumes
- candidate PRF terms considered
- PRF gate decision and reasons
- baseline second-lane behavior
- candidate second-lane behavior
- resulting query outcomes

This removes dependence on waiting for low-frequency rescue triggers.

### Replay Reproducibility Snapshot

Replay rows should persist the retrieval snapshot and version vector needed to explain differences.

Recommended fields:

- `retrieval_snapshot_id`
- `provider_request`
- `provider_response_resume_ids`
- `provider_response_raw_rank`
- `provider_response_raw_metadata`
- `dedupe_version`
- `scoring_model_version`
- `rerank_model_version`
- `query_plan_version`
- `prf_extractor_version`
- `prf_gate_version`
- `generic_explore_version`
- `company_rescue_policy_version`

Phase 1 can keep `provider_response_raw_metadata` minimal if storage pressure is high, but it must preserve enough provider snapshot state to distinguish PRF-policy effects from provider drift, scoring changes, or dedupe changes.

## PRF v1

Phase 1 does not introduce a new open-ended rewriter. It upgrades the existing `candidate_feedback` path into a bounded `PRF v1`.

### Why It Evolves From Candidate Feedback

The current `candidate_feedback` implementation already does the right kind of evidence gathering:

- it extracts surface terms from returned resumes
- it uses high-fit seeds instead of free-form model guesses
- it rejects generic and filter-like terms
- it records reasons for rejection

The current problem is feature placement, not core direction. The path is stuck in late rescue. Phase 1 promotes it into the preferred identity of the second lane.

The extractor and the policy should be separated cleanly:

- `candidate_feedback/extraction.py` becomes a shared evidence extractor
- `PRF v1` uses that extractor for second-lane policy
- late rescue may still reuse the extractor, but under a different lane identity and different policy rules

### PRF v1 Flow

1. Select a small number of high-quality seed resumes.
2. Optionally include a small negative sample to suppress noisy terms.
3. Extract candidate surface terms from internal resume evidence only.
4. Apply a strict PRF safety gate.
5. Promote exactly one PRF expression family.
6. Build a probe query using `anchor + promoted_prf_expression`.

### Seed Selection

Seeds should stay strict in Phase 1.

Recommended default conditions:

- `fit_bucket == "fit"`
- strong `overall_score`
- strong `must_have_match_score`
- acceptable `risk_score`

Phase 1 should prefer too few seeds over weak seeds.

For a round-`N` PRF probe, seeds must come only from retrieval and scoring state available before constructing that probe. The system must not use resumes first discovered by the same PRF query being evaluated.

### Candidate Term Sources

Allowed:

- resume-grounded evidence
- resume-grounded strengths
- matched requirement evidence
- short structured technical expressions from returned resumes

Disallowed:

- free-form LLM-generated terms
- company aliases
- web-derived entities
- raw notes language
- location, age, degree, and process terms

### Candidate Term Classification

Candidate expressions should be classified before PRF promotion.

Recommended classes:

- `skill`
- `technical_phrase`
- `product_or_platform`
- `company_entity`
- `location`
- `degree`
- `process`
- `generic`
- `unknown`

Phase 1 PRF allows by default:

- `skill`
- `technical_phrase`
- `product_or_platform`

Phase 1 PRF rejects by default:

- `company_entity`
- `location`
- `degree`
- `process`
- `generic`
- `unknown_high_risk`

### PRF Safety Gate

The second lane becomes `prf_probe` only when all of the following are true:

- there are enough high-quality seeds
- at least one candidate term survives extraction
- the candidate term is not classified as `company_entity`
- the candidate term is not filter-only or score-only
- the candidate term does not repeat an already tried family
- the candidate term does not show strong negative dominance

Additional soft checks may be added later, but Phase 1 should keep the gate deterministic and inspectable.

### Promotion Policy

Phase 1 promotes exactly one PRF expression family per probe.

This is intentional:

- cleaner attribution
- lower drift risk
- easier replay comparison
- easier failure analysis

The promoted unit may be a short technical phrase. It must not be misread as a single token requirement.

Phase 1 should explicitly not:

- promote multiple PRF expression families at once
- mix PRF and generic explore terms inside the same second-lane probe
- let the controller directly choose the promoted PRF term

## Second-Lane Fallback Order

The second lane should use this fixed order:

1. Attempt `prf_probe`
2. If PRF is unsafe or unavailable, use `generic_explore`
3. If quality remains poor after mainline rounds and rescue gates allow it, consider late rescue

This preserves one second lane while keeping its identity typed and replayable.

## Company Evidence Layer

### Explicit Target Company

Phase 1 defers explicit target company work.

Reason:

- current observed quality is poor
- alias maintenance cost is high
- named-entity ambiguity is structurally different from term-level PRF
- it would slow the retrieval flywheel milestone

Explicit company handling should not re-enter the mainline retrieval path in Phase 1.

### Web Company Discovery

Keep web company discovery, but redefine it as rescue-only company hypothesis generation.

Default role:

- diagnostics

Forbidden by default:

- direct query rewrite
- PRF term source
- second-lane takeover
- mainline scoring influence during retrieval-flywheel experiments
- mainline rerank influence during retrieval-flywheel experiments

Allowed late role:

- rescue-only candidate generation after mainline retrieval has failed or underperformed

### Rescue Ordering

Company rescue must come after mainline retrieval learning.

Recommended order:

1. `exploit`
2. `prf_probe if safe else generic_explore`
3. if quality is still low and PRF produced no safe or useful gain
4. if generic explore also produced no useful gain
5. if budget permits
6. then allow company rescue hypothesis generation

This keeps company evidence useful without contaminating second-lane attribution.

### Phase 1 Isolation Rule

During Phase 1 retrieval-flywheel experiments, company evidence is diagnostic-only by default.

That means company evidence must not affect:

- second-lane identity
- PRF term extraction
- PRF term promotion
- baseline-versus-candidate second-lane comparison
- mainline scoring or reranking unless explicitly enabled in a separate experiment block

Company rescue stays rescue-only and should be evaluated separately from PRF-versus-generic second-lane comparisons.

## Experiment Plan

The project is not yet online. Phase 1 should therefore be experiment-first, not rollout-first.

### Sequence

1. Add the data contract and artifacts.
2. Enable typed second lane directly in the experiment branch.
3. Run benchmark comparisons between:
   - baseline: `exploit + generic_explore`
   - candidate: `exploit + (prf_probe if safe else generic_explore)`
4. Run forced and shadow replay for cases where PRF would otherwise be too infrequent.
5. Keep company evidence diagnostic-only and outside mainline scoring or reranking during the primary comparison.
6. Keep company rescue gated and outside the mainline experiment comparison.

### Evaluation Layers

Policy evaluation:

- when PRF is allowed
- when PRF is rejected
- whether gate reasons make sense

Second-lane outcome evaluation:

- marginal gain versus generic explore
- duplicate-only rate
- zero-gain rate
- drift indicators

End-to-end evaluation:

- final judged quality
- high-fit candidate count
- cost
- number of rounds

## Acceptance Criteria

Phase 1 is complete when all of the following are true:

1. Each executed logical query has both `query_instance_id` and `query_fingerprint`.
2. Each newly added resume has `first-hit attribution`.
3. `query_resume_hits` preserves full lane visibility beyond first hit.
4. Each second-lane execution has an explicit `lane_type`.
5. The runtime can compare `prf_probe` and `generic_explore` with replay evidence.
6. `candidate_feedback` has been promoted into `PRF v1` and uses single-expression-family probe promotion.
7. The mainline second-lane budget starts at `70/30` and supports post-score zero-gain deprioritization.
8. Web company discovery remains rescue-only and does not participate in second-lane identity.
9. Every PRF rejection emits a replayable decision artifact with gate inputs and reject reasons.

Phase 1 explicitly does not require:

- a trained query rewriter
- explicit target company as a restored retrieval feature
- a fully productized company entity subsystem
- universal recall fixes across all job families

## Testing And Verification Expectations

Changes to this design should be backed by:

- unit tests for typed second-lane selection and PRF gating
- artifact schema tests for new query and attribution fields
- replay or benchmark tests showing baseline-versus-candidate comparisons
- tests for `query_resume_hits` and second-lane decision artifacts
- regression tests confirming company rescue does not leak into the mainline second lane

## Next Step

After this spec is accepted, the next artifact should be an implementation plan that breaks the work into:

- data contract changes
- typed second-lane runtime changes
- `PRF v1` refactor from current `candidate_feedback`
- experiment harness and replay updates
- company rescue boundary tightening
