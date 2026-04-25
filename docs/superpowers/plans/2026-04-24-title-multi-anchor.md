# Title Multi-Anchor Retrieval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teach SeekTalent to keep one or two title-derived anchors, use a stronger round-one query, and stop suppressing explicit domain terms needed for retrieval.

**Architecture:** Keep the current deterministic retrieval pipeline. Requirement extraction produces one or two title anchors plus a short rationale; normalization and the compiler turn those into a controlled term bank with `primary_role_anchor`, optional `secondary_title_anchor`, and stronger admitted domain terms; query planning continues to enforce a small query budget and runtime remains the final authority. Prompt changes only widen candidate discovery and explain the new rules.

**Tech Stack:** Python, Pydantic, pydantic-ai, pytest, existing `seektalent` retrieval/runtime modules.

---

## File Structure

- Modify `src/seektalent/models.py`: replace the single title-anchor field in `RequirementExtractionDraft` and `RequirementSheet`, extend `QueryRetrievalRole`, and add helper functions for anchor-role checks.
- Modify `src/seektalent/requirements/normalization.py`: normalize `title_anchor_terms`, validate the `1..2` rule, and pass the list into the compiler.
- Modify `src/seektalent/requirements/extractor.py`: keep the prompt renderer aligned with the new schema.
- Modify `src/seektalent/retrieval/query_compiler.py`: emit one or two title anchors, relax notes demotion, widen the support-term active window, and choose a strongest domain term ordering that prefers domain-defining terms.
- Modify `src/seektalent/retrieval/query_plan.py`: require exactly one primary anchor in each normal query, support optional secondary title anchors, and prefer the title-title round-one query when available.
- Modify `src/seektalent/controller/react_controller.py`: render and validate the new anchor roles in the term bank.
- Modify `src/seektalent/runtime/orchestrator.py`: switch runtime call sites from `title_anchor_term` to `title_anchor_terms`, add lightweight failure labels, and keep round-one assembly deterministic.
- Modify `src/seektalent/runtime/context_builder.py`: pass the normalized title-anchor list through controller and reflection contexts where needed.
- Modify prompt files `src/seektalent/prompts/requirements.md`, `src/seektalent/prompts/controller.md`, and `src/seektalent/prompts/reflection.md`: explain the new title-anchor and strongest-domain-term rules.
- Modify tests in `tests/test_requirement_extraction.py`, `tests/test_query_compiler.py`, `tests/test_query_plan.py`, `tests/test_llm_input_prompts.py`, `tests/test_controller_contract.py`, `tests/test_runtime_state_flow.py`, and `tests/test_runtime_audit.py`.

---

### Task 1: Replace Single Title Anchor With a `1..2` Title-Anchor List

**Files:**
- Modify: `src/seektalent/models.py`
- Modify: `src/seektalent/requirements/normalization.py`
- Modify: `src/seektalent/requirements/extractor.py`
- Test: `tests/test_requirement_extraction.py`

- [ ] **Step 1: Write the failing requirement-normalization tests**

Add these tests near the existing normalization coverage in `tests/test_requirement_extraction.py`:

```python
def test_normalize_requirement_draft_keeps_one_or_two_title_anchors() -> None:
    requirement_sheet = normalize_requirement_draft(
        RequirementExtractionDraft(
            role_title="AI主观投资团队牵头人",
            title_anchor_terms=["AI", "投研"],
            title_anchor_rationale="title simultaneously names AI scope and investment-research scope",
            jd_query_terms=["大模型", "基金"],
            role_summary="负责 AI 主观投研体系建设。",
            must_have_capabilities=["AI", "投研"],
            scoring_rationale="优先看 AI 与投研交叉经验。",
        ),
        job_title="AI主观投资团队牵头人",
    )

    assert requirement_sheet.title_anchor_terms == ["AI", "投研"]
    assert [item.term for item in requirement_sheet.initial_query_term_pool[:2]] == ["AI", "投研"]


def test_normalize_requirement_draft_does_not_require_second_title_anchor() -> None:
    requirement_sheet = normalize_requirement_draft(
        RequirementExtractionDraft(
            role_title="高级产品组经理",
            title_anchor_terms=["产品经理"],
            title_anchor_rationale="title has one stable retrieval anchor",
            jd_query_terms=["人工耳蜗"],
            role_summary="负责产品线管理。",
            must_have_capabilities=["产品管理"],
            scoring_rationale="优先看产品线管理经验。",
        ),
        job_title="高级产品组经理",
    )

    assert requirement_sheet.title_anchor_terms == ["产品经理"]


def test_normalize_requirement_draft_rejects_more_than_two_title_anchors() -> None:
    with pytest.raises(ValueError, match="title_anchor_terms must contain 1 or 2 terms"):
        normalize_requirement_draft(
            RequirementExtractionDraft(
                role_title="搜索推荐广告算法工程师",
                title_anchor_terms=["搜索", "推荐", "广告"],
                title_anchor_rationale="too many anchors",
                jd_query_terms=["Python"],
                role_summary="负责算法系统建设。",
                must_have_capabilities=["算法"],
                scoring_rationale="先看算法相关性。",
            ),
            job_title="搜索推荐广告算法工程师",
        )
```

