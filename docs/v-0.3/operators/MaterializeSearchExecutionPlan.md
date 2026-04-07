# MaterializeSearchExecutionPlan

把控制器决策物化成可执行 child 检索计划。

## 公式

```text
parent_node_t = F_t.frontier_nodes[d_t.target_frontier_node_id]
base_query_terms_t = parent_node_t.node_query_term_pool
additional_terms_t = deduplicate(drop_empty(d_t.operator_args.additional_terms))
requested_target_new_t =
  coalesce(d_t.operator_args.target_new_candidate_count, runtime_search_budget.default_target_new_candidate_count)

query_terms_t =
  clamp_term_budget(
    deduplicate(base_query_terms_t ∪ additional_terms_t),
    runtime_term_budget_range
  )

projected_filters_t = R.hard_constraints

runtime_only_constraints_t = {
  must_have_keywords:
    deduplicate(R.must_have_capabilities ∪ additional_terms_t)
}

target_new_t =
  min(requested_target_new_t, runtime_search_budget.max_target_new_candidate_count)

semantic_hash_t =
  hash(d_t.selected_operator_name, query_terms_t, projected_filters_t, runtime_only_constraints_t)

p_t = {
  query_terms: query_terms_t,
  projected_filters: projected_filters_t,
  runtime_only_constraints: runtime_only_constraints_t,
  target_new_candidate_count: target_new_t,
  semantic_hash: semantic_hash_t,
  child_frontier_node_stub: {
    frontier_node_id: derive_child_id(parent_node_t.frontier_node_id, semantic_hash_t),
    parent_frontier_node_id: parent_node_t.frontier_node_id,
    selected_operator_name: d_t.selected_operator_name
  }
}
```

## Notation Legend

```text
R := RequirementSheet
F_t := FrontierState_t
d_t := SearchControllerDecision_t
p_t := SearchExecutionPlan_t
```

## Read Set

- `FrontierState_t.frontier_nodes`
- `RequirementSheet.hard_constraints`
- `RequirementSheet.must_have_capabilities`
- `SearchControllerDecision_t.target_frontier_node_id`
- `SearchControllerDecision_t.selected_operator_name`
- `SearchControllerDecision_t.operator_args`
- `runtime_term_budget_range`
- `runtime_search_budget`

## Derived / Intermediate

- `base_query_terms_t` 来自 parent node，保证 child plan 不是凭空造 query。
- `additional_terms_t` 只接受当前 operator patch 允许新增的词，不接受游离 term source。
- `requested_target_new_t` 先读控制器 patch，如果草稿没给，再退回 runtime 默认值。
- `clamp_term_budget(...)` 负责把 term 数量压回 runtime 允许范围。
- `projected_filters_t` 只复制稳定硬约束；不把 runtime-only 约束直接塞进 CTS 可下推 filter。
- `runtime_only_constraints_t.must_have_keywords` 明确由岗位 must-have 和新增 term 合并得到，只供 runtime 过滤与审计。
- `semantic_hash_t` 是本次 child plan 的语义签名，后续 dedupe 与 frontier update 都围绕它展开。

## Write Set

- `SearchExecutionPlan_t.query_terms`
- `SearchExecutionPlan_t.projected_filters`
- `SearchExecutionPlan_t.runtime_only_constraints`
- `SearchExecutionPlan_t.target_new_candidate_count`
- `SearchExecutionPlan_t.semantic_hash`
- `SearchExecutionPlan_t.child_frontier_node_stub`

## 输入 payload

- [[FrontierState_t]]
- [[RequirementSheet]]
- [[SearchControllerDecision_t]]

## 输出 payload

- [[SearchExecutionPlan_t]]

## 不确定性边界 / 说明

- `target_new_candidate_count` 与 `semantic_hash` 在这里冻结，执行层不再读游离变量。

## 相关

- [[operator-map]]
- [[expansion-trace]]
- [[FrontierState_t]]
- [[RequirementSheet]]
- [[SearchControllerDecision_t]]
- [[SearchExecutionPlan_t]]
