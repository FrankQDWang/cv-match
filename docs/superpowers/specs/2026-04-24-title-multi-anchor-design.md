# Title Multi-Anchor Retrieval Design

## Purpose

Fix the retrieval failures caused by collapsing job titles into a single search anchor.

The target behavior is:

- `title` remains the highest-priority source.
- A title may yield one or two searchable title anchors.
- Query assembly stays small and deterministic.
- JD, notes, and company context can support title interpretation, but they do not outrank title.

This design also fixes the closely related over-strict rules that suppress useful domain terms during early retrieval.

## Current Problems

The current retrieval path is too narrow in four connected ways.

First, `RequirementExtractionDraft` only allows one `title_anchor_term`. This forces titles that contain two important signals to collapse into one anchor.

Second, the compiler produces only one admitted role anchor from title cleanup. The runtime and query planner then require exactly one anchor in each query.

Third, notes terms are demoted too aggressively. Sourcer-supplied domain hints such as `人工耳蜗` or `AI投研` can be blocked from early retrieval even when they are better search terms than generic JD vocabulary.

Fourth, the active non-anchor window is too small. High-signal domain terms can be pushed behind generic technology terms and never reach the query planner.

These issues explain the recent failures:

- A generic title such as `高级产品组经理` loses the medical-device domain signal needed for retrieval.
- A title such as `AI主观投资团队牵头人` is reduced toward generic `AI` or `大模型` language and misses the `投研` direction.

## Goals

- Preserve `title` as the primary authority for retrieval direction.
- Allow `title` to express one or two high-value searchable anchors.
- Keep round-one query size at two terms.
- Let supporting domain terms enter retrieval when they are strong and explicit.
- Keep runtime validation deterministic and auditable.
- Make prompt guidance and runtime rules align instead of fighting each other.

## Non-Goals

- Do not turn retrieval into an open-ended agent loop.
- Do not allow arbitrary numbers of anchors.
- Do not remove `blocked`, `score_only`, or `filter_only`.
- Do not let JD, notes, or company context override the main title direction.
- Do not expand normal query size past two terms in round one.
- Do not redesign scoring, reflection, finalization, or CTS integration outside the narrow changes needed here.

## Anchor Model

Replace the single-title-anchor model with a controlled two-level title anchor model.

New behavior:

- `title_anchor_terms` has length `1..2`.
- Exactly one term is the `primary_role_anchor`.
- Zero or one term may be the `secondary_title_anchor`.
- A title with only one clear retrieval signal stays single-anchor.
- A second title anchor is allowed only when it materially changes retrieval direction.

Examples:

- `AI主观投资团队牵头人`
  - `primary_role_anchor`: `AI`
  - `secondary_title_anchor`: `投研`
- `搜索/推荐算法工程师`
  - either one combined anchor if CTS behavior prefers the phrase
  - or `搜索` plus `推荐` if split anchors perform better and remain stable
- `高级产品组经理`
  - usually only one title anchor from title itself
  - domain support such as `人工耳蜗` should not be faked as a title anchor unless title explicitly carries it

## Source Hierarchy

The source hierarchy must stay explicit.

Authority order:

1. title
2. JD
3. sourcer notes
4. company context

Meaning:

- Title decides the main retrieval direction.
- JD, notes, and company context help interpret ambiguous titles and provide supporting domain terms.
- Non-title sources may provide the strongest domain term when title has only one anchor.
- Non-title sources may not replace the `primary_role_anchor`.

## Data Model Changes

`RequirementExtractionDraft`

- replace `title_anchor_term: str`
- with `title_anchor_terms: list[str]`
- require length `1..2`
- add `title_anchor_rationale: str`

`RequirementSheet`

- replace `title_anchor_term`
- with `title_anchor_terms`
- keep the final normalized title-anchor list available to runtime and prompt builders

`QueryRetrievalRole`

- replace the single `role_anchor` bucket with:
  - `primary_role_anchor`
  - `secondary_title_anchor`
  - `domain_context`
  - `framework_tool`
  - `filter_only`
  - `score_only`

Compatibility rule:

- existing code paths that ask “is this an anchor” should treat both title-anchor roles as anchors
- query structure rules still require exactly one primary anchor

## Compiler Rules

The compiler remains the deterministic gatekeeper.

Responsibilities:

- clean and normalize title anchors
- classify title anchors into primary or secondary
- reject fake second anchors made from seniority, org labels, or vague modifiers
- classify JD, notes, and company-context terms into admitted or non-admitted support terms

Secondary-title-anchor admission rules:

- must come from explicit title semantics, not only JD text
- must change candidate search direction in a meaningful way
- must be resume-searchable language
- must not be a filter, soft skill, org label, or generic modifier

Strongest-domain-term admission rules:

- may come from JD, notes, or company context
- must narrow domain better than generic capability words
- must remain below title anchors in authority
- should beat broad technology terms when domain fit is the main differentiator

Examples:

- `人工耳蜗` should outrank generic `产品管理`
- `投研` should outrank generic `大模型`
- `基金` or `证券` may outrank `Python` for AI investment-research roles