- [ ] **Step 2: Run the focused tests and capture the current failure**

Run:

```bash
uv run pytest tests/test_requirement_extraction.py::test_normalize_requirement_draft_keeps_one_or_two_title_anchors tests/test_requirement_extraction.py::test_normalize_requirement_draft_does_not_require_second_title_anchor tests/test_requirement_extraction.py::test_normalize_requirement_draft_rejects_more_than_two_title_anchors -v
```

Expected: failure because `RequirementExtractionDraft` does not yet accept `title_anchor_terms` or `title_anchor_rationale`.

- [ ] **Step 3: Change the requirement and term-role models**

In `src/seektalent/models.py`, replace the title-anchor fields and extend the enum:

```python
QueryRetrievalRole = Literal[
    "primary_role_anchor",
    "secondary_title_anchor",
    "domain_context",
    "framework_tool",
    "target_company",
    "filter_only",
    "score_only",
]
```

```python
class RequirementExtractionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_title: str = Field(min_length=1, description="Short normalized role title from the JD and notes.")
    title_anchor_terms: list[str] = Field(
        min_length=1,
        max_length=2,
        description="One or two stable searchable anchors extracted from job_title.",
    )
    title_anchor_rationale: str = Field(
        min_length=1,
        description="Short explanation for why the title anchors capture the retrieval direction.",
    )
    jd_query_terms: list[str] = Field(
        default_factory=list,
        description="High-signal searchable terms extracted from the JD only, excluding title anchors.",
    )
```

```python
class RequirementSheet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_title: str
    title_anchor_terms: list[str] = Field(default_factory=list)
    title_anchor_rationale: str
    role_summary: str
```

Add anchor-role helpers close to the query-term helpers:

```python
def is_primary_anchor_role(role: QueryRetrievalRole) -> bool:
    return role == "primary_role_anchor"


def is_title_anchor_role(role: QueryRetrievalRole) -> bool:
    return role in {"primary_role_anchor", "secondary_title_anchor"}
```

- [ ] **Step 4: Normalize the new fields and keep the old behavior for one-anchor titles**

In `src/seektalent/requirements/normalization.py`, replace the single-anchor normalization block with:

```python
    title_anchor_terms = _clean_list(draft.title_anchor_terms, limit=2)
    if not title_anchor_terms or len(title_anchor_terms) > 2:
        raise ValueError("title_anchor_terms must contain 1 or 2 terms after normalization")
    title_anchor_rationale = _clean_text(draft.title_anchor_rationale)
    if not title_anchor_rationale:
        raise ValueError("title_anchor_rationale must not be empty after normalization")
```

Filter duplicate JD and notes terms against every title anchor:

```python
    title_anchor_keys = {term.casefold() for term in title_anchor_terms}
    jd_query_terms = [
        term
        for term in _clean_list(draft.jd_query_terms, limit=8)
        if term.casefold() not in title_anchor_keys
    ]
    notes_query_terms = [
        term
        for term in _clean_list(draft.notes_query_terms, limit=8)
        if term.casefold() not in title_anchor_keys
    ]
```

Update the `RequirementSheet` construction:

```python
        title_anchor_terms=title_anchor_terms,
        title_anchor_rationale=title_anchor_rationale,
        initial_query_term_pool=compile_query_term_pool(
            job_title=role_title,
            title_anchor_terms=title_anchor_terms,
            jd_query_terms=jd_query_terms,
            notes_query_terms=notes_query_terms,
            hard_constraints=hard_constraints,
            preferences=preferences,
        ),
```

Keep `render_requirements_prompt()` in `src/seektalent/requirements/extractor.py` unchanged apart from the schema wording: it should still render `job_title`, `JD`, and `notes`, but the output type now expects the new fields.

- [ ] **Step 5: Update the test fixtures and constructors that still use `title_anchor_term`**

In `tests/test_requirement_extraction.py`, update `_valid_requirement_draft()` and the inline drafts:

```python
def _valid_requirement_draft() -> RequirementExtractionDraft:
    return RequirementExtractionDraft(
        role_title="Senior Python Engineer",
        title_anchor_terms=["Python"],
        title_anchor_rationale="title has one stable technical anchor",
        jd_query_terms=["Retrieval Systems"],
        role_summary="Build retrieval and ranking capabilities.",
        must_have_capabilities=["Python"],
        scoring_rationale="Prioritize Python and retrieval depth.",
    )
```

Likewise replace assertions like:

```python
assert requirement_sheet.title_anchor_term == "Python"
```

with:

```python
assert requirement_sheet.title_anchor_terms == ["Python"]
```

- [ ] **Step 6: Run the focused normalization tests**

Run:

```bash
uv run pytest tests/test_requirement_extraction.py -v
```

Expected: all requirement-extraction tests pass with the new `title_anchor_terms` schema.

- [ ] **Step 7: Commit**

```bash
git add src/seektalent/models.py src/seektalent/requirements/normalization.py src/seektalent/requirements/extractor.py tests/test_requirement_extraction.py
git commit -m "Add one-or-two title anchor schema"
```

---

### Task 2: Teach the Compiler to Emit Primary and Optional Secondary Title Anchors

**Files:**
- Modify: `src/seektalent/retrieval/query_compiler.py`
- Test: `tests/test_query_compiler.py`

- [ ] **Step 1: Add the failing compiler tests**

Append these tests to `tests/test_query_compiler.py`:

```python
def test_query_compiler_emits_primary_and_secondary_title_anchors() -> None:
    pool = compile_query_term_pool(
        job_title="AI主观投资团队牵头人",
        title_anchor_terms=["AI", "投研"],
        jd_query_terms=["大模型", "基金"],
        notes_query_terms=[],
    )

    assert [item.term for item in pool[:2]] == ["AI", "投研"]
    assert pool[0].retrieval_role == "primary_role_anchor"
    assert pool[1].retrieval_role == "secondary_title_anchor"


def test_query_compiler_keeps_single_title_anchor_when_only_one_is_present() -> None:
    pool = compile_query_term_pool(
        job_title="高级产品组经理",
        title_anchor_terms=["产品经理"],
        jd_query_terms=["人工耳蜗"],
        notes_query_terms=[],
    )

    assert pool[0].term == "产品经理"
    assert pool[0].retrieval_role == "primary_role_anchor"
    assert not any(item.retrieval_role == "secondary_title_anchor" for item in pool)


def test_query_compiler_admits_explicit_domain_notes_terms() -> None:
    pool = compile_query_term_pool(
        job_title="高级产品组经理",
        title_anchor_terms=["产品经理"],
        jd_query_terms=["产品管理"],
        notes_query_terms=["人工耳蜗", "沟通能力"],
    )
    terms = _by_term(pool)

    assert terms["人工耳蜗"].queryability == "admitted"
    assert terms["人工耳蜗"].active is True
    assert terms["沟通能力"].queryability == "score_only"
```

- [ ] **Step 2: Run the compiler tests to verify failure**

Run:

```bash
uv run pytest tests/test_query_compiler.py -v
```

Expected: failures because the compiler still takes `title_anchor_term`, still uses `role_anchor`, and still demotes all admitted notes terms.

- [ ] **Step 3: Update the compiler signature, anchor emission, and active-window cap**

In `src/seektalent/retrieval/query_compiler.py`, make these constant and signature changes:

```python
ACTIVE_NON_ANCHOR_WINDOW = 6
```

