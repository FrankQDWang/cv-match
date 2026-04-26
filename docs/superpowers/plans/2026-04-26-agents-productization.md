# AGENTS.md Productization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `AGENTS.md` into a productization-phase, AI-agent-facing ruleset that preserves the repository's Python-first, anti-ceremony style while adapting it to a growing codebase.

**Architecture:** Replace the current experimental-playground framing with a productization-aware structure organized by theme. Preserve the existing taste where it still fits, but explicitly add scale-aware boundaries, change safety, and layered error-handling guidance.

**Tech Stack:** Markdown, repository-local policy document, existing repository context

---

### Task 1: Replace The Top-Level Framing And Core Philosophy

**Files:**
- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/AGENTS.md`
- Test: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/AGENTS.md`

- [ ] **Step 1: Write the failing framing check**

```bash
python - <<'PY'
from pathlib import Path

text = Path("/Users/frankqdwang/Agents/SeekTalent-0.2.4/AGENTS.md").read_text()
assert "local experimental playground" not in text
assert "productization" in text.lower()
assert "Core Philosophy" in text
PY
```

- [ ] **Step 2: Run check to verify it fails**

Run: `python - <<'PY' ... PY`
Expected: FAIL because the current file still says `local experimental playground`, does not mention `productization`, and does not contain a `Core Philosophy` section.

- [ ] **Step 3: Replace the top framing with the new productization-aware opening**

```md
# AGENTS.md

## Purpose

This repository is in active productization.
Optimize for readable Python, safe change velocity, and maintainable repository-scale structure.

Default to pragmatic simplicity, but do not preserve experimental-stage shortcuts once they start increasing maintenance cost, boundary confusion, or regression risk.

## Core Philosophy

- Write idiomatic Python, not Java/C# in Python syntax.
- Prefer direct code over ceremony.
- Prefer the simplest design that remains clear at repository scale.
- Do not engineer for hypothetical future needs.
- Allow necessary abstraction when it improves boundaries, API stability, or collaboration cost.
- Reject speculative flexibility, architecture vanity, and no-payoff indirection.
- Fail fast inside trusted internal logic.
- Be more deliberate at external boundaries, user-facing flows, and integration points.
```

- [ ] **Step 4: Run check to verify it passes**

Run: `python - <<'PY' ... PY`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add AGENTS.md
git commit -m "Rewrite AGENTS framing for productization"
```

### Task 2: Rewrite The Core Coding Style Sections

**Files:**
- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/AGENTS.md`
- Test: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/AGENTS.md`

- [ ] **Step 1: Write the failing section-shape check**

```bash
python - <<'PY'
from pathlib import Path

text = Path("/Users/frankqdwang/Agents/SeekTalent-0.2.4/AGENTS.md").read_text()
needles = [
    "## Python First",
    "## Pydantic Usage",
    "## Function And Module Design",
    "## State And Mutation",
]
for needle in needles:
    assert needle in text, f"missing section: {needle}"
PY
```

- [ ] **Step 2: Run check to verify it fails**

Run: `python - <<'PY' ... PY`
Expected: FAIL because `Function And Module Design` does not exist yet.

- [ ] **Step 3: Replace the style sections with the new productization-aware versions**

```md
## Python First

- Write idiomatic Python, not Java/C# in Python syntax.
- Prefer module-level functions over classes by default.
- Only introduce a class when it holds real state, lifecycle, or identity.
- Never create `Utils`, `Helpers`, `Managers`, or similar junk containers for stateless code.
- Prefer simple protocols and direct interfaces over hierarchy-heavy design.

## Pydantic Usage

- Use Pydantic models where typed boundaries or structured input/output genuinely need them.
- Keep models small, explicit, and close to usage.
- Do not create model layers for architecture vanity.
- Do not wrap every internal value in a model.
- Add validators only when they enforce real business meaning or prevent a real bug.
- Do not add validation theater.

## Function And Module Design

- Prefer short functions with obvious inputs and outputs.
- Keep the main path readable top-to-bottom.
- Keep logic inline when extraction would only add indirection.
- Extract functions when it improves clarity, reuse, or testability.
- Keep module responsibilities legible.
- If a file becomes hard to reason about, split it by responsibility instead of stacking more local helpers into it.
- Do not add layers just to look organized.

## State And Mutation

- Keep state explicit.
- Prefer passing values directly over hiding state in broad containers.
- Mutate data only when mutation is the clearest choice.
- Do not simulate immutability with pointless copying.
- Do not add getters and setters without a real boundary reason.
```

- [ ] **Step 4: Run check to verify it passes**

Run: `python - <<'PY' ... PY`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add AGENTS.md
git commit -m "Rewrite AGENTS coding style sections"
```

### Task 3: Add Abstraction, Boundaries, And Error Handling Rules

**Files:**
- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/AGENTS.md`
- Test: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/AGENTS.md`

- [ ] **Step 1: Write the failing boundary-rules check**

```bash
python - <<'PY'
from pathlib import Path

text = Path("/Users/frankqdwang/Agents/SeekTalent-0.2.4/AGENTS.md").read_text()
needles = [
    "## Abstraction And Boundaries",
    "## Error Handling And Validation",
    "public APIs",
    "external boundaries",
    "circular dependencies",
]
for needle in needles:
    assert needle in text, f"missing rule: {needle}"
PY
```

- [ ] **Step 2: Run check to verify it fails**

