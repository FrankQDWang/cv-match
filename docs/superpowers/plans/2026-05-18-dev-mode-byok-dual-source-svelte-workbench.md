# Dev Mode BYOK Dual-Source Svelte Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the first locally usable dev-mode BYOK Svelte Workbench milestone for CTS plus Liepin dual-source sourcing.

**Architecture:** Keep Runtime as the only source orchestration and merge owner, Workbench as the UI/persistence/job owner, and Pi as the bounded Liepin provider executor. Build on the existing Svelte spike instead of replacing React wholesale, and add only the guardrails needed to verify this milestone.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLite Workbench store, SvelteKit, Svelte 5 runes, Svelte Query, OpenAPI TypeScript, Playwright, Vitest, Bun, pytest, ruff.

---

## Spec Link

This plan implements:

`docs/superpowers/specs/2026-05-18-dev-mode-byok-dual-source-svelte-workbench-design.md`

## Execution Notes

- Create a new worktree when implementation starts.
- Do not edit unrelated dirty files in the main checkout.
- Keep the milestone in dev-mode BYOK. Do not implement platform-managed entitlement or billing.
- Keep `apps/web` available. Do not delete or replace the React app.
- Make Svelte the pilot surface for this milestone.
- Do not reintroduce `dokobot_action`, `DokoBotActionSurface`, `DokoBotActionTransportSession`, `pi_runner.py`, direct cookie export, Playwright network interception, in-page script execution, or fallback browser execution.
- Liepin live browser execution remains explicit: `SEEKTALENT_LIEPIN_WORKER_MODE=pi_agent` plus Pi command, Pi skill path, DokoBot tool name, and a non-placeholder account binding secret.
- Optional live Liepin smoke is skipped by default and must be manually invoked with `seektalent liepin-smoke --live`.
- Component tests that render Svelte components must first add the Svelte Testing Library harness in Task 0. Do not write component tests that depend on undeclared packages or unconfigured DOM matchers.
- Use the generated OpenAPI schema as the frontend type source. If a Svelte component needs candidate fields, verify them against `apps/web-svelte/src/lib/api/schema.d.ts` or `src/seektalent_ui/models.py` before writing the component.
- This is a backend semantic contract plus Svelte pilot UI milestone. Do not start by making the Svelte UI prettier while backend status, final Top 10, triage approval, and readiness semantics remain unstable.

## File Structure

Create:

- `apps/web-svelte/src/test/setup.ts`
  - Vitest DOM matcher setup for Svelte component tests.
- `src/seektalent/dev_mode.py`
  - Safe dev-mode BYOK readiness model, including local data-root posture, and payload builder.
- `tests/test_dev_mode_readiness.py`
  - Unit tests for readiness status and no-secret payloads.
- `tests/test_workbench_semantic_guardrails.py`
  - Backend tests for source-run status propagation, blank triage approval rejection, final Top 10 identity rows, and source badge semantics.
- `src/seektalent_ui/final_top_candidates.py`
  - Projection helper for identity-level final Top 10 rows from Workbench review/evidence data.
- `apps/web-svelte/src/lib/components/DevModeReadinessPanel.svelte`
  - Safe credential/source readiness panel.
- `apps/web-svelte/src/lib/components/SourceSelector.svelte`
  - CTS/Liepin source selection control.
- `apps/web-svelte/src/lib/components/NewSessionForm.svelte`
  - Job title/JD/notes/source creation form.
- `apps/web-svelte/src/lib/components/SourceRunControlPanel.svelte`
  - Prepare triage, approve triage, and start sources control.
- `apps/web-svelte/src/lib/components/RequirementTriagePanel.svelte`
  - Visible must-have/nice-to-have/synonym/filter/exclusion/query-hint review surface before approval.
- `apps/web-svelte/src/lib/components/SourceStatusStrip.svelte`
  - Business-facing CTS/Liepin run status cards.
- `apps/web-svelte/src/lib/components/CandidateQueue.svelte`
  - Unified Top 10 candidate queue with source badges.
- `apps/web-svelte/src/lib/components/DetailRecommendationPanel.svelte`
  - Visible Liepin detail recommendation and budget posture.
- `apps/web-svelte/src/lib/workbench/sourceDisplay.ts`
  - Safe label/status helpers for source states.
- `apps/web-svelte/src/lib/workbench/sourceDisplay.test.ts`
  - Unit tests for source status labels and no-leak projection.
- `apps/web-svelte/tests/e2e/dev-mode-dual-source.spec.ts`
  - Playwright milestone journey test with safe mocked data.
- `scripts/verify-dev-workbench.sh`
  - Focused milestone verification command.

Modify:

- `apps/web-svelte/package.json`
  - Add component-testing dev dependencies.
- `apps/web-svelte/bun.lock`
  - Record the component-testing dependency graph.
- `apps/web-svelte/vite.config.ts`
  - Register the Vitest setup file for DOM matchers.
- `apps/web-svelte/src/routes/layout.css`
  - Style the new workbench panels, controls, responsive grid, status tones, and long-text wrapping.
- `src/seektalent_ui/models.py`
  - Add `WorkbenchDevModeStatusResponse`, readiness source/data-root models, source runtime display fields, and final Top 10 response models.
- `src/seektalent_ui/workbench_routes.py`
  - Add `GET /api/workbench/dev-mode/status` and `GET /api/workbench/sessions/{session_id}/final-top10`.
- `src/seektalent_ui/server.py`
  - Let dev-mode Workbench start with safe degraded settings when `pi_agent` env config is invalid, and expose raw-env diagnostics through app state.
- `src/seektalent_ui/workbench_store.py`
  - Enforce blank triage rejection, preserve Runtime lane status in source-run completion, expose explicit source badges, and support final Top 10 projection inputs.
- `tests/test_workbench_api.py`
  - Cover the new dev-mode status route and safe output.
- `apps/web-svelte/src/lib/api/workbench.ts`
  - Add typed API wrappers for dev-mode status, session creation, triage actions, source-run start, source connections, and Liepin policy.
- `apps/web-svelte/src/lib/api/workbench.test.ts`
  - Cover new wrapper paths and CSRF-mutating requests.
- `apps/web-svelte/src/lib/query/keys.ts`
  - Add keys for readiness, source connections, source start, and policies.
- `apps/web-svelte/src/lib/query/keys.test.ts`
  - Cover the new keys.
- `apps/web-svelte/src/lib/workbench/types.ts`
  - Add aliases for new generated OpenAPI types.
- `apps/web-svelte/src/routes/(app)/sessions/+page.svelte`
  - Add readiness panel and session creation.
- `apps/web-svelte/src/routes/(app)/sessions/[sessionId]/+page.svelte`
  - Add run controls, source strip, candidate queue, and detail recommendation panel.
- `apps/web-svelte/tests/e2e/workbench-spike.spec.ts`
  - Keep existing spike coverage; add no-leak strings if new panels expose more state.
- `docs/ui.md`
  - Document the dev-mode BYOK Svelte Workbench flow and optional live Liepin smoke.
- `docs/configuration.md`
  - Document dev-mode BYOK readiness variables and safe status meanings.

## Task 0: Add Svelte Component Test Harness And Visual Baseline

**Files:**

- Modify: `apps/web-svelte/package.json`
- Modify: `apps/web-svelte/bun.lock`
- Modify: `apps/web-svelte/vite.config.ts`
- Create: `apps/web-svelte/src/test/setup.ts`

- [ ] **Step 1: Add component test dependencies**

Run:

```bash
cd apps/web-svelte
bun add -d @testing-library/svelte @testing-library/user-event @testing-library/jest-dom
```

Expected: `package.json` and `bun.lock` are updated. Keep the existing `vitest`/`jsdom` setup; do not introduce a second test runner.

- [ ] **Step 2: Add Vitest setup file**

Create `apps/web-svelte/src/test/setup.ts`:

```ts
import '@testing-library/jest-dom/vitest';
```

Update `apps/web-svelte/vite.config.ts` test config:

```ts
test: {
  environment: 'jsdom',
  setupFiles: ['./src/test/setup.ts'],
  expect: {
    requireAssertions: true
  }
}
```

Preserve any existing aliases, plugins, and test settings.

- [ ] **Step 3: Add a smoke component test**

Create or extend a tiny component-test fixture only if the harness needs proof before later tasks. It should render static text and assert `toBeInTheDocument()` so missing jest-dom setup fails immediately.

- [ ] **Step 4: Run harness verification**

Run:

```bash
cd apps/web-svelte
bun run test src/lib/query/keys.test.ts
bun run check
```

Expected: tests and typecheck pass.

- [ ] **Step 5: Commit**

```bash
git add apps/web-svelte/package.json apps/web-svelte/bun.lock apps/web-svelte/vite.config.ts apps/web-svelte/src/test/setup.ts
git commit -m "test: add svelte component test harness"
```

## Task 0A: Pin Backend Semantic Guardrails Before UI

**Files:**

- Create: `tests/test_workbench_semantic_guardrails.py`
- Create: `src/seektalent_ui/final_top_candidates.py`
- Modify: `src/seektalent_ui/models.py`
- Modify: `src/seektalent_ui/workbench_routes.py`
- Modify: `src/seektalent_ui/workbench_store.py`

- [ ] **Step 1: Write failing backend semantic tests**

Create `tests/test_workbench_semantic_guardrails.py`:

```python
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from seektalent.runtime.source_lanes import RuntimeSourceLaneResult
from seektalent_ui.workbench_store import WorkbenchStore, WorkbenchUser


def _store(tmp_path: Path) -> WorkbenchStore:
    return WorkbenchStore(tmp_path / ".seektalent" / "workbench.sqlite3")


def _user(store: WorkbenchStore) -> WorkbenchUser:
    user, _created = store.bootstrap_admin(
        email="admin@example.com",
        display_name="Admin",
        password_hash="hash",
    )
    return user


def _lease_time() -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()


def _lane_result(status: str) -> RuntimeSourceLaneResult:
    return RuntimeSourceLaneResult(
        runtime_run_id="runtime-test",
        source_plan_id="runtime-test:source:liepin",
        source_lane_run_id="runtime-test:lane:liepin:card",
        source="liepin",
        lane_mode="card",
        attempt=1,
        status=status,
        blocked_reason_code="blocked_backend_unavailable" if status == "blocked" else None,
        stop_reason_code="partial_timeout" if status == "partial" else None,
        raw_candidate_count=0,
    )


def _approve_triage_with_visible_criteria(store: WorkbenchStore, *, user: WorkbenchUser, session_id: str) -> None:
    store.update_requirement_triage(
        user=user,
        session_id=session_id,
        must_haves=["5 年以上 Python"],
        nice_to_haves=[],
        synonyms=[],
        seniority_filters=[],
        exclusions=[],
        generated_query_hints=["python engineer"],
    )
    store.approve_requirement_triage(user=user, session_id=session_id)


def _mark_liepin_connected(store: WorkbenchStore, *, user: WorkbenchUser) -> None:
    connection, _created = store.get_or_create_liepin_source_connection(user=user)
    store.mark_liepin_connection_connected(
        user=user,
        connection_id=connection.connection_id,
        provider_account_hash="acct_test_hash",
    )


def test_backend_rejects_blank_requirement_triage_approval(tmp_path: Path) -> None:
    store = _store(tmp_path)
    user = _user(store)
    session = store.create_workbench_session(
        user=user,
        job_title="AI Recruiter Engineer",
        jd_text="Build local-first sourcing agents.",
        notes="dev pilot",
        source_kinds=["cts", "liepin"],
    )

    with pytest.raises(PermissionError, match="requirement_triage_empty"):
        store.approve_requirement_triage(user=user, session_id=session.session_id)


def test_liepin_blocked_lane_marks_source_blocked_not_completed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    user = _user(store)
    session = store.create_workbench_session(
        user=user,
        job_title="AI Recruiter Engineer",
        jd_text="Build local-first sourcing agents.",
        notes="dev pilot",
        source_kinds=["cts", "liepin"],
    )
    _approve_triage_with_visible_criteria(store, user=user, session_id=session.session_id)
    _mark_liepin_connected(store, user=user)
    liepin_run = next(run for run in session.source_runs if run.source_kind == "liepin")
    started = store.start_source_run_job(user=user, session_id=session.session_id, source_run_id=liepin_run.source_run_id)
    assert started is not None
    claimed = store.claim_next_source_run_job(owner_id="test-worker", lease_expires_at=_lease_time(), source_kind="liepin")
    assert claimed is not None

    store.complete_liepin_card_source_run_with_lane_result(context=claimed, result=_lane_result("blocked"))

    updated = store.get_workbench_session(user=user, session_id=session.session_id)
    assert updated is not None
    statuses = {run.source_kind: run.status for run in updated.source_runs}
    assert statuses["liepin"] == "blocked"
    assert statuses["cts"] == "queued"


def test_final_top10_endpoint_projects_identity_rows_with_source_evidence(tmp_path: Path) -> None:
    store = _store(tmp_path)
    user = _user(store)
    session = store.create_workbench_session(
        user=user,
        job_title="AI Recruiter Engineer",
        jd_text="Build local-first sourcing agents.",
        notes="dev pilot",
        source_kinds=["cts", "liepin"],
    )
    rows = store.list_final_top_candidates(user=user, session_id=session.session_id, limit=10)
    assert rows == []


def test_final_top10_merges_review_items_that_share_runtime_identity(tmp_path: Path) -> None:
    store = _store(tmp_path)
    user = _user(store)
    session = store.create_workbench_session(
        user=user,
        job_title="AI Recruiter Engineer",
        jd_text="Build local-first sourcing agents.",
        notes="dev pilot",
        source_kinds=["cts", "liepin"],
    )
    cts_run = next(run for run in session.source_runs if run.source_kind == "cts")
    liepin_run = next(run for run in session.source_runs if run.source_kind == "liepin")
    now = datetime.now(timezone.utc).isoformat()
    with store._connect() as conn:
        for review_id, source_run, source_kind, evidence_level, score in [
            ("review_cts", cts_run, "cts", "final", 91),
            ("review_liepin", liepin_run, "liepin", "card", 88),
        ]:
            conn.execute(
                """
                INSERT INTO candidate_review_items (
                    review_item_id, tenant_id, workspace_id, user_id, session_id, primary_evidence_id,
                    display_name, title, company, location, summary, aggregate_score, fit_bucket,
                    review_status, note, created_at, updated_at
                )
                VALUES (?, 'default', ?, ?, ?, ?, 'Candidate A', 'AI Recruiter Engineer', 'SeekTalent',
                        'Shanghai', 'Dual-source candidate.', ?, 'strong', 'new', '', ?, ?)
                """,
                (review_id, user.workspace_id, user.user_id, session.session_id, f"evidence_{review_id}", score, now, now),
            )
            conn.execute(
                """
                INSERT INTO candidate_evidence (
                    evidence_id, review_item_id, tenant_id, workspace_id, user_id, session_id,
                    source_run_id, source_kind, evidence_level, provider_candidate_key_hash, runtime_identity_id, resume_id,
                    score, fit_bucket, matched_must_haves_json, matched_preferences_json, missing_risks_json,
                    strengths_json, weaknesses_json, created_at
                )
                VALUES (?, ?, 'default', ?, ?, ?, ?, ?, ?, 'shared_provider_hash', 'identity_a', ?,
                        ?, 'strong', '[]', '[]', '[]', '[]', '[]', ?)
                """,
                (
                    f"evidence_{review_id}",
                    review_id,
                    user.workspace_id,
                    user.user_id,
                    session.session_id,
                    source_run.source_run_id,
                    source_kind,
                    evidence_level,
                    f"resume_{review_id}",
                    score,
                    now,
                ),
            )

    rows = store.list_final_top_candidates(user=user, session_id=session.session_id, limit=10)

    assert len(rows) == 1
    assert rows[0].identity_id == "identity_a"
    assert set(rows[0].merged_review_item_ids) == {"review_cts", "review_liepin"}
    assert "Multiple sources" in rows[0].source_badges
```

