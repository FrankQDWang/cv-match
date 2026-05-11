# Workbench Node Detail Layout Design

## Purpose

The recruiter workbench should make the search process understandable to business users. The strategy graph is already a workflow projection: CTS uses `queue -> keywords -> recall -> scoring -> reflection`, and Liepin uses `queue -> card search -> candidate screening -> detail approval`. This design keeps that structure and fixes the surrounding interaction model so the graph, notes, candidate details, and JD brief work as one coherent business tool.

This spec focuses on UI and safe data contracts. It does not redesign the CTS runtime, Liepin worker, or multi-source execution policy.

## Current Code Facts

- `buildRunStory()` already creates CTS round nodes with `ctsRoundQuery`, `ctsRoundResults`, `ctsRoundScoring`, and `reflection`.
- CTS recall nodes currently carry counts such as `rawCandidateCount` and `uniqueNewCount`, but they do not carry per-round candidate ids.
- Liepin candidate nodes already carry `candidateReviewItemIds` and `candidateEvidenceRefs`.
- `NodeDetailPanel` renders structured node payloads, but does not yet render candidate cards or expandable full resume snapshots.
- `StrategyGraph` already uses `@xyflow/react` with ELK layout. React Flow is the right surface for panning, zooming, and node drag. Pretext is not the right tool for graph dragging.
- The current right rail is split vertically between running notes and candidate queue / node detail tabs. That wastes space and duplicates the graph interaction model.

## Decisions

### Layout

The workbench keeps the three-column shell:

1. Left session column.
2. Center strategy graph.
3. Right inspector column.

The left `岗位简报` becomes a fixed-height, collapsible card. In collapsed state it shows the job title, session status, source count, and a short JD preview. If notes exist, a notes preview is shown below the JD preview. Expanding the card displays the full JD and full notes inside the same left column, then the user can collapse it again.

The center strategy graph continues to show all selected sources by default. The graph-level source selector is removed. The graph is a session workflow, not a per-source filter UI.

The right inspector column becomes one full-height tabbed panel. It has only two compact icon tabs:

- `运行笔记`
- `节点详情`

`运行笔记` is the default. Clicking any strategy graph node selects the node and switches the right column to `节点详情`.

The standalone `候选人短名单` panel is removed. Candidates are displayed in node details for the workflow node that produced, scored, approved, or aggregated them.

### Strategy Graph Interaction

The existing `@xyflow/react` graph remains the interaction engine.

Initial layout continues to use ELK. The user can pan and zoom the full canvas. Nodes can be dragged locally to resolve overlap or temporarily organize a complex run. Dragged node positions are not persisted in this version; refresh returns to the automatic layout.

Pretext is not introduced for graph interaction. It remains reserved for future text-heavy candidate reports or final briefing surfaces if they need higher-quality responsive text layout.

### Multi-Round Layout

Multi-round agent iteration is shown as a round-by-round chain, not as a circular edge.

Each round starts again from the left side of the graph. `第 N 轮关键词` nodes are vertically stacked and left-aligned with the previous round's keyword node. This keeps a long run readable: the user scans down by round, then left-to-right inside a round.

Each round has its own horizontal row:

```text
第 1 轮关键词 -> exploit / explore -> 召回 -> 评分 -> 反思
第 2 轮关键词 -> exploit / explore -> 召回 -> 评分 -> 反思
第 3 轮关键词 -> exploit / explore -> 召回 -> 评分 -> 反思
```

`第 1 轮关键词` is derived from the requirement decomposition node. For `N > 1`, `第 N 轮关键词` has two inbound edges:

1. From `需求拆解`, labeled as the stable requirement context.
2. From `第 N-1 轮反思`, labeled as the reflection-driven adjustment.

This makes the graph explicit: every round still obeys the original job requirements, while the previous reflection changes the next search direction.

### CTS Internal Search Lanes

CTS round details must expose the real internal strategy rather than flattening the round into one keyword string.

Within each CTS round, the graph or node detail shows:

- `exploit`: the main narrowing query path.
- `explore`: the second-lane path when one exists.

The explore path has two possible sources:

- `prf_probe`: candidate-feedback/PRF-derived exploration when the PRF gate passes.
- `generic_explore`: fallback exploration when PRF is unavailable or rejected.

If the backend only ran a single-lane round, the UI must show a single-lane round explicitly and must not invent an explore lane. If both lanes ran, the round detail should show each lane's query terms, returned count, new candidate count, outcome, and related candidates.

### Candidate Mapping

CTS round nodes must become candidate-aware.

For CTS, per-round candidate mapping is required. `ctsRoundResults` should list candidates recalled or newly surfaced by that round. `ctsRoundScoring` should list candidates scored in that round, grouped or labeled by fit outcome where data exists.

The backend must expose safe per-round relationships rather than forcing the frontend to infer them. The minimum relationship shape is:

- `session_id`
- `source_run_id`
- `round_no`
- `query_instance_id`
- `query_fingerprint`
- `query_role`
- `lane_type`: `exploit`, `prf_probe`, `generic_explore`, or other backend-defined safe lane label
- `review_item_id`
- `evidence_id`
- `relationship_kind`: `recalled`, `new`, `scored`, `fit`, or `not_fit`

This can be stored directly or generated from persisted runtime artifacts, but the UI contract must be stable and scoped to tenant, workspace, user, and session.

The lane fields are required so the UI can show which candidates came from the main exploit path versus candidate-feedback exploration or generic exploration. The frontend must not guess lane membership from text labels.

Liepin keeps its existing candidate relationship model. `liepinCardCandidates`, `liepinCardSearch`, `liepinDetailApproval`, and final aggregation nodes use safe candidate ids and evidence refs.

### Full Resume Snapshots

Candidate cards in node details show safe summaries by default. Full resume content is loaded lazily only when the user expands an individual candidate card.

The UI uses this authenticated endpoint:

```http
GET /api/workbench/candidates/{review_item_id}/resume-snapshot
```

The endpoint returns a safe display model for the saved full resume snapshot. The model has optional structured sections for profile, work experience, education, projects, skills, and source evidence text. It must not return auth-bearing provider URLs, cookies, storage state, CDP URLs, or raw provider control payloads.

Full resume snapshots are allowed in authenticated UI detail views and benchmark storage. They are not allowed in:

- memory rows
- SSE business logs
- running-note payloads
- public artifacts
- frontend graph story payloads

### Node Details

`节点详情` renders by node type:

- `岗位`: job title, JD preview, notes preview, and source mode.
- `需求拆解`: must-haves, nice-to-haves, query hints, exclusions, and triage status.
- `第 N 轮关键词`: query terms, query label, search direction, and exploit/explore lane breakdown where available.
- `CTS 召回`: round recall counts plus this round's candidate cards.
- `CTS 评分`: scored candidate cards, fit/not-fit labels, score, and key reasons.
- `反思`: summary, rationale, and next direction.
- `猎聘简介抓取`: scanned card count, unique candidate count, and related candidates where available.
- `猎聘候选人初筛`: candidate cards, score, source badge, and AI screening reasons.
- `详情审批`: candidate cards with approval status, budget impact, and blocked reason if any.
- `最终短名单`: aggregated candidates with final score and source badges.

Candidate cards have a fixed collapsed height. Collapsed cards show:

- display name or safe masked name
- title, company, location
- source badges
- score and fit bucket
- short summary
- key matched must-haves, strengths, or risks

Expanding a card loads the full resume snapshot and renders it inside that card. The card can be collapsed again. A failed full-resume fetch shows a per-card error state and does not break the whole node detail panel.

### Running Notes

`运行笔记` is for business-readable narration, not technical logs.

The source selector is removed. Running notes always show all selected sources for the current session. Multi-source concurrency is handled by business grouping:

- Events are ordered by real time.
- Each entry has a CTS or Liepin badge when source-specific.
- Short bursts of same-source same-stage events are merged into one note.
- Raw event names are not shown by default.
- Clicking a note selects the related graph node and switches to node detail.

Example entries:

- `CTS 第 1 轮完成：搜到 14 人，9 人进入评分，1 人 fit。`
- `Liepin 正在串行抓取简介：已扫描 30 张，命中 5 位候选人。`
- `反思：Kafka 关键词过窄，下一轮放宽到实时数据平台。`

### Privacy And Security

All candidate and resume data remains tenant/workspace/user/session scoped.

The UI may display complete resume snapshots only after authenticated user action. Complete snapshots must not be included in durable event payloads, SSE streams, running notes, graph payloads, public artifacts, or memory. Logs and exception serializers must continue to use existing redaction boundaries.

Provider raw payloads remain out of normal business UI unless explicitly transformed into the safe resume snapshot display model.

## Testing Requirements

### Backend

- CTS per-round candidate mapping is persisted or generated with stable scoped ids.
- CTS round result node data can resolve only that round's candidates.
- CTS scoring node data can resolve only that round's scored candidates.
- Full resume snapshot endpoint enforces tenant, workspace, user, and session scope.
- Full resume snapshot endpoint does not expose provider auth data or raw control payloads.
- Full resume snapshot data does not appear in `session_events`, SSE responses, running-note payloads, or memory rows.

### Frontend Unit And Component Tests

- The right rail has exactly two tabs: running notes and node detail.
- The candidate queue panel is not rendered as a standalone bottom panel.
- Clicking a graph node switches to node detail.
- Clicking a running-note entry selects the related graph node.
- CTS recall and scoring nodes render related candidate cards from per-round refs.
- Candidate cards are collapsed by default and have fixed summary layout.
- Expanding a candidate card requests its full resume snapshot.
- Full resume snapshot fetch failure is localized to that card.
- The graph and running notes no longer render source filter controls.
- The job brief card is fixed-height when collapsed and shows full JD/notes when expanded.
- Multi-round layout left-aligns all `第 N 轮关键词` nodes.
- For `N > 1`, each round keyword node has two incoming business edges: one from `需求拆解` and one from the previous round's `反思`.
- CTS round details render exploit and explore lane data when both lanes exist.
- CTS single-lane rounds render as single-lane rounds and do not invent explore data.
- Candidate cards in CTS recall/scoring details can be grouped or labeled by `lane_type`.

### Visual And Interaction Smoke Tests

- Long JD text no longer stretches the left column indefinitely.
- Right rail content uses the full rail height for the selected tab.
- Strategy graph supports pan and zoom.
- Strategy graph nodes can be dragged locally.
- Dragging a node does not persist after page refresh.
- Business notes remain readable when CTS and Liepin emit events close together.
- A multi-round CTS run is readable without a long horizontal chain: each new round starts on the left and scans left-to-right within its own row.

## Non-Goals

- Persisting custom graph node positions.
- Turning every candidate into a top-level graph node.
- Replacing React Flow or ELK.
- Introducing Pretext for graph interaction.
- Adding a third right-rail candidate tab.
- Changing source execution semantics.
- Exposing provider raw payloads in normal UI.

## Acceptance Criteria

- A recruiter can keep the JD brief collapsed while working in the graph.
- The graph always shows the whole selected-source workflow by default.
- The right rail is a two-tab inspector, not a stacked log and queue layout.
- Clicking CTS recall or scoring nodes shows the candidates for that exact round.
- Multi-round CTS layout returns each next round to the left side, aligns keyword nodes, and shows both stable requirement and previous-reflection inputs for `N > 1`.
- CTS node details expose the real exploit / PRF exploration / generic exploration structure when backend data exists.
- Clicking Liepin candidate, detail approval, or final shortlist nodes shows related candidates.
- Candidate cards are compact by default and expandable for complete resume snapshots.
- Running notes tell a business-readable story across all selected sources without source filters.
- Complete resume data stays out of memory, events, running notes, graph payloads, and public artifacts.
