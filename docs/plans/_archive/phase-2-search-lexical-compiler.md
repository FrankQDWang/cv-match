# Task: Phase 2 Search Lexical Compiler

## Goal

实现一个小而确定性的 lexical compiler，把 LLM 抽出的 JD/notes 搜索词先翻译成 CTS 可搜索词池，再让 controller 只能从已准入的词和合法组合里生成 query。

业务目标：减少 JD 侧脏词、硬筛选词、抽象能力词、过窄新术语污染 CTS keyword search，优先解决 `agent_jds.jsonl` replay 中的 zero-recall 和 exact-title-anchor 问题。

## Why Now

Phase 1 已经完成 `search_diagnostics.json`，可以看到搜索失败发生在哪一层。真实 CTS + 真实 LLM replay 证据在：

- `artifacts/benchmarks/agent_jds.jsonl`
- `runs/phase_1_5_diagnostic_replay_20260418_203841/benchmark_summary_20260418_212446.json`
- `runs/phase_1_5_diagnostic_replay_20260418_203841/20260418_204813_323449e3/search_diagnostics.json`

观察到的关键问题：

- `agent_jd_002` final candidate count 为 0；round query 使用 `"AI Agent工程师"`、`任务拆解`、`AgentLoop调优`、`211` 等不适合早期 CTS keyword search 的词。
- `agent_jd_006` final candidate count 为 1；query 受 `Agent算法工程师` / `LLM Agent` 这类窄 anchor 影响，缺少简历侧更常见的 broad anchor/backoff。
- 6 个样本的 LLM structured-output validator retry 总量很低；当前优先问题不是 JSON schema 解析失败，而是搜索词表示和组合规则。

## Non-goals

- 不把 SeekTalent 改成开放式 agent。
- 不实现 reflection discovery agent、verifier agent、full knowledge graph、resume-side inventory 或网页/app action harness。
- 不重写 orchestrator 主流程、CTS client、scoring、finalizer 或 UI。
- 不瘦身 `RequirementExtractionDraft` / `ScoredCandidate` / `FinalResult` schema；本阶段只减少搜索层对 LLM query terms 的直接信任。
- 不新增数据库、外部服务、训练任务或大规模配置系统。
- 不为了覆盖所有岗位穷举词典；只加通用规则和少量 benchmark 暴露出的高价值规则。

## Done Criteria

- `QueryTermCandidate` 能表达一个 term 是否可进入 CTS keyword search，以及它属于哪个 query family。
- requirement normalization 不再把 LLM draft terms 直接合并成搜索词池，而是经过 compiler 准入。
- query planning 只允许 admitted terms 进入 keyword query，并限制同一 family 在同一个 query 中最多出现一次。
- controller validator 继续 fail fast，但错误信息指向 compiler 准入或 family 冲突，而不是只要求 exact title anchor。
- `AI Agent工程师` / `Agent算法工程师` 这类职位名不再被强制原样作为每个 query 的 fixed anchor。
- `211`、`AgentLoop调优`、`长链路业务问题`、`任务拆解` 等词不会进入早期 CTS keyword search。
- Focused tests 通过；真实 CTS replay 跑完并把结果记录到本计划的 status/decision log。

## Repo Entrypoints

Read first:

1. `AGENTS.md`
2. `README.md`
3. `src/seektalent/models.py`
4. `src/seektalent/requirements/normalization.py`
5. `src/seektalent/retrieval/query_plan.py`
6. `src/seektalent/controller/react_controller.py`
7. `tests/test_requirement_extraction.py`
8. `tests/test_query_plan.py`
9. `tests/test_controller_contract.py`
10. `runs/phase_1_5_diagnostic_replay_20260418_203841/20260418_204813_323449e3/search_diagnostics.json`

Likely edit:

- `src/seektalent/models.py`
- `src/seektalent/retrieval/query_compiler.py`
- `src/seektalent/requirements/normalization.py`
- `src/seektalent/retrieval/query_plan.py`
- `src/seektalent/prompts/controller.md`
- `src/seektalent/prompts/reflection.md`
- `tests/test_query_compiler.py`
- `tests/test_requirement_extraction.py`
- `tests/test_query_plan.py`
- `tests/test_controller_contract.py`

