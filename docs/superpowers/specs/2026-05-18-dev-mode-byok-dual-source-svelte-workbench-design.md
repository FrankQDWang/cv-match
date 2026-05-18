# Dev Mode BYOK Dual-Source Svelte Workbench Design

## Product Goal

Build the first user-usable local milestone of SeekTalent: a dev-mode BYOK local recruiter workbench with a Svelte UI, CTS plus Liepin dual-source sourcing, Pi-backed Liepin browser execution, safe source status, and a final unified Top 10 candidate experience.

This milestone is not a broad rewrite. It is the product slice that should be demoable to a real user before the next one-week-plus architecture refactor.

## Current Repo Truth

The repo already has these foundations:

- Local-first product framing in CLI/docs and `seektalent inspect --json`.
- Runtime source-lane contracts for CTS and Liepin, including source plans, source evidence, identity-aware merge, coverage, and finalization revisions.
- Liepin card policy that preserves provider rank first and filters obvious mismatches before detail recommendation budget is spent.
- Pi-first Liepin executor mode through `SEEKTALENT_LIEPIN_WORKER_MODE=pi_agent`, with Pi RPC, strict JSON, payload firewall, Runtime-owned hashes, and DokoBot expected inside Pi.
- A Svelte 5 spike under `apps/web-svelte` proving typed OpenAPI access, login/session list/detail, Svelte Query, Svelte Flow graph rendering, graph-candidate loading, and lazy resume snapshot loading.
- Existing Workbench API routes for session creation, triage prepare/approve, source-run start, source connections, Liepin policy, candidates, graph candidates, session events, and resume snapshots.

The current user-facing gap is that the Svelte UI is still a read-heavy spike. It does not yet provide the full flow a recruiter needs to create a search, confirm requirements, choose CTS/Liepin, verify dev-mode readiness, run sources, monitor source progress, inspect recommendations, and consume the final Top 10.

## Target User Journey

1. A dev user starts the local backend and Svelte UI with BYOK credentials configured in local environment files.
2. The Svelte UI shows a safe readiness panel:
   - text LLM credential configured or missing;
   - CTS credential configured or missing;
   - Liepin worker mode and Pi/DokoBot readiness posture;
   - local data-root warning posture;
   - no API keys, tokens, cookies, session ids, raw provider payloads, or protected artifact paths.
3. The user creates a new sourcing session from Svelte:
   - job title;
   - JD text;
   - notes;
   - source selection with CTS and Liepin enabled by default when available;
   - source selection remains explicit and visible.
4. The user prepares and reviews requirement triage:
   - generated must-haves, nice-to-haves, synonyms, filters, exclusions, and query hints are visible;
   - the visible triage panel is the approval surface; the user must not approve a blank or hidden criteria set;
   - the user can approve the triage from Svelte;
   - running without approval is blocked with a clear UI state.
5. The user starts the selected sources:
   - CTS and Liepin source runs are queued together where selected;
   - CTS can complete even if Liepin is blocked;
   - Liepin shows connected, login-required, Pi unavailable, DokoBot unavailable, budget-limited, blocked, partial, or completed states without raw provider details.
6. The Workbench updates while the run progresses:
   - source status cards;
   - strategy graph with CTS and Liepin branches;
   - notes and events;
   - candidate queue;
   - detail recommendation counts and budget posture.
7. The final view shows a unified Top 10:
   - merged across CTS and Liepin identities;
   - duplicate/same-person evidence is preserved;
   - canonical resume selection prefers the newest or richest safe evidence when available;
   - source badges explain whether a candidate came from CTS, Liepin card, Liepin detail, or multiple sources;
   - coverage says when the final result is complete, degraded, partial, or CTS-only because Liepin was blocked.

## Backend Semantic Contract

The Svelte milestone must not paper over inconsistent backend state. Before the UI work is considered complete, the backend must guarantee these semantics:

- Runtime lane status drives source display semantics. A blocked Liepin lane must not look completed in the Workbench; partial Liepin results must remain visibly partial even if the source-run job itself has finished.
- Requirement triage approval is enforced server-side. A blank triage cannot be approved through the API even if a client bypasses the Svelte disabled state.
- The final Top 10 UI consumes a backend identity-level final-candidate contract, not a frontend `slice(0, 10)` over source-specific review items.
- Source badges are semantically explicit: CTS, Liepin card, Liepin detail, and multiple-source evidence must be distinguishable without inspecting raw payloads.
- Dev-mode readiness has an environment diagnostic path that can report incomplete `pi_agent` configuration even when strict `AppSettings` construction would otherwise fail before the server starts.
- User-visible source-state explanations use safe business labels. Internal reason codes may be retained in payloads for deterministic UI mapping, but raw provider errors and raw code strings are not shown as primary copy.

## Dev Mode BYOK Contract

Dev mode BYOK means the local developer or pilot user provides local credentials and local tools:

- `SEEKTALENT_TEXT_LLM_API_KEY` for active text LLM calls.
- CTS tenant credentials for real CTS source runs.
- `SEEKTALENT_LIEPIN_WORKER_MODE=pi_agent` plus Pi command, Pi skill path, DokoBot tool name, and a non-placeholder account binding secret for live Liepin browser source runs.
- The user is expected to already be logged into Liepin in the local browser session used by Pi/DokoBot.

