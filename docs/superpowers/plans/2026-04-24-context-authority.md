# Context Authority Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make reflection advisory-only, let controller explicitly adopt or reject advice, and ensure each LLM prompt shows the context needed for its role.

**Architecture:** Keep the existing readable-prompt style instead of dumping full JSON. Runtime remains the owner of validation and execution; reflection writes advice history only, controller owns next-round term and filter choices, and prompt renderers expose necessary context sections. Tests lock both prompt visibility and authority boundaries.

**Tech Stack:** Python, Pydantic models, pydantic-ai agents, pytest, existing `seektalent` runtime modules.

---

## File Structure

- Modify `src/seektalent/retrieval/query_plan.py`: add a narrow allow-list for inactive admitted terms during controller query canonicalization.
- Modify `src/seektalent/controller/react_controller.py`: derive reflection-backed inactive terms, pass them into validation, expand controller prompt.
- Modify `src/seektalent/runtime/context_builder.py`: pass runtime-only constraints into scoring context.
- Modify `src/seektalent/runtime/orchestrator.py`: stop applying reflection advice directly to the term pool, pass retrieval runtime constraints into scoring, write reflection adoption audit, align repair calls through controller/reflection classes.
- Modify `src/seektalent/models.py`: add `runtime_only_constraints` to `ScoringContext`.
- Modify `src/seektalent/scoring/scorer.py`: render full hard constraints, preferences, and runtime-only constraints.
- Modify `src/seektalent/reflection/critic.py`: render requirements and current runtime term bank; pass original rendered prompt to repair.
- Modify `src/seektalent/runtime/context_builder.py`: add current `query_term_pool` to `ReflectionContext`.
- Modify `src/seektalent/finalize/finalizer.py`: render richer candidate facts for presentation text.
- Modify `src/seektalent/repair.py`: repair from original rendered user prompts, not full hidden context JSON.
- Modify system prompts under `src/seektalent/prompts/*.md`: align authority and visible-context wording.
- Modify tests in `tests/test_llm_input_prompts.py`, `tests/test_controller_contract.py`, `tests/test_runtime_state_flow.py`, `tests/test_context_builder.py`, `tests/test_scoring_cache.py`, and `tests/test_finalizer_contract.py`.
- Modify docs `docs/llm-context-composition.zh-CN.md` and `docs/v-0.2/llm-context-maps.md` after tests pass.

---

### Task 1: Controller Validation Allows Only Evidence-Backed Inactive Terms

**Files:**
- Modify: `src/seektalent/retrieval/query_plan.py`
- Modify: `src/seektalent/controller/react_controller.py`
- Test: `tests/test_controller_contract.py`

- [ ] **Step 1: Write failing controller validation tests**

Add these imports in `tests/test_controller_contract.py` if they are not present:

```python
from seektalent.models import ReflectionFilterAdvice, ReflectionKeywordAdvice
```

Add these tests near the existing controller validation tests:

```python
def test_controller_rejects_inactive_term_without_reflection_advice() -> None:
    context = _controller_context()
    context.query_term_pool = [
        item.model_copy(update={"active": False}) if item.term == "retrieval" else item
        for item in context.query_term_pool
    ]
    decision = SearchControllerDecision(
        thought_summary="Try reserve term.",
        action="search_cts",
        decision_rationale="Use the inactive retrieval reserve term.",
        proposed_query_terms=["python", "retrieval"],
        proposed_filter_plan=ProposedFilterPlan(),
    )

    reason = validate_controller_decision(context=context, decision=decision)

    assert reason is not None
    assert "non-anchor query terms must be active" in reason


def test_controller_accepts_inactive_term_when_previous_reflection_advised_it() -> None:
    context = _controller_context(
        previous_reflection=ReflectionSummaryView(
            decision="continue",
            reflection_summary="Activate retrieval.",
            reflection_rationale="The previous round had shortage.",
        )
    )
    context.query_term_pool = [
        item.model_copy(update={"active": False}) if item.term == "retrieval" else item
        for item in context.query_term_pool
    ]
    context.latest_reflection_keyword_advice = ReflectionKeywordAdvice(
        suggested_activate_terms=["retrieval"]
    )
    context.latest_reflection_filter_advice = ReflectionFilterAdvice()
    decision = SearchControllerDecision(
        thought_summary="Accept reflection advice.",
        action="search_cts",
        decision_rationale="Use retrieval because reflection suggested activating it.",
        proposed_query_terms=["python", "retrieval"],
        proposed_filter_plan=ProposedFilterPlan(),
        response_to_reflection="Accepted the suggested retrieval activation.",
    )

    assert validate_controller_decision(context=context, decision=decision) is None
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_controller_contract.py::test_controller_rejects_inactive_term_without_reflection_advice tests/test_controller_contract.py::test_controller_accepts_inactive_term_when_previous_reflection_advised_it -v
```

Expected: the second test fails because inactive terms are not yet allowed by reflection advice.

- [ ] **Step 3: Add allow-list support to query canonicalization**

In `src/seektalent/retrieval/query_plan.py`, change the signature:

```python
def canonicalize_controller_query_terms(
    proposed_terms: list[str],
    *,
    round_no: int,
    title_anchor_term: str,
    query_term_pool: list[QueryTermCandidate],
    allow_inactive_non_anchor_terms: bool = False,
    allowed_inactive_non_anchor_terms: set[str] | None = None,
    allow_anchor_only: bool = False,
) -> list[str]:
```

Replace the inactive-term block with:

```python
    allowed_inactive = allowed_inactive_non_anchor_terms or set()
    inactive_terms = [
        item.term
        for item in non_anchor_candidates
        if (
            not allow_inactive_non_anchor_terms
            and not item.active
            and item.term.casefold() not in allowed_inactive
        )
    ]
    if inactive_terms:
        raise ValueError(f"non-anchor query terms must be active compiler-admitted terms: {', '.join(inactive_terms)}")
```

- [ ] **Step 4: Derive reflection-backed inactive terms in controller validation**

In `src/seektalent/controller/react_controller.py`, add this helper above `validate_controller_decision`:

```python
def _reflection_backed_inactive_terms(context: ControllerContext) -> set[str]:
    advice = context.latest_reflection_keyword_advice
    if advice is None:
        return set()
    return {
        term.casefold()
        for term in [
            *advice.suggested_activate_terms,
            *advice.suggested_keep_terms,
        ]
    }
```

Update the canonicalization call inside `validate_controller_decision`:

```python
            canonicalize_controller_query_terms(
                decision.proposed_query_terms,
                round_no=context.round_no,
                title_anchor_term=context.requirement_sheet.title_anchor_term,
                query_term_pool=context.query_term_pool,
                allowed_inactive_non_anchor_terms=_reflection_backed_inactive_terms(context),
            )
```

- [ ] **Step 5: Run focused tests**

Run:

```bash
pytest tests/test_controller_contract.py::test_controller_rejects_inactive_term_without_reflection_advice tests/test_controller_contract.py::test_controller_accepts_inactive_term_when_previous_reflection_advised_it -v
```

Expected: both tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/seektalent/retrieval/query_plan.py src/seektalent/controller/react_controller.py tests/test_controller_contract.py
git commit -m "Enforce reflection-backed inactive term adoption"
```

---

### Task 2: Stop Reflection From Mutating the Term Pool

**Files:**
- Modify: `src/seektalent/runtime/orchestrator.py`
- Test: `tests/test_runtime_state_flow.py`

- [ ] **Step 1: Write failing authority-boundary test**

Add this test to `tests/test_runtime_state_flow.py` near `test_runtime_updates_run_state_across_rounds`:

```python
def test_runtime_reflection_does_not_mutate_query_term_pool(tmp_path: Path) -> None:
    settings = make_settings(
        runs_dir=str(tmp_path / "runs"),
        mock_cts=True,
        min_rounds=1,
        max_rounds=1,
    )
    runtime = WorkflowRuntime(settings)
    _install_runtime_stubs(runtime, controller=SequenceController(), resume_scorer=StubScorer())
    runtime_any = cast(Any, runtime)
    runtime_any.requirement_extractor = SingleFamilyRequirementExtractor(include_reserve=True)
    tracer = RunTracer(tmp_path / "trace-runs")
    job_title, jd, notes = _sample_inputs()

    try:
        run_state = asyncio.run(runtime._build_run_state(job_title=job_title, jd=jd, notes=notes, tracer=tracer))
        asyncio.run(runtime._run_rounds(run_state=run_state, tracer=tracer))
    finally:
        tracer.close()

    terms = {item.term: item for item in run_state.retrieval_state.query_term_pool}
    assert terms["trace"].active is False
    assert terms["trace"].priority == 3
    assert len(run_state.retrieval_state.reflection_keyword_advice_history) == 1
    assert run_state.retrieval_state.reflection_keyword_advice_history[0].suggested_keep_terms == ["trace"]
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_runtime_state_flow.py::test_runtime_reflection_does_not_mutate_query_term_pool -v
```

Expected: fails because `_reflect_round()` currently applies `_update_query_term_pool()`.

- [ ] **Step 3: Remove reflection-driven term pool mutation**

In `src/seektalent/runtime/orchestrator.py`, replace this block in `_reflect_round()`:

```python
        run_state.retrieval_state.query_term_pool = self._update_query_term_pool(
            run_state.retrieval_state.query_term_pool,
            advice,
            context.round_no,
        )
        return advice
```

with:

```python
        return advice
