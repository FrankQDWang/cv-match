# ExecuteSearchPlan

执行单次 CTS 搜索计划，返回候选与页面统计。

## 公式

```text
cts_request_t = {
  query_terms: p_t.query_terms,
  projected_filters: p_t.projected_filters,
  target_new_candidate_count: p_t.target_new_candidate_count
}

raw_candidates_t = CTS.search(cts_request_t)
runtime_filtered_candidates_t =
  apply_runtime_only_constraints(raw_candidates_t, p_t.runtime_only_constraints)

deduplicated_candidates_t =
  deduplicate_by_candidate_id(runtime_filtered_candidates_t)

x_t = {
  raw_candidates: raw_candidates_t,
  deduplicated_candidates: deduplicated_candidates_t,
  search_page_statistics: {
    pages_fetched: page_count(raw_candidates_t),
    duplicate_rate: duplicate_rate(raw_candidates_t, deduplicated_candidates_t),
    latency_ms: wall_clock_latency(raw_candidates_t)
  },
  search_observation: {
    unique_candidate_ids: candidate_ids(deduplicated_candidates_t),
    shortage_after_last_page:
      |deduplicated_candidates_t| < p_t.target_new_candidate_count
  }
}
```

## Notation Legend

```text
p_t := SearchExecutionPlan_t
x_t := SearchExecutionResult_t
```

## Read Set

- `SearchExecutionPlan_t.query_terms`
- `SearchExecutionPlan_t.projected_filters`
- `SearchExecutionPlan_t.runtime_only_constraints`
- `SearchExecutionPlan_t.target_new_candidate_count`

## Derived / Intermediate

- `cts_request_t` 只包含 CTS 原生能执行的请求字段。
- `apply_runtime_only_constraints(...)` 负责执行 CTS 不支持但 runtime 仍要坚持的语义约束。
- `deduplicate_by_candidate_id(...)` 负责把重复命中的候选压回唯一集合，同时保留上游原始命中供审计。
- `shortage_after_last_page` 明确表示“是否没达到本轮期望新增数”，供下游 reflection 与 stop 使用。

## Write Set

- `SearchExecutionResult_t.raw_candidates`
- `SearchExecutionResult_t.deduplicated_candidates`
- `SearchExecutionResult_t.search_page_statistics`
- `SearchExecutionResult_t.search_observation`

## 输入 payload

- [[SearchExecutionPlan_t]]

## 输出 payload

- [[SearchExecutionResult_t]]

## 不确定性边界 / 说明

- 搜索层只负责执行计划，不拥有 branch 选择权，也不重新解释评分口径。

## 相关

- [[operator-map]]
- [[expansion-trace]]
- [[SearchExecutionPlan_t]]
- [[SearchExecutionResult_t]]
