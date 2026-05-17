# Liepin Live Browser Action And Card Policy Design

## Summary

SeekTalent now has the Runtime multi-source contract needed to run CTS and Liepin as source lanes, merge evidence, and produce one unified Top 10. The remaining product gap is narrower: Liepin still needs a live browser-action path that can search through the user's already logged-in Liepin browser session, collect provider-ranked profile cards, and decide which cards are worth spending detail-open budget on.

This feature defines that gap as a focused slice:

1. DokoBot MCP / compatible browser action capability is a SeekTalent runtime dependency, not a Codex tooling dependency.
2. PI Agent uses that capability only as a bounded provider executor for Liepin page work.
3. Runtime remains the owner of source strategy, budgets, card-detail recommendations, detail leases, merge, scoring, and final Top 10.
4. Liepin card decisions preserve the provider search ranking as the primary order, filter only obvious mismatches, and recommend detail opens within budget.

The user is expected to already be logged into Liepin in the local browser. The product does not ask the user to paste cookies or credentials, and it must not inspect or export browser cookies.

## Product Contract

Runtime owns:

- selected source kinds and source-lane budget policy
- card-page, card-count, detail-recommendation, and detail-open limits
- provider-rank-first Liepin card decision policy
- detail recommendations
- approved detail lease consumption
- candidate merge, canonical resume selection, final scoring, and Top 10
- public payload allowlists and safe events

PI Agent owns:

- bounded Liepin provider interaction tasks only
- using DokoBot-compatible browser actions to type a keyword, submit search, read cards, and paginate
- returning typed card observations, protected artifact refs, and action traces

DokoBot MCP / compatible browser backend owns:

- browser action execution inside the user's already logged-in local browser context
- UI-level operations declared by the trusted action manifest
- no source strategy, no budget decisions, no ranking decisions, no artifact publication policy

Workbench owns:

- display and persistence of source-run state
- detail recommendation display
- approval request, approved lease, budget ledger, and audit persistence

Workbench must not directly run Liepin browser actions and must not become a second provider orchestrator.

The runtime call chain must stay explicit:

```text
Workbench source run
  -> Runtime source lane request
  -> LiepinProviderAdapter / LiepinWorkerClient protocol
  -> LiepinPiRunner
  -> PI Agent DokoBot action backend
  -> DokoBot MCP / compatible browser actions
```

Runtime may choose source lanes, budgets, and recommendation policy, but it must not import DokoBot modules, open browser sessions, or call browser actions directly. DokoBot is only reachable behind PI Agent / LiepinPiRunner through typed provider contracts.

## Current Code Facts

The current repository already has these building blocks:

- `src/seektalent/config.py` currently accepts only `disabled`, `fake_fixture`, `managed_local`, and `external_http` Liepin worker modes. This feature must add an explicit `dokobot_action` product runtime mode or an equally explicit PI-agent backend selector, otherwise the DokoBot path can be implemented but never selected by Workbench or Runtime.
- `src/seektalent/providers/pi_agent/capabilities.py` defines trusted DokoBot-compatible action manifest checks. Action mode requires read, click, type, navigation, pagination, local transport, trusted manifest id/version, and forbidden operations disabled.
- `src/seektalent/providers/liepin/pi_runner.py` defines `LiepinPiRunner`, backend modes, connection/provider-account locking, and fail-closed `dokobot_action` dispatch. Today `SearchCardsExecutor` returns only `PiAgentResult`, so the runner cannot yet carry actual card search results back to Runtime.
- `src/seektalent/providers/liepin/worker_contracts.py` defines `LiepinWorkerCandidateCard` and `LiepinCardSearchResponse`, which are the existing typed card payload contracts.
- `src/seektalent/providers/liepin/mapper.py` currently writes provider metadata and artifact refs into `ResumeCandidate.raw`, not structured card business fields. This feature must create an allowlisted safe card summary path instead of assuming card policy can read title/company/skills directly from `candidate.raw`.
- `src/seektalent/providers/liepin/runtime_lane.py` already separates Liepin card and detail lane modes. Its current detail recommendation helper only checks how many query terms appear in `candidate.search_text`; that is not enough for recruiter-grade card judgment.
- `src/seektalent/runtime/source_lanes.py` already has `RuntimeSourceBudgetPolicy`, `RuntimeSourceLaneRequest`, `RuntimeSourceLaneResult`, `RuntimeDetailRecommendation`, `RuntimeApprovedDetailLease`, and safe public payload methods.
- `src/seektalent/providers/liepin/policy.py` already has a legacy detail-open planning helper with `card_value_score`, but it does not model provider rank, hard filters, hold decisions, or Runtime detail recommendation fields.
- `apps/liepin-worker` is legacy worker compatibility. It can navigate and extract cards through Playwright, but this feature's product direction is DokoBot/PI Agent as provider execution machinery.