```

Delete `_update_query_term_pool()` from `src/seektalent/runtime/orchestrator.py`. Replace the existing direct unit test `test_runtime_query_pool_can_activate_reserve_term_without_losing_all_active_terms` with the new no-mutation integration test above, because reserve adoption now belongs to controller validation and runtime execution rather than reflection post-processing.

- [ ] **Step 4: Run focused test**

Run:

```bash
pytest tests/test_runtime_state_flow.py::test_runtime_reflection_does_not_mutate_query_term_pool -v
```

Expected: pass.

- [ ] **Step 5: Run related state-flow tests**

Run:

```bash
pytest tests/test_runtime_state_flow.py -v
```

Expected: pass, with outdated mutation expectations updated to the new advisory behavior.

- [ ] **Step 6: Commit**

```bash
git add src/seektalent/runtime/orchestrator.py tests/test_runtime_state_flow.py
git commit -m "Keep reflection advice advisory"
```

---

### Task 3: Expand Controller Prompt and System Prompt

**Files:**
- Modify: `src/seektalent/controller/react_controller.py`
- Modify: `src/seektalent/prompts/controller.md`
- Test: `tests/test_llm_input_prompts.py`

- [ ] **Step 1: Write failing prompt visibility test**

Extend `test_controller_prompt_contains_decision_brief_and_exact_data` in `tests/test_llm_input_prompts.py` by setting these context fields:

```python
            latest_reflection_keyword_advice=ReflectionKeywordAdvice(
                suggested_activate_terms=["retrieval"],
                suggested_drop_terms=["internal roadmap"],
            ),
            latest_reflection_filter_advice=ReflectionFilterAdvice(
                suggested_drop_filter_fields=["position"]
            ),
```

Add assertions:

```python
    assert "REFLECTION ADVICE" in prompt
    assert "suggested_activate_terms" in prompt
    assert "retrieval" in prompt
    assert "suggested_drop_filter_fields" in prompt
    assert "position" in prompt
    assert "STRUCTURED CONSTRAINTS" in prompt
    assert "locations" in prompt
    assert "quality_gate_status" in prompt
```

Add imports if missing:

```python
    ReflectionFilterAdvice,
    ReflectionKeywordAdvice,
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_llm_input_prompts.py::test_controller_prompt_contains_decision_brief_and_exact_data -v
```

Expected: fails on `REFLECTION ADVICE`.

- [ ] **Step 3: Add compact JSON helpers to controller prompt renderer**

In `src/seektalent/controller/react_controller.py`, add:

```python
def _compact_json(value: object) -> str:
    if value is None:
        return "(none)"
    if hasattr(value, "model_dump"):
        return json_block("DATA", value.model_dump(mode="json"))
    return json_block("DATA", value)
```

Add `import json` only if you choose a direct `json.dumps` implementation. If using existing `json_block`, no new import is needed.

- [ ] **Step 4: Render controller reflection advice and constraints**

Inside `render_controller_prompt()`, before `exact_data`, add:

```python
    reflection_advice = {
        "keyword_advice": (
            context.latest_reflection_keyword_advice.model_dump(mode="json")
            if context.latest_reflection_keyword_advice is not None
            else None
        ),
        "filter_advice": (
            context.latest_reflection_filter_advice.model_dump(mode="json")
            if context.latest_reflection_filter_advice is not None
            else None
        ),
        "previous_reflection": (
            context.previous_reflection.model_dump(mode="json")
            if context.previous_reflection is not None
            else None
        ),
    }
    structured_constraints = {
        "hard_constraints": sheet.hard_constraints.model_dump(mode="json"),
        "preferences": sheet.preferences.model_dump(mode="json"),
    }
```

Expand the stop guidance section with:

```python
                f"- Fit count: {context.stop_guidance.fit_count}\n"
                f"- Strong fit count: {context.stop_guidance.strong_fit_count}\n"
                f"- High-risk fit count: {context.stop_guidance.high_risk_fit_count}\n"
                f"- Productive rounds: {context.stop_guidance.productive_round_count}\n"
                f"- Zero-gain rounds: {context.stop_guidance.zero_gain_round_count}\n"
                f"- Quality gate status: {context.stop_guidance.quality_gate_status}\n"
                f"- Broadening attempted: {context.stop_guidance.broadening_attempted}\n"
```

Add these prompt sections before `PREVIOUS REFLECTION`:

```python
            json_block("STRUCTURED CONSTRAINTS", structured_constraints),
            json_block("REFLECTION ADVICE", reflection_advice),
```

Expand `latest_search` to include visible details:

```python
    latest_search = (
        "\n".join(
            [
                f"- new={latest.unique_new_count}; shortage={latest.shortage_count}; attempts={latest.fetch_attempt_count}",
                f"- exhausted_reason={latest.exhausted_reason or '(none)'}",
                f"- adapter_notes={', '.join(latest.adapter_notes) or '(none)'}",
                f"- new_candidate_summaries={'; '.join(latest.new_candidate_summaries[:5]) or '(none)'}",
                f"- city_search_summaries={latest.city_search_summaries}",
            ]
        )
        if latest is not None
        else "(none yet)"
    )
