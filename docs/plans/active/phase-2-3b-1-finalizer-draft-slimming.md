# Task: Phase 2.3B.1 Finalizer Draft Slimming

## Goal

把 finalizer 的模型输出从完整 public `FinalResult` 缩成 draft schema，只让模型负责 presentation text：

- top-level `summary`
- per-candidate `resume_id`
- per-candidate `match_summary`
- per-candidate `why_selected`

Runtime 继续拥有并 materialize 现有 public `FinalResult` 的 rank、score、fit bucket、signals、risk flags、source round、run metadata 和排序。

## Why Now

Phase 2.3A Artifact Slimming 已发布为 `0.4.8`。下一步要做的是 Phase 2.3B 的低风险半段：减少 finalizer structured-output 压力，同时保持最终 API/UI/public artifact shape 不变。

仓库证据：

- `src/seektalent/finalize/finalizer.py` 当前让 model 输出完整 `FinalResult`。
- `src/seektalent/models.py` 中 `FinalCandidate` 包含大量 runtime/scoring-owned 字段：`rank`、`final_score`、`fit_bucket`、`strengths`、`weaknesses`、`matched_must_haves`、`matched_preferences`、`risk_flags`、`source_round`。
- `src/seektalent/prompts/finalize.md` 仍要求模型 preserve runtime ranking 和 preserve strengths/weaknesses。
- `tests/test_finalizer_contract.py` 当前 validator 针对完整 `FinalResult`。
- `docs/plans/phase-2-3-artifact-schema-slimming.md` 明确 2.3B 要引入 `FinalResultDraft` / `FinalCandidateDraft`，public `FinalResult` 保持不变。

## Non-goals

- 不做 W&B `benchmark_suite` / `eval_subset` 报表修正。
- 不重跑或关闭 Phase 2.3A artifact size gate。
- 不改 retrieval、CTS filters、query compiler、stop guidance、ranking sort key、scoring schema、reflection schema 或 eval/judge semantics。
- 不改 public `FinalResult` / `FinalCandidate` shape。
- 不给 public result 新增 missing/negative signals 字段。
- 不引入 fallback model chain、网络重试、generic recovery layer 或新抽象框架。
- 不做 Phase 2.3C scoring schema experiment。

## Done Criteria

- 新增 `FinalCandidateDraft` 和 `FinalResultDraft`，模型输出只包含 `summary`、`resume_id`、`match_summary`、`why_selected`。
- `Finalizer._get_agent()` 的 output type 改为 draft schema。
- Finalizer validator 只校验 draft candidate ids/count/order：
  - 不允许 unknown resume ids。
  - 不允许 duplicate resume ids。
  - draft candidate count 必须等于 runtime top candidate count。
  - draft resume id 顺序必须与 runtime ranking 完全一致。
- Finalizer runtime materializes 现有 public `FinalResult`。
- Public `FinalResult` / API / UI mapper tests 不需要改 public shape。
- `finalizer_call.json` 继续 metadata-only，不重新嵌 full payload/output。
- Focused tests 和 full tests 通过。
- 如执行真实 replay，则只用小的 4-row acceptance subset，不跑 full benchmark。

## Repo Entrypoints

Read first:

1. `AGENTS.md`
2. `docs/plans/phase-2-3-artifact-schema-slimming.md`
3. `docs/outputs.md`
4. `src/seektalent/models.py`
5. `src/seektalent/finalize/finalizer.py`
6. `src/seektalent/prompts/finalize.md`
7. `src/seektalent/runtime/orchestrator.py`
8. `tests/test_finalizer_contract.py`
9. `tests/test_llm_lifecycle.py`
10. `tests/test_llm_fail_fast.py`
11. `tests/test_runtime_audit.py`
12. `tests/test_ui_mapper.py`
13. `tests/test_ui_api.py`

Likely edit:

- `src/seektalent/models.py`
- `src/seektalent/finalize/finalizer.py`
- `src/seektalent/prompts/finalize.md`
- `tests/test_finalizer_contract.py`
- `tests/test_llm_lifecycle.py`
- `tests/test_llm_fail_fast.py`
- `tests/test_runtime_audit.py`
- `tests/test_ui_mapper.py`
- `tests/test_ui_api.py`
- This plan file

Allowed only if a direct contract test requires it:

- `tests/test_cli.py`
- `tests/test_api.py`
- `tests/test_runtime_state_flow.py`
- `docs/outputs.md`

Do not edit unless this plan is updated first:

- `src/seektalent/reflection/`
- `src/seektalent/scoring/`
- `src/seektalent/retrieval/`
- `src/seektalent/controller/`
- `src/seektalent/requirements/`
- `src/seektalent_ui/` runtime behavior beyond tests forced by public shape
- `.github/`
- `runs/`
- `artifacts/benchmarks/`

## Current Reality

Observed behavior:

- `Finalizer._get_agent()` uses `build_output_spec(..., FinalResult)`.
- `validate_output()` receives full `FinalResult` and currently checks duplicate ids, unknown ids, contiguous rank, runtime order, source round match, and candidate count.
- `finalize()` returns `result.output` directly.
- `FinalResult` is public shape and is consumed by CLI/API/UI tests.
- Phase 2.3A already made `finalizer_call.json` metadata-only via runtime tracing.

Known invariants:

- Runtime ranking must remain pinned to `scored_candidate_sort_key`: `fit_bucket`, `overall_score`, `must_have_match_score`, `risk_score`, `resume_id`.
- Finalizer must not change candidate membership or ranking order.
- `FinalResult.candidates` must remain in runtime-preserved order.
- Bounded structured-output retry is allowed; fallback model chains are not allowed.

## Target Behavior

- Finalizer model sees the same finalization context but outputs only draft presentation text.
- Runtime builds `FinalResult` from:
  - run metadata from `finalize()` args;
  - ranked candidates from `ranked_candidates`;
  - draft text from model output.
- Runtime-owned mapping:
  - `rank`: list index + 1.
  - `final_score`: use current public scoring convention from existing finalizer/scored candidate mapping.
  - `fit_bucket`: `ScoredCandidate.fit_bucket`.
  - `strengths`: `ScoredCandidate.strengths`.
  - `weaknesses`: `ScoredCandidate.weaknesses`.
  - `matched_must_haves`: `ScoredCandidate.matched_must_haves`.
  - `matched_preferences`: `ScoredCandidate.matched_preferences`.
  - `risk_flags`: `ScoredCandidate.risk_flags`.
  - `source_round`: `ScoredCandidate.source_round`.
  - `match_summary` and `why_selected`: draft fields.

## Milestones

### M1. Confirm Finalizer Mapping Surface

Steps:

- Read `src/seektalent/models.py` around `ScoredCandidate`, `FinalCandidate`, and `FinalResult`.
- Read `src/seektalent/finalize/finalizer.py`.
- Confirm exact source field for `FinalCandidate.final_score`.
- Confirm tests that assert finalizer retries and public final result shape.

Deliverables:

- Update this plan's Decision Log with the selected `final_score` mapping if it is not already obvious.
- List any extra files that must be edited before coding.

Acceptance:

- No implementation starts until the runtime-owned field mapping is explicit.

Validation:

```bash
uv run pytest tests/test_finalizer_contract.py tests/test_llm_fail_fast.py -q
```

Expected: current baseline passes before edits.

### M2. Add Draft Models and Materialization

Steps:

- Add `FinalCandidateDraft` and `FinalResultDraft` near `FinalCandidate` / `FinalResult`.
- Change `Finalizer._get_agent()` output type to `FinalResultDraft`.
- Replace the validator with draft validation:
  - unknown id rejected;
  - duplicate id rejected;
  - incomplete/extra candidate list rejected;
  - out-of-order ids rejected.
- Add a small materialization function in `src/seektalent/finalize/finalizer.py` unless inline code is clearer.
- Keep `finalize()` return type as `FinalResult`.
- Update `src/seektalent/prompts/finalize.md` to tell the model it outputs a draft and does not own runtime fields.

Acceptance:

- Model-facing schema no longer includes rank/score/signals/risk/source round.
- Public `FinalResult` returned by `finalize()` is unchanged in shape.
- Validator failures still use `ModelRetry`.

Validation:

```bash
uv run pytest tests/test_finalizer_contract.py tests/test_llm_fail_fast.py tests/test_llm_lifecycle.py -q
```

Expected: all targeted finalizer lifecycle/fail-fast tests pass.

### M3. Update Runtime/API/UI Tests

Steps:

- Update test fixtures that stub finalizer model output to use draft where they exercise `Finalizer` directly.
- Keep runtime stubs that return public `FinalResult` unchanged unless their type assumptions break.
- Verify Phase 2.3A metadata-only call artifact assertions still pass.
- Do not update UI/API public expectations except for test setup mechanics.

Acceptance:

- Public API/UI tests still see the existing `FinalResult` shape.
- `tests/test_runtime_audit.py` still confirms `finalizer_call.json` has no `user_payload` or `structured_output`.

Validation:

```bash
uv run pytest \
  tests/test_finalizer_contract.py \
  tests/test_llm_lifecycle.py \
  tests/test_llm_fail_fast.py \
  tests/test_runtime_audit.py \
  tests/test_ui_mapper.py \
  tests/test_ui_api.py \
  tests/test_api.py \
  tests/test_cli.py -q
```

Expected: all targeted tests pass.

### M4. Full Local Validation and Optional Replay

Steps:

- Run full local test suite.
- If user authorizes real LLM/CTS validation, run only the 4-row Phase 2.3B acceptance subset with eval enabled; do not run full 12-row eval.
- Compare final candidate count, ids, and order where rows overlap with the latest `0.4.8` acceptance subset.

Validation:

```bash
uv run pytest
```

Expected: `231 passed` or the current full suite count passes.

Optional replay command:

```bash
tmp_jds="$(mktemp /tmp/seektalent_phase_2_3b_finalizer.XXXXXX.jsonl)"
jq -c '
  select(
    .jd_id == "agent_jd_004" or
    .jd_id == "agent_jd_007" or
    .jd_id == "llm_training_jd_001" or
    .jd_id == "bigdata_jd_001"
  )
' artifacts/benchmarks/phase_2_2_pilot.jsonl > "$tmp_jds"

out_dir="runs/phase_2_3b_finalizer_draft_eval_$(date +%Y%m%d_%H%M%S)"
SEEKTALENT_JUDGE_MAX_CONCURRENCY=5 uv run seektalent benchmark \
  --jds-file "$tmp_jds" \
  --env-file .env \
  --output-dir "$out_dir" \
  --benchmark-max-concurrency 1 \
  --enable-eval \
  --json
```

Expected if replay is run:

- 4 rows complete.
- Every row has non-null `evaluation_result`.
- Every row has `final_candidate_count > 0`.
- No finalizer validator retry spike compared with prior acceptance subset.

## Decision Log

- 2026-04-21: Split Phase 2.3B into finalizer-first and reflection-second plans. Finalizer is first because runtime already owns ranking and candidate facts, making this the lower-risk model-facing schema reduction.
- 2026-04-21: Explicitly skipped W&B suite/report correction and no-eval artifact size closure because the user chose speed over Phase 2.3A.1 reporting cleanup.
- 2026-04-21: Confirmed `FinalCandidate.final_score` should be materialized from `ScoredCandidate.overall_score`, matching existing runtime test stubs and downstream markdown/UI consumption.
- 2026-04-21: Implemented finalizer draft output schema and runtime materialization while preserving public `FinalResult` shape. Local validation passed with `uv run pytest` (`231 passed`).
- 2026-04-21: User authorized the 4-row real LLM/CTS replay. Ran eval-enabled subset at `runs/phase_2_3b_finalizer_draft_eval_20260421_115514`; all 4 rows completed with non-null eval, 10 final candidates, finalizer validator retries `0`, and final candidate order matching runtime finalizer context.

## Risks and Unknowns

- `FinalCandidate.final_score` mapping is confirmed as `ScoredCandidate.overall_score`.
- If any downstream UI/API code implicitly depends on model-authored strengths/weaknesses text, stop and record the concrete failing assertion before widening scope.
- If finalizer draft validation increases structured-output retry count on real replay, inspect prompt/schema wording before changing runtime behavior.
- Real LLM replay showed no finalizer validator retry spike. Candidate ids/order changed versus the earlier `0.4.8` replay on overlapping rows, consistent with a fresh live CTS/LLM run; within each new run, final order matched runtime finalizer context exactly.

## Stop Rules

- Stop and update this plan if public `FinalResult` shape must change.
- Stop and ask the user before editing scoring, reflection, retrieval, CTS, or controller code.
- Do not continue to M3 while M2 validation is failing.
- Do not add fallback chains, alternate finalizer schemas, or compatibility readers for old artifacts.
- Do not fix unrelated test failures unless explicitly authorized.

## Status

- Current milestone: Complete
- Last completed: 4-row eval-enabled real LLM/CTS replay at `runs/phase_2_3b_finalizer_draft_eval_20260421_115514`.
- Next action: None.
- Blockers: None.

## Done Checklist

- [x] Goal satisfied
- [x] Non-goals preserved
- [x] Tests or validation commands pass
- [x] Decision log updated
- [x] Risks and unknowns updated
- [x] Status reflects final state
