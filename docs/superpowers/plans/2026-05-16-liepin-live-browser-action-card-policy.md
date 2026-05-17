# Liepin Live Browser Action And Card Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Liepin live card search through the PI Agent / DokoBot action boundary and replace the current matched-term detail recommendation helper with a provider-rank-first card decision policy that filters only obvious mismatches and spends detail recommendation budget deterministically.

**Architecture:** SeekTalent Runtime owns source budgets, card decision policy, detail recommendations, and final ranking. PI Agent owns bounded provider execution. DokoBot MCP / compatible action backend is used only behind PI Agent / `LiepinPiRunner`, not by Runtime or Workbench directly. DokoBot action mode must fail closed unless a trusted local action manifest, concrete action transport binding, and explicit card executor are configured.

**Tech Stack:** Python 3.12, pytest, ruff, existing `seektalent.runtime.source_lanes`, `seektalent.providers.liepin`, and `seektalent.providers.pi_agent` modules.

---

## Spec Link

This plan implements:

`docs/superpowers/specs/2026-05-16-liepin-live-browser-action-card-policy-design.md`

It builds on:

- `docs/superpowers/specs/2026-05-13-provider-interaction-agent-dokobot-design.md`
- `docs/superpowers/specs/2026-05-15-runtime-multi-source-pi-agent-source-lane-design.md`

## Execution Notes

- Do not confuse Codex-side tools with product runtime capability. DokoBot MCP/action support here belongs to SeekTalent runtime configuration.
- Do not push, merge, or release as part of this plan.
- Use tests first for each behavioral change.
- Keep the first implementation deterministic-first. PI/LLM can be added only as strict JSON classification for uncertain safe card summaries.
- Preserve provider rank as the primary order for detail recommendations.
- Keep DokoBot read-only client read-only. Add a separate action executor seam.
- Complete means the product path can select and execute `dokobot_action` through settings, provider registry, Workbench source-run plumbing, PI Agent, and DokoBot action transport. A protocol-only seam is not complete.
- A search-only PI worker client is not complete. `dokobot_action` must also support Workbench connection verification from the user's already logged-in local browser session, because current Workbench source-run start requires a connected Liepin source connection.
- If a concrete DokoBot MCP/action transport binding cannot be discovered or implemented locally, the build must report blocked; do not mark the plan complete and move transport binding to TODO.
- Do not add browser cookie export, direct API replay, network interception, in-page script execution, stealth/proxy code, or fallback chains.
- Keep Workbench out of provider execution logic.

## File Map

Modify:

- `src/seektalent/providers/liepin/pi_runner.py`
  - add `LiepinPiCardSearchResult`
  - change `SearchCardsExecutor` and `LiepinPiRunner.search_cards()` to return the wrapper result
  - pass explicit `page_size`, `max_pages`, and `max_cards` to the PI executor
  - keep lock/fail-closed/no-fallback behavior

- `src/seektalent/config.py`
  - add explicit `dokobot_action` Liepin worker mode or an equivalent PI-agent backend selector
  - add trusted DokoBot action manifest configuration needed to build the product runtime path
  - validate that `dokobot_action` cannot run without the trusted action manifest inputs

- `.env.example` and `src/seektalent/default.env`
  - document `dokobot_action` as the PI Agent browser-action backend
  - keep `disabled` as default

- `src/seektalent/providers/liepin/client.py`
  - build the PI-backed `LiepinWorkerClient` for `dokobot_action`
  - expose or move a public card-response-to-`SearchResult` mapping helper instead of depending on a private helper
  - define or import a single live-mode predicate/constant used by client, adapter, registry, and runtime lane

- `src/seektalent/providers/registry.py`
  - treat `dokobot_action` as a live Liepin mode that still needs `LiepinStore` connection safety
  - do not import DokoBot into Runtime or Workbench

- `src/seektalent/providers/liepin/adapter.py`
  - include `dokobot_action` in the live compliance/session safety branch
  - require a compliance store, ready session, provider-account binding, and provider connection safety for `dokobot_action`

- `src/seektalent/providers/liepin/runtime_lane.py`
  - call the new card policy helper
  - preserve provider rank after hard filters
  - emit detail recommendation reason codes from policy decisions
  - keep safe public payloads
  - pass `liepin_max_cards` and derived `liepin_max_pages` into provider context
  - convert PI/DokoBot blocked worker errors into safe blocked lane results instead of raw failed jobs

- `src/seektalent/providers/liepin/card_policy.py`
  - add safe card summary and card decision contracts
  - keep card policy separate from legacy detail-open grant helpers in `policy.py`

- `src/seektalent/providers/liepin/worker_contracts.py`
  - add an optional allowlisted safe card summary model/field for card business decisions

- `src/seektalent/providers/liepin/mapper.py`
  - map allowlisted safe card summary into `ResumeCandidate.raw["safe_card_summary"]`
  - do not copy raw provider payload fields into candidate raw

- `src/seektalent/providers/liepin/pi_worker_client.py`
  - adapt `LiepinPiRunner` card search results to the existing `LiepinWorkerClient` protocol
  - implement the connection/session methods needed by Workbench for `dokobot_action`, not only `search()`
  - keep blocking PI calls out of the async event loop via async transport or `asyncio.to_thread()`

- `src/seektalent/providers/liepin/dokobot_actions.py`
  - implement the PI Agent Liepin DokoBot action executor with pagination, login/risk stops, and typed result mapping
  - populate typed `safeCardSummary` for DokoBot-action cards from visible card data

- `src/seektalent/providers/pi_agent/dokobot_action_transport.py` or equivalent existing PI-agent module
  - bind the concrete DokoBot MCP/action transport used by SeekTalent runtime
  - keep the read-only `DokoBotClient` separate

- `src/seektalent/providers/pi_agent/capabilities.py`
  - add only narrow helper properties if needed for DokoBot action executor wiring

- `src/seektalent_ui/runtime_bridge.py`
  - keep Workbench source-run entrypoint unchanged at the business level
  - ensure injected or configured `LiepinWorkerClient` can be the PI-backed `dokobot_action` client without Workbench importing DokoBot

- `src/seektalent_ui/workbench_routes.py`
  - support the existing Liepin connection flow for `dokobot_action` by verifying the already logged-in browser session through the worker-client contract
  - do not import DokoBot or PI-agent transport modules

- `src/seektalent_ui/workbench_store.py`
  - preserve the current connected-source-run gate
  - ensure `dokobot_action` verification records the provider-account hash and session metadata needed by provider connection safety

- `TODOS.md`
  - update the deferred multi-source follow-up list to remove concrete transport binding from deferred work once this plan owns it

Add:

- `tests/test_liepin_card_policy.py`
- `tests/test_liepin_pi_card_search_result.py`
- `tests/test_liepin_pi_worker_client.py`
- `tests/test_liepin_dokobot_actions.py`

Modify tests:

- `tests/test_config.py` or the nearest existing settings tests
- `tests/test_liepin_pi_runner.py`
- `tests/test_liepin_runtime_source_lane.py`
- `tests/test_dokobot_capabilities.py` only if action capability helpers change
- `tests/test_runtime_source_lanes.py` only if public reason-code allowlists need new values
- `tests/test_provider_registry.py`
- `tests/test_liepin_provider_adapter.py`
- `tests/test_workbench_api.py` or `tests/test_workbench_source_runs.py` if present

## What Already Exists