```python
def compile_query_term_pool(
    *,
    job_title: str,
    title_anchor_terms: list[str],
    jd_query_terms: list[str],
    notes_query_terms: list[str],
    hard_constraints: HardConstraintSlots | None = None,
    preferences: PreferenceSlots | None = None,
) -> list[QueryTermCandidate]:
```

Replace the anchor-emission loop with:

```python
    priority = 1
    compiled_title_anchors = _compile_title_anchors(job_title=job_title, title_anchor_terms=title_anchor_terms)
    for index, anchor in enumerate(compiled_title_anchors):
        add_candidate(
            term=anchor,
            source="job_title",
            category="role_anchor",
            role="primary_role_anchor" if index == 0 else "secondary_title_anchor",
            queryability="admitted",
            family=_family_for_role(anchor),
            priority=priority,
            evidence="Compiled job title anchor.",
        )
        priority += 1
```

Rename `_compile_role_anchors()` to `_compile_title_anchors()` and normalize the list:

```python
def _compile_title_anchors(*, job_title: str, title_anchor_terms: list[str]) -> list[str]:
    cleaned_terms = [_clean_title_anchor(term) for term in title_anchor_terms]
    fallback = _clean_title_anchor(_clean_text(job_title))
    anchors = unique_strings([term for term in cleaned_terms if term] or [fallback])
    return anchors[:2]
```

- [ ] **Step 4: Relax notes-term handling without dropping the dirty-term guardrails**

Replace the hard demotion block:

```python
        if source == "notes" and queryability == "admitted":
            role = "score_only"
            queryability = "score_only"
            category = "expansion"
            family = f"notes.{_compact_key(clean) or 'unknown'}"
```

with:

```python
        if source == "notes" and queryability == "admitted":
            if _should_admit_notes_term(clean):
                family = family if family.startswith("domain.") else f"domain.{_compact_key(clean) or 'unknown'}"
            else:
                role = "score_only"
                queryability = "score_only"
                category = "expansion"
                family = f"notes.{_compact_key(clean) or 'unknown'}"
```

Add a narrow helper below `_merge_query_terms()`:

```python
def _should_admit_notes_term(term: str) -> bool:
    compact = _compact_key(term)
    if not compact:
        return False
    if _is_filter_only(term, compact):
        return False
    if any(pattern in compact for pattern in BLOCKED_PATTERNS):
        return False
    if any(pattern in term or pattern in term.casefold() for pattern in ABSTRACT_PATTERNS):
        return False
    return len(term) <= 8
```

This keeps `人工耳蜗` and `AI投研` admitted while still pushing `沟通能力` or `985` out.

- [ ] **Step 5: Update compiler tests that still assert `role_anchor` or notes demotion**

In `tests/test_query_compiler.py`, replace assertions like:

```python
assert terms["AI Agent"].retrieval_role == "role_anchor"
```

with:

```python
assert terms["AI Agent"].retrieval_role == "primary_role_anchor"
```

Update the old notes-demotion test to the new behavior:

```python
assert terms["RAG"].queryability == "admitted"
assert terms["RAG"].active is True
```

- [ ] **Step 6: Run the compiler suite**

Run:

```bash
uv run pytest tests/test_query_compiler.py -v
```

Expected: all compiler tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/seektalent/retrieval/query_compiler.py tests/test_query_compiler.py
git commit -m "Compile primary and secondary title anchors"
```

---

### Task 3: Update Query Planning and Runtime to Prefer `Primary + Secondary` in Round One

**Files:**
- Modify: `src/seektalent/retrieval/query_plan.py`
- Modify: `src/seektalent/controller/react_controller.py`
- Modify: `src/seektalent/runtime/orchestrator.py`
- Modify: `src/seektalent/runtime/context_builder.py`
- Test: `tests/test_query_plan.py`
- Test: `tests/test_controller_contract.py`
- Test: `tests/test_runtime_state_flow.py`

- [ ] **Step 1: Add the failing query-plan tests**

Add these tests to `tests/test_query_plan.py`:

```python
def test_query_plan_round_one_prefers_primary_plus_secondary_title_anchor() -> None:
    pool = [
        QueryTermCandidate(
            term="AI",
            source="job_title",
            category="role_anchor",
            priority=1,
            evidence="title",
            first_added_round=0,
            retrieval_role="primary_role_anchor",
            queryability="admitted",
            family="role.ai",
        ),
        QueryTermCandidate(
            term="投研",
            source="job_title",
            category="role_anchor",
            priority=2,
            evidence="title",
            first_added_round=0,
            retrieval_role="secondary_title_anchor",
            queryability="admitted",
            family="domain.investmentresearch",
        ),
        QueryTermCandidate(
            term="大模型",
            source="jd",
            category="domain",
            priority=3,
            evidence="jd",
            first_added_round=0,
            retrieval_role="domain_context",
            queryability="admitted",
            family="domain.llm",
        ),
    ]

    assert select_query_terms(pool, round_no=1, title_anchor_terms=["AI", "投研"]) == ["AI", "投研"]


