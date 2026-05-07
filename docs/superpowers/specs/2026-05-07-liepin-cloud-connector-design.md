# Liepin Cloud Connector And Detail-Budgeted Provider Adapter Design

## Context

SeekTalent needs a Liepin provider path that can be used from a future web UI or from another department's client through APIs. The user does not want to depend on the other department's Electron codebase and does not want a browser extension. For the experimental product path, the user accepts a managed embedded browser where the recruiter logs into Liepin inside our controlled session.

The current SeekTalent runtime already has:

- a provider adapter contract for retrieval;
- Python scoring, PRF, corpus, flywheel, benchmark, and artifact systems;
- a corpus layer that saves every provider-returned resume snapshot by default.

The Liepin work should add a provider connector, not replace the Python product core.

## Decision

Use a split architecture:

```text
Bun/TypeScript Liepin browser worker
  owns browser session execution, page navigation, card extraction, detail-page execution

Python SeekTalent core
  owns search planning, detail-open decisions, scoring, PRF, corpus/flywheel writes, artifacts, eval
```

The browser worker is an execution boundary. It must not own business ranking, LLM calls, PRF, corpus policy, or detail-budget policy.

The first implementation should be API-first and UI-later:

- expose backend APIs for connection, login status, run submission, run events, and result retrieval;
- do not implement the web UI in this rollout;
- keep the worker usable by a future Vite + TanStack web UI;
- keep the API usable by another client without coupling to that client's runtime.

## Why This Is The Performance-Oriented Choice

The dominant latency and cost are not Python versus Bun. The dominant costs are:

- browser startup and session readiness;
- Liepin page navigation and rendering;
- provider throttling and user-action pauses;
- opening candidate detail pages;
- duplicate detail opens across runs.

Performance should therefore come from product policy and execution discipline:

1. Search result cards first.
2. Score and dedupe card-level candidates before opening details.
3. Open details only for candidates selected by Python core.
4. Never reopen a detail page that was already opened for the same account and candidate unless explicitly forced.
5. Reuse the managed browser session.
6. Keep concurrency conservative and account-safe.
7. Treat CAPTCHA, login expiry, and verification as user-action states, not retry loops.

Bun/TypeScript is still the preferred worker stack because it is lightweight for web/browser automation, fits the future Vite/TanStack UI stack, and keeps browser-facing code close to the JS ecosystem. The design should keep a thin process boundary so the same worker code can be run under Node if a specific Playwright dependency is not stable under Bun.

## Goals

1. Add a Liepin provider connector that can search and extract resume cards through a managed browser session.
2. Keep the Python runtime as the authority for query planning, detail-open decisions, scoring, PRF, corpus, and flywheel.
3. Save all provider-returned card/detail snapshots into the existing corpus asset path.
4. Prevent wasted detail opens through a durable per-account detail-open ledger.
5. Provide API boundaries that can support both a future web UI and another department's client.
6. Build a fixture replay harness so page parsing and provider mapping can be tested without live Liepin access.
7. Avoid browser extensions, local Chrome profile scraping, and dependency on a user's existing local Chrome login state.

## Non-Goals

This design does not implement:

- the Vite/TanStack web UI;
- a browser extension;
- local Chrome profile reuse;
- CAPTCHA bypass or anti-bot evasion as a product feature;
- first-party resume search engine indexing;
- static benchmark pools or qrels;
- personalized memory;
- migration of Python scoring, PRF, corpus, flywheel, or eval logic to TypeScript.

## Components

### 1. Liepin Connector API

The backend should expose an API surface that is stable enough for both our future UI and external clients.

Initial API shape:

```text
POST /liepin/connections
  create or reuse a managed Liepin browser connection

GET /liepin/connections/{connection_id}
  return login/session/risk-control status

POST /liepin/connections/{connection_id}/login-url
  return a URL or session handle for the user to log in

POST /runs
  submit a SeekTalent run using provider=liepin

GET /runs/{run_id}
  return run status and high-level counters

GET /runs/{run_id}/events
  stream progress events

GET /runs/{run_id}/results
  return selected candidates and artifact refs
```

The API must not expose raw browser internals. Browser status should be domain-level:

- `logged_out`
- `ready`
- `needs_user_action`
- `risk_control_wait`
- `daily_detail_budget_exhausted`
- `temporarily_rate_limited`
- `failed`

### 2. Bun/TypeScript Browser Worker

The worker owns:

- launching and reusing managed browser sessions;
- presenting Liepin login to the user;
- detecting session readiness;
- executing keyword searches;
- extracting search result cards;
- opening detail pages only when instructed;
- returning raw card/detail payloads plus lightweight diagnostics;
- recording page structure and selector health for harness tests.

The worker does not decide which candidates are worth opening. It receives a detail-open plan from Python and executes it.

The worker should keep its contract small:

```text
search_cards(request) -> card batch + cursor + diagnostics
open_details(request) -> detail payloads + budget/status diagnostics
get_session_status(connection_id) -> status
```

### 3. Python Liepin Provider Adapter

The Python adapter implements the existing `ProviderAdapter` contract. It calls the connector API or internal worker client and maps Liepin card/detail payloads into `ResumeCandidate` objects.

The adapter should support two phases:

1. `fetch_mode=summary`: search card pages and return card-level candidates.
2. `fetch_mode=detail`: open approved detail pages and return detail-enriched candidates.

The current runtime should remain card-first. Detail fetch is a separate enrichment step, not the default retrieval path.

### 4. Detail Open Policy

Daily detail openings are scarce. Python core owns the policy.