Allowed only if the direct compiler change is not enough:

- `src/seektalent/prompts/requirements.md`
- `src/seektalent/runtime/orchestrator.py`

Do not edit unless this plan is updated first:

- `src/seektalent/clients/`
- `src/seektalent/scoring/`
- `src/seektalent/reflection/`
- `src/seektalent/finalize/`
- `src/seektalent_ui/`
- `experiments/`
- `apps/`

Ignore unless evidence says otherwise:

- `runs/` except reading Phase 1 diagnostics and writing new benchmark output
- `.venv/`
- `.pytest_cache/`
- `__pycache__/`
- `dist/`

## Current Reality

Observed behavior:

- `README.md` describes the main flow as requirement extraction -> controlled CTS retrieval -> scoring -> reflection -> finalization.
- `RequirementExtractionDraft` currently asks the LLM for `title_anchor_term`, `jd_query_terms`, `notes_query_terms`, and `preferred_query_terms`.
- `QueryTermCandidate` currently has `term`, `source`, `category`, `priority`, `evidence`, `first_added_round`, and `active`.
- `requirements/normalization.py::_build_query_term_pool` directly merges LLM `jd_query_terms` and `notes_query_terms`, with a tiny keyword heuristic for `category`.
- `retrieval/query_plan.py::canonicalize_controller_query_terms` requires the fixed `title_anchor_term` exactly once in every query.
- Phase 1 diagnostics show zero-recall rounds where CTS queries include exact title anchors and JD-side phrases that candidates are unlikely to write in resumes.

Known invariants:

- Keep the outer workflow deterministic and auditable.
- Keep query length budget small: round 1 has anchor + 1 non-anchor; later rounds have anchor + 1 or 2 non-anchors unless this plan is updated.
- Reflection may activate/deactivate terms, but compiler/query_plan owns whether a term is searchable.
- This repo prefers small direct Python; avoid abstract compiler class hierarchies.

## Target Behavior

Term pool:

- Each `QueryTermCandidate` has enough metadata for search admission:
  - `retrieval_role`: `role_anchor`, `core_skill`, `framework_tool`, `domain_context`, `filter_only`, or `score_only`
  - `queryability`: `admitted`, `score_only`, `filter_only`, or `blocked`
  - `family`: stable string such as `role.agent`, `skill.python`, `framework.langchain`, `constraint.school_type`
- Defaults preserve most existing tests and manual `QueryTermCandidate(...)` construction.

Compiler:

- Lives in one small module, likely `src/seektalent/retrieval/query_compiler.py`.
- Takes cleaned job title, LLM title anchor, JD query terms, notes query terms, and known hard/preference constraints.
- Emits a compact list of `QueryTermCandidate` objects.
- Adds or normalizes broad resume-side anchors when the title anchor is too literal, for example:
  - `AI Agent工程师` -> admitted anchor `AI Agent` or `Agent`
  - `Agent算法工程师` -> admitted anchor `Agent` plus possible broad domain `大模型`
- Marks obvious non-search terms out of CTS keyword search:
  - `211`, `985`, degree/school/age/gender/location constraints -> `filter_only`
  - `任务拆解`, `长链路业务问题`, `复杂业务问题`, soft skills -> `score_only` or `blocked`
  - too-narrow emerging framework aliases such as `veADK` / `Google ADK` -> not first-round admitted unless evidence changes

Query planning:

- `canonicalize_controller_query_terms` no longer requires exact `title_anchor_term` in every query.
- A valid query must contain exactly one admitted role/domain anchor from the compiled pool.
- Non-anchor query terms must be active and `queryability == "admitted"` unless explicitly allowed for explore/backoff.
- Same `family` may not appear twice in one query.
- `select_query_terms` and `derive_explore_query_terms` use compiler metadata when ranking terms.

## Milestones

### M1. Confirm Change Surface and Exact Schema

Steps:

- Re-read the entrypoints listed above.
- Inspect all direct `QueryTermCandidate(...)` constructions in tests and source.
- Decide the final literal names for `retrieval_role`, `queryability`, and `family`.
- Confirm whether `title_anchor_term` remains a display/context field while role anchors come from compiled pool.

Deliverables:

- Updated decision log if field names or edit files differ from this plan.
- Exact list of files to edit before implementation starts.

Acceptance:

- The compiler can be implemented without changing runtime orchestration.
- Existing tests that manually build `QueryTermCandidate` can keep working through sensible defaults or narrow test updates.

Validation:

```bash
uv run pytest tests/test_requirement_extraction.py tests/test_query_plan.py tests/test_controller_contract.py
```

Expected: baseline targeted tests pass before implementation, or pre-existing failures are recorded here before proceeding.

### M2. Add Minimal Compiler

Steps:

- Add `src/seektalent/retrieval/query_compiler.py` with module-level functions only.
- Extend `QueryTermCandidate` with small metadata fields and defaults.
- Move query term classification out of `_build_query_term_pool` into the compiler.
- Keep `RequirementExtractionDraft` unchanged in this milestone.
- Keep compiler rules generic first: title suffix cleanup, school/degree/filter detection, abstract phrase detection, obvious tech/tool detection, family assignment.

Acceptance:

- Unit tests can call compiler directly.
- `normalize_requirement_draft` returns a compiled `initial_query_term_pool`.
- `211` is not admitted.
- `AI Agent工程师` does not become the only possible role anchor.
- `Python`, `LangChain`, `RAG`, `AI Agent` style resume-side terms can be admitted.

Validation:

```bash
uv run pytest tests/test_query_compiler.py tests/test_requirement_extraction.py
```

Expected: all targeted tests pass.

### M3. Enforce Compiler Admission in Query Plan

Steps:

- Update `canonicalize_controller_query_terms` to validate against `queryability`, `retrieval_role`, and `family`.
- Replace exact-title-anchor validation with admitted-anchor validation.
- Update `select_query_terms` to choose one admitted anchor and the best admitted non-anchor terms.
- Update `derive_explore_query_terms` so inactive/backup terms still must be compiler-admitted and family-compatible.
- Keep round query size limits unchanged.

Acceptance:

- Queries containing `211`, `任务拆解`, `AgentLoop调优`, or two terms from the same family are rejected.
- Queries with a compiled anchor alias are accepted even if they do not contain the literal `title_anchor_term`.
- Existing controller contract tests still validate bad controller outputs through `ModelRetry`.

Validation:

```bash
uv run pytest tests/test_query_plan.py tests/test_controller_contract.py
```

Expected: all targeted tests pass.

### M4. Run Focused Runtime Validation

Steps:

- Run runtime-focused tests after compiler and query plan tests pass.
- Fix only failures caused by this task.
- Do not change scoring, reflection, CTS client, or finalizer behavior to make tests pass.

Acceptance:

- Existing runtime tests pass with compiled term pool metadata.
- Existing artifact generation still works.

Validation:

```bash
uv run pytest tests/test_runtime_state_flow.py tests/test_runtime_audit.py tests/test_cli.py
```

Expected: all targeted tests pass.

### M5. Replay Real CTS Benchmark and Record Results

Steps:

- Run the 6-sample benchmark with real CTS and real LLM after all focused tests pass.
- Use a new output directory under `runs/`.
- Compare against Phase 1 replay on zero-final runs, final precision, raw/unique candidates, and diagnostic query terms.
- Update this plan's status and decision log with the exact summary path and key metrics.

Command:

```bash
uv run seektalent benchmark \
  --jds-file artifacts/benchmarks/agent_jds.jsonl \
  --env-file .env \
  --output-dir runs/phase_2_compiler_replay_$(date +%Y%m%d_%H%M%S) \
  --enable-eval \
  --json
```

Acceptance:

- Benchmark completes all 6 samples without task-caused crashes.
- `agent_jd_002` and `agent_jd_006` no longer fail because of exact title anchor plus dirty JD terms; if they still fail, `search_diagnostics.json` must show the remaining failure mode clearly.
- Good prior samples `agent_jd_001` and `agent_jd_003` do not obviously regress in final candidate quality without a recorded reason.

