# SearchExecutionResult_t

执行检索计划后返回的候选集合与页面统计。

```text
SearchExecutionResult_t = { raw_candidates, deduplicated_candidates, search_page_statistics, search_observation }
```

## 稳定字段组

- 原始候选：`raw_candidates`
- 去重候选：`deduplicated_candidates`
- 页面统计：`search_page_statistics`
- 搜索观察：`search_observation`

## Direct Producer / Direct Consumers

- Direct producer：[[ExecuteSearchPlan]]
- Direct consumers：[[ScoreSearchResults]]、[[EvaluateBranchOutcome]]、[[ComputeNodeRewardBreakdown]]

## Invariants

- `deduplicated_candidates` 必须是 `raw_candidates` 的去重子集。
- `search_page_statistics` 记录成本事实，不承担语义推断。

## 最小示例

```yaml
search_page_statistics:
  pages_fetched: 2
  duplicate_rate: 0.25
  latency_ms: 1800
search_observation:
  unique_candidate_ids: ["c07", "c19", "c51", "c77"]
  shortage_after_last_page: false
```

## 相关

- [[operator-map]]
- [[SearchExecutionPlan_t]]
- [[ExecuteSearchPlan]]
- [[SearchScoringResult_t]]