## Non-Goals

This feature does not build:

- a human card-review UI
- a manual detail-approval UI
- a generic browser automation plugin marketplace
- A2A transport
- automatic source strategy optimization
- broad Candidate Evidence Graph UI
- DokoBot installation or permission mutation
- cookie extraction, authenticated API replay, network interception, in-page script execution, or provider-signature replay

If DokoBot action capability is unavailable, untrusted, expired, or read-only, Liepin live action must fail closed. It must not silently downgrade to read-only, silently switch to legacy worker compatibility, install DokoBot, mutate MCP permissions, or ask Codex tooling to operate the browser.

## DokoBot Runtime Boundary

The DokoBot action backend is part of SeekTalent's runtime provider integration, but it is not owned by Runtime orchestration code. It is not the Codex-side `dokobot` skill or Codex MCP tooling. Codex may help implement and test the repository, but production Liepin search must be executed by SeekTalent's PI Agent through its own configured DokoBot-compatible action manifest and runtime connector.

For this feature to be complete, SeekTalent must have an explicit product path from settings to PI Agent action execution:

- settings can select a live `dokobot_action` / PI-agent Liepin backend;
- worker-client factory or provider registry can build the PI-backed Liepin worker client;
- Workbench source runs can use that mode without knowing DokoBot details;
- Workbench source connection state can be verified as connected from the user's already logged-in local browser session before a Liepin source run starts;
- DokoBot capability probing and trusted action manifest binding happen before live action;
- if the actual DokoBot MCP/action transport binding cannot be implemented or proven locally, the build is blocked rather than marked complete.

Live action requirements:

- The action manifest must be preconfigured and trusted by SeekTalent.
- Transport must be local-only for the first implementation.
- The backend must operate on the user's already logged-in browser session.
- `dokobot_action` is a live Liepin worker mode. It must use the same compliance store, provider-account binding, ready-session check, and provider connection safety enforcement as other live Liepin worker modes.
- The PI-backed worker client must provide the Workbench connection methods needed to mark the source connection connected, including a safe provider-account hash and session metadata path. A search-only client is not enough.
- Login/risk state must be detected before card collection and after navigation changes through typed executor status, not free-form strings.
- Missing login, verification challenge, risk challenge, unsupported route, timeout, or blocked capability must return a typed PI stop reason and a normalized Runtime safe reason code. Raw PI failure codes are execution-layer diagnostics and must not be exposed directly in Runtime public payloads, Workbench graph state, notes, or CLI output.
- Browser actions are limited to allowed Liepin routes and provider UI operations:
  - navigate to search
  - type keyword
  - submit search
  - read card list
  - paginate within budget
  - read detail only through approved detail lease in a later lane

The existing read-only `DokoBotClient` remains read-only. Live action must use a separate action executor contract so read-only command output cannot be mistaken for permission to type or click.

