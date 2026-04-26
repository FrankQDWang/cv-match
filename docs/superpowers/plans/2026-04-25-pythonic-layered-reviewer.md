# Pythonic Layered Reviewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a global, self-contained Codex skill named `pythonic-layered-reviewer` under `~/.codex/skills/` for strict, repo-first Python 3.12+ code review.

**Architecture:** Build the skill as a documentation-first package with one `SKILL.md` entrypoint and four reference files: idioms, design, scale, and sources. The implementation should optimize for judgment consistency and portability, not automation or repo-specific coupling.

**Tech Stack:** Markdown, YAML frontmatter, Codex skill conventions, Python 3.12 standard-library reference material

---

### Task 1: Create The Global Skill Skeleton

**Files:**
- Create: `/Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/SKILL.md`
- Create: `/Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/references/`

- [ ] **Step 1: Write the failing scaffold validation**

```bash
python - <<'PY'
from pathlib import Path

skill = Path("/Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/SKILL.md")
assert skill.exists(), f"missing skill file: {skill}"
text = skill.read_text()
assert "name: pythonic-layered-reviewer" in text
assert "description: Use when" in text
assert "# Pythonic Layered Reviewer" in text
PY
```

- [ ] **Step 2: Run validation to verify it fails**

Run: `python - <<'PY' ... PY`
Expected: FAIL with `missing skill file: /Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/SKILL.md`.

- [ ] **Step 3: Create the directory and minimal `SKILL.md`**

```md
---
name: pythonic-layered-reviewer
description: Use when reviewing Python 3.12+ repositories, packages, or modules for Pythonic idioms, local design quality, and scale-aware engineering boundaries.
---

# Pythonic Layered Reviewer

## Overview

Review Python code with mainstream Python consensus as the skeleton and scale-aware pragmatic minimalism as the soul.

This skill is repo-first. It prefers mature Python-native idioms, necessary abstraction, and maintainable boundaries over ceremony, speculative flexibility, or framework-shaped code.

## When To Use

- Review a whole Python repository for Pythonic quality
- Review a package or subdirectory for design drift
- Review a module that feels readable but unidiomatic
- Review a Python codebase that may be growing abstraction or boundary debt

## References

- See `references/idioms.md` for Python-native idiom rules
- See `references/design.md` for local design rules
- See `references/scale.md` for repository-scale review rules
- See `references/sources.md` for authority ordering
```

- [ ] **Step 4: Run validation to verify it passes**

Run: `python - <<'PY' ... PY`
Expected: PASS with no output.

- [ ] **Step 5: Commit**

```bash
git add /Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/SKILL.md
git commit -m "Create pythonic layered reviewer skill scaffold"
```

### Task 2: Expand `SKILL.md` Into The Full Review Contract

**Files:**
- Modify: `/Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/SKILL.md`

- [ ] **Step 1: Write the failing section validator**

```bash
python - <<'PY'
from pathlib import Path

skill = Path("/Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/SKILL.md")
text = skill.read_text()
needles = [
    "## Review Flow",
    "## Output Shape",
    "## Finding Taxonomy",
    "## Boundary Rules",
    "Hard findings",
    "Strong suggestions",
    "Preference notes",
]
for needle in needles:
    assert needle in text, f"missing section: {needle}"
PY
```

- [ ] **Step 2: Run validation to verify it fails**

Run: `python - <<'PY' ... PY`
Expected: FAIL on the first missing section, likely `missing section: ## Review Flow`.

- [ ] **Step 3: Replace `SKILL.md` with the full review contract**