Expected: write the benchmark summary path and comparison notes into this plan before finalizing.

## Decision Log

- 2026-04-19: Chose deterministic compiler before reflection discovery agent because Phase 1 diagnostics show query representation failures, while structured-output validator retries were low.
- 2026-04-19: Keep `RequirementExtractionDraft` unchanged for this phase to avoid making the LLM output schema larger while testing search admission.
- 2026-04-19: Prefer one small module with functions over compiler/controller class abstractions because the repo prioritizes local simplicity.
- 2026-04-19: Baseline validation passed before implementation: `uv run pytest tests/test_requirement_extraction.py tests/test_query_plan.py tests/test_controller_contract.py` returned 23 passed.
- 2026-04-19: Final compiler metadata field names are `retrieval_role`, `queryability`, and `family`; `title_anchor_term` remains a display/context field while compiled pool terms own runtime search anchors.
- 2026-04-19: `src/seektalent/prompts/controller.md` and `src/seektalent/prompts/reflection.md` are in the edit surface because both currently encode the old fixed-title-anchor contract.
- 2026-04-19: Focused and full validation passed after implementation: compiler/normalization 11 passed, query plan/controller 21 passed, runtime-focused 34 passed, full suite 208 passed.
- 2026-04-19: Real CTS replay completed at `runs/phase_2_compiler_replay_20260419_133020/benchmark_summary_20260419_141832.json`. `agent_jd_002` improved from 0 final candidates / 0.0 precision to 10 final candidates / 0.2 precision; queries used compiled `AI Agent` anchor and admitted terms instead of literal `AI Agent工程师`, `任务拆解`, `AgentLoop调优`, or `211`. `agent_jd_006` improved from 1 final candidate / 0.0 precision to 10 final candidates / 0.9 precision; queries used `Agent` with admitted skill/framework terms instead of narrow `Agent算法工程师` / `LLM Agent` anchoring.
- 2026-04-19: Recorded precision tradeoff on prior strong samples: `agent_jd_001` final precision moved from 0.9 to 0.5 and `agent_jd_003` from 1.0 to 0.8. The likely cause is intentional broader compiled anchors increasing recall surface; this phase accepts the tradeoff because the target zero/low-recall failures were fixed, but follow-up tuning should improve precision without restoring mandatory exact title anchors.

## Risks and Unknowns

- Exact title anchor rules are baked into tests and prompts; update only the tests/prompts that directly encode the old contract.
- Hardcoded phrase rules can overfit Agent JDs. Keep the first rules type-based and generic, and only add benchmark-specific examples when they represent a broader class.
- If compiler blocks all non-anchor terms for a JD, stop and update this plan before allowing anchor-only search.
- If `queryability` metadata makes artifacts too noisy, keep it in `QueryTermCandidate` and diagnostics but do not create separate model layers.
- If real CTS results still return zero after cleaner queries, the next issue may be CTS filters or resume-side phrase inventory, not this compiler.
- Broad compiled anchors can reduce precision on samples where exact title search already worked. Future tuning should be evidence-based and must not reintroduce a global fixed exact-title-anchor requirement.

## Stop Rules

- Stop and update this plan if compiler requires orchestrator refactor or new runtime interfaces.
- Do not proceed to benchmark replay while focused tests are failing.
- Do not add new LLM calls to compensate for compiler gaps.
- Do not widen into reflection discovery, verifier, or resume inventory during this phase.
- Do not fix unrelated test failures without user approval.

## Status

- Current milestone: Complete
- Last completed: M5 real CTS replay and comparison notes.
- Next action: Review the precision tradeoff and decide whether to add a narrow precision-tuning follow-up.
- Blockers: None known.

## Done Checklist

- [x] Goal satisfied
- [x] Non-goals preserved
- [x] Compiler metadata implemented
- [x] Query planning enforces compiler admission
- [x] Focused tests pass
- [x] Real CTS benchmark replay completed or explicitly deferred
- [x] Decision log updated
- [x] Risks and unknowns updated
- [x] Status reflects final state
