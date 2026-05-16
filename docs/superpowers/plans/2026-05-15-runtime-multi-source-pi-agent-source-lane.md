# Runtime Multi-Source Sourcing Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Runtime run CTS and Liepin as parallel multi-source lanes, merge likely same-person candidates, preserve all source evidence, select the freshest canonical resume, budget Liepin detail recommendations from provider-ranked cards, and return one unified Top 10.

**Architecture:** Runtime owns source planning, parallel lane lifecycle, budget policy, stable identity merge, canonical resume selection, finalization revisions, scoring, and safe public events. Workbench owns display, persistence, approval/lease/budget/audit state, latest lane display state, and consumes Runtime payloads. Provider adapters and PI Agent only execute bounded provider actions.

**Tech Stack:** Python 3.12, pytest, ruff, existing SeekTalent Runtime/Workbench modules, existing Liepin provider adapter/store contracts.

---

## Spec Link

This plan implements:

`docs/superpowers/specs/2026-05-15-runtime-multi-source-pi-agent-source-lane-design.md`

## Execution Notes

- Build on the current dirty working tree. Do not revert existing user or previous-agent changes.
- This repository uses staged `fw-*` gates. Do not push, merge, or release as part of this plan.
- Use tests first for each behavioral change.
- Complete Task 0 before editing orchestration code. Contract drift here will create merge, lease, and payload regressions later.
- Keep public serializers allowlisted. Do not use `asdict()` for CLI, Workbench, notes, graph, or log payloads.
- Prefer enum/allowlist reason codes over string redaction. Redaction remains a backstop, not the public contract.
- Keep Workbench out of source-specific execution logic.
- Keep `models.py` independent of `runtime/source_lanes.py`. `source_lanes.py` may import model contracts, but `models.py` must not import `source_lanes.py`.

## File Map

Modify:

- `src/seektalent/runtime/source_lanes.py`
  - source budget policy
  - lane request shape
  - candidate identity index and merge logic
  - canonical resume selection helper
  - identity-aware merge helpers
  - lane-safe exception classification helpers
  - coverage summary helpers
  - safe public payload serializers

- `src/seektalent/models.py`
  - `RuntimeIdentitySignals`
  - `RuntimeCandidateIdentity`
  - `RuntimeIdentityConflict`
  - `RuntimeCanonicalResumeSelection`
  - `RuntimeSourceCoverageSummary`
  - `RuntimeFinalizationRevision`
  - expanded `RuntimeSourceEvidence`
  - `RunState` fields for identity, evidence, and canonical resume state
  - cloning behavior for lane-local state

- `src/seektalent/runtime/orchestrator.py`
  - full-run safe source-lane runner
  - Python 3.12 structured concurrency for parallel source lane scheduling
  - terminal barrier
  - precise source coverage summary
  - finalization revision creation
  - explicit approved-detail enrichment entrypoint that consumes a base finalized run
  - CTS budget cap for multi-source lane
  - unified Top 10 scoring after merge

- `src/seektalent/providers/liepin/runtime_lane.py`
  - provider-rank-first card policy
  - hard filter reason codes
  - per-run detail recommendation budget
  - detail recommendation public fields
  - stricter approved detail lease validation

- `src/seektalent/providers/liepin/adapter.py`
  - keep approved detail lease enforcement
  - expose only safe detail/card metadata to runtime lane

- `src/seektalent_ui/runtime_bridge.py`
  - pass source budget policy through Runtime lane request
  - consume new recommendation, coverage, and finalization revision payload fields

- `src/seektalent_ui/workbench_store.py`
  - idempotent event log insert for source events and detail recommendations
  - latest source-lane state upsert

- `src/seektalent_ui/workbench_routes.py`
  - expose only new safe public payloads if route output changes

- `TODOS.md`
  - record deferred UI/platform follow-ups once

Add or modify tests:

- `tests/test_runtime_source_lanes.py`
- `tests/test_liepin_runtime_source_lane.py`
- `tests/test_provider_registry.py`
- `tests/test_workbench_api.py`
- `tests/test_workbench_note_writer.py`
- new `tests/test_runtime_candidate_identity.py`

## What Already Exists

- `RuntimeSourceLanePlan`, `RuntimeSourceLaneRequest`, `RuntimeSourceLaneResult`, `RuntimeSourceLaneEvent`, and `RuntimeDetailRecommendation` already exist in `src/seektalent/runtime/source_lanes.py`; extend them instead of creating parallel contracts. Keep `RuntimeSourceLaneResult` as a lane delta; do not add `finalization_revision` to it.
- `RuntimeSourceEvidence` already exists in `src/seektalent/models.py`; attach it to identities instead of inventing a second evidence type.
- `RuntimeApprovedDetailLease` already exists in `src/seektalent/runtime/source_lanes.py`; expand it with source/recommendation/evidence/candidate/actor/budget binding fields instead of adding a second lease type. Preserve the current detail-execution fields used by the Liepin adapter (`request_id`, `ledger_id`, `candidate_evidence_id`, `connection_id`, `compliance_gate_ref`, `provider_account_hash`, `detail_candidates_json`, `daily_budget`, `budget_date`, `provider_day_key`, `timezone`, and `open_policy_version`).
- `RunState` already owns candidate, normalized resume, evidence, and scorecard stores; add identity/canonical fields there instead of making a separate runtime state object.
- `RunArtifacts` already returns `run_id`, `run_dir`, candidate store, and normalized store. Extend or wrap it only where needed for detail enrichment state; it must carry or point to enough public-safe runtime state to merge later detail evidence, including source evidence, identities, canonical selections, coverage, and finalization revision. Do not make Workbench reconstruct finalization from raw lane results.
- `WorkflowRuntime._run_full_source_lanes()` already writes source plan, lane result, and coverage artifacts; revise it for safe parallel execution instead of creating another orchestrator.
- `WorkflowRuntime._run_cts_source_lane()` already creates lane-local CTS deltas; replace its `_run_rounds()` internals with a single-page retrieval path, not a new CTS provider stack.
- `RetrievalRuntime.execute_search_tool()` can currently refill pages until `search_max_pages_per_round`; the CTS source lane must bypass or hard-cap that behavior at the provider request level.
- `run_liepin_source_lane()` already separates card and detail modes; keep that boundary and add card policy/budget fields.
- Workbench source-run jobs, event persistence, detail request rows, and source-run counts already exist in `src/seektalent_ui/workbench_store.py`; extend them idempotently instead of creating a second persistence surface. Add latest-lane-state storage separately from the immutable event log.

## NOT In Scope

- Manual card-review UI: deferred because the first version only needs Runtime recommendations and Workbench-safe display state.
- Manual detail approval UI: deferred because approved lease contracts and store state are enough for this implementation boundary.
- Automatic source strategy optimization: deferred until lane quality and cost metrics exist.
- Generic source plugin marketplace: deferred because the immediate product is CTS plus Liepin.
- A2A transport: deferred until PI Agent has an out-of-process lifecycle, identity, and negotiated task execution.
- DokoBot action executor: deferred until trusted action manifest, capability probe, conformance tests, and audit trail exist.

## Runtime Data Flow

```text
Full Runtime run
  |
  v
Build source plan + budget policy
  |
  v
Start safe source-lane runners with asyncio.TaskGroup
  |                         |
  |                         |
  v                         v
CTS single-page lane        Liepin card lane
page=1, page_size=10        provider-ranked cards
  |                         |
  |                         v
  |                         card filters + detail recommendation budget
  |                         |
  +-----------+-------------+
              |
              v
RuntimeSourceLaneResult deltas only
              |
              v
Identity-aware merge
  |
  +-- preserve CTS evidence
  +-- preserve Liepin card evidence
  +-- preserve Liepin detail evidence when approved lease later runs
  |
  v
Canonical normalized resume selection per identity
              |
              v
Unified scoring + finalization revision 1 Top 10
              |
              v
Workbench notes + graph from public payloads only

Approved Liepin detail lease later
  |
  v
Runtime approved-detail enrichment entrypoint
  |
  v
run_source_lane_async(detail) returns RuntimeSourceLaneResult delta only
  |
  v
merge evidence into existing finalized run -> canonical select -> rescore -> finalization revision 2
```

## Task 0: Freeze Runtime Contract Schemas

Purpose: define the typed contracts before implementation touches orchestration, so identity merge, detail leases, coverage, revisions, and public payloads do not drift into ad hoc fields.