```md
---
name: pythonic-layered-reviewer
description: Use when reviewing Python 3.12+ repositories, packages, or modules for Pythonic idioms, local design quality, and scale-aware engineering boundaries.
---

# Pythonic Layered Reviewer

## Overview

Review Python 3.12+ codebases with mainstream Python consensus as the skeleton and scale-aware pragmatic minimalism as the soul.

This is a review skill, not a writing assistant and not a tutorial coach.

Default posture:

- strict on high-confidence problems
- repo-first rather than snippet-first
- grounded in mainstream Python consensus
- biased toward pragmatic simplicity
- conscious of product-scale maintenance and collaboration

## When To Use

- Review a whole Python repository for Pythonic quality
- Review a package or subdirectory for design drift
- Review a module that feels readable but unidiomatic
- Review a codebase that may be growing abstraction or boundary debt

## Scope

Primary target:

- full repositories
- packages and subdirectories
- groups of related modules

Secondary target:

- single files

In scope:

- Python source code
- tests
- public API shape
- package and module boundaries
- exception and resource handling
- type usage where it affects clarity

Default caution:

- performance strategy
- concurrency strategy
- framework choice
- infrastructure choice
- product and business decomposition

## Review Layers

Review in this order:

1. `Idioms`
2. `Design`
3. `Scale`

Load the supporting references as needed:

- `references/idioms.md`
- `references/design.md`
- `references/scale.md`

## Review Flow

1. Determine scope: file, directory, or repository.
2. For repository or directory review, inspect high-level structure before local details.
3. Identify public packages, entrypoints, tests, and major configuration surfaces.
4. Form a repo-level diagnosis before drilling into local idioms.
5. Report high-confidence Pythonic and scale problems first.
6. Report lower-confidence stylistic preferences last, or suppress them.

Do not comment on everything. Prune aggressively and keep findings high-signal.

## Output Shape

Default output is two-layered:

1. findings
2. high-level diagnosis

Findings must be grouped into:

- `Hard findings`
- `Strong suggestions`
- `Preference notes`

Diagnosis labels may include:

- `Pythonic and scalable`
- `Pythonic but locally overgrown`
- `Readable but unidiomatic`
- `Over-abstracted for current needs`
- `Fragile at scale`

The diagnosis section must not introduce new findings.

## Finding Taxonomy

### Hard findings

Use only when there is clear practical cost:

- obvious anti-Pythonic boilerplate that harms readability
- obvious misuse or avoidance of mature Python-native idioms
- design ceremony with no demonstrated payoff
- repository structures that create maintenance or boundary risk
- public APIs that leak internal structure without benefit

### Strong suggestions

Use for high-value improvements that are not mandatory fixes:

- replacing repeated control-flow boilerplate with common Python idioms
- simplifying abstractions that add local complexity
- improving exception or resource semantics
- tightening module boundaries before they become active pain

### Preference notes

Use only when both approaches are viable but one is more idiomatic:

- a more natural standard-library choice
- a more concise but not materially safer rewrite
- stylistic alignment with mainstream Python practice

Do not write preference notes as defects.

## Boundary Rules

Suppress or downgrade comments when:

- the judgment depends primarily on product strategy
- the judgment depends on deep business semantics
- the tradeoff is mainly framework-local rather than Pythonic
- the issue is stylistic but produces no clear readability or maintenance gain
- the code is stable and the rewrite value is marginal

Strictness means refusing to ignore high-confidence problems, not commenting on every possible improvement.

## References

- See `references/idioms.md` for Python-native idiom rules
- See `references/design.md` for local design rules
- See `references/scale.md` for repository-scale review rules
- See `references/sources.md` for authority ordering
```

- [ ] **Step 4: Run validation to verify it passes**

Run: `python - <<'PY' ... PY`
Expected: PASS with no output.

- [ ] **Step 5: Commit**

```bash
git add /Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/SKILL.md
git commit -m "Define pythonic layered reviewer workflow"
```

### Task 3: Add The Idioms Reference

**Files:**
- Create: `/Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/references/idioms.md`

- [ ] **Step 1: Write the failing idioms coverage validator**

```bash
python - <<'PY'
from pathlib import Path

path = Path("/Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/references/idioms.md")
assert path.exists(), f"missing: {path}"
text = path.read_text()
for needle in [
    "zip",
    "enumerate",
    "defaultdict",
    "Counter",
    "pathlib",
    "context managers",
    "for i in range(len(",
]:
    assert needle in text, f"missing idiom guidance: {needle}"
PY
```

- [ ] **Step 2: Run validation to verify it fails**

Run: `python - <<'PY' ... PY`
Expected: FAIL with `missing: /Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/references/idioms.md`.

- [ ] **Step 3: Add `references/idioms.md`**

```md
# Idioms

## Core Rule

Prefer mature, common Python-native idioms over hand-written boilerplate when the idiom is stable, recognizable, and improves readability.

## Prefer

- `zip` for coordinated iteration across iterables
- `enumerate` when an index is actually needed
- `extend` when appending multiple items to a list
- `defaultdict` for grouped accumulation
- `Counter` for counting
- comprehensions for straightforward collection construction
- generator expressions for one-pass aggregation or streaming transforms
- `any`, `all`, and `sum` over manual sentinel loops when intent is clearer
- `pathlib` over stringly-typed path assembly
- context managers over manual resource teardown
- standard-library tools over custom helper wrappers

## Common Anti-Patterns

### Index bookkeeping instead of direct iteration

Prefer:

```python
for i, item in enumerate(items):
    ...
```

Avoid:

```python
for i in range(len(items)):
    item = items[i]
    ...
```

### Manual paired iteration

Prefer:

```python
for left, right in zip(a, b):
    ...
```

Avoid:

```python
for i in range(len(a)):
    left = a[i]
    right = b[i]
    ...
```

### Manual counting or grouping

Prefer:

```python
from collections import Counter, defaultdict

counts = Counter(colors)
grouped = defaultdict(list)
for row in rows:
    grouped[row.kind].append(row)