## Query Assembly

Round-one queries stay small and deterministic.

Round 1:

- if title has two anchors:
  - use `primary_role_anchor + secondary_title_anchor`
- if title has one anchor:
  - use `primary_role_anchor + strongest_domain_term`

Later rounds:

- always keep exactly one `primary_role_anchor`
- allow one or two admitted non-primary terms
- `secondary_title_anchor` can remain selectable, but it is not mandatory in every later round

Query limits remain:

- round one: exactly two terms unless a runtime rescue lane explicitly enables anchor-only
- later rounds: one primary anchor plus one or two admitted support terms
- no duplicate families in a single query

This preserves the current deterministic search budget while fixing the single-anchor collapse.

## Notes and Domain-Term Relaxation

The current notes handling is too strict.

New rule:

- notes terms are not automatically `score_only`
- sourcer-supplied notes terms may be `admitted` when they are explicit, search-friendly, and domain-narrowing
- abstract, filter-only, or vague notes terms remain non-admitted

Examples of notes terms that should be able to enter retrieval:

- `人工耳蜗`
- `AI投研`
- `金融AI`

Examples that should still stay out:

- `沟通能力`
- `高频沟通`
- `985`
- `抗压`

## Active Window Changes

The fixed admitted non-anchor window should be relaxed, but not removed.

New rule:

- keep a small bounded active set
- expand the active admitted non-primary term window from a brittle fixed `4` toward a slightly wider cap such as `6`
- rank support terms so domain-defining words are not automatically pushed behind generic tech words

The exact cap can stay configurable in code, but the design intent is stable:

- preserve determinism
- reduce suppression of high-value domain terms
- avoid large uncontrolled term banks in query selection

## Runtime Determinism

Runtime owns the final hard boundary.

Runtime validation rules:

- `title_anchor_terms` length must be `1..2`
- there must be exactly one `primary_role_anchor`
- there may be zero or one `secondary_title_anchor`
- a second title anchor must not share the same family as the primary anchor
- round-one query uses two terms unless explicitly rescued into anchor-only mode
- the second round-one term is chosen by the query-assembly rules above
- non-title terms cannot replace the primary anchor
- blocked, filter-only, and score-only terms cannot enter keyword query execution

This keeps the system auditable even when prompts become more expressive.

## Prompt Integration

Prompt changes should align with runtime, not compete with it.

Rendered task prompts should ask the model to discover candidate anchors and support terms, but runtime must remain the final authority on what becomes queryable.

Requirements prompt changes:

- state that title is the highest-priority retrieval source
- allow one or two title anchors
- say the second title anchor is optional, not required
- require the second title anchor only when title itself carries a second high-value retrieval signal
- ask for a short `title_anchor_rationale`
- tell the model to use JD, notes, and company context to disambiguate title meaning, not to invent fake title anchors

Controller prompt changes:

- explain that round one should prefer title-title pairing when two title anchors exist
- otherwise use title plus strongest domain term
- reinforce that exactly one primary anchor is required in every normal query

Reflection prompt changes:

- treat title anchors as stable retrieval direction signals
- allow reflection to recommend stronger domain support terms
- do not let reflection replace the primary title anchor

## Diagnostic Labels

Add lightweight labels so failures can be explained quickly.

Suggested labels:

- `title_multi_anchor_collapsed`
- `strong_domain_term_suppressed`
- `notes_term_suppressed`

These labels are for audit and replay analysis only. They are not a second decision engine.

## Testing

Add or update tests in these groups.

Requirement extraction:

- one-title-anchor titles remain valid
- two-signal titles can emit two title anchors
- second title anchor is optional, not forced

Compiler:

- primary and secondary title anchors are classified correctly
- fake second anchors from seniority or org labels are rejected
- notes terms can be admitted when they are explicit domain terms
- blocked and filter-only notes terms stay out

Query planning:

- round one uses primary plus secondary when two title anchors exist
- round one falls back to primary plus strongest domain term when only one title anchor exists
- later rounds still require exactly one primary anchor
- duplicate-family and blocked-term protections still hold

Runtime and prompt integration:

- prompt text matches the new title-anchor rules
- runtime rejects invalid anchor counts and invalid role combinations
- audit labels are deterministic for replayed failure cases

## Implementation Order

1. Change requirement draft and normalized sheet title-anchor fields.
2. Extend retrieval-role enums and anchor classification logic.
3. Update the compiler to emit one or two title anchors.
4. Relax notes-term admission and widen the active support-term window.
5. Update query planning for primary-plus-secondary or primary-plus-domain round-one assembly.
6. Update requirements, controller, and reflection prompts.
7. Add diagnostic labels.
8. Update targeted tests and benchmark replay coverage.

## Success Criteria

The design is successful when:

- titles with two real search signals no longer collapse into one anchor
- titles with one signal stay simple
- domain-defining support terms survive early retrieval more often
- sourcer-supplied domain notes can help retrieval when they are explicit and searchable
- runtime remains deterministic and query size stays bounded
- failure analysis can separate title-collapse problems from domain-term suppression problems