```

- [ ] **Step 5: Update controller system prompt**

In `src/seektalent/prompts/controller.md`, replace:

```markdown
- If `action=stop`, ground `decision_rationale` and `stop_reason` only in facts visible in `CONTROLLER_CONTEXT`.
```

with:

```markdown
- If `action=stop`, ground `decision_rationale` and `stop_reason` only in facts visible in the provided controller prompt sections.
```

Replace:

```markdown
- When `previous_reflection` exists, provide `response_to_reflection`.
```

with:

```markdown
- Previous reflection is advisory. When it exists, provide `response_to_reflection` that explicitly accepts, partially accepts, or rejects the visible advice.
- Inactive or reserve terms may be selected only when visible reflection or rescue evidence supports using them.
```

- [ ] **Step 6: Run focused tests**

Run:

```bash
pytest tests/test_llm_input_prompts.py::test_controller_prompt_contains_decision_brief_and_exact_data tests/test_llm_input_prompts.py::test_controller_prompt_says_few_shot_terms_are_not_reusable -v
```

Expected: pass after updating prompt text assertions if they check exact wording.

- [ ] **Step 7: Commit**

```bash
git add src/seektalent/controller/react_controller.py src/seektalent/prompts/controller.md tests/test_llm_input_prompts.py
git commit -m "Expose reflection advice to controller"
```

---

### Task 4: Expand Reflection Prompt and System Prompt

**Files:**
- Modify: `src/seektalent/models.py`
- Modify: `src/seektalent/runtime/context_builder.py`
- Modify: `src/seektalent/reflection/critic.py`
- Modify: `src/seektalent/prompts/reflection.md`
- Test: `tests/test_llm_input_prompts.py`

- [ ] **Step 1: Write failing reflection prompt visibility assertions**

Extend `test_reflection_prompt_contains_round_review_and_candidate_ids` with:

```python
    assert "REQUIREMENTS" in prompt
    assert "JD text" in prompt
    assert "Notes text" in prompt
    assert "Senior Python Engineer" in prompt
    assert "TERM BANK" in prompt
    assert "skill.retrieval" in prompt
    assert "active" in prompt
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_llm_input_prompts.py::test_reflection_prompt_contains_round_review_and_candidate_ids -v
```

Expected: fails on `REQUIREMENTS` or `TERM BANK`.

- [ ] **Step 3: Add current term bank to ReflectionContext**

In `src/seektalent/models.py`, update `ReflectionContext`:

```python
class ReflectionContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    round_no: int
    full_jd: str
    full_notes: str
    requirement_sheet: RequirementSheet
    current_retrieval_plan: RoundRetrievalPlan
    search_observation: SearchObservation
    search_attempts: list[SearchAttempt] = Field(default_factory=list)
    top_candidates: list[ScoredCandidate] = Field(default_factory=list)
    dropped_candidates: list[ScoredCandidate] = Field(default_factory=list)
    scoring_failures: list[ScoringFailure] = Field(default_factory=list)
    sent_query_history: list[SentQueryRecord] = Field(default_factory=list)
    query_term_pool: list[QueryTermCandidate] = Field(default_factory=list)
```

In `src/seektalent/runtime/context_builder.py`, add this field in `build_reflection_context()`:

```python
        query_term_pool=run_state.retrieval_state.query_term_pool,