def test_query_plan_round_one_falls_back_to_primary_plus_domain_term() -> None:
    pool = [
        QueryTermCandidate(
            term="产品经理",
            source="job_title",
            category="role_anchor",
            priority=1,
            evidence="title",
            first_added_round=0,
            retrieval_role="primary_role_anchor",
            queryability="admitted",
            family="role.productmanager",
        ),
        QueryTermCandidate(
            term="人工耳蜗",
            source="notes",
            category="domain",
            priority=2,
            evidence="notes",
            first_added_round=0,
            retrieval_role="domain_context",
            queryability="admitted",
            family="domain.cochlearimplant",
        ),
    ]

    assert select_query_terms(pool, round_no=1, title_anchor_terms=["产品经理"]) == ["产品经理", "人工耳蜗"]
```

- [ ] **Step 2: Run the focused query-plan tests**

Run:

```bash
uv run pytest tests/test_query_plan.py::test_query_plan_round_one_prefers_primary_plus_secondary_title_anchor tests/test_query_plan.py::test_query_plan_round_one_falls_back_to_primary_plus_domain_term -v
```

Expected: failure because `select_query_terms()` still takes `title_anchor_term` and treats all anchors as one role.

- [ ] **Step 3: Change query-plan anchor checks and round-one selection**

In `src/seektalent/retrieval/query_plan.py`, add anchor-role helpers at the top:

```python
def _is_primary_anchor_candidate(item: QueryTermCandidate) -> bool:
    return item.queryability == "admitted" and item.retrieval_role == "primary_role_anchor"


def _is_title_anchor_candidate(item: QueryTermCandidate) -> bool:
    return item.queryability == "admitted" and item.retrieval_role in {
        "primary_role_anchor",
        "secondary_title_anchor",
    }
```

Replace the old `_is_anchor_candidate()` usage in `canonicalize_controller_query_terms()` with:

```python
    primary_anchors = [item for item in candidates if _is_primary_anchor_candidate(item)]
    if len(primary_anchors) != 1:
        raise ValueError("proposed_query_terms must contain exactly one compiler-admitted primary anchor.")
    anchor = primary_anchors[0]
```

Change the selection signature and round-one path:

```python
def select_query_terms(
    query_term_pool: list[QueryTermCandidate],
    *,
    round_no: int,
    title_anchor_terms: list[str],
) -> list[str]:
```

```python
    primary = next(
        item for item in query_term_pool
        if item.active and item.queryability == "admitted" and item.retrieval_role == "primary_role_anchor"
    )
    secondary = next(
        (
            item for item in query_term_pool
            if item.active and item.queryability == "admitted" and item.retrieval_role == "secondary_title_anchor"
        ),
        None,
    )
    if round_no == 1 and secondary is not None:
        return canonicalize_controller_query_terms(
            [primary.term, secondary.term],
            round_no=1,
            title_anchor_terms=title_anchor_terms,
            query_term_pool=query_term_pool,
        )
