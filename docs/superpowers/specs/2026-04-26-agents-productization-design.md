# AGENTS.md Productization Design

## Goal

Rewrite `AGENTS.md` so it still preserves the repository's Python-first, anti-ceremony, anti-overengineering character, but no longer assumes the codebase is only an early experimental playground.

The new file should be written primarily for AI coding agents. It should guide them toward productization-phase decisions in a repository that is expected to ship within a month and continue growing in size.

The rewrite should not become a generic enterprise handbook. It should remain opinionated, concise, and operational.

## Core Shift

The old document assumes:

- local experimental playground
- fastest iteration above all else
- low code volume as a persistent design target
- mostly local simplicity as the dominant decision criterion

The new document should assume:

- active productization
- increasing repository scale
- multiple modules and boundaries that need to remain understandable
- the need to preserve clarity while reducing future coordination and maintenance cost

The new governing stance should be:

`mainstream Python clarity with scale-aware pragmatic minimalism`

That means:

- preserve the preference for direct code over ceremony
- preserve the rejection of premature abstraction
- allow necessary abstraction when it improves module boundaries, API stability, or collaboration cost
- distinguish internal fail-fast logic from external boundary validation

## Audience

Primary audience:

- AI coding agents working directly in this repository

Secondary audience:

- future human collaborators who want to understand the intended coding posture

The language should optimize for agent behavior, not for organizational branding.

## Tone

Use the `sharp but narrowed` voice.

Requirements:

- direct and opinionated
- not corporate
- not vague
- not performatively aggressive
- specific about defaults and exceptions

The file should keep some of the current voice, but reduce absolute rules that were only safe under the old experimental-stage assumption.

## Structure

The new file should be medium length and organized by theme.

Recommended sections:

1. `Purpose`
2. `Core Philosophy`
3. `Python First`
4. `Pydantic Usage`
5. `Function And Module Design`
6. `Abstraction And Boundaries`
7. `State And Mutation`
8. `Error Handling And Validation`
9. `Comments And Docstrings`
10. `Testing And Change Safety`
11. `When Changing Code`
12. `What To Avoid`
13. `Decision Rule`
14. `Priority`

This should replace the current structure rather than preserve every existing heading.

## What Must Be Preserved

The rewrite should preserve these values from the current file:

- idiomatic Python over Java/C#-style structure
- module-level functions as the default
- no fake helper/manager/util containers
- no speculative generic abstraction
- no validation theater
- no architecture vanity
- no large rewrites without reason
- clear names, shallow reasoning paths, and explicit state

These are still part of the repository identity and should remain visible.

## What Must Change

### 1. Repository framing

The new `Purpose` section must stop calling the repository:

- `a local experimental playground`

and must stop optimizing primarily for:

- `fast iteration, low code volume, and immediate readability`

Instead it should say the repository is in a productization phase and needs code that is:

- readable
- maintainable
- easy to change safely
- still biased against unnecessary complexity

### 2. Simplicity rules

The current document treats local simplicity as nearly absolute.

The rewrite should explicitly say:

- local simplicity is the default
- but repository-scale clarity, stable boundaries, and maintainable APIs can justify additional structure
- smaller is not better if it increases ambiguity, coupling, or future coordination cost

### 3. Error handling and validation

The current document's fail-fast guidance should be split into layers:

- inside trusted internal logic: fail fast remains the default
- at external boundaries: validate inputs, preserve clear error semantics, and add handling when it changes user outcome or operator understanding

The rewrite should reject both:

- defensive programming spam
- careless boundary handling in product code

### 4. Abstraction guidance

The rewrite should keep the anti-abstraction posture, but explicitly allow:

- abstractions that reduce duplication across important paths
- abstractions that clarify ownership
- abstractions that stabilize public interfaces
- abstractions that reduce integration or maintenance cost in a growing repo

It should still reject:

- speculative flexibility
- fake extension points
- generic base layers with no real pressure behind them

### 5. Productization safeguards

The current file has little explicit guidance on tests, boundary safety, and scale signals.

The rewrite should add a dedicated section that tells agents:

- changes to public behavior or critical paths should come with tests or updated tests
- productization work should consider regression risk
- oversized files or tangled modules may justify limited restructuring
- avoid changing stable code for style alone

### 6. Decision ordering

The current ordering:

1. correct
2. smaller
3. clearer
4. easier to change locally

should be replaced.

The new ordering should be:

1. correct
2. clear
3. maintainable at repository scale
4. small
5. easy to evolve locally

This is the clearest expression of the productization shift.

## Section Intent

### `Purpose`

Short, factual, and explicit:

- no longer experimental-first
- productization phase
- clarity and maintainability over raw speed of iteration

### `Core Philosophy`

State the central worldview:

- Python-first
- pragmatic minimalism
- anti-ceremony
- anti-speculative design
- necessary abstraction is allowed when it earns its cost

### `Function And Module Design`

This should absorb the old `Function Design` guidance, but also recognize module-level scale:

- keep functions direct
- keep module responsibilities legible
- split modules when they become hard to reason about
- do not create extra layers only to look organized

### `Abstraction And Boundaries`

This is a new core section.

It should instruct agents to care about:

- cohesion
- public API boundaries
- dependency direction
- avoiding junk-drawer modules
- avoiding circular dependency pressure

### `Error Handling And Validation`

This should explicitly distinguish:

- internal assumptions
- external input and integration boundaries

### `Testing And Change Safety`

This should explicitly tell agents:

- do not make risky product changes without verification
- tests should track real behavior, not ceremony
- add or update tests when behavior, boundaries, or failure modes change

### `Priority`

This should replace the old:

- `local simplicity beats theoretical architecture`

with a productization-aware version such as:

- practical clarity beats theoretical architecture
- repository-scale maintainability beats local cleverness
- working code still beats scaffolding, but stable boundaries beat short-term hacks

## Style Constraints

The rewritten file should:

- remain concise
- avoid bloated prose
- avoid management-speak
- use short bullets and short framing paragraphs
- be concrete enough that an AI can follow it as an operational rule set

It should not:

- turn into a full engineering handbook
- add process theater
- introduce enterprise wording that conflicts with the repository's culture

## Success Criteria

The rewrite is successful if a coding agent reading the new file would:

- still avoid overengineering
- still write idiomatic Python
- stop treating every validation or boundary check as forbidden ceremony
- stop over-prioritizing local minimalism when module boundaries are already strained
- make safer productization-phase changes
- preserve the repository's original taste while adapting it to a larger, more durable codebase