```

- [ ] **Step 4: Render requirements and current term bank**

In `src/seektalent/reflection/critic.py`, add:

```python
def _term_bank_rows(context: ReflectionContext) -> str:
    tried_terms = {term.casefold() for record in context.sent_query_history for term in record.query_terms}
    term_pool = context.query_term_pool or context.requirement_sheet.initial_query_term_pool
    rows = [
        "| term | family | role | queryability | active | priority | source | tried |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in term_pool:
        tried = "yes" if item.term.casefold() in tried_terms else "no"
        rows.append(
            f"| {item.term} | {item.family} | {item.retrieval_role} | {item.queryability} | "
            f"{item.active} | {item.priority} | {item.source} | {tried} |"
        )
    return "\n".join(rows)
```

Inside `render_reflection_prompt()`, add after `TASK`:

```python
            (
                "REQUIREMENTS\n"
                f"- Role: {context.requirement_sheet.role_title}\n"
                f"- Summary: {context.requirement_sheet.role_summary}\n"
                f"- Must have:\n{_join_terms(context.requirement_sheet.must_have_capabilities) or '(none)'}\n"
                f"- Preferred:\n{_join_terms(context.requirement_sheet.preferred_capabilities) or '(none)'}\n"
                f"- Hard constraints: {context.requirement_sheet.hard_constraints.model_dump(mode='json')}\n"
                f"- Preferences: {context.requirement_sheet.preferences.model_dump(mode='json')}\n"
                f"- JD: {context.full_jd}\n"
                f"- Notes: {context.full_notes or '(none)'}"
            ),
            "TERM BANK\n" + _term_bank_rows(context),
```

- [ ] **Step 5: Update reflection system prompt**

In `src/seektalent/prompts/reflection.md`, add after the advisory stop rule:

```markdown
- Your advice does not mutate the term pool. Controller/runtime decide whether to adopt it in a subsequent step.
```

Replace:

```markdown
- Review whether the next round should adjust query terms or non-location filters, then return structured advice and a stop recommendation.
```

with:

```markdown
- Review whether the next round should consider adjusted query terms or non-location filters, then return structured advice and a stop recommendation.
```

- [ ] **Step 6: Run focused tests**

Run:

```bash
pytest tests/test_llm_input_prompts.py::test_reflection_prompt_contains_round_review_and_candidate_ids tests/test_llm_input_prompts.py::test_reflection_prompt_mentions_rationale_schema_budget -v
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add src/seektalent/models.py src/seektalent/runtime/context_builder.py src/seektalent/reflection/critic.py src/seektalent/prompts/reflection.md tests/test_llm_input_prompts.py
git commit -m "Expose requirements to reflection"
```

---

### Task 5: Expand Scoring Context With Full Constraints

**Files:**
- Modify: `src/seektalent/models.py`
- Modify: `src/seektalent/runtime/context_builder.py`
- Modify: `src/seektalent/runtime/orchestrator.py`
- Modify: `src/seektalent/scoring/scorer.py`
- Test: `tests/test_llm_input_prompts.py`
- Test: `tests/test_context_builder.py`
- Test: `tests/test_scoring_cache.py`

- [ ] **Step 1: Write failing scoring prompt assertions**

In `tests/test_llm_input_prompts.py`, update `test_scoring_prompt_contains_policy_resume_card_and_exact_resume_id` so the `ScoringPolicy.hard_constraints` includes non-location fields:

```python
                hard_constraints=HardConstraintSlots(
                    locations=["上海市"],
                    school_names=["复旦大学"],
                    degree_requirement=DegreeRequirement(canonical_degree="本科及以上", raw_text="本科及以上"),
                    experience_requirement=ExperienceRequirement(min_years=3, max_years=5, raw_text="3-5年"),
                    gender_requirement=GenderRequirement(canonical_gender="男", raw_text="男性优先"),
                    age_requirement=AgeRequirement(max_age=35, raw_text="35岁以下"),
                    company_names=["阿里巴巴"],
                ),
                preferences=PreferenceSlots(
                    preferred_companies=["字节跳动"],
                    preferred_domains=["AI"],
                    preferred_backgrounds=["大厂"],
                    preferred_query_terms=["RAG"],
                ),
```

Add imports for `AgeRequirement`, `DegreeRequirement`, `ExperienceRequirement`, `GenderRequirement`, and `PreferenceSlots`.

Pass runtime constraints into `ScoringContext`:

```python
            runtime_only_constraints=[
                RuntimeConstraint(
                    field="age_requirement",
                    normalized_value=["max=35"],
                    source="notes",
                    rationale="Age not projected to CTS.",
                    blocking=False,
                )
            ],
```

Add assertions:

```python
    assert "Hard constraints" in prompt
    assert "本科及以上" in prompt
    assert "3-5年" in prompt
    assert "35岁以下" in prompt
    assert "阿里巴巴" in prompt
    assert "Preferences" in prompt
    assert "字节跳动" in prompt
    assert "Runtime-only constraints" in prompt
    assert "age_requirement" in prompt
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_llm_input_prompts.py::test_scoring_prompt_contains_policy_resume_card_and_exact_resume_id -v
```

Expected: fails because scoring prompt does not render these fields.

- [ ] **Step 3: Add runtime-only constraints to ScoringContext**

In `src/seektalent/models.py`, update `ScoringContext`:

```python
class ScoringContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    round_no: int
    scoring_policy: ScoringPolicy
    normalized_resume: NormalizedResume
    requirement_sheet_sha256: str = Field(min_length=1)
    runtime_only_constraints: list[RuntimeConstraint] = Field(default_factory=list)
```

- [ ] **Step 4: Pass runtime-only constraints through context builder and orchestrator**

In `src/seektalent/runtime/context_builder.py`, update the signature:

```python
def build_scoring_context(
    *,
    run_state: RunState,
    round_no: int,
    normalized_resume,
    runtime_only_constraints: list[RuntimeConstraint] | None = None,
) -> ScoringContext:
```

Return:

```python
        runtime_only_constraints=list(runtime_only_constraints or []),
```

Import `RuntimeConstraint` from `seektalent.models`.

In `src/seektalent/runtime/orchestrator.py`, update `_score_round()` signature:

```python
    async def _score_round(
        self,
        *,
        round_no: int,
        new_candidates: list[ResumeCandidate],
        run_state: RunState,
        tracer: RunTracer,
        runtime_only_constraints: list[RuntimeConstraint],
    ) -> tuple[list[ScoredCandidate], list[PoolDecision], list[ScoredCandidate]]:
```

Pass it at the call site:

```python
                runtime_only_constraints=retrieval_plan.runtime_only_constraints,
```

Pass it to `build_scoring_context()`:

```python
                runtime_only_constraints=runtime_only_constraints,
```

- [ ] **Step 5: Render full scoring policy**

In `src/seektalent/scoring/scorer.py`, add:

```python
def _jsonish(value: object) -> str:
    if hasattr(value, "model_dump"):
        return str(value.model_dump(mode="json"))
    return str(value)
```

Replace the policy block in `render_scoring_prompt()` with:

```python
            (
                "SCORING POLICY\n"
                f"- Role: {policy.role_title}\n"
                f"- Summary: {policy.role_summary}\n"
                f"- Must have:\n{_lines(policy.must_have_capabilities)}\n"
                f"- Preferred:\n{_lines(policy.preferred_capabilities)}\n"
                f"- Exclusions:\n{_lines(policy.exclusion_signals)}\n"
                f"- Hard constraints: {policy.hard_constraints.model_dump(mode='json')}\n"
                f"- Preferences: {policy.preferences.model_dump(mode='json')}\n"
                f"- Runtime-only constraints: {[item.model_dump(mode='json') for item in context.runtime_only_constraints] or '(none)'}\n"
                f"- Rationale: {policy.scoring_rationale}"
            ),
```

- [ ] **Step 6: Update tests that construct ScoringContext**

Run:

```bash
rg -n "ScoringContext\\(" tests src/seektalent
```

For test constructors that do not care about runtime-only constraints, no change is needed because the field has a default. For assertions in `tests/test_context_builder.py`, add:

```python
    assert scoring_context.runtime_only_constraints == []
```

- [ ] **Step 7: Run focused tests**

Run:

```bash
pytest tests/test_llm_input_prompts.py::test_scoring_prompt_contains_policy_resume_card_and_exact_resume_id tests/test_context_builder.py tests/test_scoring_cache.py -v
```

Expected: pass after updating cache expectations if the rendered prompt hash changes.

- [ ] **Step 8: Commit**

```bash
git add src/seektalent/models.py src/seektalent/runtime/context_builder.py src/seektalent/runtime/orchestrator.py src/seektalent/scoring/scorer.py tests/test_llm_input_prompts.py tests/test_context_builder.py tests/test_scoring_cache.py
git commit -m "Expose full scoring constraints"
```

---

### Task 6: Expand Finalizer Prompt With Existing Candidate Facts

**Files:**
- Modify: `src/seektalent/finalize/finalizer.py`
- Test: `tests/test_llm_input_prompts.py`
- Test: `tests/test_finalizer_contract.py`

- [ ] **Step 1: Write failing finalizer prompt assertions**

In `tests/test_llm_input_prompts.py`, extend `test_finalizer_prompt_contains_ranked_list_and_exact_order`:

```python
    assert "matched_must_haves" in prompt
    assert "matched_preferences" in prompt
    assert "strengths" in prompt
    assert "weaknesses" in prompt
    assert "risk_flags" in prompt
    assert "short tenure" in prompt
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_llm_input_prompts.py::test_finalizer_prompt_contains_ranked_list_and_exact_order -v
```

Expected: fails because the finalizer prompt only renders summary scoring fields.

- [ ] **Step 3: Render richer candidate lines**

In `src/seektalent/finalize/finalizer.py`, replace `candidate_lines` with:

```python
    candidate_lines = [
        (
            f"{rank}. {candidate.resume_id}: score={candidate.overall_score}, "
            f"fit={candidate.fit_bucket}, must={candidate.must_have_match_score}, "
            f"risk={candidate.risk_score}; {candidate.reasoning_summary}; "
            f"matched_must_haves={candidate.matched_must_haves[:4]}; "
            f"matched_preferences={candidate.matched_preferences[:4]}; "
            f"strengths={candidate.strengths[:3]}; "
            f"weaknesses={candidate.weaknesses[:3]}; "
            f"risk_flags={candidate.risk_flags[:3]}"
        )
        for rank, candidate in enumerate(ranked_candidates, start=1)
    ]
```

- [ ] **Step 4: Run finalizer tests**

Run:

```bash
pytest tests/test_llm_input_prompts.py::test_finalizer_prompt_contains_ranked_list_and_exact_order tests/test_finalizer_contract.py -v
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/seektalent/finalize/finalizer.py tests/test_llm_input_prompts.py tests/test_finalizer_contract.py
git commit -m "Expose candidate facts to finalizer"
```

---

### Task 7: Align Repair Prompts With Original Visible Prompts

**Files:**
- Modify: `src/seektalent/repair.py`
- Modify: `src/seektalent/controller/react_controller.py`
- Modify: `src/seektalent/reflection/critic.py`
- Test: `tests/test_llm_fail_fast.py`
- Test: `tests/test_reflection_contract.py`

- [ ] **Step 1: Update repair function signatures**

In `src/seektalent/repair.py`, change `repair_controller_decision()` signature:

```python
async def repair_controller_decision(
    settings: AppSettings,
    prompt: LoadedPrompt,
    source_user_prompt: str,
    decision: ControllerDecision,
    reason: str,
) -> tuple[ControllerDecision, ProviderUsageSnapshot | None]:
```

Change its `user_prompt` body:

```python
            json_block(
                "SOURCE_PROMPT",
                {
                    "name": prompt.name,
                    "sha256": prompt.sha256,
                    "content": prompt.content,
                },
            ),
            json_block("SOURCE_USER_PROMPT", {"content": source_user_prompt}),
            json_block("CURRENT_DECISION", decision.model_dump(mode="json")),
```

Remove `json_block("CONTROLLER_CONTEXT", ...)` from the model-facing repair prompt.

Change `repair_reflection_draft()` signature:

```python
async def repair_reflection_draft(
    settings: AppSettings,
    prompt: LoadedPrompt,
    source_user_prompt: str,
    draft: ReflectionAdviceDraft,
    reason: str,
) -> tuple[ReflectionAdviceDraft, ProviderUsageSnapshot | None]:
```

Change its prompt body:

```python
            json_block("SOURCE_USER_PROMPT", {"content": source_user_prompt}),
            json_block("CURRENT_DRAFT", draft.model_dump(mode="json")),
```

Remove `json_block("REFLECTION_CONTEXT", ...)` from the model-facing repair prompt.

- [ ] **Step 2: Pass rendered prompts from controller**

In `src/seektalent/controller/react_controller.py`, update `decide()`:

```python
        source_user_prompt = render_controller_prompt(context)
        decision = await self._decide_live(
            context=context,
            prompt_cache_key=prompt_cache_key,
            source_user_prompt=source_user_prompt,
        )
```

Update `_decide_live()` signature and body:

```python
    async def _decide_live(
        self,
        *,
        context: ControllerContext,
        prompt_cache_key: str | None = None,
        source_user_prompt: str | None = None,
    ) -> ControllerDecision:
        agent = self._get_agent() if prompt_cache_key is None else self._get_agent(prompt_cache_key=prompt_cache_key)
        result = await agent.run(source_user_prompt or render_controller_prompt(context), deps=context)
        self.last_provider_usage = provider_usage_from_result(result)
        return result.output
```

Update repair call:

```python
        repaired, repair_usage = await repair_controller_decision(
            self.settings,
            self.prompt,
            source_user_prompt,
            decision,
            reason,
        )
```

When doing the full retry, pass the same source prompt:

```python
        retried = await self._decide_live(
            context=context,
            prompt_cache_key=prompt_cache_key,
            source_user_prompt=source_user_prompt,
        )
```

- [ ] **Step 3: Pass rendered prompts from reflection**

In `src/seektalent/reflection/critic.py`, compute `source_user_prompt = render_reflection_prompt(context)` at the start of `reflect()`, pass it into `_reflect_live()`, and pass it into `repair_reflection_draft()`.

Update `_reflect_live()`:

```python
    async def _reflect_live(
        self,
        *,
        context: ReflectionContext,
        prompt_cache_key: str | None = None,
        source_user_prompt: str | None = None,
    ) -> ReflectionAdviceDraft:
        agent = self._get_agent() if prompt_cache_key is None else self._get_agent(prompt_cache_key=prompt_cache_key)
        result = await agent.run(source_user_prompt or render_reflection_prompt(context))
        self.last_provider_usage = provider_usage_from_result(result)
        return result.output
```

Update the repair call:

```python
            repaired, repair_usage = await repair_reflection_draft(
                self.settings,
                self.prompt,
                source_user_prompt,
                repaired,
                repaired_reason,
            )
```

- [ ] **Step 4: Run repair-related tests**

Run:

```bash
pytest tests/test_llm_fail_fast.py tests/test_reflection_contract.py -v
```

Expected: pass after updating monkeypatches or stubs that call the old repair signatures.

- [ ] **Step 5: Commit**

```bash
git add src/seektalent/repair.py src/seektalent/controller/react_controller.py src/seektalent/reflection/critic.py tests/test_llm_fail_fast.py tests/test_reflection_contract.py
git commit -m "Align repair prompts with visible context"
```

---

### Task 8: Add Reflection Adoption Audit

**Files:**
- Modify: `src/seektalent/runtime/orchestrator.py`
- Test: `tests/test_runtime_audit.py`

- [ ] **Step 1: Write failing audit test**

In `tests/test_runtime_audit.py`, add an assertion to the existing round diagnostic test that reads a diagnostic round:

```python
    adoption = diagnostic_round["reflection_advice_application"]
    assert adoption["controller_response"] is not None
    assert "suggested_activate_terms" in adoption
    assert "accepted_terms" in adoption
    assert "ignored_terms" in adoption
```

- [ ] **Step 2: Run audit test to verify failure**

Run:

```bash
pytest tests/test_runtime_audit.py -k reflection_advice_application -v
```

Expected: fails because the diagnostic object has no adoption section.

- [ ] **Step 3: Add deterministic adoption helper**

In `src/seektalent/runtime/orchestrator.py`, add:

```python
    def _reflection_advice_application(self, *, run_state: RunState, round_state: RoundState) -> dict[str, object]:
        previous_reflection = None
        if round_state.round_no > 1:
            previous_index = round_state.round_no - 2
            if previous_index >= 0:
                previous_reflection = run_state.round_history[previous_index].reflection_advice
        if previous_reflection is None:
            return {
                "suggested_activate_terms": [],
                "suggested_keep_terms": [],
                "suggested_deprioritize_terms": [],
                "suggested_drop_terms": [],
                "suggested_filter_fields": [],
                "accepted_terms": [],
                "ignored_terms": [],
                "accepted_filter_fields": [],
                "ignored_filter_fields": [],
                "controller_response": round_state.controller_decision.response_to_reflection,
            }
        selected_terms = (
            set(term.casefold() for term in round_state.controller_decision.proposed_query_terms)
            if isinstance(round_state.controller_decision, SearchControllerDecision)
            else set()
        )
        suggested_terms = unique_strings(
            [
                *previous_reflection.keyword_advice.suggested_activate_terms,
                *previous_reflection.keyword_advice.suggested_keep_terms,
            ]
        )
        accepted_terms = [term for term in suggested_terms if term.casefold() in selected_terms]
        ignored_terms = [term for term in suggested_terms if term.casefold() not in selected_terms]
        selected_filter_fields = (
            set(round_state.controller_decision.proposed_filter_plan.added_filter_fields)
            | set(round_state.controller_decision.proposed_filter_plan.dropped_filter_fields)
            if isinstance(round_state.controller_decision, SearchControllerDecision)
            else set()
        )
        suggested_filter_fields = unique_strings(
            [
                *previous_reflection.filter_advice.suggested_keep_filter_fields,
                *previous_reflection.filter_advice.suggested_drop_filter_fields,
                *previous_reflection.filter_advice.suggested_add_filter_fields,
            ]
        )
        return {
            "suggested_activate_terms": previous_reflection.keyword_advice.suggested_activate_terms,
            "suggested_keep_terms": previous_reflection.keyword_advice.suggested_keep_terms,
            "suggested_deprioritize_terms": previous_reflection.keyword_advice.suggested_deprioritize_terms,
            "suggested_drop_terms": previous_reflection.keyword_advice.suggested_drop_terms,
            "suggested_filter_fields": suggested_filter_fields,
            "accepted_terms": accepted_terms,
            "ignored_terms": ignored_terms,
            "accepted_filter_fields": [field for field in suggested_filter_fields if field in selected_filter_fields],
            "ignored_filter_fields": [field for field in suggested_filter_fields if field not in selected_filter_fields],
            "controller_response": round_state.controller_decision.response_to_reflection,
        }
```

- [ ] **Step 4: Add adoption object to diagnostic round**

In the method that builds round diagnostic payloads, add:

```python
            "reflection_advice_application": self._reflection_advice_application(
                run_state=run_state,
                round_state=round_state,
            ),
```

Use the explicit-argument helper shape:

```python
    def _reflection_advice_application(self, *, run_state: RunState, round_state: RoundState) -> dict[str, object]:
```

- [ ] **Step 5: Run audit tests**

Run:

```bash
pytest tests/test_runtime_audit.py -v
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add src/seektalent/runtime/orchestrator.py tests/test_runtime_audit.py
git commit -m "Audit reflection advice adoption"
```

---

### Task 9: Update Context Documentation

**Files:**
- Modify: `docs/llm-context-composition.zh-CN.md`
- Modify: `docs/v-0.2/llm-context-maps.md`
- Modify: `docs/superpowers/specs/2026-04-24-context-authority-design.md` only if implementation decisions diverged from the design.

- [ ] **Step 1: Update Chinese context composition doc**

In `docs/llm-context-composition.zh-CN.md`, update the controller section so it says:

```markdown
Controller 会看到上一轮 reflection 的完整建议字段，但 reflection 只有建议权。Controller 需要在 `response_to_reflection` 中说明采纳、部分采纳或拒绝。Runtime 只执行 Controller 的结构化决定，并校验查询词、筛选字段和停止条件。
```

Update the reflection section so it says:

```markdown
Reflection 不直接修改 `query_term_pool`，也不决定下一轮 query。它只输出关键词、筛选和停止建议。下一轮 Controller 会看到这些建议，并决定是否采纳。
```

Update the scoring section so it says:

```markdown
Scoring prompt 会包含完整的结构化 hard constraints、preferences，以及本轮未能投到 CTS 的 runtime-only constraints。评分仍然只针对单份简历，不比较候选人。
```

- [ ] **Step 2: Update v0.2 context map**

In `docs/v-0.2/llm-context-maps.md`, update the Controller mindmap bullet from `latest reflection summary` to:

```markdown
latest reflection advice
  keyword advice
  filter advice
  stop advice
  summary and rationale
```

Update the Reflection bullet to include:

```markdown
current runtime term bank
full requirement sheet
```

Add a note:

```markdown
Reflection advice is advisory-only. Runtime records advice history, but controller/runtime own adoption and execution.
```

- [ ] **Step 3: Run doc check commands**

Run:

```bash
rg -n "reflection.*directly|直接修改|latest reflection summary|CONTROLLER_CONTEXT" docs src/seektalent/prompts
```

Expected: any remaining hits are either accurate historical descriptions or updated to the new advisory-only wording.

- [ ] **Step 4: Commit**

```bash
git add docs/llm-context-composition.zh-CN.md docs/v-0.2/llm-context-maps.md docs/superpowers/specs/2026-04-24-context-authority-design.md
git commit -m "Document context authority semantics"
```

---

### Task 10: Full Verification

**Files:**
- No source edits expected.

- [ ] **Step 1: Run focused test suite**

Run:

```bash
pytest tests/test_llm_input_prompts.py tests/test_controller_contract.py tests/test_context_builder.py tests/test_runtime_state_flow.py tests/test_filter_projection.py tests/test_scoring_cache.py tests/test_finalizer_contract.py tests/test_reflection_contract.py tests/test_runtime_audit.py -v
```

Expected: pass.

- [ ] **Step 2: Run full test suite**

Run:

```bash
pytest -q
```

Expected: pass.

- [ ] **Step 3: Run lint if configured**

Run:

```bash
ruff check src tests
```

Expected: pass.

- [ ] **Step 4: Inspect final git state**

Run:

```bash
git status --short
git log --oneline -8
```

Expected: clean worktree after the final verification commit, with the task commits visible.