The DokoBot action executor must live under PI Agent / Liepin provider execution code. Runtime and Workbench may depend only on typed results such as `LiepinPiCardSearchResult`, `LiepinCardSearchResponse`, `RuntimeSourceLaneResult`, and `RuntimeDetailRecommendation`.

## PI Runner Card Result Contract

`LiepinPiRunner.search_cards()` must return both the PI execution result and, on success, a typed card search response. The current return type, `PiAgentResult`, is insufficient because Runtime needs actual `LiepinCardSearchResponse` data to build candidates, evidence, and detail recommendations.

Introduce a small result wrapper:

```python
@dataclass(frozen=True, kw_only=True)
class LiepinPiCardSearchResult:
    pi_result: PiAgentResult
    card_search: LiepinCardSearchResponse | None = None

    @property
    def status(self) -> PiAgentResultStatus:
        return self.pi_result.status
```

Rules:

- `status=SUCCEEDED` requires `card_search` to be present.
- `status=BLOCKED` or `FAILED` may omit `card_search`, but must carry the safe PI stop reason and action trace.
- `status=PARTIAL` may omit `card_search` only when no cards were safely collected. If partial cards were safely collected, it must carry `card_search` so Runtime can preserve partial candidates and evidence instead of discarding them as a blocked/failed lane.
- Existing runner lock behavior stays unchanged.
- `dokobot_action` calls only the explicit DokoBot card executor.
- `legacy_worker_compat` calls only the explicit legacy executor.
- No backend mode can fallback to another mode.

## Live Card Search Contract

The DokoBot card executor should return `LiepinCardSearchResponse`, reusing the existing worker card model so the adapter surface does not split into parallel payload shapes.

Inputs:

- `session_id`
- `source_run_id`
- `connection_id`
- `provider_account_lock_key`
- `keyword_query`
- `query_terms`
- `max_pages`
- `page_size`
- `max_cards`
- `allowed_hosts`
- `transport_policy`
- `source_budget_policy_version`

Output:

- `PiAgentResult` with action trace ref
- `LiepinCardSearchResponse` with:
  - provider-ranked cards in page/index order
  - allowlisted `safeCardSummary` for each DokoBot-action card
  - redacted diagnostics
  - raw candidate count
  - request payload containing only safe request metadata
  - protected artifact refs inside card payloads where needed

The executor must not return cookies, raw HTML, full raw provider responses, contact details, approval secrets, or browser storage material in public payloads. Raw or protected browser observations must go through protected artifact refs.

Pagination must be explicit and budget-bound:

- start from page 1 unless an approved cursor is provided by the PI task;
- collect at most `max_pages`;
- collect at most `max_cards` total across pages;
- preserve provider rank across pages as `(page_index, page_rank, global_provider_rank)`;
- stop on provider exhaustion, login/risk state, unsupported route, timeout, or budget exhaustion with a typed safe stop reason.

Runtime must pass card-search budget into the provider context used by the PI-backed worker client:

- `liepin_card_page_size` controls the page size sent to the executor;
- `liepin_max_cards` controls the total cards collected across pages;
- `liepin_max_pages` is derived from `ceil(liepin_max_cards / liepin_card_page_size)` unless a stricter runtime policy is configured.

## Card Summary Contract

The card decision policy must not parse arbitrary raw provider payloads in Runtime. The card collector or mapper should expose a safe card summary shape from card text and safe payload fields:

```python
@dataclass(frozen=True, kw_only=True)
class LiepinCardSummary:
    candidate_resume_id: str
    provider_rank: int
    display_title: str | None = None
    current_or_recent_company: str | None = None
    current_or_recent_title: str | None = None
    work_years: int | None = None
    age: int | None = None
    city: str | None = None
    expected_city: str | None = None
    education_level: str | None = None
    school_names: tuple[str, ...] = ()
    major_names: tuple[str, ...] = ()
    skill_tags: tuple[str, ...] = ()
    job_intention: str | None = None
    recent_experience_text: str | None = None
    normalized_card_text: str = ""
    masked_name: bool = False
```

