# Context Authority and Visibility Design

## Purpose

Fix the context-passing and authority-boundary issues found in the retrieval loop.

The target behavior is simple:

- Reflection advises.
- Controller decides.
- Runtime validates, executes, and audits.
- Every LLM sees the context needed for its own job.

This design covers the full repair scope discussed on 2026-04-24.

## Current Problems

The current implementation has two classes of issues.

First, authority is blurred. Reflection output is treated as advice in the prompts, but runtime currently applies reflection keyword advice directly to `query_term_pool.active` and `priority`. That makes reflection a state mutator, not just a critic.

Second, some model-facing prompts do not include fields that their system prompts or context models imply are visible. Examples:

- `ControllerContext` contains `latest_reflection_keyword_advice` and `latest_reflection_filter_advice`, but the controller prompt only renders a compressed previous reflection summary.
- `ReflectionContext` contains full JD, notes, and `RequirementSheet`, but the reflection prompt does not render them.
- `ScoringPolicy` contains full hard constraints and preferences, but the scoring prompt only renders hard locations plus a few top-level fields.
- Repair prompts can receive fuller JSON context than the original model-facing prompt.

## Authority Model

`query_term_pool` remains, but its role is a runtime-managed term registry.

Allowed writers:

- Requirements normalization and query compilation create the initial pool.
- Runtime rescue lanes can inject new evidence-backed terms, such as candidate feedback terms or web-discovered company terms.
- Runtime may record that a controller-selected reserve term has been used or adopted.

Not allowed:

- Reflection must not directly mutate `query_term_pool.active`, `priority`, or any other pool state.

Reflection can only produce:

- `keyword_advice`
- `filter_advice`
- `suggest_stop`
- `suggested_stop_reason`
- `reflection_rationale`
- `reflection_summary`

Controller owns the next-round retrieval decision. It may accept, partly accept, or reject reflection advice. Its `response_to_reflection` is the audit surface for that decision.

Runtime owns validation and execution. It must reject unknown, blocked, duplicate-family, invalid-anchor, or over-budget query terms.

## Term Selection Rules

Active admitted terms remain normally selectable.

Inactive admitted terms are selectable only when backed by visible evidence:

- The previous reflection suggested activating or keeping the term.
- A runtime rescue lane explicitly injected or forced the term.

Even then, all existing rules still apply:

- Terms must exist in the compiled pool.
- Terms must have `queryability=admitted`.
- One and only one role anchor is required unless a runtime rescue path explicitly allows anchor-only.
- Families must not repeat, except for existing company-term handling.
- Round 1 uses one non-anchor term; later rounds use one or two non-anchor terms.

Reflection-suggested inactive terms are not activated automatically. They become usable only if the controller selects them or explicitly adopts them.

## Controller Context

The controller prompt should show the decision inputs it needs, without dumping full JSON.

Add or expand these sections:

- `REFLECTION ADVICE`: keyword advice, filter advice, stop advice, summary, rationale.
- `TERM BANK`: all admitted terms, including active/reserve status, family, role, priority, source, and tried status.
- `STRUCTURED CONSTRAINTS`: hard constraints and preferences from `RequirementSheet`.
- `STOP GUIDANCE`: include fit count, strong-fit count, high-risk fit count, productive round count, zero-gain round count, quality gate status, broadening status.
- `LATEST SEARCH OBSERVATION`: include exhausted reason, adapter notes, city summaries, and new candidate summaries.

Controller system prompt changes:

- Say reflection is advisory.
- Require explicit accept, partial accept, or reject language in `response_to_reflection`.
- Say inactive/reserve terms require visible reflection or rescue evidence.
- Refer to provided prompt sections, not an implied full `CONTROLLER_CONTEXT` JSON.

## Reflection Context

The reflection prompt should show the job requirements and the current term bank.

Add these sections:

- `REQUIREMENTS`: role title, summary, must-have capabilities, preferred capabilities, hard constraints, preferences, JD, notes.
- `TERM BANK`: current runtime term pool, not only the initial pool; include active status, queryability, role, family, priority, source, and tried status.
- Keep existing round result, current query, search attempts, sent query history, top candidates, dropped candidates, failures, and untried admitted terms.

Reflection system prompt changes:

- Keep the critic/advisor role.
- State that advice does not mutate the term pool.
- State that filter advice is field-level advice only, not direct filter execution.
- State that next-round query ownership remains with controller/runtime.

## Scoring Context

The scoring prompt should include the full structured scoring policy needed to identify hard conflicts.

Add to `SCORING POLICY`:

- locations
- school names
- degree requirement
- school type requirement
- experience requirement
- gender requirement
- age requirement
- company names
- preferred locations
- preferred companies
- preferred domains
- preferred backgrounds
- preferred query terms
- runtime-only constraints for the current retrieval plan when present

The scorer still sees only one resume and must not compare candidates.

## Finalizer Context

Finalizer remains presentation-only and must not change candidate membership or ranking.

Expand each ranked candidate line with existing scored facts:

- matched must-haves
- matched preferences
- strengths
- weaknesses
- risk flags

Runtime continues to materialize final structured fields from scored candidates, not from finalizer text.

## Repair Prompts

Repair prompts should not gain broader decision context than the original call.

Controller repair should receive:

- repair reason
- original rendered controller prompt
- broken decision

Reflection repair should receive:

- repair reason
- original rendered reflection prompt
- broken draft

Full JSON context can remain in artifacts for debugging, but should not be used as model-facing repair input unless it is also visible in the original prompt.

## Audit Artifacts

Keep existing context and call artifacts.

Add a lightweight per-round audit object when previous reflection exists:

- `suggested_activate_terms`
- `suggested_keep_terms`
- `suggested_deprioritize_terms`
- `suggested_drop_terms`
- `suggested_filter_fields`
- `accepted_terms`
- `ignored_terms`
- `accepted_filter_fields`
- `ignored_filter_fields`
- `controller_response`

This object records what the controller actually adopted. It is not a second decision engine.

## Testing

Add or update tests in these groups.

Prompt visibility:

- Controller prompt includes raw reflection keyword/filter/stop advice.
- Controller prompt includes structured hard constraints and preferences.
- Reflection prompt includes JD, notes, `RequirementSheet`, and current term bank.
- Scoring prompt includes full hard constraints, preferences, and runtime-only constraints when present.
- Finalizer prompt includes matched signals, strengths, weaknesses, and risk flags.

Authority boundary:

- Reflection no longer changes `query_term_pool.active` or `priority`.
- Reflection advice history is still recorded.
- The next controller context still includes previous reflection advice.

Controller adoption:

- Active admitted terms remain valid.
- Inactive admitted terms fail unless backed by previous reflection or rescue evidence.
- Reflection-backed inactive admitted terms pass validation.
- Unknown and blocked terms still fail.
- `response_to_reflection` remains required when previous reflection exists.

Audit:

- Round artifacts show previous advice, controller response, and actual query terms.
- If the adoption audit object is added, accepted and ignored fields are deterministic.

Regression:

- Keep existing contract tests for controller, reflection, scoring, finalizer, context builder, runtime state flow, and filter projection.

## Implementation Order

1. Stop applying reflection keyword advice directly to `query_term_pool`.
2. Update controller query validation to allow only evidence-backed inactive admitted terms.
3. Add controller reflection-adoption audit.
4. Expand controller prompt and system prompt.
5. Expand reflection prompt and system prompt.
6. Expand scoring prompt.
7. Expand finalizer prompt.
8. Align repair prompts with original rendered prompt visibility.
9. Update docs and tests.

## Non-Goals

- Do not replace readable prompts with full JSON context dumps.
- Do not create a heavy prompt-facing model layer unless later maintenance requires it.
- Do not let reflection choose the next query.
- Do not let finalizer change ranking or candidate membership.
- Do not add fallback model chains or broad recovery behavior.