```

Then keep the existing non-anchor ordering for the fallback path.

- [ ] **Step 4: Update call sites from `title_anchor_term` to `title_anchor_terms`**

In `src/seektalent/controller/react_controller.py`, replace:

```python
title_anchor_term=context.requirement_sheet.title_anchor_term,
```

with:

```python
title_anchor_terms=context.requirement_sheet.title_anchor_terms,
```

In `src/seektalent/runtime/orchestrator.py`, update all `select_query_terms()` and `canonicalize_controller_query_terms()` calls to pass `run_state.requirement_sheet.title_anchor_terms`.

In `src/seektalent/runtime/context_builder.py`, keep the full `RequirementSheet` flowing through contexts; no extra denormalization step is needed once the models carry the list.

- [ ] **Step 5: Add a narrow runtime-audit label for the old failure mode**

In `src/seektalent/runtime/orchestrator.py`, add a helper near the diagnostic assembly:

```python
def _round_failure_labels(requirement_sheet: RequirementSheet, query_terms: list[str]) -> list[str]:
    labels: list[str] = []
    title_terms = {term.casefold() for term in requirement_sheet.title_anchor_terms}
    if len(requirement_sheet.title_anchor_terms) == 2:
        used_title_terms = sum(1 for term in query_terms if term.casefold() in title_terms)
        if used_title_terms < 2:
            labels.append("title_multi_anchor_collapsed")
    return labels
```

Store the returned labels in the round audit object or `search_diagnostics.json` round payload, whichever is already closest to the existing diagnostics assembly.

- [ ] **Step 6: Update the query-plan and runtime assertions**

In `tests/test_query_plan.py`, replace `retrieval_role="role_anchor"` with `retrieval_role="primary_role_anchor"` for existing primary anchors.

In `tests/test_controller_contract.py` and `tests/test_runtime_state_flow.py`, update inline `RequirementSheet(...)` and `RequirementExtractionDraft(...)` instances to use:

```python
title_anchor_terms=["python"]
title_anchor_rationale="title has one stable technical anchor"
```

and replace any `title_anchor_term=requirement_sheet.title_anchor_term` call arguments with `title_anchor_terms=requirement_sheet.title_anchor_terms`.

- [ ] **Step 7: Run the focused suites**

Run:

```bash
uv run pytest tests/test_query_plan.py tests/test_controller_contract.py tests/test_runtime_state_flow.py -v
```

Expected: all three suites pass with the new title-anchor behavior and runtime labels.

- [ ] **Step 8: Commit**

```bash
git add src/seektalent/retrieval/query_plan.py src/seektalent/controller/react_controller.py src/seektalent/runtime/orchestrator.py src/seektalent/runtime/context_builder.py tests/test_query_plan.py tests/test_controller_contract.py tests/test_runtime_state_flow.py
git commit -m "Prefer primary plus secondary title anchors in round one"
```

---

### Task 4: Align Prompts and Diagnostics With the New Runtime Rules

**Files:**
- Modify: `src/seektalent/prompts/requirements.md`
- Modify: `src/seektalent/prompts/controller.md`
- Modify: `src/seektalent/prompts/reflection.md`
- Modify: `tests/test_llm_input_prompts.py`
- Modify: `tests/test_runtime_audit.py`

- [ ] **Step 1: Add prompt and audit tests first**

Add these assertions to `tests/test_llm_input_prompts.py`:

```python
def test_requirements_prompt_describes_one_or_two_title_anchors() -> None:
    prompt = load_prompt("requirements")

    assert "allow one or two title anchors" in prompt.content
    assert "second title anchor is optional" in prompt.content


def test_controller_prompt_prefers_title_title_round_one_pairing() -> None:
    prompt = load_prompt("controller")

    assert "primary_role_anchor" in prompt.content
    assert "secondary_title_anchor" in prompt.content
    assert "Round 1 should prefer primary_role_anchor + secondary_title_anchor" in prompt.content
```

Add a runtime-audit test to `tests/test_runtime_audit.py`:

```python
def test_search_diagnostics_records_title_multi_anchor_collapse_label(tmp_path: Path) -> None:
    diagnostics = {
        "rounds": [
            {
                "round_no": 1,
                "failure_labels": ["title_multi_anchor_collapsed"],
            }
        ]
    }

    assert diagnostics["rounds"][0]["failure_labels"] == ["title_multi_anchor_collapsed"]
