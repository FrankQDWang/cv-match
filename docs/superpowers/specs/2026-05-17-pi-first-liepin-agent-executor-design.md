# Pi-First Liepin Agent Executor Design

## Summary

This spec supersedes the Liepin live-browser direction in `docs/superpowers/specs/2026-05-16-liepin-live-browser-action-card-policy-design.md` where it treats a repo-built `DokoBotActionSurface` / `dokobot_action` transport as the primary executor.

The product direction is now Pi-first:

1. SeekTalent uses Pi as the external general agent harness for Liepin browser work.
2. DokoBot MCP and DokoBot browser tools are registered inside the Pi runtime, not inside Codex and not as Runtime-owned browser tooling.
3. Runtime stays the source-lane, budget, merge, evidence, scoring, and finalization owner.
4. Pi is a bounded provider executor: it receives a typed Liepin task, uses its DokoBot tool access to search and read visible cards, and returns a strict typed result.
5. Existing self-built action-surface skeletons are cleaned up when they no longer pay for themselves. There is no compatibility fallback from Pi to the old `dokobot_action` route.
6. Runtime, not Pi, owns public hashes, public payload serialization, and final acceptance of provider artifacts.

The user is expected to already be logged into Liepin in the browser profile used by DokoBot. SeekTalent must not ask for cookies, export cookies, replay authenticated provider APIs, or use Codex-side browser tools for production Liepin execution.

## Terminology

- **Pi** means the external general agent harness selected for this product path.
- **DokoBot MCP** means the browser capability Pi can use inside its own runtime. It is not the Codex `dokobot` skill.
- **Runtime** means SeekTalent's source-run orchestration layer under `src/seektalent/runtime` and provider lane adapters.
- **Workbench** means the UI/API/store layer that displays source runs and persists approval, lease, budget, and audit state.
- **Old DokoBot action route** means repo-local `DokoBotActionSurface`, `DokoBotActionTransportSession`, and `liepin_worker_mode=dokobot_action` code that attempted to make SeekTalent itself own a browser action surface.

## Product Contract

The live Liepin card-search call chain must be:

```text
Workbench source run
  -> RuntimeSourceLaneRequest(source="liepin", lane_mode="card")
  -> LiepinProviderAdapter
  -> Pi-backed Liepin worker client
  -> Pi external agent session
  -> Pi Liepin skill/instructions
  -> DokoBot MCP/tooling registered inside Pi
  -> strict JSON result
  -> Pydantic validation
  -> LiepinCardSearchResponse
  -> RuntimeSourceLaneResult
```

Runtime owns:

- selected source lanes and source-lane budgets
- CTS and Liepin concurrent lane execution
- provider-rank-first Liepin card decision policy
- detail recommendations
- approved detail lease consumption in a separate detail lane
- evidence merge, identity dedupe, canonical selection, scoring, and unified Top 10
- public payload allowlists and safe events

Pi owns:

- bounded Liepin provider interaction for a single assigned task
- browser page variance handling through its DokoBot MCP/tool access
- returning one strict structured JSON envelope with action trace refs, protected artifact refs, safe card summaries, observed provider-key material refs, and typed stop reasons

DokoBot MCP owns:

- browser navigation and interaction inside Pi's runtime
- using the already logged-in browser context selected by the product configuration
- no source strategy, no ranking strategy, no budget strategy, no approval strategy, and no finalization authority

Workbench owns:

- source-run display and persistence
- detail recommendation display
- approval request, approved detail lease, budget ledger, and audit persistence
- no direct Liepin browser actions

## Key Decisions

### Pi Is The Live Executor

The first real live Liepin executor is `pi_agent`, meaning "run this provider task through the external Pi agent harness." It is not a custom in-process browser automation wrapper.

`fake_fixture` may remain for tests and local demos only when explicitly selected. It is not a fallback from live Pi.

### DokoBot Belongs Inside Pi

SeekTalent config may check that Pi is configured with a DokoBot-capable environment, but Runtime and Workbench must not import or invoke DokoBot action APIs. Product code speaks to Pi through a narrow process/RPC adapter and validates Pi output.

