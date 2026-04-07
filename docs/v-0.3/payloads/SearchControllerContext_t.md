# SearchControllerContext_t

送入控制器的当前分支上下文快照。

```text
SearchControllerContext_t = { active_frontier_node_summary, frontier_head_summary, unmet_requirement_weights, operator_statistics_summary, term_budget_range, fit_gate_constraints }
```

## 稳定字段组

- active node 摘要：`active_frontier_node_summary`
- frontier 头部摘要：`frontier_head_summary`
- 未满足需求权重：`unmet_requirement_weights`
- operator 统计摘要：`operator_statistics_summary`
- term 预算范围：`term_budget_range`
- fit gate 约束：`fit_gate_constraints`

## Direct Producer / Direct Consumers

- Direct producer：[[SelectActiveFrontierNode]]
- Direct consumers：[[GenerateSearchControllerDecision]]

## Invariants

- `SearchControllerContext_t` 是只读快照，不是可回写状态。
- 它只暴露控制器真正需要的字段，不暴露整份 frontier。

## 最小示例

```yaml
active_frontier_node_summary:
  frontier_node_id: "seed_alias"
  selected_operator_name: "must_have_alias"
  node_query_term_pool: ["python backend", "llm application", "rag"]
  node_shortlist_candidate_ids: ["c32", "c44"]
frontier_head_summary:
  open_node_count: 2
  remaining_budget: 3
unmet_requirement_weights:
  retrieval_or_ranking_experience: 0.8
operator_statistics_summary:
  must_have_alias:
    average_reward: 3.8
    times_selected: 1
term_budget_range: [3, 8]
fit_gate_constraints:
  locations: ["Shanghai"]
  min_years: 5
```

## 相关

- [[operator-map]]
- [[FrontierState_t]]
- [[SelectActiveFrontierNode]]
- [[SearchControllerDecision_t]]