- [x] Add failing schema tests in `tests/test_runtime_source_lanes.py` and `tests/test_runtime_candidate_identity.py`:

```python
def test_runtime_identity_signals_public_payload_has_no_raw_fields():
    signals = RuntimeIdentitySignals(
        normalized_name="王明",
        is_masked_name=False,
        current_company_norm="海光集成电路",
        current_title_norm="高级主管工程师",
        school_norms=("南京邮电大学",),
        work_chronology_fingerprints=("work-fp-1",),
        provider_candidate_key_hash="provider-hash",
        protected_contact_hashes=("contact-hash",),
    )

    payload = signals.to_public_payload()

    assert "raw" not in json.dumps(payload, ensure_ascii=False)
    assert payload["is_masked_name"] is False
```

```python
def test_runtime_source_evidence_public_schema_has_merge_fields():
    evidence = make_source_evidence(
        source_plan_id="plan-1",
        source_lane_run_id="lane-1",
        provider_rank=3,
        protected_contact_hashes=("contact-hash",),
        safe_reason_codes=("source_card_candidate",),
    )

    payload = evidence.to_public_payload()

    assert payload["source_plan_id"] == "plan-1"
    assert payload["source_lane_run_id"] == "lane-1"
    assert payload["provider_rank"] == 3
    assert payload["safe_reason_codes"] == ["source_card_candidate"]
```

```python
def test_public_reason_codes_are_allowlisted_not_redacted_free_text():
    event = RuntimeSourceLaneEvent(
        schema_version="runtime_source_lane_event_v1",
        runtime_run_id="run-1",
        source_plan_id="plan-1",
        source_lane_run_id="lane-1",
        source="liepin",
        attempt=1,
        event_seq=1,
        event_type="source_lane_failed",
        status="failed",
        safe_reason_code="Bearer secret-token",
    )

    assert event.to_public_payload()["safe_reason_code"] == "unknown_reason"
```

```python
def test_approved_detail_lease_binds_recommendation_candidate_and_budget():
    lease = RuntimeApprovedDetailLease(
        lease_ref="lease-1",
        request_id="detail-request-1",
        ledger_id="detail-ledger-1",
        candidate_evidence_id="evidence-1",
        connection_id="connection-1",
        compliance_gate_ref="gate-1",
        provider_account_hash="acct-hash-1",
        detail_candidates_json=(
            '[{"candidate_id":"provider-detail-id",'
            '"stable_provider_id":"provider-detail-id",'
            '"weak_fingerprint":"provider-detail-id",'
            '"card_value_score":91}]'
        ),
        daily_budget=3,
        budget_date="2026-05-15",
        provider_day_key="liepin:acct-hash-1:2026-05-15",
        timezone="Asia/Shanghai",
        open_policy_version="detail-policy-v1",
        runtime_run_id="run-1",
        source_plan_id="plan-1",
        source_lane_run_id="lane-1",
        source="liepin",
        recommendation_id="rec-1",
        source_evidence_id="evidence-1",
        candidate_resume_id="resume-1",
        provider_candidate_key_hash="provider-hash",
        approved_by_actor_hash="actor-hash",
        approved_at="2026-05-15T00:00:00+08:00",
        expires_at="2026-05-15T01:00:00+08:00",
        budget_policy_hash="budget-hash",
        lease_signature_ref="artifact://public-summary/lease-signature",
    )

    assert lease.to_public_payload()["recommendation_id"] == "rec-1"
```

```python
def test_detail_enrichment_result_carries_revision_without_mutating_lane_result_contract():
    lane_result = make_lane_result(source="liepin", lane_mode="detail", status="completed")
    revision = RuntimeFinalizationRevision(
        runtime_run_id="run-1",
        revision=2,
        reason_code="detail_enrichment_applied",
        source_lane_run_id=lane_result.source_lane_run_id,
    )
    result = RuntimeDetailEnrichmentResult(
        runtime_run_id="run-1",
        base_finalization_revision=1,
        lane_result=lane_result,
        finalization_revision=revision,
    )

    lane_payload = lane_result.to_public_payload()
    payload = result.to_public_payload()

    assert "finalization_revision" not in lane_payload
    assert payload["finalization_revision"]["revision"] == 2
```

- [x] Add `RuntimeIdentitySignals`, `RuntimeIdentityConflict`, `RuntimeSourceCoverageSummary`, and `RuntimeFinalizationRevision` to `src/seektalent/models.py`.
- [x] Add `RuntimeDetailEnrichmentResult` in `src/seektalent/runtime/source_lanes.py` or another dependency-light runtime contract module. It should wrap the detail `RuntimeSourceLaneResult` delta and the new `RuntimeFinalizationRevision`; do not add finalization fields to `RuntimeSourceLaneResult`.
- [x] Expand `RuntimeSourceEvidence` in `src/seektalent/models.py` with:
  - `source_plan_id`
  - `source_lane_run_id`
  - `protected_contact_hashes`
  - `provider_rank`
  - `safe_summary_ref`
  - `protected_artifact_ref`
  - `safe_reason_codes`
- [x] Expand `RuntimeApprovedDetailLease` in `src/seektalent/runtime/source_lanes.py` with source, recommendation, evidence, candidate, actor, expiry, budget, and signature binding fields while keeping the current detail-execution fields required by `run_liepin_source_lane()` and `LiepinProviderAdapter`.
- [x] If `source_evidence_id` is added alongside the existing `candidate_evidence_id`, keep them aliased or validated against each other until the existing field can be safely migrated. Do not leave two independent evidence ids on the lease.
- [x] Add enum/allowlist helpers for public reason codes and artifact ref schemes. Free-form text that is not allowlisted must become `unknown_reason`.
- [x] Extend the event type enum with explicit failed and cancelled lane events if missing. Failed lanes must not be encoded as blocked lanes.
- [x] Keep private diagnostics behind protected artifact refs; do not put raw exception text into public payloads.
- [x] Run:

```bash
uv run pytest tests/test_runtime_source_lanes.py tests/test_runtime_candidate_identity.py -q
```

Expected result: all contract schema payloads are stable, public-safe, and ready for later tasks.

## Task 1: Add Runtime Source Budget Policy

Purpose: make CTS and Liepin source limits explicit instead of scattering budget constants through lanes.

- [x] Add failing tests in `tests/test_runtime_source_lanes.py`:

```python
def test_default_source_budget_policy_is_public_safe():
    policy = RuntimeSourceBudgetPolicy.defaults()

    assert policy.cts_max_pages == 1
    assert policy.cts_page_size == 10
    assert policy.liepin_card_max_pages == 1
    assert policy.liepin_detail_open_limit_per_run > 0
    assert policy.final_top_k == 10
    assert policy.to_public_payload() == {
        "cts_max_pages": 1,
        "cts_page_size": 10,
        "liepin_card_max_pages": 1,
        "liepin_card_page_size": policy.liepin_card_page_size,
        "liepin_detail_open_limit_per_run": policy.liepin_detail_open_limit_per_run,
        "final_top_k": 10,
    }
```

- [x] Implement `RuntimeSourceBudgetPolicy` in `src/seektalent/runtime/source_lanes.py`.
- [x] Use literal domain names, not generic configuration wrappers.
- [x] Keep the public payload count-only and secret-free.
- [x] Run:

```bash
uv run pytest tests/test_runtime_source_lanes.py -q
```

Expected result: the new budget test passes.

## Task 2: Extend Lane Request And Plan With Budget Context

Purpose: every source lane should know the same runtime-owned budget policy.

- [x] Add failing tests in `tests/test_runtime_source_lanes.py`:

```python
def test_runtime_source_lane_request_includes_budget_policy_publicly():
    request = RuntimeSourceLaneRequest(
        source="liepin",
        lane_mode="card",
        job_title="数字前端工程师",
        jd="需要 Verilog 和芯片经验",
        notes=None,
        source_budget_policy=RuntimeSourceBudgetPolicy.defaults(),
    )

    payload = request.to_public_payload()

    assert payload["source"] == "liepin"
    assert payload["lane_mode"] == "card"
    assert payload["source_budget_policy"]["cts_page_size"] == 10
    assert "provider_context" not in payload
```