- [ ] **Step 2: Verify the tests fail for real current behavior**

Run:

```bash
uv run pytest tests/test_workbench_semantic_guardrails.py -q
```

Expected: fails because blank triage approval is allowed, blocked Liepin completion becomes completed, and `list_final_top_candidates()` does not exist.

- [ ] **Step 3: Enforce non-empty triage approval in the store and route**

In `src/seektalent_ui/workbench_store.py`, add a local helper near the triage helpers:

```python
def _triage_has_visible_criteria(triage: WorkbenchRequirementTriage) -> bool:
    return any(
        [
            triage.must_haves,
            triage.nice_to_haves,
            triage.synonyms,
            triage.seniority_filters,
            triage.exclusions,
            triage.generated_query_hints,
        ]
    )
```

Update `approve_requirement_triage()` to load the triage before updating:

```python
triage = _triage_by_session(conn, [session_id]).get(session_id)
if triage is None:
    return None
if not _triage_has_visible_criteria(triage):
    raise PermissionError("requirement_triage_empty")
```

In `src/seektalent_ui/workbench_routes.py`, catch that specific error in the approve route and return `409 Conflict` with safe detail `Requirement triage is empty.`.

- [ ] **Step 4: Preserve Runtime lane status in Workbench source display**

Keep `source_run_jobs.status` coarse (`completed` or `failed`), but map Runtime lane result status into `source_runs.status`, warnings, and runtime latest state:

```python
def _source_run_status_from_lane_result(result: object) -> tuple[str, str | None, str | None, str]:
    status = str(_attr(result, "status") or "completed")
    reason = _safe_candidate_text(_attr(result, "blocked_reason_code"), 128) or _safe_candidate_text(
        _attr(result, "stop_reason_code"), 128
    )
    if status == "blocked":
        return "blocked", reason or "blocked_backend_unavailable", "Liepin source was blocked.", "failed"
    if status == "failed":
        return "failed", reason or "failed_provider_error", "Liepin source failed.", "failed"
    if status == "cancelled":
        return "failed", reason or "cancelled_by_user", "Liepin source was cancelled.", "failed"
    if status == "partial":
        return "completed", reason or "partial_timeout", "Liepin source returned partial results.", "completed"
    return "completed", None, None, "completed"
```

Use this helper inside `complete_liepin_card_source_run_with_lane_result()`:

- update `source_runs.status`, `warning_code`, and `warning_message` before finishing the job;
- pass the mapped job status to `_finish_source_run_job_conn()`;
- keep Runtime lane events persisted, because UI will prefer `runtimeSourceState.sources[].status` when available.
- add `reasonCode: str | None = None` to `WorkbenchRuntimeSourceLaneStateResponse`;
- populate `reasonCode` in `_runtime_source_lane_state_response()` from the latest Runtime payload reason code when present, otherwise from `source_run.warning_code`.

The route projection should use an allowlist, not arbitrary text passthrough:

```python
RUNTIME_SOURCE_REASON_CODES = {
    "blocked_backend_unavailable",
    "failed_provider_error",
    "login_required",
    "partial_timeout",
    "cancelled_by_user",
    "liepin_connection_not_connected",
}


def _runtime_source_reason_code(*values: object) -> str | None:
    for value in values:
        text = str(value).strip() if value is not None else ""
        if text in RUNTIME_SOURCE_REASON_CODES:
            return text
    return None


reason_code = _runtime_source_reason_code(
    payload.get("safe_reason_code"),
    payload.get("blocked_reason_code"),
    payload.get("stop_reason_code"),
    source_run.warning_code,
)
```

Return this as `reasonCode=reason_code`; do not expose raw exception text.

- [ ] **Step 5: Make source badges explicit**

Update `_review_item_from_row()` so badges are derived from source plus evidence level:

```python
def _source_badge_for_evidence(evidence: WorkbenchCandidateEvidence) -> str:
    if evidence.source_kind == "cts":
        return "CTS final" if evidence.evidence_level == "final" else "CTS"
    if evidence.evidence_level == "detail":
        return "Liepin detail"
    return "Liepin card"
```

Then:

```python
source_badges = _unique_list(_source_badge_for_evidence(item) for item in evidence)
if len({item.source_kind for item in evidence}) > 1:
    source_badges.append("Multiple sources")
```

- [ ] **Step 6: Add final Top 10 response models and route**

Add these models to `src/seektalent_ui/models.py`:

```python
class WorkbenchFinalTopCandidateEvidenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sourceKind: SourceKind
    sourceRunId: str
    evidenceLevel: WorkbenchCandidateEvidenceLevel
    score: int | None = None
    fitBucket: str | None = None


class WorkbenchFinalTopCandidateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identityId: str
    canonicalReviewItemId: str
    mergedReviewItemIds: list[str]
    rank: int
    displayName: str
    title: str
    company: str
    location: str
    summary: str
    aggregateScore: int | None = None
    fitBucket: str | None = None
    sourceBadges: list[str]
    evidenceLevel: WorkbenchCandidateEvidenceLevel
    sourceEvidence: list[WorkbenchFinalTopCandidateEvidenceResponse]


class WorkbenchFinalTopCandidateListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[WorkbenchFinalTopCandidateResponse]
    coverageStatus: RuntimeSourceCoverageStatus
    finalizationRevision: int | None = None
```

Add a nullable `runtime_identity_id` column to `candidate_evidence` using the existing `_ensure_column()` migration style. Include the field on `WorkbenchCandidateEvidence` and `_candidate_evidence_from_row()`. Runtime-backed Workbench evidence should persist this id when the Runtime source evidence already knows it.

Create `src/seektalent_ui/final_top_candidates.py` with a projection function that projects Runtime identity-level rows without turning Workbench into a second merge owner:

- group items by persisted Runtime identity id when available;
- allow provider-hash grouping only as a conservative fallback when two rows already share the exact same safe provider hash and source evidence is not masked;
- do not auto-merge masked/weak candidates in this milestone;
- choose canonical row by evidence level rank (`final > detail > card`), then aggregate score, then newest `updated_at`;
- return at most 10 identity rows.

Expose it through:

```python
@router.get(
    "/api/workbench/sessions/{session_id}/final-top10",
    response_model=WorkbenchFinalTopCandidateListResponse,
)
def list_final_top_candidates(...):
    ...
```

The route must derive `coverageStatus` and `finalizationRevision` from the same backend runtime source-state projection used by the session detail response. Reuse `_runtime_source_state_response(...)` or its underlying store data; do not hard-code coverage in the route and do not let the Svelte UI infer final coverage from candidate rows.

This endpoint is the only data source for the Svelte final Top 10 component.

- [ ] **Step 7: Make readiness support invalid raw environment diagnostics**

Extend Task 1's `seektalent.dev_mode` design so it has both:

```python
def build_dev_mode_env_diagnostics(env: Mapping[str, str | None], *, workspace_root: Path) -> DevModeEnvDiagnostics: ...
def build_dev_mode_status(settings: AppSettings) -> DevModeStatus: ...
```

`build_dev_mode_env_diagnostics()` must not construct `AppSettings`. It reports missing/invalid `SEEKTALENT_LIEPIN_WORKER_MODE=pi_agent`, Pi command, skill path, DokoBot tool name, and account binding secret so a dev-mode API can show setup errors instead of the whole process failing first.

- [ ] **Step 8: Run backend semantic verification**

Run:

```bash
uv run pytest tests/test_workbench_semantic_guardrails.py tests/test_workbench_api.py -q
uv run ruff check src/seektalent_ui/final_top_candidates.py src/seektalent_ui/models.py src/seektalent_ui/workbench_routes.py src/seektalent_ui/workbench_store.py tests/test_workbench_semantic_guardrails.py
```

Expected: tests pass and ruff reports no issues.

- [ ] **Step 9: Commit**

```bash
git add src/seektalent_ui/final_top_candidates.py src/seektalent_ui/models.py src/seektalent_ui/workbench_routes.py src/seektalent_ui/workbench_store.py tests/test_workbench_semantic_guardrails.py
git commit -m "feat: pin workbench semantic guardrails"
```

## Task 1: Add Safe Dev-Mode BYOK Readiness Contract

**Files:**

- Create: `src/seektalent/dev_mode.py`
- Modify: `src/seektalent_ui/models.py`
- Modify: `src/seektalent_ui/workbench_routes.py`
- Modify: `src/seektalent_ui/server.py`
- Test: `tests/test_dev_mode_readiness.py`
- Test: `tests/test_workbench_api.py`

- [ ] **Step 1: Write failing readiness model tests**

Create `tests/test_dev_mode_readiness.py`:

```python
from __future__ import annotations

from pathlib import Path

from seektalent.config import AppSettings
from seektalent.dev_mode import build_dev_mode_env_diagnostics, build_dev_mode_status


def _settings(**overrides: object) -> AppSettings:
    base = {
        "runtime_mode": "dev",
        "text_llm_api_key": "sk-local-secret-value",
        "cts_tenant_key": "cts-key-secret",
        "cts_tenant_secret": "cts-secret-value",
        "liepin_worker_mode": "disabled",
        "workspace_root": str(Path.cwd()),
    }
    base.update(overrides)
    return AppSettings(**base)


def test_dev_mode_status_reports_byok_without_secret_values() -> None:
    payload = build_dev_mode_status(_settings()).to_public_payload()

    assert payload["mode"] == "dev_byok"
    assert payload["overall_status"] == "needs_setup"
    text = str(payload).lower()
    assert "sk-local-secret-value" not in text
    assert "cts-secret-value" not in text
    assert "secret" not in text
    assert payload["credentials"]["text_llm"]["status"] == "configured"
    assert payload["credentials"]["cts"]["status"] == "configured"


def test_liepin_pi_agent_reports_actionable_missing_config() -> None:
    payload = build_dev_mode_status(
        _settings(
            liepin_worker_mode="disabled",
            text_llm_api_key=None,
            cts_tenant_secret=None,
        )
    ).to_public_payload()

    assert payload["overall_status"] == "needs_setup"
    assert payload["credentials"]["text_llm"]["status"] == "missing"
    assert payload["credentials"]["cts"]["status"] == "missing"
    assert payload["sources"]["liepin"]["status"] == "disabled"
    assert payload["sources"]["liepin"]["reason_code"] == "liepin_worker_disabled"


def test_raw_env_diagnostics_survive_invalid_pi_agent_settings(tmp_path: Path) -> None:
    payload = build_dev_mode_env_diagnostics(
        {
            "SEEKTALENT_LIEPIN_WORKER_MODE": "pi_agent",
            "SEEKTALENT_LIEPIN_PI_COMMAND": "pi",
            "SEEKTALENT_LIEPIN_ACCOUNT_BINDING_SECRET": "local-development",
        },
        workspace_root=tmp_path,
    ).to_public_payload()

    assert payload["overall_status"] == "needs_setup"
    assert payload["sources"]["liepin"]["status"] == "invalid"
    assert payload["sources"]["liepin"]["reason_code"] in {
        "liepin_pi_command_invalid",
        "liepin_pi_skill_missing",
        "liepin_account_binding_secret_missing",
    }
    assert "local-development" not in str(payload)


def test_pi_agent_readiness_never_displays_command_or_skill_secret_material(tmp_path: Path) -> None:
    skill = tmp_path / "liepin_search_cards.md"
    skill.write_text("Use DokoBot inside Pi for Liepin card search.", encoding="utf-8")

    payload = build_dev_mode_status(
        _settings(
            workspace_root=str(tmp_path),
            liepin_worker_mode="pi_agent",
            liepin_pi_command="pi --mode rpc --no-session",
            liepin_pi_skill_path="liepin_search_cards.md",
            liepin_pi_dokobot_tool_name="dokobot",
            liepin_account_binding_secret="account-binding-secret-value",
        )
    ).to_public_payload()

    assert payload["sources"]["liepin"]["status"] == "configured"
    text = str(payload)
    assert "account-binding-secret-value" not in text
    assert "liepin_search_cards.md" not in text
    assert "pi --mode rpc" not in text


def test_readiness_includes_safe_local_data_root_posture(tmp_path: Path) -> None:
    workspace_root = tmp_path / "repo-like-root"
    workspace_root.mkdir()

    payload = build_dev_mode_status(_settings(workspace_root=str(workspace_root))).to_public_payload()

    assert payload["data_roots"]["overall_status"] in {"safe", "warning", "error", "unknown"}
    assert "workspace_root" in payload["data_roots"]["roots"]
    root_payload = payload["data_roots"]["roots"]["workspace_root"]
    assert root_payload["status"] in {"safe", "warning", "error", "unknown"}
    assert root_payload["reason_code"]
    text = str(payload).lower()
    assert "api_key" not in text
    assert "token" not in text
    assert "cookie" not in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/test_dev_mode_readiness.py -q
```

