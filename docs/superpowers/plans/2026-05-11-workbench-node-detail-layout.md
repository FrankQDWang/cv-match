# Workbench Node Detail Layout Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` for this implementation. Use sub-agents only when the user explicitly requests the sub-agent-driven pattern for the execution turn. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the workbench strategy graph and right inspector reflect real backend CTS/Liepin workflow data for business users: agent-first criteria extraction, multi-round CTS rows, exploit/explore lane details, node-scoped candidate cards, safe expandable resume snapshots, interactive Liepin detail approval, business-readable `运行笔记`, and the existing lower `候选人队列` / `节点详情` inspector.

**Architecture:** Keep CTS runtime/flywheel/corpus as source of truth. Workbench adds only the minimum internal recoverable `source_run_id -> runtime_run_id` link, then exposes paginated safe graph-candidate and resume-snapshot projections with opaque candidate ids. Do not add Workbench shadow tables for graph relationships or resume snapshots. Frontend keeps `buildRunStory()` as the business graph projection and fetches node candidates lazily when a node is selected.

**Tech Stack:** Python 3.12, FastAPI, SQLite, Pydantic, Bun, Vite, React 19, TypeScript, TanStack Query, `@xyflow/react`, `elkjs`, Vitest, Testing Library, Pytest.

## Implementation Status

Status: implemented in the current worktree.

Implemented outcomes:

- CTS `source_run_id -> runtime_run_id` is persisted internally when runtime allocates `run_id`, with idempotent completion and repair support.
- Backend graph candidate and safe resume snapshot endpoints are in place with scoped, paginated, opaque ids and allowlisted output.
- Frontend graph-candidate and resume-snapshot queries use TanStack Query keys scoped by session/node/candidate and load data lazily.
- `buildRunStory()` consumes real split runtime events, tolerates duplicate/out-of-order replay, preserves lane metadata, and keeps raw runtime event names out of business notes.
- The strategy graph is an interactive React Flow surface with ELK/fallback layout, local node dragging, pan/zoom, keyboard selection, and CTS round rows.
- Later CTS rounds connect from both `需求拆解` and the previous `反思` node.
- Source selection happens at session creation and left source cards. The graph and running notes default to all selected sources and no longer expose Source/View filters.
- Node detail renders node-scoped candidates lazily; individual candidate cards expand safe resume snapshots only on demand.
- Liepin detail approval remains reachable from the global queue and the `详情审批` node detail.
- `docs/ui.md` has been updated with the current workbench flow.

Verification completed:

```bash
cd apps/web && bun run test
cd apps/web && bun run typecheck
cd apps/web && bun run build
uv run pytest tests/test_workbench_api.py -q
uv run pytest tests/test_workbench_api.py tests/test_workbench_security_audit.py -q
python -m compileall -q src/seektalent_ui src/seektalent/runtime src/seektalent/corpus src/seektalent/flywheel tests/test_workbench_api.py
git diff --check
```

Known note: `bun run build` passes with the existing Vite large-chunk warning for the frontend bundle.

---

## Scope Notes

- The current branch already contains React Flow/ELK work from `docs/superpowers/plans/2026-05-11-interactive-strategy-graph.md`.
- This plan does not change source execution semantics. Selected sources start through `POST /api/workbench/sessions/{session_id}/start`; CTS can run in parallel workers; Liepin remains protected by its worker, detail-open approval, and ledger.
- Source selection happens at session creation and is represented by left-column source cards. The graph and running notes do not expose source filters.
- Pretext is not used for graph interaction.
- Current worktree is dirty. Do not revert existing uncommitted changes unless the user explicitly asks.

## Worktree Hygiene

- [ ] Run `git status --short` before editing and record dirty files in the task notes.
- [ ] Do not run intermediate `git add` or `git commit` from this plan.
- [ ] Keep write scopes explicit when multiple workers are used.
- [ ] At the end, run `git status --short`, `git diff --check`, and the verification commands.
- [ ] Commit/merge only after user approval.

Known dirty files at review time:

- `apps/web/src/api.ts`
- `apps/web/src/app.test.tsx`
- `apps/web/src/app.tsx`
- `apps/web/src/styles.css`
- `src/seektalent/runtime/orchestrator.py`
- `src/seektalent_ui/runtime_bridge.py`
- `src/seektalent_ui/workbench_routes.py`
- `tests/test_workbench_api.py`

## File Structure

Backend:

- Modify: `src/seektalent_ui/models.py`
  - Add graph candidate and safe resume snapshot response models.
