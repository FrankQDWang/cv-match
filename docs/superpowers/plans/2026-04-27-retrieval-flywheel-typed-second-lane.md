# Retrieval Flywheel And Typed Second Lane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 1 retrieval flywheel foundation: stable query identity, full lane attribution, typed second-lane routing, `PRF v1` from current candidate feedback, and experiment-ready replay artifacts for `prf_probe` versus `generic_explore`.

**Architecture:** Keep the runtime as a controlled workflow. Introduce query identity and attribution primitives first, then move second-lane policy selection out of the orchestration tangle into a dedicated runtime helper, then promote `candidate_feedback` into a bounded `PRF v1` second-lane policy, and finally add reproducible replay and benchmark support. Keep company handling isolated: no mainline company rewrite, no company-driven second lane, no company scoring/rerank in the primary Phase 1 comparison.

**Tech Stack:** Python 3.12, Pydantic models, existing SeekTalent runtime split modules, pytest, existing benchmark harness and run artifacts

---

## File Map

### New files

- Create: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/retrieval/query_identity.py`
  Purpose: Build `job_intent_fingerprint`, `query_fingerprint`, `query_instance_id`, and the canonical query-spec hash helpers.

- Create: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/second_lane_runtime.py`
  Purpose: Own typed second-lane selection, second-lane decision artifacts, and the `prf_probe if safe else generic_explore` routing contract.

- Create: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/candidate_feedback/policy.py`
  Purpose: Turn the shared extraction output into a `PRF v1` policy decision, separate from late-rescue use.

- Create: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_query_identity.py`
  Purpose: Lock query fingerprint and canonical query-spec behavior.

### Modified files

- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/models.py`
  Purpose: Add `CanonicalQuerySpec`, `QueryResumeHit`, `SecondLaneDecision`, lane-type literals, and new attribution fields.

- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/retrieval_runtime.py`
  Purpose: Carry lane metadata, emit `query_resume_hits`, and support score-aware second-lane refill decisions.

- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/orchestrator.py`
  Purpose: Wire query identity, second-lane runtime, new artifacts, and the typed-lane round loop.

- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/runtime_diagnostics.py`
  Purpose: Compute query outcome labels and replay snapshot fields.

- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/candidate_feedback/models.py`
  Purpose: Represent PRF expression families and expression classification.

- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/candidate_feedback/extraction.py`
  Purpose: Make extraction return shared evidence structures that `PRF v1` and late rescue can both consume.

- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/rescue_execution_runtime.py`
  Purpose: Reuse the shared extractor under a `late_rescue` identity without sharing PRF policy state.

- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_candidate_feedback.py`
  Purpose: Lock expression-family extraction, term classification, and PRF gate rules.

- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_state_flow.py`
  Purpose: Lock typed second-lane selection, PRF rejection artifacts, and post-score refill behavior.

- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_audit.py`
  Purpose: Lock new artifacts such as `query_resume_hits.json`, `second_lane_decision.json`, and replay snapshot fields.

- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_evaluation.py`
  Purpose: Lock outcome-label definitions and replay-row shape.

- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_experiment_entrypoints.py`
  Purpose: Lock baseline-versus-candidate experiment wiring and company-isolation defaults.

- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/tools/run_global_benchmark.py`
  Purpose: Add baseline-versus-candidate second-lane comparison entrypoints.

- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/experiments/baseline_evaluation.py`
  Purpose: Add typed second-lane experiment modes and replay row export.

- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/docs/outputs.md`
  Purpose: Document new artifacts and their intended use.

## Task 1: Add Query Identity And Canonical Query Specification

**Files:**
- Create: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/retrieval/query_identity.py`
- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/models.py`
- Test: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_query_identity.py`

- [ ] **Step 1: Write the failing query identity tests**