- `DokoBotCapabilities.can_execute_liepin_actions` already requires trusted local action manifest, read, click, type, navigation, and pagination.
- `LiepinPiRunner` already owns backend mode dispatch and connection/provider-account locks.
- `LiepinWorkerCandidateCard` and `LiepinCardSearchResponse` already provide typed card payloads.
- `run_liepin_source_lane()` already has card and detail lane modes.
- `RuntimeDetailRecommendation` already carries `provider_rank`, `card_policy_rank`, `hard_filter_status`, `budget_reason_code`, and `safe_reason_codes`.
- `RuntimeSourceBudgetPolicy` already has `liepin_card_page_size`, `liepin_max_cards`, `liepin_max_detail_recommendations`, and `liepin_max_detail_opens_per_run`.
- `AppSettings.liepin_worker_mode`, `build_liepin_worker_client()`, and provider registry do not yet expose `dokobot_action`; this plan must add that wiring.
- `map_liepin_worker_card()` currently puts safe provider metadata into `ResumeCandidate.raw`, but not structured card business fields; this plan must add an allowlisted `safe_card_summary` path.
- Workbench source-run start currently blocks Liepin until the source connection is `connected` with provider-account state; this plan must add the PI-backed connection verification path, otherwise live search remains unreachable from Workbench.
- `LiepinProviderAdapter.search()` currently treats only `managed_local` and `external_http` as live modes; this plan must put `dokobot_action` through the same compliance/session safety path.

## NOT In Scope

- Human card-review UI
- Manual detail approval UI
- A2A
- generic source plugin marketplace
- automatic DokoBot install or permission mutation
- switching live execution to Codex MCP tools
- direct provider API replay
- final Top 10 ranking changes beyond consuming existing Runtime detail recommendations
- leaving concrete DokoBot MCP/action transport binding as a TODO while claiming live Liepin card search is implemented

## Required Product Path

The final implementation must make this path work in tests:

```text
Workbench Liepin source run
  -> verified connected Liepin source connection
  -> RuntimeSourceLaneRequest(source="liepin", lane_mode="card")
  -> LiepinProviderAdapter
  -> LiepinPiWorkerClient
  -> LiepinPiRunner(backend_mode=DOKOBOT_ACTION)
  -> PI Agent DokoBot action executor
  -> DokoBot MCP/action transport
  -> LiepinCardSearchResponse
  -> SearchResult
  -> RuntimeDetailRecommendation
```

Forbidden path:

```text
Runtime or Workbench -> DokoBot client / browser action
```

Runtime and Workbench consume typed provider contracts only. DokoBot remains PI Agent execution machinery.

## Tasks

- [x] **Task 1: Add failing tests for provider-rank-first card policy**

Create `tests/test_liepin_card_policy.py`:

```python
from __future__ import annotations

from seektalent.providers.liepin.card_policy import (
    LiepinCardDecisionAction,
    LiepinCardSummary,
    build_liepin_card_decisions,
)


def _summary(
    candidate_id: str,
    provider_rank: int,
    text: str,
    *,
    title: str | None = None,
    company: str | None = None,
    city: str | None = None,
    skills: tuple[str, ...] = (),
) -> LiepinCardSummary:
    return LiepinCardSummary(
        candidate_resume_id=candidate_id,
        provider_rank=provider_rank,
        current_or_recent_company=company,
        current_or_recent_title=title,
        city=city,
        skill_tags=skills,
        normalized_card_text=text,
    )


def test_provider_rank_is_primary_after_hard_filters_and_budget() -> None:
    decisions = build_liepin_card_decisions(
        cards=[
            _summary("rank-1", 1, "FastAPI ranking platform", title="Backend Engineer", skills=("FastAPI",)),
            _summary("rank-2", 2, "store sales manager", title="Store Manager"),
            _summary("rank-3", 3, "FastAPI search services", title="Python Engineer", skills=("Python",)),
            _summary("rank-4", 4, "FastAPI distributed systems", title="Backend Engineer"),
        ],
        query_terms=("FastAPI", "ranking"),
        role_title="Backend Engineer",
        max_detail_recommendations=2,
    )

    recommended = [item for item in decisions if item.action == LiepinCardDecisionAction.RECOMMEND_DETAIL]

    assert [item.candidate_resume_id for item in recommended] == ["rank-1", "rank-3"]
    assert [item.provider_rank for item in recommended] == [1, 3]
    assert [item.card_policy_rank for item in recommended] == [1, 2]
    assert decisions[1].action == LiepinCardDecisionAction.REJECT_OBVIOUS_MISMATCH
    assert "obvious_role_mismatch" in decisions[1].reason_codes


def test_missing_card_fields_hold_instead_of_recommending_detail() -> None:
    decisions = build_liepin_card_decisions(
        cards=[
            _summary("thin-card", 1, "engineer"),
        ],
        query_terms=("FastAPI", "ranking"),
        role_title="Backend Engineer",
        max_detail_recommendations=1,
    )

    assert decisions[0].action == LiepinCardDecisionAction.HOLD_INSUFFICIENT_CARD_SIGNAL
    assert decisions[0].budget_reason_code == "insufficient_card_signal"


def test_obvious_mismatch_does_not_consume_recommendation_budget() -> None:
    decisions = build_liepin_card_decisions(
        cards=[
            _summary("wrong", 1, "retail sales store manager", title="Store Manager"),
            _summary("right", 2, "FastAPI ranking backend services", title="Backend Engineer"),
        ],
        query_terms=("FastAPI", "ranking"),
        role_title="Backend Engineer",
        max_detail_recommendations=1,
    )

    recommended = [item for item in decisions if item.action == LiepinCardDecisionAction.RECOMMEND_DETAIL]

    assert [item.candidate_resume_id for item in recommended] == ["right"]
```

Run and confirm failure:

```bash
uv run pytest tests/test_liepin_card_policy.py -q
```

- [x] **Task 2: Implement safe Liepin card summary and decision policy**

Create `src/seektalent/providers/liepin/card_policy.py`. Keep legacy detail-open grant helpers in `src/seektalent/providers/liepin/policy.py`. If older call sites need compatibility, re-export the new card-policy names from `policy.py`, but do not mix the new card decision logic into the legacy detail-open grant file.

Add:

```python
from enum import StrEnum


class LiepinCardDecisionAction(StrEnum):
    RECOMMEND_DETAIL = "recommend_detail"
    REJECT_OBVIOUS_MISMATCH = "reject_obvious_mismatch"
    HOLD_INSUFFICIENT_CARD_SIGNAL = "hold_insufficient_card_signal"


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


@dataclass(frozen=True, kw_only=True)
class LiepinCardDecision:
    candidate_resume_id: str
    provider_rank: int
    card_policy_rank: int | None
    action: LiepinCardDecisionAction
    value_score: int | None
    hard_filter_status: str
    budget_reason_code: str
    reason_codes: tuple[str, ...]
```

Add the policy:

```python
def build_liepin_card_decisions(
    *,
    cards: list[LiepinCardSummary],
    query_terms: tuple[str, ...],
    role_title: str,
    max_detail_recommendations: int,
) -> list[LiepinCardDecision]:
    remaining = max(0, max_detail_recommendations)
    card_policy_rank = 0
    decisions: list[LiepinCardDecision] = []
    for card in sorted(cards, key=lambda item: item.provider_rank):
        hard_reject = _hard_reject_reason(card=card, query_terms=query_terms, role_title=role_title)
        if hard_reject is not None:
            decisions.append(
                LiepinCardDecision(
                    candidate_resume_id=card.candidate_resume_id,
                    provider_rank=card.provider_rank,
                    card_policy_rank=None,
                    action=LiepinCardDecisionAction.REJECT_OBVIOUS_MISMATCH,
                    value_score=0,
                    hard_filter_status=hard_reject,
                    budget_reason_code=hard_reject,
                    reason_codes=(hard_reject,),
                )
            )
            continue

        score, reasons = _card_signal_score(card=card, query_terms=query_terms, role_title=role_title)
        if score < 2:
            decisions.append(
                LiepinCardDecision(
                    candidate_resume_id=card.candidate_resume_id,
                    provider_rank=card.provider_rank,
                    card_policy_rank=None,
                    action=LiepinCardDecisionAction.HOLD_INSUFFICIENT_CARD_SIGNAL,
                    value_score=score * 20,
                    hard_filter_status="hard_filter_passed",
                    budget_reason_code="insufficient_card_signal",
                    reason_codes=("hard_filter_passed", "insufficient_card_signal"),
                )
            )
            continue

        if card_policy_rank >= remaining:
            decisions.append(
                LiepinCardDecision(
                    candidate_resume_id=card.candidate_resume_id,
                    provider_rank=card.provider_rank,
                    card_policy_rank=None,
                    action=LiepinCardDecisionAction.HOLD_INSUFFICIENT_CARD_SIGNAL,
                    value_score=min(100, 40 + score * 15),
                    hard_filter_status="hard_filter_passed",
                    budget_reason_code="blocked_budget_exhausted",
                    reason_codes=("hard_filter_passed", "blocked_budget_exhausted"),
                )
            )
            continue

        card_policy_rank += 1
        decisions.append(
            LiepinCardDecision(
                candidate_resume_id=card.candidate_resume_id,
                provider_rank=card.provider_rank,
                card_policy_rank=card_policy_rank,
                action=LiepinCardDecisionAction.RECOMMEND_DETAIL,
                value_score=min(100, 40 + score * 15),
                hard_filter_status="hard_filter_passed",
                budget_reason_code="within_run_detail_budget",
                reason_codes=(
                    "hard_filter_passed",
                    "provider_rank_preserved",
                    "card_rank_budget",
                    "within_run_detail_budget",
                    *reasons,
                ),
            )
        )
    return decisions
```

Keep `_hard_reject_reason()` conservative. It should reject obvious wrong-role cards such as retail/sales/store manager when role title/query terms indicate engineering. Missing fields should not become a reject.

Update `src/seektalent/runtime/source_lanes.py` `_SAFE_REASON_CODES` with new enum values:

```python
"obvious_role_mismatch",
"must_have_zero_overlap",
"hard_location_mismatch",
"hard_education_mismatch",
"insufficient_card_signal",
```

Add or extend `tests/test_runtime_source_lanes.py` to assert these new card-policy reason codes survive `RuntimeDetailRecommendation.to_public_payload()` and do not sanitize to `unknown_reason`.

Run:

```bash
uv run pytest tests/test_liepin_card_policy.py tests/test_runtime_source_lanes.py -q
uv run ruff check src/seektalent/providers/liepin/card_policy.py src/seektalent/providers/liepin/policy.py src/seektalent/runtime/source_lanes.py tests/test_liepin_card_policy.py tests/test_runtime_source_lanes.py
```

- [x] **Task 3: Add allowlisted safe card summary mapping**

The runtime card policy must not scrape arbitrary provider payloads from `ResumeCandidate.raw`. Add an explicit safe summary path.

Modify `src/seektalent/providers/liepin/worker_contracts.py`:

```python
class LiepinSafeCardSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    masked_name: bool = False


class LiepinWorkerCandidateCard(BaseModel):
    ...
    safe_card_summary: LiepinSafeCardSummary | None = Field(default=None, alias="safeCardSummary")
```

Keep the field optional in the shared worker contract for fixture and legacy worker compatibility. DokoBot action-produced cards must populate it. Tests for the DokoBot executor should assert every returned card has `safe_card_summary is not None`.

Modify `src/seektalent/providers/liepin/mapper.py` so `_safe_raw()` includes only the allowlisted summary:

```python
summary = worker_candidate.safe_card_summary.model_dump(mode="json") if (
    isinstance(worker_candidate, LiepinWorkerCandidateCard) and worker_candidate.safe_card_summary is not None
) else None
raw = {
    ...
    "safe_card_summary": summary,
}
```

If the DokoBot action executor or legacy worker cannot populate `safe_card_summary`, mapper should leave it `None`; runtime card policy may still use `candidate.search_text` as normalized card text, but must not read raw provider payload keys such as `title`, `company`, `skills`, or raw HTML.

For DokoBot action mode, failure to populate `safeCardSummary` should be treated as an executor bug or partial/blocked extraction outcome. Do not make Runtime compensate by scraping arbitrary fields out of `payload`.

Tests:

- `LiepinWorkerCandidateCard` accepts allowlisted `safeCardSummary`.
- unknown fields inside `safeCardSummary` are rejected.
- mapper writes `safe_card_summary` to `ResumeCandidate.raw`.
- mapper does not copy raw provider payload fields or direct contact material into `safe_card_summary`.
- DokoBot action-produced cards require `safeCardSummary` and reject raw contact/browser fields in that summary.

Run:

```bash
uv run pytest tests/test_liepin_provider_adapter.py tests/test_liepin_runtime_source_lane.py -q
uv run ruff check src/seektalent/providers/liepin/worker_contracts.py src/seektalent/providers/liepin/mapper.py tests/test_liepin_provider_adapter.py tests/test_liepin_runtime_source_lane.py
```

- [x] **Task 4: Apply card policy inside Liepin runtime card lane**

Modify `src/seektalent/providers/liepin/runtime_lane.py`.

Replace `_detail_recommendations_for_candidates()` term-count logic with summary creation plus policy decisions:

```python
from seektalent.providers.liepin.card_policy import (
    LiepinCardDecisionAction,
    LiepinCardSummary,
    build_liepin_card_decisions,
)
```

Add:

```python
def _card_summary_for_candidate(*, candidate: ResumeCandidate, provider_rank: int) -> LiepinCardSummary:
    raw = candidate.raw if isinstance(candidate.raw, dict) else {}
    summary = raw.get("safe_card_summary") if isinstance(raw.get("safe_card_summary"), dict) else {}
    return LiepinCardSummary(
        candidate_resume_id=candidate.resume_id,
        provider_rank=provider_rank,
        display_title=_raw_text(summary, "display_title"),
        current_or_recent_company=_raw_text(summary, "current_or_recent_company"),
        current_or_recent_title=_raw_text(summary, "current_or_recent_title"),
        city=_raw_text(summary, "city"),
        expected_city=_raw_text(summary, "expected_city"),
        education_level=_raw_text(summary, "education_level"),
        school_names=_raw_tuple(summary, "school_names"),
        major_names=_raw_tuple(summary, "major_names"),
        skill_tags=_raw_tuple(summary, "skill_tags"),
        job_intention=_raw_text(summary, "job_intention"),
        recent_experience_text=_raw_text(summary, "recent_experience_text"),
        normalized_card_text=candidate.search_text,
        masked_name=bool(summary.get("masked_name")) if isinstance(summary, dict) else False,
    )
```

Then:

```python
decisions = build_liepin_card_decisions(
    cards=[
        _card_summary_for_candidate(candidate=candidate, provider_rank=evidence.provider_rank or index)
        for index, (candidate, evidence) in enumerate(zip(candidates, evidence_updates, strict=True), start=1)
    ],
    query_terms=tuple(query_terms),
    role_title=role_title,
    max_detail_recommendations=max_recommendations,
)
decision_by_resume_id = {decision.candidate_resume_id: decision for decision in decisions}
```