- Modify: `src/seektalent_ui/workbench_store.py`
  - Add internal `source_runs.runtime_run_id` migration, early persistence, and repair support.
  - Do not add `candidate_graph_relationships`.
  - Do not add `candidate_resume_snapshots`.
- Add: `src/seektalent_ui/workbench_candidate_graph.py`
  - Build scoped paginated `GraphCandidateSummary` rows from Workbench source runs, FlywheelStore, CorpusStore, review items, evidence, and detail requests.
  - Generate and verify opaque graph candidate ids.
- Add: `src/seektalent_ui/resume_snapshot_projection.py`
  - Build safe allowlisted resume snapshot projections from corpus/review state.
- Modify: `src/seektalent_ui/workbench_routes.py`
  - Add graph candidate and graph candidate snapshot endpoints.
  - Keep route functions thin.
- Modify: `src/seektalent/runtime/orchestrator.py`
  - Emit or expose runtime `run_id` when allocated so Workbench can attach it before completion.
- Modify: `src/seektalent_ui/runtime_bridge.py`
  - Attach CTS runtime `run_id` to the Workbench source run before completion.
- Test: `tests/test_workbench_api.py`
  - Cover runtime link, graph candidates, safe snapshots, detail approval continuity, and leakage boundaries.

Frontend:

- Modify: `apps/web/src/types.ts`
  - Add `GraphCandidateSummary`, graph candidate list response, and safe snapshot types.
- Modify: `apps/web/src/api.ts`
  - Add graph candidate and graph candidate snapshot client methods.
- Modify: `apps/web/src/recruiterAnimation.ts`
  - Add CTS lane detail payloads, node kind metadata, and detail payload fields.
- Modify: `apps/web/src/runStory.ts`
  - Aggregate real runtime progress events by round.
  - Build CTS multi-round rows and business notes.
  - Stop using candidate review items as recall-pool inputs.
- Modify: `apps/web/src/strategyGraphLayout.ts`
  - Use virtual content bounds and CTS round-row post-processing.
- Modify: `apps/web/src/StrategyGraph.tsx`
  - Enable pan/zoom and local node dragging.
- Modify: `apps/web/src/NodeDetailPanel.tsx`
  - Compose payload detail, graph candidate query, candidate cards, and approval panel.
- Add: `apps/web/src/NodeCandidateCard.tsx`
  - Render collapsed candidate summaries, safe snapshot expansion, and review-backed actions.
- Add: `apps/web/src/DetailApprovalPanel.tsx`
  - Render pending and historical Liepin detail approval cards with approve/reject.
- Add: `apps/web/src/JobBrief.tsx`
  - Render fixed-height collapsible JD/notes brief.
- Modify: `apps/web/src/app.tsx`
  - Keep shell/query orchestration only; keep the global candidate/detail queue as the default shortlist view and remove source filters.
- Modify: `apps/web/src/styles.css`
  - Layout and visual states for the revised workbench.
- Modify: `docs/ui.md`
  - Document the new graph/inspector behavior.

## Task 0: Confirm Current Baseline

- [ ] Run `git status --short`.
- [ ] Run the narrow current frontend tests if quick:

```bash
cd apps/web && bun run test src/runStory.test.ts src/strategyGraphLayout.test.ts
```

- [ ] Run the narrow current backend tests if quick:

```bash
uv run pytest tests/test_workbench_api.py -q
```

Expected: record current failures if any. Do not fix unrelated failures in this task.

## Task 1: Persist And Recover CTS Runtime Link

**Files:**

- Modify: `src/seektalent/runtime/orchestrator.py`
- Modify: `src/seektalent_ui/runtime_bridge.py`
- Modify: `src/seektalent_ui/workbench_store.py`
- Modify: `src/seektalent_ui/maintenance.py` if schema audit requires it.
- Test: `tests/test_workbench_api.py`