```

If an existing helper already loads the real diagnostics artifact, wire the assertion into that helper-backed test instead of keeping the standalone dict.

- [ ] **Step 2: Run the prompt test nodes to verify failure**

Run:

```bash
uv run pytest tests/test_llm_input_prompts.py::test_requirements_prompt_describes_one_or_two_title_anchors tests/test_llm_input_prompts.py::test_controller_prompt_prefers_title_title_round_one_pairing -v
```

Expected: both tests fail because the prompt text still describes a single title anchor and `role_anchor`.

- [ ] **Step 3: Update the requirements, controller, and reflection prompts**

In `src/seektalent/prompts/requirements.md`, replace the single-anchor language with:

```md
- Set `title_anchor_terms` to one or two stable searchable anchors extracted from `job_title`.
- The second title anchor is optional. Use it only when `job_title` clearly contains a second retrieval-defining signal.
- Set `title_anchor_rationale` to a short explanation of why the chosen title anchors capture the retrieval direction.
- Do not invent fake title anchors from JD-only terms, seniority words, org labels, or soft skills.
```

In `src/seektalent/prompts/controller.md`, replace the old round-one and anchor-role rules with:

```md
- Round 1 must return exactly 2 query terms unless runtime explicitly enabled anchor-only mode.
- Round 1 should prefer `primary_role_anchor + secondary_title_anchor` when both title anchors are present and admitted.
- Otherwise Round 1 should use `primary_role_anchor + strongest_domain_term`.
- Round 2 and later must return 2 or 3 query terms: exactly 1 `primary_role_anchor` plus 1~2 admitted support terms.
```

In `src/seektalent/prompts/reflection.md`, replace the old anchor wording with:

```md
- Treat `primary_role_anchor` as the fixed title direction.
- Do not suggest replacing the primary title anchor.
- You may suggest keeping or reusing a `secondary_title_anchor` when it remains the strongest title-side domain signal.
```

- [ ] **Step 4: Update the prompt-rendering tests and audit fixture code**

In `tests/test_llm_input_prompts.py`, update any helper `RequirementSheet(...)` or `RequirementExtractionDraft(...)` construction to use:

```python
title_anchor_terms=["AI", "投研"]
title_anchor_rationale="title has two retrieval-defining signals"
```

In `tests/test_runtime_audit.py`, extend the existing expected round diagnostics payload to include:

```python
"failure_labels": ["title_multi_anchor_collapsed"]
```

only in the case that deliberately omits the secondary title anchor from a two-anchor title.

- [ ] **Step 5: Run the prompt and audit suites**

Run:

```bash
uv run pytest tests/test_llm_input_prompts.py tests/test_runtime_audit.py -v
```

Expected: prompt wording and audit-label coverage both pass.

- [ ] **Step 6: Run the full targeted regression pack**

Run:

```bash
uv run pytest tests/test_requirement_extraction.py tests/test_query_compiler.py tests/test_query_plan.py tests/test_llm_input_prompts.py tests/test_controller_contract.py tests/test_runtime_state_flow.py tests/test_runtime_audit.py -v
```

Expected: all targeted suites pass.

- [ ] **Step 7: Commit**

```bash
git add src/seektalent/prompts/requirements.md src/seektalent/prompts/controller.md src/seektalent/prompts/reflection.md tests/test_llm_input_prompts.py tests/test_runtime_audit.py
git commit -m "Align prompts and diagnostics with title multi-anchor retrieval"
```

---

## Self-Review

### Spec Coverage

- Title can yield one or two searchable anchors: covered by Task 1 and Task 2.
- Secondary anchor is optional and must not be forced: covered by Task 1 tests and Task 2 compiler rules.
- Round-one query prefers title-title, otherwise title-domain: covered by Task 3.
- Notes and active-window relaxation: covered by Task 2.
- Runtime determinism and prompt/runtime/task-prompt alignment: covered by Task 3 and Task 4.
- Lightweight diagnostic labels: covered by Task 3 and Task 4.

### Placeholder Scan

- No `TBD`, `TODO`, `implement later`, or “write tests for the above” placeholders remain.
- Every code-changing step includes concrete snippets or exact replacements.
- Every validation step includes exact commands and expected outcomes.

### Type Consistency

- New public field names are `title_anchor_terms` and `title_anchor_rationale` throughout the plan.
- New anchor roles are `primary_role_anchor` and `secondary_title_anchor` throughout the plan.
- Query-planning signatures consistently switch from `title_anchor_term` to `title_anchor_terms`.