- [x] Add `source_budget_policy` to `RuntimeSourceLaneRequest`.
- [x] Add budget fields to `RuntimeSourceLanePlan.to_public_payload()`.
- [x] Make Workbench and full Runtime callers pass `RuntimeSourceBudgetPolicy.defaults()` when they do not specify a policy.
- [x] Run:

```bash
uv run pytest tests/test_runtime_source_lanes.py tests/test_workbench_api.py -q
```

Expected result: request and Workbench route tests pass.

## Task 3: Add Candidate Identity Signals And Stable Identity Models

Purpose: merge CTS and Liepin at the person level without losing per-source evidence.

- [x] Create `tests/test_runtime_candidate_identity.py`.
- [x] Add `RuntimeIdentitySignals`, `RuntimeCandidateIdentity`, `RuntimeIdentityConflict`, and `RuntimeCanonicalResumeSelection` to `src/seektalent/models.py`, not `src/seektalent/runtime/source_lanes.py`, because `RunState` stores these records and `source_lanes.py` already imports `RunState`.
- [x] Make `RuntimeCandidateIdentityIndex` accept `RuntimeIdentitySignals`, not raw candidate payloads or display text parsing.
- [x] Add failing tests for strong same-provider identity:

```python
def test_same_provider_key_maps_to_same_identity():
    first = make_source_evidence(
        source="liepin",
        provider="liepin",
        candidate_resume_id="liepin-card-1",
        provider_candidate_key_hash="hash-a",
        evidence_level="card",
    )
    second = make_source_evidence(
        source="liepin",
        provider="liepin",
        candidate_resume_id="liepin-detail-1",
        provider_candidate_key_hash="hash-a",
        evidence_level="detail",
    )

    index = RuntimeCandidateIdentityIndex()
    signals = make_identity_signals("王某", "海光集成电路", "高级主管工程师")
    first_identity = index.identity_for_evidence(first, signals=signals)
    second_identity = index.identity_for_evidence(second, signals=signals)

    assert second_identity.identity_id == first_identity.identity_id
```

- [x] Add failing test for lane-order-independent canonical identity ids:

```python
def test_identity_id_is_stable_regardless_of_lane_completion_order():
    cts_evidence = make_source_evidence(
        source="cts",
        candidate_resume_id="cts-1",
        provider_candidate_key_hash="cts-hash",
    )
    liepin_evidence = make_source_evidence(
        source="liepin",
        candidate_resume_id="liepin-1",
        provider_candidate_key_hash="liepin-hash",
    )
    signals = RuntimeIdentitySignals(
        normalized_name="王明",
        is_masked_name=False,
        current_company_norm="海光集成电路",
        current_title_norm="高级主管工程师",
        school_norms=("南京邮电大学",),
        work_chronology_fingerprints=("work-overlap-1",),
    )

    first_order = RuntimeCandidateIdentityIndex()
    identity_a = first_order.identity_for_evidence(cts_evidence, signals=signals)
    identity_b = first_order.identity_for_evidence(liepin_evidence, signals=signals)

    second_order = RuntimeCandidateIdentityIndex()
    identity_c = second_order.identity_for_evidence(liepin_evidence, signals=signals)
    identity_d = second_order.identity_for_evidence(cts_evidence, signals=signals)

    assert identity_a.identity_id == identity_b.identity_id
    assert identity_c.identity_id == identity_d.identity_id
    assert identity_a.identity_id == identity_c.identity_id
```

- [x] Add failing test for alias preservation when later stronger evidence merges two earlier identities:

```python
def test_identity_alias_map_preserves_previous_ids_after_late_merge():
    index = RuntimeCandidateIdentityIndex()
    first = index.identity_for_evidence(make_source_evidence(evidence_id="e1"), signals=make_weak_signals("A"))
    second = index.identity_for_evidence(make_source_evidence(evidence_id="e2"), signals=make_weak_signals("B"))

    merged = index.merge_with_strong_contact_hash(
        first.identity_id,
        second.identity_id,
        protected_contact_hash="contact-hash",
    )

    assert index.canonical_identity_id(first.identity_id) == merged.identity_id
    assert index.canonical_identity_id(second.identity_id) == merged.identity_id
    assert first.identity_id in index.identity_aliases_by_canonical_id[merged.identity_id]
```

- [x] Add parametrized failing tests for masked Liepin names:

```python
@pytest.mark.parametrize("masked_name", ["王**", "*明", "王某", "王女士", "W**", "Wang**", "候选人123", "匿名", "-", ""])
def test_masked_liepin_name_does_not_merge_on_company_title_only(masked_name):
    index = RuntimeCandidateIdentityIndex()

    cts_identity = index.identity_for_evidence(
        make_source_evidence(
            source="cts",
            candidate_resume_id="cts-1",
            provider_candidate_key_hash="cts-hash-1",
        ),
        signals=make_identity_signals(
            "王明",
            "海光集成电路",
            "高级主管工程师",
            school="南京邮电大学",
            work_years=("2023.10-至今 海光集成电路 高级主管工程师",),
        ),
    )
    liepin_identity = index.identity_for_evidence(
        make_source_evidence(
            source="liepin",
            candidate_resume_id="liepin-card-1",
            provider_candidate_key_hash="liepin-hash-1",
        ),
        signals=make_identity_signals(
            masked_name,
            "海光集成电路",
            "高级主管工程师",
            school="",
            work_years=(),
        ),
    )

    assert liepin_identity.identity_id != cts_identity.identity_id
    assert "masked_name_insufficient" in index.conflict_reasons[liepin_identity.identity_id]
```

- [x] Add failing tests for ambiguous name-only matches:

```python
def test_name_only_match_does_not_auto_merge():
    index = RuntimeCandidateIdentityIndex()

    first = index.identity_for_evidence(
        make_source_evidence(candidate_resume_id="cts-1", provider_candidate_key_hash="hash-1"),
        signals=make_identity_signals("王某", "A 公司", "后端工程师"),
    )
    second = index.identity_for_evidence(
        make_source_evidence(candidate_resume_id="liepin-1", provider_candidate_key_hash="hash-2"),
        signals=make_identity_signals("王某", "B 公司", "前端工程师"),
    )

    assert second.identity_id != first.identity_id
    assert index.conflict_reasons
```

- [x] Implement small dataclasses in `src/seektalent/models.py`:

```python
@dataclass(frozen=True)
class RuntimeIdentitySignals:
    normalized_name: str | None = None
    is_masked_name: bool = False
    current_company_norm: str | None = None
    current_title_norm: str | None = None
    school_norms: tuple[str, ...] = ()
    work_chronology_fingerprints: tuple[str, ...] = ()
    provider_candidate_key_hash: str | None = None
    protected_contact_hashes: tuple[str, ...] = ()

@dataclass(frozen=True)
class RuntimeCandidateIdentity:
    identity_id: str
    match_confidence: Literal["strong", "medium", "weak", "ambiguous"]
    safe_match_reason_codes: tuple[str, ...] = ()

@dataclass(frozen=True)
class RuntimeIdentityConflict:
    candidate_identity_id: str
    conflicting_identity_id: str
    safe_reason_codes: tuple[str, ...]

@dataclass(frozen=True)
class RuntimeCanonicalResumeSelection:
    identity_id: str
    resume_id: str
    source_evidence_id: str
    safe_reason_codes: tuple[str, ...]
```

- [x] Add a focused `RuntimeCandidateIdentityIndex` helper in `src/seektalent/runtime/source_lanes.py`.
- [x] Generate canonical identity ids from stable identity key priority:
  - protected contact hash
  - same-provider candidate key
  - provider plus candidate key hash
  - normalized name plus company plus title plus distinctive school or work chronology fingerprint
  - deterministic minimum evidence id set when no stronger key exists
- [x] Preserve identity aliases when later evidence merges previously separate identities. Public payloads expose only canonical identity ids.
- [x] Do not include raw contact data, raw provider ids, raw resume text, or raw profile payloads in identity ids.
- [x] Treat masked names such as `王**`, `W**`, and `*明` as weak identity evidence. A masked name plus current company/title must not auto-merge with another source.
- [x] Permit masked-name merge only when stronger corroboration exists, such as the same provider key hash, protected contact hash, distinctive school plus overlapping work chronology, or a later approved detail resume.
- [x] Run:

```bash
uv run pytest tests/test_runtime_candidate_identity.py -q
```

Expected result: strong matches merge; ambiguous matches stay separate.