- [ ] Add a failing test: CTS source run stores `source_runs.runtime_run_id` when runtime allocates `run_id`, before completion persistence.
- [ ] Assert normal session/source card API responses do not include `runtimeRunId`, `runtime_run_id`, `runDir`, or `run_dir`.
- [ ] Add nullable `runtime_run_id TEXT` to `source_runs`.
- [ ] Add a small runtime-start callback or equivalent hook so `WorkflowRuntime` can expose `tracer.run_id` after `_start_corpus_run(...)` and `_start_flywheel_run(...)`.
- [ ] Add `WorkbenchStore.attach_source_run_runtime_run_id(...)` with tenant/workspace/user/source-run scope checks.
- [ ] Call the attach method from `runtime_bridge.py` as soon as the callback provides `run_id`.
- [ ] Keep completion persistence idempotent: if `complete_cts_source_run_with_candidate_results(...)` receives artifacts with the same `run_id`, it verifies or preserves the existing link.
- [ ] If completion receives a different `run_id`, fail explicitly; do not silently overwrite.
- [ ] Keep `run_dir` out of Workbench state and responses.
- [ ] Add a repair/backfill helper for source runs missing `runtime_run_id`; keep it scoped and safe to run repeatedly.
- [ ] Graph candidate reads return a recoverable empty response with reason `runtime_link_missing` when the link is unavailable and cannot be repaired.
- [ ] Run:

```bash
uv run pytest tests/test_workbench_api.py::test_cts_runtime_run_id_is_attached_before_completion_without_exposing_runtime_paths -q
uv run pytest tests/test_workbench_api.py::test_cts_runtime_link_repair_is_idempotent_for_missing_source_run_link -q
```

Expected: PASS.

## Task 2: Backend Graph Candidate Read Model

**Files:**

- Add: `src/seektalent_ui/workbench_candidate_graph.py`
- Modify: `src/seektalent_ui/models.py`
- Modify: `src/seektalent_ui/workbench_routes.py`
- Test: `tests/test_workbench_api.py`

- [ ] Add Pydantic models:
  - `WorkbenchGraphCandidateSummaryResponse`
  - `WorkbenchGraphCandidateListResponse`
- [ ] Add endpoint:

```http
GET /api/workbench/sessions/{session_id}/graph-candidates?node_id={node_id}&limit=50&cursor={cursor}
```

- [ ] Enforce default `limit=50` and backend maximum limit.
- [ ] Return `nextCursor`, `totalEstimate`, `truncated`, and `generatedAt`.
- [ ] Cursor values must be opaque and server-verifiable.
- [ ] Parse supported node ids:
  - `cts-round-{n}-result`
  - `cts-round-{n}-score`
  - `final-shortlist`
  - `liepin-card-search`
  - `liepin-card-candidates`
  - `liepin-detail-approval`
- [ ] Validate tenant/workspace/user/session scope before reading candidates.
- [ ] Build a structured `GraphNodeRef` after parsing `node_id`; do not pass raw string parsing throughout the read model.
- [ ] Node ids are UI descriptors, not authorization. Every read revalidates the resolved source run/session relationship.
- [ ] For CTS recall/scoring nodes:
  - Resolve selected session source run.
  - Read `source_runs.runtime_run_id`.
  - Query flywheel `query_resume_hits` and `run_queries`.
  - Join corpus documents/observations for safe display fields.
  - Return `GraphCandidateSummary` rows with opaque, non-forgeable `graphCandidateId`.
- [ ] For final nodes:
  - Read review-backed candidates from `candidate_review_items` and evidence.
- [ ] For Liepin nodes:
  - Use existing review/evidence/detail request state.
- [ ] Implement stable ordering:
  - CTS recall: round, lane, query order, provider rank, deterministic candidate key.
  - CTS scoring: fit bucket, score descending, deterministic candidate key.
  - final: final score descending, review status, deterministic candidate key.
  - Liepin approval: pending first, then updated time descending.
- [ ] `graphCandidateId` must not expose or encode raw `runtime_run_id`, resume document id, provider id, artifact id, filesystem path, provider key, or detail URL.
- [ ] Resolve snapshot candidates by verifying `graphCandidateId` against the scoped node candidate set or an HMAC/server-secret payload; do not trust client-constructed ids.
- [ ] Do not upsert recall-only candidates into `candidate_review_items`.
- [ ] Do not return full resume text or raw provider payload.
- [ ] All new routes use explicit FastAPI `response_model`.
- [ ] Add tests:
  - recall node returns all round hits for that round.
  - scoring node returns scored hits and fit/not-fit metadata.
  - single-lane CTS returns only that lane.
  - `prf_probe` and `generic_explore` lane labels survive.
  - another user cannot read graph candidates.
  - forged graph candidate id is rejected.
  - cross-session graph candidate id is rejected.
  - pagination returns stable pages with deterministic ordering.
  - response text does not include runtime ids, artifact paths, provider keys, cookies, authorization values, storage state, CDP, or WebSocket endpoints.
- [ ] Run:

```bash
uv run pytest tests/test_workbench_api.py::test_cts_graph_candidates_are_read_from_flywheel_for_round_nodes -q
uv run pytest tests/test_workbench_api.py::test_graph_candidate_ids_are_opaque_and_scoped_to_session_node -q
uv run pytest tests/test_workbench_api.py::test_graph_candidate_list_is_paginated_and_stably_ordered -q
```

Expected: PASS.

## Task 3: Safe Resume Snapshot Projection

**Files:**

- Add: `src/seektalent_ui/resume_snapshot_projection.py`
- Modify: `src/seektalent_ui/models.py`
- Modify: `src/seektalent_ui/workbench_routes.py`
- Test: `tests/test_workbench_api.py`

- [ ] Add Pydantic models:
  - `WorkbenchResumeSnapshotProfileResponse`
  - `WorkbenchGraphCandidateResumeSnapshotResponse`
- [ ] Add endpoint:

```http
GET /api/workbench/sessions/{session_id}/graph-candidates/{graph_candidate_id}/resume-snapshot
```

- [ ] Resolve `graphCandidateId` inside tenant/workspace/user/session/node scope.
- [ ] Verify the graph candidate id is still valid for a current candidate in the selected session.
- [ ] Return safe failure states for stale or missing candidates:
  - `snapshot_forbidden`
  - `snapshot_not_found`
  - `snapshot_redacted`
- [ ] Project from corpus/review state through an allowlist:
  - profile summary
  - work experience
  - education
  - projects
  - skills
  - safe source evidence text
- [ ] Do not add a Workbench snapshot table.
- [ ] Do not return cookies, auth headers, storage state, CDP/WebSocket values, provider account hashes, auth-bearing URLs, raw control payloads, `run_dir`, or artifact paths.
- [ ] Do not serialize internal runtime/corpus/store objects directly; construct response models field by field.
- [ ] Snapshot errors must not include raw provider payload, raw resume content, artifact paths, or exception reprs.
- [ ] Add leakage tests proving complete resume content does not enter:
  - `session_events`
  - event API/SSE payloads
  - running-note/story payloads
  - memory rows if present
  - ordinary logs and exception payloads
- [ ] Run:

```bash
uv run pytest tests/test_workbench_api.py::test_graph_candidate_resume_snapshot_is_scoped_and_allowlisted -q
uv run pytest tests/test_workbench_api.py::test_graph_candidate_resume_snapshot_errors_are_redacted -q
```

Expected: PASS.

## Task 4: Frontend API And Types

**Files:**

- Modify: `apps/web/src/types.ts`
- Modify: `apps/web/src/api.ts`
- Test: `apps/web/src/runStory.test.ts`

- [ ] Add frontend types matching backend models:
  - `GraphCandidateSummary`
  - `GraphCandidateListResponse`
  - `GraphCandidateResumeSnapshot`
- [ ] Include pagination fields in `GraphCandidateListResponse`: `nextCursor`, `totalEstimate`, `truncated`, `generatedAt`.
- [ ] Add API methods:

```ts
listGraphCandidates(
  sessionId: string,
  nodeId: string,
  options?: { limit?: number; cursor?: string | null; signal?: AbortSignal },
): Promise<GraphCandidateListResponse>;
getGraphCandidateResumeSnapshot(
  sessionId: string,
  graphCandidateId: string,
  options?: { signal?: AbortSignal },
): Promise<GraphCandidateResumeSnapshot>;
```

- [ ] Query keys must include session and graph candidate ids:

```ts
['workbench', 'session', sessionId, 'graph-candidates', nodeId]
['workbench', 'session', sessionId, 'graph-candidate-snapshot', graphCandidateId]
```

- [ ] Pass TanStack Query's `signal` into both API methods so node switches abort stale requests.
- [ ] Snapshot queries use `staleTime: 0`, short `gcTime`, `enabled: expanded`, and `retry: false`.
- [ ] Snapshot queries are removed on logout, workspace/session switch, and when the selected session changes.
- [ ] Do not add any persisted query cache for snapshots.
- [ ] Remove plan/test assumptions that all node candidates are `WorkbenchCandidateReviewItem`.
- [ ] Run:

```bash
cd apps/web && bun run typecheck
```

Expected: PASS.

## Task 5: Build Story From Real Runtime Events

**Files:**

- Modify: `apps/web/src/recruiterAnimation.ts`
- Modify: `apps/web/src/runStory.ts`
- Test: `apps/web/src/runStory.test.ts`

- [ ] Add failing tests with real split events:
  - `runtime_requirements_completed`
  - `runtime_search_completed`
  - `runtime_scoring_completed`
  - `runtime_round_completed`
  - `runtime_run_completed`