Expected: fail with `ModuleNotFoundError: No module named 'seektalent.dev_mode'`.

- [ ] **Step 3: Implement `src/seektalent/dev_mode.py`**

Create `src/seektalent/dev_mode.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping

from seektalent.config import AppSettings, evaluate_local_data_root_policy

ReadinessStatus = Literal["ready", "needs_setup", "disabled", "configured", "missing", "invalid"]
DataRootStatus = Literal["safe", "warning", "error", "unknown"]


@dataclass(frozen=True)
class DevModeCredentialStatus:
    status: ReadinessStatus
    reason_code: str
    label: str

    def to_public_payload(self) -> dict[str, str]:
        return {
            "status": self.status,
            "reason_code": self.reason_code,
            "label": self.label,
        }


@dataclass(frozen=True)
class DevModeSourceStatus:
    status: ReadinessStatus
    reason_code: str
    label: str
    live_mode: str | None = None
    auth_note: str | None = None

    def to_public_payload(self) -> dict[str, str | None]:
        return {
            "status": self.status,
            "reason_code": self.reason_code,
            "label": self.label,
            "live_mode": self.live_mode,
            "auth_note": self.auth_note,
        }


@dataclass(frozen=True)
class DevModeDataRootStatus:
    status: DataRootStatus
    reason_code: str
    label: str

    def to_public_payload(self) -> dict[str, str]:
        return {
            "status": self.status,
            "reason_code": self.reason_code,
            "label": self.label,
        }


@dataclass(frozen=True)
class DevModeDataRootPosture:
    overall_status: DataRootStatus
    roots: dict[str, DevModeDataRootStatus]

    def to_public_payload(self) -> dict[str, object]:
        return {
            "overall_status": self.overall_status,
            "roots": {key: value.to_public_payload() for key, value in self.roots.items()},
        }


@dataclass(frozen=True)
class DevModeStatus:
    overall_status: Literal["ready", "needs_setup"]
    credentials: dict[str, DevModeCredentialStatus]
    sources: dict[str, DevModeSourceStatus]
    data_roots: DevModeDataRootPosture

    def to_public_payload(self) -> dict[str, object]:
        return {
            "mode": "dev_byok",
            "overall_status": self.overall_status,
            "credentials": {key: value.to_public_payload() for key, value in self.credentials.items()},
            "sources": {key: value.to_public_payload() for key, value in self.sources.items()},
            "data_roots": self.data_roots.to_public_payload(),
        }


DevModeEnvDiagnostics = DevModeStatus


def build_dev_mode_env_diagnostics(env: Mapping[str, str | None], *, workspace_root: Path) -> DevModeEnvDiagnostics:
    credentials = {
        "text_llm": _env_credential_status(env.get("SEEKTALENT_TEXT_LLM_API_KEY"), "Text LLM", "text_llm_api_key"),
        "cts": _env_cts_status(env),
    }
    sources = {
        "cts": DevModeSourceStatus(
            "configured" if credentials["cts"].status == "configured" else "missing",
            "cts_ready_for_live_search" if credentials["cts"].status == "configured" else "cts_credentials_missing",
            "CTS",
            live_mode="cts",
        ),
        "liepin": _env_liepin_status(env, workspace_root=workspace_root),
    }
    data_roots = _data_root_posture_for_path(workspace_root, runtime_mode=str(env.get("SEEKTALENT_RUNTIME_MODE") or "dev"))
    all_statuses = [item.status for item in [*credentials.values(), *sources.values()]]
    overall = "ready" if all(status in {"ready", "configured"} for status in all_statuses) else "needs_setup"
    return DevModeEnvDiagnostics(overall, credentials, sources, data_roots)


def build_dev_mode_status(settings: AppSettings) -> DevModeStatus:
    credentials = {
        "text_llm": _text_llm_status(settings),
        "cts": _cts_status(settings),
    }
    sources = {
        "cts": _cts_source_status(settings),
        "liepin": _liepin_source_status(settings),
    }
    data_roots = _data_root_posture(settings)
    all_statuses = [item.status for item in [*credentials.values(), *sources.values()]]
    overall = (
        "ready"
        if all(status in {"ready", "configured"} for status in all_statuses)
        and data_roots.overall_status in {"safe", "unknown", "warning"}
        else "needs_setup"
    )
    return DevModeStatus(
        overall_status=overall,
        credentials=credentials,
        sources=sources,
        data_roots=data_roots,
    )


def _env_credential_status(value: str | None, label: str, key_name: str) -> DevModeCredentialStatus:
    if value:
        return DevModeCredentialStatus("configured", f"{key_name}_configured", label)
    return DevModeCredentialStatus("missing", f"{key_name}_missing", label)


def _env_cts_status(env: Mapping[str, str | None]) -> DevModeCredentialStatus:
    if env.get("SEEKTALENT_CTS_TENANT_KEY") and env.get("SEEKTALENT_CTS_TENANT_SECRET"):
        return DevModeCredentialStatus("configured", "cts_credentials_configured", "CTS")
    return DevModeCredentialStatus("missing", "cts_credentials_missing", "CTS")


def _env_liepin_status(env: Mapping[str, str | None], *, workspace_root: Path) -> DevModeSourceStatus:
    mode = env.get("SEEKTALENT_LIEPIN_WORKER_MODE") or "disabled"
    if mode == "disabled":
        return DevModeSourceStatus("disabled", "liepin_worker_disabled", "Liepin", live_mode="disabled")
    if mode != "pi_agent":
        return DevModeSourceStatus("invalid", "liepin_worker_mode_not_pi_agent", "Liepin", live_mode=mode)

    command = env.get("SEEKTALENT_LIEPIN_PI_COMMAND") or ""
    skill = env.get("SEEKTALENT_LIEPIN_PI_SKILL_PATH") or ""
    secret = env.get("SEEKTALENT_LIEPIN_ACCOUNT_BINDING_SECRET") or ""
    if "--mode rpc" not in command or "--no-session" not in command:
        return DevModeSourceStatus("invalid", "liepin_pi_command_invalid", "Liepin", live_mode="pi_agent")
    if not skill or not (workspace_root / skill).exists():
        return DevModeSourceStatus("invalid", "liepin_pi_skill_missing", "Liepin", live_mode="pi_agent")
    if not env.get("SEEKTALENT_LIEPIN_PI_DOKOBOT_TOOL_NAME"):
        return DevModeSourceStatus("invalid", "liepin_dokobot_tool_missing", "Liepin", live_mode="pi_agent")
    if not secret or secret == "local-development":
        return DevModeSourceStatus("invalid", "liepin_account_binding_secret_missing", "Liepin", live_mode="pi_agent")
    return DevModeSourceStatus(
        "configured",
        "liepin_pi_agent_configured",
        "Liepin",
        live_mode="pi_agent",
        auth_note="Pi uses DokoBot inside the agent. User must already be logged into Liepin.",
    )


def _text_llm_status(settings: AppSettings) -> DevModeCredentialStatus:
    if settings.text_llm_api_key:
        return DevModeCredentialStatus("configured", "text_llm_byok_configured", "Text LLM")
    return DevModeCredentialStatus("missing", "text_llm_api_key_missing", "Text LLM")


def _cts_status(settings: AppSettings) -> DevModeCredentialStatus:
    if settings.cts_tenant_key and settings.cts_tenant_secret:
        return DevModeCredentialStatus("configured", "cts_credentials_configured", "CTS")
    return DevModeCredentialStatus("missing", "cts_credentials_missing", "CTS")


def _cts_source_status(settings: AppSettings) -> DevModeSourceStatus:
    credential = _cts_status(settings)
    if credential.status == "configured":
        return DevModeSourceStatus("configured", "cts_ready_for_live_search", "CTS", live_mode="cts")
    return DevModeSourceStatus("missing", "cts_credentials_missing", "CTS", live_mode="cts")


def _liepin_source_status(settings: AppSettings) -> DevModeSourceStatus:
    mode = settings.liepin_worker_mode
    if mode == "disabled":
        return DevModeSourceStatus(
            "disabled",
            "liepin_worker_disabled",
            "Liepin",
            live_mode="disabled",
            auth_note="Set SEEKTALENT_LIEPIN_WORKER_MODE=pi_agent for live browser search.",
        )
    if mode == "pi_agent":
        return DevModeSourceStatus(
            "configured",
            "liepin_pi_agent_configured",
            "Liepin",
            live_mode="pi_agent",
            auth_note="Pi uses DokoBot inside the agent. User must already be logged into Liepin.",
        )
    return DevModeSourceStatus(
        "configured",
        "liepin_legacy_live_mode_configured",
        "Liepin",
        live_mode=mode,
        auth_note="This milestone is expected to use pi_agent for live Liepin.",
    )


def _data_root_posture(settings: AppSettings) -> DevModeDataRootPosture:
    return _data_root_posture_for_path(settings.project_root, runtime_mode=settings.runtime_mode)


def _data_root_posture_for_path(path: Path, *, runtime_mode: str) -> DevModeDataRootPosture:
    roots = {
        "workspace_root": _single_data_root_status(
            label="Workspace data root",
            path=path,
            runtime_mode=runtime_mode,
        )
    }
    statuses = [root.status for root in roots.values()]
    if any(status == "error" for status in statuses):
        overall: DataRootStatus = "error"
    elif any(status == "warning" for status in statuses):
        overall = "warning"
    elif any(status == "unknown" for status in statuses):
        overall = "unknown"
    else:
        overall = "safe"
    return DevModeDataRootPosture(overall_status=overall, roots=roots)


def _single_data_root_status(
    *,
    label: str,
    path: Path,
    runtime_mode: str,
) -> DevModeDataRootStatus:
    policy = evaluate_local_data_root_policy(
        path,
        runtime_mode=runtime_mode,
        packaged=False,
    )
    return DevModeDataRootStatus(
        status=policy.status,
        reason_code=policy.reason_code,
        label=label,
    )
```

Also add `build_dev_mode_env_diagnostics(env, workspace_root)` as described in Task 0A. `get_dev_mode_status()` should prefer `build_dev_mode_status(settings)` when valid settings exist, but tests must cover the raw-env diagnostic helper directly so incomplete `pi_agent` configuration is represented as `missing` or `invalid` instead of requiring a successful `AppSettings()` construction.

- [ ] **Step 4: Make server startup preserve dev-mode diagnostics**

In `src/seektalent_ui/server.py`, add a small startup helper used by `main()`:

```python
import os

from seektalent.dev_mode import DevModeEnvDiagnostics, build_dev_mode_env_diagnostics


def _build_server_settings_for_dev_mode(
    *,
    mock_cts: bool | None,
    workbench_enabled: bool | None,
) -> tuple[AppSettings, DevModeEnvDiagnostics | None]:
    try:
        settings = AppSettings().with_overrides(
            mock_cts=mock_cts,
            workbench_enabled=workbench_enabled,
        )
        return settings, None
    except (ValueError, ValidationError):
        raw_mode = os.environ.get("SEEKTALENT_LIEPIN_WORKER_MODE")
        if raw_mode != "pi_agent":
            raise
        workspace_root = Path(os.environ.get("SEEKTALENT_WORKSPACE_ROOT") or Path.cwd())
        diagnostics = build_dev_mode_env_diagnostics(os.environ, workspace_root=workspace_root)
        safe_settings = AppSettings(liepin_worker_mode="disabled").with_overrides(
            mock_cts=mock_cts,
            workbench_enabled=workbench_enabled,
        )
        return safe_settings, diagnostics
```

Update `create_app()` to accept `dev_mode_env_diagnostics: DevModeEnvDiagnostics | None = None` and set `app.state.dev_mode_env_diagnostics = dev_mode_env_diagnostics`.

Update `main()` from direct `AppSettings().with_overrides(...)` to:

```python
settings, dev_mode_env_diagnostics = _build_server_settings_for_dev_mode(
    mock_cts=args.mock_cts,
    workbench_enabled=False if args.disable_workbench else None,
)
```

