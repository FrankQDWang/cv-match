# Workbench Node Detail Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the recruiter workbench strategy graph and right inspector reflect real backend CTS/Liepin workflow data for business users: multi-round CTS rows, exploit/explore lane details, node-scoped candidate cards, expandable safe resume snapshots, and one full-height right inspector with `运行笔记` / `节点详情`.

**Architecture:** Keep the existing Workbench API style and React Flow + ELK graph surface. Add a small backend-safe graph relationship and resume snapshot contract so frontend nodes consume authoritative runtime/store data instead of inferring candidates from labels. Frontend keeps `buildRunStory()` as the business projection layer and moves candidate display into `NodeDetailPanel`.

**Tech Stack:** Python 3.12, FastAPI, SQLite, Pydantic, Bun, Vite, React 19, TypeScript, TanStack Query, `@xyflow/react`, `elkjs`, Vitest, Testing Library, Pytest.

---

## Scope Notes

- This plan assumes the current branch already contains the React Flow/ELK work from `docs/superpowers/plans/2026-05-11-interactive-strategy-graph.md`.
- Do not revert existing uncommitted implementation files unless the user explicitly asks.
- This plan does not change source execution semantics: selected sources are started through `POST /api/workbench/sessions/{session_id}/start`; CTS can run in parallel workers; Liepin remains protected by its current worker and detail-open ledger.
- This plan removes graph/log source filters from the UI. Selected sources are chosen at session creation and represented by source cards in the left column.

## File Structure

- Modify: `src/seektalent_ui/models.py`
  - Add response models for candidate graph relationships and resume snapshots.
- Modify: `src/seektalent_ui/workbench_store.py`
  - Add `candidate_graph_relationships` and `candidate_resume_snapshots` storage.
  - Persist CTS round/lane/candidate relationships from runtime artifacts.
  - Expose scoped relationship and safe snapshot lookup methods.
- Modify: `src/seektalent_ui/workbench_routes.py`
  - Include graph relationships in candidate queue responses.
  - Add `GET /api/workbench/candidates/{review_item_id}/resume-snapshot`.
- Modify: `tests/test_workbench_api.py`
  - Cover CTS relationship persistence, resume snapshot scoping, and redaction.
- Modify: `apps/web/src/types.ts`
  - Add frontend relationship and resume snapshot types.
- Modify: `apps/web/src/api.ts`
  - Add `getCandidateResumeSnapshot(reviewItemId)`.
- Modify: `apps/web/src/recruiterAnimation.ts`
  - Add CTS lane payload types, candidate refs, and node detail fields.
- Modify: `apps/web/src/runStory.ts`
  - Build multi-round CTS rows with stable requirement and previous-reflection edges.
  - Attach candidates to CTS recall/scoring/final nodes from backend relationships.
  - Add exploit/prf/generic lane summaries to query and result details.
- Modify: `apps/web/src/runStory.test.ts`
  - Cover multi-round layout semantics, two incoming round edges, CTS lane details, and candidate refs.
- Modify: `apps/web/src/strategyGraphLayout.ts`
  - Post-process CTS round nodes into vertically stacked rows with aligned keyword nodes.
  - Keep shared/final nodes readable with multi-source lanes.
- Modify: `apps/web/src/strategyGraphLayout.test.ts`
  - Cover round-row placement and aligned query nodes.
- Modify: `apps/web/src/StrategyGraph.tsx`
  - Enable local node dragging while keeping positions non-persistent.
- Modify: `apps/web/src/NodeDetailPanel.tsx`
  - Render node-scoped candidate cards.
  - Expand candidate cards to fetch safe resume snapshots.
- Modify: `apps/web/src/app.tsx`
  - Remove source filters from graph and running notes.
  - Replace right-side candidate/node tabs with `运行笔记` / `节点详情`.
  - Keep the central graph start button.
  - Keep source cards and detail mode controls in the left column.
- Modify: `apps/web/src/app.test.tsx`
  - Cover right inspector tabs, central start, no source selectors, candidate cards in node details, and snapshot expansion.
- Modify: `apps/web/src/styles.css`
  - Fixed-height collapsible JD brief, full-height right inspector, node candidate cards, snapshot sections, and graph canvas overflow/pan affordance.
- Modify: `docs/ui.md`
  - Update the workbench graph/inspector documentation so it no longer describes the removed candidate queue tab or source filters.

## Task 1: Backend Candidate Graph Relationship Contract

**Files:**
- Modify: `src/seektalent_ui/models.py`
- Modify: `src/seektalent_ui/workbench_store.py`
- Modify: `src/seektalent_ui/workbench_routes.py`
- Test: `tests/test_workbench_api.py`

- [ ] **Step 1: Write failing API test for CTS graph relationships**

Add this helper near `_candidate_artifacts()` in `tests/test_workbench_api.py`:

```python
def _candidate_artifacts_with_round_hits(tmp_path: Path) -> object:
    run_dir = tmp_path / "run-artifacts"
    hits_path = run_dir / "rounds" / "01" / "retrieval" / "query_resume_hits.json"
    hits_path.parent.mkdir(parents=True)
    hits_path.write_text(
        json.dumps(
            [
                {
                    "resume_id": "resume-1",
                    "round_no": 1,
                    "query_instance_id": "q-round-1-exploit",
                    "query_fingerprint": "fingerprint-exploit",
                    "lane_type": "exploit",
                    "query_role": "exploit",
                    "hit_sequence_no": 1,
                    "was_new_to_pool": True,
                    "final_candidate_status": "fit",
                    "overall_score": 91,
                },
                {
                    "resume_id": "resume-2",
                    "round_no": 1,
                    "query_instance_id": "q-round-1-prf",
                    "query_fingerprint": "fingerprint-prf",
                    "lane_type": "prf_probe",
                    "query_role": "explore",
                    "hit_sequence_no": 2,
                    "was_new_to_pool": True,
                    "final_candidate_status": "not_fit",
                    "overall_score": 64,
                },
            ],
            ensure_ascii=False,
        )
    )
    return SimpleNamespace(
        final_result=SimpleNamespace(
            candidates=[
                SimpleNamespace(
                    resume_id="resume-1",
                    final_score=91,
                    fit_bucket="fit",
                    match_summary="Strong FastAPI and retrieval systems background.",
                    why_selected="Best match for backend agent workflow.",
                    strengths=["Built SSE APIs"],
                    weaknesses=[],
                    matched_must_haves=["FastAPI"],
                    matched_preferences=["retrieval systems"],
                    risk_flags=[],
                    source_round=1,
                )
            ]
        ),
        run_dir=run_dir,
        candidate_store={
            "resume-1": SimpleNamespace(
                source_resume_id="source-resume-1",
                raw={"name": "Lin Qian", "fullText": "Full private resume text for Lin."},
                compact_summary=lambda: "Lin Qian · Senior Backend Engineer · SearchCo",
            ),
            "resume-2": SimpleNamespace(
                source_resume_id="source-resume-2",
                raw={"name": "Wang Yu", "fullText": "Full private resume text for Wang."},
                compact_summary=lambda: "Wang Yu · Data Engineer · DataCo",
            ),
        },
        normalized_store={
            "resume-1": SimpleNamespace(
                candidate_name="Lin Qian",
                headline="Backend platform engineer",
                current_title="Senior Backend Engineer",
                current_company="SearchCo",
                locations=["Shanghai"],
                raw_text_excerpt="FastAPI, retrieval ranking, SSE APIs.",
            ),
            "resume-2": SimpleNamespace(
                candidate_name="Wang Yu",
                headline="Data engineer",
                current_title="Data Engineer",
                current_company="DataCo",
                locations=["Hangzhou"],
                raw_text_excerpt="Batch pipelines and SQL platforms.",
            ),
        },
    )
```