The milestone must not implement platform-managed key custody, entitlement leases, billing, or account control-plane integration. Those remain a later productization phase.

The BYOK readiness surface must be diagnostic, not a secret viewer. It may say a credential is present, missing, invalid configuration, or not checked. It must never display actual secret values or derivable token material.

## Svelte UI Contract

The Svelte app becomes the primary dev-mode trial surface for this milestone. The existing React app remains available but should not receive new user-facing milestone work unless needed for backend parity tests.

The Svelte UI must be:

- business-facing, not a debug console;
- dense enough for recruiter workflows;
- visually polished enough for a pilot user;
- responsive on desktop and tablet widths;
- safe by construction: no raw backend errors, raw artifact paths, cookies, CSRF headers, auth headers, provider payloads, or protected snapshots rendered in visible UI.

The UI should avoid decorative landing-page patterns. The first screen after login is a practical workbench surface: readiness, session creation, session list, and recent runs.

Implementation must include the CSS/layout work required for this milestone's new panels. New components must be styled in the Svelte app's shared layout surface, with explicit desktop and tablet/mobile behavior, stable button/control dimensions, safe wrapping for long labels, and no overlapping primary controls.

## Dual-Source Runtime Contract

The milestone uses the existing Runtime as the execution and merge owner:

- Runtime owns source selection normalization, source plans, source-lane lifecycle, merge, scoring, finalization, source coverage, and Top 10.
- Workbench owns UI state, persistence, source-run jobs, approval/lease state, and display.
- Pi owns bounded provider execution for Liepin only.
- DokoBot is used inside Pi, not directly by Workbench or Runtime.

CTS and Liepin should run as selected source lanes and be displayed as peer branches. One source failing or blocking must not erase the other source's candidates. The final result may be degraded but must be honest.

## Liepin Card And Detail Contract

Liepin first collects cards. Card ranking is provider-rank-first:

- keep the search engine's order as the primary priority;
- reject only obvious mismatches using safe card fields;
- recommend details within a deterministic budget;
- preserve partial cards if timeout or risk blocking happens after valid card collection;
- do not open details from card-search mode unless a separate approved detail lease exists.

For this milestone, full manual detail approval UI can remain shallow if the runtime recommendation boundary is visible and safe. The UI must not hide detail recommendations in ad hoc payloads.

## Usability Acceptance Criteria

The milestone is complete only if all are true:

1. A dev user can run the Svelte UI and backend locally.
2. The Svelte UI can create a new session with CTS and Liepin selected.
3. The Svelte UI can prepare and approve requirement triage.
4. The Svelte UI can start the selected sources.
5. CTS can run and produce candidates in the same Svelte flow.
6. Liepin can enter a clear connected/login-required/blocked/partial/completed state in the same Svelte flow.
7. When Liepin is configured for `pi_agent`, the UI and backend preserve the Pi/DokoBot boundary and do not reintroduce old `dokobot_action` or direct browser fallback paths.
8. The strategy graph shows separate CTS and Liepin branches when both are selected.
9. Candidate queue and graph-candidate views show source badges and source evidence without raw protected payloads.
10. Final results are identity-level Top 10, not a naive concatenation of CTS and Liepin lists.
11. Coverage state is visible when one source is blocked or partial.
12. BYOK readiness shows actionable missing-config states without secret values.
13. The backend rejects blank triage approval, preserves blocked/partial source semantics before the Svelte UI starts source runs, and can start in a safe degraded dev-mode state to display invalid `pi_agent` setup.
14. The Svelte UI passes unit, build, and e2e checks.
15. The milestone verification command proves Python focused tests, Svelte checks, OpenAPI type generation/drift checks, no-leak assertions, and a narrow static check that the Svelte milestone does not call old Liepin browser fallback paths.

## Non-Goals

- No hosted SaaS experience.
- No platform-managed entitlement or key custody implementation.
- No production packaging installer.
- No cloud deployment migration.
- No Storybook catalog unless a narrow story is needed for this milestone's visual review.
- No A2A protocol.
- No generic provider plugin marketplace.
- No broad Runtime API redesign.
- No full React-to-Svelte replacement.
- No manual recruiter card-review UI beyond the minimal visible recommendation/budget boundary needed for this milestone.

## Deferred After This Milestone

The next phase can be a one-week-plus refactor once the dev-mode product path is usable. Strong candidates for that phase:

- separate package/app ownership for Svelte versus legacy React;
- richer Runtime request object;
- formal entitlement and control-plane integration;
- broader provider-agent executor interface;
- full protected artifact registry and trace replay harness;
- Svelte bundle splitting and ELK workerization if real graph sizes require it;
- manual card review and detail approval queues;
- offline entity-merge evaluation set;
- production packaging and launcher.

## Verification Expectations

At minimum, the implementation plan must include:

- Python tests for readiness/status payloads and source-run behavior.
- Svelte unit tests for API wrappers, query keys, session creation, source selection, triage review/approval, candidate display, and safe error rendering.
- Playwright e2e for the create -> triage -> start -> source state -> Top 10 journey using safe seeded or mocked data.
- A local milestone verification script that can run the focused gate without requiring live Liepin credentials.
- A documented optional live smoke for Pi/DokoBot/Liepin that is explicit, safe, and skipped by default.
