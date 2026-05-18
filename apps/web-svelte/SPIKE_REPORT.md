# Svelte 5 Frontend Spike Report

## Result

Status: pass

## What Was Proven

- `apps/web-svelte` builds as a SvelteKit + Svelte 5 TypeScript SPA/static app with `@sveltejs/adapter-static` fallback output.
- OpenAPI types are generated from the running FastAPI backend through `openapi-typescript` and formatted by `api:gen`.
- The typed frontend wrapper covers the spike subset: auth bootstrap/me/login/logout, session list/detail, candidate review queue, session events, graph candidates, and lazy resume snapshot.
- The first-login backend baseline works against an isolated live backend on port `8012`: bootstrap `201`, login `204`, `/api/auth/me` `200`, `/api/workbench/sessions` `200`, with both session and CSRF cookies present.
- The Svelte Workbench route renders a non-trivial business strategy graph using Svelte Flow, custom recruiter-facing nodes, keyboard selection, pointer selection, node drag, zoom, and pan.
- Selecting the final shortlist node triggers the graph-candidates query once. Selecting a graph candidate triggers the lazy resume-snapshot query once.
- The UI uses safe error display for backend errors. Playwright asserts raw artifact paths, auth headers, cookies, CSRF labels, and raw provider payload strings are not rendered.

## What Was Not Proven

- This is not a full React replacement. `apps/web` remains untouched.
- Settings/setup/source connection/Liepin login routes were intentionally not migrated.
- SSE/event streaming was not proven. The spike proves polling through Svelte Query.
- The UI graph test uses a mocked non-trivial Workbench fixture. The live backend smoke proves auth/session reachability, but the isolated backend had zero sessions.
- Production bundle optimization is not solved. The session detail route currently pulls a large Svelte Flow/ELK chunk.
- Advanced tables, rich text, drag-heavy editors, and production UI library choices were not evaluated.
- ELK layout timing was not measured in this spike; only the build chunk warning was captured.

## Migration Recommendation

Continue with bounded Svelte route-by-route migration while keeping `apps/web-svelte` isolated from `apps/web`. The next approved slice should migrate real login/session shell behavior and one real high-frequency read-only page against seeded backend data. Do not start full frontend replacement until the TODOs around seeded integration data, bundle splitting, schema drift checks, and UI component direction are handled.

## Evidence

- Final verification command:

```bash
bun run api:gen && bun run check && bun run lint && bun run test && bun run build && bun run test:e2e
```

- Final verification result:
  - `api:gen`: generated `src/lib/api/schema.d.ts` from `http://127.0.0.1:8012/openapi.json`.
  - `svelte-check`: `0 errors and 0 warnings`.
  - `lint`: passed.
  - `vitest`: `6` test files passed, `13` tests passed.
  - `build`: passed and wrote static output to `build`.
  - `test:e2e`: `2` tests passed.
- Targeted Workbench unit verification:
  - Command: `bun run test src/lib/workbench/runStory.test.ts src/lib/workbench/strategyGraphLayout.test.ts`
  - Result: `2` test files passed, `7` tests passed.
- Live backend smoke:
  - `bootstrap=201`
  - `login=204`
  - `me=200`
  - `sessions=200`
  - `csrf_cookie_lines=1`
  - `session_cookie_lines=1`
  - `me_email=admin@example.com`
  - `session_count=0`
- Playwright behavioral assertions:
  - `graph-candidates` endpoint call count: `1`.
  - `resume-snapshot` endpoint call count: `1`.
  - Security no-leak assertions cover `/private/artifacts/foo.json`, `X-CSRF-Token`, `cookie`, `raw_provider_payload`, and `Authorization`.
  - Node drag, zoom, pan, pointer selection, keyboard selection, and right-panel updates are asserted behaviorally, not only by screenshot.
  - Session events polling is asserted with at least two endpoint calls.
- Playwright screenshots:
  - `apps/web-svelte/test-results/workbench-spike-Svelte-Wor-4cf3f-es-and-lazy-resume-snapshot/desktop-graph-detail.png`
  - `apps/web-svelte/test-results/workbench-spike-Svelte-Wor-4cf3f-es-and-lazy-resume-snapshot/tablet-1024-graph-detail.png`
- Build warning to carry forward:
  - Session detail client route chunk `nodes/5.*.js`: `1,649.90 kB`, gzip `511.72 kB`.
  - Recommendation: split Svelte Flow and ELK with dynamic import, and move ELK layout to a worker if real graphs grow.
- ELK layout timing:
  - Not measured in this spike.
- Justified dirty-file deviation:
  - `TODOS.md` was updated to preserve deferred migration follow-ups from this spike: seeded live-backend fixture, Svelte Flow/ELK bundle splitting, OpenAPI drift checks, UI route selection, ESLint boundary rules, and polling-vs-SSE decision.

## Dev Mode BYOK Dual-Source Milestone

The Svelte app now covers dev-mode BYOK readiness, session creation, explicit CTS/Liepin source selection, requirement triage controls, source-run start, source status, unified Top 10 candidate queue, and Liepin detail recommendation visibility.

The backend contract for this milestone is not a frontend-only mock. It includes safe readiness diagnostics, blank-triage approval rejection, Runtime lane status propagation into Workbench source runs, source badge semantics, and an identity-level final Top 10 endpoint.

Verification added for this milestone:

- Python semantic gate: `SEEKTALENT_VERIFY_PYTHON_ONLY=1 ./scripts/verify-dev-workbench.sh`
- Svelte unit/component/API coverage: readiness display helpers, API wrappers, source-run controls, candidate queue, and component harness.
- Playwright dual-source milestone e2e: readiness, session creation, triage generation/approval, source start, degraded Liepin state, final Top 10 badges, detail recommendation posture, mobile overflow check, and no raw leak strings.

Known follow-ups remain: split Svelte Flow/ELK from the detail-route bundle, add the OpenAPI drift gate to CI, decide the production UI component route, and add seeded live-backend fixtures with non-trivial Workbench data.