Add this test after the existing CTS candidate-result test block:

```python
def test_cts_candidates_include_round_graph_relationships(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _bootstrap_and_login(client)
    session = _create_session(client, source_kinds=["cts"])
    session_id = session["sessionId"]
    _approve_triage(client, session_id)

    FakeWorkbenchRuntime.artifacts = _candidate_artifacts_with_round_hits(tmp_path)
    start = _start_session(client, session_id)
    assert start.status_code == 202, start.text
    FakeWorkbenchRuntime.started.wait(timeout=2)
    FakeWorkbenchRuntime.release.set()
    source_run_id = _started_source(start.json(), "cts")["sourceRunId"]
    _wait_for_source_status(client, session_id, source_run_id, "completed")

    candidates = client.get(f"/api/workbench/sessions/{session_id}/candidates")
    assert candidates.status_code == 200, candidates.text
    items = candidates.json()["items"]
    relationships = [
        relationship
        for item in items
        for relationship in item["graphRelationships"]
    ]

    assert {
        (rel["roundNo"], rel["laneType"], rel["relationshipKind"], rel["queryInstanceId"])
        for rel in relationships
    } >= {
        (1, "exploit", "recalled", "q-round-1-exploit"),
        (1, "exploit", "fit", "q-round-1-exploit"),
        (1, "prf_probe", "recalled", "q-round-1-prf"),
        (1, "prf_probe", "not_fit", "q-round-1-prf"),
    }
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
uv run pytest tests/test_workbench_api.py::test_cts_candidates_include_round_graph_relationships -q
```

Expected: FAIL because `graphRelationships` is not in `WorkbenchCandidateReviewItemResponse`.

- [ ] **Step 3: Add backend response/dataclass types**

In `src/seektalent_ui/workbench_store.py`, add:

```python
@dataclass(frozen=True)
class WorkbenchCandidateGraphRelationship:
    relationship_id: str
    review_item_id: str
    evidence_id: str
    source_run_id: str
    source_kind: Literal["cts", "liepin"]
    round_no: int
    query_instance_id: str
    query_fingerprint: str
    query_role: str
    lane_type: str
    relationship_kind: Literal["recalled", "new", "scored", "fit", "not_fit"]
    created_at: str
```

Add a field to `WorkbenchCandidateReviewItem`:

```python
graph_relationships: list[WorkbenchCandidateGraphRelationship]
```

In `src/seektalent_ui/models.py`, add:

```python
class WorkbenchCandidateGraphRelationshipResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relationshipId: str
    reviewItemId: str
    evidenceId: str
    sourceRunId: str
    sourceKind: SourceKind
    roundNo: int
    queryInstanceId: str
    queryFingerprint: str
    queryRole: str
    laneType: str
    relationshipKind: Literal["recalled", "new", "scored", "fit", "not_fit"]
    createdAt: str
```

Add this field to `WorkbenchCandidateReviewItemResponse`:

```python
graphRelationships: list[WorkbenchCandidateGraphRelationshipResponse]
```

- [ ] **Step 4: Add SQLite table and row mappers**

In `_initialize()` in `src/seektalent_ui/workbench_store.py`, after `candidate_evidence`, create:

```python
conn.execute(
    """
    CREATE TABLE IF NOT EXISTS candidate_graph_relationships (
        relationship_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        workspace_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        source_run_id TEXT NOT NULL,
        source_kind TEXT NOT NULL CHECK(source_kind IN ('cts', 'liepin')),
        review_item_id TEXT NOT NULL,
        evidence_id TEXT NOT NULL,
        round_no INTEGER NOT NULL,
        query_instance_id TEXT NOT NULL,
        query_fingerprint TEXT NOT NULL,
        query_role TEXT NOT NULL,
        lane_type TEXT NOT NULL,
        relationship_kind TEXT NOT NULL CHECK(relationship_kind IN ('recalled', 'new', 'scored', 'fit', 'not_fit')),
        created_at TEXT NOT NULL,
        FOREIGN KEY (review_item_id) REFERENCES candidate_review_items(review_item_id),
        FOREIGN KEY (evidence_id) REFERENCES candidate_evidence(evidence_id),
        FOREIGN KEY (source_run_id) REFERENCES source_runs(source_run_id)
    )
    """
)
conn.execute(
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_candidate_graph_relationships_unique
    ON candidate_graph_relationships(
        tenant_id, workspace_id, session_id, source_run_id,
        review_item_id, evidence_id, round_no, query_instance_id, relationship_kind
    )
    """
)
conn.execute(
    """
    CREATE INDEX IF NOT EXISTS idx_candidate_graph_relationships_review
    ON candidate_graph_relationships(tenant_id, workspace_id, session_id, review_item_id, round_no)
    """
)
```

Add helper functions:

```python
def _graph_relationships_by_review_item(
    conn: sqlite3.Connection,
    review_item_ids: list[str],
) -> dict[str, list[WorkbenchCandidateGraphRelationship]]:
    if not review_item_ids:
        return {}
    placeholders = ",".join("?" for _ in review_item_ids)
    rows = conn.execute(
        f"""
        SELECT *
        FROM candidate_graph_relationships
        WHERE review_item_id IN ({placeholders})
        ORDER BY round_no ASC, lane_type ASC, relationship_kind ASC, relationship_id ASC
        """,
        tuple(review_item_ids),
    ).fetchall()
    grouped: dict[str, list[WorkbenchCandidateGraphRelationship]] = {}
    for row in rows:
        grouped.setdefault(row["review_item_id"], []).append(_candidate_graph_relationship_from_row(row))
    return grouped


def _candidate_graph_relationship_from_row(row: sqlite3.Row) -> WorkbenchCandidateGraphRelationship:
    return WorkbenchCandidateGraphRelationship(
        relationship_id=row["relationship_id"],
        review_item_id=row["review_item_id"],
        evidence_id=row["evidence_id"],
        source_run_id=row["source_run_id"],
        source_kind=row["source_kind"],
        round_no=row["round_no"],
        query_instance_id=row["query_instance_id"],
        query_fingerprint=row["query_fingerprint"],
        query_role=row["query_role"],
        lane_type=row["lane_type"],
        relationship_kind=row["relationship_kind"],
        created_at=row["created_at"],
    )
```

- [ ] **Step 5: Wire relationships into candidate queue responses**

Update `_review_item_from_row(...)` to accept `graph_relationships` and set the new dataclass field.

Update `list_candidate_review_items(...)` and `_list_candidate_review_items_by_ids(...)`:

```python
relationships_by_review = _graph_relationships_by_review_item(conn, [row["review_item_id"] for row in rows])
```

Pass `relationships_by_review.get(row["review_item_id"], [])` into each review item.

In `src/seektalent_ui/workbench_routes.py`, add:

```python
def _candidate_graph_relationship_response(
    relationship: WorkbenchCandidateGraphRelationship,
) -> WorkbenchCandidateGraphRelationshipResponse:
    return WorkbenchCandidateGraphRelationshipResponse(
        relationshipId=relationship.relationship_id,
        reviewItemId=relationship.review_item_id,
        evidenceId=relationship.evidence_id,
        sourceRunId=relationship.source_run_id,
        sourceKind=relationship.source_kind,
        roundNo=relationship.round_no,
        queryInstanceId=relationship.query_instance_id,
        queryFingerprint=relationship.query_fingerprint,
        queryRole=relationship.query_role,
        laneType=relationship.lane_type,
        relationshipKind=relationship.relationship_kind,
        createdAt=relationship.created_at,
    )
```

