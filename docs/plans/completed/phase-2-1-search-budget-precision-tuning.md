# Task: Phase 2.1 Search Budget and Precision Tuning

## Goal

在保留 Phase 2 lexical compiler 成果的前提下，修复“召回变稳定后 controller 停得太早”和 broad anchor 带来的 precision tradeoff。

业务目标：让 controller 明确知道当前轮次预算、剩余预算、是否允许停止、哪些 high-signal admitted families 还没试；同时让 query planner 优先组合 broad anchor + high-signal framework/core skill，而不是 broad anchor + 泛 domain phrase。

## Why Now

`docs/plans/roadmap.md` 把 Phase 2.1 定为下一步。Phase 2 已经解决 dirty query、exact title anchor 和 zero/low-recall，但真实 CTS replay 记录了新的 precision tradeoff：

- 6 个样本 final candidates 总数从 41 到 60。
- zero-final 样本从 1 个到 0 个。
- `agent_jd_002` 从 0 candidates / 0.0 precision 到 10 candidates / 0.2 precision。
- `agent_jd_006` 从 1 candidate / 0.0 precision 到 10 candidates / 0.9 precision。
- 平均 final precision@10 从约 0.42 到约 0.55。
- `agent_jd_001` 从 0.9 precision 到 0.5 precision，`agent_jd_003` 从 1.0 到 0.8。

当前判断：Phase 2 成功修复召回硬失败；Phase 2.1 只做预算纪律和精确化，不回滚 compiler。

## Non-goals

- 不恢复 “每个 query 必须包含 exact title anchor”。
- 不改 `src/seektalent/retrieval/query_compiler.py` 的准入规则，除非实现中发现 query planner 无法读取现有 metadata。
- 不做 schema slimming；controller/reflection/scorer/finalizer 的 structured output schema 不在本阶段瘦身。
- 不切换 controller/reflection 到 reasoning model，不做模型 A/B。
- 不实现 reflection discovery agent、verifier、session memory、网页/app action harness。
- 不扩 benchmark 到 15-20 条；本阶段只用现有 6 条 Agent JD 做 Phase 2.1 replay。
- 不引入新配置项、数据库、外部服务或抽象接口层。

## Done Criteria

- `ControllerContext` 明确包含当前预算状态：当前轮次、总轮次、当前轮预算占用、当前轮之后剩余轮次、是否进入 80% 预算区间。
- `ControllerContext` 明确包含 deterministic stop guidance：是否允许 stop、原因、已尝试 families、未尝试 high-priority admitted families、productive/zero-gain 轮数、top pool strength。
- Runtime 在 `stop_guidance.can_stop == false` 时不接受 controller stop，而是用已有受控 query selection 继续搜索。
- `search_diagnostics.json` 的 terminal controller summary 能解释 stop decision 看到的 stop guidance。
- `query_plan.py` 优先选择 high-signal non-anchor families：`core_skill` / `framework_tool` 优先于泛 `domain_context`，并继续遵守 admitted/family/query budget 合同。
- Controller prompt 明确要求遵守 budget/stop guidance；进入 80% 预算区间后偏向 exploit/high-signal narrowing，而不是 broad exploration。
- Focused tests 通过；真实 CTS + 真实 LLM replay 完成并把结果写回本计划。

## Repo Entrypoints

Read first:

1. `AGENTS.md`
2. `README.md`
3. `docs/plans/roadmap.md`
4. `docs/plans/completed/phase-2-search-lexical-compiler.md`
5. `src/seektalent/models.py`
6. `src/seektalent/runtime/context_builder.py`
7. `src/seektalent/runtime/orchestrator.py`
8. `src/seektalent/retrieval/query_plan.py`
9. `src/seektalent/prompts/controller.md`
10. `tests/test_context_builder.py`
11. `tests/test_query_plan.py`
12. `tests/test_controller_contract.py`
13. `tests/test_runtime_state_flow.py`
14. `tests/test_runtime_audit.py`

Likely edit:

- `src/seektalent/models.py`
- `src/seektalent/runtime/context_builder.py`
- `src/seektalent/runtime/orchestrator.py`
- `src/seektalent/retrieval/query_plan.py`
- `src/seektalent/prompts/controller.md`
- `tests/test_context_builder.py`
- `tests/test_query_plan.py`
- `tests/test_controller_contract.py`
- `tests/test_runtime_state_flow.py`
- `tests/test_runtime_audit.py`
- This plan file

Allowed only if direct tests require it:

- `tests/test_v02_models.py`
- `tests/test_llm_fail_fast.py`

Do not edit unless this plan is updated first:

- `src/seektalent/retrieval/query_compiler.py`
- `src/seektalent/requirements/`
- `src/seektalent/scoring/`
- `src/seektalent/reflection/`
- `src/seektalent/finalize/`
- `src/seektalent/clients/`
- `src/seektalent_ui/`
- `experiments/`
- `apps/`

Ignore unless evidence says otherwise:

- `runs/` except writing the final Phase 2.1 replay output.
- `.venv/`
- `.pytest_cache/`
- `__pycache__/`
- `dist/`

## Current Reality

Observed behavior:

- `AppSettings` already has `min_rounds=3` and `max_rounds=10`; `max_rounds` is capped at 10.
- `ControllerContext` already has `round_no`, `min_rounds`, `max_rounds`, `is_final_allowed_round`, `target_new`, `query_term_pool`, `current_top_pool`, latest search/reflection views, and `shortage_history`.
- Runtime currently overrides stop only when `round_no < min_rounds`.
- Runtime lets controller stop after `min_rounds` without deterministic coverage/budget guidance.
- `query_plan.py::select_query_terms` and `derive_explore_query_terms` mainly sort by active state, prior usage, priority, first-added round, and term text.
- `search_diagnostics.json` records terminal controller round, stop reason, and response to reflection, but not the stop guidance visible to that controller.

Known invariants:

- Keep the outer workflow controlled and auditable.
- Keep query length budget unchanged: round 1 has 1 anchor + 1 non-anchor; later rounds have 1 anchor + 1 or 2 non-anchors.
- Query terms must still come from compiler-admitted pool and must not repeat a `family`.
- Reflection remains a critic only; it may activate/drop terms, but cannot execute search or bypass compiler.

## Target Behavior

Add one small `StopGuidance` model in `src/seektalent/models.py`:

```python
TopPoolStrength = Literal["empty", "weak", "usable", "strong"]

class StopGuidance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    can_stop: bool
    reason: str
    continue_reasons: list[str] = Field(default_factory=list)
    tried_families: list[str] = Field(default_factory=list)
    untried_admitted_families: list[str] = Field(default_factory=list)
    productive_round_count: int = 0
    zero_gain_round_count: int = 0
    top_pool_strength: TopPoolStrength
```

Extend `ControllerContext` with:

```python
rounds_remaining_after_current: int
budget_used_ratio: float
near_budget_limit: bool
stop_guidance: StopGuidance
```

Budget calculation:

- `rounds_remaining_after_current = max(0, max_rounds - round_no)`
- `budget_used_ratio = round_no / max_rounds`
- `near_budget_limit = budget_used_ratio >= 0.8`

Top pool strength calculation:

- `empty`: no current top candidates.
- `weak`: fewer than 5 current top candidates, or no `fit` candidate.
- `strong`: at least 10 current top candidates and at least 5 candidates with `fit_bucket == "fit"`, `overall_score >= 80`, `must_have_match_score >= 70`, and `risk_score <= 30`.
- `usable`: anything between weak and strong.

Family coverage calculation:

- Build a term index from `run_state.retrieval_state.query_term_pool`.
- `tried_families`: families that appeared in `sent_query_history`.
- `untried_admitted_families`: active admitted non-anchor families in the current pool that are not in `tried_families`, sorted by `(priority, first_added_round, family)`.

Stop guidance rule:

- `can_stop = True` when `round_no >= max_rounds`.
- `can_stop = False` when `round_no < min_rounds`.
- `can_stop = False` when top pool is `empty` or `weak` and `untried_admitted_families` is non-empty.
- `can_stop = False` when top pool is not `strong`, fewer than 2 rounds have been productive, and `untried_admitted_families` is non-empty.
- Otherwise `can_stop = True`.

Runtime enforcement:

- If controller returns `StopControllerDecision` and `controller_context.stop_guidance.can_stop` is false, runtime must convert it to a continue decision using existing safe selection logic.
- The forced continue rationale must mention the stop guidance reason.
- Max-round behavior must not be blocked.

Query precision ordering:

- In `select_query_terms` and `derive_explore_query_terms`, prefer non-anchor `retrieval_role` in this order:
  1. `core_skill`
  2. `framework_tool`
  3. `domain_context`
  4. everything else admitted
- Keep existing family dedupe and active/admitted validation.
- Do not add new compiler families in this phase.

Diagnostics:

- Extend `TerminalControllerRound` or the terminal summary so `search_diagnostics.json["summary"]["terminal_controller"]` includes the terminal `stop_guidance` when a terminal controller stop exists.
- Do not expand every round diagnostic unless needed by tests; `controller_context.json` already stores per-round guidance.

Prompt:

- Update `src/seektalent/prompts/controller.md` to state:
  - if `stop_guidance.can_stop` is false, continue search.
  - stop rationale must cite visible stop guidance facts.
  - when `near_budget_limit` is true, prefer high-signal exploit/narrowing over broad exploration.

## Milestones

### M1. Confirm Baseline and Change Surface

Steps:

- Confirm no active implementation plan conflicts with this plan.
- Re-run targeted baseline tests before implementation.
- Inspect `ControllerContext` construction and all tests that instantiate it directly.

Deliverables:

- Update this plan's decision log with baseline test result.
- Record any extra test file that needs edits.

Acceptance:

- Edit surface is still limited to the likely edit list above.
- No need to change compiler, scoring, reflection, finalizer, or CTS client.

Validation:

```bash
uv run pytest tests/test_context_builder.py tests/test_query_plan.py tests/test_controller_contract.py tests/test_runtime_state_flow.py tests/test_runtime_audit.py
```

Expected: targeted tests pass before implementation, or pre-existing failures are recorded here before proceeding.

### M2. Add Budget Fields and Stop Guidance to Controller Context

Steps:

- Add `TopPoolStrength` and `StopGuidance` to `src/seektalent/models.py`.
- Extend `ControllerContext` with `rounds_remaining_after_current`, `budget_used_ratio`, `near_budget_limit`, and `stop_guidance`.
- Implement stop guidance helpers in `src/seektalent/runtime/context_builder.py` as module-level functions.
- Keep helpers small and deterministic; do not create manager/helper classes.
- Update context-builder/model tests.

Acceptance:

- Controller context JSON includes the new budget and guidance fields.
- `untried_admitted_families` is family-based, not term-based.
- Top pool strength follows the thresholds in this plan.

Validation:

```bash
uv run pytest tests/test_context_builder.py tests/test_v02_models.py
```

Expected: all targeted tests pass.

### M3. Enforce Stop Guidance in Runtime and Diagnostics

Steps:

- In `_run_rounds`, keep the built `controller_context` available when handling the sanitized controller decision.
- If a stop decision arrives while `controller_context.stop_guidance.can_stop` is false, force a continue decision.
- Reuse or minimally adapt `_force_continue_decision`; do not add a second policy engine.
- Preserve existing `round_no < min_rounds` behavior under the same guidance path.
- Include terminal stop guidance in `TerminalControllerRound` or `search_diagnostics.json` terminal summary.
- Update runtime audit/state-flow tests for forced continue and terminal guidance.

Acceptance:

- A controller stop at round 3 of 10 with weak pool and untried admitted families is converted to search.
- A controller stop at max round is allowed.
- A controller stop with strong top pool after `min_rounds` is allowed.
- `search_diagnostics.json` can explain a terminal stop with visible stop guidance.

Validation:

```bash
uv run pytest tests/test_controller_contract.py tests/test_runtime_state_flow.py tests/test_runtime_audit.py
```

Expected: all targeted tests pass.

### M4. Tune Query Planner Ordering and Controller Prompt

Steps:

- Add a small signal-rank helper in `src/seektalent/retrieval/query_plan.py`.
- Apply the helper in `select_query_terms` and `derive_explore_query_terms`.
- Keep canonicalization rules unchanged.
- Update `tests/test_query_plan.py` so high-signal `core_skill` / `framework_tool` terms win over lower-signal `domain_context` terms when both are active and admitted.
- Update `src/seektalent/prompts/controller.md` with budget/stop guidance instructions.

Acceptance:

- Broad anchor + `LangChain` / `Python` / `RAG` style high-signal terms are preferred over broad anchor + generic domain phrases when priorities are otherwise comparable.
- No query can bypass admitted/family/budget validation.
- Prompt change does not introduce new output fields.

Validation:

```bash
uv run pytest tests/test_query_plan.py tests/test_controller_contract.py
```

Expected: all targeted tests pass.

### M5. Final Validation and Real CTS Replay

Steps:

- Run focused tests.
- Run the full test suite if focused tests pass.
- Run real CTS + real LLM replay on the existing 6 Agent JDs.
- Compare against Phase 2 replay and update this plan with the summary path and key metrics.

Validation:

```bash
uv run pytest tests/test_context_builder.py tests/test_query_plan.py tests/test_controller_contract.py tests/test_runtime_state_flow.py tests/test_runtime_audit.py
uv run pytest
uv run seektalent doctor --env-file .env --json
uv run seektalent benchmark \
  --jds-file artifacts/benchmarks/agent_jds.jsonl \
  --env-file .env \
  --output-dir runs/phase_2_1_budget_precision_replay_$(date +%Y%m%d_%H%M%S) \
  --json
```

Expected:

- All task-related tests pass.
- Replay completes all 6 samples.
- zero-final remains 0.
- `agent_jd_002` and `agent_jd_006` do not regress materially from Phase 2.
- `agent_jd_001` and `agent_jd_003` precision improve or the remaining regression is explained by diagnostics.
- If CTS/API/LLM environment fails, record the failure and do not infer quality from missing replay.

## Decision Log

- 2026-04-19: Chose budget/stop guidance before schema slimming and reasoning model A/B because Phase 2 showed recall repaired but controller stopping and precision ordering remain under-modeled.
- 2026-04-19: Keep compiler contract unchanged; Phase 2.1 tunes budget and query ordering without restoring mandatory exact title anchor.
- 2026-04-19: Use deterministic runtime guidance plus prompt instructions, not prompt-only stop advice, because early stop is a control-flow issue.
- 2026-04-19: M1 baseline focused tests passed: `uv run pytest tests/test_context_builder.py tests/test_query_plan.py tests/test_controller_contract.py tests/test_runtime_state_flow.py tests/test_runtime_audit.py` -> 35 passed.
- 2026-04-19: M2 validation passed: `uv run pytest tests/test_context_builder.py tests/test_v02_models.py` -> 3 passed.
- 2026-04-19: M3 validation passed: `uv run pytest tests/test_controller_contract.py tests/test_runtime_state_flow.py tests/test_runtime_audit.py` -> 26 passed.
- 2026-04-19: M4 validation passed: `uv run pytest tests/test_query_plan.py tests/test_controller_contract.py` -> 23 passed.
- 2026-04-19: Final focused validation passed: `uv run pytest tests/test_context_builder.py tests/test_query_plan.py tests/test_controller_contract.py tests/test_runtime_state_flow.py tests/test_runtime_audit.py` -> 38 passed.
- 2026-04-19: Full validation passed: `uv run pytest` -> 211 passed.
- 2026-04-19: Version metadata was bumped to `0.4.4` before replay so W&B report grouping distinguishes this run from `0.4.3`.
- 2026-04-19: W&B hygiene fix: deleted 12 accidental `0.4.3` eval-enabled runs from Apr 18/19. Root cause was benchmark commands using `--enable-eval`, which overrides `.env` `SEEKTALENT_ENABLE_EVAL=false`.
- 2026-04-19: Final replay used `.env` eval setting without `--enable-eval`: `uv run seektalent benchmark --jds-file artifacts/benchmarks/agent_jds.jsonl --env-file .env --output-dir runs/phase_2_1_budget_precision_replay_0_4_4_20260419_151845 --json`.
- 2026-04-19: Final replay completed 6/6 samples. Summary path: `runs/phase_2_1_budget_precision_replay_0_4_4_20260419_151845/benchmark_summary_20260419_160948.json`.
- 2026-04-19: Final replay means for `0.4.4`: avg rounds `3.00`, final total `0.6334`, final p@10 `0.6333`, final ndcg@10 `0.6337`, round1 total `0.2999`, round1 p@10 `0.2833`, round1 ndcg@10 `0.3385`.
- 2026-04-19: W&B report verified after upsert: `Version Means` shows `0.4.4` run count `6`, `0.4.3` run count `6`, and `All versions` run set count `36`.

## Risks and Unknowns

- Top pool strength thresholds are heuristic. If they block useful early stop too often, tune thresholds in this plan before widening scope.
- More forced continuation may increase CTS calls and token cost. Replay must report rounds, sent query count, and final quality.
- Query signal ranking can overfit Agent JDs. Keep the rule role-based, not term-list based.
- If all admitted families are already tried and the pool is still weak, this phase should allow stop rather than loop blindly.
- If precision still drops after Phase 2.1, the next likely work is benchmark expansion and scorer/verifier analysis, not exact-title rollback.

## Stop Rules

- Stop and update this plan if implementation requires changing compiler admission rules.
- Do not proceed to real CTS replay while focused tests are failing.
- Do not add new LLM calls, new model settings, or fallback model chains.
- Do not make schema slimming or reasoning model changes in this phase.
- Do not fix unrelated test failures without user approval.

## Status

- Current milestone: Completed
- Last completed: M5 final validation and real CTS replay.
- Next action: None.
- Blockers: None known.

## Done Checklist

- [x] Goal satisfied
- [x] Non-goals preserved
- [x] Budget fields added to controller context
- [x] Stop guidance implemented and enforced
- [x] Query planner high-signal ordering implemented
- [x] Controller prompt updated without new output schema
- [x] Focused tests pass
- [x] Full test suite passes or unrelated failures are recorded
- [x] Real CTS replay completed or explicitly blocked by environment
- [x] Decision log updated
- [x] Risks and unknowns updated
- [x] Status reflects final state