Pass `dev_mode_env_diagnostics` into `create_app()`. This is a dev-mode readiness escape hatch only: the backend may start so the UI can show configuration problems, but live Liepin execution remains disabled until the invalid env is fixed. Do not swallow non-`pi_agent` settings errors.

- [ ] **Step 5: Add API response models**

Append these models near the existing Workbench settings/source response models in `src/seektalent_ui/models.py`:

```python
class WorkbenchDevModeCredentialStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ready", "needs_setup", "disabled", "configured", "missing", "invalid"]
    reasonCode: str
    label: str


class WorkbenchDevModeSourceStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ready", "needs_setup", "disabled", "configured", "missing", "invalid"]
    reasonCode: str
    label: str
    liveMode: str | None = None
    authNote: str | None = None


class WorkbenchDevModeDataRootStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["safe", "warning", "error", "unknown"]
    reasonCode: str
    label: str


class WorkbenchDevModeDataRootPostureResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overallStatus: Literal["safe", "warning", "error", "unknown"]
    roots: dict[str, WorkbenchDevModeDataRootStatusResponse]


class WorkbenchDevModeStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["dev_byok"]
    overallStatus: Literal["ready", "needs_setup"]
    credentials: dict[str, WorkbenchDevModeCredentialStatusResponse]
    sources: dict[str, WorkbenchDevModeSourceStatusResponse]
    dataRoots: WorkbenchDevModeDataRootPostureResponse
```

- [ ] **Step 6: Add `GET /api/workbench/dev-mode/status`**

Add imports in `src/seektalent_ui/workbench_routes.py`:

```python
import os
from pathlib import Path

from seektalent.dev_mode import build_dev_mode_env_diagnostics, build_dev_mode_status
from seektalent_ui.models import (
    WorkbenchDevModeCredentialStatusResponse,
    WorkbenchDevModeDataRootPostureResponse,
    WorkbenchDevModeDataRootStatusResponse,
    WorkbenchDevModeSourceStatusResponse,
    WorkbenchDevModeStatusResponse,
)
```

Add this route near the other Workbench settings routes:

```python
@router.get("/api/workbench/dev-mode/status", response_model=WorkbenchDevModeStatusResponse)
def get_dev_mode_status(
    request: Request,
    user: WorkbenchUser = Depends(require_current_user),
) -> WorkbenchDevModeStatusResponse:
    del user
    diagnostics = getattr(request.app.state, "dev_mode_env_diagnostics", None)
    if diagnostics is not None:
        payload = diagnostics.to_public_payload()
    else:
        settings = getattr(request.app.state, "settings", None)
        if settings is None:
            workspace_root = Path(os.environ.get("SEEKTALENT_WORKSPACE_ROOT") or Path.cwd())
            payload = build_dev_mode_env_diagnostics(os.environ, workspace_root=workspace_root).to_public_payload()
        else:
            payload = build_dev_mode_status(settings).to_public_payload()
    return WorkbenchDevModeStatusResponse(
        mode="dev_byok",
        overallStatus=str(payload["overall_status"]),
        credentials={
            key: WorkbenchDevModeCredentialStatusResponse(
                status=str(value["status"]),
                reasonCode=str(value["reason_code"]),
                label=str(value["label"]),
            )
            for key, value in payload["credentials"].items()
            if isinstance(value, dict)
        },
        sources={
            key: WorkbenchDevModeSourceStatusResponse(
                status=str(value["status"]),
                reasonCode=str(value["reason_code"]),
                label=str(value["label"]),
                liveMode=value.get("live_mode") if isinstance(value.get("live_mode"), str) else None,
                authNote=value.get("auth_note") if isinstance(value.get("auth_note"), str) else None,
            )
            for key, value in payload["sources"].items()
            if isinstance(value, dict)
        },
        dataRoots=WorkbenchDevModeDataRootPostureResponse(
            overallStatus=str(payload["data_roots"]["overall_status"]),
            roots={
                key: WorkbenchDevModeDataRootStatusResponse(
                    status=str(value["status"]),
                    reasonCode=str(value["reason_code"]),
                    label=str(value["label"]),
                )
                for key, value in payload["data_roots"]["roots"].items()
                if isinstance(value, dict)
            },
        ),
    )
```

- [ ] **Step 7: Add API route test**

Add to `tests/test_workbench_api.py`:

```python
def test_dev_mode_status_is_safe(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _bootstrap_and_login(client)

    response = client.get("/api/workbench/dev-mode/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "dev_byok"
    assert "credentials" in payload
    assert "sources" in payload
    assert "dataRoots" in payload
    assert "workspace_root" in payload["dataRoots"]["roots"]
    text = str(payload).lower()
    assert "sk-local-secret-value" not in text
    assert "cts-secret-value" not in text
    assert "token" not in text
    assert "cookie" not in text
    assert "authorization" not in text


def test_dev_mode_status_uses_startup_diagnostics_when_settings_were_degraded(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _bootstrap_and_login(client)
    client.app.state.dev_mode_env_diagnostics = build_dev_mode_env_diagnostics(
        {
            "SEEKTALENT_LIEPIN_WORKER_MODE": "pi_agent",
            "SEEKTALENT_LIEPIN_PI_COMMAND": "pi",
            "SEEKTALENT_LIEPIN_ACCOUNT_BINDING_SECRET": "local-development",
        },
        workspace_root=tmp_path,
    )

    response = client.get("/api/workbench/dev-mode/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["overallStatus"] == "needs_setup"
    assert payload["sources"]["liepin"]["status"] == "invalid"
    assert "local-development" not in str(payload)
```

Import `build_dev_mode_env_diagnostics` in this test file for the second test.

- [ ] **Step 8: Run backend verification**

Run:

```bash
uv run pytest tests/test_dev_mode_readiness.py tests/test_workbench_api.py -q
uv run ruff check src/seektalent/dev_mode.py src/seektalent_ui/models.py src/seektalent_ui/workbench_routes.py src/seektalent_ui/server.py tests/test_dev_mode_readiness.py tests/test_workbench_api.py
```

Expected: tests pass and ruff reports `All checks passed!`.

- [ ] **Step 9: Commit**

```bash
git add src/seektalent/dev_mode.py src/seektalent_ui/models.py src/seektalent_ui/workbench_routes.py src/seektalent_ui/server.py tests/test_dev_mode_readiness.py tests/test_workbench_api.py
git commit -m "feat: expose dev mode byok readiness"
```

## Task 2: Extend Svelte API Wrappers For The Full Workbench Flow

**Files:**

- Modify: `apps/web-svelte/src/lib/api/workbench.ts`
- Modify: `apps/web-svelte/src/lib/api/workbench.test.ts`
- Modify: `apps/web-svelte/src/lib/query/keys.ts`
- Modify: `apps/web-svelte/src/lib/query/keys.test.ts`
- Modify: `apps/web-svelte/src/lib/workbench/types.ts`

- [ ] **Step 1: Regenerate OpenAPI types**

Start the backend on a disposable workspace root if it is not already running. Keep it in the background and clean it up; the server command is not a one-shot command:

```bash
tmp_root="$(mktemp -d)"
env SEEKTALENT_WORKSPACE_ROOT="$tmp_root" uv run seektalent-ui-api --host 127.0.0.1 --port 8012 &
api_pid=$!
trap 'kill "$api_pid" 2>/dev/null || true; rm -rf "$tmp_root"' EXIT
until curl -fsS http://127.0.0.1:8012/openapi.json >/dev/null; do sleep 0.2; done
```

Then run:

```bash
cd apps/web-svelte
bun run api:gen
```

Expected: `apps/web-svelte/src/lib/api/schema.d.ts` contains `WorkbenchDevModeStatusResponse` and `/api/workbench/dev-mode/status`.

If `schema.d.ts` changes unexpectedly after implementation has already regenerated types, fail the task and inspect the backend schema drift before continuing.

- [ ] **Step 2: Add failing wrapper tests**

Append to `apps/web-svelte/src/lib/api/workbench.test.ts`:

```ts
it('creates sessions with explicit selected sources', async () => {
	const requests: { path: string; body: unknown }[] = [];
	const fetchMock = vi.fn(async (request: Request) => {
		const url = new URL(request.url);
		requests.push({ path: url.pathname, body: await request.clone().json() });
		return jsonResponse({
			sessionId: 'session-new',
			workspaceId: 'workspace-1',
			ownerUserId: 'user-1',
			jobTitle: 'AI Recruiter Engineer',
			jdText: 'Build local-first sourcing agents.',
			notes: 'dev pilot',
			status: 'draft',
			requirementTriage: {
				sessionId: 'session-new',
				status: 'draft',
				mustHaves: [],
				niceToHaves: [],
				synonyms: [],
				seniorityFilters: [],
				exclusions: [],
				generatedQueryHints: [],
				createdAt: '2026-05-18T00:00:00Z',
				updatedAt: '2026-05-18T00:00:00Z',
				approvedAt: null
			},
			sourceRuns: [],
			sourceCards: [],
			runtimeSourceState: null
		});
	});
	vi.stubGlobal('fetch', fetchMock);
	const { createSession } = await import('./workbench');

	await createSession({
		jobTitle: 'AI Recruiter Engineer',
		jdText: 'Build local-first sourcing agents.',
		notes: 'dev pilot',
		sourceKinds: ['cts', 'liepin']
	});

	expect(requests).toEqual([
		{
			path: '/api/workbench/sessions',
			body: {
				jobTitle: 'AI Recruiter Engineer',
				jdText: 'Build local-first sourcing agents.',
				notes: 'dev pilot',
				sourceKinds: ['cts', 'liepin']
			}
		}
	]);
});

it('wraps dev mode status and source start endpoints', async () => {
	const requests: string[] = [];
	const fetchMock = vi.fn(async (request: Request) => {
		const url = new URL(request.url);
		requests.push(`${request.method} ${url.pathname}`);
		if (url.pathname === '/api/workbench/dev-mode/status') {
			return jsonResponse({
				mode: 'dev_byok',
				overallStatus: 'needs_setup',
				credentials: {},
				sources: {},
				dataRoots: {
					status: 'ready',
					roots: {}
				}
			});
		}
		return jsonResponse({ sessionId: 'session-1', sourceRuns: [], blockedSources: [] });
	});
	vi.stubGlobal('fetch', fetchMock);
		const { getDevModeStatus, listFinalTopCandidates, startSessionSourceRuns } = await import('./workbench');

		await getDevModeStatus();
		await startSessionSourceRuns('session-1');
		await listFinalTopCandidates('session-1');

		expect(requests).toEqual([
			'GET /api/workbench/dev-mode/status',
			'POST /api/workbench/sessions/session-1/start',
			'GET /api/workbench/sessions/session-1/final-top10'
		]);
	});
```

- [ ] **Step 3: Implement wrapper functions**

Add type aliases and functions to `apps/web-svelte/src/lib/api/workbench.ts`:

```ts
type CreateSessionInput = components['schemas']['WorkbenchSessionCreateRequest'];
type TriageUpdateInput = components['schemas']['WorkbenchRequirementTriageUpdateRequest'];
type LiepinPolicyUpdateInput = components['schemas']['WorkbenchSourceRunPolicyUpdateRequest'];

export async function getDevModeStatus() {
	return requireData(await api.GET('/api/workbench/dev-mode/status'));
}

export async function createSession(input: CreateSessionInput) {
	return requireData(await api.POST('/api/workbench/sessions', { body: input }));
}

export async function prepareRequirementTriage(sessionId: string) {
	return requireData(
		await api.POST('/api/workbench/sessions/{session_id}/triage/prepare', {
			params: { path: { session_id: sessionId } }
		})
	);
}

export async function updateRequirementTriage(sessionId: string, input: TriageUpdateInput) {
	return requireData(
		await api.PUT('/api/workbench/sessions/{session_id}/triage', {
			params: { path: { session_id: sessionId } },
			body: input
		})
	);
}

export async function approveRequirementTriage(sessionId: string) {
	return requireData(
		await api.POST('/api/workbench/sessions/{session_id}/triage/approve', {
			params: { path: { session_id: sessionId } }
		})
	);
}

export async function startSessionSourceRuns(sessionId: string) {
	return requireData(
		await api.POST('/api/workbench/sessions/{session_id}/start', {
			params: { path: { session_id: sessionId } }
		})
	);
}

export async function listFinalTopCandidates(sessionId: string) {
	return requireData(
		await api.GET('/api/workbench/sessions/{session_id}/final-top10', {
			params: { path: { session_id: sessionId } }
		})
	);
}

export async function listSourceConnections() {
	return requireData(await api.GET('/api/workbench/source-connections'));
}

export async function createLiepinSourceConnection() {
	return requireData(await api.POST('/api/workbench/source-connections/liepin'));
}

export async function getLiepinSourceRunPolicy(sessionId: string) {
	return requireData(
		await api.GET('/api/workbench/sessions/{session_id}/source-runs/liepin/policy', {
			params: { path: { session_id: sessionId } }
		})
	);
}

export async function updateLiepinSourceRunPolicy(sessionId: string, input: LiepinPolicyUpdateInput) {
	return requireData(
		await api.PUT('/api/workbench/sessions/{session_id}/source-runs/liepin/policy', {
			params: { path: { session_id: sessionId } },
			body: input
		})
	);
}
```

- [ ] **Step 4: Add query keys**

Update `apps/web-svelte/src/lib/query/keys.ts`:

```ts
export const workbenchKeys = {
	me: ['auth', 'me'] as const,
	devModeStatus: ['workbench', 'dev-mode-status'] as const,
	sourceConnections: ['workbench', 'source-connections'] as const,
	sessions: ['workbench', 'sessions'] as const,
	session: (sessionId: string) => ['workbench', 'sessions', sessionId] as const,
	candidates: (sessionId: string) => ['workbench', 'sessions', sessionId, 'candidates'] as const,
	finalTop10: (sessionId: string) => ['workbench', 'sessions', sessionId, 'final-top10'] as const,
	sessionEvents: (sessionId: string, afterSeq = 0) =>
		['workbench', 'sessions', sessionId, 'events', afterSeq] as const,
	graphCandidates: (sessionId: string, nodeId: string) =>
		['workbench', 'sessions', sessionId, 'graph-candidates', nodeId] as const,
	resumeSnapshot: (sessionId: string, graphCandidateId: string) =>
		['workbench', 'sessions', sessionId, 'resume-snapshot', graphCandidateId] as const,
	liepinPolicy: (sessionId: string) =>
		['workbench', 'sessions', sessionId, 'liepin-policy'] as const
};
```

- [ ] **Step 5: Add type aliases**

Add to `apps/web-svelte/src/lib/workbench/types.ts`:

```ts
export type WorkbenchDevModeStatus = components['schemas']['WorkbenchDevModeStatusResponse'];
export type WorkbenchSourceConnection =
	components['schemas']['WorkbenchSourceConnectionResponse'];
export type WorkbenchSessionStartResponse =
	components['schemas']['WorkbenchSessionStartResponse'];
export type WorkbenchSourceRunPolicy =
	components['schemas']['WorkbenchSourceRunPolicyResponse'];
export type WorkbenchFinalTopCandidate =
	components['schemas']['WorkbenchFinalTopCandidateResponse'];
export type WorkbenchFinalTopCandidateList =
	components['schemas']['WorkbenchFinalTopCandidateListResponse'];
```

- [ ] **Step 6: Run Svelte API verification**

Run:

```bash
cd apps/web-svelte
bun run test src/lib/api/workbench.test.ts src/lib/query/keys.test.ts
bun run check
```

Expected: tests pass and `svelte-check` reports no errors.

- [ ] **Step 7: Commit**

```bash
git add apps/web-svelte/src/lib/api/schema.d.ts apps/web-svelte/src/lib/api/workbench.ts apps/web-svelte/src/lib/api/workbench.test.ts apps/web-svelte/src/lib/query/keys.ts apps/web-svelte/src/lib/query/keys.test.ts apps/web-svelte/src/lib/workbench/types.ts
git commit -m "feat: extend svelte workbench api flow"
```

## Task 3: Add Dev Readiness And New Session Flow To Svelte

**Files:**

- Create: `apps/web-svelte/src/lib/components/DevModeReadinessPanel.svelte`
- Create: `apps/web-svelte/src/lib/components/SourceSelector.svelte`
- Create: `apps/web-svelte/src/lib/components/NewSessionForm.svelte`
- Modify: `apps/web-svelte/src/routes/(app)/sessions/+page.svelte`
- Test: `apps/web-svelte/src/lib/components/NewSessionForm.test.ts`

- [ ] **Step 1: Add source display helpers**

Create `apps/web-svelte/src/lib/workbench/sourceDisplay.ts`:

```ts
export type SourceKind = 'cts' | 'liepin';

export function sourceLabel(source: SourceKind) {
	return source === 'cts' ? 'CTS' : 'Liepin';
}

export function readinessTone(status: string) {
	if (status === 'ready' || status === 'configured') return 'ready';
	if (status === 'disabled' || status === 'missing' || status === 'needs_setup') return 'warning';
	return 'blocked';
}

export function readinessStatusLabel(status: string) {
	const labels: Record<string, string> = {
		ready: '可用',
		configured: '已配置',
		missing: '缺少配置',
		disabled: '未启用',
		invalid: '配置无效',
		needs_setup: '需要设置',
		safe: '安全',
		warning: '需注意',
		error: '不可用',
		unknown: '待确认'
	};
	return labels[status] ?? '待确认';
}

export function sourceStatusLabel(status: string) {
	const labels: Record<string, string> = {
		pending: '等待启动',
		queued: '排队中',
		running: '检索中',
		completed: '已完成',
		partial: '部分完成',
		blocked: '已阻塞',
		failed: '失败',
		cancelled: '已取消',
		draft: '草稿'
	};
	return labels[status] ?? status;
}

export function sourceReasonLabel(reasonCode: string | null | undefined) {
	const labels: Record<string, string> = {
		blocked_backend_unavailable: 'Liepin 浏览器执行暂不可用。',
		failed_provider_error: '检索源返回错误。',
		login_required: '需要先完成 Liepin 登录。',
		partial_timeout: '部分结果已返回，检索超时停止。',
		cancelled_by_user: '检索已取消。',
		liepin_connection_not_connected: 'Liepin 连接未就绪。'
	};
	if (!reasonCode) return null;
	return labels[reasonCode] ?? '检索源需要处理。';
}

export function selectedSourceKinds(input: { cts: boolean; liepin: boolean }): SourceKind[] {
	const result: SourceKind[] = [];
	if (input.cts) result.push('cts');
	if (input.liepin) result.push('liepin');
	return result;
}
```

Add tests in `apps/web-svelte/src/lib/workbench/sourceDisplay.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { readinessStatusLabel, readinessTone, selectedSourceKinds, sourceReasonLabel, sourceStatusLabel } from './sourceDisplay';

describe('source display helpers', () => {
	it('preserves explicit source order', () => {
		expect(selectedSourceKinds({ cts: true, liepin: true })).toEqual(['cts', 'liepin']);
		expect(selectedSourceKinds({ cts: false, liepin: true })).toEqual(['liepin']);
	});

	it('maps statuses to business-facing labels', () => {
		expect(sourceStatusLabel('running')).toBe('检索中');
		expect(sourceStatusLabel('blocked')).toBe('已阻塞');
		expect(readinessStatusLabel('missing')).toBe('缺少配置');
		expect(readinessTone('configured')).toBe('ready');
		expect(readinessTone('missing')).toBe('warning');
		expect(sourceReasonLabel('blocked_backend_unavailable')).toContain('暂不可用');
		expect(sourceReasonLabel('secret-token')).toBe('检索源需要处理。');
	});
});
```

- [ ] **Step 2: Create readiness panel**

Create `apps/web-svelte/src/lib/components/DevModeReadinessPanel.svelte`:

```svelte
<script lang="ts">
	import type { WorkbenchDevModeStatus } from '$lib/workbench/types';
	import { readinessStatusLabel, readinessTone } from '$lib/workbench/sourceDisplay';

	type Props = {
		status: WorkbenchDevModeStatus | null;
		loading?: boolean;
		error?: string | null;
	};

	let { status, loading = false, error = null }: Props = $props();
</script>

<section class="readiness-panel" aria-labelledby="readiness-title">
	<div>
		<p class="eyebrow">Dev mode BYOK</p>
		<h2 id="readiness-title">本地运行准备</h2>
	</div>
	{#if loading}
		<p>正在检查本地配置。</p>
	{:else if error}
		<p class="readiness-warning">{error}</p>
	{:else if status}
		<div class="readiness-grid">
			{#each Object.entries(status.credentials) as [key, item] (key)}
				<div class={`readiness-item ${readinessTone(item.status)}`}>
					<strong>{item.label}</strong>
					<span>{readinessStatusLabel(item.status)}</span>
				</div>
			{/each}
			{#each Object.entries(status.sources) as [key, item] (key)}
				<div class={`readiness-item ${readinessTone(item.status)}`}>
					<strong>{item.label}</strong>
					<span>{readinessStatusLabel(item.status)}</span>
					{#if item.authNote}<small>{item.authNote}</small>{/if}
				</div>
			{/each}
			{#each Object.entries(status.dataRoots.roots) as [key, item] (key)}
				<div class={`readiness-item ${item.status}`}>
					<strong>{item.label}</strong>
					<span>{readinessStatusLabel(item.status)}</span>
				</div>
			{/each}
		</div>
	{:else}
		<p>暂无本地准备状态。</p>
	{/if}
</section>
```

- [ ] **Step 3: Create source selector and session form**

Create `apps/web-svelte/src/lib/components/SourceSelector.svelte`:

```svelte
<script lang="ts">
	import type { SourceKind } from '$lib/workbench/sourceDisplay';

	type Props = {
		selected: SourceKind[];
		onChange: (selected: SourceKind[]) => void;
		disabled?: boolean;
	};

	let { selected, onChange, disabled = false }: Props = $props();
	const options: { value: SourceKind; label: string; description: string }[] = [
		{ value: 'cts', label: 'CTS', description: '结构化简历源' },
		{ value: 'liepin', label: 'Liepin', description: 'Pi + DokoBot 浏览器源' }
	];

	function toggle(value: SourceKind) {
		const next = selected.includes(value)
			? selected.filter((source) => source !== value)
			: [...selected, value];
		onChange(next);
	}
</script>

<div class="source-selector" role="group" aria-label="检索源">
	{#each options as option (option.value)}
		<button
			type="button"
			class:selected={selected.includes(option.value)}
			{disabled}
			onclick={() => toggle(option.value)}
		>
			<strong>{option.label}</strong>
			<span>{option.description}</span>
		</button>
	{/each}
</div>
```

Create `apps/web-svelte/src/lib/components/NewSessionForm.svelte`:

```svelte
<script lang="ts">
	import SourceSelector from './SourceSelector.svelte';
	import type { SourceKind } from '$lib/workbench/sourceDisplay';

	type SubmitInput = {
		jobTitle: string;
		jdText: string;
		notes: string;
		sourceKinds: SourceKind[];
	};

	type Props = {
		submitting?: boolean;
		error?: string | null;
		onSubmit: (input: SubmitInput) => void;
	};

	let { submitting = false, error = null, onSubmit }: Props = $props();
	let jobTitle = $state('');
	let jdText = $state('');
	let notes = $state('');
	let sourceKinds = $state<SourceKind[]>(['cts', 'liepin']);

	function submit() {
		onSubmit({
			jobTitle: jobTitle.trim(),
			jdText: jdText.trim(),
			notes: notes.trim(),
			sourceKinds
		});
	}
</script>

<form class="new-session-form" onsubmit={(event) => { event.preventDefault(); submit(); }}>
	<div class="form-row">
		<label>
			<span>岗位名称</span>
			<input bind:value={jobTitle} required maxlength="256" />
		</label>
	</div>
	<label>
		<span>JD</span>
		<textarea bind:value={jdText} required maxlength="20000" rows="8"></textarea>
	</label>
	<label>
		<span>补充说明</span>
		<textarea bind:value={notes} maxlength="5000" rows="3"></textarea>
	</label>
	<SourceSelector selected={sourceKinds} disabled={submitting} onChange={(next) => (sourceKinds = next)} />
	{#if error}<p class="form-error">{error}</p>{/if}
	<button class="button" type="submit" disabled={submitting || sourceKinds.length === 0}>
		{submitting ? '正在创建' : '创建检索会话'}
	</button>
</form>
```

- [ ] **Step 4: Wire the sessions page**

Update `apps/web-svelte/src/routes/(app)/sessions/+page.svelte` by preserving the existing imports and adding the new dependencies. The merged import block should include:

```svelte
import { goto } from '$app/navigation';
import { resolve } from '$app/paths';
import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';
import { safeErrorMessage } from '$lib/api/errors';
import { createSession, getDevModeStatus, listSessions } from '$lib/api/workbench';
import DevModeReadinessPanel from '$lib/components/DevModeReadinessPanel.svelte';
import ErrorState from '$lib/components/ErrorState.svelte';
import LoadingState from '$lib/components/LoadingState.svelte';
import NewSessionForm from '$lib/components/NewSessionForm.svelte';
import { workbenchKeys } from '$lib/query/keys';
```

Add queries and mutation:

```svelte
const queryClient = useQueryClient();
const devModeQuery = createQuery(() => ({
	queryKey: workbenchKeys.devModeStatus,
	queryFn: getDevModeStatus
}));

const createSessionMutation = createMutation(() => ({
	mutationFn: createSession,
	onSuccess: async (session) => {
		await queryClient.invalidateQueries({ queryKey: workbenchKeys.sessions });
		await goto(resolve(`/sessions/${session.sessionId}`));
	}
}));
```

Place this above the session list:

```svelte
<DevModeReadinessPanel
	status={devModeQuery.data ?? null}
	loading={devModeQuery.isPending}
	error={devModeQuery.error ? safeErrorMessage(devModeQuery.error, '本地准备状态加载失败') : null}
/>

<NewSessionForm
	submitting={createSessionMutation.isPending}
	error={createSessionMutation.error
		? safeErrorMessage(createSessionMutation.error, '会话创建失败')
		: null}
	onSubmit={(input) => createSessionMutation.mutate(input)}
/>
```

- [ ] **Step 5: Add component tests**

Create `apps/web-svelte/src/lib/components/NewSessionForm.test.ts`:

```ts
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import NewSessionForm from './NewSessionForm.svelte';

describe('NewSessionForm', () => {
	it('submits explicit CTS and Liepin source selection', async () => {
		const user = userEvent.setup();
		const onSubmit = vi.fn();
		render(NewSessionForm, { props: { onSubmit } });

		await user.type(screen.getByLabelText('岗位名称'), 'AI Recruiter Engineer');
		await user.type(screen.getByLabelText('JD'), 'Build local sourcing agents.');
		await user.click(screen.getByRole('button', { name: '创建检索会话' }));

		expect(onSubmit).toHaveBeenCalledWith({
			jobTitle: 'AI Recruiter Engineer',
			jdText: 'Build local sourcing agents.',
			notes: '',
			sourceKinds: ['cts', 'liepin']
		});
	});
});
```