The policy should:

- maintain per-tenant, per-workspace, per-Liepin-account, per-day budgets;
- check whether a provider candidate was already opened before;
- prefer opening candidates with stronger card-level evidence;
- avoid opening duplicate candidates across exploit, PRF, and generic explore lanes;
- stop opening details when budget is exhausted, while allowing the run to continue with card-level evidence;
- emit artifacts explaining which candidates were opened, skipped, or deferred.

The worker only executes the approved plan.

### 5. Detail Open Ledger

Add a durable connector ledger separate from `CorpusStore`.

The ledger owns provider/account operational facts:

- connection ID;
- provider account hash;
- session status;
- daily budget counters;
- detail-open events;
- provider candidate identity;
- skip/open reasons;
- last successful detail-open timestamp;
- user-action or risk-control states.

`CorpusStore` remains the document asset store. It saves card/detail snapshots and observations. The connector ledger answers "should we spend a detail open"; the corpus answers "what documents have we seen and saved."

### 6. Corpus Integration

Every Liepin provider-returned card should be saved as a provider snapshot. Detail pages should be saved as richer snapshots or detail observations.

The corpus row must distinguish:

- card-level payload;
- detail-level payload;
- provider name `liepin`;
- query/run/stage provenance;
- raw payload artifact ref;
- normalized text availability;
- whether the snapshot is sufficient for scoring or only for dedupe/search preview.

Raw Liepin payloads remain untrusted external content and must be treated as quoted data when sent to LLMs.

## Data Flow

```text
User creates Liepin connection
  -> managed browser session opens
  -> user logs into Liepin
  -> connector reports ready

SeekTalent run starts with provider=liepin
  -> Python builds search requests
  -> worker searches card pages
  -> Python saves all card snapshots to CorpusStore
  -> Python scores/dedupes card-level candidates
  -> Python builds detail-open plan under budget
  -> worker opens approved details
  -> Python saves detail snapshots
  -> Python continues scoring, PRF, finalization, artifacts, flywheel
```

## Risk-Control And Account Safety

This connector must not treat Liepin as a generic scraping target.

Rules:

- no CAPTCHA bypass;
- no credential collection outside the managed Liepin login page;
- no use of the user's local Chrome cookies or profile;
- no aggressive concurrency;
- no hidden retry storm when Liepin asks for verification;
- no automatic detail opening beyond the approved budget;
- account-risk statuses must be surfaced to the API and artifacts.

If Liepin requires user action, the run should pause or degrade gracefully instead of failing after a long partial run. For example, card-level results can still be preserved if details cannot be opened.

## Session And Secret Boundary

Liepin login state is a connector secret, not a corpus or flywheel asset.

Rules:

- never ask the user to paste Liepin credentials into SeekTalent;
- only let the user authenticate inside the managed Liepin browser page;
- store session cookies/tokens only in the connector's protected session store;
- do not write cookies, tokens, request headers, or account identifiers into run artifacts;
- store provider account identity only as a stable hash for budget and audit purposes;
- do not include connector secrets in fixture replay files;
- allow explicit session revocation from the API.

## Performance Strategy

Use these defaults unless testing proves otherwise:

- one managed browser context per active Liepin connection;
- one active page for card search per connection initially;
- detail page openings serialized or very low concurrency;
- browser session reuse across runs;
- fixture replay for parser iteration;
- API event streaming so long-running operations remain observable.

Do not optimize by increasing concurrency first. For this provider, high concurrency is likely to hurt account safety and reliability. The faster path is reducing unnecessary detail opens.

## Failure Handling

Expected failures should become explicit states:

- login expired -> `needs_user_action`;
- verification required -> `needs_user_action`;
- detail budget exhausted -> continue with card-level results;
- page structure changed -> parser health failure with saved fixture;
- temporary rate limit -> stop provider calls and record status;
- worker crashed -> run can resume from saved corpus/ledger/artifacts in a future resumability rollout.

Retries should be bounded and only used where they reduce transient browser flakiness. They must not bypass user-action states or consume detail budget repeatedly.

## Testing And Harness

The first implementation plan should include:

1. Contract tests for the Python `LiepinProviderAdapter`.
2. Fixture replay tests for card extraction and detail extraction.
3. Detail-budget tests proving duplicate candidates are not reopened.
4. Corpus tests proving card and detail payloads are saved as provider snapshots.
5. Risk-state tests for logged-out, needs-user-action, and budget-exhausted states.
6. A small live smoke command gated behind explicit local credentials/session setup.

The live command should be manual-only. CI should use fixture replay.

## Rollout

Recommended order:

1. Add provider selection config for `cts` vs `liepin`.
2. Add connector API client and Python adapter with fake worker fixtures.
3. Add detail-open ledger and policy.
4. Add Bun/TypeScript worker skeleton with fixture replay.
5. Add live session login and card search.
6. Add selective detail opening.
7. Run one JD end-to-end with low budgets.
8. Only after live behavior is stable, design the Vite/TanStack UI.

## Acceptance Criteria

- Python remains the source of truth for query planning, scoring, PRF, corpus, flywheel, and detail-open policy.
- Bun/TypeScript worker only executes browser/session/page operations.
- No browser extension is required.
- No local Chrome profile or local user cookies are read.
- All provider-returned Liepin cards are saved to CorpusStore.
- Detail pages are opened only when Python approves them.
- Repeated candidates do not consume detail budget again.
- Budget exhaustion does not fail the whole run.
- Fixture replay can test extraction without live Liepin access.
- API status exposes user-action and account-risk states clearly.
