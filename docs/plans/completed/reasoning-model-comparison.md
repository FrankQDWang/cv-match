# Reasoning Model Comparison

## Goal

验证百炼平台内的 reasoning model 能否提升 controller/reflection 质量，并先确认 reasoning mode 是否还能使用当前严格结构化输出能力。

本阶段的硬前提：

- 公司只提供阿里云百炼平台 API。
- 不使用 OpenAI 官方 Responses 模型做 Phase 2.4。
- 当前主链路基线是百炼 OpenAI-compatible endpoint 上的 `deepseek-v3.2` 非思考模式。
- Reasoning 候选模型优先级：
  1. `deepseek-v3.2` 开启 `enable_thinking=true`
  2. `kimi/kimi-k2.5` 开启 `enable_thinking=true`
  3. 仅当前两者不可用时，再记录其他百炼模型为后续候选，不在本阶段扩大模型矩阵

Phase 2.4 先回答能力问题，再回答效果问题：

1. 百炼 reasoning mode 能不能和严格结构化输出一起用？
2. 如果可以，直接做 single-pass reasoning A/B。
3. 如果不可以，是否采用 two-pass：reasoning model 先产出方案，再由非思考 structured-output model 将“原始 input + reasoning output”转成现有 Pydantic schema。

## Why Now

`docs/plans/roadmap.md` 当前把 Phase 2.4 列为下一步，并要求：

- 先试 reflection，再试 controller。
- 与 `deepseek-chat v3.2` 非推理模型对比。
- 保持 structured output 小，不因为换 reasoning model 扩 JSON schema。
- 如果结构化输出不稳定，先记录失败，不立刻做多模型 fallback 链。

本次修订吸收的新前提和外部证据：

- 百炼 DeepSeek 文档写明 `deepseek-v3.2` 支持通过 `enable_thinking` 参数设置思考/非思考模式；OpenAI Python SDK 需要用 `extra_body={"enable_thinking": true}` 传入该非 OpenAI 标准参数。
- 百炼结构化输出文档写明“思考模式的模型暂不支持结构化输出功能”。
- 百炼错误码文档明确 `Json mode response is not supported when enable_thinking is true`，建议结构化输出时关闭 `enable_thinking`。
- 百炼结构化输出文档的常见问题给出 two-pass 修复方向：思考模型先生成高质量输出；如果不是标准 JSON，再调用支持 JSON Mode 的模型修复。
- 百炼 Kimi 文档写明 `kimi/kimi-k2.5` 是混合思考模型，通过 `enable_thinking` 控制；功能表列出结构化输出支持，但是否支持“思考 + strict JSON schema 同时开启”仍必须真实 API 探针确认。

Repo evidence:

- `.env.example` 和 `src/seektalent/default.env` 当前使用 `OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`，主链路模型为 `openai-chat:deepseek-v3.2`，`SEEKTALENT_REASONING_EFFORT=off`。
- `src/seektalent/llm.py` 当前只把 `openai-chat:deepseek-v3.2` 放入 `NATIVE_OPENAI_CHAT_MODELS`，因此该模型通过 Pydantic AI `NativeOutput(..., strict=True)` 走严格 JSON Schema。
- `pydantic_ai.settings.ModelSettings` 支持 `extra_body`，可以透传百炼的 `enable_thinking`。
- 当前 `build_model_settings()` 只设置通用 `thinking`，不会为百炼 OpenAI-compatible chat 模型自动传 `extra_body={"enable_thinking": ...}`。
- `src/seektalent/controller/react_controller.py` 和 `src/seektalent/reflection/critic.py` 都直接使用现有 schema output，不支持 raw reasoning text -> structured rewrite 的 two-pass 流程。
- `src/seektalent/runtime/orchestrator.py` 已记录 stage、model id、latency、payload char counts、output char counts、validator retry count；但不记录 provider token usage。

External docs used for this plan:

- Bailian structured output: `https://www.alibabacloud.com/help/zh/model-studio/qwen-structured-output`
- Bailian DeepSeek API: `https://help.aliyun.com/zh/model-studio/deepseek-api`
- Bailian Kimi API: `https://help.aliyun.com/zh/model-studio/kimi-api-by-moonshot-ai`
- Bailian error codes: `https://help.aliyun.com/zh/model-studio/error-code`
- Bailian DashScope API reference: `https://www.alibabacloud.com/help/zh/model-studio/qwen-api-via-dashscope`

## Non-goals

- 不使用 `openai-responses:*` 或 OpenAI 官方模型做 A/B。
- 不把百炼之外的 provider 加入 Phase 2.4。
- 不改 retrieval/query compiler/query planner/CTS client。
- 不改 scoring/finalizer/requirements schema。
- 不扩大 controller/reflection structured output schema。
- 不把 Phase 3 bounded reflection discovery 提前做进本阶段。
- 不让 reflection 直接执行 query；reflection 仍只给 advisory signal。
- 不用 prompt-only 大改来弥补 A/B 指标。
- 不新增领域 alias、domain router、surface canonicalization 或人工词表。
- 不新增 benchmark matrix CLI，除非手工 A/B 命令实际成为执行瓶颈。
- 不做 fallback model chain。Two-pass 只有在 M0 证明 reasoning+structured 不可用时才可作为显式 stage 设计。

## Done Criteria

- M0 百炼 capability probe 完成，记录每个候选模型在以下组合下的结果：
  - non-thinking + strict JSON schema
  - thinking + strict JSON schema
  - thinking + JSON object
  - raw thinking text