DokoBot read capability and DokoBot action capability are separate. Public DokoBot documentation describes both read-oriented extraction and browser-control tools, so SeekTalent must not infer capability from the product name alone. A live Liepin lane requires:

- a configured Pi runtime
- the repo-owned Liepin Pi skill loaded into that runtime
- a trusted DokoBot action capability manifest or equivalent admin-configured proof
- observed evidence that Pi can invoke the expected read/action tool names
- allowed host policy including `liepin.com`

If Pi cannot access DokoBot, Liepin card search returns a blocked lane with a safe reason code such as `blocked_backend_unavailable` or `blocked_login_required`. It must not switch to Codex tooling or the old repo-local action surface.

### Strict Output Beats Natural Language

Pi may reason and navigate flexibly, but the boundary back into SeekTalent is strict:

- final assistant output must be exactly one JSON object, allowing only surrounding whitespace
- natural-language prefaces, Markdown fences, trailing notes, and "last JSON wins" extraction are invalid
- JSON is validated by strict Pydantic models with `extra="forbid"`, `strict=True`, and hidden validation inputs
- unknown enum values fail closed
- raw exception text, cookies, raw HTML, browser storage, direct contact material, and approval secrets are rejected by a SafePayloadFirewall before mapping to Runtime models
- partial card results are allowed only when each card passes schema validation

### Runtime Keeps Card Policy

Pi collects and summarizes visible cards. Runtime decides which cards are worth detail budget.

The first card policy remains provider-rank-first:

1. Preserve Liepin provider order.
2. Reject only obvious mismatches.
3. Hold insufficient-signal cards instead of spending detail budget.
4. Recommend details for eligible cards until the Runtime budget is exhausted.
5. Use scores and reason codes for audit, not as primary reranking.

### Old Skeleton Cleanup Is Part Of The Plan

The previous branch introduced useful contracts, but several names and seams now encode the wrong executor premise. The implementation must remove or rename these live-path concepts where they would mislead future work:

- `liepin_worker_mode=dokobot_action`
- `DokoBotActionSurface`
- `DokoBotActionTransportSession`
- custom `DokoBotLiepinSearchCardsExecutor`
- `PiBackendMode.DOKOBOT_ACTION` as the product live path
- automatic compatibility dispatch from one backend mode to another

Some underlying typed contracts are still valuable and should be reused when they remain true:

- provider interaction task/result models
- protected artifact refs
- action trace refs
- safe reason code mapping
- `LiepinCardSearchResponse`
- safe card summary model
- Runtime source-lane budget and evidence models

## Current Repository Facts

The current worktree already contains a partial 05-16 implementation:

- `src/seektalent/providers/liepin/pi_runner.py` dispatches between backend modes such as `DOKOBOT_ACTION`, `LEGACY_WORKER_COMPAT`, and `FAKE_FIXTURE`.
- `src/seektalent/providers/liepin/client.py` can build a `DokoBotActionTransportSession` with `action_surface=None`, which means the product path is not a real Pi executor.
- `src/seektalent/providers/pi_agent/dokobot_action_transport.py` defines a repo-local action transport abstraction that does not represent DokoBot MCP registered inside Pi.
- `src/seektalent/providers/liepin/dokobot_actions.py` is tied to the old self-built action route.
- `src/seektalent/providers/liepin/card_policy.py` and the Runtime budget/detail-recommendation path are still aligned with the product requirement and should be preserved.
- `src/seektalent/runtime/source_lanes.py` already contains multi-source lane, budget, evidence, lease, and safe public payload models that the Pi executor must feed.

This feature is therefore a pivot, not a greenfield rewrite. Keep the source-lane contract and card policy work; replace the executor premise.

## Pi Executor Boundary

Use Pi's documented headless interfaces, not an invented command. Pi supports print/JSON mode for simple scripts and RPC mode for embedding. SeekTalent should use RPC mode as the product boundary because it gives request/response correlation and streamed events over JSONL.