- [ ] Aggregate round summaries by `roundNo`.
- [ ] Search events provide executed queries, query terms, lane data, recall count, and unique-new count.
- [ ] Scoring events provide scored count, fit count, and not-fit count.
- [ ] Round/reflection events provide reflection summary, rationale, and next direction where available.
- [ ] Keep compatibility for legacy composite `runtime_round_completed`, but do not rely on it as the only source.
- [ ] Add CTS lane detail payloads driven by actual `laneType/queryRole/queryInstanceId/queryFingerprint`.
- [ ] Do not invent explore lanes.
- [ ] Use graph node ids and node metadata as lightweight descriptors only; do not put full candidate lists into story payloads.
- [ ] Story builder is idempotent under duplicate events.
- [ ] Story builder tolerates out-of-order events by grouping by round/source/lane and using stable event sequence fallback.
- [ ] Unknown event types appear only in the collapsed developer log, not business notes.
- [ ] Missing scoring events still leave recall/query nodes visible with recoverable empty scoring detail.
- [ ] Generate business notes as summaries, not one log per graph node.
- [ ] Run:

```bash
cd apps/web && bun run test src/runStory.test.ts
```

Expected: PASS.

## Task 5.5: Event Schema Versioning And Replay Safety

**Files:**

- Modify: `src/seektalent_ui/workbench_store.py`
- Modify: `src/seektalent_ui/job_runner.py`
- Modify: `apps/web/src/runStory.ts`
- Test: `tests/test_workbench_api.py`
- Test: `apps/web/src/runStory.test.ts`

- [ ] Add or preserve event metadata needed for replay:
  - `global_seq`
  - `session_seq`
  - `source_run_id`
  - `source_kind`
  - `event_name`
  - `schema_version`
  - `created_at` / occurred timestamp where available
  - idempotency key where producer can provide one
- [ ] Keep this migration backward compatible for existing `session_events`.
- [ ] Runtime progress events include enough source/run/round/lane metadata for deterministic story rebuild.
- [ ] Duplicate event payloads do not duplicate graph nodes, candidate counts, or running notes.
- [ ] Out-of-order split events still produce one coherent round row.
- [ ] Legacy composite `runtime_round_completed` plus split events does not double count the same round.
- [ ] Run:

```bash
uv run pytest tests/test_workbench_api.py::test_workbench_event_schema_supports_versioned_replay_metadata -q
cd apps/web && bun run test src/runStory.test.ts -t "replay"
```

Expected: PASS.

## Task 6: CTS Round Row Layout With Virtual Content Bounds

**Files:**

- Modify: `apps/web/src/strategyGraphLayout.ts`
- Modify: `apps/web/src/StrategyGraph.tsx`
- Test: `apps/web/src/strategyGraphLayout.test.ts`

- [ ] Add failing layout tests for 6+ CTS rounds.
- [ ] Post-process CTS round nodes into rows:
  - query/result/score/reflect stages have stable x positions.
  - each next round gets a stable y offset.
  - positions are not clamped to the viewport bottom.
- [ ] Use content bounds larger than viewport when rounds exceed visible height.
- [ ] Keep final/shared nodes readable with multi-source lanes.
- [ ] Enable local node dragging through React Flow.
- [ ] Keep dragged positions non-persistent.
- [ ] Memoize custom graph node and edge components.
- [ ] Layout recalculates only when the story signature or measured bounds changes.
- [ ] Dragging nodes does not rebuild `buildRunStory()`.
- [ ] Graph node components never receive candidate arrays or resume snapshot data.
- [ ] Keep React Flow keyboard accessibility enabled.
- [ ] Nodes can be selected with mouse and keyboard.
- [ ] Run:

```bash
cd apps/web && bun run test src/strategyGraphLayout.test.ts
cd apps/web && bun run test src/app.test.tsx -t "strategy graph keyboard"
```

Expected: PASS.

## Task 7: Agent-First Triage And Central Start

**Files:**

- Modify: `apps/web/src/app.tsx`
- Add/Modify: `apps/web/src/JobBrief.tsx`
- Modify: `apps/web/src/styles.css`
- Test: `apps/web/src/app.test.tsx`

