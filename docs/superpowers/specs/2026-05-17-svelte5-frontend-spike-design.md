# Svelte 5 Frontend Migration Spike Design

## Summary

SeekTalent should validate a Svelte 5 frontend before committing to a full React replacement.

The current frontend is small enough to rebuild, but it is not a plain CRUD app. It has a recruiter workbench shell, authenticated Workbench APIs, event polling/streaming, graph-candidate read models, lazy resume snapshots, detail approval flows, and an interactive strategy graph currently backed by React Flow and ELK. A migration that only proves login and list pages would miss the highest-risk part.

This spec defines a bounded spike:

1. Create a new SvelteKit + Svelte 5 app beside the existing React app.
2. Consume the existing FastAPI Workbench API through generated OpenAPI TypeScript types.
3. Rebuild the minimum authenticated Workbench path.
4. Prove that `@xyflow/svelte` plus the existing ELK layout logic can support the current strategy graph interaction, graph-candidate loading, and lazy resume snapshots.
5. Verify the spike against the live backend contract where it matters, not only mocked UI routes.
6. Keep the existing `apps/web` React app unchanged until the spike passes.

This is not the full migration plan. If the spike passes review, a later spec/plan should cover route-by-route replacement.

## Product Direction

Use Svelte 5 because this product is AI-coded and the current frontend has high boilerplate-to-product-value ratio. The intended win is not framework novelty. The intended win is a frontend structure that is easier for Codex to read, modify, and verify:

- file-based routes instead of a large hand-built router tree
- smaller `.svelte` components instead of a single large `app.tsx`
- generated API types instead of handwritten endpoint and response shapes
- Svelte 5 runes for local UI state
- TanStack Svelte Query for server state
- Playwright coverage for real recruiter-visible behavior
- Svelte MCP/autofixer guidance for framework-specific syntax

## Current Code Facts

- Existing frontend app: `apps/web`.
- Existing frontend stack: Bun, Vite, React 19, TanStack React Query, TanStack React Router, `@xyflow/react`, `elkjs`, Vitest, Testing Library, Playwright.
- Existing frontend source shape:
  - `apps/web/src/app.tsx` owns router construction, query orchestration, shell pages, login/setup, sessions, settings, Liepin login, and much of the workbench page.
  - `apps/web/src/api.ts` owns a handwritten `WorkbenchApi` wrapper with cookie credentials and CSRF retry behavior.
  - `apps/web/src/types.ts` owns handwritten TypeScript API response types.
  - `apps/web/src/runStory.ts`, `recruiterAnimation.ts`, and `strategyGraphLayout.ts` are mostly framework-independent business projection/layout modules.
  - `apps/web/src/StrategyGraph.tsx` owns the React Flow surface.
  - `apps/web/tests/visual/workbench.visual.spec.ts` already verifies visual workbench behavior through Playwright.
- Existing app routes:
  - `/` redirects to `/sessions`
  - `/setup`
  - `/login`
  - `/sessions`
  - `/sessions/$sessionId`
  - `/settings`
  - `/settings/sources`
  - `/settings/sources/liepin`
  - `/connections/liepin/$connectionId/login`
- Existing backend API stack:
  - `src/seektalent_ui/server.py` creates a FastAPI app.
  - `src/seektalent_ui/workbench_routes.py` declares `/api/auth/*` and `/api/workbench/*` routes with Pydantic `response_model` values.
  - `src/seektalent_ui/event_routes.py` declares Workbench event list and SSE stream routes.
  - FastAPI already exposes `/openapi.json` when the backend is running.
- Current checkout is dirty with active Liepin/runtime changes. The frontend spike must not edit those backend files.

## External References

The spike should follow these current upstream docs:

- Svelte CLI `sv create`, `sv add`, and `sv check`: https://svelte.dev/docs/cli/sv-create
- Svelte 5 runes: https://svelte.dev/docs/svelte/what-are-runes
- SvelteKit SPA/static fallback: https://svelte.dev/docs/kit/single-page-apps
- Svelte MCP addon: https://svelte.dev/docs/cli/mcp
- TanStack Svelte Query: https://tanstack.com/query/latest/docs/framework/svelte
- openapi-fetch and openapi-typescript: https://openapi-ts.dev/openapi-fetch/
- Svelte Flow: https://svelteflow.dev/
- shadcn-svelte and Bits UI: https://www.shadcn-svelte.com/docs and https://next.bits-ui.com/docs/migration-guide

## Target Spike Stack

- Framework: SvelteKit + Svelte 5
- Rendering mode: SPA/static for the Workbench app
- Language: TypeScript strict, with `noUncheckedIndexedAccess`
- Package manager: Bun
- API contract: `openapi-typescript` + `openapi-fetch`
- Server state: `@tanstack/svelte-query`
- Graph: `@xyflow/svelte` + existing `elkjs` layout concepts
- Styling: Tailwind CSS
- UI primitives: shadcn-svelte/Bits UI only if the spike needs dialog/dropdown/alert primitives; otherwise local components first
- Tests: Vitest, svelte-check, Playwright
- AI support: Svelte MCP config and `apps/web-svelte/AGENTS.md`

