# Runtime Lifecycle And Latency Observability Design

Date: 2026-04-23

## Context

The latest real benchmark run showed that scoring concurrency and exact-cache work are useful, but whole-run latency is now dominated by requirements, controller, and reflection thinking calls. One controller call took 182.5s without a full retry. Its visible structured output included a 6,128-character `decision_rationale`, so output length is also part of the latency profile.

The same run used a fresh local exact-cache directory. Therefore local exact cache did not hit during that run; it populated `requirements=1` and `scoring=24` entries for future identical runs. The local exact-cache currently has no TTL or automatic cleanup. Run artifacts also remain until manually deleted.

The goal of this design is to improve local lifecycle behavior and observability without changing retrieval strategy, scoring strategy, stop policy, or candidate-selection behavior.

## Goals

- Add a simple `dev` / `prod` runtime mode.
- Put production artifacts under `~/.seektalent`.
- Keep development run artifacts permanently as local debugging assets.
- Clear local exact LLM cache automatically on startup in both modes.
- In production, automatically remove run artifacts older than 7 days.
- Record provider token usage and cached-token counts in LLM call snapshots.
- Limit visible controller/reflection rationale verbosity with generous schema and prompt constraints.
- Keep controller query-term discipline intact: controller may only choose active admitted terms.

## Non-Goals

- No background cleanup daemon or scheduler.
- No A/B benchmark in this change.
- No change to retrieval, scoring, stop, or ranking semantics.
- No disabling requirements/controller/reflection thinking.
- No model fallback chain.
- No relaxation that lets controller invent executable query terms outside the active admitted term bank.

## Runtime Mode

Add `runtime_mode` with exactly two values:

```env
# dev: source/local development. Runs stay in ./runs and are never auto-deleted.
# prod: packaged production. Runs/cache live under ~/.seektalent.
SEEKTALENT_RUNTIME_MODE=dev
```

Behavior:

- Source/local execution defaults to `dev`.
- Local developers can override the mode in `.env`.
- Packaged production must force `prod`, even if no `.env` is provided.
- If packaged detection is not reliable in the core library, the package entrypoint should set `SEEKTALENT_RUNTIME_MODE=prod` before settings are loaded.

Resolved defaults:

| Mode | runs_dir | llm_cache_dir |
| --- | --- | --- |
| `dev` | `./runs` | `./.seektalent/cache` |
| `prod` | `~/.seektalent/runs` | `~/.seektalent/cache` |

Explicit `SEEKTALENT_RUNS_DIR`, `SEEKTALENT_LLM_CACHE_DIR`, and CLI `--output-dir` continue to override these defaults for tests and special workflows.

## Cleanup

Cleanup runs once at the start of `seektalent run` and `seektalent benchmark`, after settings are loaded and before new artifacts or cache entries are written.

Rules:

- `dev` runs: keep forever.
- `dev` exact cache: clear on every startup.
- `prod` runs: delete run directories older than 7 days.
- `prod` exact cache: clear on every startup.

This is deliberately opportunistic cleanup, not a timer. It keeps the implementation small and avoids platform-specific scheduling. Clearing exact cache on startup also avoids unbounded SQLite growth and stale repeated-experiment artifacts.

Run cleanup should only delete directories that match the run directory naming pattern produced by `RunTracer`, not arbitrary files under the configured runs root. Benchmark summary JSON files can be kept in `dev`; in `prod`, summaries older than 7 days may be deleted with the same retention rule.

## Provider Usage Snapshot

Extend `LLMCallSnapshot` with provider usage data captured from `AgentRunResult.usage()`.

Suggested shape:

```json
{
  "provider_usage": {
    "input_tokens": 0,
    "output_tokens": 0,
    "total_tokens": 0,
    "cache_read_tokens": 0,
    "cache_write_tokens": 0,
    "details": {}
  },
  "cached_input_tokens": 0
}
```

Mapping:

- `provider_usage.input_tokens` from Pydantic AI usage input tokens.
- `provider_usage.output_tokens` from output tokens.
- `provider_usage.total_tokens = input_tokens + output_tokens`.
- `provider_usage.cache_read_tokens` from usage cache-read tokens.
- `provider_usage.cache_write_tokens` from usage cache-write tokens.
- `cached_input_tokens` mirrors `cache_read_tokens` for existing audit compatibility.

If Bailian returns cached-token information that Pydantic AI does not map into `cache_read_tokens`, preserve any provider details that are available under `provider_usage.details`. A later change can add raw response extraction if needed.

This does not reduce latency directly. It makes cache behavior measurable so latency decisions are based on provider evidence instead of request parameters alone.

## Rationale Length Governance

Limit visible explanatory fields without changing the thinking stages or the decision policy.

Schema constraints should be generous enough for useful audit text:

- `thought_summary`: max 500 characters.
- `decision_rationale`: max 1200 characters.
- `response_to_reflection`: max 800 characters.
- `reflection_rationale`: max 1200 characters.

Prompt updates should say that visible rationale is an audit summary, not a step-by-step reasoning transcript. Controller and reflection should keep the decision itself structured as today, but avoid expanding term-bank deliberation into long prose.

Do not use provider-level `max_tokens` as the primary control in this change. A hard cap can truncate JSON and cause expensive structured-output failures. Schema and prompt constraints are safer and easier to test.

## Controller Query-Term Discipline

Keep the current rule: controller may only choose terms from the current query term pool where `queryability=admitted`, the term is active, and the retrieval role/family rules allow it.

This does constrain model freedom, but it protects the runtime boundary. The controller decides among executable terms; it does not invent executable search terms. If a term like `FastAPI` is important, it should be extracted and admitted during requirements/term-bank construction before controller selection.

Update controller prompt examples so few-shot terms are clearly examples only. A few-shot term such as `FastAPI` must not be reused unless it exists in the current active admitted term bank.

## Data Flow

1. CLI loads settings and resolves `runtime_mode`.
2. Startup cleanup runs for `run` and `benchmark`.
3. `RunTracer` writes artifacts under the resolved runs directory.
4. Exact requirements/scoring cache reads and writes under the resolved cache directory.
5. Each LLM call captures provider usage from `AgentRunResult.usage()` and writes it into its call snapshot.
6. Controller/reflection model outputs are validated against the same behavioral rules plus generous visible-rationale length limits.

## Testing

- Unit-test runtime mode default resolution and `.env` override.
- Unit-test production path defaults under `~/.seektalent`.
- Unit-test cleanup:
  - `dev` keeps run directories and clears exact cache.
  - `prod` deletes run directories older than 7 days and clears exact cache.
  - cleanup ignores files/directories that do not match known artifact patterns.
- Unit-test `LLMCallSnapshot` serialization for `provider_usage` and `cached_input_tokens`.
- Unit-test usage extraction with a fake `AgentRunResult.usage()` object at requirements/controller/reflection/scoring call sites.
- Unit-test schema max-length constraints for controller and reflection rationale fields.
- Unit-test controller prompt text that few-shot terms are not reusable unless present in the active admitted term bank.

## Acceptance Criteria

- A packaged production run uses `~/.seektalent/runs` and `~/.seektalent/cache` by default.
- A local source run defaults to `./runs` and `./.seektalent/cache`.
- `SEEKTALENT_RUNTIME_MODE=dev|prod` is the only runtime-mode value accepted.
- Development runs are not auto-deleted.
- Production runs older than 7 days are auto-deleted on startup.
- Exact LLM cache is cleared on startup in both modes.
- New LLM call snapshots include provider usage when available.
- `cached_input_tokens` is populated from provider cache-read tokens when available.
- Controller/reflection visible rationale fields cannot grow into multi-thousand-character outputs.
- Controller still rejects executable query terms that are not active admitted terms.