## Task 4: Extend RunState For Identity-Aware Source State

Purpose: Runtime needs first-class state for identities, evidence by identity, and canonical selection.

- [x] Add failing tests in `tests/test_runtime_candidate_identity.py`:

```python
def test_run_state_preserves_evidence_by_identity_after_clone():
    run_state = RunState()
    identity = RuntimeCandidateIdentity(identity_id="identity-1", match_confidence="strong")
    evidence = make_source_evidence(candidate_resume_id="resume-1", evidence_id="evidence-1")

    run_state.candidate_identity_store[identity.identity_id] = identity
    run_state.source_evidence_by_identity_id[identity.identity_id] = [evidence]

    clone = clone_run_state_for_source_lane(run_state, source="cts")

    assert clone.candidate_identity_store == {}
    assert clone.source_evidence_by_identity_id == {}
```

- [x] Add fields to `RunState` in `src/seektalent/models.py`:

```python
candidate_identity_store: dict[str, RuntimeCandidateIdentity]
candidate_identity_by_resume_id: dict[str, str]
identity_aliases_by_canonical_id: dict[str, list[str]]
source_evidence_by_identity_id: dict[str, list[RuntimeSourceEvidence]]
canonical_resume_by_identity_id: dict[str, RuntimeCanonicalResumeSelection]
identity_conflict_reasons: dict[str, list[str]]
source_coverage_summary: RuntimeSourceCoverageSummary | None
finalization_revisions: list[RuntimeFinalizationRevision]
```

- [x] Keep these field types import-local to `models.py`. `models.py` must not import `RuntimeCandidateIdentityIndex` or any runtime lane helper.
- [x] Keep lane cloning as a free function: `clone_run_state_for_source_lane(run_state, source)`. Do not add a `RunState.clone_empty_for_lane()` method that imports runtime helpers into `models.py`.
- [x] Update `clone_run_state_for_source_lane()` in `src/seektalent/runtime/source_lanes.py` to clear the new identity stores, coverage summary, and finalization revisions for lane-local state.
- [x] Ensure lane-local cloning starts empty for lane outputs.
- [x] Run:

```bash
uv run pytest tests/test_runtime_candidate_identity.py tests/test_runtime_source_lanes.py -q
```

Expected result: RunState supports identity state without contaminating lane-local state.

## Task 5: Replace Resume-Id Merge With Identity-Aware Merge

Purpose: preserve all source evidence and avoid wrong overwrites when the same person appears in CTS and Liepin.

- [x] Add failing tests in `tests/test_runtime_source_lanes.py`:

```python
def test_apply_source_lane_result_merges_same_person_from_cts_and_liepin():
    run_state = RunState()
    cts_result = make_lane_result(
        source="cts",
        candidates=[
            make_candidate(
                "resume-cts",
                name="王明",
                company="海光集成电路",
                title="高级主管工程师",
                school="南京邮电大学",
                work_years=("2023.10-至今 海光集成电路 高级主管工程师",),
            )
        ],
        evidence=[make_source_evidence(source="cts", candidate_resume_id="resume-cts", provider_candidate_key_hash="cts-hash")],
    )
    liepin_result = make_lane_result(
        source="liepin",
        candidates=[
            make_candidate(
                "resume-liepin",
                name="王明",
                company="海光集成电路",
                title="高级主管工程师",
                school="南京邮电大学",
                work_years=("2023.10-至今 海光集成电路 高级主管工程师",),
            )
        ],
        evidence=[make_source_evidence(source="liepin", candidate_resume_id="resume-liepin", provider_candidate_key_hash="liepin-hash")],
    )

    apply_source_lane_result(run_state, cts_result)
    apply_source_lane_result(run_state, liepin_result)

    assert len(run_state.candidate_identity_store) == 1
    identity_id = next(iter(run_state.candidate_identity_store))
    assert {e.source for e in run_state.source_evidence_by_identity_id[identity_id]} == {"cts", "liepin"}
```

- [x] Add masked-name false-positive test:

```python
def test_apply_source_lane_result_keeps_masked_liepin_card_separate_without_strong_evidence():
    run_state = RunState()
    cts_result = make_lane_result(
        source="cts",
        candidates=[make_candidate("resume-cts", name="王明", company="海光集成电路", title="高级主管工程师")],
        evidence=[make_source_evidence(source="cts", candidate_resume_id="resume-cts", provider_candidate_key_hash="cts-hash")],
    )
    liepin_result = make_lane_result(
        source="liepin",
        candidates=[make_candidate("resume-liepin-card", name="王**", company="海光集成电路", title="高级主管工程师")],
        evidence=[
            make_source_evidence(
                source="liepin",
                candidate_resume_id="resume-liepin-card",
                provider_candidate_key_hash="liepin-card-hash",
            )
        ],
    )

    apply_source_lane_result(run_state, cts_result)
    apply_source_lane_result(run_state, liepin_result)

    assert len(run_state.candidate_identity_store) == 2
    assert any("masked_name_insufficient" in reasons for reasons in run_state.identity_conflict_reasons.values())
```

- [x] Add failing idempotency test:

```python
def test_apply_source_lane_result_is_idempotent_for_same_evidence_id():
    run_state = RunState()
    result = make_lane_result(
        source="liepin",
        candidates=[make_candidate("resume-liepin")],
        evidence=[make_source_evidence(evidence_id="evidence-1", candidate_resume_id="resume-liepin")],
    )

    apply_source_lane_result(run_state, result)
    apply_source_lane_result(run_state, result)

    identity_id = run_state.candidate_identity_by_resume_id["resume-liepin"]
    assert [e.evidence_id for e in run_state.source_evidence_by_identity_id[identity_id]] == ["evidence-1"]
```

- [x] Update `apply_source_lane_result()` in `src/seektalent/runtime/source_lanes.py`.
- [x] Extract `RuntimeIdentitySignals` for every candidate from normalized safe fields and source evidence. Do not parse raw provider payloads in the identity index.
- [x] Keep `candidate_store` and `normalized_store` for display and scoring compatibility, but make identity stores the source of merge truth.
- [x] Append evidence once by stable evidence id.
- [x] When a later result merges identities, update `identity_aliases_by_canonical_id` and remap `candidate_identity_by_resume_id` to the canonical identity id.
- [x] Sort evidence deterministically:
  - source plan order
  - evidence level card before detail when timestamps tie
  - collected timestamp
  - evidence id
- [x] Run:

```bash
uv run pytest tests/test_runtime_source_lanes.py tests/test_runtime_candidate_identity.py -q
```

Expected result: same-person source records merge into one identity and duplicate lane result application is stable.

## Task 6: Implement Canonical Resume Selection

Purpose: final scoring should use the best available resume per identity while retaining evidence.

- [x] Add failing tests in `tests/test_runtime_candidate_identity.py`:

```python
def test_canonical_selection_prefers_detail_over_card():
    selection = choose_canonical_resume_for_identity(
        identity_id="identity-1",
        candidates={
            "card": make_candidate("card"),
            "detail": make_candidate("detail"),
        },
        normalized_resumes={
            "card": make_normalized_resume("card", completeness_score=20),
            "detail": make_normalized_resume("detail", completeness_score=80),
        },
        evidence=[
            make_source_evidence(evidence_id="card-evidence", candidate_resume_id="card", evidence_level="card"),
            make_source_evidence(evidence_id="detail-evidence", candidate_resume_id="detail", evidence_level="detail"),
        ],
    )

    assert selection.resume_id == "detail"
    assert "detail_evidence" in selection.safe_reason_codes
```

- [x] Add freshness tie-break test:

```python
def test_canonical_selection_prefers_newer_resume_when_both_are_detail():
    selection = choose_canonical_resume_for_identity(
        identity_id="identity-1",
        candidates={
            "old": make_candidate("old", raw={"resume_updated_at": "2024-01-01"}),
            "new": make_candidate("new", raw={"resume_updated_at": "2026-01-01"}),
        },
        normalized_resumes={
            "old": make_normalized_resume("old", completeness_score=90),
            "new": make_normalized_resume("new", completeness_score=90),
        },
        evidence=[
            make_source_evidence(candidate_resume_id="old", evidence_level="detail"),
            make_source_evidence(candidate_resume_id="new", evidence_level="detail"),
        ],
    )

    assert selection.resume_id == "new"
```