Create recommendations only for `RECOMMEND_DETAIL`. Do not include `safe_reason` free text:

```python
if decision.action != LiepinCardDecisionAction.RECOMMEND_DETAIL:
    continue
RuntimeDetailRecommendation(
    recommendation_id=f"{source_plan_id}:detail:{candidate.resume_id}",
    source="liepin",
    source_evidence_id=evidence.evidence_id,
    candidate_resume_id=candidate.resume_id,
    provider_candidate_key_hash=evidence.provider_candidate_key_hash,
    value_score=decision.value_score,
    provider_rank=decision.provider_rank,
    card_policy_rank=decision.card_policy_rank,
    hard_filter_status=decision.hard_filter_status,
    budget_reason_code=decision.budget_reason_code,
    reason_code="provider_rank_preserved",
    safe_reason_codes=decision.reason_codes,
    provider_snapshot_ref=evidence.provider_snapshot_ref,
    safe_summary_ref=evidence.safe_summary_ref,
    budget_policy_version=budget_policy_version,
)
```

Update tests in `tests/test_liepin_runtime_source_lane.py`:

- high-rank obvious mismatch is skipped
- lower-rank matching card uses the freed budget
- missing-field thin card is held
- public payload does not include raw card text or free-form `safe_reason`
- public payload preserves allowlisted card-policy reason codes and never turns them into `unknown_reason`
- runtime policy reads `safe_card_summary` only and does not inspect arbitrary raw provider payload keys

Run:

```bash
uv run pytest tests/test_liepin_card_policy.py tests/test_liepin_runtime_source_lane.py tests/test_runtime_source_lanes.py -q
uv run ruff check src/seektalent/providers/liepin/runtime_lane.py tests/test_liepin_runtime_source_lane.py tests/test_runtime_source_lanes.py
```

- [x] **Task 5: Add PI card-search result wrapper tests**

Add `tests/test_liepin_pi_card_search_result.py` for wrapper contract tests. Keep `tests/test_liepin_pi_runner.py` for runner integration behavior so final verification has one stable file path.

Add tests:

```python
from seektalent.providers.liepin.worker_contracts import LiepinCardSearchResponse, LiepinWorkerCandidateCard


def _card_response() -> LiepinCardSearchResponse:
    return LiepinCardSearchResponse(
        cards=[
            LiepinWorkerCandidateCard(
                payload={"safe_summary_ref": "artifact://summary/liepin/card-1"},
                normalized_text="FastAPI ranking platform",
                provider_subject_id="provider-1",
                synthetic_candidate_fingerprint="fingerprint-1",
                identity_confidence="provider_subject_id",
                extraction_source="dom_fallback",
                extractor_version="test",
                pii_classification="no_direct_contact",
                retention_policy="provider_snapshot_7d",
                access_scope="local_run_only",
                redaction_state="redacted",
            )
        ],
        raw_candidate_count=1,
    )


def test_dokobot_action_search_cards_returns_pi_result_and_typed_cards() -> None:
    def dokobot_search_cards(**kwargs: object) -> LiepinPiCardSearchResult:
        return LiepinPiCardSearchResult(
            pi_result=PiAgentResult(
                schema_version="pi-agent-result-v1",
                status=PiAgentResultStatus.SUCCEEDED,
                action_trace_ref=_trace_writer(
                    b'{"schema_version":"pi-agent-action-trace-v1","interaction_id":"trace_ok"}',
                    ProtectedArtifactClass.REDACTED_EVIDENCE,
                    "liepin-trace-redaction-v1",
                ),
            ),
            card_search=_card_response(),
        )

    runner = _runner(
        backend_mode=PiBackendMode.DOKOBOT_ACTION,
        capabilities=_capabilities(action=True),
        dokobot_search_cards=dokobot_search_cards,
    )

    result = runner.search_cards(**SEARCH_KWARGS)

    assert result.status == PiAgentResultStatus.SUCCEEDED
    assert result.card_search is not None
    assert result.card_search.cards[0].normalized_text == "FastAPI ranking platform"


def test_successful_pi_card_search_requires_card_response() -> None:
    with pytest.raises(ValueError, match="card_search is required"):
        LiepinPiCardSearchResult(
            pi_result=PiAgentResult(
                schema_version="pi-agent-result-v1",
                status=PiAgentResultStatus.SUCCEEDED,
                action_trace_ref=_trace_writer(
                    b'{"schema_version":"pi-agent-action-trace-v1","interaction_id":"trace_ok"}',
                    ProtectedArtifactClass.REDACTED_EVIDENCE,
                    "liepin-trace-redaction-v1",
                ),
            )
        )
```

Existing tests that assert `runner.search_cards(...).status` should continue to work through the wrapper's `status` property, but update any direct `PiAgentResult` assumptions.

Run and confirm failure:

```bash
uv run pytest tests/test_liepin_pi_card_search_result.py tests/test_liepin_pi_runner.py -q
```

- [x] **Task 6: Implement `LiepinPiCardSearchResult` and update runner return types**

Modify `src/seektalent/providers/liepin/pi_runner.py`.

Add imports:

```python
from seektalent.providers.pi_agent.contracts import PiAgentCompletionReason
from seektalent.providers.liepin.worker_contracts import LiepinCardSearchResponse
```

Add:

```python
@dataclass(frozen=True, kw_only=True)
class LiepinPiCardSearchResult:
    pi_result: PiAgentResult
    card_search: LiepinCardSearchResponse | None = None

    def __post_init__(self) -> None:
        if self.pi_result.status == PiAgentResultStatus.SUCCEEDED and self.card_search is None:
            raise ValueError("card_search is required for successful Liepin PI card search")

    @property
    def status(self) -> PiAgentResultStatus:
        return self.pi_result.status

    @property
    def stop_reason(self) -> PiAgentFailureCode | PiAgentCompletionReason | None:
        return self.pi_result.stop_reason

    @property
    def action_trace_ref(self) -> PiArtifactRef | None:
        return self.pi_result.action_trace_ref
```

Update protocol and methods:

```python
class SearchCardsExecutor(Protocol):
    def __call__(...) -> LiepinPiCardSearchResult: ...

def search_cards(..., page_size: int) -> LiepinPiCardSearchResult:
    ...

def _blocked_result(...) -> LiepinPiCardSearchResult:
    return LiepinPiCardSearchResult(pi_result=PiAgentResult(...))
```

For fake fixture mode, either return a blocked result for live use or a succeeded fixture result with an empty `LiepinCardSearchResponse`. Keep existing fixture tests explicit.

Update tests and imports:

```bash
uv run pytest tests/test_liepin_pi_card_search_result.py tests/test_liepin_pi_runner.py -q
uv run ruff check src/seektalent/providers/liepin/pi_runner.py tests/test_liepin_pi_card_search_result.py tests/test_liepin_pi_runner.py
```

- [x] **Task 7: Add PI Agent DokoBot action executor and concrete transport binding**

Add `src/seektalent/providers/liepin/dokobot_actions.py`.

This executor belongs to PI Agent provider execution. Do not bind to Codex tools. It may be unit-tested with an injected fake action session, but the implementation must also include the concrete SeekTalent runtime DokoBot MCP/action transport binding or fail closed during build. Do not stop at protocol-only code.