- 如果 reasoning + strict structured output 可用：
  - 直接进入 single-pass A/B；
  - reflection 先试，controller 后试；
  - 首选 `deepseek-v3.2` thinking，Kimi 只作为次选。
- 如果 reasoning + structured output 不可用：
  - 计划明确采用或拒绝 two-pass；
  - two-pass 必须保持现有 public schema，第二次 structured call 使用非思考模型；
  - 记录新增 LLM call 成本和 failure mode。
- 4-row gate replay 完成并记录 summary path、模型配置、precision/nDCG、final count、final id overlap、rounds、stop quality、latency/char-count cost proxy、validator retries。
- 若 4-row gate 有明确正向或分歧，按计划条件跑 12-row mixed benchmark；否则记录不切默认模型。
- 若决定切默认模型或新增 two-pass code path，更新默认配置/code/version 到 `0.4.11`；若只是实验结论，不 bump version。
- `docs/plans/roadmap.md` 更新 Phase 2.4 状态、summary paths、接受/拒绝理由和下一步。

## Repo Entrypoints

Read first:

1. `AGENTS.md`
2. `README.md`
3. `docs/plans/roadmap.md`
4. `.env.example`
5. `src/seektalent/default.env`
6. `src/seektalent/config.py`
7. `src/seektalent/llm.py`
8. `src/seektalent/controller/react_controller.py`
9. `src/seektalent/reflection/critic.py`
10. `src/seektalent/runtime/orchestrator.py`
11. `src/seektalent/cli.py`
12. `src/seektalent/evaluation.py`
13. `tests/test_llm_provider_config.py`
14. `tests/test_controller_contract.py`
15. `tests/test_reflection_contract.py`
16. `tests/test_runtime_state_flow.py`
17. `tests/test_runtime_audit.py`
18. `tests/test_evaluation.py`

Likely edit:

- `docs/plans/roadmap.md`
- This plan file
- `src/seektalent/config.py`, if adding explicit Bailian thinking stage settings
- `src/seektalent/llm.py`, if mapping Bailian reasoning settings into `extra_body`
- `src/seektalent/controller/react_controller.py`, only if implementing two-pass controller
- `src/seektalent/reflection/critic.py`, only if implementing two-pass reflection
- `src/seektalent/runtime/orchestrator.py`, only if recording two-pass artifacts/call snapshots or provider usage
- `tests/test_llm_provider_config.py`
- `tests/test_controller_contract.py`
- `tests/test_reflection_contract.py`
- `tests/test_runtime_audit.py`
- `.env.example` and `src/seektalent/default.env`, only if accepted default config changes
- `pyproject.toml`, `src/seektalent/__init__.py`, `src/seektalent/evaluation.py`, `tests/test_evaluation.py`, `uv.lock`, only if accepted changes create version `0.4.11`

Do not edit unless this plan is updated first:

- `src/seektalent/retrieval/`
- `src/seektalent/scoring/`
- `src/seektalent/finalize/`
- `src/seektalent/requirements/`
- `src/seektalent/prompts/`, except for a narrow two-pass prompt if M0 requires it
- `src/seektalent/clients/cts_client.py`
- `artifacts/benchmarks/`
- Existing `runs/` artifacts
- `.github/`

## Current Reality

Observed behavior:

- App settings accept provider-qualified model ids such as `openai-chat:deepseek-v3.2`.
- Model id names may contain `/`, so `openai-chat:kimi/kimi-k2.5` is the expected Kimi form if Pydantic AI/OpenAI SDK accepts it.
- Current code loads OpenAI-family models through `OpenAIProvider` pointed at `OPENAI_BASE_URL`, which is currently DashScope compatible mode in `.env.example`.
- Current strict schema path depends on `NativeOutput(output_type, strict=True)` in `src/seektalent/llm.py`.
- `ModelSettings` supports `extra_body`, but current `build_model_settings()` does not use it.
- Pydantic AI strips the generic `thinking` setting unless the model profile declares thinking support; for `openai-chat:deepseek-v3.2` this is not sufficient to control Bailian `enable_thinking`.
- `LLMCallSnapshot` does not store actual token usage. Cost analysis must start with call count, latency, prompt/input/output char counts, and provider-side usage only if captured later.

Known invariants:

- Controller output remains `ControllerDecision`.
- Reflection model-facing output remains `ReflectionAdviceDraft` unless two-pass explicitly separates reasoning text from structured rewrite.
- Runtime stop guidance remains authoritative; reasoning controller cannot bypass `stop_guidance.can_stop`.
- Structured-output retry remains bounded to schema/output validation only.
- Network/tool/provider/rate-limit failures fail loudly.
- Judge model and judge settings stay fixed across A/B variants.

## Target Behavior

- Phase 2.4 starts with a capability probe, not a benchmark.
- If Bailian thinking + strict JSON schema works, use single-pass reasoning A/B.
- If it fails, use the official-style two-pass design only after recording the failure:
  - pass 1: reasoning model produces natural-language decision/advice/draft;
  - pass 2: non-thinking structured-output model converts original context plus pass-1 output into the existing schema.
- Reflection is tested before controller.
- DeepSeek thinking is tested before Kimi thinking.
- Default config changes only after eval evidence supports the change.

## Approach Options

Recommended: capability probe -> single-pass if possible -> two-pass only if required.

- Pros: respects Bailian platform constraints, preserves strict schema when available, and avoids speculative two-call latency.
- Cons: requires a small probe harness before benchmark.
- Use this route.