- [x] Implement `choose_canonical_resume_for_identity()` in `src/seektalent/runtime/source_lanes.py`.
- [x] Use deterministic sort keys:
  - detail evidence
  - parsed resume update timestamp from safe candidate provider metadata when present
  - current work recency
  - `NormalizedResume.completeness_score`
  - source trust
  - provider rank
  - resume id
- [x] Add tests for ongoing current work, completeness, source trust, and provider-rank tie-breaks. Detail and freshness tests alone are not enough.
- [x] Do not put `completeness_score` on `ResumeCandidate`; completeness belongs to `NormalizedResume` in the current codebase. Freshness may come from safe provider metadata on the candidate or evidence, but public payloads must expose only normalized timestamps/reason codes.
- [x] Call canonical selection from `apply_source_lane_result()` after identity evidence changes.
- [x] Run:

```bash
uv run pytest tests/test_runtime_candidate_identity.py tests/test_runtime_source_lanes.py -q
```

Expected result: canonical resume choice is deterministic and evidence-preserving.

## Task 7: Make Full Source Lanes Run In Parallel

Purpose: CTS and Liepin should run as parallel source searches, then merge into one final pool.

- [x] Add failing async test in `tests/test_runtime_source_lanes.py` or an orchestrator-focused test file:

```python
@pytest.mark.asyncio
async def test_full_source_lanes_start_cts_and_liepin_before_barrier():
    started = []
    release = asyncio.Event()

    runtime = make_runtime_with_lane_hooks(
        cts_hook=lambda: started.append("cts"),
        liepin_hook=lambda: started.append("liepin"),
        release=release,
    )

    task = asyncio.create_task(runtime.run(job_title="工程师", jd="JD", source_kinds=("cts", "liepin")))

    await wait_until(lambda: set(started) == {"cts", "liepin"})
    release.set()
    result = await task

    assert result.source_coverage_summary.status == "complete"
```

- [x] Update `_run_full_source_lanes()` in `src/seektalent/runtime/orchestrator.py`.
- [x] Add `_run_source_lane_safely(...)` in `src/seektalent/runtime/orchestrator.py`. It should call the source-specific lane and convert provider/runtime exceptions into a failed `RuntimeSourceLaneResult` with safe reason codes.
- [x] Classify safe lane-isolated errors separately from runtime invariant failures:
  - provider, network, session, rate-limit, and login errors become `blocked` or `failed` lane results
  - malformed provider payload can become `partial` or `failed` with a private diagnostic artifact ref
  - runtime invariant errors, programmer errors, schema corruption, and merge corruption fail the whole run
- [x] Run lane safe runners concurrently with Python 3.12 standard-library structured concurrency:

```python
async with asyncio.TaskGroup() as task_group:
    lane_tasks = {
        lane.source: task_group.create_task(
            self._run_source_lane_safely(
                lane=lane,
                run_state=run_state,
                tracer=tracer,
                liepin_context=liepin_context,
                progress_callback=progress_callback,
            )
        )
        for lane in source_plan
    }

lane_results = [lane_tasks[lane.source].result() for lane in source_plan]
```

- [x] Do not let ordinary provider exceptions escape `_run_source_lane_safely()`. If they escape, `TaskGroup` will cancel sibling lanes, which violates the CTS/Liepin parallel contract.
- [x] Let user cancellation propagate through `asyncio.CancelledError` so a cancelled run can stop all lanes.
- [x] Add a barrier-style test proving both CTS and Liepin have entered their provider calls before either is released. If any provider call is blocking synchronous I/O, wrap it in an async adapter or `asyncio.to_thread()` before claiming parallel behavior.
- [x] Merge lane results only after selected lanes are terminal.
- [x] Do not let CTS mutate the active final `RunState` before its lane result is returned.
- [x] Keep a regression test where Liepin raises a raw exception and CTS still completes, then assert the public lane artifact contains only `failed_provider_error` and not the raw exception text.
- [x] Run:

```bash
uv run pytest tests/test_runtime_source_lanes.py -q
```

Expected result: both selected full-run lanes start before finalization and return one merged result.

## Task 8: Add Finalization Coverage Semantics

Purpose: users must know when the Top 10 came from all selected sources or only available sources.

- [x] Add failing tests:

```python
@pytest.mark.asyncio
async def test_blocked_liepin_and_completed_cts_finalizes_with_degraded_coverage():
    runtime = make_runtime_with_lane_results(
        cts=make_lane_result(source="cts", status="completed", candidates=[make_candidate("cts-1")]),
        liepin=make_lane_result(source="liepin", status="blocked", candidates=[]),
    )

    result = await runtime.run(job_title="工程师", jd="JD", source_kinds=("cts", "liepin"))

    assert result.source_coverage_summary.status == "degraded"
    assert result.source_coverage_summary.blocked_source_kinds == ["liepin"]
    assert result.source_coverage_summary.missing_source_kinds == []
    assert len(result.candidates) <= 10
```

- [x] Add completed-zero-candidates coverage test:

```python
@pytest.mark.asyncio
async def test_completed_zero_candidate_source_is_empty_not_missing():
    runtime = make_runtime_with_lane_results(
        cts=make_lane_result(source="cts", status="completed", candidates=[make_candidate("cts-1")]),
        liepin=make_lane_result(source="liepin", status="completed", candidates=[]),
    )

    result = await runtime.run(job_title="工程师", jd="JD", source_kinds=("cts", "liepin"))

    assert result.source_coverage_summary.empty_source_kinds == ["liepin"]
    assert result.source_coverage_summary.missing_source_kinds == []
```

- [x] Store `RuntimeSourceCoverageSummary` on `RunState` and expose it through existing runtime result payloads.
- [x] Use `complete` only when all selected lanes completed without lane-level degradation.
- [x] Use `degraded` when at least one selected source is partial, blocked, failed, timed out, or produced no usable candidates. Partial lanes may still contribute accepted candidates, but the coverage summary must include the source in `partial_source_kinds` and remain degraded.
- [x] Use `empty` when no selected lane produced candidates.
- [x] Keep separate lists for blocked, failed, partial, empty, and missing source kinds.
- [x] Update Workbench notes/graph context to include safe coverage status.
- [x] Run:

```bash
uv run pytest tests/test_runtime_source_lanes.py tests/test_workbench_note_writer.py -q
```

Expected result: finalization scope is explicit and public-safe.

## Task 9: Cap CTS Multi-Source Lane To One Page Of 10

Purpose: the first multi-source version should respect the CTS budget the product expects.

- [x] Add failing test around `_run_cts_source_lane()`:

```python
@pytest.mark.asyncio
async def test_cts_source_lane_uses_one_page_of_ten_in_multi_source_mode():
    captured_requests = []
    runtime = make_runtime_with_cts_capture(captured_requests)
    source_plan = make_source_plan(source="cts")
    run_state = make_run_state()
    tracer = make_tracer()

    await runtime._run_cts_source_lane(
        run_state=run_state,
        tracer=tracer,
        source_plan=source_plan,
        source_budget_policy=RuntimeSourceBudgetPolicy.defaults(),
        progress_callback=None,
    )

    assert len(captured_requests) == 1
    assert captured_requests[0].page_size == 10
    assert captured_requests[0].page == 1
```

- [x] Modify the CTS source lane path in `src/seektalent/runtime/orchestrator.py` to use the runtime source budget.
- [x] Do not implement this by calling the full `_run_rounds()` loop. `_run_rounds()` is a multi-round controller path and can issue more than one provider request.
- [x] Build a dedicated CTS single-page lane path on existing retrieval code:
  - construct one CTS query from the current requirement sheet and source query terms
  - call the CTS retrieval/provider path exactly once with `target_new=source_budget_policy.cts_page_size`
  - force `query.page == 1`
  - force provider request page size `10`
  - disable refill pagination for this lane, even if the provider returns fewer than 10 candidates
  - pass the lane-local `seen_resume_ids` and `seen_dedup_keys`
  - write source-lane artifacts/events, not normal round artifacts
- [x] Add a provider-level spy test that asserts exactly one CTS provider request occurred. Checking only outer runtime arguments is not sufficient because `execute_search_tool()` can internally refill pages.
- [x] Keep CTS-only legacy behavior unchanged outside the multi-source source-lane path.
- [x] Record CTS source evidence for every returned candidate.
- [x] Run:

```bash
uv run pytest tests/test_runtime_source_lanes.py tests/test_cli.py -q
```

Expected result: multi-source CTS is capped to one page of 10, while CLI compatibility tests remain green.

## Task 10: Implement Provider-Rank-First Liepin Card Policy

Purpose: Liepin recommendations should primarily respect the search engine's card order while filtering obvious non-fits.

- [x] Add failing tests in `tests/test_liepin_runtime_source_lane.py`:

```python
def test_liepin_detail_recommendations_preserve_provider_rank_after_hard_filters():
    candidates = [
        make_liepin_card("rank-1", provider_rank=1, title="数字前端工程师", tags=("verilog",)),
        make_liepin_card("rank-2", provider_rank=2, title="数字前端专家", tags=("verilog", "FTI", "SDP")),
    ]

    recommendations = detail_recommendations_for_liepin_cards(
        candidates,
        job_title="数字前端工程师",
        jd="需要 verilog",
        budget_policy=RuntimeSourceBudgetPolicy(liepin_detail_open_limit_per_run=2),
    )

    assert [r.candidate_resume_id for r in recommendations] == ["rank-1", "rank-2"]
```

- [x] Add hard-filter test:

```python
def test_liepin_card_hard_filter_blocks_obvious_wrong_title():
    candidates = [
        make_liepin_card("rank-1", provider_rank=1, title="销售经理"),
        make_liepin_card("rank-2", provider_rank=2, title="数字前端工程师"),
    ]

    recommendations = detail_recommendations_for_liepin_cards(
        candidates,
        job_title="数字前端工程师",
        jd="芯片数字前端",
        budget_policy=RuntimeSourceBudgetPolicy(liepin_detail_open_limit_per_run=2),
    )

    assert [r.candidate_resume_id for r in recommendations] == ["rank-2"]
    assert recommendations[0].safe_reason_codes
```

- [x] Add fields to `RuntimeDetailRecommendation`:
  - `provider_rank`
  - `card_policy_rank`
  - `hard_filter_status`
  - `budget_reason_code`
  - `safe_reason_codes`
- [x] Implement a small Liepin card policy function in `src/seektalent/providers/liepin/runtime_lane.py`.
- [x] Keep provider rank primary for all cards that pass hard filters.
- [x] Use safe reason-code enums only. Do not keep free-form `safe_reason` in public recommendation payloads.
- [x] Run:

```bash
uv run pytest tests/test_liepin_runtime_source_lane.py -q
```

Expected result: Liepin card recommendations are provider-rank-first and hard-filtered.

## Task 11: Enforce Liepin Detail Recommendation Budget

Purpose: Runtime should recommend only the allowed number of detail opens per run.

- [x] Add failing budget tests:

```python
def test_liepin_detail_recommendations_stop_at_budget_limit():
    candidates = [
        make_liepin_card(f"rank-{index}", provider_rank=index, title="数字前端工程师")
        for index in range(1, 6)
    ]

    recommendations = detail_recommendations_for_liepin_cards(
        candidates,
        job_title="数字前端工程师",
        jd="芯片数字前端",
        budget_policy=RuntimeSourceBudgetPolicy(liepin_detail_open_limit_per_run=2),
    )

    assert [r.provider_rank for r in recommendations] == [1, 2]
    assert {r.budget_reason_code for r in recommendations} == {"within_run_detail_budget"}
```

- [x] Add duplicate identity skip test:

```python
def test_liepin_detail_budget_skips_identity_already_detail_enriched():
    recommendations = detail_recommendations_for_liepin_cards(
        [make_liepin_card("rank-1", provider_rank=1), make_liepin_card("rank-2", provider_rank=2)],
        job_title="工程师",
        jd="JD",
        budget_policy=RuntimeSourceBudgetPolicy(liepin_detail_open_limit_per_run=2),
        candidate_resume_id_to_identity_id={"rank-1": "identity-rank-1", "rank-2": "identity-rank-2"},
        identities_with_detail={"identity-rank-1"},
    )

    assert [r.candidate_resume_id for r in recommendations] == ["rank-2"]
```

- [x] Apply budget after hard filters and before returning public lane result.
- [x] Pass either `candidate_resume_id_to_identity_id` or a small identity resolver into the card policy when skipping identities already detail-enriched. The policy must not infer identity from card ids.
- [x] Do not fetch detail resumes in the card lane.
- [x] Include safe counts in lane events:
  - cards seen
  - cards filtered
  - detail recommendations emitted
  - detail budget limit
- [x] Run:

```bash
uv run pytest tests/test_liepin_runtime_source_lane.py tests/test_runtime_source_lanes.py -q
```

Expected result: detail recommendations are budgeted, deterministic, and safe.

## Task 12: Keep Approved Detail Lease As Separate Detail Lane

Purpose: card search and detail fetch must stay separated so future approval UI can plug in safely.

- [x] Add or update tests in `tests/test_liepin_runtime_source_lane.py`:

```python
@pytest.mark.asyncio
async def test_liepin_detail_lane_requires_approved_lease():
    request = RuntimeSourceLaneRequest(
        source="liepin",
        lane_mode="detail",
        job_title="工程师",
        jd="JD",
        notes=None,
        source_budget_policy=RuntimeSourceBudgetPolicy.defaults(),
        approved_detail_lease=None,
    )

    result = await run_liepin_source_lane(request, adapter=make_liepin_adapter())

    assert result.status == "blocked"
    assert result.blocked_reason_code == "blocked_approval_missing"
```

- [x] Ensure `RuntimeSourceLaneRequest(lane_mode="detail")` carries `approved_detail_lease`.
- [x] Keep `run_source_lane_async(RuntimeSourceLaneRequest(lane_mode="detail", ...))` delta-only. It returns `RuntimeSourceLaneResult`; it must not produce or expose `RuntimeFinalizationRevision`.
- [x] Add detail lease mismatch tests for:
  - wrong source
  - wrong recommendation id
  - wrong source evidence id
  - source evidence id and existing candidate evidence id disagree
  - wrong candidate resume id
  - wrong provider candidate key hash
  - expired lease
  - budget policy hash mismatch
- [x] Ensure `run_liepin_source_lane()` rejects missing or invalid leases.
- [x] Validate lease bindings in Runtime before building provider context.
- [x] Preserve the existing approved-lease fields that build the Liepin provider context: connection id, compliance gate ref, provider account hash, detail candidates JSON, budget date/day key, timezone, and detail open policy version.
- [x] Ensure `LiepinProviderAdapter` still enforces lease validity before detail fetch.
- [x] Do not add approval UI.
- [x] Run:

```bash
uv run pytest tests/test_liepin_runtime_source_lane.py tests/test_liepin_provider_adapter.py -q
```

Expected result: detail fetch is impossible without an approved lease.

## Task 13: Score And Return Unified Top 10 By Identity

Purpose: after merge, final output should rank the shared multi-source pool once.

- [x] Add failing integration-style test:

```python
@pytest.mark.asyncio
async def test_cts_and_liepin_multi_source_run_returns_unified_top_ten():
    runtime = make_runtime_with_lane_results(
        cts=make_lane_result(source="cts", candidates=[make_candidate(f"cts-{i}") for i in range(10)]),
        liepin=make_lane_result(source="liepin", candidates=[make_candidate(f"liepin-{i}") for i in range(10)]),
    )

    result = await runtime.run(job_title="工程师", jd="JD", source_kinds=("cts", "liepin"))

    assert len(result.candidates) == 10
    assert result.source_coverage_summary.status == "complete"
    assert result.finalization_revision.revision == 1
    assert {candidate.source_context.primary_source for candidate in result.candidates} <= {"cts", "liepin"}
```

- [x] Add test proving a raw detail lane is still non-finalizing:

```python
@pytest.mark.asyncio
async def test_liepin_detail_source_lane_returns_delta_without_finalization_revision():
    runtime = make_runtime_with_card_then_detail_lane()

    lane_result = await runtime.run_source_lane_async(
        RuntimeSourceLaneRequest(
            source="liepin",
            lane_mode="detail",
            job_title="工程师",
            jd="JD",
            notes=None,
            approved_detail_lease=make_approved_detail_lease(candidate_resume_id="liepin-1"),
        )
    )

    assert lane_result.status == "completed"
    assert not hasattr(lane_result, "finalization_revision")
```