The executor may expose a synchronous callable because `LiepinPiWorkerClient` will call the runner through `asyncio.to_thread()` when the surrounding worker-client API is async. If the concrete DokoBot action transport is async, keep the async boundary inside the transport module and provide a small synchronous wrapper for the PI runner, or make the PI runner executor protocol async and update the worker client accordingly. Do not call blocking DokoBot transport operations directly from an async source-lane task.

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from seektalent.providers.liepin.pi_runner import LiepinPiCardSearchResult
from seektalent.providers.liepin.worker_contracts import LiepinCardSearchResponse
from seektalent.providers.pi_agent.contracts import PiAgentFailureCode, PiAgentResult


DokoBotActionProviderState = Literal[
    "ready",
    "login_required",
    "verification_required",
    "risk_control",
    "unsupported_route",
    "timeout",
    "capability_unavailable",
]


@dataclass(frozen=True, kw_only=True)
class DokoBotActionReadiness:
    state: DokoBotActionProviderState
    failure_code: PiAgentFailureCode | None = None

    @property
    def is_ready(self) -> bool:
        return self.state == "ready"


def pi_failure_code_for_provider_state(state: DokoBotActionProviderState) -> PiAgentFailureCode:
    if state == "login_required":
        return PiAgentFailureCode.LOGIN_EXPIRED
    if state == "verification_required":
        return PiAgentFailureCode.VERIFICATION_REQUIRED
    if state == "risk_control":
        return PiAgentFailureCode.RISK_CONTROL
    if state == "unsupported_route":
        return PiAgentFailureCode.SELECTOR_DRIFT
    if state == "timeout":
        return PiAgentFailureCode.PAGE_TIMEOUT
    if state == "capability_unavailable":
        return PiAgentFailureCode.DOKOBOT_ACTION_CAPABILITY_UNAVAILABLE
    raise ValueError(f"ready provider state has no failure code: {state}")


class DokoBotLiepinActionSession(Protocol):
    def submit_keyword_search(self, *, keyword_query: str, source_run_id: str) -> None: ...
    def read_card_page(self, *, page_index: int, page_size: int, remaining_cards: int) -> LiepinCardSearchResponse: ...
    def turn_page(self, *, page_index: int) -> None: ...
    def detect_provider_state(self) -> DokoBotActionReadiness: ...
    def write_action_trace(
        self,
        *,
        source_run_id: str,
        result_code: str,
        failure_code: PiAgentFailureCode | None,
    ) -> PiAgentResult: ...


@dataclass(frozen=True, kw_only=True)
class DokoBotLiepinSearchCardsExecutor:
    session: DokoBotLiepinActionSession

    def __call__(
        self,
        *,
        session_id: str,
        source_run_id: str,
        connection_id: str,
        provider_account_lock_key: str,
        keyword_query: str,
        query_terms: list[str],
        max_pages: int,
        page_size: int,
        max_cards: int,
    ) -> LiepinPiCardSearchResult:
        del session_id, connection_id, provider_account_lock_key, query_terms
        remaining_cards = max_cards
        pages: list[LiepinCardSearchResponse] = []
        self.session.submit_keyword_search(keyword_query=keyword_query, source_run_id=source_run_id)
        for page_index in range(1, max_pages + 1):
            provider_state = self.session.detect_provider_state()
            if not provider_state.is_ready:
                failure_code = provider_state.failure_code or pi_failure_code_for_provider_state(provider_state.state)
                if any(page.cards for page in pages):
                    partial_cards = merge_liepin_card_pages(pages, max_cards=max_cards)
                    return LiepinPiCardSearchResult(
                        pi_result=self.session.write_action_trace(
                            source_run_id=source_run_id,
                            result_code="partial",
                            failure_code=failure_code,
                        ),
                        card_search=partial_cards,
                    )
                return LiepinPiCardSearchResult(
                    pi_result=self.session.write_action_trace(
                        source_run_id=source_run_id,
                        result_code="blocked",
                        failure_code=failure_code,
                    )
                )
            if page_index > 1:
                self.session.turn_page(page_index=page_index)
            page = self.session.read_card_page(
                page_index=page_index,
                page_size=page_size,
                remaining_cards=remaining_cards,
            )
            pages.append(page)
            remaining_cards -= len(page.cards)
            if remaining_cards <= 0 or page.exhausted:
                break
        cards = merge_liepin_card_pages(pages, max_cards=max_cards)
        return LiepinPiCardSearchResult(
            pi_result=self.session.write_action_trace(source_run_id=source_run_id, result_code="ok", failure_code=None),
            card_search=cards,
        )
```

Add a concrete DokoBot action transport under `src/seektalent/providers/pi_agent/dokobot_action_transport.py` or the nearest existing PI-agent module. It must:

- use only the SeekTalent-configured DokoBot MCP/action surface, not Codex tools;
- prove the trusted action manifest before exposing click/type/navigation/pagination;
- expose a startup/capability probe that `dokobot_action` mode can run before the first live provider action;
- expose the `DokoBotLiepinActionSession` operations used above;
- preserve action traces and protected artifact refs;
- return a typed blocked result when login, risk state, unsupported route, timeout, or missing capability is detected before any cards are safely collected.
- return `PiAgentResultStatus.PARTIAL` with `card_search` when those states are detected after one or more cards have been safely collected. `write_action_trace(result_code="partial", failure_code=...)` must create a PI result with `status=PARTIAL` and the same stop reason so Task 8 can preserve the partial cards through `LiepinWorkerPartialSearchError`.
- extract allowlisted safe card summaries from visible card text/DOM into `safeCardSummary` fields before returning `LiepinCardSearchResponse`.

If the local DokoBot MCP/action API cannot be discovered or invoked, implementation must stop as blocked with evidence from the failed capability/transport probe. Do not update `TODOS.md` to defer the concrete transport and still mark this build complete.

Tests:

- ready session returns typed cards
- login-required session returns blocked PI result
- state changes after one or more pages were read, such as timeout/risk/login, return `PARTIAL + card_search` and preserve the already collected cards
- verification-required, risk-control, unsupported-route, timeout, and missing-capability states return distinct PI failure codes instead of being collapsed into `LOGIN_EXPIRED`
- executor never falls back to legacy worker
- executor respects `max_pages`, `page_size`, and `max_cards`
- provider rank is preserved across pages
- every DokoBot-action card has `safeCardSummary`
- raw HTML, cookies, contact details, browser storage, and approval secrets never appear in `safeCardSummary`
- missing concrete DokoBot action transport blocks before live action

Run:

```bash
uv run pytest tests/test_liepin_pi_runner.py tests/test_liepin_pi_card_search_result.py -q
uv run pytest tests/test_liepin_dokobot_actions.py tests/test_dokobot_capabilities.py -q
uv run ruff check src/seektalent/providers/liepin/dokobot_actions.py src/seektalent/providers/pi_agent/dokobot_action_transport.py tests/test_liepin_dokobot_actions.py tests/test_liepin_pi_card_search_result.py
```

- [x] **Task 8: Bridge PI card search result into the Liepin provider adapter path**

Choose the smallest repo-consistent bridge. Prefer adapting the PI runner result into the existing `LiepinWorkerClient` search shape instead of adding a second Runtime card search pipeline.

Add a typed partial worker error to `src/seektalent/providers/liepin/worker_contracts.py` so Runtime can import it from the same worker contract boundary as `LiepinWorkerModeError`:

```python
from seektalent.core.retrieval.provider_contract import SearchResult