The summary is a safe decision input. It is not a public resume and it is not enough to finalize a candidate.

Safe card summary fields must be produced by an allowlist path:

- DokoBot action-produced `LiepinWorkerCandidateCard` values must carry a `safe_card_summary` field;
- legacy or fixture cards may leave the field absent for backward compatibility;
- mapper writes a `safe_card_summary` object into `ResumeCandidate.raw` only from the typed allowlisted field.

In both cases the fields must be explicitly allowlisted. Raw payload blobs, raw HTML, browser state, cookies, direct contact material, and approval secrets must not be copied into the summary.

If DokoBot can read a card but cannot extract a full summary, it should still return a typed summary with known fields populated and unknown fields `None` or empty tuples. It must not make Runtime parse arbitrary payload keys to compensate.

## Card Decision Policy

The card decision answers one narrow question:

> Is this provider-ranked Liepin card worth spending detail budget on?

It does not decide the final Top 10 and does not rerank the whole run. Final ranking remains Runtime scoring after CTS and Liepin evidence are merged.

Actions:

- `recommend_detail`: card is eligible for detail recommendation within budget
- `reject_obvious_mismatch`: card is clearly not relevant and should not consume detail budget
- `hold_insufficient_card_signal`: card lacks enough safe card evidence; do not spend budget in v1

Provider ranking is primary:

1. Iterate cards in Liepin provider rank order.
2. Apply only hard obvious-mismatch filters.
3. Keep eligible cards in their original provider order.
4. Recommend the first eligible cards until `liepin_max_detail_recommendations` is reached.
5. Record policy scores and reason codes for audit, but do not use those scores as a primary reranker.

Hard reject examples:

- role family is clearly wrong for the target role
- must-have terms have zero overlap and current/recent role evidence does not compensate
- work-year range is far outside hard constraints
- city/location is a hard mismatch when the JD requires one location
- education requirement is a hard mismatch when explicitly required
- card text indicates sales/store/non-technical profile for an engineering role

Missing fields are not hard rejects. Missing fields should usually become `hold_insufficient_card_signal` unless enough other safe card fields support `recommend_detail`.

Reason codes must be enum/allowlist values such as:

- `card_rank_budget`
- `provider_rank_preserved`
- `hard_filter_passed`
- `obvious_role_mismatch`
- `must_have_zero_overlap`
- `hard_location_mismatch`
- `hard_education_mismatch`
- `insufficient_card_signal`
- `within_run_detail_budget`

Public payloads may expose only reason codes, provider rank, card policy rank, budget reason code, counts, and safe artifact refs.

## PI / LLM Role In Card Judgment

The first implementation should be deterministic-first:

- Extract safe card fields and normalized card text.
- Run direct hard filters and budget allocation in Python.
- Use PI/LLM classification only for uncertain card summaries when the deterministic policy cannot classify safely.

If PI/LLM classification is used:

- input is the safe card summary, not raw provider HTML or raw resume
- output is strict JSON with action and allowlisted reason codes
- it cannot change budget
- it cannot approve detail open
- it cannot override a Runtime hard reject without an explicit policy reason
- parsing failure becomes `hold_insufficient_card_signal`, not a detail recommendation

## Budget Contract

Default policy remains Runtime-owned:

- CTS multi-source lane: one page of 10
- Liepin card search: configured page size and max card count
- Liepin detail recommendations: configured per-run recommendation count
- Liepin detail opens: approved lease budget, separate from recommendation count
- final shortlist: Top 10 after all selected source lanes are merged and scored

For Liepin:

- card collection budget controls how many provider-ranked cards are inspected
- detail recommendation budget controls how many cards Runtime recommends opening
- detail-open budget controls how many approved leases may be consumed

Recommendation budget and open budget must remain separate because v1 may recommend details before a human approval UI exists.