- [ ] Empty triage renders readonly "agent will decompose JD" state, not blank textareas.
- [ ] Central graph button shows `启动 Agent`.
- [ ] Clicking `启动 Agent` calls `/triage/prepare` and does not call `/start`.
- [ ] Prepared triage renders an agent criteria review card.
- [ ] `确认并开始检索` calls approve then start.
- [ ] `修改` reveals textareas.
- [ ] Approved triage shows `启动检索`, which calls `/start`.
- [ ] Source cards do not render per-source start buttons.
- [ ] Remove graph and running-note source filter controls.
- [ ] Run:

```bash
cd apps/web && bun run test src/app.test.tsx -t "triage"
```

Expected: PASS.

## Task 8: Right Inspector And Node Candidate Cards

**Files:**

- Modify: `apps/web/src/NodeDetailPanel.tsx`
- Add: `apps/web/src/NodeCandidateCard.tsx`
- Modify: `apps/web/src/app.tsx`
- Modify: `apps/web/src/styles.css`
- Test: `apps/web/src/app.test.tsx`

- [ ] Keep `运行笔记` as the business narrative area above the lower inspector.
- [ ] Lower inspector has only `候选人队列` and `节点详情`.
- [ ] Keep the global `CandidateReviewQueue` as the default shortlist view; node-scoped candidates render inside `节点详情`.
- [ ] Do not fetch graph candidates for non-candidate workflow nodes such as job, requirements, source queue, query, or reflection.
- [ ] `NodeDetailPanel` props:

```ts
node: RecruiterGraphNode | null;
sessionId: string;
```

- [ ] When no node is selected, graph candidates are not fetched.
- [ ] When a node is selected, fetch graph candidates with a session/node-scoped query key.
- [ ] Fetch graph candidates with `limit`/`cursor`; load more within node detail instead of preloading all candidates.
- [ ] Render `totalEstimate`/`truncated` in recruiter-friendly language when available.
- [ ] Candidate cards are fixed-height and collapsed by default.
- [ ] Recall-only candidates are read-only except safe snapshot expansion when allowed.
- [ ] Review-backed candidates expose allowed actions based on backend capability flags.
- [ ] Expanding one card fetches only that card's safe snapshot.
- [ ] Switching nodes aborts stale graph candidate and snapshot requests through `AbortSignal`.
- [ ] Rendering also guards `response.nodeId === selectedNode.id` before displaying candidates.
- [ ] Candidate list virtualizes or window-renders when visible candidates exceed 50.
- [ ] Expanding/collapsing a snapshot does not rerender the graph.
- [ ] Snapshot error UI is per-card and does not render raw backend error payloads.
- [ ] Run:

```bash
cd apps/web && bun run test src/app.test.tsx -t "node detail"
cd apps/web && bun run test src/app.test.tsx -t "stale graph candidate response"
```

Expected: PASS.

## Task 9: Liepin Detail Approval In Node Detail

**Files:**

- Add: `apps/web/src/DetailApprovalPanel.tsx`
- Modify: `apps/web/src/NodeDetailPanel.tsx`
- Modify: `apps/web/src/app.tsx`
- Test: `apps/web/src/app.test.tsx`

- [ ] `详情审批` node shows pending and recent detail requests for the session/node.
- [ ] Pending request card shows candidate summary, AI reason, budget impact, mode, `批准打开`, and `暂不打开`.
- [ ] Approved/leased/opened cards show budget reservation and provider action.
- [ ] Rejected cards show no quota consumed.
- [ ] Blocked cards show blocked reason.
- [ ] Approve calls existing detail approve API.
- [ ] Reject calls existing detail reject API.
- [ ] Backend approve/reject endpoints remain authoritative; UI capability flags are display hints only.
- [ ] Preserve existing request status preconditions, CSRF protection, budget reservation, ledger append, external write intent, and audit events.
- [ ] Add or preserve regression coverage:
  - double approve consumes quota once.
  - approve after reject returns conflict.
  - reject after approve returns conflict.
  - blocked request cannot be approved.
  - another user cannot approve or reject.
  - ledger failure does not leave request falsely approved without a compensating state.
- [ ] Mutations invalidate:
  - detail requests
  - current node graph candidates
  - session
  - session list
- [ ] Confirm detail approval remains reachable from the global queue and relevant detail nodes.
- [ ] Pending approval count remains discoverable on the source card, running note, and `详情审批` graph node.
- [ ] Run:

```bash
cd apps/web && bun run test src/app.test.tsx -t "detail approval"
uv run pytest tests/test_workbench_api.py -k "detail_open and approve" -q
```

Expected: PASS.

## Task 10: Business Running Notes

**Files:**

- Modify: `apps/web/src/runStory.ts`
- Modify: `apps/web/src/app.tsx`
- Test: `apps/web/src/runStory.test.ts`
- Test: `apps/web/src/app.test.tsx`