- [ ] **Step 6: Run Svelte flow tests**

Run:

```bash
cd apps/web-svelte
bun run test src/lib/workbench/sourceDisplay.test.ts src/lib/components/NewSessionForm.test.ts
bun run check
```

Expected: tests pass and typecheck passes.

- [ ] **Step 7: Commit**

```bash
git add apps/web-svelte/src/lib/workbench/sourceDisplay.ts apps/web-svelte/src/lib/workbench/sourceDisplay.test.ts apps/web-svelte/src/lib/components/DevModeReadinessPanel.svelte apps/web-svelte/src/lib/components/SourceSelector.svelte apps/web-svelte/src/lib/components/NewSessionForm.svelte apps/web-svelte/src/lib/components/NewSessionForm.test.ts 'apps/web-svelte/src/routes/(app)/sessions/+page.svelte'
git commit -m "feat: add svelte dev readiness session creation"
```

## Task 4: Add Svelte Triage And Source Run Controls

**Files:**

- Create: `apps/web-svelte/src/lib/components/SourceRunControlPanel.svelte`
- Create: `apps/web-svelte/src/lib/components/RequirementTriagePanel.svelte`
- Create: `apps/web-svelte/src/lib/components/SourceStatusStrip.svelte`
- Modify: `apps/web-svelte/src/routes/(app)/sessions/[sessionId]/+page.svelte`
- Test: `apps/web-svelte/src/lib/components/SourceRunControlPanel.test.ts`

- [ ] **Step 1: Create source status strip**

Create `apps/web-svelte/src/lib/components/SourceStatusStrip.svelte`:

```svelte
<script lang="ts">
	import type { WorkbenchSession } from '$lib/workbench/types';
	import { sourceReasonLabel, sourceStatusLabel } from '$lib/workbench/sourceDisplay';

	type Props = {
		session: WorkbenchSession;
	};

	let { session }: Props = $props();
	const runtimeSources = $derived(
		new Map((session.runtimeSourceState?.sources ?? []).map((source) => [source.sourceKind, source]))
	);
</script>

<section class="source-status-strip" aria-label="检索源状态">
		{#each session.sourceCards as source (source.sourceRunId)}
			{@const runtime = runtimeSources.get(source.sourceKind)}
			{@const displayStatus = runtime?.status ?? source.status}
			{@const reasonLabel = sourceReasonLabel(runtime?.reasonCode ?? source.warningCode ?? source.connectionWarningCode)}
			<article class={`source-status-card ${displayStatus}`}>
			<div>
				<p class="eyebrow">{source.label}</p>
				<h2>{sourceStatusLabel(displayStatus)}</h2>
			</div>
			<dl>
				<div><dt>已扫描</dt><dd>{runtime?.cardsSeenCount ?? source.cardsScannedCount}</dd></div>
				<div><dt>候选人</dt><dd>{runtime?.candidatesCount ?? source.uniqueCandidatesCount}</dd></div>
				<div><dt>详情</dt><dd>{runtime?.detailRecommendationsCount ?? source.detailOpenUsedCount}/{source.detailOpenBlockedCount}</dd></div>
			</dl>
			{#if source.connectionStatus}
				<p class="source-note">连接：{source.connectionStatus}</p>
			{/if}
			{#if reasonLabel}
				<p class="source-warning">{reasonLabel}</p>
			{/if}
			{#if source.warningMessage}
				<p class="source-warning">{source.warningMessage}</p>
			{/if}
		</article>
	{/each}
</section>
```

- [ ] **Step 2: Create requirement triage review panel**

Create `apps/web-svelte/src/lib/components/RequirementTriagePanel.svelte`:

```svelte
<script lang="ts">
	import type { WorkbenchSession } from '$lib/workbench/types';

	type VisibleTriage = Pick<
		WorkbenchSession['requirementTriage'],
		'status' | 'mustHaves' | 'niceToHaves' | 'synonyms' | 'seniorityFilters' | 'exclusions' | 'generatedQueryHints'
	>;
	type TriageSession = { requirementTriage: VisibleTriage };

	type Props = {
		session: TriageSession;
	};

	let { session }: Props = $props();
	const triage = $derived(session.requirementTriage);
	const sections = $derived([
		['必须条件', triage.mustHaves],
		['加分项', triage.niceToHaves],
		['同义词', triage.synonyms],
		['年限/职级过滤', triage.seniorityFilters],
		['排除项', triage.exclusions],
		['检索提示', triage.generatedQueryHints]
	] as const);
	const hasCriteria = $derived(sections.some(([, values]) => values.length > 0));
</script>

<section class="triage-panel" aria-labelledby="triage-title">
	<div>
		<p class="eyebrow">需求确认</p>
		<h2 id="triage-title">检索标准</h2>
	</div>
	{#if !hasCriteria}
		<p class="empty-state">先生成标准，再确认并启动检索。</p>
	{:else}
		<div class="triage-grid">
			{#each sections as [label, values] (label)}
				<section>
					<h3>{label}</h3>
					{#if values.length > 0}
						<ul>
							{#each values as value (value)}
								<li>{value}</li>
							{/each}
						</ul>
					{:else}
						<p>暂无</p>
					{/if}
				</section>
			{/each}
		</div>
	{/if}
</section>
```

The approval button in `SourceRunControlPanel` must be visually adjacent to this panel. The user must be able to see the generated criteria before approving.

- [ ] **Step 3: Create run control panel**

Create `apps/web-svelte/src/lib/components/SourceRunControlPanel.svelte`:

```svelte
<script lang="ts">
	import type { WorkbenchSession } from '$lib/workbench/types';

	type VisibleTriage = Pick<
		WorkbenchSession['requirementTriage'],
		'status' | 'mustHaves' | 'niceToHaves' | 'synonyms' | 'seniorityFilters' | 'exclusions' | 'generatedQueryHints'
	>;
	type RunControlSession = {
		requirementTriage: VisibleTriage;
		sourceRuns: Array<Pick<WorkbenchSession['sourceRuns'][number], 'status'>>;
	};

	type Props = {
		session: RunControlSession;
		preparing?: boolean;
		approving?: boolean;
		starting?: boolean;
		error?: string | null;
		onPrepare: () => void;
		onApprove: () => void;
		onStart: () => void;
	};

	let {
		session,
		preparing = false,
		approving = false,
		starting = false,
		error = null,
		onPrepare,
		onApprove,
		onStart
	}: Props = $props();

	const triageApproved = $derived(session.requirementTriage.status === 'approved');
	const hasVisibleCriteria = $derived(
		session.requirementTriage.mustHaves.length > 0 ||
			session.requirementTriage.niceToHaves.length > 0 ||
			session.requirementTriage.synonyms.length > 0 ||
			session.requirementTriage.seniorityFilters.length > 0 ||
			session.requirementTriage.exclusions.length > 0 ||
			session.requirementTriage.generatedQueryHints.length > 0
	);
	const hasActiveSource = $derived(session.sourceRuns.some((run) => run.status === 'running'));
</script>

<section class="run-control-panel" aria-labelledby="run-control-title">
	<div>
		<p class="eyebrow">运行控制</p>
		<h2 id="run-control-title">确认标准并启动检索</h2>
	</div>
	<div class="run-control-actions">
		<button class="button secondary" type="button" disabled={preparing} onclick={onPrepare}>
			{preparing ? '正在生成标准' : '生成标准'}
		</button>
		<button class="button secondary" type="button" disabled={approving || triageApproved || !hasVisibleCriteria} onclick={onApprove}>
			{triageApproved ? '标准已确认' : approving ? '正在确认' : '确认标准'}
		</button>
		<button class="button" type="button" disabled={starting || !triageApproved || !hasVisibleCriteria || hasActiveSource} onclick={onStart}>
			{starting ? '正在启动' : '启动双源检索'}
		</button>
	</div>
	{#if error}<p class="form-error">{error}</p>{/if}
</section>
```

- [ ] **Step 4: Wire controls into session detail page**

Update `apps/web-svelte/src/routes/(app)/sessions/[sessionId]/+page.svelte` imports:

```svelte
import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';
import {
	approveRequirementTriage,
	getGraphCandidateResumeSnapshot,
	getSession,
	listGraphCandidates,
	listSessionEvents,
	prepareRequirementTriage,
	startSessionSourceRuns
} from '$lib/api/workbench';
import RequirementTriagePanel from '$lib/components/RequirementTriagePanel.svelte';
import SourceRunControlPanel from '$lib/components/SourceRunControlPanel.svelte';
import SourceStatusStrip from '$lib/components/SourceStatusStrip.svelte';
```

Add mutations:

```svelte
const queryClient = useQueryClient();
const refreshSession = async () => {
	await queryClient.invalidateQueries({ queryKey: workbenchKeys.session(data.sessionId) });
	await queryClient.invalidateQueries({ queryKey: workbenchKeys.sessionEvents(data.sessionId, 0) });
};

const prepareMutation = createMutation(() => ({
	mutationFn: () => prepareRequirementTriage(data.sessionId),
	onSuccess: refreshSession
}));
const approveMutation = createMutation(() => ({
	mutationFn: () => approveRequirementTriage(data.sessionId),
	onSuccess: refreshSession
}));
const startMutation = createMutation(() => ({
	mutationFn: () => startSessionSourceRuns(data.sessionId),
	onSuccess: refreshSession
}));
```

Render after the job brief:

```svelte
<RequirementTriagePanel session={sessionQuery.data} />
<SourceRunControlPanel
	session={sessionQuery.data}
	preparing={prepareMutation.isPending}
	approving={approveMutation.isPending}
	starting={startMutation.isPending}
	error={prepareMutation.error
		? safeErrorMessage(prepareMutation.error, '标准生成失败')
		: approveMutation.error
			? safeErrorMessage(approveMutation.error, '标准确认失败')
			: startMutation.error
				? safeErrorMessage(startMutation.error, '检索启动失败')
				: null}
	onPrepare={() => prepareMutation.mutate()}
	onApprove={() => approveMutation.mutate()}
	onStart={() => startMutation.mutate()}
/>
<SourceStatusStrip session={sessionQuery.data} />
```

- [ ] **Step 5: Add triage and control panel tests**

Create `apps/web-svelte/src/lib/components/SourceRunControlPanel.test.ts`:

```ts
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { WorkbenchSession } from '$lib/workbench/types';
import RequirementTriagePanel from './RequirementTriagePanel.svelte';
import SourceRunControlPanel from './SourceRunControlPanel.svelte';

type RunControlSession = {
	requirementTriage: Pick<
		WorkbenchSession['requirementTriage'],
		'status' | 'mustHaves' | 'niceToHaves' | 'synonyms' | 'seniorityFilters' | 'exclusions' | 'generatedQueryHints'
	>;
	sourceRuns: Array<Pick<WorkbenchSession['sourceRuns'][number], 'status'>>;
};

const session = {
	requirementTriage: {
		status: 'draft',
		mustHaves: [],
		niceToHaves: [],
		synonyms: [],
		seniorityFilters: [],
		exclusions: [],
		generatedQueryHints: []
	},
	sourceRuns: [{ status: 'queued' }]
} satisfies RunControlSession;

describe('SourceRunControlPanel', () => {
	it('blocks source start until triage is approved', async () => {
		const onStart = vi.fn();
		render(SourceRunControlPanel, {
			props: {
				session,
				onPrepare: vi.fn(),
				onApprove: vi.fn(),
				onStart
			}
		});

		expect(screen.getByRole('button', { name: '启动双源检索' })).toBeDisabled();
	});

	it('emits start when triage is approved', async () => {
		const user = userEvent.setup();
		const onStart = vi.fn();
		render(SourceRunControlPanel, {
			props: {
				session: {
					...session,
					requirementTriage: {
						...session.requirementTriage,
						status: 'approved',
						mustHaves: ['5 年以上 Python']
					}
				},
				onPrepare: vi.fn(),
				onApprove: vi.fn(),
				onStart
			}
		});

		await user.click(screen.getByRole('button', { name: '启动双源检索' }));
		expect(onStart).toHaveBeenCalledTimes(1);
	});

	it('renders generated triage criteria before approval', () => {
		render(RequirementTriagePanel, {
			props: {
				session: {
					...session,
					requirementTriage: {
						...session.requirementTriage,
						mustHaves: ['Svelte Workbench'],
						generatedQueryHints: ['recruiting agent']
					}
				}
			}
		});

		expect(screen.getByText('Svelte Workbench')).toBeInTheDocument();
		expect(screen.getByText('recruiting agent')).toBeInTheDocument();
	});
});
```

- [ ] **Step 6: Run verification**

Run:

```bash
cd apps/web-svelte
bun run test src/lib/components/SourceRunControlPanel.test.ts
bun run check
```

Expected: tests pass and typecheck passes.

- [ ] **Step 7: Commit**

```bash
git add apps/web-svelte/src/lib/components/RequirementTriagePanel.svelte apps/web-svelte/src/lib/components/SourceRunControlPanel.svelte apps/web-svelte/src/lib/components/SourceRunControlPanel.test.ts apps/web-svelte/src/lib/components/SourceStatusStrip.svelte 'apps/web-svelte/src/routes/(app)/sessions/[sessionId]/+page.svelte'
git commit -m "feat: add svelte source run controls"
```

## Task 5: Add Unified Top 10 And Detail Recommendation Display

**Files:**