```python
from seektalent.models import CanonicalQuerySpec
from seektalent.retrieval.query_identity import (
    build_job_intent_fingerprint,
    build_query_fingerprint,
    build_query_instance_id,
)


def _spec() -> CanonicalQuerySpec:
    return CanonicalQuerySpec(
        lane_type="generic_explore",
        anchors=["python"],
        expansion_terms=["resume matching"],
        promoted_prf_expression=None,
        generic_explore_terms=["trace"],
        required_terms=["python"],
        optional_terms=["resume matching", "trace"],
        excluded_terms=[],
        location_key="shanghai",
        provider_filters={"city": "上海"},
        boolean_template="required_plus_optional",
        rendered_provider_query='python "resume matching" trace',
        provider_name="cts",
        source_plan_version="2",
    )


def test_query_fingerprint_is_stable_across_runs() -> None:
    spec = _spec()
    job_fingerprint = build_job_intent_fingerprint(
        role_title="Python Engineer",
        must_haves=["python", "resume matching"],
        preferred_terms=["trace"],
    )

    first = build_query_fingerprint(
        job_intent_fingerprint=job_fingerprint,
        lane_type="generic_explore",
        canonical_query_spec=spec,
        policy_version="typed-second-lane-v1",
    )
    second = build_query_fingerprint(
        job_intent_fingerprint=job_fingerprint,
        lane_type="generic_explore",
        canonical_query_spec=spec,
        policy_version="typed-second-lane-v1",
    )

    assert first == second


def test_query_instance_id_changes_by_run_but_not_fingerprint() -> None:
    spec = _spec()
    job_fingerprint = build_job_intent_fingerprint(
        role_title="Python Engineer",
        must_haves=["python", "resume matching"],
        preferred_terms=["trace"],
    )
    query_fingerprint = build_query_fingerprint(
        job_intent_fingerprint=job_fingerprint,
        lane_type="generic_explore",
        canonical_query_spec=spec,
        policy_version="typed-second-lane-v1",
    )

    first = build_query_instance_id(
        run_id="run-a",
        round_no=2,
        lane_type="generic_explore",
        query_fingerprint=query_fingerprint,
        source_plan_version=2,
    )
    second = build_query_instance_id(
        run_id="run-b",
        round_no=2,
        lane_type="generic_explore",
        query_fingerprint=query_fingerprint,
        source_plan_version=2,
    )

    assert first != second
    assert query_fingerprint
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_query_identity.py -q`
Expected: FAIL with import or attribute errors because `CanonicalQuerySpec` and the query identity helpers do not exist yet.

- [ ] **Step 3: Add canonical query spec and query identity helpers**

```python
# /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/models.py
class CanonicalQuerySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lane_type: str
    anchors: list[str] = Field(default_factory=list)
    expansion_terms: list[str] = Field(default_factory=list)
    promoted_prf_expression: str | None = None
    generic_explore_terms: list[str] = Field(default_factory=list)
    required_terms: list[str] = Field(default_factory=list)
    optional_terms: list[str] = Field(default_factory=list)
    excluded_terms: list[str] = Field(default_factory=list)
    location_key: str | None = None
    provider_filters: dict[str, Any] = Field(default_factory=dict)
    boolean_template: str
    rendered_provider_query: str
    provider_name: str
    source_plan_version: str
```