- [x] Add detail-enrichment revision test through the explicit Runtime entrypoint:

```python
@pytest.mark.asyncio
async def test_approved_detail_enrichment_creates_new_finalization_revision():
    runtime = make_runtime_with_card_then_detail_lane()

    first = await runtime.run(job_title="工程师", jd="JD", source_kinds=("cts", "liepin"))
    second = await runtime.apply_approved_detail_lane_to_run_async(
        base_run_artifacts=first,
        base_finalization_revision=1,
        detail_lane_request=RuntimeSourceLaneRequest(
            source="liepin",
            lane_mode="detail",
            job_title="工程师",
            jd="JD",
            notes=None,
            runtime_run_id=first.run_id,
            approved_detail_lease=make_approved_detail_lease(
                runtime_run_id=first.run_id,
                candidate_resume_id="liepin-1",
            ),
        ),
    )

    assert first.finalization_revision.revision == 1
    assert second.finalization_revision.revision == 2
    assert second.finalization_revision.reason_code == "detail_enrichment_applied"
```

- [x] Add failure tests for detail enrichment:
  - no existing finalized run or run artifact state returns a blocked/failed safe result, not an ungrounded Top 10
  - approved lease `runtime_run_id` does not match the base run id
  - requested `base_finalization_revision` is stale
  - Workbench generic single-lane source run remains non-finalizing
- [x] Add `WorkflowRuntime.apply_approved_detail_lane_to_run_async(...)` or an equivalently explicit entrypoint. This method should internally call `run_source_lane_async()` for the Liepin detail lane, then merge the returned `RuntimeSourceLaneResult` into the existing finalized run state or run artifact state before creating a new `RuntimeFinalizationRevision`.
- [x] Extend `RunArtifacts` with `finalization_revision` and enough runtime state or artifact refs for later detail enrichment, or introduce a small wrapper returned by full multi-source runs. The implementation must not parse `final_markdown` or Workbench graph payloads to rebuild source evidence.
- [x] Do not use `run_source_lane_async()` as the public finalization API. Its return type remains `RuntimeSourceLaneResult`.
- [x] Update finalization in `src/seektalent/runtime/orchestrator.py` to score canonical identities after all selected lane results are merged.
- [x] Final ranking must iterate canonical identity ids, not raw `candidate_store.values()`.
- [x] Create `RuntimeFinalizationRevision` for initial full run and for later approved detail enrichment.
- [x] Keep `TOP_K = 10` as the final shortlist contract.
- [x] Ensure multi-source context is available to note generation and graph rendering.
- [x] Run:

```bash
uv run pytest tests/test_runtime_source_lanes.py tests/test_workbench_note_writer.py -q
```

Expected result: final candidates are one unified Top 10 identities across selected sources, with revision history when detail enrichment lands.

## Task 14: Update Workbench Source-Run Persistence For Stable Ids

Purpose: async source events and recommendations must be idempotent across retry and refresh.

- [x] Add failing tests in `tests/test_workbench_api.py` or a store-focused test:

```python
def test_workbench_upserts_detail_recommendation_by_recommendation_id(tmp_path):
    store = WorkbenchStore(tmp_path / "workbench.sqlite")
    recommendation = make_detail_recommendation(recommendation_id="rec-1")

    store.upsert_detail_recommendations(run_id="run-1", recommendations=[recommendation])
    store.upsert_detail_recommendations(run_id="run-1", recommendations=[recommendation])

    assert store.list_detail_recommendations(run_id="run-1") == [recommendation.to_public_payload()]
```

- [x] Add event sequence test:

```python
def test_workbench_ignores_older_source_event_sequence(tmp_path):
    store = WorkbenchStore(tmp_path / "workbench.sqlite")

    store.upsert_source_event(make_source_event(source_lane_run_id="lane-1", event_seq=2, event_type="source_lane_completed"))
    store.upsert_source_event(make_source_event(source_lane_run_id="lane-1", event_seq=1, event_type="source_lane_started"))

    assert store.get_source_lane_state("lane-1")["event_type"] == "source_lane_completed"
```

- [x] Implement or adjust upsert helpers in `src/seektalent_ui/workbench_store.py`.
- [x] Store immutable Runtime lane events separately from latest source-lane state:
  - event log key: `(runtime_run_id, source_lane_run_id, attempt, event_seq)`
  - latest state key: `(runtime_run_id, source_lane_run_id)` with monotonic attempt/event sequence updates
- [x] Do not discard older out-of-order events from the event log merely because they are older than latest state.
- [x] Keep Workbench persistence generic. It should store Runtime public payloads, not call Liepin provider logic.
- [x] Run:

```bash
uv run pytest tests/test_workbench_api.py -q
```

Expected result: repeated recommendation/event writes are idempotent and order-safe.

## Task 15: Harden Public Payload Serializers

Purpose: new identity, budget, and recommendation payloads must not reintroduce leakage.

- [x] Add leakage tests in `tests/test_runtime_source_lanes.py`:

```python
def test_public_payloads_do_not_include_raw_provider_or_secrets():
    event = RuntimeSourceLaneEvent(
        schema_version="runtime_source_lane_event_v1",
        runtime_run_id="run-1",
        source_plan_id="plan-1",
        source_lane_run_id="lane-1",
        source="liepin",
        attempt=1,
        event_seq=1,
        event_type="source_lane_completed",
        status="completed",
        safe_counts={"cards_seen": 1},
        safe_reason_code="Bearer secret-token",
        artifact_refs=("artifact://public-summary/safe", "cookie=session-secret"),
    )
    recommendation = RuntimeDetailRecommendation(
        recommendation_id="rec-1",
        source="liepin",
        source_evidence_id="evidence-1",
        candidate_resume_id="resume-1",
        provider_candidate_key_hash="hash-1",
        safe_reason_codes=("raw_resume copied token=secret-token",),
    )
    result = RuntimeSourceLaneResult(
        runtime_run_id="run-1",
        source_plan_id="plan-1",
        source_lane_run_id="lane-1",
        source="liepin",
        lane_mode="card",
        attempt=1,
        status="completed",
        detail_recommendations=(recommendation,),
        events=(event,),
        safe_error_summary="provider_token=secret-token",
    )

    payload = result.to_public_payload()
    rendered = json.dumps(payload, ensure_ascii=False)

    assert "secret-token" not in rendered
    assert "secret-cookie" not in rendered
    assert "raw_resume" not in rendered
    assert payload["events"][0]["safe_reason_code"] == "unknown_reason"
```

- [x] Ensure these objects all expose allowlisted `to_public_payload()` methods:
  - `RuntimeSourceBudgetPolicy`
  - `RuntimeSourceLaneRequest`
  - `RuntimeSourceLanePlan`
  - `RuntimeSourceLaneEvent`
  - `RuntimeSourceEvidence`
  - `RuntimeDetailRecommendation`
  - `RuntimeSourceLaneResult`
  - `RuntimeIdentitySignals`
  - `RuntimeCandidateIdentity`
  - `RuntimeIdentityConflict`
  - `RuntimeCanonicalResumeSelection`
  - `RuntimeSourceCoverageSummary`
  - `RuntimeFinalizationRevision`
  - `RuntimeDetailEnrichmentResult`
- [x] Remove public serialization paths that call `asdict()` on these dataclasses.
- [x] Public serializer should allow only known reason-code enum values and scheme-allowlisted artifact refs. Regex/token redaction is only a backstop.
- [x] Run:

```bash
uv run pytest tests/test_runtime_source_lanes.py tests/test_cli.py tests/test_workbench_api.py -q
```

Expected result: public payloads remain allowlisted and existing leakage tests remain green.

## Task 16: Update Notes And Graph Context For Multi-Source Evidence

Purpose: recruiter-facing notes should know when evidence came from CTS, Liepin card, Liepin detail, or a degraded run.

- [x] Add or update tests in `tests/test_workbench_note_writer.py`:

```python
def test_run_notes_include_multi_source_context_without_raw_resume():
    note = render_run_note(
        source_coverage_summary=make_public_coverage_summary(
            status="degraded",
            blocked_source_kinds=["liepin"],
        ),
        source_evidence=[
            make_public_evidence(source="cts", evidence_level="detail"),
            make_public_evidence(source="liepin", evidence_level="card"),
        ],
        finalization_revision=make_public_finalization_revision(revision=1),
    )

    assert "CTS" in note
    assert "Liepin" in note
    assert "degraded" in note
    assert "raw_resume" not in note
```