Alternative: implement two-pass immediately.

- Pros: likely works even if thinking mode cannot structured-output.
- Cons: adds an extra LLM call, extra artifacts, and a new failure point before proving it is necessary.
- Do not start here.

Alternative: keep non-thinking models and skip Phase 2.4.

- Pros: zero implementation risk.
- Cons: does not test the roadmap hypothesis.
- Use only if M0 shows reasoning models are unavailable or too unstable under company API constraints.

## M0 Capability Matrix

Probe only small schemas and tiny prompts. Do not run CTS benchmark in M0.

Model candidates:

| Probe | Model id | Thinking setting | Structured mode | Expected use if pass |
| --- | --- | --- | --- | --- |
| D0 | `deepseek-v3.2` | `enable_thinking=false` | strict `json_schema` | current baseline compatibility |
| D1 | `deepseek-v3.2` | `enable_thinking=true` | strict `json_schema` | single-pass reasoning, first choice |
| D2 | `deepseek-v3.2` | `enable_thinking=true` | `json_object` | fallback structured mode evidence |
| D3 | `deepseek-v3.2` | `enable_thinking=true` | none | pass-1 reasoner for two-pass |
| K0 | `kimi/kimi-k2.5` | `enable_thinking=false` | strict `json_schema` | Kimi structured compatibility |
| K1 | `kimi/kimi-k2.5` | `enable_thinking=true` | strict `json_schema` | single-pass reasoning, second choice |
| K2 | `kimi/kimi-k2.5` | `enable_thinking=true` | `json_object` | fallback structured mode evidence |
| K3 | `kimi/kimi-k2.5` | `enable_thinking=true` | none | pass-1 reasoner for two-pass |

Record for each probe:

- HTTP success/failure.
- Error body if failure.
- Whether `message.content` is valid JSON.
- Whether it matches schema.
- Whether `reasoning_content` exists.
- Usage fields if returned.
- Whether non-streaming works. If it does not, test streaming only for raw thinking text.

## Milestones

### M1. Confirm Local Config and Pydantic AI Integration Surface

Steps:

- Confirm current Bailian endpoint config in `.env.example` and `src/seektalent/default.env`.
- Confirm `openai-chat:deepseek-v3.2` still uses `NativeOutput(..., strict=True)`.
- Confirm `ModelSettings.extra_body` is available in the installed Pydantic AI version.
- Confirm no current code path passes `enable_thinking`.
- Confirm Kimi model id format can be represented as `openai-chat:kimi/kimi-k2.5`.

Acceptance:

- Plan records whether M0 can be a raw OpenAI SDK probe only, or must also include a Pydantic AI probe after a small `extra_body` patch.
- No benchmark starts before this surface is understood.

Validation:

```bash
rg -n "OPENAI_BASE_URL|deepseek-v3.2|kimi|enable_thinking|extra_body|NATIVE_OPENAI_CHAT_MODELS|NativeOutput|build_model_settings" \
  .env.example src/seektalent/default.env src/seektalent src tests

uv run python - <<'PY'
from pydantic_ai.settings import ModelSettings
print("extra_body" in ModelSettings.__optional_keys__)
print(ModelSettings.__optional_keys__)
PY
```

Expected:

- Search output confirms current DeepSeek/Bailian config and no existing `enable_thinking` path.
- Python output includes `True` for `extra_body`.

### M2. Run Raw Bailian Capability Probe

Steps:

- Use the OpenAI Python SDK against `OPENAI_BASE_URL`.
- Load `.env` via `seektalent.config.load_process_env`.
- Use tiny prompts and a tiny schema.
- Write probe output to a new timestamped run-local file under `/tmp`, not to repo artifacts.
- Do not print API keys.

Probe command:

```bash
probe_out="$(mktemp /tmp/seektalent_phase_2_4_bailian_probe.XXXXXX.json)"
PROBE_OUT="$probe_out" uv run python - <<'PY'
import json
import os
from pathlib import Path

from openai import OpenAI

from seektalent.config import load_process_env

load_process_env(".env")
client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ.get("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
)

schema_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "probe_result",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "decision": {"type": "string", "enum": ["continue", "stop"]},
                "reason": {"type": "string"},
            },
            "required": ["decision", "reason"],
            "additionalProperties": False,
        },
    },
}
json_object_format = {"type": "json_object"}
messages = [
    {"role": "system", "content": "Return JSON only. Choose continue when more evidence is useful."},
    {"role": "user", "content": "We have two weak candidates and one untried high-signal search family. Should we continue?"},
]
probes = [
    ("D0", "deepseek-v3.2", False, schema_format),
    ("D1", "deepseek-v3.2", True, schema_format),
    ("D2", "deepseek-v3.2", True, json_object_format),
    ("D3", "deepseek-v3.2", True, None),
    ("K0", "kimi/kimi-k2.5", False, schema_format),
    ("K1", "kimi/kimi-k2.5", True, schema_format),
    ("K2", "kimi/kimi-k2.5", True, json_object_format),
    ("K3", "kimi/kimi-k2.5", True, None),
]
results = []
for probe_id, model, enable_thinking, response_format in probes:
    kwargs = {
        "model": model,
        "messages": messages,
        "extra_body": {"enable_thinking": enable_thinking},
    }
    if response_format is not None:
        kwargs["response_format"] = response_format
    try:
        response = client.chat.completions.create(**kwargs)
        message = response.choices[0].message
        content = message.content or ""
        parsed = None
        parse_error = None
        try:
            parsed = json.loads(content)
        except Exception as exc:  # noqa: BLE001
            parse_error = str(exc)
        results.append({
            "probe_id": probe_id,
            "model": model,
            "enable_thinking": enable_thinking,
            "response_format": response_format["type"] if response_format else "text",
            "ok": True,
            "content": content,
            "parsed": parsed,
            "parse_error": parse_error,
            "reasoning_content_present": bool(getattr(message, "reasoning_content", None)),
            "usage": response.usage.model_dump(mode="json") if response.usage else None,
        })
    except Exception as exc:  # noqa: BLE001
        body = getattr(exc, "body", None)
        results.append({
            "probe_id": probe_id,
            "model": model,
            "enable_thinking": enable_thinking,
            "response_format": response_format["type"] if response_format else "text",
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "body": body,
        })
Path(os.environ["PROBE_OUT"]).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
for item in results:
    print(item["probe_id"], item["model"], item["enable_thinking"], item["response_format"], item["ok"], item.get("error", "")[:160])
print(os.environ["PROBE_OUT"])
PY
```