Do not introduce TanStack Router in the Svelte app. SvelteKit owns routing.

Do not introduce a SvelteKit server/BFF in the spike. The Python FastAPI backend remains the API boundary.

## Architecture

Create a new sibling app:

```text
apps/web/          # existing React app, unchanged during spike
apps/web-svelte/   # new SvelteKit spike app
```

The new frontend consumes backend data through this flow:

```text
FastAPI response_model
  -> /openapi.json
  -> openapi-typescript generated schema
  -> openapi-fetch typed client
  -> src/lib/api/workbench.ts query functions
  -> Svelte Query reactive query objects
  -> route/page components
```

Components must not call raw `fetch` directly. All Workbench API calls go through `src/lib/api`.

The full Svelte migration may eventually use this route shape:

```text
src/routes/+layout.svelte
src/routes/+layout.ts
src/routes/+error.svelte
src/routes/+page.ts
src/routes/(auth)/login/+page.svelte
src/routes/(auth)/setup/+page.svelte
src/routes/(app)/+layout.svelte
src/routes/(app)/sessions/+page.svelte
src/routes/(app)/sessions/[sessionId]/+page.svelte
src/routes/(app)/settings/+page.svelte
src/routes/(app)/settings/sources/+page.svelte
src/routes/(app)/settings/sources/liepin/+page.svelte
src/routes/(app)/connections/liepin/[connectionId]/login/+page.svelte
```

This spike creates only:

```text
src/routes/+layout.svelte
src/routes/+layout.ts
src/routes/+error.svelte
src/routes/+page.ts
src/routes/(auth)/login/+page.svelte
src/routes/(app)/+layout.svelte
src/routes/(app)/sessions/+page.svelte
src/routes/(app)/sessions/[sessionId]/+page.svelte
```

Do not create `/setup`, `/settings`, source connection, or provider login routes in this spike unless a separate plan explicitly approves them.

Use `load` only for route-level redirects and tiny bootstrap state. Use Svelte Query for Workbench server state that needs refresh, mutation, invalidation, pagination, or optimistic UI.

## State Model

Spike server state:

- current user
- sessions
- selected session
- candidate review queue
- graph candidates
- resume snapshots
- event list / event polling

Use `@tanstack/svelte-query`.

Later migration server state:

- source connections
- detail open requests and approval flows
- Workbench settings
- setup/settings/source login routes
- SSE/streaming event adapters

Local UI state:

- selected graph node
- right inspector tab
- expanded candidate card
- local form draft
- local graph node positions for the current view

Use Svelte 5 `$state` or `$state.raw` when deep reactivity would be wasteful. Svelte Flow's own docs recommend `$state.raw` for nodes and edges for performance.

Derived UI state:

- selected node detail payload
- button enabled/disabled state
- session status labels
- empty-state labels

Use `$derived`.

Side effects:

- query invalidation after mutations
- event polling timer if SSE is not used in this spike
- browser navigation after login/logout

Use Svelte Query mutation callbacks or narrow `$effect` blocks. Do not fetch data directly inside broad `$effect` blocks.

## API Contract

The spike must stop adding handwritten API response types to `src/types.ts` style files. The generated schema is source-derived from FastAPI OpenAPI.

The generated schema may include all backend paths. For this bounded spike, the public frontend API wrapper must expose only the minimum validated Workbench subset:

- `/api/auth/bootstrap`
- `/api/auth/login`
- `/api/auth/logout`
- `/api/auth/me`
- `/api/workbench/sessions`
- `/api/workbench/sessions/{session_id}`
- `/api/workbench/sessions/{session_id}/candidates`
- `/api/workbench/sessions/{session_id}/events`
- `/api/workbench/sessions/{session_id}/graph-candidates`
- `/api/workbench/sessions/{session_id}/graph-candidates/{graph_candidate_id}/resume-snapshot`

`/api/auth/bootstrap` is included for setup and live-backend smoke validation. It is not a prerequisite for every login attempt unless the backend contract changes.

These existing Workbench paths are allowed for later migration but are not required by this spike:

- `/api/workbench/settings`
- `/api/workbench/source-connections`
- `/api/workbench/source-connections/liepin`
- `/api/workbench/source-connections/{connection_id}`
- `/api/workbench/source-connections/{connection_id}/login`
- `/api/workbench/source-connections/{connection_id}/login/frame`
- `/api/workbench/source-connections/{connection_id}/login/snapshot`
- `/api/workbench/source-connections/{connection_id}/login/input`
- `/api/workbench/source-connections/{connection_id}/login/complete`
- `/api/workbench/detail-open-requests`
- `/api/workbench/detail-open-requests/{request_id}/approve`
- `/api/workbench/detail-open-requests/{request_id}/reject`
- `/api/workbench/sessions/{session_id}/triage`
- `/api/workbench/sessions/{session_id}/triage/prepare`
- `/api/workbench/sessions/{session_id}/triage/approve`
- `/api/workbench/sessions/{session_id}/start`
- `/api/workbench/sessions/{session_id}/source-runs/liepin/policy`
- `/api/workbench/events`

