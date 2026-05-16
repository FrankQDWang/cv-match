# Runtime Multi-Source Sourcing Contract Design

## Summary

SeekTalent needs a recruiter-grade multi-source sourcing runtime. The first target is CTS and Liepin running as parallel source lanes, feeding one shared candidate pool, merging likely duplicate people, selecting the freshest usable resume for each person, and returning a final Top 10.

Liepin differs from CTS because it has a two-stage provider flow:

1. Search returns ranked profile cards.
2. Runtime decides which cards are worth recommending for detail open within a budget.
3. A later approved detail lease allows the detail resume to be fetched.

The first implementation must keep the human-in-loop boundary ready, but does not build the manual card-review UI yet. Workbench can display recommendations and state; approval UI and manual card selection remain deferred platform work.

## Product Contract

Runtime owns:

- source planning for selected source kinds
- parallel full-run source lane scheduling
- source-lane terminal barriers
- source budget policy
- Liepin card filtering and detail recommendation ranking
- deterministic candidate identity merge
- canonical resume selection per identity
- source evidence preservation
- final scoring and Top 10 selection
- safe public source events and payloads

Workbench owns:

- source-run display state
- persisted source-run rows
- approved detail request, lease, budget, and audit state
- graph and notes rendering

Provider adapters and PI Agent own:

- bounded provider execution only
- card search
- detail fetch only when Runtime passes an approved detail lease
- raw provider artifact creation behind protected artifact refs

Provider adapters and PI Agent must not choose sources, approve detail opens, change budgets, finalize ranking, or expose raw resumes in public payloads.

## Contract Model Placement

Runtime contracts must avoid import cycles. `RunState` is defined in `src/seektalent/models.py`, and `src/seektalent/runtime/source_lanes.py` already imports `RunState`. Therefore any models that `RunState` stores directly must live in `models.py` or another dependency-light module imported by both `models.py` and `source_lanes.py`.

For this feature:

- `RuntimeCandidateIdentity` lives in `models.py`
- `RuntimeCanonicalResumeSelection` lives in `models.py`
- `RuntimeIdentitySignals` lives in `models.py`
- `RuntimeSourceCoverageSummary` lives in `models.py`
- `RuntimeFinalizationRevision` lives in `models.py`
- `RuntimeSourceEvidence` stays in `models.py`
- `RuntimeDetailEnrichmentResult` may live in `source_lanes.py` or another dependency-light runtime contract module because it is an API result wrapper, not stored `RunState`
- `RuntimeCandidateIdentityIndex` may live in `source_lanes.py` because it is merge logic, not stored state

`source_lanes.py` must not become a module that `models.py` imports.

## Current Code Facts

The current working tree already contains an initial source-lane implementation:

- `src/seektalent/runtime/source_lanes.py` defines source-lane plan/result/event/detail recommendation contracts and merge helpers.
- `src/seektalent/runtime/orchestrator.py` can run full source lanes and Workbench single source lanes.
- `src/seektalent/providers/liepin/runtime_lane.py` adapts Liepin search results into runtime lane results and detail recommendations.
- `src/seektalent_ui/runtime_bridge.py` routes Workbench Liepin card source runs through Runtime.
- `src/seektalent/evaluation.py` defines final shortlist size as `TOP_K = 10`.

The current implementation is not sufficient for this product contract:

- full-run source lanes are currently executed in source-plan order, not as true parallel lanes
- merge is still primarily keyed by `resume_id`, so CTS and Liepin records for the same person can remain split or overwrite the wrong surface
- source evidence is preserved, but not yet centered on a stable candidate identity
- identity ids are not yet defined as order-independent canonical ids with alias tracking
- identity merge has no typed `RuntimeIdentitySignals` input, so implementation would be tempted to parse raw payloads or display text
- canonical resume selection does not yet prefer the freshest and most complete resume across sources
- Liepin detail recommendation uses a simple matched-term score instead of provider-rank-first card policy plus detail-open budget allocation
- CTS multi-source lane behavior must be capped to the product budget of one page with page size 10
- current public payload safety relies partly on string sanitization; this feature must move new public fields to enum and allowlist serializers

## Non-Goals

This spec does not build:

- a card-review or manual approval UI
- manual card selection before detail open
- automatic source strategy optimization
- lane health, cost, or quality dashboards
- a generic plugin system
- A2A transport
- DokoBot action execution without a trusted action manifest, capability probe, conformance tests, and audit trail

Those items should be documented as deferred follow-ups, not implemented inside this feature.

## Source Budget Policy

Runtime must create an explicit source budget policy for each run.

The first version uses these defaults:

- CTS: one page, page size 10
- Liepin cards: one search page with a configured card page size
- Liepin details: a configured max detail-open recommendation count per run
- final shortlist: Top 10

The budget policy is runtime-owned. Workbench may display budget state and persist approved detail leases, but it must not silently change the runtime budget for a lane.

Public budget payloads may include counts and reason codes only. They must not include provider credentials, approval secrets, cookies, raw profile payloads, or raw resumes.

## Frozen Runtime Contracts

Before lane orchestration changes, the implementation must freeze these minimal contracts:

- `RuntimeSourceBudgetPolicy`
- `RuntimeIdentitySignals`
- `RuntimeCandidateIdentity`
- `RuntimeIdentityConflict`
- `RuntimeCanonicalResumeSelection`
- `RuntimeSourceEvidence`
- `RuntimeDetailRecommendation`
- `RuntimeApprovedDetailLease`
- `RuntimeSourceLaneEvent`
- `RuntimeSourceLaneResult`
- `RuntimeSourceCoverageSummary`
- `RuntimeFinalizationRevision`
- `RuntimeDetailEnrichmentResult`

These contracts must expose explicit `to_public_payload()` methods. Public serializers must be allowlists and must not call `asdict()` or serialize model internals directly.

`RuntimeIdentitySignals` is the only input the identity index may use for person matching. It should contain safe normalized fields:

- normalized name
- masked-name boolean
- normalized current company
- normalized current title
- normalized school names
- work chronology fingerprints
- provider candidate key hash
- protected contact hashes when available

`RuntimeCandidateIdentity` ids must be stable independent of lane completion order. Runtime should derive canonical identity ids from the strongest available non-raw key in this priority order:

1. protected contact hash
2. same-provider candidate key
3. provider plus candidate key hash
4. normalized name plus company plus title plus distinctive school or chronology hash
5. deterministic minimum evidence id set when no stronger key exists

When later evidence proves two identities are the same person, Runtime must preserve an alias map from old identity ids to the canonical identity id. Public payloads should expose canonical identity ids only, while internal merge diagnostics may retain alias records.

`RuntimeSourceEvidence` must carry enough structured information for merge, canonical selection, notes, graph, and audit without inspecting raw provider payloads:

- evidence id
- source
- provider
- source plan id
- source lane run id
- candidate resume id
- provider candidate key hash
- protected contact hashes
- evidence level
- provider rank when available
- collected timestamp
- safe summary ref for card or detail evidence, using the existing `safe_summary_ref` field name
- protected artifact ref
- safe reason codes

`RuntimeApprovedDetailLease` must bind approval to the exact detail recommendation and source evidence:

- lease id or lease ref
- runtime run id
- source plan id
- source lane run id
- source kind
- recommendation id
- source evidence id
- candidate resume id
- provider candidate key hash
- approved actor hash
- approved timestamp
- expiry timestamp
- budget policy hash
- lease signature ref

Runtime must reject a detail lane if any lease binding mismatches the request, source, recommendation, evidence, candidate, provider candidate key hash, expiry, or budget policy.

## Parallel Source Lanes

A full Runtime run with `source_kinds=("cts", "liepin")` must start CTS and Liepin as independent lane-local executions. Each lane returns a `RuntimeSourceLaneResult` delta. Runtime waits for selected lanes to reach a terminal state before scoring and finalization.

Concurrency should use Python 3.12 standard-library structured concurrency. Runtime should create a small safe runner around each lane:

1. `run_source_lane_safely(lane)` invokes the source-specific lane.
2. It catches lane-isolated provider errors and converts them into a failed `RuntimeSourceLaneResult` with safe reason codes.
3. `_run_full_source_lanes()` starts those safe runners concurrently, preferably with `asyncio.TaskGroup`.
4. After the TaskGroup exits, Runtime reads each task result and merges only `RuntimeSourceLaneResult` objects.

