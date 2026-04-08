# SearchRunSummaryDraft_t

`SearchRunFinalizationLLM` 输出的最终总结草稿。

```text
SearchRunSummaryDraft_t = { run_summary }
```

## 稳定字段组

- 运行总结草稿：`run_summary`

## Direct Producer / Direct Consumers

- Direct producer：SearchRunFinalizationLLM
- Direct consumers：[[FinalizeSearchRun]]

## Invariants

- `SearchRunSummaryDraft_t` 只承载解释性总结，不承载 shortlist 事实或 stop fact。
- 它必须通过 provider-native strict structured output 产出，不允许退回自由文本或 prompt JSON。
- 最终 `final_shortlist_candidate_ids` 与 `stop_reason` 由 runtime 持有并直接写入 `SearchRunResult`，不接受 LLM 改写。

## 最小示例

```yaml
run_summary: "must-have 已覆盖，ranking 背景得到补强，当前 shortlist 可进入人工审阅。"
```

## 相关

- [[FinalizeSearchRun]]
- [[SearchRunResult]]
- [[FrontierState_t1]]