Acceptance:

- D0 must pass before any A/B, because it validates current strict structured baseline.
- If D1 passes, direct DeepSeek single-pass reasoning is allowed.
- If D1 fails but D3 passes, DeepSeek can be used only as pass-1 reasoner in two-pass.
- Kimi is considered only after DeepSeek result is recorded.
- If all raw thinking probes fail, stop Phase 2.4 and record no model switch.

Validation:

```bash
PROBE_OUT="$probe_out" uv run python - <<'PY'
import json
import os
from pathlib import Path

rows = json.loads(Path(os.environ["PROBE_OUT"]).read_text(encoding="utf-8"))
for row in rows:
    print(row["probe_id"], "ok=", row["ok"], "parsed=", row.get("parsed") is not None, "reasoning=", row.get("reasoning_content_present"))
assert any(row["probe_id"] == "D0" and row["ok"] for row in rows), "D0 strict baseline failed"
PY
```

Expected:

- Prints all probe outcomes.
- D0 succeeds, or the plan stops before benchmark.

### M3. Decide Single-pass vs Two-pass Design

Steps:

- Read the M2 probe JSON.
- Choose exactly one path:
  - Path A: single-pass DeepSeek reasoning if D1 passes.
  - Path B: single-pass Kimi reasoning if D1 fails and K1 passes.
  - Path C: two-pass DeepSeek if D1 fails and D3 passes.
  - Path D: two-pass Kimi only if DeepSeek cannot serve as pass-1 reasoner and K3 passes.
  - Path E: no reasoning A/B if no viable reasoning path exists.
- Update this plan's Decision Log before code changes.

Acceptance:

- No implementation starts until the selected path is recorded.
- If two-pass is selected, the plan records why single-pass is impossible.
- If Kimi is selected, the plan records why DeepSeek was rejected or insufficient.

Validation:

```bash
git diff --check
```

Expected: no whitespace errors.

### M4A. Implement Single-pass Bailian Thinking, If Probe Allows

Run only if M3 chooses Path A or Path B.

Steps:

- Add the smallest settings needed to express Bailian thinking for controller/reflection.
- Prefer explicit stage-level settings over global ambiguity:
  - `SEEKTALENT_CONTROLLER_ENABLE_THINKING`
  - `SEEKTALENT_REFLECTION_ENABLE_THINKING`
- In `build_model_settings()`, for `openai-chat:` Bailian models, set `extra_body={"enable_thinking": true/false}` when the stage requests it.
- Keep `NativeOutput(..., strict=True)` unchanged for the selected model only if the M2 probe proved strict schema works.
- Add tests proving:
  - non-thinking DeepSeek still passes native structured output;
  - thinking setting adds `extra_body.enable_thinking=true`;
  - unrelated OpenAI-family model settings are not changed;
  - controller/reflection can be configured independently.

Acceptance:

- No two-pass code exists in this path.
- No prompt/schema changes are required.
- Existing default config remains non-thinking unless M8 accepts a switch.

Validation:

```bash
uv run pytest tests/test_llm_provider_config.py tests/test_controller_contract.py tests/test_reflection_contract.py tests/test_runtime_audit.py -q
```

Expected: all targeted tests pass.

### M4B. Implement Two-pass Reasoning-to-Structured, If Required

Run only if M3 chooses Path C or Path D.

Steps:

- Keep existing single-pass structured stage as the default.
- Add a small, explicit two-pass mode for reflection first:
  - pass 1: call selected reasoning model with no `response_format`;
  - pass 2: call non-thinking structured model with existing `ReflectionAdviceDraft` schema;
  - pass 2 input is the original `ReflectionContext` plus pass-1 reasoning output.
- Only after reflection two-pass works and eval suggests value, repeat for controller.
- Persist two new metadata artifacts when two-pass is used:
  - `reflection_reasoning_call.json` / `controller_reasoning_call.json`
  - `reflection_reasoning_output.txt` / `controller_reasoning_output.txt`
- Do not persist chain-of-thought if provider marks it as hidden/private. Persist only the model's visible answer content unless product policy explicitly permits reasoning_content storage.
- Fail fast if pass 1 fails.
- Keep bounded structured-output retry only on pass 2 validation.

Acceptance:

- Two-pass is opt-in per stage.
- Existing public schemas and artifacts remain compatible.
- Additional LLM call count and latency are visible in run artifacts.
- No fallback model chain: the selected pass-1 model and selected pass-2 model are explicit config.