Add this field in `_candidate_review_item_response(...)`:

```python
graphRelationships=[
    _candidate_graph_relationship_response(relationship)
    for relationship in item.graph_relationships
],
```

- [ ] **Step 6: Persist CTS relationships from runtime artifacts**

In `_persist_cts_candidate_results_conn(...)`, after current final candidate persistence, load query hits:

```python
query_hits = _cts_query_resume_hits_from_artifacts(artifacts)
```

Add helper:

```python
def _cts_query_resume_hits_from_artifacts(artifacts: object) -> list[dict[str, object]]:
    run_dir = _attr(artifacts, "run_dir")
    if run_dir is None:
        return []
    root = Path(run_dir)
    hits: list[dict[str, object]] = []
    for path in sorted(root.glob("rounds/*/retrieval/query_resume_hits.json")):
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, list):
            hits.extend(item for item in payload if isinstance(item, dict))
    return hits
```

For each hit with a candidate present in `candidate_store` or `normalized_store`, upsert a review item and a card-level evidence row. Then insert relationships using deterministic ids:

```python
relationship_id = _stable_id(
    "graphrel",
    context.session.session_id,
    context.job.source_run_id,
    provider_resume_id,
    query_instance_id,
    relationship_kind,
)
```

Relationship kind rules:

```python
relationship_kinds = ["recalled"]
if bool(hit.get("was_new_to_pool")):
    relationship_kinds.append("new")
status = _safe_candidate_text(hit.get("final_candidate_status"), 32)
if status == "fit":
    relationship_kinds.extend(["scored", "fit"])
elif status == "not_fit":
    relationship_kinds.extend(["scored", "not_fit"])
elif _int_or_none(hit.get("overall_score")) is not None:
    relationship_kinds.append("scored")
```

Use `lane_type`, `query_role`, `query_instance_id`, and `query_fingerprint` from the hit. Bound strings with `_safe_candidate_text(...)`.

- [ ] **Step 7: Run backend relationship test**

Run:

```bash
uv run pytest tests/test_workbench_api.py::test_cts_candidates_include_round_graph_relationships -q
```

Expected: PASS.

- [ ] **Step 8: Commit backend relationship contract**

```bash
git add src/seektalent_ui/models.py src/seektalent_ui/workbench_store.py src/seektalent_ui/workbench_routes.py tests/test_workbench_api.py
git commit -m "feat: expose workbench candidate graph relationships"
```

## Task 2: Safe Full Resume Snapshot Endpoint

**Files:**
- Modify: `src/seektalent_ui/models.py`
- Modify: `src/seektalent_ui/workbench_store.py`
- Modify: `src/seektalent_ui/workbench_routes.py`
- Test: `tests/test_workbench_api.py`

- [ ] **Step 1: Write failing API test for resume snapshot scoping and redaction**

Add:

```python
def test_candidate_resume_snapshot_is_authenticated_scoped_and_redacted(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _bootstrap_and_login(client)
    session = _create_session(client, source_kinds=["cts"])
    session_id = session["sessionId"]
    _approve_triage(client, session_id)

    FakeWorkbenchRuntime.artifacts = _candidate_artifacts_with_round_hits(tmp_path)
    start = _start_session(client, session_id)
    assert start.status_code == 202, start.text
    FakeWorkbenchRuntime.started.wait(timeout=2)
    FakeWorkbenchRuntime.release.set()
    source_run_id = _started_source(start.json(), "cts")["sourceRunId"]
    _wait_for_source_status(client, session_id, source_run_id, "completed")

    candidates = client.get(f"/api/workbench/sessions/{session_id}/candidates").json()["items"]
    review_item_id = candidates[0]["reviewItemId"]

    snapshot = client.get(f"/api/workbench/candidates/{review_item_id}/resume-snapshot")
    assert snapshot.status_code == 200, snapshot.text
    payload = snapshot.json()
    assert payload["reviewItemId"] == review_item_id
    assert payload["profile"]["displayName"]
    assert "full private resume text" in json.dumps(payload, ensure_ascii=False).lower()

    forbidden = json.dumps(payload, ensure_ascii=False).lower()
    for secret_word in ["cookie", "authorization", "storage", "cdp", "websocket", "provider_account_hash"]:
        assert secret_word not in forbidden

    other = _client(tmp_path)
    other_login = other.post("/api/auth/login", json={"email": "admin@example.com", "password": "correct horse"})
    assert other_login.status_code == 204
    other.cookies.clear()
    unauth = other.get(f"/api/workbench/candidates/{review_item_id}/resume-snapshot")
    assert unauth.status_code == 401
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
uv run pytest tests/test_workbench_api.py::test_candidate_resume_snapshot_is_authenticated_scoped_and_redacted -q
```

Expected: FAIL with route not found.

- [ ] **Step 3: Add snapshot models**

In `src/seektalent_ui/models.py`, add:

```python
class WorkbenchResumeSnapshotProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    displayName: str
    title: str
    company: str
    location: str
    summary: str


class WorkbenchCandidateResumeSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewItemId: str
    sourceKind: SourceKind
    evidenceLevel: WorkbenchCandidateEvidenceLevel
    profile: WorkbenchResumeSnapshotProfileResponse
    workExperience: list[str]
    education: list[str]
    projects: list[str]
    skills: list[str]
    sourceEvidenceText: str
    createdAt: str
```

- [ ] **Step 4: Add snapshot storage**

In `src/seektalent_ui/workbench_store.py`, add dataclass:

```python
@dataclass(frozen=True)
class WorkbenchCandidateResumeSnapshot:
    review_item_id: str
    source_kind: Literal["cts", "liepin"]
    evidence_level: CandidateEvidenceLevel
    profile: dict[str, str]
    work_experience: list[str]
    education: list[str]
    projects: list[str]
    skills: list[str]
    source_evidence_text: str
    created_at: str
```

Add table:

```python
conn.execute(
    """
    CREATE TABLE IF NOT EXISTS candidate_resume_snapshots (
        review_item_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        workspace_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        source_kind TEXT NOT NULL CHECK(source_kind IN ('cts', 'liepin')),
        evidence_level TEXT NOT NULL CHECK(evidence_level IN ('card', 'detail', 'final')),
        profile_json TEXT NOT NULL,
        work_experience_json TEXT NOT NULL,
        education_json TEXT NOT NULL,
        projects_json TEXT NOT NULL,
        skills_json TEXT NOT NULL,
        source_evidence_text TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (review_item_id) REFERENCES candidate_review_items(review_item_id)
    )
    """
)
```

When persisting CTS candidates, upsert a snapshot using normalized fields plus raw text:

```python
_upsert_candidate_resume_snapshot_conn(
    conn,
    review_item_id=review_item_id,
    tenant_id=DEFAULT_TENANT_ID,
    workspace_id=context.session.workspace_id,
    user_id=context.session.owner_user_id,
    session_id=context.session.session_id,
    source_kind="cts",
    evidence_level="final" if provider_resume_id in final_candidate_ids else "card",
    profile={
        "displayName": display_name,
        "title": title,
        "company": company,
        "location": location,
        "summary": summary,
    },
    source_evidence_text=_safe_resume_snapshot_text(raw_candidate, normalized),
    now=now,
)
```

Sanitizer:

```python
def _safe_resume_snapshot_text(raw_candidate: object, normalized: object) -> str:
    values = [
        _safe_candidate_text(_attr(normalized, "raw_text_excerpt"), 5000),
        _safe_candidate_text(_attr(raw_candidate, "compact_summary")() if callable(_attr(raw_candidate, "compact_summary")) else "", 3000),
        _safe_candidate_text(json.dumps(_attr(raw_candidate, "raw"), ensure_ascii=False, default=str), 8000),
    ]
    text = "\n".join(value for value in values if value)
    return redact_text(text)[:12000]
```

- [ ] **Step 5: Add scoped route**

Add store method:

```python
def get_candidate_resume_snapshot(
    self,
    *,
    user: WorkbenchUser,
    review_item_id: str,
) -> WorkbenchCandidateResumeSnapshot | None:
    self._initialize()
    with self._connect() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM candidate_resume_snapshots
            WHERE workspace_id = ? AND user_id = ? AND review_item_id = ?
            """,
            (user.workspace_id, user.user_id, review_item_id),
        ).fetchone()
    return _candidate_resume_snapshot_from_row(row) if row is not None else None
```

Add route in `src/seektalent_ui/workbench_routes.py`:

```python
@router.get(
    "/api/workbench/candidates/{review_item_id}/resume-snapshot",
    response_model=WorkbenchCandidateResumeSnapshotResponse,
)
def get_candidate_resume_snapshot(
    review_item_id: str,
    request: Request,
    user: WorkbenchUser = Depends(require_current_user),
) -> WorkbenchCandidateResumeSnapshotResponse:
    store = get_workbench_store(request)
    snapshot = store.get_candidate_resume_snapshot(user=user, review_item_id=review_item_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Not found.")
    return _candidate_resume_snapshot_response(snapshot)
```

- [ ] **Step 6: Run snapshot tests**

Run:

```bash
uv run pytest tests/test_workbench_api.py::test_candidate_resume_snapshot_is_authenticated_scoped_and_redacted -q
```

Expected: PASS.

- [ ] **Step 7: Commit snapshot endpoint**

```bash
git add src/seektalent_ui/models.py src/seektalent_ui/workbench_store.py src/seektalent_ui/workbench_routes.py tests/test_workbench_api.py
git commit -m "feat: add safe candidate resume snapshots"
```

## Task 3: Frontend API And Type Contract

**Files:**
- Modify: `apps/web/src/types.ts`
- Modify: `apps/web/src/api.ts`
- Test: `apps/web/src/runStory.test.ts`

- [ ] **Step 1: Add frontend types**

In `apps/web/src/types.ts`, add:

```ts
export type WorkbenchCandidateGraphRelationshipKind = 'recalled' | 'new' | 'scored' | 'fit' | 'not_fit';

export type WorkbenchCandidateGraphRelationship = {
  relationshipId: string;
  reviewItemId: string;
  evidenceId: string;
  sourceRunId: string;
  sourceKind: SourceKind;
  roundNo: number;
  queryInstanceId: string;
  queryFingerprint: string;
  queryRole: string;
  laneType: 'exploit' | 'prf_probe' | 'generic_explore' | string;
  relationshipKind: WorkbenchCandidateGraphRelationshipKind;
  createdAt: string;
};

export type WorkbenchResumeSnapshotProfile = {
  displayName: string;
  title: string;
  company: string;
  location: string;
  summary: string;
};

export type WorkbenchCandidateResumeSnapshot = {
  reviewItemId: string;
  sourceKind: SourceKind;
  evidenceLevel: WorkbenchCandidateEvidenceLevel;
  profile: WorkbenchResumeSnapshotProfile;
  workExperience: string[];
  education: string[];
  projects: string[];
  skills: string[];
  sourceEvidenceText: string;
  createdAt: string;
};
```

Add this field to `WorkbenchCandidateReviewItem`:

```ts
graphRelationships: WorkbenchCandidateGraphRelationship[];
```

- [ ] **Step 2: Add API method**

In `WorkbenchApi` in `apps/web/src/api.ts`, add:

```ts
getCandidateResumeSnapshot(reviewItemId: string): Promise<WorkbenchCandidateResumeSnapshot>;
```

Import `WorkbenchCandidateResumeSnapshot`, then add implementation:

```ts
getCandidateResumeSnapshot(reviewItemId) {
  return request<WorkbenchCandidateResumeSnapshot>(
    `/api/workbench/candidates/${encodeURIComponent(reviewItemId)}/resume-snapshot`,
  );
},
```

- [ ] **Step 3: Update test factories**

Every `WorkbenchCandidateReviewItem` factory in `apps/web/src/runStory.test.ts` and `apps/web/src/app.test.tsx` must include:

```ts
graphRelationships: [],
```

- [ ] **Step 4: Run frontend typecheck**

Run:

```bash
cd apps/web && bun run typecheck
```

Expected: PASS.

- [ ] **Step 5: Commit frontend contract**

```bash
git add apps/web/src/types.ts apps/web/src/api.ts apps/web/src/runStory.test.ts apps/web/src/app.test.tsx
git commit -m "feat: add workbench candidate graph types"
```

## Task 4: Source-Aware Run Story With CTS Round Rows

**Files:**
- Modify: `apps/web/src/recruiterAnimation.ts`
- Modify: `apps/web/src/runStory.ts`
- Test: `apps/web/src/runStory.test.ts`

- [ ] **Step 1: Write failing runStory tests**

Add tests:

```ts
it('returns every CTS round keyword to the left and adds requirement plus reflection inputs', () => {
  const story = buildRunStory({
    session: session({ sourceCards: [session().sourceCards[0]], sourceRuns: [session().sourceRuns[0]] }),
    events: [
      event({
        globalSeq: 1,
        sourceKind: 'cts',
        eventName: 'runtime_requirements_completed',
        payload: { payload: { must_have_capabilities: ['Flink CDC'] } },
      }),
      event({
        globalSeq: 2,
        sourceKind: 'cts',
        eventName: 'runtime_round_completed',
        payload: {
          roundNo: 1,
          payload: {
            executed_queries: [{ query_terms: ['Flink CDC'], lane_type: 'exploit', query_role: 'exploit', query_instance_id: 'q1' }],
            raw_candidate_count: 10,
            unique_new_count: 4,
            newly_scored_count: 4,
            fit_count: 1,
            not_fit_count: 3,
            reflection_summary: '放宽到实时平台。',
          },
        },
      }),
      event({
        globalSeq: 3,
        sourceKind: 'cts',
        eventName: 'runtime_round_completed',
        payload: {
          roundNo: 2,
          payload: {
            executed_queries: [{ query_terms: ['实时平台'], lane_type: 'exploit', query_role: 'exploit', query_instance_id: 'q2' }],
            raw_candidate_count: 8,
            unique_new_count: 3,
            newly_scored_count: 3,
            fit_count: 1,
            not_fit_count: 2,
            reflection_summary: '继续扩大 CDC 同义词。',
          },
        },
      }),
    ],
    sourceFilter: 'cts',
  });

  expect(story.graphNodes.find((node) => node.id === 'cts-round-1-query')?.x).toBe(
    story.graphNodes.find((node) => node.id === 'cts-round-2-query')?.x,
  );
  expect(story.graphEdges).toEqual(
    expect.arrayContaining([
      expect.objectContaining({ from: 'requirements', to: 'cts-round-2-query', label: '需求约束' }),
      expect.objectContaining({ from: 'cts-round-1-reflect', to: 'cts-round-2-query', label: '反思调整' }),
    ]),
  );
});

it('attaches CTS lane relationships and candidates to round nodes', () => {
  const item = candidateReviewItem({
    reviewItemId: 'review-cts-1',
    sourceBadges: ['CTS'],
    graphRelationships: [
      {
        relationshipId: 'rel-1',
        reviewItemId: 'review-cts-1',
        evidenceId: 'evidence-cts-1',
        sourceRunId: 'src-cts',
        sourceKind: 'cts',
        roundNo: 1,
        queryInstanceId: 'q-round-1-exploit',
        queryFingerprint: 'fp',
        queryRole: 'exploit',
        laneType: 'exploit',
        relationshipKind: 'fit',
        createdAt: '2026-05-09T00:00:07Z',
      },
    ],
  });

  const story = buildRunStory({
    session: session({ sourceCards: [session().sourceCards[0]], sourceRuns: [session().sourceRuns[0]] }),
    events,
    candidateReviewItems: [item],
    sourceFilter: 'cts',
  });

  expect(story.graphNodes.find((node) => node.id === 'cts-round-1-result')?.candidateReviewItemIds).toContain('review-cts-1');
  expect(story.graphNodes.find((node) => node.id === 'cts-round-1-score')?.candidateReviewItemIds).toContain('review-cts-1');
});
```