Provider, network, login, session, rate-limit, and malformed-provider-payload errors may become failed or partial lane results. Runtime invariant violations, programmer errors, schema corruption, and merge corruption should fail the whole run unless a specific error type is deliberately marked lane-isolated. Public payloads must contain safe reason codes only.

Provider exceptions must not escape a lane task and cancel unrelated source lanes. `CancelledError` from user cancellation may still propagate as cancellation.

Async tasks only provide useful parallelism when lane provider calls yield control. The implementation must test that both selected lanes reach their provider-call barrier before either completes. If a lane calls blocking synchronous provider code, the lane must move that call behind an async adapter or `asyncio.to_thread()` before claiming true parallel behavior.

Terminal lane statuses are:

- `completed`
- `partial`
- `blocked`
- `failed`
- `cancelled`

Blocked or failed lanes do not prevent finalization when at least one selected source produced candidates. Runtime must mark the finalization scope as degraded and record source categories precisely:

- `blocked_source_kinds`
- `failed_source_kinds`
- `partial_source_kinds`
- `empty_source_kinds`
- `missing_source_kinds`

`missing_source_kinds` is only for a selected source with no terminal lane result. A completed source with zero candidates is an empty source, not a missing source.

Workbench single-lane source runs remain non-finalizing. They may execute one lane and persist lane state, but they must not produce the full final Top 10 by themselves. `run_source_lane_async(...)` returns a `RuntimeSourceLaneResult` delta only; it must not grow a finalization revision field.

## CTS Lane Contract

CTS is the baseline source. In the multi-source runtime contract, CTS contributes one source lane:

- one page
- page size 10
- lane-local state
- no provider-specific detail approval stage
- source evidence for every returned candidate

The multi-source CTS lane must not call the full multi-round `_run_rounds()` path. It should use a dedicated single-page path built on the existing retrieval service. The cap must be enforced at the provider request boundary, not only by an outer runtime argument. The CTS source lane must issue exactly one provider request with page `1`, page size `10`, target new `10`, and no refill pagination for this lane. CTS-only CLI behavior may continue using the legacy full `_run_rounds()` path.

CTS-only CLI behavior must remain compatible with existing product behavior unless explicitly invoked through the multi-source runtime contract.

## Liepin Card Policy

Liepin search returns provider-ranked cards. Runtime should use provider ranking as the primary ordering signal because the provider search engine is already applying relevance, recency, and marketplace signals that are not fully visible in the card.

Runtime may filter out cards that are clearly not worth opening:

- hard location mismatch when the job has a hard location constraint
- obviously wrong current title, target role, or function
- materially insufficient required years of experience when stated as a hard constraint
- materially insufficient required education when stated as a hard constraint
- excluded company, school, industry, or keyword
- stale or irrelevant work history that does not match the search intent

Runtime should not overfit the card text. When a card passes hard filters, provider rank remains the primary ordering signal. Soft card value only breaks ties or pushes down weak matches; it should not reorder a provider rank 1 card below a provider rank 8 card unless the higher-ranked card has a clear hard-negative reason.

Each detail recommendation must include structured, public-safe fields:

- stable recommendation id
- source evidence id
- source candidate resume id
- provider candidate key hash
- provider rank
- card policy rank
- hard-filter status
- safe reason codes
- budget reason code
- safe summary ref when available, using the existing `safe_summary_ref` field name

The card lane must not fetch detail resumes directly. It only emits detail recommendations.

## Detail-Open Boundary

Detail open is a two-stage boundary:

1. Runtime emits detail recommendations from card evidence.
2. Workbench store owns approval, lease, budget, and audit.

Runtime may execute a Liepin detail lane only from an approved detail lease. The detail lane must reject missing, expired, over-budget, wrong-source, or wrong-candidate leases. The Liepin provider adapter remains the final enforcement layer.

The first implementation must keep this boundary in contracts and tests, while leaving the actual human approval UI for later.

The Liepin detail lane itself remains delta-only. A separate Runtime detail-enrichment entrypoint, for example `apply_approved_detail_lane_to_run_async(...)`, must consume an existing finalized runtime run plus an approved detail lease, run the Liepin detail lane, merge its `RuntimeSourceLaneResult` delta into the existing run state or run artifact state, rerun canonical resume selection, rescore affected identities, and emit a `RuntimeDetailEnrichmentResult` with a new `RuntimeFinalizationRevision`.