```

### Hand-built output lists for simple transforms

Prefer:

```python
names = [user.name for user in users if user.active]
```

Avoid:

```python
names = []
for user in users:
    if user.active:
        names.append(user.name)
```

### Manual resource teardown

Prefer:

```python
with open(path) as f:
    data = f.read()
```

## Review Notes

- Do not push clever idioms that reduce readability.
- Do not treat newer syntax as inherently better.
- Prefer common Python-native constructs, not novelty.
```

- [ ] **Step 4: Run validation to verify it passes**

Run: `python - <<'PY' ... PY`
Expected: PASS with no output.

- [ ] **Step 5: Commit**

```bash
git add /Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/references/idioms.md
git commit -m "Add pythonic idioms reference"
```

### Task 4: Add The Design Reference

**Files:**
- Create: `/Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/references/design.md`

- [ ] **Step 1: Write the failing design coverage validator**

```bash
python - <<'PY'
from pathlib import Path

path = Path("/Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/references/design.md")
assert path.exists(), f"missing: {path}"
text = path.read_text()
for needle in [
    "module-level functions",
    "Utils",
    "Managers",
    "Java/C#",
    "public API",
    "necessary abstraction",
]:
    assert needle in text, f"missing design guidance: {needle}"
PY
```

- [ ] **Step 2: Run validation to verify it fails**

Run: `python - <<'PY' ... PY`
Expected: FAIL with `missing: /Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/references/design.md`.

- [ ] **Step 3: Add `references/design.md`**

```md
# Design

## Core Rule

Prefer direct, natural Python structure. Allow necessary abstraction, but reject speculative flexibility and no-payoff ceremony.

## Prefer

- module-level functions unless a class holds real state or lifecycle
- explicit state over hidden state containers
- names that express domain meaning
- small, clear public APIs
- one clear responsibility per unit
- targeted abstraction with a demonstrated payoff

## Watch For

### Java/C#-style ceremony in Python

Examples:

- classes that only group stateless helpers
- empty wrapper layers around simple functions
- architectural naming without domain meaning
- method chains that exist only to imitate another ecosystem

### Vanity containers

Treat these names as warning signs unless they clearly earn their keep:

- `Utils`
- `Helpers`
- `Managers`
- `Services` used as junk drawers

### Over-abstraction

Push back when the code introduces:

- extension points with no current consumer
- generic interfaces with only one implementation and no pressure to generalize
- indirection that makes the happy path harder to follow

## Public API Guidance

- Prefer public APIs that expose stable intent, not internal structure.
- Prefer parameters typed by capability when it improves clarity.
- Prefer return values that are concrete and obvious to consume.
- Call out APIs that leak private storage details across modules.

## Review Notes

- Do not confuse "more layers" with "more maintainable".
- Do not demand abstraction where direct code is still clear.
- Do not reward framework-shaped structure over natural Python structure.
```

- [ ] **Step 4: Run validation to verify it passes**

Run: `python - <<'PY' ... PY`
Expected: PASS with no output.

- [ ] **Step 5: Commit**

```bash
git add /Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/references/design.md
git commit -m "Add pythonic design reference"
```

### Task 5: Add The Scale Reference

**Files:**
- Create: `/Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/references/scale.md`

- [ ] **Step 1: Write the failing scale coverage validator**

```bash
python - <<'PY'
from pathlib import Path

path = Path("/Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/references/scale.md")
assert path.exists(), f"missing: {path}"
text = path.read_text()
for needle in [
    "package and module cohesion",
    "dependency direction",
    "public API stability",
    "circular dependencies",
    "configuration bloat",
    "speculative extension points",
]:
    assert needle in text, f"missing scale guidance: {needle}"
PY
```

- [ ] **Step 2: Run validation to verify it fails**

Run: `python - <<'PY' ... PY`
Expected: FAIL with `missing: /Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/references/scale.md`.

- [ ] **Step 3: Add `references/scale.md`**

```md
# Scale

## Core Rule

As repositories grow, Pythonic code still favors clarity and directness, but now also requires stable boundaries, cohesive modules, and disciplined dependency direction.

## Review Priorities

- package and module cohesion
- dependency direction
- public API stability and boundary clarity
- leakage of internals across modules
- circular dependencies
- abstraction bloat
- configuration bloat
- speculative extension points

## Signals To Flag

### Boundary drift

Flag when modules import through each other in ways that make ownership unclear or require readers to chase behavior across too many files.

### Public API instability

Flag when package consumers appear to depend on internal implementation details rather than a clear public entrypoint.

### Circular dependencies

Treat circular dependencies as a strong scale signal even when the code still runs. They usually indicate unclear ownership or a boundary split that no longer matches the code's responsibilities.

### Configuration bloat

Flag settings, flags, and indirection layers that mostly exist to support hypothetical futures rather than current behavior.

### Speculative extension points

Push back on plugin hooks, abstract bases, or generic registries that do not yet have real pressure behind them.

## Review Notes

- Do not confuse repository growth with a mandate for enterprise ceremony.
- Necessary abstraction is acceptable when it clearly reduces maintenance cost.
- Prefer structures that reduce coordination cost across contributors.
```