Validation:

```bash
uv run pytest \
  tests/test_llm_provider_config.py \
  tests/test_reflection_contract.py \
  tests/test_controller_contract.py \
  tests/test_runtime_audit.py \
  tests/test_runtime_state_flow.py -q
```

Expected: all targeted tests pass.

### M5. Build the 4-row Gate Dataset

Steps:

- Create a temporary JSONL containing:
  - `agent_jd_004`
  - `agent_jd_007`
  - `llm_training_jd_001`
  - `bigdata_jd_001`
- Do not edit `artifacts/benchmarks/phase_2_2_pilot.jsonl`.

Command:

```bash
tmp_jds="$(mktemp /tmp/seektalent_phase_2_4_gate.XXXXXX.jsonl)"
TMP_JDS="$tmp_jds" uv run python - <<'PY'
import json
import os
from pathlib import Path

wanted = {"agent_jd_004", "agent_jd_007", "llm_training_jd_001", "bigdata_jd_001"}
source = Path("artifacts/benchmarks/phase_2_2_pilot.jsonl")
target = Path(os.environ["TMP_JDS"])
seen = []
with source.open(encoding="utf-8") as src, target.open("w", encoding="utf-8") as dst:
    for line in src:
        row = json.loads(line)
        if row.get("jd_id") in wanted:
            seen.append(row["jd_id"])
            dst.write(json.dumps(row, ensure_ascii=False) + "\n")
print(target)
print("\n".join(seen))
assert set(seen) == wanted, seen
PY
wc -l "$tmp_jds"
```

Expected: line count is `4`.

### M6. Run 4-row A/B Gate

Steps:

- Run fresh A0 with current non-thinking baseline.
- Run B1 reflection first using selected reasoning path.
- Analyze B1 before controller.
- Run C1 controller only if B1 is stable or if the plan explicitly records why controller should still be tested.
- Keep requirements/scoring/finalize/judge fixed across variants.
- Use benchmark row concurrency `1` and judge concurrency `5`.

Baseline command shape:

```bash
out_dir="runs/phase_2_4_a0_bailian_deepseek_non_thinking_gate_$(date +%Y%m%d_%H%M%S)"
SEEKTALENT_REQUIREMENTS_MODEL=openai-chat:deepseek-v3.2 \
SEEKTALENT_CONTROLLER_MODEL=openai-chat:deepseek-v3.2 \
SEEKTALENT_SCORING_MODEL=openai-chat:deepseek-v3.2 \
SEEKTALENT_FINALIZE_MODEL=openai-chat:deepseek-v3.2 \
SEEKTALENT_REFLECTION_MODEL=openai-chat:deepseek-v3.2 \
SEEKTALENT_REASONING_EFFORT=off \
SEEKTALENT_JUDGE_MAX_CONCURRENCY=5 \
uv run seektalent benchmark \
  --jds-file "$tmp_jds" \
  --output-dir "$out_dir" \
  --benchmark-max-concurrency 1 \
  --enable-eval \
  --enable-reflection \
  --json
```

Variant commands must be added to this plan after M3 selects Path A/B/C/D, because the exact env vars differ for single-pass versus two-pass.

Acceptance:

- 4/4 rows complete with non-null `evaluation_result`.
- No new zero-final regression versus A0.
- Validator retries do not materially increase.
- Stop guidance remains enforced.
- For two-pass, added call latency/cost is recorded separately from structured pass latency.

Validation:

```bash
SUMMARY="$(find "$out_dir" -maxdepth 1 -name 'benchmark_summary_*.json' | sort | tail -1)"
SUMMARY="$SUMMARY" uv run python - <<'PY'
import json
import os
from pathlib import Path

summary = json.loads(Path(os.environ["SUMMARY"]).read_text(encoding="utf-8"))
runs = summary["runs"]
assert len(runs) == 4, len(runs)
assert all(row["evaluation_result"] for row in runs)
for row in runs:
    final = row["evaluation_result"]["final"]
    print(row["jd_id"], row["run_id"], len(final["candidates"]), final["total_score"], final["precision_at_10"], final["ndcg_at_10"])
print("summary", os.environ["SUMMARY"])
PY
```

Expected: prints four rows and no assertion failure.

### M7. Analyze Gate Results

Steps:

- Compare A0/B1/C1 by JD:
  - final total;
  - precision@10;
  - nDCG@10;
  - final candidate count;
  - final id overlap;
  - rounds executed;
  - stop reason;
  - controller/reflection validator retries;
  - controller/reflection call latency and char counts;
  - provider usage if available.
- Inspect at least one high-change row:
  - `search_diagnostics.json`
  - `rounds/*/controller_decision.json`
  - `rounds/*/reflection_advice.json`
  - `rounds/*/round_review.md`
  - `final_candidates.json`

Acceptance:

- A variant qualifies for 12-row only if:
  - no zero-final regression;
  - schema failures are zero;
  - validator retries are stable;
  - average final total is flat or better versus A0, or a difficult Agent row improves with documented tradeoff;
  - stop quality is not worse;
  - added latency/call cost does not dominate the observed quality gain.
- Reject if average final total drops by more than `0.08`, or any single row drops by more than `0.20` without trace evidence.

Validation:

```bash
uv run --group dev python -m pytest tests/test_llm_provider_config.py tests/test_controller_contract.py tests/test_reflection_contract.py -q
git diff --check
```