When detail enrichment succeeds, Runtime must treat the result as a new finalization revision for the same run. Workbench should show the latest revision while preserving enough history to explain that an earlier revision was card-only. If the referenced finalized run cannot be loaded, the lease references the wrong runtime run, or the base finalization revision is stale, Runtime must reject the enrichment instead of producing an ungrounded Top 10.

## Candidate Identity Merge

Runtime must merge source outputs by likely person identity, not just by resume id.

The merge model must preserve all evidence while choosing one display/canonical resume for scoring and final output.

Required concepts:

- `RuntimeCandidateIdentity`: stable identity record for a likely person
- `RuntimeSourceEvidence`: source evidence attached to an identity
- `RuntimeCanonicalResumeSelection`: deterministic choice of the best resume for the identity
- `RuntimeIdentitySignals`: safe normalized signals used by merge logic
- `RuntimeIdentityConflict`: safe conflict record for ambiguous possible duplicates

Identity matching should use conservative rules:

- exact provider candidate key within the same provider is strong evidence
- exact protected contact hashes may be strong evidence when available
- exact name plus current company plus current title is medium evidence
- name plus school plus overlapping work chronology is medium evidence
- name-only or broad keyword overlap is weak evidence and must not auto-merge
- masked names such as `王**`, `W**`, or other partially hidden provider names must not be used as strong or medium identity evidence by themselves

Ambiguous matches must remain separate identities and record a safe conflict reason. Runtime should prefer false negatives over false positive merges because merging two different people corrupts recruiter output.

Masked Liepin cards need special care. A masked name plus matching company/title is still not enough to merge with a CTS resume. Auto-merge requires stronger corroboration, such as the same provider candidate key, protected contact hash, distinctive school plus overlapping work chronology, or a later approved detail resume that exposes enough safe normalized identity fields.

Masked-name detection must cover common card patterns, including `王**`, `*明`, `王某`, `王女士`, `W**`, `Wang**`, `候选人123`, `匿名`, `-`, and empty strings.

## Canonical Resume Selection

For each candidate identity, Runtime must select a canonical resume deterministically from normalized resume data:

1. detail evidence beats card-only evidence
2. newer resume update timestamp beats older timestamp
3. current work marked as ongoing beats stale current-job data
4. more complete normalized resume beats sparse resume
5. source trust and provider rank break remaining ties

Canonical selection must not delete or overwrite source evidence. CTS evidence, Liepin card evidence, and Liepin detail evidence for the same identity must remain available to scoring, notes, graph rendering, and audit.

## Unified Scoring And Final Top 10

After all selected full-run lanes reach terminal state, Runtime merges lane deltas into identity records, selects canonical resumes, scores identities once, and returns Top 10 as `RuntimeFinalizationRevision(revision=1)`.

The scoring context must be multi-source aware:

- a candidate may have evidence from CTS, Liepin card, and Liepin detail
- detail-enriched resumes should improve available context
- card-only candidates may still rank when they are strong enough
- missing or blocked source lanes must be reflected as coverage gaps, not silently hidden

Final output remains 10 candidates unless fewer identities are available. Later approved detail enrichment may produce revision `2`, `3`, and so on for the same run after detail evidence is applied.

## Workbench Graph And Notes Contract

Workbench must render the B-scope multi-source state from Runtime public payloads without becoming a second source orchestrator.

The strategy graph needs these source branches and states:

- one branch node per selected source, at minimum `CTS` and `Liepin`
- lane state: `pending`, `running`, `completed`, `partial`, `blocked`, `failed`, `cancelled`
- coverage state: `complete`, `degraded`, or `empty`
- Liepin card state: cards scanned, cards filtered, detail recommendations emitted
- Liepin detail state: detail pending approval, leased, completed, or blocked
- merge state: identity merge count, ambiguous duplicate count, canonical resume selected

Run notes must include safe multi-source context:

- selected sources and final coverage status
- which sources contributed evidence to a candidate
- whether the candidate is card-only or detail-enriched
- whether a final Top 10 result is degraded because one selected source blocked or failed

Notes and graph must consume allowlisted public payloads only. They must not resolve protected artifact contents or display raw provider payloads.

Workbench persistence must distinguish immutable event history from latest display state:

- event log: append or idempotent insert by runtime run id, source lane run id, attempt, and event sequence
- latest state: upsert only when a newer attempt or event sequence advances the lane state

An out-of-order older event must not move the graph backward, but it may still be kept in the event log for audit.

## Public Events And Payload Safety

All public payloads must use allowlisted serializers. Public paths include CLI JSON, Workbench graph state, Workbench notes, source-run rows, logs, and events.

Forbidden in public payloads:

- provider API keys
- provider tokens
- browser cookies
- approval secrets
- raw resumes
- raw HTML
- raw provider responses
- unredacted exception messages
- protected artifact contents

New public reason fields must be enum or allowlist values. Free-form text such as raw exception messages, provider diagnostics, raw card summaries, and generated prose may not enter public payloads directly. If a non-enum string reaches a public serializer, it must be replaced with `unknown_reason` or a redacted artifact ref, not passed through after regex cleanup.

Artifact refs in public payloads must be scheme-allowlisted. Public graph and notes may reference safe summary artifacts but must not include protected artifact contents.

Runtime source events must include stable correlation fields:

- schema version
- runtime run id
- source plan id
- source lane run id
- source kind
- attempt
- event sequence
- event type
- safe counts
- safe reason codes
- safe artifact refs

The event type enum must include explicit source lane terminal events for completed, blocked, partial, failed, and cancelled states. Failed lanes should not be represented as blocked lanes.

Events may arrive out of order in Workbench. Workbench persistence must upsert by stable ids and avoid graph state moving backward.

## Acceptance Criteria

- CTS-only default behavior remains available.
- A full run with CTS and Liepin starts both selected source lanes in parallel.
- Full-run parallelism uses a safe source-lane runner with Python standard-library structured concurrency; a failed Liepin lane must not cancel a successful CTS lane.
- Full-run parallelism proves both selected lane provider calls are entered before either lane is released.
- Full-run finalization waits for selected lanes to reach terminal state.
- If one selected source blocks and another returns candidates, Runtime finalizes with degraded source coverage.
- Coverage payloads distinguish blocked, failed, partial, empty, and missing source kinds.
- CTS multi-source lane performs exactly one provider request with page 1 and page size 10.
- Liepin card lane emits detail recommendations but does not fetch detail resumes.
- Liepin card recommendation ranking is provider-rank-first after hard filters.
- Liepin detail recommendations respect the per-run detail-open budget.
- Runtime can consume an approved Liepin detail lease through a separate detail lane.
- The separate detail lane remains a `RuntimeSourceLaneResult` delta and does not itself carry `finalization_revision`.
- Approved detail enrichment uses an explicit Runtime entrypoint that consumes a base finalized run and returns a `RuntimeDetailEnrichmentResult`.
- Approved Liepin detail leases bind source, recommendation, evidence, candidate, provider key hash, actor, expiry, and budget policy.
- CTS and Liepin records for the same person merge into one identity when conservative identity evidence is strong enough.
- Identity ids are stable regardless of lane completion order, and alias records preserve identity merges.
- Masked Liepin names do not auto-merge with CTS records based only on company/title similarity.
- Ambiguous possible duplicates stay separate and record safe conflict reasons.
- Canonical resume selection prefers detail, normalized resume freshness, completeness, and source trust deterministically.
- Source evidence is never collapsed or overwritten by canonical resume selection.
- Final shortlist returns Top 10 identities across all selected sources.
- Approved detail enrichment creates a new finalization revision and refreshes canonical selection, scoring, and Top 10 only when the referenced base run and lease bindings are valid.
- Run notes and graph context include explicit CTS/Liepin branch state, coverage status, card/detail state, and multi-source evidence context.
- Public serializers do not leak provider credentials, session secrets, cookies, approval secrets, raw resumes, raw HTML, raw exception text, or raw provider payloads.

## Deferred Follow-Ups

Record these outside the current implementation scope:

- human card-review UI
- manual detail-open approval UI
- manual source budget editing UI
- lane health, cost, and marginal quality metrics
- automatic source strategy optimization
- broader source capability descriptor
- offline entity-merge evaluation set
- trace context alignment for future out-of-process source lanes
- trusted DokoBot action manifest and conformance suite
- future A2A bridge if PI Agent becomes out-of-process with independent lifecycle and identity