Run: `python - <<'PY' ... PY`
Expected: FAIL because the new sections and phrases are not in the file yet.

- [ ] **Step 3: Add the new abstraction and error sections**

```md
## Abstraction And Boundaries

- Treat local simplicity as the default, not an absolute.
- Introduce abstraction only when it clearly improves ownership, boundaries, reuse across important paths, or API stability.
- Keep public APIs small, explicit, and stable.
- Do not leak internal storage or implementation details across modules without a strong reason.
- Avoid junk-drawer modules that mix unrelated responsibilities.
- Avoid circular dependencies. If modules want to know too much about each other, the boundary is probably wrong.
- Do not create extension points, generic bases, or extra indirection without real pressure behind them.

## Error Handling And Validation

- Fail fast inside trusted internal logic.
- Be more deliberate at external boundaries, user-facing flows, and integration points.
- Validate input where it changes user outcome, operator understanding, or downstream safety.
- Do not swallow exceptions.
- Preserve clear error semantics.
- Do not add fallback chains, retry logic, or recovery scaffolding unless the use case actually requires it.
- Reject both defensive-programming spam and careless boundary handling.
```

- [ ] **Step 4: Run check to verify it passes**

Run: `python - <<'PY' ... PY`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add AGENTS.md
git commit -m "Add AGENTS boundary and error rules"
```

### Task 4: Add Productization-Phase Safety Rules

**Files:**
- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/AGENTS.md`
- Test: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/AGENTS.md`

- [ ] **Step 1: Write the failing safety-section check**

```bash
python - <<'PY'
from pathlib import Path

text = Path("/Users/frankqdwang/Agents/SeekTalent-0.2.4/AGENTS.md").read_text()
needles = [
    "## Comments And Docstrings",
    "## Testing And Change Safety",
    "## When Changing Code",
    "regression risk",
    "stable code for style alone",
]
for needle in needles:
    assert needle in text, f"missing section or rule: {needle}"
PY
```

- [ ] **Step 2: Run check to verify it fails**

Run: `python - <<'PY' ... PY`
Expected: FAIL because `Testing And Change Safety` does not exist yet.

- [ ] **Step 3: Add the productization safety sections**

```md
## Comments And Docstrings

- Write comments only when the reason is non-obvious.
- Do not comment what the code already says.
- Prefer self-explanatory code over explanatory comments.
- Use short, factual docstrings for public functions or non-obvious behavior.

## Testing And Change Safety

- Productization work should consider regression risk by default.
- Changes to public behavior, failure modes, or critical paths should come with tests or updated tests.
- Tests should track real behavior, not ceremony.
- Do not make risky changes to important paths without verification.
- If code is stable and correct, do not churn it for style alone.

## When Changing Code

- Make the smallest change that fully solves the problem.
- Prefer surgical diffs by default.
- Preserve working code unless there is a real reason to change it.
- Do not rewrite large sections without need.
- Do not reshape stable code for style alone.
- If the current structure is actively harming clarity or maintenance, limited restructuring is allowed.
- When restructuring, improve boundaries and readability, not architecture theater.
```

- [ ] **Step 4: Run check to verify it passes**

Run: `python - <<'PY' ... PY`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add AGENTS.md
git commit -m "Add AGENTS productization safety rules"
```

### Task 5: Replace The Closing Decision Logic

**Files:**
- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/AGENTS.md`
- Test: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/AGENTS.md`

- [ ] **Step 1: Write the failing decision-order check**

```bash
python - <<'PY'
from pathlib import Path

text = Path("/Users/frankqdwang/Agents/SeekTalent-0.2.4/AGENTS.md").read_text()
needles = [
    "## What To Avoid",
    "## Decision Rule",
    "maintainable at repository scale",
    "## Priority",
    "repository-scale maintainability beats local cleverness",
]
for needle in needles:
    assert needle in text, f"missing closing rule: {needle}"
assert "2. smaller" not in text
PY
```

- [ ] **Step 2: Run check to verify it fails**

Run: `python - <<'PY' ... PY`
Expected: FAIL because the old ordering still contains `2. smaller` and the new phrasing is absent.

- [ ] **Step 3: Replace the closing sections**

```md
## What To Avoid

- No enterprise architecture cosplay.
- No premature extensibility.
- No speculative generic abstractions.
- No fake base classes created just in case.
- No defensive programming spam.
- No configuration bloat without real payoff.
- No ceremony added just to look professional.

## Decision Rule

When several implementations are possible, prefer the one that is:

1. correct
2. clear
3. maintainable at repository scale
4. small
5. easy to evolve locally

If two options are equally correct, choose the less abstract one unless the extra structure clearly improves boundaries or long-term maintenance.

## Priority

- Practical clarity beats theoretical architecture.
- Repository-scale maintainability beats local cleverness.
- Readable Python beats pattern-heavy design.
- Working code still beats scaffolding, but stable boundaries beat short-term hacks.
```

- [ ] **Step 4: Run check to verify it passes**

Run: `python - <<'PY' ... PY`
Expected: PASS.

- [ ] **Step 5: Run a final file-level review check**

Run:

```bash
sed -n '1,260p' /Users/frankqdwang/Agents/SeekTalent-0.2.4/AGENTS.md
```

Expected: The file reads as one coherent productization-phase policy, still sounds direct and opinionated, and no longer frames the repository as an experimental playground.

- [ ] **Step 6: Commit**

```bash
git add AGENTS.md
git commit -m "Rewrite AGENTS for productization phase"
```