The spike proves polling-based session refresh only, with a behavioral test that the session-events endpoint refetches after initial load. SSE/streaming is a later migration task.

Cookie credentials and CSRF behavior must match the existing React client:

- every request sends `credentials: "include"`
- mutating requests attach `X-CSRF-Token` when available
- response `X-CSRF-Token` refreshes the client-held token
- a mutating `403` with an existing CSRF token refreshes `/api/auth/me` once, then retries once

## Graph Spike Requirement

The strategy graph is the critical migration risk.

The spike must rebuild a Svelte version of:

- `buildRunStory()` consumption
- ELK/fallback layout consumption
- node selection
- node dragging with local positions
- pan/zoom
- keyboard-reachable node selection
- right-side node detail update
- graph-candidate loading from selected graph context
- lazy resume snapshot loading from selected graph candidate context
- sanitized resume snapshot rendering without raw provider payloads or artifact paths
- Playwright screenshot artifact coverage at desktop and 1024px widths
- behavioral drag, zoom, and pan assertions; screenshots are evidence, not the only proof

Do not migrate the full workbench before this graph proof exists.

## AI Coding Guardrails

Create `apps/web-svelte/AGENTS.md` with frontend-specific rules:

- Use Svelte 5 runes in new code.
- Do not use React patterns.
- Do not use legacy Svelte syntax in new files unless explicitly justified.
- Use SvelteKit file-based routing.
- Use `src/lib/api` for all API calls.
- Use central query key helpers; do not invent ad hoc query keys in pages.
- Do not display raw backend error detail in UI.
- Do not edit generated OpenAPI files manually.
- Use Svelte Query for server state.
- Use the current Svelte Query reactive object API, such as `query.isPending` and `query.data`; do not write legacy `$query` store syntax unless the installed package documentation for that exact version requires it.
- Every page must handle loading, error, empty, and permission states.
- Run `bun run check`, `bun run lint`, `bun run test`, and `bun run test:e2e` before finishing frontend work.

Document the existing Codex Svelte plugin in this file. Do not add Svelte MCP setup with `sv add mcp` during the spike unless a later task explicitly approves local MCP files and uses a fully non-interactive command with all required options set.

## Non-Goals

This spike does not:

- delete `apps/web`
- replace the production frontend entrypoint
- migrate every page
- redesign the Workbench product UI
- change Python backend routes or response models except if a missing OpenAPI contract bug is discovered and separately approved
- touch Liepin runtime, Pi executor, provider registry, source-lane implementation, or current uncommitted runtime plans
- add SSR/BFF/server actions
- add a generic component library mix
- solve all table/form/detail approval UX
- implement full `/setup`, `/settings`, source connection, and provider login routes
- implement detail approval flows
- implement SSE/streaming reconnect and backoff behavior
- publish, merge, release, or deploy

## Acceptance Criteria

The spike is successful only if all are true:

1. `apps/web-svelte` builds as a SvelteKit + Svelte 5 TypeScript SPA/static app.
2. `bun run api:gen` generates OpenAPI types from the running FastAPI backend.
3. Typed API wrapper covers auth bootstrap/me/login/logout, session list/detail, candidate review queue, session events, graph candidates, and resume snapshots, with local Workbench aliases derived from generated OpenAPI schema types instead of copied handwritten React types.
4. Live-backend smoke validates bootstrap/login/me/session-list against the existing backend using isolated local test state. If test state or credentials are unavailable, the spike is blocked rather than silently downgraded to mocked UI only.
5. A real session detail route renders a non-trivial strategy graph using Svelte Flow and existing run-story/layout concepts.
6. The graph uses custom business-facing nodes, not default label-only nodes.
7. Pointer selection and keyboard selection update the right detail panel.
8. Node drag, zoom, and pan have behavioral assertions, not only screenshots.
9. Selecting a graph/candidate context triggers graph-candidates loading.
10. Selecting or expanding a graph candidate triggers lazy resume snapshot loading.
11. The resume snapshot panel renders sanitized summary information without raw provider payloads.
12. Session event polling refetches after initial load.
13. No raw provider payloads, raw artifact paths, cookies, tokens, CSRF headers, or auth headers are rendered or persisted; this is covered by tests.
14. `bun run check`, `bun run lint`, `bun run test`, `bun run build`, and `bun run test:e2e` pass in `apps/web-svelte`.
15. The old `apps/web` app remains untouched and usable.

If the graph spike fails because Svelte Flow cannot support the required interaction quality without disproportionate custom work, stop and report. Do not continue into full migration.

## Follow-Up Decision After Spike

After the spike, run `fw-plan-review`. If approved and the spike passes, the next planning step should choose one of:

1. Continue Svelte migration route by route.
2. Keep React and instead refactor the current frontend around generated OpenAPI types and smaller React modules.
3. Keep both temporarily, with Svelte only for a new Workbench surface.

The decision should be based on live evidence from the spike, not framework preference.