- [ ] **Step 2: Run failing runStory tests**

Run:

```bash
cd apps/web && bun run test src/runStory.test.ts
```

Expected: FAIL on the new CTS round and relationship expectations.

- [ ] **Step 3: Extend detail payload types**

In `apps/web/src/recruiterAnimation.ts`, add:

```ts
export type RecruiterCtsLaneDetail = {
  laneType: string;
  queryRole: string;
  queryInstanceId: string;
  queryFingerprint: string;
  queryTerms: string[];
  candidateReviewItemIds: string[];
  recalledCount: number;
  scoredCount: number;
  fitCount: number;
  notFitCount: number;
};
```

Update `ctsRoundQuery`, `ctsRoundResults`, and `ctsRoundScoring` payloads:

```ts
lanes: RecruiterCtsLaneDetail[];
candidateReviewItemIds: string[];
```

- [ ] **Step 4: Parse CTS lane summaries**

In `apps/web/src/runStory.ts`, add helper:

```ts
type CtsRelationship = WorkbenchCandidateReviewItem['graphRelationships'][number];

function ctsRelationshipsForRound(
  candidateReviewItems: WorkbenchCandidateReviewItem[],
  roundNo: number,
): CtsRelationship[] {
  return candidateReviewItems.flatMap((item) =>
    item.graphRelationships.filter((relationship) => relationship.sourceKind === 'cts' && relationship.roundNo === roundNo),
  );
}

function ctsLaneDetails(
  round: RoundSummary,
  candidateReviewItems: WorkbenchCandidateReviewItem[],
): RecruiterCtsLaneDetail[] {
  const relationships = ctsRelationshipsForRound(candidateReviewItems, round.roundNo);
  const byLane = new Map<string, CtsRelationship[]>();
  for (const relationship of relationships) {
    byLane.set(relationship.laneType, [...(byLane.get(relationship.laneType) ?? []), relationship]);
  }
  const queryLanes = round.executedQueries.map((query) => query.laneType);
  for (const lane of queryLanes) {
    byLane.set(lane, byLane.get(lane) ?? []);
  }
  return [...byLane.entries()].map(([laneType, laneRelationships]) => {
    const query = round.executedQueries.find((item) => item.laneType === laneType);
    return {
      laneType,
      queryRole: query?.queryRole ?? (laneType === 'exploit' ? 'exploit' : 'explore'),
      queryInstanceId: query?.queryInstanceId ?? laneRelationships[0]?.queryInstanceId ?? '',
      queryFingerprint: query?.queryFingerprint ?? laneRelationships[0]?.queryFingerprint ?? '',
      queryTerms: query?.queryTerms ?? [],
      candidateReviewItemIds: uniqueStrings(laneRelationships.map((item) => item.reviewItemId)),
      recalledCount: laneRelationships.filter((item) => item.relationshipKind === 'recalled').length,
      scoredCount: laneRelationships.filter((item) => item.relationshipKind === 'scored').length,
      fitCount: laneRelationships.filter((item) => item.relationshipKind === 'fit').length,
      notFitCount: laneRelationships.filter((item) => item.relationshipKind === 'not_fit').length,
    };
  });
}
```

Add `executedQueries` to `RoundSummary` and parse `lane_type`, `query_role`, `query_instance_id`, and `query_fingerprint` from each executed query.

- [ ] **Step 5: Rebuild CTS round graph edges**

In `appendCtsLane(...)`, pass `candidateReviewItems` into the function. Replace round edge creation so round rows work:

```ts
const roundX = 42;
const roundYOffset = index * 20;
const queryY = positions.query + roundYOffset;
const resultY = positions.result + roundYOffset;
const scoreY = positions.score + roundYOffset;
const reflectY = positions.reflect + roundYOffset;
```

Set every query node `x` to `roundX`.

For round 1:

```ts
graphEdges.push({ from: anchor, to: queryId, tone: 'blue', label: '需求约束' });
graphEdges.push({ from: startId, to: queryId, tone: 'teal', label: '开始检索' });
```

For round N where `index > 0`:

```ts
graphEdges.push({ from: anchor, to: queryId, tone: 'blue', label: '需求约束' });
graphEdges.push({ from: previousReflectId, to: queryId, tone: 'violet', label: '反思调整' });
```

Then keep:

```ts
graphEdges.push(
  { from: queryId, to: resultId, tone: 'teal', label: 'CTS 检索' },
  { from: resultId, to: scoreId, tone: 'green', label: '评分' },
  { from: scoreId, to: reflectId, tone: 'violet', label: '复盘' },
);
```

- [ ] **Step 6: Attach CTS candidate ids to round nodes**

For each round:

```ts
const roundRelationships = ctsRelationshipsForRound(candidateReviewItems, round.roundNo);
const recalledIds = uniqueStrings(
  roundRelationships
    .filter((item) => item.relationshipKind === 'recalled' || item.relationshipKind === 'new')
    .map((item) => item.reviewItemId),
);
const scoredIds = uniqueStrings(
  roundRelationships
    .filter((item) => ['scored', 'fit', 'not_fit'].includes(item.relationshipKind))
    .map((item) => item.reviewItemId),
);
```

Attach `recalledIds` to `ctsRoundResults`, and `scoredIds` to `ctsRoundScoring`.

- [ ] **Step 7: Run runStory tests**

Run:

```bash
cd apps/web && bun run test src/runStory.test.ts
```

Expected: PASS.

- [ ] **Step 8: Commit story semantics**

```bash
git add apps/web/src/recruiterAnimation.ts apps/web/src/runStory.ts apps/web/src/runStory.test.ts
git commit -m "feat: model CTS round lanes in run story"
```

## Task 5: Layout CTS Rounds As Stacked Rows

**Files:**
- Modify: `apps/web/src/strategyGraphLayout.ts`
- Modify: `apps/web/src/StrategyGraph.tsx`
- Test: `apps/web/src/strategyGraphLayout.test.ts`

- [ ] **Step 1: Write failing layout test**

Add:

```ts
it('stacks CTS rounds vertically while keeping keyword nodes aligned', () => {
  const nodes = [
    node('requirements', 'shared', 20, 40),
    node('cts-round-1-query', 'cts', 42, 20),
    node('cts-round-1-result', 'cts', 58, 20),
    node('cts-round-1-score', 'cts', 74, 20),
    node('cts-round-1-reflect', 'cts', 90, 20),
    node('cts-round-2-query', 'cts', 42, 40),
    node('cts-round-2-result', 'cts', 58, 40),
    node('cts-round-2-score', 'cts', 74, 40),
    node('cts-round-2-reflect', 'cts', 90, 40),
  ];
  const graph = fallbackLayout(nodes, [], { width: 1200, height: 700 });
  const round1 = graph.nodes.find((item) => item.id === 'cts-round-1-query');
  const round2 = graph.nodes.find((item) => item.id === 'cts-round-2-query');

  expect(round1?.position.x).toBe(round2?.position.x);
  expect((round2?.position.y ?? 0) - (round1?.position.y ?? 0)).toBeGreaterThan(90);
});
```

- [ ] **Step 2: Run failing layout test**

Run:

```bash
cd apps/web && bun run test src/strategyGraphLayout.test.ts
```

Expected: FAIL because current lane stacking collapses same-lane round y positions.

- [ ] **Step 3: Add CTS round row post-processing**

In `apps/web/src/strategyGraphLayout.ts`, after `stackLanePositions(...)`, add:

```ts
const CTS_ROUND_X: Record<string, number> = {
  query: 260,
  result: 490,
  score: 720,
  reflect: 950,
};
const CTS_ROUND_Y_START = 120;
const CTS_ROUND_Y_GAP = 145;

function applyCtsRoundRows(
  positions: Map<string, GraphPosition>,
  nodes: RecruiterGraphNode[],
  bounds: GraphBounds,
): Map<string, GraphPosition> {
  const next = new Map(positions);
  const maxX = Math.max(GRAPH_INSET, bounds.width - NODE_WIDTH - GRAPH_INSET);
  for (const node of nodes) {
    const match = /^cts-round-(\d+)-(query|result|score|reflect)$/.exec(node.id);
    if (!match) {
      continue;
    }
    const roundNo = Number(match[1]);
    const stage = match[2];
    next.set(node.id, {
      x: clamp(CTS_ROUND_X[stage], GRAPH_INSET, maxX),
      y: clamp(CTS_ROUND_Y_START + (roundNo - 1) * CTS_ROUND_Y_GAP, GRAPH_INSET, bounds.height - NODE_HEIGHT - GRAPH_INSET),
    });
  }
  return next;
}
```

Call it in `layoutStrategyGraph(...)` and `fallbackLayout(...)`:

```ts
const stacked = stackLanePositions(rawPositions, nodes, bounds);
const positioned = applyCtsRoundRows(stacked, nodes, bounds);
return { nodes: flowNodes(nodes, positioned), edges: flowEdges(edges) };
```

- [ ] **Step 4: Enable local node dragging**

In `flowNodes(...)`, set:

```ts
draggable: true,
```

In `apps/web/src/StrategyGraph.tsx`, set:

```tsx
nodesDraggable
```

Keep positions non-persistent by leaving node state inside React Flow only and by resetting layout when story changes.

- [ ] **Step 5: Run layout tests**

Run:

```bash
cd apps/web && bun run test src/strategyGraphLayout.test.ts
```

Expected: PASS.

- [ ] **Step 6: Commit layout rows**

```bash
git add apps/web/src/strategyGraphLayout.ts apps/web/src/StrategyGraph.tsx apps/web/src/strategyGraphLayout.test.ts
git commit -m "feat: stack CTS graph rounds"
```

## Task 6: Move Candidate Display Into Node Detail

**Files:**
- Modify: `apps/web/src/NodeDetailPanel.tsx`
- Modify: `apps/web/src/app.tsx`
- Test: `apps/web/src/app.test.tsx`

- [ ] **Step 1: Write failing component tests**

Add tests:

```tsx
it('shows candidates inside selected graph node detail instead of a candidate tab', async () => {
  renderWithWorkbench(<App />);

  await userEvent.click(await screen.findByRole('button', { name: /第 1 轮关键词|搜到|评分/ }));

  expect(screen.getByRole('tab', { name: '节点详情' })).toHaveAttribute('aria-selected', 'true');
  expect(screen.queryByRole('tab', { name: '候选人队列' })).not.toBeInTheDocument();
  expect(await screen.findByText('Lin Qian')).toBeInTheDocument();
});

it('expands a candidate card and fetches the safe resume snapshot', async () => {
  renderWithWorkbench(<App />);

  await userEvent.click(await screen.findByRole('button', { name: /搜到/ }));
  await userEvent.click(await screen.findByRole('button', { name: /展开简历/ }));

  expect(await screen.findByText(/Full private resume text/)).toBeInTheDocument();
});
```

Use the existing test server mock to return `graphRelationships` and the new `/resume-snapshot` payload.

- [ ] **Step 2: Run failing app tests**

Run:

```bash
cd apps/web && bun run test src/app.test.tsx
```

Expected: FAIL because candidate cards are still in the candidate queue tab and snapshot API is not called.

- [ ] **Step 3: Change NodeDetailPanel props**

Update `NodeDetailPanelProps`:

```ts
type NodeDetailPanelProps = {
  node: RecruiterGraphNode | null;
  sessionId: string;
  candidateReviewItems: WorkbenchCandidateReviewItem[];
};
```

Build node candidates:

```ts
const nodeCandidates = node?.candidateReviewItemIds
  ? candidateReviewItems.filter((item) => node.candidateReviewItemIds?.includes(item.reviewItemId))
  : [];
```

Render candidate cards after payload details:

```tsx
{nodeCandidates.length > 0 ? (
  <section className="node-candidate-section">
    <span>相关候选人</span>
    {nodeCandidates.map((item) => (
      <NodeCandidateCard key={item.reviewItemId} sessionId={sessionId} item={item} />
    ))}
  </section>
) : null}
```

- [ ] **Step 4: Add expandable node candidate card**

In `NodeDetailPanel.tsx`, add:

```tsx
function NodeCandidateCard({ sessionId, item }: { sessionId: string; item: WorkbenchCandidateReviewItem }) {
  const { api } = useWorkbenchRuntime();
  const [expanded, setExpanded] = useState(false);
  const snapshotQuery = useQuery({
    queryKey: ['candidate-resume-snapshot', item.reviewItemId],
    queryFn: () => api.getCandidateResumeSnapshot(item.reviewItemId),
    enabled: expanded,
  });

  return (
    <article className={expanded ? 'node-candidate-card expanded' : 'node-candidate-card'}>
      <div className="node-candidate-head">
        <div>
          <strong>{item.displayName}</strong>
          <span>{[item.title, item.company, item.location].filter(Boolean).join(' · ')}</span>
        </div>
        <span className="score-badge">{item.aggregateScore ?? '-'}</span>
      </div>
      <p>{item.summary}</p>
      <div className="badge-row">
        {item.sourceBadges.map((badge) => <span key={badge} className="source-badge">{badge}</span>)}
        <span className="source-badge muted-badge">{item.evidenceLevel}</span>
      </div>
      <button className="secondary-link compact" type="button" onClick={() => setExpanded((value) => !value)}>
        {expanded ? '收起简历' : '展开简历'}
      </button>
      {expanded ? <ResumeSnapshotView query={snapshotQuery} /> : null}
    </article>
  );
}
```

Add `ResumeSnapshotView`:

```tsx
function ResumeSnapshotView({ query }: { query: UseQueryResult<WorkbenchCandidateResumeSnapshot, Error> }) {
  if (query.isLoading) {
    return <p className="muted">正在加载完整简历...</p>;
  }
  if (query.isError) {
    return <p className="form-error" role="alert">完整简历加载失败。</p>;
  }
  if (!query.data) {
    return null;
  }
  return (
    <div className="resume-snapshot">
      <DetailBlock title="简介" value={query.data.profile.summary} />
      <DetailList title="工作经历" values={query.data.workExperience} />
      <DetailList title="项目" values={query.data.projects} />
      <DetailList title="技能" values={query.data.skills} />
      <DetailBlock title="原始简历文本" value={query.data.sourceEvidenceText} />
    </div>
  );
}
```