```python
# /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/retrieval/query_identity.py
from __future__ import annotations

import json
from hashlib import sha1

from seektalent.models import CanonicalQuerySpec


def _stable_hash(payload: dict[str, object]) -> str:
    blob = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return sha1(blob.encode("utf-8")).hexdigest()


def build_job_intent_fingerprint(*, role_title: str, must_haves: list[str], preferred_terms: list[str]) -> str:
    return _stable_hash(
        {
            "role_title": role_title.strip(),
            "must_haves": sorted(item.strip().casefold() for item in must_haves if item.strip()),
            "preferred_terms": sorted(item.strip().casefold() for item in preferred_terms if item.strip()),
        }
    )


def build_query_fingerprint(
    *,
    job_intent_fingerprint: str,
    lane_type: str,
    canonical_query_spec: CanonicalQuerySpec,
    policy_version: str,
) -> str:
    return _stable_hash(
        {
            "job_intent_fingerprint": job_intent_fingerprint,
            "lane_type": lane_type,
            "canonical_query_spec": canonical_query_spec.model_dump(mode="json"),
            "policy_version": policy_version,
        }
    )


def build_query_instance_id(
    *,
    run_id: str,
    round_no: int,
    lane_type: str,
    query_fingerprint: str,
    source_plan_version: int,
) -> str:
    return _stable_hash(
        {
            "run_id": run_id,
            "round_no": round_no,
            "lane_type": lane_type,
            "query_fingerprint": query_fingerprint,
            "source_plan_version": source_plan_version,
        }
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_query_identity.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/models.py \
        /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/retrieval/query_identity.py \
        /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_query_identity.py
git commit -m "Add query identity and canonical query spec"
```

## Task 2: Add Query-Resume Hit Logging And Second-Lane Decision Artifacts

**Files:**
- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/models.py`
- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/retrieval_runtime.py`
- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/orchestrator.py`
- Test: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_audit.py`
- Test: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_state_flow.py`

- [ ] **Step 1: Write failing artifact tests**

```python
def test_round_search_records_query_resume_hits_for_all_lanes(tmp_path: Path) -> None:
    settings = make_settings(runs_dir=str(tmp_path / "runs"), mock_cts=True, min_rounds=1, max_rounds=2)
    runtime = WorkflowRuntime(settings)
    _install_runtime_stubs(runtime, controller=SequenceController(), resume_scorer=StubScorer())
    tracer = RunTracer(tmp_path / "trace")

    try:
        run_state = asyncio.run(runtime._build_run_state(*_sample_inputs(), tracer=tracer))
        asyncio.run(runtime._run_rounds(run_state=run_state, tracer=tracer, progress_callback=None))
    finally:
        tracer.close()

    hits = json.loads((tracer.run_dir / "rounds" / "round_02" / "query_resume_hits.json").read_text())
    assert any(row["lane_type"] == "exploit" for row in hits)
    assert any(row["lane_type"] == "generic_explore" for row in hits)
    assert all("query_instance_id" in row for row in hits)
    assert all("query_fingerprint" in row for row in hits)