- [ ] **Step 4: Run validation to verify it passes**

Run: `python - <<'PY' ... PY`
Expected: PASS with no output.

- [ ] **Step 5: Commit**

```bash
git add /Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/references/scale.md
git commit -m "Add pythonic scale reference"
```

### Task 6: Add The Sources Reference And Validate The Whole Skill

**Files:**
- Create: `/Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/references/sources.md`
- Modify: `/Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/SKILL.md`

- [ ] **Step 1: Write the failing end-to-end validator**

```bash
python - <<'PY'
from pathlib import Path

root = Path("/Users/frankqdwang/.codex/skills/pythonic-layered-reviewer")
required = [
    root / "SKILL.md",
    root / "references" / "idioms.md",
    root / "references" / "design.md",
    root / "references" / "scale.md",
    root / "references" / "sources.md",
]
for path in required:
    assert path.exists(), f"missing file: {path}"

skill_text = (root / "SKILL.md").read_text()
for ref in [
    "references/idioms.md",
    "references/design.md",
    "references/scale.md",
    "references/sources.md",
]:
    assert ref in skill_text, f"missing reference link: {ref}"

sources_text = (root / "references" / "sources.md").read_text()
for needle in [
    "https://peps.python.org/pep-0020/",
    "https://peps.python.org/pep-0008/",
    "https://docs.python.org/3.12/",
    "treyhunner.com",
    "realpython.com",
]:
    assert needle in sources_text, f"missing source: {needle}"
PY
```

- [ ] **Step 2: Run validation to verify it fails**

Run: `python - <<'PY' ... PY`
Expected: FAIL because `references/sources.md` does not exist yet.

- [ ] **Step 3: Add `references/sources.md` and tighten the `SKILL.md` authority wording**

```md
# Sources

## Authority Order

### Primary authority

1. PEP 20: https://peps.python.org/pep-0020/
2. PEP 8: https://peps.python.org/pep-0008/
3. Python 3.12 documentation: https://docs.python.org/3.12/

### Secondary authority

- `typing`: https://docs.python.org/3.12/library/typing.html
- `pathlib`: https://docs.python.org/3.12/library/pathlib.html
- `enum`: https://docs.python.org/3.12/library/enum.html
- standard library index: https://docs.python.org/3.12/library/
- Python 3.12 changes: https://docs.python.org/3.12/whatsnew/3.12.html

### Tertiary support

- Trey Hunner on built-ins and common idioms: https://treyhunner.com/2019/05/python-builtins-worth-learning/
- Trey Hunner on counting and `Counter`: https://treyhunner.com/2015/11/counting-things-in-python/
- Real Python best practices index: https://realpython.com/ref/best-practices/
- Real Python on Pythonic code: https://realpython.com/ref/best-practices/pythonic-code/
- Real Python on comprehensions: https://realpython.com/ref/best-practices/comprehensions/
- Real Python on generator expressions: https://realpython.com/ref/best-practices/generator-expressions/
- Real Python on loops and `enumerate()`: https://realpython.com/ref/best-practices/loops/

## Usage Rule

- Treat official Python sources as the base authority.
- Use community sources to sharpen judgment, not to override official guidance.
- Do not depend on project-local or machine-local research files to use this skill.
```

```md
<!-- /Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/SKILL.md -->
## References

- See `references/idioms.md` for Python-native idiom rules.
- See `references/design.md` for local design rules.
- See `references/scale.md` for repository-scale review rules.
- See `references/sources.md` for authority ordering and source precedence.
```

- [ ] **Step 4: Run the end-to-end validation**

Run: `python - <<'PY' ... PY`
Expected: PASS with no output.

- [ ] **Step 5: Run a manual smoke review checklist**

Run:

```bash
sed -n '1,220p' /Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/SKILL.md
sed -n '1,220p' /Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/references/idioms.md
sed -n '1,220p' /Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/references/design.md
sed -n '1,220p' /Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/references/scale.md
sed -n '1,220p' /Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/references/sources.md
```

Expected: All five files render cleanly, have no unresolved markers, and read as a coherent review system rather than five disconnected notes.

- [ ] **Step 6: Commit**

```bash
git add /Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/SKILL.md /Users/frankqdwang/.codex/skills/pythonic-layered-reviewer/references/sources.md
git commit -m "Finish pythonic layered reviewer skill"
```
