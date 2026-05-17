# Liepin Live Browser Action And Card Policy Execution Ledger

Spec:

- `docs/superpowers/specs/2026-05-16-liepin-live-browser-action-card-policy-design.md`

Plan:

- `docs/superpowers/plans/2026-05-16-liepin-live-browser-action-card-policy.md`

## Execution Owner

Main Codex thread owns integration, Runtime/provider contracts, final verification, and the acceptance checklist. Subagents may implement bounded slices, but their reports are not completion evidence until the main thread verifies tests, public payloads, and plan coverage.

## Task Ledger

| Plan Task | Scope | Status | Evidence |
| --- | --- | --- | --- |
| Task 1 | Failing tests for provider-rank-first card policy | completed | Worker A RED/GREEN; verified by `uv run pytest tests/test_liepin_card_policy.py -q` -> 3 passed |
| Task 2 | Safe card summary and deterministic card decision policy | completed | `src/seektalent/providers/liepin/card_policy.py`; verified in final pytest/ruff set |
| Task 3 | Allowlisted safe card summary mapping | completed | `uv run pytest tests/test_liepin_provider_mapping.py -q` -> 9 passed after RED import failure |
| Task 4 | Runtime Liepin card lane applies card policy | completed | Runtime lane now uses card-policy decisions, budget context, safe reason codes, and partial result builder; final pytest set passed |
| Task 5 | PI card-search result wrapper tests | completed | `tests/test_liepin_pi_card_search_result.py` and `tests/test_liepin_pi_runner.py`; final pytest set passed |
| Task 6 | `LiepinPiCardSearchResult` and runner return types | completed | `LiepinPiRunner.search_cards()` returns typed wrapper and carries `page_size`; final pytest set passed |
| Task 7 | DokoBot action executor and concrete transport/probe | completed_with_live_surface_caveat | Executor and transport session implemented with trusted-manifest probe and fail-closed missing action surface; no repo-local production `DokoBotActionSurface` adapter was discoverable |
| Task 8 | PI card result bridge into `LiepinWorkerClient` | completed | `LiepinPiWorkerClient` maps success/partial/blocked through typed worker contracts and `asyncio.to_thread()`; final pytest set passed |
| Task 9 | `dokobot_action` settings, registry, Runtime, Workbench wiring | completed_with_live_surface_caveat | Settings/registry/live-safety/runtime budget/Workbench injection path wired; default `dokobot_action` client blocks without an injected product action surface |
| Task 10 | Final tests, ruff, whitespace verification | completed | Final pytest/ruff/diff/TODO checks passed |

## Non-Negotiable Contract Checks

- Runtime and Workbench must not import DokoBot/browser action modules.
- `dokobot_action` must be selectable only through product runtime settings with trusted action manifest inputs.
- DokoBot read-only capability must not submit a search.
- PI/DokoBot blocked paths expose only Runtime safe reason codes.
- PI/DokoBot partial card search with collected cards must preserve partial candidates/evidence through `RuntimeSourceLaneResult(status="partial")`.
- Liepin card recommendations must preserve provider rank after hard filters and budget allocation.
- Runtime card policy may read only `safe_card_summary` plus normalized card text, not arbitrary raw provider payload keys.
- Workbench remains display/persistence/approval state, not provider execution.
- If concrete DokoBot MCP/action transport cannot be proven locally, the build reports blocked and is not marked complete.

## Verification Ledger

| Command | Status | Notes |
| --- | --- | --- |
| `uv run pytest tests/test_liepin_pi_runner.py tests/test_liepin_runtime_source_lane.py tests/test_liepin_provider_adapter.py tests/test_liepin_worker_client.py tests/test_provider_registry.py tests/test_runtime_source_lanes.py -q` | passed | Baseline before implementation: 122 passed |
| `uv run pytest tests/test_liepin_provider_mapping.py -q` | passed | Task 3 safe card summary mapping: 9 passed |
| `uv run pytest tests/test_liepin_worker_client.py tests/test_provider_registry.py tests/test_liepin_provider_adapter.py tests/test_liepin_runtime_source_lane.py tests/test_liepin_card_policy.py tests/test_liepin_pi_worker_client.py tests/test_dokobot_capabilities.py tests/test_liepin_dokobot_actions.py -q` | passed | Integration subset after Task 4/9: 139 passed |
| `uv run pytest tests/test_liepin_card_policy.py tests/test_liepin_provider_mapping.py tests/test_liepin_pi_card_search_result.py tests/test_liepin_pi_runner.py tests/test_liepin_dokobot_actions.py tests/test_dokobot_capabilities.py tests/test_liepin_pi_worker_client.py tests/test_liepin_worker_client.py tests/test_provider_registry.py tests/test_liepin_provider_adapter.py tests/test_liepin_runtime_source_lane.py tests/test_runtime_source_lanes.py tests/test_workbench_api.py -q` | passed | Final plan pytest set: 280 passed |
| `uv run ruff check src/seektalent/config.py src/seektalent/providers/liepin/client.py src/seektalent/providers/liepin/adapter.py src/seektalent/providers/liepin/runtime_lane.py src/seektalent/providers/registry.py src/seektalent/providers/liepin/card_policy.py src/seektalent/providers/liepin/mapper.py src/seektalent/providers/liepin/worker_contracts.py src/seektalent/providers/liepin/pi_runner.py src/seektalent/providers/liepin/pi_worker_client.py src/seektalent/providers/liepin/dokobot_actions.py src/seektalent/providers/pi_agent/dokobot_action_transport.py src/seektalent/runtime/source_lanes.py tests/test_liepin_card_policy.py tests/test_liepin_provider_mapping.py tests/test_liepin_pi_card_search_result.py tests/test_liepin_pi_runner.py tests/test_liepin_dokobot_actions.py tests/test_dokobot_capabilities.py tests/test_liepin_pi_worker_client.py tests/test_liepin_worker_client.py tests/test_provider_registry.py tests/test_liepin_provider_adapter.py tests/test_liepin_runtime_source_lane.py tests/test_runtime_source_lanes.py tests/test_workbench_api.py` | passed | All checks passed |
| `git diff --check` | passed | No whitespace errors |
| `rg -n "Trusted browser action conformance" TODOS.md && if rg -n "before enabling action execution" TODOS.md; then exit 1; fi` | passed | Follow-up appears once; old deferred action-execution wording absent |

## Live Surface Caveat

The product code now has a `dokobot_action` settings/registry/runtime path and a fail-closed DokoBot action transport session. The repository does not currently contain a production `DokoBotActionSurface` adapter that can invoke the external SeekTalent DokoBot MCP/action server. Without that injected action surface, `dokobot_action` remains selectable but blocks before live provider actions. This is intentional fail-closed behavior and should not be reported as fully live Liepin browser execution.