- [ ] Running notes render all selected sources without source selector.
- [ ] Remove `slice(-10)` truncation from business notes; show full business history with normal panel scrolling.
- [ ] Developer raw event names appear only inside the collapsed developer log.
- [ ] Notes summarize business meaning and do not mirror every graph node.
- [ ] CTS same-round search/scoring/reflection can merge into one business summary when useful.
- [ ] Multi-source notes remain source-badged and time ordered.
- [ ] Parallel source events are grouped by timestamp/source without implying a false serial order.
- [ ] Human action required notes surface pending Liepin detail approvals.
- [ ] Clicking a note selects the most relevant graph node.
- [ ] Tests assert no default `runtime_`, `source_run_`, or `candidate_review_item_` text appears in business notes.
- [ ] Run:

```bash
cd apps/web && bun run test src/runStory.test.ts src/app.test.tsx -t "running note"
```

Expected: PASS.

## Task 11: Documentation Update

**Files:**

- Modify: `docs/ui.md`

- [ ] Update workbench docs:
  - agent-first triage
  - central session start
  - no graph/log source filters
  - two right inspector tabs
  - node-scoped candidates
  - safe snapshot expansion
  - detail approval inside node detail
  - graph candidate read model sourced from flywheel/corpus

## Task 12: Full Verification And Manual Smoke

- [ ] Run frontend tests:

```bash
cd apps/web && bun run test
```

- [ ] Run frontend typecheck:

```bash
cd apps/web && bun run typecheck
```

- [ ] Run frontend build:

```bash
cd apps/web && bun run build
```

- [ ] Run backend tests:

```bash
uv run pytest tests/test_workbench_api.py tests/test_workbench_security_audit.py -q
```

- [ ] Run focused hardening tests:

```bash
uv run pytest tests/test_workbench_api.py -k "runtime_run_id or graph_candidate or resume_snapshot or detail_open" -q
cd apps/web && bun run test src/runStory.test.ts src/app.test.tsx -t "replay|node detail|snapshot|detail approval|running note|keyboard"
```

- [ ] Run diff check:

```bash
git diff --check
```

- [ ] Manual browser smoke:

```bash
uv run seektalent-ui-api
cd apps/web && bun run dev --host 127.0.0.1 --port 5176
```

Open `http://127.0.0.1:5176/` in the in-app browser and verify:

1. Create a CTS-only session using a benchmark JD.
2. Click `启动 Agent`.
3. Agent extracts criteria first and does not start CTS yet.
4. Confirm criteria and start CTS.
5. Strategy graph shows requirements, CTS source queue, multi-round rows, recall/scoring/reflection, and final aggregation.
6. Round 2+ keyword nodes have edges from `需求拆解` and previous `反思`.
7. Clicking recall/scoring/final nodes opens `节点详情`.
8. Node candidates load lazily and match the selected node.
9. Node candidates paginate or truncate safely when a node has many candidates.
10. Expanding one card fetches safe resume snapshot.
11. Switching nodes rapidly does not show stale candidates or stale resume snapshots.
12. Detail approvals remain discoverable and actionable from the `详情审批` node.
13. Keyboard can select graph nodes and switch inspector tabs.
14. `运行笔记` is business-readable and does not show raw event names by default.
15. Graph and running notes have no source filter selectors.

## Self-Review Checklist

- [ ] No `candidate_graph_relationships` table was added.
- [ ] No `candidate_resume_snapshots` table was added.
- [ ] Recall pool candidates are not forced into `candidate_review_items`.
- [ ] `source_runs.runtime_run_id` is attached before completion, recoverable, and not exposed through ordinary responses.
- [ ] Graph candidate API is scoped by tenant/workspace/user/session/node.
- [ ] Graph candidate ids and cursors are opaque and server-verifiable.
- [ ] Graph candidate API is paginated and stably ordered.
- [ ] Snapshot API is graph-candidate scoped and allowlisted.
- [ ] Snapshot queries are short-lived, non-persisted, and cleared on logout/session/workspace switch.
- [ ] Full resume text does not leak into events, SSE, running notes, graph story payloads, memory, frontend persistent cache, errors, or logs.
- [ ] Right rail keeps business `运行笔记`; lower inspector has only `候选人队列` and `节点详情`.
- [ ] Detail approval remains interactive and discoverable from the candidate queue and relevant detail nodes.
- [ ] Detail approval mutations remain backend-authoritative, scoped, CSRF protected, idempotent, and quota safe.
- [ ] Event replay is idempotent under duplicate/out-of-order events.
- [ ] Running notes summarize business meaning rather than repeating graph nodes.
- [ ] Multi-round graph uses virtual content bounds and does not overlap after several rounds.
- [ ] Graph and node detail remain keyboard accessible.

