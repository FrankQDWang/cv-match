# SelectActiveFrontierNode

从当前 frontier 里选出最值得扩展的节点，并打包控制器上下文。

## 公式

```text
open_nodes_t = [F_t.frontier_nodes[node_id] for node_id in F_t.open_frontier_node_ids]

priority_score_t(n) =
  frontier_priority(n)
  + unmet_requirement_bonus(n, R.must_have_capabilities)
  - saturation_penalty(n, F_t.run_shortlist_candidate_ids)

n_t = argmax_{n in open_nodes_t} priority_score_t(n)

SearchControllerContext_t = {
  active_frontier_node_summary: {
    frontier_node_id: n_t.frontier_node_id,
    selected_operator_name: n_t.selected_operator_name,
    node_query_term_pool: n_t.node_query_term_pool,
    node_shortlist_candidate_ids: n_t.node_shortlist_candidate_ids
  },
  frontier_head_summary: {
    open_node_count: |F_t.open_frontier_node_ids|,
    remaining_budget: F_t.remaining_budget,
    highest_priority_score: priority_score_t(n_t)
  },
  unmet_requirement_weights:
    compute_unmet_requirement_weights(R.must_have_capabilities, n_t.node_shortlist_candidate_ids),
  operator_statistics_summary:
    summarize_operator_statistics(F_t.operator_statistics),
  term_budget_range: derive_term_budget_range(F_t.remaining_budget),
  fit_gate_constraints: P.fit_gate_constraints
}
```

## Notation Legend

```text
R := RequirementSheet
P := ScoringPolicy
F_t := FrontierState_t
n_t := active frontier node
```

## Read Set

- `FrontierState_t.open_frontier_node_ids`
- `FrontierState_t.frontier_nodes`
- `FrontierState_t.run_shortlist_candidate_ids`
- `FrontierState_t.operator_statistics`
- `FrontierState_t.remaining_budget`
- `RequirementSheet.must_have_capabilities`
- `ScoringPolicy.fit_gate_constraints`

## Derived / Intermediate

- `priority_score_t(n)` 只负责选点，不负责生成 query；它结合节点已有 priority、未满足需求空间和 run-global 饱和度。
- `compute_unmet_requirement_weights(...)` 把岗位 must-have 与当前节点已命中的 shortlist 做差，压成控制器可读的权重摘要。
- `summarize_operator_statistics(...)` 只暴露控制器真正需要的 operator 统计摘要，而不是整份 frontier 状态。
- `derive_term_budget_range(...)` 根据剩余预算给出当前轮允许的 term 数量范围。

## Write Set

- `SearchControllerContext_t.active_frontier_node_summary`
- `SearchControllerContext_t.frontier_head_summary`
- `SearchControllerContext_t.unmet_requirement_weights`
- `SearchControllerContext_t.operator_statistics_summary`
- `SearchControllerContext_t.term_budget_range`
- `SearchControllerContext_t.fit_gate_constraints`

## 输入 payload

- [[FrontierState_t]]
- [[RequirementSheet]]
- [[ScoringPolicy]]

## 输出 payload

- [[SearchControllerContext_t]]

## 不确定性边界 / 说明

- 真正的搜索控制权在 runtime 的选点逻辑，不在控制器自由改写 query 的能力。

## 相关

- [[operator-map]]
- [[expansion-trace]]
- [[FrontierState_t]]
- [[RequirementSheet]]
- [[ScoringPolicy]]
- [[SearchControllerContext_t]]