class LiepinWorkerPartialSearchError(LiepinWorkerModeError):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        partial_search_result: SearchResult,
        cards_collected: int,
    ) -> None:
        super().__init__(message, code=code)
        self.partial_search_result = partial_search_result
        self.cards_collected = cards_collected
```

Add a focused adapter, for example `src/seektalent/providers/liepin/pi_worker_client.py`:

```python
import asyncio

from seektalent.providers.pi_agent.contracts import PiAgentFailureCode, PiAgentResultStatus
from seektalent.providers.liepin.worker_contracts import LiepinWorkerModeError, LiepinWorkerPartialSearchError


class LiepinPiWorkerClient:
    def __init__(self, runner: LiepinPiRunner, *, session_id: str, connection_id: str, provider_account_lock_key: str) -> None:
        self._runner = runner
        self._session_id = session_id
        self._connection_id = connection_id
        self._provider_account_lock_key = provider_account_lock_key

    async def ensure_ready(self, *, on_event=None) -> None:
        del on_event

    async def session_status(
        self,
        *,
        connection_id: str,
        tenant: str | None = None,
        workspace: str | None = None,
        provider_account_hash: str | None = None,
    ) -> SessionStatus:
        ...

    async def login_handoff(
        self,
        *,
        connection_id: str,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        provider_account_hash: str | None = None,
    ) -> LoginHandoff:
        ...

    async def complete_login_relay(self, *, connection_id: str) -> LoginRelayCompleteResult:
        ...

    async def search(
        self,
        request: SearchRequest,
        *,
        round_no: int,
        trace_id: str,
        provider_account_hash: str | None = None,
    ) -> SearchResult:
        del round_no, provider_account_hash
        result = await asyncio.to_thread(
            self._runner.search_cards,
            session_id=self._session_id,
            source_run_id=trace_id,
            connection_id=self._connection_id,
            provider_account_lock_key=self._provider_account_lock_key,
            keyword_query=request.keyword_query or " ".join(request.query_terms),
            query_terms=list(request.query_terms),
            max_pages=max(1, int(request.provider_context.get("liepin_max_pages", 1))),
            page_size=request.page_size,
            max_cards=max(1, int(request.provider_context.get("liepin_max_cards", request.page_size))),
        )
        if result.status == PiAgentResultStatus.SUCCEEDED and result.card_search is not None:
            return liepin_card_search_response_to_search_result(result.card_search)
        if result.status == PiAgentResultStatus.PARTIAL and result.card_search is not None:
            partial_search = liepin_card_search_response_to_search_result(result.card_search)
            raise LiepinWorkerPartialSearchError(
                "Liepin PI card search returned partial cards",
                code=_worker_error_code_from_pi_stop_reason(result.stop_reason),
                partial_search_result=partial_search,
                cards_collected=len(partial_search.candidates),
            )
        else:
            raise LiepinWorkerModeError(
                "Liepin PI card search blocked",
                code=_worker_error_code_from_pi_stop_reason(result.stop_reason),
            )


def _worker_error_code_from_pi_stop_reason(stop_reason: object) -> str:
    if isinstance(stop_reason, PiAgentFailureCode):
        return stop_reason.value
    return "failed_provider_error"
```

Expose `liepin_card_search_response_to_search_result()` as a public helper in `src/seektalent/providers/liepin/client.py` or move it to a small mapping module. It should wrap the existing private `_search_result_from_worker_response()` implementation or replace it with the public name. Do not import the private `_search_result_from_worker_response()` helper from new code.

The PI-backed worker client must satisfy the existing `LiepinWorkerClient` protocol enough for Workbench and `LiepinProviderAdapter`:

- `login_handoff()` starts or probes the DokoBot action session without opening a Codex browser path.
- `complete_login_relay()` verifies the user's already logged-in local browser session and returns `LoginRelayCompleteResult(status="ready", provider_account_hash=...)`.
- `session_status()` returns `ready` only after the DokoBot transport confirms login state and the provider-account hash matches.
- login relay snapshot/input methods may return safe `LiepinWorkerModeError` if no frame-based relay is available, but source connection verification must still work through the existing Workbench route flow or an explicitly tested backend verify path.
- blocked PI/DokoBot results should raise `LiepinWorkerModeError` with `code` set to the PI failure code value or another allowlisted worker error code so Runtime can convert it into a safe blocked lane result. Runtime must not parse the exception message.

Tests:

- PI card response maps to `SearchResult.candidates`
- blocked PI result becomes safe worker mode error / blocked lane, not raw exception leakage
- blocked PI result preserves the PI failure code in `LiepinWorkerModeError.code`
- partial PI result with `card_search` raises `LiepinWorkerPartialSearchError` with mapped partial `SearchResult`, `cards_collected`, and structured failure code
- provider rank is preserved into runtime evidence
- `LiepinPiWorkerClient.search()` does not block the event loop when the runner is synchronous
- `complete_login_relay()` verifies an already logged-in DokoBot browser session and returns a provider-account hash
- `session_status()` rejects mismatched or missing provider-account hash
- login/risk/capability-blocked states return safe worker errors, not raw transport text

Run:

```bash
uv run pytest tests/test_liepin_pi_runner.py tests/test_liepin_pi_worker_client.py tests/test_liepin_runtime_source_lane.py tests/test_liepin_provider_adapter.py -q
```

- [x] **Task 9: Wire `dokobot_action` into product settings, registry, and Workbench path**

Do not add card-review UI or manual approval UI in this plan. Do wire the existing Workbench Liepin source-run path to the PI-backed worker client through normal settings and provider registry paths.

First add a shared live-mode helper in the smallest sensible module, for example `src/seektalent/providers/liepin/client.py`:

```python
LIVE_LIEPIN_WORKER_MODES = frozenset({"managed_local", "external_http", "dokobot_action"})


def is_live_liepin_worker_mode(worker_mode: str) -> bool:
    return worker_mode in LIVE_LIEPIN_WORKER_MODES
```

Use this helper in `src/seektalent/providers/liepin/adapter.py`, `src/seektalent/providers/liepin/runtime_lane.py`, and `src/seektalent/providers/registry.py`. Do not leave separate hard-coded mode sets that omit `dokobot_action`.

Modify `src/seektalent/config.py`:

```python
LiepinWorkerMode = Literal["disabled", "fake_fixture", "managed_local", "external_http", "dokobot_action"]

liepin_dokobot_action_manifest_path: str | None = None
liepin_dokobot_trusted_manifest_ids: tuple[str, ...] = ()
```

Validation rule:

```python
if self.liepin_worker_mode == "dokobot_action":
    if not self.liepin_dokobot_action_manifest_path:
        raise ValueError("liepin_dokobot_action_manifest_path is required when liepin_worker_mode=dokobot_action")
    if not self.liepin_dokobot_trusted_manifest_ids:
        raise ValueError("liepin_dokobot_trusted_manifest_ids is required when liepin_worker_mode=dokobot_action")
```

Modify `src/seektalent/providers/liepin/client.py`:

```python
def build_liepin_worker_client(settings: AppSettings) -> LiepinWorkerClient:
    ...
    if settings.liepin_worker_mode == "dokobot_action":
        return build_liepin_pi_worker_client(settings)