- Create: `apps/web-svelte/src/lib/components/CandidateQueue.svelte`
- Create: `apps/web-svelte/src/lib/components/DetailRecommendationPanel.svelte`
- Modify: `apps/web-svelte/src/routes/(app)/sessions/[sessionId]/+page.svelte`
- Test: `apps/web-svelte/src/lib/components/CandidateQueue.test.ts`

- [ ] **Step 1: Create candidate queue**

Create `apps/web-svelte/src/lib/components/CandidateQueue.svelte`:

```svelte
<script lang="ts">
	import type { WorkbenchFinalTopCandidate } from '$lib/workbench/types';

	type Props = {
		items: WorkbenchFinalTopCandidate[];
		loading?: boolean;
		error?: string | null;
	};

	let { items, loading = false, error = null }: Props = $props();
</script>

<section class="candidate-queue" aria-labelledby="candidate-queue-title">
	<div>
		<p class="eyebrow">Top 10</p>
		<h2 id="candidate-queue-title">候选人队列</h2>
	</div>
	{#if loading}
		<p>正在加载候选人。</p>
	{:else if error}
		<p class="form-error">{error}</p>
	{:else if items.length === 0}
		<p>检索完成后会在这里显示统一排序候选人。</p>
	{:else}
		<ol>
			{#each items as item (item.identityId)}
				<li>
					<span class="rank">{item.rank}</span>
					<div>
						<strong>{item.displayName || '候选人'}</strong>
						<p>{item.title || '暂无标题'} · {item.company || '公司未知'} · {item.location || '地点未知'}</p>
						{#if item.summary}<small>{item.summary}</small>{/if}
						<div class="source-badges" aria-label="候选人来源">
							{#each item.sourceBadges as badge (badge)}
								<span>{badge}</span>
							{/each}
							<span>{item.evidenceLevel}</span>
						</div>
					</div>
					{#if item.aggregateScore !== null && item.aggregateScore !== undefined}
						<span class="score">{item.aggregateScore}</span>
					{/if}
				</li>
			{/each}
		</ol>
	{/if}
</section>
```

- [ ] **Step 2: Create detail recommendation panel**

Create `apps/web-svelte/src/lib/components/DetailRecommendationPanel.svelte`:

```svelte
<script lang="ts">
	import type { WorkbenchSession } from '$lib/workbench/types';

	type Props = {
		session: WorkbenchSession;
	};

	let { session }: Props = $props();
	const liepinSource = $derived(session.runtimeSourceState?.sources.find((source) => source.sourceKind === 'liepin'));
</script>

<section class="detail-recommendation-panel" aria-labelledby="detail-recommendation-title">
	<p class="eyebrow">Liepin detail budget</p>
	<h2 id="detail-recommendation-title">详情推荐</h2>
	{#if liepinSource}
		<dl>
			<div><dt>推荐</dt><dd>{liepinSource.detailRecommendationsCount}</dd></div>
			<div><dt>状态</dt><dd>{liepinSource.detailState ?? '无详情推荐'}</dd></div>
			<div><dt>已扫描</dt><dd>{liepinSource.cardsSeenCount}</dd></div>
			<div><dt>已过滤</dt><dd>{liepinSource.cardsFilteredCount}</dd></div>
		</dl>
	{:else}
		<p>当前会话未选择 Liepin。</p>
	{/if}
</section>
```

- [ ] **Step 3: Render candidate and detail panels**

In `apps/web-svelte/src/routes/(app)/sessions/[sessionId]/+page.svelte`, import:

```svelte
import CandidateQueue from '$lib/components/CandidateQueue.svelte';
import DetailRecommendationPanel from '$lib/components/DetailRecommendationPanel.svelte';
import { listFinalTopCandidates } from '$lib/api/workbench';
```

Remove any final-queue wiring that still imports `listCandidateReviewItems()` for this page. Review items may remain available for graph details, but they must not feed the final Top 10.

Add a final Top 10 query:

```svelte
const finalTopQuery = createQuery(() => ({
	queryKey: workbenchKeys.finalTop10(data.sessionId),
	queryFn: () => listFinalTopCandidates(data.sessionId)
}));
```

Render near the graph grid:

```svelte
<section class="workbench-summary-grid">
	<CandidateQueue
		items={finalTopQuery.data?.items ?? []}
		loading={finalTopQuery.isPending && Boolean(sessionQuery.data)}
		error={finalTopQuery.error ? safeErrorMessage(finalTopQuery.error, '候选人加载失败') : null}
	/>
	<DetailRecommendationPanel session={sessionQuery.data} />
</section>
```

Do not use `listCandidateReviewItems()` or frontend `items.slice(0, 10)` for the final queue. The queue must render the backend identity-level `final-top10` response.

- [ ] **Step 4: Add candidate queue test**

Create `apps/web-svelte/src/lib/components/CandidateQueue.test.ts`:

```ts
import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import type { WorkbenchFinalTopCandidate } from '$lib/workbench/types';
import CandidateQueue from './CandidateQueue.svelte';

describe('CandidateQueue', () => {
	it('renders backend identity-level top ten candidates', () => {
		const items = Array.from({ length: 10 }, (_, index) => ({
			identityId: `identity-${index}`,
			canonicalReviewItemId: `review-${index}`,
			mergedReviewItemIds: [`review-${index}`],
			rank: index + 1,
			displayName: `候选人 ${index + 1}`,
			title: 'AI Recruiter Engineer',
			company: 'SeekTalent',
			location: 'Shanghai',
			summary: 'Local dual-source recruiting workflow.',
			aggregateScore: 90 - index,
			fitBucket: 'strong',
			sourceBadges: ['CTS', 'Liepin card'],
			evidenceLevel: 'card',
			sourceEvidence: [
				{
					sourceKind: 'liepin',
					sourceRunId: 'source-liepin',
					evidenceLevel: 'card',
					score: 90 - index,
					fitBucket: 'strong'
				}
			]
		})) satisfies WorkbenchFinalTopCandidate[];

		render(CandidateQueue, { props: { items } });

		expect(screen.getByText('候选人 1')).toBeInTheDocument();
		expect(screen.getByText('候选人 10')).toBeInTheDocument();
		expect(screen.getAllByText('Liepin card').length).toBeGreaterThan(0);
	});
});
```

- [ ] **Step 5: Run verification**

Run:

```bash
cd apps/web-svelte
bun run test src/lib/components/CandidateQueue.test.ts
bun run check
```

Expected: tests pass and typecheck passes.

- [ ] **Step 6: Commit**

```bash
git add apps/web-svelte/src/lib/components/CandidateQueue.svelte apps/web-svelte/src/lib/components/CandidateQueue.test.ts apps/web-svelte/src/lib/components/DetailRecommendationPanel.svelte 'apps/web-svelte/src/routes/(app)/sessions/[sessionId]/+page.svelte'
git commit -m "feat: show svelte top ten candidate queue"
```

## Task 5A: Add Shared Workbench Styling And Responsive Layout

**Files:**

- Modify: `apps/web-svelte/src/routes/layout.css`

- [ ] **Step 1: Style the new milestone panels**

Update `apps/web-svelte/src/routes/layout.css` for the new classes introduced by Tasks 3-5:

- `.readiness-panel`, `.readiness-grid`, `.readiness-item`
- `.source-selector`
- `.new-session-form`
- `.triage-panel`, `.triage-grid`
- `.run-control-panel`, `.run-control-actions`
- `.source-status-strip`, `.source-status-card`
- `.candidate-queue`, `.source-badges`
- `.detail-recommendation-panel`
- `.workbench-summary-grid`

Rules:

- keep cards at 8px radius or less, matching the existing Svelte workbench tone;
- avoid nested card-in-card visual treatment;
- keep buttons stable in size and prevent long Chinese or English labels from overflowing;
- use restrained status tones for ready/warning/blocked/partial/completed without a one-note palette;
- make the session detail page scan like a recruiter workbench, not a marketing page.

- [ ] **Step 2: Add responsive rules**

Add explicit desktop/tablet/mobile behavior:

- desktop: readiness/session creation and session list can share a two-column workbench layout where space allows;
- tablet: stack primary panels but keep source status cards in a readable grid;
- narrow mobile: single column, no horizontal overflow, source selector wraps, action buttons remain tappable.

- [ ] **Step 3: Define responsive assertions for Task 7**

Do not edit the e2e file in this task, because Task 7 creates it. Task 7 must include viewports at 1440px, 1024px, and 390px and assert that primary controls are visible and no body-level horizontal overflow appears:

```ts
for (const size of [
	{ width: 1440, height: 1000 },
	{ width: 1024, height: 900 },
	{ width: 390, height: 900 }
]) {
	await page.setViewportSize(size);
	await expect(page.getByText('本地运行准备')).toBeVisible();
	await expect(page.getByRole('button', { name: '启动双源检索' })).toBeVisible();
	const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
	expect(overflow).toBe(false);
}
```

- [ ] **Step 4: Run styling verification**

Run:

```bash
cd apps/web-svelte
bun run check
```

Expected: typecheck passes. The viewport e2e assertions are verified in Task 7 after the e2e file exists.

- [ ] **Step 5: Commit**

```bash
git add apps/web-svelte/src/routes/layout.css
git commit -m "style: polish dev workbench responsive layout"
```

## Task 6: Preserve Dual-Source Runtime Behavior In Workbench Tests

**Files:**

- Test: `tests/test_workbench_dual_source_dev_mode.py`
- Modify: `src/seektalent_ui/workbench_store.py`

- [ ] **Step 1: Add focused dual-source Workbench tests**

Create `tests/test_workbench_dual_source_dev_mode.py`:

```python
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from seektalent.runtime.source_lanes import RuntimeSourceLaneResult
from seektalent_ui.workbench_store import WorkbenchStore, WorkbenchUser


def _store(tmp_path: Path) -> WorkbenchStore:
    return WorkbenchStore(tmp_path / ".seektalent" / "workbench.sqlite3")


def _user(store: WorkbenchStore) -> WorkbenchUser:
    user, _created = store.bootstrap_admin(
        email="admin@example.com",
        display_name="Admin",
        password_hash="hash",
    )
    return user


def _lease_time() -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()


def test_workbench_session_defaults_to_cts_and_liepin(tmp_path: Path) -> None:
    store = _store(tmp_path)
    user = _user(store)

    session = store.create_workbench_session(
        user=user,
        job_title="AI Recruiter Engineer",
        jd_text="Build local-first sourcing agents.",
        notes="dev pilot",
        source_kinds=None,
    )

    assert [run.source_kind for run in session.source_runs] == ["cts", "liepin"]


def test_liepin_blocked_result_does_not_remove_cts_source_run(tmp_path: Path) -> None:
    store = _store(tmp_path)
    user = _user(store)
    session = store.create_workbench_session(
        user=user,
        job_title="AI Recruiter Engineer",
        jd_text="Build local-first sourcing agents.",
        notes="dev pilot",
        source_kinds=["cts", "liepin"],
    )
    liepin_run = next(run for run in session.source_runs if run.source_kind == "liepin")
    context = store.start_source_run_job(
        user=user,
        session_id=session.session_id,
        source_run_id=liepin_run.source_run_id,
    )
    assert context is not None
    _source_run, job, _created = context
    claimed = store.claim_next_source_run_job(
        owner_id="test-worker",
        lease_expires_at=_lease_time(),
        source_kind="liepin",
    )
    assert claimed is not None

    result = RuntimeSourceLaneResult(
        runtime_run_id="runtime-test",
        source_plan_id="runtime-test:source:liepin",
        source_lane_run_id="runtime-test:lane:liepin:card",
        source="liepin",
        lane_mode="card",
        attempt=1,
        status="blocked",
        raw_candidate_count=0,
        blocked_reason_code="blocked_backend_unavailable",
    )
    store.complete_liepin_card_source_run_with_lane_result(context=claimed, result=result)
    updated = store.get_workbench_session(user=user, session_id=session.session_id)

    assert updated is not None
    statuses = {run.source_kind: run.status for run in updated.source_runs}
    assert statuses["liepin"] == "blocked"
    assert statuses["cts"] in {"pending", "queued", "running", "completed"}
```

- [ ] **Step 2: Run tests to verify current behavior**

Run:

```bash
uv run pytest tests/test_workbench_dual_source_dev_mode.py -q
```

Expected: tests pass after Task 0A. If they fail, the failure should identify a real regression in source-run scoping or status propagation.

- [ ] **Step 3: Repair only real behavioral gaps**

Patch `src/seektalent_ui/workbench_store.py` only when Step 2 exposes a real source-run state regression. The permitted repair is narrow: source-run completion must update only the source run bound to the claimed job. Do not change Runtime merge behavior here.

The update must preserve this invariant:

```python
def _source_run_update_scope(source_run_id: str) -> tuple[str, tuple[str]]:
    return "WHERE source_run_id = ?", (source_run_id,)
```

Use the existing SQL style in `WorkbenchStore`; do not introduce a new data access layer.

- [ ] **Step 4: Run backend verification**

Run:

```bash
uv run pytest tests/test_workbench_dual_source_dev_mode.py tests/test_runtime_source_lanes.py tests/test_liepin_runtime_source_lane.py -q
uv run ruff check src/seektalent_ui/workbench_store.py tests/test_workbench_dual_source_dev_mode.py
```

Expected: tests pass and ruff reports no issues.

- [ ] **Step 5: Commit**

```bash
git add tests/test_workbench_dual_source_dev_mode.py src/seektalent_ui/workbench_store.py
git commit -m "test: pin workbench dual source source-run behavior"
```

## Task 7: Add Milestone E2E With Safe Dual-Source Fixtures