The process command is built by SeekTalent and must include RPC mode, disabled session persistence, and the repo-owned Liepin skill. Ambient skill discovery should be disabled so the product task is not influenced by unrelated skills:

```text
pi --mode rpc --no-session --no-skills --skill <repo-liepin-skill-path>
```

The client sends newline-delimited JSON commands such as:

```json
{"id":"req-1","type":"prompt","message":"..."}
```

The client reads newline-delimited JSON responses and events. A prompt acknowledgement only means the prompt was accepted; the final task result must be extracted from the terminal agent message/event stream and then validated as a SeekTalent JSON envelope.

The RPC adapter must be one-task-per-process for this slice. It must not multiplex concurrent prompts through one Pi process because event streams are not a safe source-run correlation boundary.

The RPC adapter must:

- validate `--mode rpc`, `--no-session`, and the loaded `--skill` path before launching Pi
- apply one deadline to process start, prompt acknowledgement, streamed events, final output extraction, and process shutdown
- drain stdout and stderr concurrently
- handle prompt command response `success=false` as a safe failed result
- treat `extension_ui_request` or equivalent UI/input requests as denied and stop the provider task
- terminate or kill the Pi process on timeout, missing `agent_end`, or UI request
- never expose stderr or raw event payloads in public Runtime payloads

Add a small Pi adapter that is explicit about the RPC transport and easy to test with fakes:

```python
@dataclass(frozen=True, kw_only=True)
class PiRpcCommand:
    argv: tuple[str, ...]
    timeout_seconds: int
    artifact_root: Path
    cwd: Path | None = None
    env: Mapping[str, str] = field(default_factory=dict)


class PiRpcTransport(Protocol):
    def request(self, command: PiRpcCommand, *, prompt: str) -> PiRpcTaskResult:
        ...
```

Tests must not require Pi to be installed. They inject a fake `PiRpcTransport` that returns JSONL-like task results.

The adapter must expose:

```python
class PiLiepinExecutor:
    def search_cards(self, task: LiepinSearchCardsTask) -> LiepinPiCardSearchResult:
        ...

    def probe_capabilities(self) -> PiLiepinCapabilityProbeResult:
        ...

    def probe_session(self, task: LiepinSessionProbeTask) -> PiLiepinSessionProbeResult:
        ...
```

The executor is responsible for:

- probing Pi availability before live use
- probing whether Pi's runtime exposes the configured DokoBot tool
- probing login/risk/account state for the Workbench connected gate
- building the Liepin task prompt and including the strict output schema
- sending the task to Pi
- extracting the final JSON envelope
- validating the envelope with strict schemas, business invariants, safe artifact refs, and SafePayloadFirewall
- computing Runtime-owned provider candidate/account hashes from protected observed material
- mapping it to `LiepinCardSearchResponse`
- returning blocked/failed typed results for Pi unavailable, DokoBot unavailable, login blocked, risk blocked, timeout, and malformed output

The executor is not responsible for:

- deciding sources
- changing Runtime budgets
- approving detail opens
- reranking candidates
- merging CTS and Liepin
- writing Workbench state directly

## Pi Capability Proof Contract

Pi core does not guarantee MCP support. DokoBot availability must therefore be proven inside the configured Pi runtime before any Liepin live source run.

Before `pi_agent` can report ready, SeekTalent runs a Pi capability probe task. Self-reported JSON booleans are not sufficient. A ready probe requires a strict JSON envelope plus proof that SeekTalent can verify outside the final assistant text. For this slice, the primary proof is the Pi RPC event stream: SeekTalent must extract observed tool names from tool execution events and confirm that the expected DokoBot read/action tools were actually invoked. A trusted capability manifest or `tool_evidence_ref` may add protected diagnostic evidence, but it is not enough by itself unless the local artifact registry validates a signed/admin-trusted manifest.