- [x] Add graph state test in `tests/test_workbench_api.py`:

```python
def test_workbench_graph_shows_parallel_cts_liepin_branches_and_detail_state(tmp_path):
    session = make_session_with_source_runs(
        cts_status="completed",
        liepin_status="partial",
        source_coverage_summary=make_public_coverage_summary(status="degraded", partial_source_kinds=["liepin"]),
        finalization_revision=make_public_finalization_revision(revision=1),
        liepin_counts={"cards_seen": 30, "cards_filtered": 8, "detail_recommendations": 5},
    )

    graph = render_strategy_graph(session)

    assert graph.node("source:cts")["status"] == "completed"
    assert graph.node("source:liepin")["status"] == "partial"
    assert graph.node("source:liepin:cards")["cardsSeenCount"] == 30
    assert graph.node("source:liepin:detail")["status"] == "detail_recommended"
    assert graph.node("merge:identity")["coverageStatus"] == "degraded"
```

- [x] Update note/graph builders to consume public Runtime payloads only.
- [x] Define a small `RuntimeSourceRunPublicState` or equivalent route payload assembled from public Runtime contracts. Graph/notes should consume this shape instead of reading raw lane result objects.
- [x] Display these graph states without provider-specific raw fields:
  - source branch nodes: `source:cts`, `source:liepin`
  - lane status: `pending`, `running`, `completed`, `partial`, `blocked`, `failed`, `cancelled`
  - coverage status: `complete`, `degraded`, `empty`
  - Liepin card state: cards scanned, cards filtered, detail recommendations emitted
  - Liepin detail state: pending approval, leased, completed, blocked
  - merge state: identity merge count, ambiguous duplicate count, canonical resume selected
- [x] Update run notes to include selected sources, coverage status, source evidence summary per candidate, card-only/detail-enriched status, finalization revision, and degraded-run warning when a selected source blocked or failed.
- [x] Keep UI copy business-facing.
- [x] Run:

```bash
uv run pytest tests/test_workbench_note_writer.py tests/test_workbench_api.py -q
```

Expected result: notes and graph context reflect multi-source state safely.

## Task 17: Record Deferred Product Follow-Ups Once

Purpose: keep first implementation scoped while preserving the platform roadmap.

- [x] Update the existing `Runtime Multi-Source Platform Follow-Ups` section in `TODOS.md`, or create it if missing. Do not create a duplicate section with a slightly different name.
- [x] Include:
  - human card-review UI
  - manual detail-open approval UI
  - manual source budget editing UI
  - lane health/cost/quality metrics
  - automatic source strategy optimization
  - broader source capability descriptor
  - offline entity-merge evaluation set
  - trace context alignment for future out-of-process lanes
  - trusted DokoBot action manifest and conformance suite
  - future A2A bridge only if PI Agent becomes out-of-process with independent lifecycle and identity
- [x] Run:

```bash
rg -n "Runtime Multi-Source Platform Follow-Ups|Human card-review UI|Trusted browser action conformance|Offline entity-merge evaluation set|Trace context alignment" TODOS.md
```

Expected result: the deferred scope exists once and does not duplicate older sections.

## Task 18: Full Verification

Purpose: prove the multi-source contract works without breaking existing product behavior.

- [x] Run focused tests:

```bash
uv run pytest \
  tests/test_runtime_candidate_identity.py \
  tests/test_runtime_source_lanes.py \
  tests/test_liepin_runtime_source_lane.py \
  tests/test_provider_registry.py \
  tests/test_workbench_api.py \
  tests/test_workbench_note_writer.py \
  tests/test_liepin_provider_adapter.py \
  tests/test_liepin_session_store.py \
  tests/test_cli.py \
  -q
```

Expected result: all selected tests pass.

- [x] Run lint:

```bash
uv run ruff check \
  src/seektalent/runtime/source_lanes.py \
  src/seektalent/runtime/orchestrator.py \
  src/seektalent/providers/liepin/runtime_lane.py \
  src/seektalent/providers/liepin/adapter.py \
  src/seektalent/models.py \
  src/seektalent_ui/runtime_bridge.py \
  src/seektalent_ui/workbench_store.py \
  src/seektalent_ui/workbench_routes.py \
  tests/test_runtime_candidate_identity.py \
  tests/test_runtime_source_lanes.py \
  tests/test_liepin_runtime_source_lane.py \
  tests/test_workbench_api.py \
  tests/test_workbench_note_writer.py \
  tests/test_cli.py
```

Expected result: ruff passes.

- [x] Run whitespace check:

```bash
git diff --check
```

Expected result: no whitespace errors.

- [x] Run public leakage scan over generated JSON fixtures or direct CLI outputs used by existing tests:

```bash
uv run pytest tests/test_cli.py tests/test_runtime_source_lanes.py tests/test_liepin_runtime_source_lane.py -q
```

Expected result: no provider key, token, cookie, session secret, approval secret, raw HTML, raw resume, or raw provider payload appears in public output tests.

## Completion Criteria

The plan is complete when:

- Core runtime schemas are frozen before orchestration work starts.
- CTS and Liepin selected together start as parallel full-run lanes, and both provider calls enter before the full-run barrier releases.
- CTS multi-source lane issues exactly one provider request with page 1 and page size 10.
- Liepin card lane emits provider-rank-first detail recommendations within budget.
- Liepin detail fetch requires an approved detail lease bound to source, recommendation, evidence, candidate, provider key hash, actor, expiry, and budget.
- Liepin detail source lane remains delta-only; `run_source_lane_async()` returns `RuntimeSourceLaneResult` and does not carry finalization revision fields.
- Runtime merges same-person candidates into stable canonical identities while preserving all source evidence and alias history.
- Runtime selects a canonical resume per identity deterministically.
- Runtime returns one unified Top 10 identities across selected sources.
- Approved detail enrichment uses an explicit Runtime entrypoint, consumes a valid base finalized run and approved lease, creates a later finalization revision, and refreshes canonical selection, scoring, and Top 10.
- Workbench source-run persistence handles stable ids, immutable event logs, latest source-lane state, and out-of-order events.
- Notes and graph context use multi-source public payloads only.
- Public serializers are enum/allowlist-first and leakage tests pass.
- Deferred UI/platform items are recorded once in `TODOS.md`.

## GSTACK REVIEW REPORT

**Review date:** 2026-05-15

**Wrapper:** `fw-plan-review`

**Scope decision:** B scope accepted. This is intentionally the complete multi-source contract: parallel CTS/Liepin lanes, identity merge, canonical resume selection, Liepin card/detail budget boundary, unified Top 10, Workbench graph/notes state, and public payload safety.

| Review | Trigger | Why | Runs | Status | Findings |
| --- | --- | --- | --- | --- | --- |
| Eng Review | `fw-plan-review` | Required plan gate before build | 3 | CLEAR | Previous contract blockers were repaired: detail enrichment is explicit, lane results stay delta-only, and Task 0 now freezes identity/evidence/lease/coverage/public payload contracts before build |
| Design Review | Conditional | Workbench graph/notes are user-facing state | 1 | CLEAR | Existing `DESIGN.md` applies; no new visual mockup required because this plan updates existing state semantics, not a new screen or layout |

Engineering review notes:

- The external review findings were validated against the actual runtime, provider, and Workbench code paths, then folded into the spec and plan.
- Task 0 now freezes the core contracts before build: stable identity signals, source evidence, approved detail lease, coverage summary, finalization revision, detail enrichment result, and allowlisted public payload serializers.
- Liepin detail source lanes remain delta-only. Revision creation now sits behind an explicit approved-detail enrichment entrypoint that consumes a finalized base run and approved lease.
- Design review remains satisfied by the explicit Workbench graph/notes state contract and the existing repository design baseline. Implementation should reuse the current warm, dense, business-facing workbench patterns from `DESIGN.md`.

Remaining risks for implementation:

- Keep code changes task-by-task. The plan touches shared runtime, provider, and Workbench surfaces, so start with Task 0 contract schemas before parallel orchestration and UI state.
- Do not expand into deferred items during build: manual card review UI, manual approval UI, DokoBot action executor, source capability descriptor, lane health dashboards, and A2A remain out of scope.

**Verdict:** CLEAR FOR `fw-build`.