```

Modify `src/seektalent/providers/registry.py`:

- `dokobot_action` is not disabled.
- It creates/uses `LiepinStore` because live connection safety still applies.
- It returns `LiepinProviderAdapter(worker_client=build_liepin_worker_client(settings), store=store)`.

Modify `src/seektalent/providers/liepin/adapter.py`:

- `dokobot_action` follows the same live branch as `managed_local` and `external_http`.
- It enforces compliance gate, source connection, ready session, provider-account hash, and provider connection safety before worker search.
- It never treats `dokobot_action` as a fixture/disabled mode that bypasses live safety.

Modify `src/seektalent/providers/liepin/runtime_lane.py`:

- `_build_provider()` creates a `LiepinStore` for every live Liepin worker mode, including `dokobot_action`.
- factor card-lane result construction into a small helper that can build either `status="completed"` from a normal `SearchResult` or `status="partial"` from a partial worker error without duplicating candidate/evidence/recommendation logic.
- card-lane provider context includes:

```python
"liepin_card_page_size": str(budget.liepin_card_page_size),
"liepin_max_cards": str(budget.liepin_max_cards),
"liepin_max_pages": str(max(1, math.ceil(budget.liepin_max_cards / budget.liepin_card_page_size))),
```

- catch `LiepinWorkerModeError` from the PI-backed worker client, read its structured `code`, and convert that code through the Runtime safe reason-code helper before building `RuntimeSourceLaneResult`; blocked lanes set both `blocked_reason_code` and `stop_reason_code`, while partial lanes set only `stop_reason_code`.
- return a safe blocked lane result with safe events instead of letting Workbench mark the job failed from raw exception text.
- catch `LiepinWorkerPartialSearchError` before the generic worker error catch. Use `error.partial_search_result` as the source of candidates/provider snapshots, call the Runtime safe reason-code helper with `error.code` and `cards_collected=error.cards_collected > 0`, and return a partial lane result:

```python
except LiepinWorkerPartialSearchError as error:
    safe_reason_code = runtime_safe_reason_code_from_pi_failure_code(
        error.code,
        cards_collected=error.cards_collected > 0,
    )
    return _card_lane_result_from_search_result(
        search_result=error.partial_search_result,
        status="partial",
        stop_reason_code=safe_reason_code,
        blocked_reason_code=None,
    )
```

Partial lane behavior:

- safely collected candidates, evidence, provider snapshots, and detail recommendations are preserved;
- event type is `source_lane_partial`;
- `blocked_reason_code` remains `None` because the lane has usable partial output;
- `stop_reason_code` and event `safe_reason_code` use Runtime safe reason codes such as `partial_timeout`;
- raw PI/worker error codes and exception messages are not exposed.

Add one small Runtime-side normalization helper near the Liepin runtime lane or source-lane boundary. Do not pass raw `PiAgentFailureCode.value`, `LiepinWorkerModeError.code`, or exception messages into `RuntimeSourceLaneResult.blocked_reason_code`, `stop_reason_code`, or `RuntimeSourceLaneEvent.safe_reason_code`.

```python
def runtime_safe_reason_code_from_pi_failure_code(
    failure_code: PiAgentFailureCode | str | None,
    *,
    cards_collected: bool = False,
) -> str:
    if isinstance(failure_code, str):
        try:
            failure_code = PiAgentFailureCode(failure_code)
        except ValueError:
            return "failed_provider_error"
    if failure_code == PiAgentFailureCode.LOGIN_EXPIRED:
        return "blocked_login_required"
    if failure_code in {PiAgentFailureCode.VERIFICATION_REQUIRED, PiAgentFailureCode.RISK_CONTROL}:
        return "blocked_compliance"
    if failure_code in {
        PiAgentFailureCode.DOKOBOT_ACTION_CAPABILITY_UNAVAILABLE,
        PiAgentFailureCode.PROVIDER_CONNECTION_LOCKED,
    }:
        return "blocked_backend_unavailable"
    if failure_code == PiAgentFailureCode.PAGE_TIMEOUT:
        return "partial_timeout" if cards_collected else "failed_provider_error"
    if failure_code in {PiAgentFailureCode.SELECTOR_DRIFT, PiAgentFailureCode.EXTRACTION_FAILURE}:
        return "failed_provider_error"
    return "failed_provider_error"
```

The Runtime public reason-code contract is intentionally narrower than PI Agent failure codes:

| PI failure code | Runtime safe reason code |
| --- | --- |
| `LOGIN_EXPIRED` | `blocked_login_required` |
| `VERIFICATION_REQUIRED` | `blocked_compliance` |
| `RISK_CONTROL` | `blocked_compliance` |
| `DOKOBOT_ACTION_CAPABILITY_UNAVAILABLE` | `blocked_backend_unavailable` |
| `PROVIDER_CONNECTION_LOCKED` | `blocked_backend_unavailable` |
| `PAGE_TIMEOUT` | `partial_timeout` when partial cards exist, otherwise `failed_provider_error` |
| `SELECTOR_DRIFT` | `failed_provider_error` |
| `EXTRACTION_FAILURE` | `failed_provider_error` |
| unknown worker/PI error code | `failed_provider_error` |

`run_liepin_source_lane()` should catch `LiepinWorkerModeError` around `provider.search(...)`, call this helper with `error.code`, and emit a `RuntimeSourceLaneResult` whose public payload contains only Runtime safe reason codes.

Modify `src/seektalent_ui/workbench_routes.py` and `src/seektalent_ui/workbench_store.py` only as needed to make the existing Liepin source-connection flow work for `dokobot_action`:

- starting the connection may use the PI-backed worker client to prepare or probe the DokoBot action session;
- completing the connection verifies the already logged-in browser session and records `provider_account_hash`;
- provider session metadata is recorded so `LiepinStoreConnectionSafetyResolver` can later validate ready-session safety;
- Workbench still does not import DokoBot or PI-agent transport modules.

Modify `src/seektalent_ui/runtime_bridge.py` only if needed to pass source budget context fields or worker-client injection; do not import DokoBot or PI-agent transport modules into Workbench.

Modify `.env.example` and `src/seektalent/default.env` to document:

```dotenv
# disabled | fake_fixture | managed_local | external_http | dokobot_action
SEEKTALENT_LIEPIN_WORKER_MODE=disabled
# Required only when SEEKTALENT_LIEPIN_WORKER_MODE=dokobot_action.
SEEKTALENT_LIEPIN_DOKOBOT_ACTION_MANIFEST_PATH=
SEEKTALENT_LIEPIN_DOKOBOT_TRUSTED_MANIFEST_IDS=
```

Update `TODOS.md` under `Runtime Multi-Source Platform Follow-Ups` so concrete DokoBot MCP/action transport binding is no longer deferred by this item. Leave future dry-run coverage, broader action audit, and future browser-backend conformance if not completed.

Tests:

- settings accepts `dokobot_action` with manifest config and rejects it without manifest config.
- `build_liepin_worker_client()` returns a PI-backed worker client for `dokobot_action`.
- provider registry creates `LiepinStore` for `dokobot_action`.
- `LiepinProviderAdapter.search()` enforces live compliance/session safety for `dokobot_action`.
- runtime lane creates a compliance store for `dokobot_action`.
- runtime lane passes `liepin_card_page_size`, `liepin_max_cards`, and derived `liepin_max_pages` to the worker client.
- blocked PI/DokoBot card search becomes a blocked runtime lane result with safe reason codes.
- partial PI/DokoBot card search with safe collected cards becomes a partial runtime lane result that preserves partial candidates/evidence and uses a safe stop reason code.
- raw PI failure-code values such as `login_expired`, `risk_control`, and `dokobot_action_capability_unavailable` never appear in Runtime public payloads, Workbench graph state, notes, or CLI output.
- every supported `PiAgentFailureCode` from DokoBot card search maps to the expected Runtime safe reason code.
- Runtime lane tests cover `LiepinWorkerModeError.code` normalization and assert exception messages are never parsed or exposed.
- Runtime lane tests cover `LiepinWorkerPartialSearchError` and assert partial cards are not dropped or marked completed.
- Workbench Liepin source-run path can use an injected PI-backed worker client and still keeps Workbench out of DokoBot imports.
- Workbench connection completion can mark the Liepin source connection connected for an already logged-in DokoBot browser session and records provider session metadata.
- `rg -n "Trusted browser action conformance" TODOS.md` still returns exactly one entry.
- `rg -n "before enabling action execution" TODOS.md` returns no entries; concrete DokoBot action execution is owned by this plan, while future dry-run/audit/conformance expansion remains deferred.

Run:

```bash
uv run pytest tests/test_liepin_worker_client.py tests/test_provider_registry.py tests/test_liepin_provider_adapter.py tests/test_liepin_runtime_source_lane.py tests/test_workbench_api.py -q
uv run ruff check src/seektalent/config.py src/seektalent/providers/liepin/client.py src/seektalent/providers/liepin/adapter.py src/seektalent/providers/liepin/runtime_lane.py src/seektalent/providers/registry.py src/seektalent_ui/runtime_bridge.py src/seektalent_ui/workbench_routes.py src/seektalent_ui/workbench_store.py tests/test_liepin_worker_client.py tests/test_provider_registry.py tests/test_liepin_provider_adapter.py tests/test_liepin_runtime_source_lane.py tests/test_workbench_api.py
rg -n "Trusted browser action conformance" TODOS.md
if rg -n "before enabling action execution" TODOS.md; then exit 1; fi
```

- [x] **Task 10: Run final verification**

Run focused tests:

```bash
uv run pytest \
  tests/test_liepin_card_policy.py \
  tests/test_liepin_pi_card_search_result.py \
  tests/test_liepin_pi_worker_client.py \
  tests/test_liepin_dokobot_actions.py \
  tests/test_liepin_pi_runner.py \
  tests/test_liepin_runtime_source_lane.py \
  tests/test_dokobot_capabilities.py \
  tests/test_liepin_worker_client.py \
  tests/test_provider_registry.py \
  tests/test_liepin_provider_adapter.py \
  tests/test_workbench_api.py \
  tests/test_runtime_source_lanes.py \
  -q