Expected: tests pass and no whitespace errors.

### M8. Optional 12-row Acceptance Replay

Run only for variants that pass M7.

Steps:

- Use `artifacts/benchmarks/phase_2_2_pilot.jsonl`.
- Run fresh same-day A0 12-row if none exists for Phase 2.4.
- Run the selected B/C variant with benchmark concurrency `1` and judge concurrency `5`.
- Store outputs under versioned names:
  - `runs/phase_2_4_a0_bailian_deepseek_non_thinking_12row_*`
  - `runs/phase_2_4_b1_SELECTED_REASONING_PATH_12row_*`
  - `runs/phase_2_4_c1_SELECTED_REASONING_PATH_12row_*`

Acceptance:

- 12/12 rows complete with non-null `evaluation_result`.
- No new zero-final regression versus A0.
- Difficult Agent rows show enough lift to justify reasoning cost, or the variant is rejected.
- Bigdata controls do not show broad precision regression.

Validation:

```bash
SUMMARY="$(find "$out_dir" -maxdepth 1 -name 'benchmark_summary_*.json' | sort | tail -1)"
SUMMARY="$SUMMARY" uv run python - <<'PY'
import json
import os
from pathlib import Path

summary = json.loads(Path(os.environ["SUMMARY"]).read_text(encoding="utf-8"))
runs = summary["runs"]
assert len(runs) == 12, len(runs)
assert all(row["evaluation_result"] for row in runs)
zero = []
for row in runs:
    final = row["evaluation_result"]["final"]
    if not final["candidates"]:
        zero.append(row["jd_id"])
    print(row["jd_id"], len(final["candidates"]), final["total_score"], final["precision_at_10"], final["ndcg_at_10"])
print("zero_final", zero)
print("summary", os.environ["SUMMARY"])
PY
```

Expected: prints 12 rows, zero-final list, and summary path.

### M9. Apply Accepted Default/Code Change, If Any

Run only if M7/M8 supports changing defaults or adding two-pass.

Steps:

- If single-pass thinking is accepted:
  - update default config only for the accepted stage(s);
  - keep non-target stages non-thinking;
  - update `.env.example` and `src/seektalent/default.env`.
- If two-pass is accepted:
  - keep it opt-in unless 12-row evidence strongly supports default-on;
  - document extra call cost in `docs/outputs.md` if new artifacts are added.
- Bump version to `0.4.11` only when code/default config changes.
- Update version files:
  - `pyproject.toml`
  - `src/seektalent/__init__.py`
  - fallback in `src/seektalent/evaluation.py`
  - `tests/test_evaluation.py`
  - `uv.lock`
- Update `docs/plans/roadmap.md` and this plan.

Acceptance:

- `seektalent init` default env mirrors `.env.example`.
- `uv run seektalent version` prints `0.4.11` if version was bumped.
- Run config artifacts expose accepted Bailian thinking/two-pass settings.
- No unrelated defaults change.

Validation:

```bash
uv run seektalent version
uv run pytest tests/test_cli.py tests/test_llm_provider_config.py tests/test_runtime_audit.py tests/test_evaluation.py -q
uv run --group dev python tools/check_arch_imports.py
uv run --group dev ruff check src tests experiments
uv run --group dev ty check src tests
uv run --group dev python -m pytest -q
```

Expected:

- Version command prints `0.4.11` if M9 ran; otherwise `0.4.10`.
- All checks pass.

### M10. Close the Experiment in Docs

Steps:

- Update this plan with:
  - M0 probe output path and summarized results;
  - selected path A/B/C/D/E;
  - A/B summary paths;
  - accepted/rejected variants;
  - metric table;
  - stop quality notes;
  - validator retry notes;
  - latency/char-count/provider-usage notes;
  - final default config decision.
- Update `docs/plans/roadmap.md` Phase 2.4 status.
- If no default/code changes were accepted, explicitly record "no version bump".

Acceptance:

- A fresh agent can understand Phase 2.4 outcome from docs and run artifacts alone.
- Roadmap no longer lists Phase 2.4 as pending after the experiment is accepted or rejected.

Validation:

```bash
git diff --check
git status --short
```

Expected:

- No whitespace errors.
- Git status contains only planned docs/config/code/version/lockfile changes.

## Decision Log