**Files:**

- Create: `apps/web-svelte/tests/e2e/dev-mode-dual-source.spec.ts`
- Modify: `apps/web-svelte/tests/e2e/workbench-spike.spec.ts`
- Modify: `apps/web-svelte/playwright.config.ts` only if the existing config needs an additional project name.

- [ ] **Step 1: Create Playwright dual-source journey test**

Create `apps/web-svelte/tests/e2e/dev-mode-dual-source.spec.ts` with the same route-mocking style as `workbench-spike.spec.ts`. Include these required constants:

```ts
const SESSION_ID = 'session-dev-dual-source';
const RAW_LEAK_STRINGS = [
	'/private/artifacts/',
	'X-CSRF-Token',
	'Authorization',
	'cookie',
	'raw_provider_payload',
	'sk-local-secret-value',
	'cts-secret-value',
	'account-binding-secret-value'
];
```

Mock these endpoints:

```ts
await page.route('**/api/workbench/dev-mode/status', async (route) => {
	await route.fulfill({
		contentType: 'application/json',
		body: JSON.stringify({
			mode: 'dev_byok',
			overallStatus: 'ready',
			credentials: {
				text_llm: { status: 'configured', reasonCode: 'text_llm_byok_configured', label: 'Text LLM' },
				cts: { status: 'configured', reasonCode: 'cts_credentials_configured', label: 'CTS' }
			},
				sources: {
					cts: { status: 'configured', reasonCode: 'cts_ready_for_live_search', label: 'CTS', liveMode: 'cts', authNote: null },
					liepin: { status: 'configured', reasonCode: 'liepin_pi_agent_configured', label: 'Liepin', liveMode: 'pi_agent', authNote: 'Pi uses DokoBot inside the agent. User must already be logged into Liepin.' }
				},
				dataRoots: {
					overallStatus: 'warning',
					roots: {
						workspace_root: { status: 'warning', reasonCode: 'inside_repo', label: 'Workspace data root' }
					}
				}
			})
		});
});
```

Assert:

```ts
await expect(page.getByText('本地运行准备')).toBeVisible();
await expect(page.getByText('创建检索会话')).toBeVisible();
await expect(page.getByText('CTS')).toBeVisible();
await expect(page.getByText('Liepin')).toBeVisible();
await expect(page.getByText('启动双源检索')).toBeVisible();
await expect(page.getByText('Top 10')).toBeVisible();
await expect(page.getByText('详情推荐')).toBeVisible();

const visibleText = await page.locator('body').innerText();
for (const leak of RAW_LEAK_STRINGS) {
	expect(visibleText).not.toContain(leak);
}
```

Also include the responsive assertions defined in Task 5A:

```ts
for (const size of [
	{ width: 1440, height: 1000 },
	{ width: 1024, height: 900 },
	{ width: 390, height: 900 }
]) {
	await page.setViewportSize(size);
	await expect(page.getByText('本地运行准备')).toBeVisible();
	await expect(page.getByRole('button', { name: '启动双源检索' })).toBeVisible();
	const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
	expect(overflow).toBe(false);
}
```

- [ ] **Step 2: Include source start and polling assertions**

In the same test file, capture calls:

```ts
const calls: string[] = [];
await page.route('**/api/workbench/sessions/*/start', async (route) => {
	calls.push('start');
	await route.fulfill({
		contentType: 'application/json',
		status: 202,
		body: JSON.stringify({ sessionId: SESSION_ID, sourceRuns: [], blockedSources: [] })
	});
});
```

Assert:

```ts
await page.getByRole('button', { name: '启动双源检索' }).click();
expect(calls).toContain('start');
```

- [ ] **Step 3: Run e2e test**

Run:

```bash
cd apps/web-svelte
bun run test:e2e -- tests/e2e/dev-mode-dual-source.spec.ts
```

Expected: Playwright passes and screenshots do not show overlapping primary controls.

- [ ] **Step 4: Commit**

```bash
git add apps/web-svelte/tests/e2e/dev-mode-dual-source.spec.ts apps/web-svelte/tests/e2e/workbench-spike.spec.ts apps/web-svelte/playwright.config.ts
git commit -m "test: add svelte dual source milestone e2e"
```

## Task 8: Add Focused Milestone Verification Command

**Files:**

- Create: `scripts/verify-dev-workbench.sh`
- Modify: `docs/ui.md`
- Modify: `docs/configuration.md`

- [ ] **Step 1: Create verification script**

Create `scripts/verify-dev-workbench.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

uv run pytest \
  tests/test_dev_mode_readiness.py \
  tests/test_workbench_api.py \
  tests/test_workbench_semantic_guardrails.py \
  tests/test_workbench_dual_source_dev_mode.py \
  tests/test_runtime_source_lanes.py \
  tests/test_liepin_runtime_source_lane.py \
  tests/test_liepin_config.py \
  tests/test_liepin_pi_executor.py \
  tests/test_pi_external_agent.py \
  tests/test_pi_payload_firewall.py \
  -q

uv run ruff check \
  src/seektalent/dev_mode.py \
  src/seektalent_ui/final_top_candidates.py \
  src/seektalent_ui/models.py \
  src/seektalent_ui/workbench_routes.py \
  src/seektalent_ui/runtime_bridge.py \
  src/seektalent_ui/workbench_store.py \
  tests/test_dev_mode_readiness.py \
  tests/test_workbench_api.py \
  tests/test_workbench_semantic_guardrails.py \
  tests/test_workbench_dual_source_dev_mode.py

if [[ "${SEEKTALENT_VERIFY_PYTHON_ONLY:-0}" == "1" ]]; then
  echo "SEEKTALENT_VERIFY_PYTHON_ONLY=1; skipped Svelte verification" >&2
  exit 0
fi

command -v bun >/dev/null 2>&1 || {
  echo "bun not found; rerun with SEEKTALENT_VERIFY_PYTHON_ONLY=1 only for Python-only local checks" >&2
  exit 1
}

tmp_root="$(mktemp -d)"
api_pid=""
cleanup() {
  if [[ -n "$api_pid" ]]; then
    kill "$api_pid" 2>/dev/null || true
  fi
  rm -rf "$tmp_root"
}
trap cleanup EXIT

env SEEKTALENT_WORKSPACE_ROOT="$tmp_root" uv run seektalent-ui-api --host 127.0.0.1 --port 8012 &
api_pid=$!
until curl -fsS http://127.0.0.1:8012/openapi.json >/dev/null; do sleep 0.2; done

(
  cd apps/web-svelte
  bun run api:gen
  bun run check
  bun run lint
  bun run test
  bun run build
  bun run test:e2e
)

git diff --exit-code -- apps/web-svelte/src/lib/api/schema.d.ts

for forbidden in login-relay 'login/snapshot' 'login/frame' server_managed_browser managed_local external_http dokobot_action DokoBotActionSurface DokoBotActionTransportSession pi_runner.py; do
  if rg -n "$forbidden" apps/web-svelte/src; then
    echo "Forbidden legacy Liepin browser fallback reference found in Svelte milestone wiring: $forbidden" >&2
    exit 1
  fi
done

git diff --check
```

- [ ] **Step 2: Make executable and verify syntax**

Run:

```bash
chmod +x scripts/verify-dev-workbench.sh
bash -n scripts/verify-dev-workbench.sh
```

Expected: shell syntax check passes.

- [ ] **Step 3: Document the milestone command**

Add to `docs/ui.md`:

```markdown
## Dev Mode BYOK Svelte Workbench

The Svelte Workbench is the dev-mode pilot surface for the local dual-source milestone. It supports local BYOK readiness checks, session creation, requirement triage, CTS/Liepin source selection, source-run start, source status, strategy graph, candidate queue, and safe resume snapshots.

Run the focused milestone verification gate:

```bash
./scripts/verify-dev-workbench.sh
```

Live Liepin smoke is manual and explicit:

```bash
uv run seektalent liepin-smoke --live --worker-mode pi_agent --keyword "python" --page-size 1 --max-detail-opens 1
```

The smoke command requires local BYOK settings, Pi RPC configuration, DokoBot available inside Pi, and an already logged-in Liepin browser session. It is not part of the default automated gate.
```

Add to `docs/configuration.md`:

```markdown
### Dev Mode BYOK Readiness

For the first local dual-source Svelte milestone, BYOK readiness is diagnostic. The Workbench may report whether text LLM, CTS, Liepin/Pi settings, and local data-root posture are configured or risky, but it must not display API keys, tokens, cookies, command secrets, protected artifact paths, raw provider payloads, or sensitive local filesystem paths.

Required live variables:

- `SEEKTALENT_TEXT_LLM_API_KEY`
- `SEEKTALENT_CTS_TENANT_KEY`
- `SEEKTALENT_CTS_TENANT_SECRET`
- `SEEKTALENT_LIEPIN_WORKER_MODE=pi_agent`
- `SEEKTALENT_LIEPIN_PI_COMMAND=pi --mode rpc --no-session`
- `SEEKTALENT_LIEPIN_PI_SKILL_PATH=src/seektalent/providers/pi_agent/pi_skills/liepin_search_cards.md`
- `SEEKTALENT_LIEPIN_PI_DOKOBOT_TOOL_NAME=dokobot`
- `SEEKTALENT_LIEPIN_ACCOUNT_BINDING_SECRET=<local non-placeholder secret>`
```

- [ ] **Step 4: Run focused verification**

Run:

```bash
SEEKTALENT_VERIFY_PYTHON_ONLY=1 ./scripts/verify-dev-workbench.sh
```

Expected: Python-focused gate passes without requiring Bun.

Then run full verification where Bun is available:

```bash
./scripts/verify-dev-workbench.sh
```

Expected: Python tests, ruff, Svelte check, lint, tests, build, e2e, and `git diff --check` pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/verify-dev-workbench.sh docs/ui.md docs/configuration.md
git commit -m "chore: add dev workbench milestone verification"
```

## Task 9: Final Milestone Review Checklist

**Files:**

- Modify: `apps/web-svelte/SPIKE_REPORT.md`
- Modify: `TODOS.md`

- [ ] **Step 1: Update Svelte spike report status**

After Task 8 verification passes, append this section to `apps/web-svelte/SPIKE_REPORT.md`:

```markdown
## Dev Mode Dual-Source Milestone Update

Status: implemented

The Svelte app now covers dev-mode BYOK readiness, session creation, explicit CTS/Liepin source selection, requirement triage controls, source-run start, source status, unified Top 10 candidate queue, and Liepin detail recommendation visibility.

Verification:

```bash
./scripts/verify-dev-workbench.sh
```
```

- [ ] **Step 2: Keep deferred items accurate**

Review `TODOS.md`. Keep Svelte follow-ups that remain true after this milestone:

- bundle splitting for Svelte Flow/ELK if chunk warnings remain;
- OpenAPI drift checks if not fully in CI;
- UI library direction;
- polling versus SSE decision;
- broader manual card review and detail approval UI;
- platform-managed entitlement.

Remove only items demonstrably completed by this milestone. Do not delete deferred runtime platform items that remain out of scope.

- [ ] **Step 3: Run final verification**

Run:

```bash
./scripts/verify-dev-workbench.sh
uv run pytest tests -q
uv run ruff check src tests
git diff --check
```

Expected: all pass.

- [ ] **Step 4: Commit final docs**

```bash
git add apps/web-svelte/SPIKE_REPORT.md TODOS.md
git commit -m "docs: record dev workbench milestone status"
```

## Acceptance Checklist

- [ ] Svelte UI shows safe dev-mode BYOK readiness.
- [ ] Readiness includes local data-root posture without exposing sensitive local paths.
- [ ] Svelte UI can create a session with CTS and Liepin selected.
- [ ] Svelte UI can prepare, visibly review, and approve requirement triage.
- [ ] Svelte UI can start selected source runs.
- [ ] CTS source-run state remains independent when Liepin blocks.
- [ ] Liepin `pi_agent` posture is visible and safe.
- [ ] Strategy graph shows CTS and Liepin branches for dual-source sessions.
- [ ] Candidate queue displays a unified Top 10.
- [ ] Candidate queue uses the backend identity-level `WorkbenchFinalTopCandidateResponse` contract and shows source badges/evidence level.
- [ ] Detail recommendation and budget posture are visible.
- [ ] No UI renders API keys, tokens, cookies, auth headers, CSRF header names, raw provider payloads, or protected artifact paths.
- [ ] Verification runs `bun run api:gen` and fails on unexpected OpenAPI schema drift.
- [ ] Verification fails if Svelte milestone wiring calls old login relay, managed-browser, or direct browser fallback paths.
- [ ] Optional `seektalent liepin-smoke --live` remains manual and skipped by default.
- [ ] `./scripts/verify-dev-workbench.sh` passes.

## Self-Review Notes

- Spec coverage: the tasks cover dev-mode readiness including local data-root posture, Svelte session creation, visible triage review before approval, source start, dual-source status, candidate Top 10, detail recommendation visibility, responsive styling, focused verification, and docs.
- Scope control: platform-managed entitlement, full React replacement, Storybook, A2A, generic provider executor, cloud migration, and packaging remain out of scope.
- Type consistency: backend public model names use `WorkbenchDevMode*Response` and `WorkbenchFinalTopCandidate*Response`; Svelte type aliases reference generated OpenAPI `components['schemas']`; candidate queue examples use real identity-level final Top 10 fields; source values stay `cts | liepin`.
- Placeholder scan: no implementation step relies on unspecified provider fallback or hidden browser action surface; milestone verification checks that the Svelte milestone does not call legacy Liepin browser fallback endpoints.