def test_runtime_records_second_lane_fallback_when_prf_is_rejected(tmp_path: Path) -> None:
    settings = make_settings(runs_dir=str(tmp_path / "runs"), mock_cts=True, min_rounds=1, max_rounds=2)
    runtime = WorkflowRuntime(settings)
    _install_runtime_stubs(runtime, controller=SequenceController(), resume_scorer=StubScorer())
    tracer = RunTracer(tmp_path / "trace")

    try:
        run_state = asyncio.run(runtime._build_run_state(*_sample_inputs(), tracer=tracer))
        asyncio.run(runtime._run_rounds(run_state=run_state, tracer=tracer, progress_callback=None))
    finally:
        tracer.close()

    decision = json.loads((tracer.run_dir / "rounds" / "round_02" / "second_lane_decision.json").read_text())
    assert decision["attempted_prf"] is True
    assert decision["prf_gate_passed"] is False
    assert decision["fallback_lane_type"] == "generic_explore"
    assert decision["reject_reasons"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_audit.py::test_round_search_records_query_resume_hits_for_all_lanes /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_state_flow.py::test_runtime_records_second_lane_fallback_when_prf_is_rejected -q`
Expected: FAIL because `query_resume_hits.json` and `second_lane_decision.json` do not exist yet.

- [ ] **Step 3: Add models and artifact writes**

```python
# /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/models.py
class ResumeCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resume_id: str
    source_resume_id: str | None = None
    snapshot_sha256: str = ""
    dedup_key: str
    used_fallback_id: bool = False
    source_round: int | None = None
    first_query_instance_id: str | None = None
    first_query_fingerprint: str | None = None
    first_lane_type: str | None = None
    first_location_key: str | None = None
    first_location_type: str | None = None
    first_batch_no: int | None = None
    age: int | None = None
    gender: str | None = None
    now_location: str | None = None
    work_year: int | None = None
    expected_location: str | None = None
    expected_job_category: str | None = None
    expected_industry: str | None = None
    expected_salary: str | None = None
    active_status: str | None = None
    job_state: str | None = None
    education_summaries: list[str] = Field(default_factory=list)
    work_experience_summaries: list[str] = Field(default_factory=list)
    project_names: list[str] = Field(default_factory=list)
    work_summaries: list[str] = Field(default_factory=list)
    search_text: str
    raw: dict[str, Any] = Field(default_factory=dict)


class QueryResumeHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    query_instance_id: str
    query_fingerprint: str
    resume_id: str
    round_no: int
    lane_type: str
    location_key: str | None = None
    batch_no: int
    rank_in_query: int
    provider_score_if_any: float | None = None
    was_new_to_pool: bool
    was_duplicate: bool
    scored_fit_bucket: FitBucket | None = None
    final_candidate_status: str | None = None


class SecondLaneDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    round_no: int
    attempted_prf: bool
    prf_gate_passed: bool
    reject_reasons: list[str] = Field(default_factory=list)
    fallback_lane_type: str | None = None
    fallback_query_fingerprint: str | None = None
    no_fetch_reason: str | None = None
```

```python
# /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/retrieval_runtime.py
candidate = candidate.model_copy(
    update={
        "first_query_instance_id": query_instance_id,
        "first_query_fingerprint": query_fingerprint,
        "first_lane_type": lane_type,
        "first_location_key": location_key,
        "first_location_type": location_type,
        "first_batch_no": batch_no,
    }
)
query_resume_hits.append(
    QueryResumeHit(
        run_id=run_id,
        query_instance_id=query_instance_id,
        query_fingerprint=query_fingerprint,
        resume_id=candidate.resume_id,
        round_no=round_no,
        lane_type=lane_type,
        location_key=location_key,
        batch_no=batch_no,
        rank_in_query=rank_in_query,
        was_new_to_pool=was_new_to_pool,
        was_duplicate=not was_new_to_pool,
    )
)
```

```python
# /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/orchestrator.py
tracer.write_json(
    f"rounds/round_{round_no:02d}/second_lane_decision.json",
    second_lane_decision.model_dump(mode="json"),
)
tracer.write_json(
    f"rounds/round_{round_no:02d}/query_resume_hits.json",
    [item.model_dump(mode="json") for item in query_resume_hits],
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_audit.py::test_round_search_records_query_resume_hits_for_all_lanes /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_state_flow.py::test_runtime_records_second_lane_fallback_when_prf_is_rejected -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/models.py \
        /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/retrieval_runtime.py \
        /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/orchestrator.py \
        /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_audit.py \
        /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_state_flow.py
git commit -m "Add query hit and second-lane decision artifacts"
```

## Task 3: Promote Candidate Feedback Extraction Into PRF Expression Families

**Files:**
- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/candidate_feedback/models.py`
- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/candidate_feedback/extraction.py`
- Create: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/candidate_feedback/policy.py`
- Test: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_candidate_feedback.py`

- [ ] **Step 1: Write the failing PRF expression tests**

```python
def test_prf_expression_family_keeps_short_phrase_as_one_unit() -> None:
    decision = build_feedback_decision(
        seed_resumes=[
            _scored_candidate("seed-1", evidence=["distributed systems", "python"]),
            _scored_candidate("seed-2", evidence=["distributed systems", "python"]),
        ],
        negative_resumes=[],
        existing_terms=[
            _query_term("Backend Engineer", source="job_title", category="role_anchor", retrieval_role="role_anchor")
        ],
        sent_query_terms=[],
        round_no=2,
    )

    assert decision.accepted_expression is not None
    assert decision.accepted_expression.canonical_expression == "distributed systems"
    assert decision.accepted_expression.surface_forms == ["distributed systems"]


def test_prf_classification_rejects_company_entity_but_keeps_product_platform() -> None:
    expressions = classify_feedback_expressions(["Databricks", "ByteDance", "distributed systems"])
    lookup = {item.canonical_expression: item.candidate_term_type for item in expressions}
    assert lookup["Databricks"] == "product_or_platform"
    assert lookup["ByteDance"] == "company_entity"
    assert lookup["distributed systems"] == "technical_phrase"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_candidate_feedback.py -q`
Expected: FAIL because `accepted_expression`, `surface_forms`, and expression classification do not exist yet.

- [ ] **Step 3: Refactor extraction into shared PRF expression evidence**

```python
# /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/candidate_feedback/models.py
class FeedbackCandidateExpression(BaseModel):
    model_config = ConfigDict(extra="forbid")

    term_family_id: str
    canonical_expression: str
    surface_forms: list[str] = Field(default_factory=list)
    candidate_term_type: str
    supporting_resume_ids: list[str] = Field(default_factory=list)
    linked_requirements: list[str] = Field(default_factory=list)
    field_hits: dict[str, int] = Field(default_factory=dict)
    fit_support_rate: float = 0.0
    not_fit_support_rate: float = 0.0
    score: float = 0.0
    reject_reasons: list[str] = Field(default_factory=list)
```

```python
# /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/candidate_feedback/policy.py
class PRFPolicyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accepted_expression: FeedbackCandidateExpression | None = None
    reject_reasons: list[str] = Field(default_factory=list)


def choose_prf_expression(
    *,
    candidate_expressions: list[FeedbackCandidateExpression],
    tried_query_fingerprints: set[str],
) -> PRFPolicyDecision:
    allowed_types = {"skill", "technical_phrase", "product_or_platform"}
    eligible = [
        item
        for item in candidate_expressions
        if item.candidate_term_type in allowed_types and not item.reject_reasons
    ]
    accepted = max(eligible, key=lambda item: (item.score, len(item.supporting_resume_ids)), default=None)
    if accepted is None:
        return PRFPolicyDecision(reject_reasons=["no_safe_prf_expression"])
    return PRFPolicyDecision(accepted_expression=accepted)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_candidate_feedback.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/candidate_feedback/models.py \
        /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/candidate_feedback/extraction.py \
        /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/candidate_feedback/policy.py \
        /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_candidate_feedback.py
git commit -m "Refactor candidate feedback into PRF expression extraction"
```

## Task 4: Add Typed Second-Lane Runtime Routing

**Files:**
- Create: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/second_lane_runtime.py`
- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/retrieval_runtime.py`
- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/orchestrator.py`
- Test: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_state_flow.py`

- [ ] **Step 1: Write failing typed-lane routing tests**

```python
class PRFPositiveScorer(StubScorer):
    def score_many(self, normalized_resumes, *, scoring_policy, round_no):
        del scoring_policy, round_no
        return [
            _fit_scorecard(
                resume.resume_id,
                overall_score=92,
                must_have_match_score=88,
                risk_score=15,
                reasoning_summary="strong fit",
                evidence=["distributed systems", "python"],
                matched_must_haves=["python"],
                strengths=["distributed systems"],
            )
            for resume in normalized_resumes
        ]


def test_round_two_uses_prf_probe_when_gate_passes(tmp_path: Path) -> None:
    settings = make_settings(runs_dir=str(tmp_path / "runs"), mock_cts=True, min_rounds=1, max_rounds=2)
    runtime = WorkflowRuntime(settings)
    _install_runtime_stubs(runtime, controller=SequenceController(), resume_scorer=PRFPositiveScorer())
    tracer = RunTracer(tmp_path / "trace")

    try:
        run_state = asyncio.run(runtime._build_run_state(*_sample_inputs(), tracer=tracer))
        asyncio.run(runtime._run_rounds(run_state=run_state, tracer=tracer, progress_callback=None))
    finally:
        tracer.close()

    decision = json.loads((tracer.run_dir / "rounds" / "round_02" / "second_lane_decision.json").read_text())
    assert decision["prf_gate_passed"] is True
    assert decision["fallback_lane_type"] is None


def test_round_two_falls_back_to_generic_explore_when_prf_is_unsafe(tmp_path: Path) -> None:
    settings = make_settings(runs_dir=str(tmp_path / "runs"), mock_cts=True, min_rounds=1, max_rounds=2)
    runtime = WorkflowRuntime(settings)
    _install_runtime_stubs(runtime, controller=SequenceController(), resume_scorer=StubScorer())
    tracer = RunTracer(tmp_path / "trace")

    try:
        run_state = asyncio.run(runtime._build_run_state(*_sample_inputs(), tracer=tracer))
        asyncio.run(runtime._run_rounds(run_state=run_state, tracer=tracer, progress_callback=None))
    finally:
        tracer.close()

    queries = json.loads((tracer.run_dir / "rounds" / "round_02" / "cts_queries.json").read_text())
    assert [item["lane_type"] for item in queries] == ["exploit", "generic_explore"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_state_flow.py::test_round_two_uses_prf_probe_when_gate_passes /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_state_flow.py::test_round_two_falls_back_to_generic_explore_when_prf_is_unsafe -q`
Expected: FAIL because there is no typed second-lane runtime and no `lane_type` in the serialized queries.

- [ ] **Step 3: Move second-lane policy into a dedicated runtime helper**

```python
# /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/retrieval_runtime.py
@dataclass
class LogicalQueryState:
    query_role: QueryRole
    lane_type: str
    query_terms: list[str]
    keyword_query: str
    next_page: int = 1
    exhausted: bool = False
    adapter_notes: list[str] = field(default_factory=list)
    city_states: dict[str, CityExecutionState] = field(default_factory=dict)
```

```python
# /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/second_lane_runtime.py
def build_second_lane_decision(
    *,
    round_no: int,
    retrieval_plan: RoundRetrievalPlan,
    query_term_pool: list[QueryTermCandidate],
    sent_query_history: list[SentQueryRecord],
    prf_decision: PRFPolicyDecision | None,
) -> tuple[SecondLaneDecision, LogicalQueryState | None]:
    if round_no == 1 or len(retrieval_plan.query_terms) == 1:
        return (
            SecondLaneDecision(
                round_no=round_no,
                attempted_prf=False,
                prf_gate_passed=False,
                reject_reasons=["round_one_or_anchor_only"],
                fallback_lane_type=None,
                no_fetch_reason="single_lane_round",
            ),
            None,
        )
    if prf_decision is not None and prf_decision.accepted_expression is not None:
        return (
            SecondLaneDecision(round_no=round_no, attempted_prf=True, prf_gate_passed=True),
            LogicalQueryState(
                query_role="explore",
                lane_type="prf_probe",
                query_terms=[retrieval_plan.query_terms[0], prf_decision.accepted_expression.canonical_expression],
                keyword_query=serialize_keyword_query(
                    [retrieval_plan.query_terms[0], prf_decision.accepted_expression.canonical_expression]
                ),
            ),
        )
    explore_terms = derive_explore_query_terms(
        retrieval_plan.query_terms,
        title_anchor_terms=[],
        query_term_pool=query_term_pool,
        sent_query_history=sent_query_history,
    )
    if explore_terms is None:
        return (
            SecondLaneDecision(
                round_no=round_no,
                attempted_prf=True,
                prf_gate_passed=False,
                reject_reasons=["no_safe_prf_expression"],
                fallback_lane_type=None,
                no_fetch_reason="no_generic_explore_query",
            ),
            None,
        )
    return (
        SecondLaneDecision(
            round_no=round_no,
            attempted_prf=True,
            prf_gate_passed=False,
            reject_reasons=["no_safe_prf_expression"],
            fallback_lane_type="generic_explore",
        ),
        LogicalQueryState(
            query_role="explore",
            lane_type="generic_explore",
            query_terms=explore_terms,
            keyword_query=serialize_keyword_query(explore_terms),
        ),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_state_flow.py::test_round_two_uses_prf_probe_when_gate_passes /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_state_flow.py::test_round_two_falls_back_to_generic_explore_when_prf_is_unsafe -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/second_lane_runtime.py \
        /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/retrieval_runtime.py \
        /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/orchestrator.py \
        /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_state_flow.py
git commit -m "Add typed second-lane runtime routing"
```

## Task 5: Make Second-Lane Budget And Refill Score-Aware

**Files:**
- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/retrieval_runtime.py`
- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/orchestrator.py`
- Test: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_state_flow.py`

- [ ] **Step 1: Write the failing score-aware refill tests**

```python
def test_second_lane_starts_with_seventy_thirty_allocation(tmp_path: Path) -> None:
    settings = make_settings(runs_dir=str(tmp_path / "runs"), mock_cts=True, min_rounds=1, max_rounds=2)
    runtime = WorkflowRuntime(settings)
    query_states = [
        LogicalQueryState(query_role="exploit", lane_type="exploit", query_terms=["python", "ranking"], keyword_query="python ranking"),
        LogicalQueryState(query_role="explore", lane_type="generic_explore", query_terms=["python", "trace"], keyword_query="python trace"),
    ]

    targets = runtime.retrieval_runtime.allocate_initial_lane_targets(query_states=query_states, target_new=10)
    assert targets == [7, 3]


def test_second_lane_refill_stops_after_post_score_zero_gain(tmp_path: Path) -> None:
    settings = make_settings(runs_dir=str(tmp_path / "runs"), mock_cts=True, min_rounds=1, max_rounds=2)
    runtime = WorkflowRuntime(settings)

    should_refill = runtime.retrieval_runtime.allow_lane_refill(
        lane_type="generic_explore",
        query_outcome_label="duplicate_only",
        new_fit_or_near_fit_count=0,
    )

    assert should_refill is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_state_flow.py::test_second_lane_starts_with_seventy_thirty_allocation /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_state_flow.py::test_second_lane_refill_stops_after_post_score_zero_gain -q`
Expected: FAIL because the retrieval runtime still uses a generic half-split and has no score-aware refill helper.

- [ ] **Step 3: Add initial allocation and post-score refill helpers**

```python
# /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/retrieval_runtime.py
def allocate_initial_lane_targets(*, query_states: list[LogicalQueryState], target_new: int) -> list[int]:
    if len(query_states) <= 1:
        return [target_new]
    exploit_target = max(1, int(round(target_new * 0.7)))
    second_lane_target = max(1, target_new - exploit_target)
    return [exploit_target, second_lane_target]


def allow_lane_refill(
    *,
    lane_type: str,
    query_outcome_label: str,
    new_fit_or_near_fit_count: int,
) -> bool:
    if lane_type == "exploit":
        return True
    if query_outcome_label in {"zero_recall", "duplicate_only", "broad_noise", "drift_suspected"}:
        return False
    return new_fit_or_near_fit_count > 0
```

```python
# /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/orchestrator.py
initial_targets = self.retrieval_runtime.allocate_initial_lane_targets(
    query_states=query_states,
    target_new=target_new,
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_state_flow.py::test_second_lane_starts_with_seventy_thirty_allocation /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_state_flow.py::test_second_lane_refill_stops_after_post_score_zero_gain -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/retrieval_runtime.py \
        /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/orchestrator.py \
        /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_state_flow.py
git commit -m "Make second-lane allocation and refill score-aware"
```

## Task 6: Add Replay Snapshot, Outcome Labels, And Experiment Isolation

**Files:**
- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/runtime_diagnostics.py`
- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/evaluation.py`
- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/tools/run_global_benchmark.py`
- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/experiments/baseline_evaluation.py`
- Modify: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/docs/outputs.md`
- Test: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_evaluation.py`
- Test: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_experiment_entrypoints.py`
- Test: `/Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_audit.py`

- [ ] **Step 1: Write the failing replay and experiment-isolation tests**

```python
def test_query_outcome_labels_are_artifact_recomputable() -> None:
    label = classify_query_outcome(
        provider_returned_count=6,
        new_unique_resume_count=0,
        new_fit_or_near_fit_count=0,
        fit_rate=0.0,
        must_have_match_avg=10.0,
        exploit_baseline_must_have_match_avg=50.0,
        off_intent_reason_count=3,
    )
    assert label == "duplicate_only"


def test_primary_benchmark_comparison_disables_company_rescue() -> None:
    config = build_policy_comparison_config(mode="candidate")
    assert config.company_discovery_enabled is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_evaluation.py /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_experiment_entrypoints.py -q`
Expected: FAIL because there is no artifact-recomputable outcome classifier and no explicit typed-second-lane experiment config.

- [ ] **Step 3: Add replay snapshot fields, outcome rules, and experiment isolation**

```python
# /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/runtime_diagnostics.py
def classify_query_outcome(
    *,
    provider_returned_count: int,
    new_unique_resume_count: int,
    new_fit_or_near_fit_count: int,
    fit_rate: float,
    must_have_match_avg: float,
    exploit_baseline_must_have_match_avg: float,
    off_intent_reason_count: int,
) -> str:
    if provider_returned_count == 0:
        return "zero_recall"
    if new_unique_resume_count == 0:
        return "duplicate_only"
    if new_fit_or_near_fit_count >= 1:
        return "marginal_gain"
    if fit_rate <= 0.1 and must_have_match_avg <= 30:
        return "broad_noise"
    if must_have_match_avg < exploit_baseline_must_have_match_avg - 15 and off_intent_reason_count >= 2:
        return "drift_suspected"
    return "low_recall_high_precision"
```

```python
# /Users/frankqdwang/Agents/SeekTalent-0.2.4/tools/run_global_benchmark.py
def build_policy_comparison_config(*, mode: str) -> AppSettings:
    settings = load_settings()
    settings.company_discovery_enabled = False
    return settings
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_evaluation.py /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_experiment_entrypoints.py /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_audit.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/runtime_diagnostics.py \
        /Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/evaluation.py \
        /Users/frankqdwang/Agents/SeekTalent-0.2.4/tools/run_global_benchmark.py \
        /Users/frankqdwang/Agents/SeekTalent-0.2.4/experiments/baseline_evaluation.py \
        /Users/frankqdwang/Agents/SeekTalent-0.2.4/docs/outputs.md \
        /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_evaluation.py \
        /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_experiment_entrypoints.py \
        /Users/frankqdwang/Agents/SeekTalent-0.2.4/tests/test_runtime_audit.py
git commit -m "Add replay diagnostics and typed-lane experiment isolation"
```

## Spec Coverage Check

- Query identity and canonical spec: covered by Task 1.
- First-hit attribution and full lane visibility: covered by Task 2.
- Typed second-lane routing and rejection artifacts: covered by Task 4.
- `PRF v1` from current candidate feedback: covered by Task 3.
- `70/30` second-lane allocation and post-score refill discipline: covered by Task 5.
- Replay reproducibility snapshot and outcome labels: covered by Task 6.
- Company evidence isolation from the mainline PRF-versus-generic comparison: covered by Task 6.

## Self-Review Notes

- No placeholder steps remain; each task names exact files, test commands, and commit commands.
- Type names are consistent across tasks: `CanonicalQuerySpec`, `QueryResumeHit`, `SecondLaneDecision`, `FeedbackCandidateExpression`.
- The plan keeps Phase 1 narrow: no explicit target company mainline work, no third always-on lane, and no company-driven second-lane identity.