Blocked source behavior is part of the budget contract. If a PI/DokoBot card lane is blocked before or during collection, Runtime must return a safe blocked or partial `RuntimeSourceLaneResult`; Workbench must not collapse that into an ordinary failed job with raw exception text.

PI stop reasons must be normalized before crossing into Runtime public payloads:

- `LOGIN_EXPIRED` -> `blocked_login_required`
- `VERIFICATION_REQUIRED` or `RISK_CONTROL` -> `blocked_compliance`
- `DOKOBOT_ACTION_CAPABILITY_UNAVAILABLE` or `PROVIDER_CONNECTION_LOCKED` -> `blocked_backend_unavailable`
- `PAGE_TIMEOUT` -> `partial_timeout` if cards were collected, otherwise `failed_provider_error`
- `SELECTOR_DRIFT` or `EXTRACTION_FAILURE` -> `failed_provider_error`

Unknown PI failure codes must map to `failed_provider_error` and may only appear in protected diagnostics or action traces, not public payloads.

When the PI-backed worker client adapts a blocked PI result into the existing `LiepinWorkerClient` protocol, it must carry the PI failure code through a structured worker error code such as `LiepinWorkerModeError.code`. Runtime must normalize that code; it must not parse raw exception messages and must not require direct access to `LiepinPiCardSearchResult` on the Runtime side.

When the PI-backed worker client adapts `PARTIAL + card_search`, it must carry the mapped partial `SearchResult`, cards-collected count, and structured failure code through a typed partial worker error. Runtime must merge the partial candidates/evidence, emit `RuntimeSourceLaneResult(status="partial")`, and expose only Runtime safe reason codes such as `partial_timeout`.

## Acceptance Criteria

- `dokobot_action` mode uses a SeekTalent runtime action executor and returns typed cards, not only `PiAgentResult`.
- Workbench/Runtime can actually select the `dokobot_action` Liepin path through product settings and provider registry without importing DokoBot into Runtime or Workbench code.
- Workbench can mark a Liepin source connection connected through the PI-backed DokoBot path when the user's local browser is already logged in, and cannot start the source run when that verification is missing.
- `dokobot_action` runs through the live compliance/session safety branch, including `LiepinStore` and provider connection safety checks.
- If DokoBot MCP/action transport binding is unavailable, the build is blocked or the lane reports a safe blocked result; it is not counted as complete.
- DokoBot read-only capability still cannot submit a search.
- DokoBot action mode still fails closed without trusted local action manifest capability.
- No Codex-side MCP/tool availability is treated as SeekTalent runtime capability.
- Card collection preserves provider rank across pages and respects `max_pages`, `page_size`, and `max_cards`.
- Runtime passes `liepin_max_cards` and derived `liepin_max_pages` from `RuntimeSourceBudgetPolicy` to the PI-backed worker client.
- Card policy consumes safe card summaries from an allowlisted field path, not arbitrary raw provider payloads.
- DokoBot action-produced cards populate `safeCardSummary`; Runtime never falls back to arbitrary raw provider payload keys for card judgment.
- Liepin card detail recommendations preserve provider rank after hard filters.
- Obvious mismatches do not consume detail recommendation budget.
- Missing/ambiguous cards do not become detail recommendations by default.
- Detail recommendation public payloads expose reason codes and ranks, not free-text raw card material.
- PI/DokoBot partial card search preserves safely collected candidates/evidence and marks the source lane partial instead of completed, blocked, or failed.
- PI/DokoBot blocked results become safe blocked lane/source-run state, not generic failed jobs with raw exception text or raw PI failure-code values.
- PI/LLM card classification, if added, is strict JSON and cannot own budget or final ranking.
- CTS and Liepin still merge into one Runtime candidate pool and one final Top 10 through the existing multi-source contract.
- Human card-review UI, manual approval UI, and A2A remain deferred.