## GSTACK REVIEW REPORT

### Review Summary

The original spec direction was valid, but the implementation plan was not safe to execute as written. It mixed design-state assumptions with backend reality and proposed Workbench-owned shadow tables that would have duplicated or distorted existing CTS runtime/flywheel/corpus truth.

### Accepted Decisions

1. Split backend safe contracts/read models from frontend rendering work.
2. Do not add Workbench-owned full-resume snapshot storage.
3. Do not copy all recalled candidates into `candidate_review_items`.
4. Migrate candidate actions into node detail before deleting standalone queue UI.
5. Scope every new data read by tenant, workspace, user, and session.
6. Split focused modules instead of growing `app.tsx` and `workbench_store.py`.
7. Use virtual graph content bounds for multi-round layout.
8. Build safe resume snapshots from corpus allowlist projection.
9. Test that full resume content does not leak into events, SSE, notes, graph payloads, or memory.
10. Running notes should be full business history, not a truncated technical log.
11. Keep agent-first triage: prepare criteria before start, with human confirm by default.
12. Remove per-task commits and use dirty-worktree hygiene.
13. Reuse `query_resume_hits`, `run_queries`, corpus documents/observations, review items, and evidence.
14. Persist an internal `source_run_id -> runtime_run_id` link.
15. Aggregate real split runtime events, not only idealized `runtime_round_completed`.
16. Replace review-item snapshot endpoint with graph-candidate scoped snapshot endpoint.
17. Use `GraphCandidateSummary` instead of `WorkbenchCandidateReviewItem` for all node candidates.
18. Lazy-load node candidates by selected node.
19. Keep Liepin detail approval interactive inside node detail.
20. Use lane-driven CTS display and do not invent exploit/explore branches.
21. Make running notes a business narrative layer distinct from graph structure.
22. Use realistic backend/read-model tests against flywheel/corpus contracts.
23. Attach `runtime_run_id` before completion and provide a repair/backfill path.
24. Use opaque graph candidate ids and cursors.
25. Paginate and stably sort graph candidate lists.
26. Keep resume snapshots out of frontend persisted caches and error payloads.
27. Make event replay duplicate/out-of-order tolerant.
28. Keep detail approval discoverable after queue removal.
29. Preserve React Flow performance and keyboard accessibility.

### Required Plan Changes Applied

- Removed `candidate_graph_relationships` and `candidate_resume_snapshots` from the plan.
- Added `source_runs.runtime_run_id` as the only new required persistence for CTS graph reads.
- Changed runtime link persistence from completion-only to early attach plus repair/backfill.
- Added `workbench_candidate_graph.py` and `resume_snapshot_projection.py` as focused backend modules.
- Added `NodeCandidateCard.tsx`, `DetailApprovalPanel.tsx`, and `JobBrief.tsx` as focused frontend modules.
- Replaced review-item based snapshot contract with session graph-candidate snapshot contract.
- Added opaque graph candidate ids, opaque cursors, pagination, stable ordering, and response-model constraints.
- Added snapshot cache hardening and stale-response guards for rapid node switching.
- Added event replay/idempotency and unknown-event handling requirements.
- Added detail approval transaction/discoverability requirements for both global queue and contextual detail nodes.
- Added React Flow performance and keyboard accessibility requirements.
- Replaced full candidate preload with selected-node lazy graph candidate loading.
- Reworked testing around real split runtime events and flywheel/corpus read models.
- Removed all intermediate `git add` and `git commit` steps.

### Residual Risks

- The graph candidate read model depends on reliable `runtime_run_id` persistence. The updated plan requires early attach and repair/backfill, but implementation must still prove crash/retry behavior.
- Opaque graph candidate ids should stay simple. Prefer HMAC/server-verifiable tokens or scoped recomputation over a new durable mapping table unless implementation proves a table is necessary.
- Corpus/flywheel store access from `seektalent_ui` must stay bounded and direct; avoid turning Workbench into a second artifact index.
- Large CTS runs can stress graph, candidate pagination, and snapshot cache behavior; large-run smoke is required before merge.
- UI smoke must be run with a real CTS-only session after implementation because mock event tests cannot fully prove end-to-end runtime alignment.