- [ ] **Step 5: Pass candidates into NodeDetailPanel**

In `apps/web/src/app.tsx`, replace:

```tsx
nodePanel={<NodeDetailPanel node={selectedGraphNode} />}
```

with:

```tsx
nodePanel={
  <NodeDetailPanel
    node={selectedGraphNode}
    sessionId={session.sessionId}
    candidateReviewItems={candidateReviewItems}
  />
}
```

- [ ] **Step 6: Remove standalone candidate queue from the right inspector**

Remove `CandidateReviewQueue` and `DetailOpenRequestQueue` from `RightWorkbenchTabs`. Keep their helper code only if still used in node candidate actions; delete unused components after TypeScript confirms no references.

Change `RightWorkbenchTabs` tabs to:

```tsx
activeTab: 'notes' | 'node';
```

Tab labels:

```tsx
运行笔记
节点详情
```

- [ ] **Step 7: Run component tests**

Run:

```bash
cd apps/web && bun run test src/app.test.tsx
```

Expected: PASS.

- [ ] **Step 8: Commit node candidate detail**

```bash
git add apps/web/src/NodeDetailPanel.tsx apps/web/src/app.tsx apps/web/src/app.test.tsx
git commit -m "feat: show candidates in node detail"
```

## Task 7: Remove Source Filters And Preserve Central Start

**Files:**
- Modify: `apps/web/src/app.tsx`
- Modify: `apps/web/src/runStory.ts`
- Test: `apps/web/src/app.test.tsx`

- [ ] **Step 1: Write failing tests for no source selectors and central start**

Add:

```tsx
it('does not render graph or running-note source filters', async () => {
  renderWithWorkbench(<App />);

  expect(await screen.findByText('检索策略图')).toBeInTheDocument();
  expect(screen.queryByLabelText(/Source/)).not.toBeInTheDocument();
  expect(screen.queryByLabelText(/View/)).not.toBeInTheDocument();
});

it('keeps one central graph start button for the selected session sources', async () => {
  renderWithWorkbench(<App />);

  const button = await screen.findByRole('button', { name: /启动 Agent|确认并开始检索|启动检索/ });
  expect(button.closest('.strategy-panel')).not.toBeNull();
  expect(screen.queryByRole('button', { name: '启动全部' })).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run failing app tests**

Run:

```bash
cd apps/web && bun run test src/app.test.tsx
```

Expected: FAIL if source filters remain visible.

- [ ] **Step 3: Remove source filter state from WorkbenchShell**

Delete:

```ts
const [sourceFilter, setSourceFilter] = useState<SourceFilter>('all');
```

Use all selected sources:

```ts
const visibleStory = sessionStory;
const strategyEvents = useMemo(
  () => sessionEvents.filter((event) => event.eventName !== 'session_created'),
  [sessionEvents],
);
```

Remove `visibleEvents`.

- [ ] **Step 4: Remove SourceFilterControl usage**

Delete `SourceFilterControl(...)`.

Remove these props from `StrategyCanvas`:

```ts
sourceFilter
onSourceFilterChange
```

Remove these props from `ActivityLog`:

```ts
sourceFilter
onSourceFilterChange
sourceKinds
```

Keep `SourceLaneBands` by deriving active lanes from `story.graphNodes`.

- [ ] **Step 5: Keep central start semantics**

`StrategyCanvas` keeps:

```tsx
{canStart || startError ? (
  <div className="canvas-start-overlay">
    <button className="central-start" type="button" disabled={!canStart || starting} onClick={onStart}>
      {starting ? '处理中' : startLabel}
    </button>
    {startError ? <p className="form-error" role="alert">{startError}</p> : null}
  </div>
) : null}
```

No per-source start buttons are added.

- [ ] **Step 6: Run app tests**

Run:

```bash
cd apps/web && bun run test src/app.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Commit filter cleanup**

```bash
git add apps/web/src/app.tsx apps/web/src/runStory.ts apps/web/src/app.test.tsx
git commit -m "fix: remove strategy graph source filters"
```

## Task 8: Fixed Collapsible JD Brief And Right Inspector Layout

**Files:**
- Modify: `apps/web/src/app.tsx`
- Modify: `apps/web/src/styles.css`
- Test: `apps/web/src/app.test.tsx`

- [ ] **Step 1: Write failing tests for layout behavior**

Add:

```tsx
it('renders a collapsible fixed-height job brief with JD and notes previews', async () => {
  renderWithWorkbench(<App />);

  expect(await screen.findByText('岗位简报')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: '展开岗位简报' })).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: '展开岗位简报' }));
  expect(screen.getByRole('button', { name: '收起岗位简报' })).toBeInTheDocument();
});

it('uses running notes as the default right inspector tab', async () => {
  renderWithWorkbench(<App />);

  expect(await screen.findByRole('tab', { name: '运行笔记' })).toHaveAttribute('aria-selected', 'true');
  expect(screen.getByRole('tab', { name: '节点详情' })).toBeInTheDocument();
  expect(screen.queryByRole('tab', { name: '候选人队列' })).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run failing app tests**

Run:

```bash
cd apps/web && bun run test src/app.test.tsx
```

Expected: FAIL until the JD brief and right tabs are changed.

- [ ] **Step 3: Add collapsible job brief state**

In `WorkbenchShell`, add:

```ts
const [jobBriefExpanded, setJobBriefExpanded] = useState(false);
```

Wrap JD/notes:

```tsx
<section className={jobBriefExpanded ? 'job-brief expanded' : 'job-brief collapsed'}>
  <div className="job-brief-head">
    <div>
      <p className="section-label">岗位简报</p>
      <h2 data-testid="active-session-title">{session.jobTitle}</h2>
    </div>
    <button
      className="secondary-link compact"
      type="button"
      aria-label={jobBriefExpanded ? '收起岗位简报' : '展开岗位简报'}
      onClick={() => setJobBriefExpanded((value) => !value)}
    >
      {jobBriefExpanded ? '收起' : '展开'}
    </button>
  </div>
  <JobBriefBody session={session} expanded={jobBriefExpanded} />
</section>
```

Add `JobBriefBody` in the same file. In collapsed mode show a clipped JD preview and notes preview. In expanded mode show full JD and full notes.

- [ ] **Step 4: Update right inspector tabs**

`RightWorkbenchTabs` receives:

```tsx
notesPanel={<ActivityLog ... />}
nodePanel={<NodeDetailPanel ... />}
```

Default state:

```ts
const [rightDetailTab, setRightDetailTab] = useState<'notes' | 'node'>('notes');
```

When no selected graph node:

```ts
if (!selectedGraphNodeId) {
  setRightDetailTab('notes');
  return;
}
```

Clicking graph nodes still switches to `node`.

- [ ] **Step 5: Add CSS for fixed brief and inspector**

Add:

```css
.job-brief.collapsed {
  max-height: 320px;
  overflow: hidden;
}

.job-brief.expanded {
  max-height: none;
}

.right-workbench-tabs {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  min-height: 0;
  height: 100%;
}

.right-workbench-tabs [role='tabpanel'] {
  min-height: 0;
  overflow: auto;
}

.node-candidate-card {
  min-height: 168px;
  max-height: 220px;
  overflow: hidden;
}