- 2026-04-21: Rejected the earlier OpenAI Responses A/B framing because company API access is limited to Aliyun Bailian.
- 2026-04-21: Phase 2.4 must begin with Bailian capability probing before any benchmark, because official docs indicate thinking mode conflicts with structured output while model-specific pages list overlapping capabilities.
- 2026-04-21: Reasoning model priority is DeepSeek `deepseek-v3.2` thinking first, Kimi `kimi/kimi-k2.5` thinking second.
- 2026-04-21: If thinking + strict schema fails, the only allowed alternative is an explicit two-pass design: reasoning text first, non-thinking structured rewrite second.
- 2026-04-21: Two-pass is not a fallback chain. It is a selected stage mode and must fail fast when either pass fails.
- 2026-04-21: M1 confirmed local Bailian config, strict `NativeOutput(..., strict=True)` for `openai-chat:deepseek-v3.2`, `ModelSettings.extra_body` support, and no existing `enable_thinking` path.
- 2026-04-21: M2 raw Bailian probe wrote `/tmp/seektalent_phase_2_4_bailian_probe.XXXXXX.json`. DeepSeek D0 non-thinking strict schema passed; D1 thinking strict schema also passed and returned `reasoning_content`; D2 JSON object passed transport but did not satisfy the strict schema; D3 raw text passed. Kimi K0-K3 all failed with product-not-activated `invalid_parameter_error`.
- 2026-04-21: M3 selected Path A: single-pass DeepSeek thinking for A/B. Two-pass was not implemented because D1 proved strict structured output works with DeepSeek thinking on this account.
- 2026-04-21: M4A added stage flags: `SEEKTALENT_CONTROLLER_ENABLE_THINKING` and `SEEKTALENT_REFLECTION_ENABLE_THINKING`.
- 2026-04-21: Corrected experiment framing after review: the first executed A0/B1 runs changed judge to `openai-chat:deepseek-v3.2`. This violates the invariant that judge model/settings stay fixed across A/B variants. Those runs can be used only as provider capability and runtime smoke evidence, not as Phase 2.4 quality acceptance evidence.
- 2026-04-21: The invalid fixed-judge run set was: A0 `runs/phase_2_4_a0_bailian_deepseek_non_thinking_gate_local_20260421_154659/benchmark_summary_20260421_160129.json`, whose summary reports `judge_model=openai-chat:deepseek-v3.2`; B1 `runs/phase_2_4_b1_deepseek_reflection_thinking_gate_local_20260421_160145`, whose `run_config.json` files also report `judge_model=openai-chat:deepseek-v3.2`.
- 2026-04-21: B1 smoke still showed no observed reflection schema failures in completed calls, but reflection latencies were high: `21.9s`, `19.7s`, `39.0s`, `36.8s`, `23.2s`, `31.5s`, `87.8s`, plus `33.6s` in the incomplete row.
- 2026-04-21: After user direction to save time, the stage plan changed from staged A0/B1/C1 to a direct default-on gate: controller and reflection use DeepSeek thinking by default, judge stays unchanged from `.env`, and version bumps to `0.4.11`.
- 2026-04-21: 0.4.11 fixed-judge 4-row gate completed at `runs/phase_2_4_0_4_11_controller_reflection_thinking_gate_20260421_164528/benchmark_summary_20260421_173854.json`. All four rows used `judge_model=openai-responses:gpt-5.4`; all run configs show controller/reflection thinking enabled; W&B upload completed for all rows.
- 2026-04-21: Effect attribution remains limited because this was a direct default-on gate, not a fresh same-day A0 versus B/C A/B. The valid conclusion is operational: DeepSeek thinking for controller+reflection is compatible with strict output and completed 4/4 fixed-judge eval rows without schema failures.

## Execution Results

Capability probe:

| Probe | Model | Thinking | Structured mode | Result | Notes |
| --- | --- | ---: | --- | --- | --- |
| D0 | `deepseek-v3.2` | false | strict `json_schema` | pass | Baseline strict schema compatible. |
| D1 | `deepseek-v3.2` | true | strict `json_schema` | pass | Selected single-pass path; `reasoning_content` present. |
| D2 | `deepseek-v3.2` | true | `json_object` | transport pass | Parsed JSON but not the strict probe schema. |
| D3 | `deepseek-v3.2` | true | none | pass | Raw reasoner path available but unused. |
| K0-K3 | `kimi/kimi-k2.5` | mixed | mixed | fail | Account/product not activated; not treated as a model capability rejection. |

Implemented changes:

- `src/seektalent/config.py` accepts `controller_enable_thinking` and `reflection_enable_thinking`.
- `src/seektalent/llm.py` maps selected Bailian thinking-capable model ids to `extra_body={"enable_thinking": ...}` when a stage flag is passed.
- `src/seektalent/controller/react_controller.py` and `src/seektalent/reflection/critic.py` pass their independent stage flags into model settings.
- `src/seektalent/runtime/orchestrator.py` records both flags in new run configs.
- `.env`, `.env.example`, and `src/seektalent/default.env` are synchronized with both flags set to `true` for the 0.4.11 default-on gate.
- `pyproject.toml`, `src/seektalent/__init__.py`, `src/seektalent/evaluation.py`, `tests/test_evaluation.py`, and `uv.lock` are bumped to `0.4.11`.

A0 smoke metrics, not acceptance metrics because judge was changed:

| JD | Run | Final candidates | Final total | Precision@10 | nDCG@10 |
| --- | --- | ---: | ---: | ---: | ---: |
| `agent_jd_004` | `cf6aa069` | 10 | 0.4614 | 0.5000 | 0.3713 |
| `agent_jd_007` | `1d2ea8d2` | 10 | 0.5073 | 0.5000 | 0.5243 |
| `llm_training_jd_001` | `8901730f` | 10 | 0.3572 | 0.3000 | 0.4907 |
| `bigdata_jd_001` | `8945d43b` | 10 | 0.5891 | 0.6000 | 0.5635 |
| Average | - | 10 | 0.4787 | 0.4750 | 0.4874 |

B1 smoke result, not acceptance result because judge was changed:

- Variant: DeepSeek single-pass strict structured output, `SEEKTALENT_REFLECTION_ENABLE_THINKING=true`, `SEEKTALENT_CONTROLLER_ENABLE_THINKING=false`.
- Judge config used in this run: `openai-chat:deepseek-v3.2` through Bailian, which is invalid for A/B acceptance.
- Completed run directories: `20260421_160146_b83e19fa`, `20260421_160621_51b965a6`.
- Incomplete run directory: `20260421_161158_175a1c43`.
- Failure mode: the benchmark did not finish 4/4 rows and produced no `benchmark_summary_*.json`.
- Decision at the time: keep default thinking flags disabled until a fixed-judge run exists. This was superseded by the later user-directed 0.4.11 direct default-on gate below.