```

Run lint:

```bash
uv run ruff check \
  src/seektalent/config.py \
  src/seektalent/providers/liepin/client.py \
  src/seektalent/providers/liepin/worker_contracts.py \
  src/seektalent/providers/liepin/mapper.py \
  src/seektalent/providers/liepin/adapter.py \
  src/seektalent/providers/liepin/policy.py \
  src/seektalent/providers/liepin/card_policy.py \
  src/seektalent/providers/liepin/runtime_lane.py \
  src/seektalent/providers/liepin/pi_runner.py \
  src/seektalent/providers/liepin/pi_worker_client.py \
  src/seektalent/providers/liepin/dokobot_actions.py \
  src/seektalent/providers/pi_agent/dokobot_action_transport.py \
  src/seektalent/providers/registry.py \
  src/seektalent/runtime/source_lanes.py \
  src/seektalent_ui/runtime_bridge.py \
  src/seektalent_ui/workbench_routes.py \
  src/seektalent_ui/workbench_store.py \
  tests/test_liepin_card_policy.py \
  tests/test_liepin_pi_card_search_result.py \
  tests/test_liepin_pi_worker_client.py \
  tests/test_liepin_dokobot_actions.py \
  tests/test_liepin_pi_runner.py \
  tests/test_liepin_runtime_source_lane.py \
  tests/test_liepin_worker_client.py \
  tests/test_provider_registry.py \
  tests/test_liepin_provider_adapter.py \
  tests/test_workbench_api.py \
  tests/test_runtime_source_lanes.py
```

Run whitespace check:

```bash
git diff --check \
  docs/superpowers/specs/2026-05-16-liepin-live-browser-action-card-policy-design.md \
  docs/superpowers/plans/2026-05-16-liepin-live-browser-action-card-policy.md \
  .env.example \
  src/seektalent/default.env \
  src/seektalent/config.py \
  src/seektalent/providers/liepin/client.py \
  src/seektalent/providers/liepin/worker_contracts.py \
  src/seektalent/providers/liepin/mapper.py \
  src/seektalent/providers/liepin/adapter.py \
  src/seektalent/providers/liepin/policy.py \
  src/seektalent/providers/liepin/card_policy.py \
  src/seektalent/providers/liepin/runtime_lane.py \
  src/seektalent/providers/liepin/pi_runner.py \
  src/seektalent/providers/liepin/pi_worker_client.py \
  src/seektalent/providers/liepin/dokobot_actions.py \
  src/seektalent/providers/pi_agent/dokobot_action_transport.py \
  src/seektalent/providers/registry.py \
  src/seektalent/runtime/source_lanes.py \
  src/seektalent_ui/runtime_bridge.py \
  src/seektalent_ui/workbench_routes.py \
  src/seektalent_ui/workbench_store.py \
  tests/test_liepin_card_policy.py \
  tests/test_liepin_pi_card_search_result.py \
  tests/test_liepin_pi_worker_client.py \
  tests/test_liepin_dokobot_actions.py \
  tests/test_liepin_pi_runner.py \
  tests/test_liepin_runtime_source_lane.py \
  tests/test_liepin_worker_client.py \
  tests/test_provider_registry.py \
  tests/test_liepin_provider_adapter.py \
  tests/test_workbench_api.py
```

## Completion Criteria

- Liepin card recommendation policy is provider-rank-first and budget-bound.
- Obvious mismatches are filtered before budget allocation.
- Thin/missing cards are held, not recommended.
- PI runner can return typed card data plus PI action trace.
- DokoBot action mode remains trusted-manifest-only and fail-closed.
- `dokobot_action` is selectable through product settings and documented env files, with `disabled` still the default.
- `build_liepin_worker_client()` and provider registry can construct the PI-backed Liepin worker client for `dokobot_action`.
- `dokobot_action` can verify the already logged-in local browser session and mark the Workbench Liepin source connection connected with provider-account/session metadata.
- `dokobot_action` runs through the live compliance/session safety branch and cannot bypass `LiepinStore` safety checks.
- Workbench Liepin source runs use the normal Runtime/provider path and do not import DokoBot or browser-action modules.
- The concrete DokoBot MCP/action transport binding or probe is implemented; if it cannot be proven locally, the build is explicitly blocked and this plan is not marked complete.
- The executor respects `max_pages`, `page_size`, and `max_cards`, and preserves provider rank across pages.
- Runtime passes `liepin_max_cards` and derived `liepin_max_pages` from `RuntimeSourceBudgetPolicy` to the PI-backed worker client.
- DokoBot action-produced cards populate typed `safeCardSummary`.
- Runtime card policy reads only `safe_card_summary` plus normalized card text, not arbitrary raw provider payload keys.
- PI/DokoBot blocked card search becomes a safe blocked runtime lane/source-run state rather than a raw failed job.
- PI/DokoBot execution failure codes are normalized through the explicit Runtime safe reason-code mapping before any public payload is emitted.
- Async source-lane execution does not call synchronous PI/browser work directly on the event loop.
- No Codex-side MCP/tool availability is treated as product runtime capability.
- Workbench scope remains display/persistence/approval state, not provider execution.
- Tests and ruff pass.