.node-candidate-card.expanded {
  max-height: none;
}
```

- [ ] **Step 6: Run tests**

Run:

```bash
cd apps/web && bun run test src/app.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Commit layout shell**

```bash
git add apps/web/src/app.tsx apps/web/src/styles.css apps/web/src/app.test.tsx
git commit -m "feat: refine workbench inspector layout"
```

## Task 9: Business Running Notes Cleanup

**Files:**
- Modify: `apps/web/src/runStory.ts`
- Modify: `apps/web/src/app.tsx`
- Test: `apps/web/src/runStory.test.ts`
- Test: `apps/web/src/app.test.tsx`

- [ ] **Step 1: Write tests for business-readable notes**

Add:

```ts
it('does not expose raw runtime event names in business notes', () => {
  const story = buildRunStory({ session: session(), events, candidateReviewItems: [candidateReviewItem()], sourceFilter: 'all' });

  expect(story.logEntries.map((entry) => entry.text).join('\n')).not.toMatch(/runtime_|source_run_|candidate_review_item_/);
});
```

Add component assertion:

```tsx
expect(screen.queryByText('runtime_round_completed')).not.toBeInTheDocument();
expect(screen.getByText(/Developer log/)).toBeInTheDocument();
```

- [ ] **Step 2: Merge bursty same-stage notes**

In `runStory.ts`, before returning logs, add:

```ts
const sortedLogs = mergeBusinessLogBursts(
  logEntries.sort((left, right) => left.at - right.at || left.id.localeCompare(right.id)),
);
```

Add helper:

```ts
function mergeBusinessLogBursts(entries: RecruiterLogEntry[]): RecruiterLogEntry[] {
  const merged: RecruiterLogEntry[] = [];
  for (const entry of entries) {
    const previous = merged[merged.length - 1];
    if (
      previous &&
      previous.sourceKind === entry.sourceKind &&
      previous.tag === entry.tag &&
      Math.abs(previous.at - entry.at) < 0.25
    ) {
      merged[merged.length - 1] = {
        ...previous,
        text: `${previous.text}；${entry.text}`,
        relatedNodeId: entry.relatedNodeId ?? previous.relatedNodeId,
      };
      continue;
    }
    merged.push(entry);
  }
  return merged;
}
```

- [ ] **Step 3: Keep developer log collapsed**

In `ActivityLog`, keep raw events only behind the existing `Developer log` toggle. Default rendered text must only come from `story.logEntries`.

- [ ] **Step 4: Run notes tests**

Run:

```bash
cd apps/web && bun run test src/runStory.test.ts src/app.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit notes cleanup**

```bash
git add apps/web/src/runStory.ts apps/web/src/app.tsx apps/web/src/runStory.test.ts apps/web/src/app.test.tsx
git commit -m "fix: keep running notes business readable"
```

## Task 10: Documentation Update

**Files:**
- Modify: `docs/ui.md`

- [ ] **Step 1: Update strategy graph documentation**

Replace the current strategy graph paragraph in `docs/ui.md` that says the `候选人队列` tab remains available with:

```markdown
The workbench strategy graph is rendered with React Flow and laid out through ELK. It is not a workflow engine; it is a recruiter-facing projection of durable Workbench session events, source-run state, candidate evidence, and detail approval state.

Graph lanes separate shared job/requirement nodes from CTS and Liepin source work. CTS rounds are displayed as stacked rows: each round starts from the left, proceeds through keyword, recall, scoring, and reflection nodes, and later rounds show both requirement-context and previous-reflection inputs. Nodes are clickable business objects. Clicking a graph node opens the `节点详情` tab in the right inspector.

The right inspector has two tabs: `运行笔记` and `节点详情`. Candidate cards are shown inside the node detail for the workflow node that produced, scored, approved, or aggregated them. The previous standalone `候选人队列` inspector tab is no longer part of the workbench layout.
```

- [ ] **Step 2: Update running notes and source-filter documentation**

In `docs/ui.md`, add:

```markdown
The graph and running notes show all selected sources for the session. Source selection happens when the session is created and is represented by the left-column source cards. The graph and running notes do not expose source filters in the default recruiter workflow.
```

- [ ] **Step 3: Commit docs**

```bash
git add docs/ui.md
git commit -m "docs: update workbench inspector behavior"
```

## Task 11: Full Verification And Manual Smoke

**Files:**
- Modify only if verification exposes a defect in files already touched by this plan.

- [ ] **Step 1: Run frontend unit tests**

Run:

```bash
cd apps/web && bun run test
```

Expected: PASS.

- [ ] **Step 2: Run frontend typecheck**

Run:

```bash
cd apps/web && bun run typecheck
```

Expected: PASS.

- [ ] **Step 3: Run frontend build**

Run:

```bash
cd apps/web && bun run build
```

Expected: PASS.

- [ ] **Step 4: Run backend workbench tests**

Run:

```bash
uv run pytest tests/test_workbench_api.py tests/test_workbench_security_audit.py -q
```

Expected: PASS.

- [ ] **Step 5: Check diff cleanliness**

Run:

```bash
git diff --check
```

Expected: no output.

- [ ] **Step 6: Manual browser smoke**

Start backend:

```bash
uv run seektalent-ui-api
```

Start frontend in another terminal:

```bash
cd apps/web && bun run dev --host 127.0.0.1 --port 5176
```

Open `http://127.0.0.1:5176/` in the in-app browser and verify:

1. Create a CTS-only session.
2. Click the central graph start button.
3. Agent extracts criteria first.
4. Confirm criteria, then start CTS.
5. Strategy graph shows `需求拆解`, CTS source queue, round rows, recall/scoring/reflection, and final aggregation.
6. For round 2 or later, the keyword node has an edge from `需求拆解` and an edge from previous `反思`.
7. Clicking recall/scoring/final nodes opens `节点详情`.
8. Candidate cards appear inside node detail.
9. Expanding one card fetches the resume snapshot.
10. `运行笔记` shows business notes and no raw event names by default.
11. The graph and running notes have no source filter selectors.

- [ ] **Step 7: Commit verification fixes**

If Step 6 required small fixes:

```bash
git add apps/web/src src/seektalent_ui tests
git commit -m "fix: polish workbench node detail flow"
```

If no fixes were required, do not create an empty commit.

## Self-Review Checklist

- Spec coverage:
  - Fixed/collapsible JD brief: Task 8.
  - Right inspector as `运行笔记` / `节点详情`: Task 6 and Task 8.
  - Remove standalone candidate queue: Task 6.
  - Remove source filters from graph/log: Task 7.
  - CTS multi-round rows and dual inbound edges: Task 4 and Task 5.
  - CTS exploit/prf/generic lane details: Task 1 and Task 4.
  - Node-scoped candidate cards: Task 1, Task 4, and Task 6.
  - Expandable safe resume snapshots: Task 2 and Task 6.
  - Running notes business readability: Task 9.
  - Privacy boundaries: Task 2 and Task 10.
- Type consistency:
  - Backend `graphRelationships` maps to frontend `WorkbenchCandidateGraphRelationship[]`.
  - `laneType`, `queryRole`, `queryInstanceId`, and `queryFingerprint` use camelCase in API responses and frontend types.
  - Resume snapshot endpoint returns `WorkbenchCandidateResumeSnapshot`.
- Verification:
  - Backend: `uv run pytest tests/test_workbench_api.py tests/test_workbench_security_audit.py -q`.
  - Frontend: `cd apps/web && bun run test && bun run typecheck && bun run build`.
  - Diff: `git diff --check`.