The read tool and every required action tool must belong to the configured DokoBot tool prefix in both places: the final probe envelope and the observed Pi RPC tool events. A probe that reports `dokobot.read` but uses non-DokoBot tools such as `browser.click` or `browser.type_text` is blocked for this slice rather than treated as a mixed-tool fallback.

The probe returns:

```json
{
  "schema_version": "seektalent.pi_capability_probe.v1",
  "status": "ready",
  "pi_version": "0.0.0",
  "read_tool_name": "dokobot.read",
  "action_tool_names": ["dokobot.navigate", "dokobot.click", "dokobot.type_text"],
  "proof_kind": "trusted_manifest_and_observed_tool_event",
  "capability_manifest_ref": "artifact://protected/pi-capability/run-123/manifest",
  "tool_evidence_ref": "artifact://protected/pi-capability/run-123/tool-events",
  "allowed_hosts": ["liepin.com"],
  "stop_reason": null
}
```

Allowed statuses:

- `ready`
- `blocked`
- `failed`

Allowed stop reasons:

- `blocked_pi_unavailable`
- `blocked_dokobot_unavailable`
- `blocked_dokobot_tool_unavailable`
- `blocked_dokobot_permission_missing`
- `blocked_unsupported_host_policy`
- `failed_malformed_output`
- `failed_internal_error`

If the capability probe is not `ready`, the worker client is not ready and the Runtime lane returns a safe blocked result. There is no fallback to the old repo-local DokoBot action route.

## Pi Artifact Handoff Contract

Pi artifact refs are not trusted just because the final JSON names them. For every Pi task, SeekTalent creates or selects a scoped local artifact root under the configured local artifacts directory and passes it to the Pi RPC process as `SEEKTALENT_PI_ARTIFACT_ROOT`. The task prompt also states the same root for auditability.

The Pi Liepin skill must write every returned `artifact://protected/...` and `artifact://public-summary/...` ref to that root before returning the final JSON. The relative file path is the artifact ref path after the scope. For example, `artifact://protected/pi-trace/run-123` must materialize under:

```text
$SEEKTALENT_PI_ARTIFACT_ROOT/protected/pi-trace/run-123
```

SeekTalent then validates each ref through the local artifact registry and resolves protected provider-key/account material only inside Runtime for HMAC. Pi must not compute SeekTalent provider hashes and must not return unmaterialized refs. Missing files, path traversal, unsupported schemes, and invented refs fail closed before cards merge.

If a configured Pi runtime cannot write scoped local artifact files, `pi_agent` is not ready for live Liepin use in this slice. Do not silently accept string-only artifact refs and do not fall back to the old DokoBot action route.

## Pi Skill Contract

SeekTalent should include a repo-owned Pi instruction asset for Liepin card search. The asset is product instruction, not a Codex skill.

The instruction must tell Pi:

- use DokoBot browser tooling only from inside the Pi runtime
- do not ask for credentials or cookies
- use the already logged-in browser profile
- type the provided keyword exactly
- collect cards in provider order
- stop at Runtime-provided page/card budgets
- never open detail pages during card mode
- return only the strict JSON envelope
- include safe card summaries and artifact refs
- use typed stop reasons

The instruction must forbid:

- cookie export
- credential prompts
- direct provider API replay
- network interception
- in-page script execution to extract hidden data
- solving provider verification challenges
- opening details without an approved detail lease
- using Codex tools

## Output Envelope

Pi returns one JSON object shaped like this:

```json
{
  "schema_version": "seektalent.pi_liepin_cards.v1",
  "status": "succeeded",
  "stop_reason": null,
  "source_run_id": "run-123",
  "query": "python ranking backend",
  "cards_seen": 10,
  "cards_returned": 8,
  "pages_visited": 1,
  "action_trace_ref": "artifact://protected/pi-trace/run-123",
  "safe_summary_refs": [],
  "protected_snapshot_refs": ["artifact://protected/pi-snapshot/run-123/page-1"],
  "cards": [
    {
      "provider_rank": 1,
      "provider_candidate_key_material_ref": "artifact://protected/pi-provider-key/run-123/1",
      "candidate_resume_id": "liepin-card-1",
      "display_name_masked": true,
      "safe_card_summary": {
        "display_title": "Senior Backend Engineer",
        "current_or_recent_company": "Example Inc",
        "current_or_recent_title": "Senior Backend Engineer",
        "work_years": 8,
        "age": 33,
        "city": "Shanghai",
        "expected_city": "Shanghai",
        "education_level": "master",
        "school_names": ["Shanghai Jiao Tong University"],
        "major_names": ["Computer Science"],
        "skill_tags": ["Python", "Search", "Ranking"],
        "job_intention": "Backend Engineer",
        "recent_experience_text": "Built ranking services",
        "normalized_card_text": "Senior backend engineer Python search ranking"
      },
      "safe_card_summary_ref": "artifact://public-summary/pi-card/run-123/1",
      "protected_snapshot_ref": "artifact://protected/pi-card-snapshot/run-123/1"
    }
  ]
}
```

Allowed statuses:

- `succeeded`
- `partial`
- `blocked`
- `failed`

Allowed stop reasons:

- `completed`
- `partial_timeout`
- `blocked_pi_unavailable`
- `blocked_dokobot_unavailable`
- `blocked_dokobot_tool_unavailable`
- `blocked_permission_required`
- `blocked_login_required`
- `blocked_risk_control`
- `blocked_unsupported_route`
- `blocked_budget_exhausted`
- `failed_malformed_output`
- `failed_provider_error`
- `failed_internal_error`

Public Runtime payloads must map these into existing Runtime safe reason codes. Raw Pi stderr, natural language explanations, provider page text, and exception messages must be stored only in protected diagnostics when needed.

The provider boundary may keep the original Pi stop reason for private diagnostics and typed control flow, but `safe_reason_code` values exposed to Runtime events, Workbench graph/notes, CLI, or logs must be normalized to the Runtime allowlist. In this slice:

- Pi/DokoBot unavailable -> `blocked_backend_unavailable`
- login missing -> `blocked_login_required`
- permission, risk-control, verification, or UI request denied -> `blocked_compliance`
- budget exhausted -> `blocked_budget_exhausted`
- timeout with usable partial cards -> `partial_timeout`
- RPC timeout before a strict final envelope with usable cards -> `failed_provider_error`
- malformed Pi output, unsupported route, process failure, prompt rejection, or missing `agent_end` -> `failed_provider_error`

Pi must not compute public HMACs and must not receive Runtime or tenant-scoped HMAC secrets. Pi returns protected observed provider-key material refs and safe card summaries. SeekTalent resolves those protected refs through a local artifact registry/material resolver inside the provider boundary and computes `provider_candidate_key_hash`, `provider_account_hash`, and any Runtime identity keys.

## Configuration

Use a new live worker mode:

```text
SEEKTALENT_LIEPIN_WORKER_MODE=pi_agent
```

Minimum supporting settings:

- `SEEKTALENT_LIEPIN_PI_COMMAND`
- `SEEKTALENT_LIEPIN_PI_TIMEOUT_SECONDS`
- `SEEKTALENT_LIEPIN_PI_SKILL_PATH`
- `SEEKTALENT_LIEPIN_PI_DOKOBOT_TOOL_NAME`

Rules:

- default remains `disabled`
- `pi_agent` requires an explicit Pi command that resolves to RPC mode
- `pi_agent` requires a configured Liepin skill asset path
- `pi_agent` requires the expected DokoBot tool name for the Pi environment
- worker construction appends or verifies `--skill <path>` and rejects a missing/unreadable skill
- worker construction rejects commands without `--mode rpc` or `--no-session`
- missing or invalid `pi_agent` config fails closed at settings construction or worker-client construction before source-lane execution
- no automatic fallback to `managed_local`, `external_http`, `fake_fixture`, or `dokobot_action`

## Connection And Login Semantics

Workbench may still require a connected Liepin source connection before starting a live Liepin lane. For `pi_agent`, connection verification is a Pi task:

```text
Runtime/Workbench asks provider client to verify connection
  -> Pi receives a "detect login/risk state" task
  -> Pi uses DokoBot inside its runtime
  -> Pi returns safe account/session metadata
  -> Workbench store persists connected state and provider-account hash
```

The account hash must be computed by SeekTalent from visible account metadata or provider-safe account identifiers stored behind protected refs. Pi must not receive the HMAC secret and must not invent the public hash. The public account hash must not expose cookies, session ids, phone numbers, emails, or raw account strings.

If login is missing, verification challenge appears, DokoBot is unavailable, or Pi cannot run, connection is blocked with a safe reason. The UI should show the source as not ready; it should not ask Codex to operate the browser.

The session probe returns a strict envelope:

```json
{
  "schema_version": "seektalent.pi_liepin_session_probe.v1",
  "status": "ready",
  "connection_id": "liepin-pi-agent",
  "provider_account_material_ref": "artifact://protected/pi-account/run-123/current",
  "page_origin": "https://www.liepin.com",
  "stop_reason": null
}
```

Allowed statuses:

- `ready`
- `login_required`
- `risk_control`
- `blocked`
- `failed`

Allowed stop reasons:

- `blocked_pi_unavailable`
- `blocked_dokobot_unavailable`
- `blocked_dokobot_tool_unavailable`
- `blocked_permission_required`
- `blocked_login_required`
- `blocked_risk_control`
- `failed_malformed_output`
- `failed_provider_error`
- `failed_internal_error`

`ready` requires a non-empty `provider_account_material_ref`; SeekTalent hashes that protected material into `provider_account_hash` before returning the existing `LiepinWorkerClient.session_status()` contract. Other statuses must not include account identifiers or account material refs.

## Card Decision Policy

The existing policy direction remains valid:

- preserve provider rank
- reject obvious mismatches
- hold weak card signals
- recommend within budget

The first version should use deterministic card checks over the safe card summary. Pi's general-agent strength is used for navigation and extraction variability, not final budget policy.

Hard reject examples:

- role family is plainly wrong
- must-have query terms have zero overlap and title/company/history do not compensate
- city is incompatible with a hard location requirement
- education/work-years are obviously outside hard user constraints when those constraints exist

Hold examples:

- card text too sparse
- masked identity with no distinctive experience
- title looks adjacent but there is no skill or experience support

Recommendation examples:

- current/recent title and card text overlap the target role
- key technologies, domain terms, or school/work chronology strongly match
- provider rank is high and no hard filter triggered

## Budgets

Runtime budget settings control Pi:

- `liepin_card_page_size`
- `liepin_max_cards`
- `liepin_max_detail_recommendations`
- `liepin_max_detail_opens_per_run`

Pi may not exceed these limits. It should stop when the card budget is exhausted and return `blocked_budget_exhausted` only when budget prevents further useful work. If it returns valid cards before the stop, Runtime may merge partial evidence and mark coverage as partial.

## Detail Open Boundary

Card search mode never opens detail pages.

This must be observable, not only asserted in the prompt. The protected action trace for card mode must be materialized locally and parsed by SeekTalent. It must not contain detail-route classifications, detail-tab clicks, contact-button interactions, or detail-page artifact refs. A card-mode output with valid cards but a materialized trace that shows detail navigation fails closed even if the artifact ref string itself looks harmless.

Detail opening remains a separate two-stage boundary:

1. Runtime emits detail recommendations from card evidence.
2. Workbench owns approval, approved detail lease, budget ledger, and audit.
3. Runtime may run a detail lane only with an approved lease.
4. Pi may open a detail page only when the task includes a validated approved lease.

Manual approval UI is outside this first Pi executor slice, but the boundary must remain intact.

`display_name_masked` is part of the card evidence contract. Runtime mapping must carry it into the existing safe-card summary shape as `masked_name` so later card policy and conservative identity merge logic can treat masked Liepin identities as weak identity evidence.

## Security And Compliance

Required fail-closed cases:

- Pi command missing
- Pi command cannot start
- Pi exits non-zero
- Pi output has no final JSON envelope
- Pi final output contains prose, Markdown fences, or multiple top-level payloads around the JSON
- Pi output fails schema validation
- Pi prompt command response is unsuccessful
- Pi emits a UI/input/confirmation request during a production provider task
- Pi reports DokoBot unavailable
- Pi cannot prove DokoBot action capability through a trusted manifest or observed tool evidence
- Pi reports login required
- Pi reports risk/verification challenge
- Pi returns cards with forbidden raw fields
- Pi returns detail data in card mode
- Pi returns card-mode traces showing detail navigation
- Pi exceeds configured budget

Forbidden data in public payloads:

- cookies
- session ids
- access tokens
- approval secrets
- raw HTML
- raw browser storage
- raw provider responses
- hidden contact information
- direct phone/email/contact material
- natural-language exception text

Allowed public payloads:

- safe enum reason codes
- counts
- provider ranks
- safe card summaries
- public summary refs
- protected artifact refs by id only

The first implementation must include a minimal local artifact registry/material resolver that fails closed on missing refs. Richer retention, protected-open audit, and UI access policy can remain deferred.

SafePayloadFirewall must reject or quarantine:

- free-text phone, email, WeChat-like contact, token, cookie, localStorage/sessionStorage, HTML/script fragments, and raw exception patterns
- artifact refs with unsupported schemes, path traversal, external URLs, or missing registry records
- safe reason values outside enum allowlists
- output where `cards_returned != len(cards)`, `pages_visited > max_pages`, `cards_returned > max_cards`, duplicate provider ranks, mismatched `source_run_id`, or mismatched query

## Acceptance Criteria

1. `SEEKTALENT_LIEPIN_WORKER_MODE=pi_agent` is the only live Pi-based Liepin browser mode.
2. The old `dokobot_action` live path is removed from production configuration and factory dispatch.
3. Runtime and Workbench do not import DokoBot action modules.
4. The Pi adapter uses documented Pi RPC/JSONL mode, not an invented CLI command.
5. Pi unavailable produces a blocked Liepin lane with a safe reason code and no fallback.
6. DokoBot unavailable inside Pi produces a blocked Liepin lane with a safe reason code and no fallback.
7. A Pi capability probe proves DokoBot read/click/type capability with trusted manifest or observed tool evidence before live search.
8. A Pi session probe backs Workbench's connected Liepin source gate and returns only protected account material that SeekTalent hashes when ready.
9. Malformed Pi JSON produces a failed/blocked typed result and never merges cards.
10. Partial Pi output with valid cards preserves those cards and marks coverage partial.
11. Card mode cannot open detail pages, and action trace validation enforces this.
12. Detail mode can only be planned around an approved detail lease boundary.
13. Safe card summaries feed the existing provider-rank-first card decision policy.
14. CTS and Liepin evidence still merge into one Runtime identity/candidate pool and one final Top 10.
15. Tests prove the product path does not depend on Codex's `dokobot` skill.
16. Static checks show no production import path from Runtime/Workbench to old DokoBot action surface modules.
17. Configuration docs describe Pi and DokoBot as product runtime dependencies, not Codex tools.
18. Tests cover prompt rejection, timeout before `agent_end`, UI request denial, strict JSON extra text rejection, business invariant rejection, Runtime-owned HMAC mapping, SafePayloadFirewall rejection, and card-mode detail-route trace rejection.
19. Tests cover Pi artifact root propagation, materialized local artifact resolution, and missing artifact fail-closed behavior.

## Out Of Scope

- installing Pi for the user
- installing DokoBot MCP
- implementing a manual card-review UI
- implementing manual detail approval UI
- switching to Claude Code or Skyvern
- introducing A2A
- building a generic source plugin marketplace
- using Codex MCP tools as production execution machinery

## External Interface References

- Pi RPC mode: `https://pi.dev/docs/latest/rpc`
- Pi skills: `https://pi.dev/docs/latest/skills`
- Pi usage modes: `https://pi.dev/docs/latest/usage`