0.4.11 direct default-on fixed-judge gate:

- Variant: DeepSeek single-pass strict structured output, `SEEKTALENT_CONTROLLER_ENABLE_THINKING=true`, `SEEKTALENT_REFLECTION_ENABLE_THINKING=true`.
- Version: `0.4.11`.
- Judge config: unchanged from `.env`, `openai-responses:gpt-5.4`.
- Benchmark row concurrency: 1.
- Judge concurrency: 5.
- Summary: `runs/phase_2_4_0_4_11_controller_reflection_thinking_gate_20260421_164528/benchmark_summary_20260421_173854.json`.
- W&B runs: `438deec1` / `at8tdi4i`, `c7ebee24` / `0a6j03dv`, `063c2268` / `hlo332tl`, `c27f02d7` / `ngloojq4`.
- W&B report: `https://wandb.ai/frankqdwang1-personal-creations/seektalent/reports/SeekTalent-Version-Metrics--VmlldzoxNjUzODMyOA==`.

| JD | Run | Final candidates | Final total | Precision@10 | nDCG@10 | Rounds |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `agent_jd_004` | `438deec1` | 8 | 0.2780 | 0.2000 | 0.4599 | 3 |
| `agent_jd_007` | `c7ebee24` | 10 | 0.3374 | 0.3000 | 0.4248 | 3 |
| `llm_training_jd_001` | `063c2268` | 10 | 0.5890 | 0.6000 | 0.5634 | 4 |
| `bigdata_jd_001` | `c27f02d7` | 10 | 0.6547 | 0.7000 | 0.5490 | 3 |
| Average | - | 9.50 | 0.4648 | 0.4500 | 0.4993 | 3.25 |

Gate conclusion:

- 4/4 rows completed eval and uploaded to W&B.
- zero-final = 0.
- All four `run_config.json` files show `controller_enable_thinking=true`, `reflection_enable_thinking=true`, `enable_eval=true`, and `enable_reflection=true`.
- All four eval results show `judge_model=openai-responses:gpt-5.4`.
- No structured-output/schema failure was observed.
- This supports the 0.4.11 operational switch, but it is not a clean effect A/B against a same-day non-thinking baseline.

## Risks and Unknowns

- Bailian docs are ambiguous in general, but this account's live probe confirmed `deepseek-v3.2` thinking plus strict `json_schema` works for the tiny probe.
- Kimi remains unknown because this account has not activated the product. Do not infer Kimi model capability from the activation error.
- Pydantic AI generic `thinking` does not map to Bailian `enable_thinking`; the implementation uses `extra_body`.
- Provider token usage may be available from raw SDK responses but is not currently persisted in `LLMCallSnapshot`.
- Reasoning controller/reflection materially increases wall-clock time. The 0.4.11 4-row gate took about 54 minutes at benchmark row concurrency 1, with several reflection/controller calls above 80s and one reflection call around 169s.
- Two-pass remains unimplemented and untested because DeepSeek single-pass strict schema worked; it should only be revived if a future model fails strict schema in thinking mode.
- Persisting visible reasoning output can leak sensitive reasoning. Persist only visible answer content by default; do not persist hidden/private reasoning content.
- Live CTS/LLM runs are nondeterministic. Interpret metric changes with candidate overlap and trace evidence.

## Stop Rules

- Stop if D0 non-thinking strict schema probe fails; current baseline assumption is invalid.
- Stop if all reasoning probes fail.
- Stop if thinking + structured probe returns provider errors and no raw thinking text path works.
- Stop if Pydantic AI cannot represent or call the selected Bailian model id without broad provider rewrites.
- Stop if any A/B variant hits structured-output failures; record failure instead of adding fallback chains.
- Stop if focused tests fail for unrelated reasons; do not fold unrelated fixes into Phase 2.4.
- Defaults were changed only after explicit user direction to run a direct 0.4.11 default-on gate. Any future quality claim still needs either a fresh A/B baseline or a broader replay.
- Do not edit retrieval/scoring/finalizer/requirements files without updating this plan first.

## Status

- Current milestone: M10 documentation closeout.
- Last completed: 0.4.11 direct default-on fixed-judge 4-row gate.
- Next action: decide separately whether to run a 12-row replay or proceed to Phase 3. Do not interpret the 4-row gate as a clean A/B lift estimate.
- Blockers: Kimi product not activated; clean same-day non-thinking baseline was skipped by user direction.

## Done Checklist

- [x] M1 local config and Pydantic AI integration surface confirmed
- [x] M2 raw Bailian capability probe completed
- [x] M3 single-pass/two-pass/no-go path selected
- [x] M4A single-pass implemented, or skipped with reason
- [x] M4B two-pass skipped because DeepSeek thinking strict schema passed
- [x] M5 4-row gate dataset created
- [x] M6 fixed-judge 4-row gate completed
- [x] M7 fixed-judge gate analysis recorded
- [x] M8 optional 12-row replay skipped by user direction
- [x] M9 default-on and version bump completed for `0.4.11`
- [x] M10 roadmap and plan closed
- [x] Goal satisfied for the direct 0.4.11 gate
- [x] Non-goals preserved
- [x] Validation commands pass
- [x] Decision log updated
- [x] Risks and unknowns updated
- [x] Status reflects final state
