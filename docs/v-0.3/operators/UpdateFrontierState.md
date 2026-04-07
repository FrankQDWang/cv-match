# UpdateFrontierState

把一次扩展的结果回写到 frontier，并生成下一状态。

## 公式

```text
parent_node_t =
  F_t.frontier_nodes[p_t.child_frontier_node_stub.parent_frontier_node_id]

child_frontier_node_t = {
  frontier_node_id: p_t.child_frontier_node_stub.frontier_node_id,
  parent_frontier_node_id: p_t.child_frontier_node_stub.parent_frontier_node_id,
  selected_operator_name: p_t.child_frontier_node_stub.selected_operator_name,
  node_query_term_pool: deduplicate(parent_node_t.node_query_term_pool ∪ p_t.query_terms),
  parent_shortlist_candidate_ids: parent_node_t.node_shortlist_candidate_ids,
  node_shortlist_candidate_ids: y_t.node_shortlist_candidate_ids,
  previous_branch_evaluation: a_t,
  reward_breakdown: b_t,
  status: "closed" if a_t.branch_exhausted else "open"
}

updated_frontier_nodes_t =
  replace_status(F_t.frontier_nodes, parent_node_t.frontier_node_id, "closed")
  then upsert child_frontier_node_t

F_{t+1} = {
  frontier_nodes: updated_frontier_nodes_t,
  open_frontier_node_ids:
    (F_t.open_frontier_node_ids - {parent_node_t.frontier_node_id})
    ∪ ({child_frontier_node_t.frontier_node_id} if child_frontier_node_t.status = "open" else {}),
  closed_frontier_node_ids:
    F_t.closed_frontier_node_ids ∪ {parent_node_t.frontier_node_id},
  run_term_catalog: F_t.run_term_catalog ∪ set(p_t.query_terms),
  run_shortlist_candidate_ids:
    merge_run_shortlist(F_t.run_shortlist_candidate_ids, y_t.node_shortlist_candidate_ids),
  semantic_hashes_seen: F_t.semantic_hashes_seen ∪ {p_t.semantic_hash},
  operator_statistics:
    accumulate_operator_statistics(F_t.operator_statistics, child_frontier_node_t.selected_operator_name, b_t.reward_score),
  remaining_budget: F_t.remaining_budget - 1
}
```

## Notation Legend

```text
F_t := FrontierState_t
F_{t+1} := FrontierState_t1
p_t := SearchExecutionPlan_t
y_t := SearchScoringResult_t
a_t := BranchEvaluation_t
b_t := NodeRewardBreakdown_t
```

## Read Set

- `FrontierState_t.frontier_nodes`
- `FrontierState_t.open_frontier_node_ids`
- `FrontierState_t.closed_frontier_node_ids`
- `FrontierState_t.run_term_catalog`
- `FrontierState_t.run_shortlist_candidate_ids`
- `FrontierState_t.semantic_hashes_seen`
- `FrontierState_t.operator_statistics`
- `FrontierState_t.remaining_budget`
- `SearchExecutionPlan_t.query_terms`
- `SearchExecutionPlan_t.semantic_hash`
- `SearchExecutionPlan_t.child_frontier_node_stub`
- `SearchScoringResult_t.node_shortlist_candidate_ids`
- `BranchEvaluation_t.*`
- `NodeRewardBreakdown_t.*`

## Derived / Intermediate

- `parent_shortlist_candidate_ids` 在 child node 上显式快照化，避免后续再回头猜 parent baseline。
- `merge_run_shortlist(...)` 负责把 node-local shortlist 合并进 run-global shortlist，同时维持稳定去重与排序规则。
- `accumulate_operator_statistics(...)` 把本轮 reward 写回 operator 统计，供下一轮选点与控制器上下文使用。
- child 节点是否立刻进入 `closed` 由 `a_t.branch_exhausted` 决定，不再依赖隐式 side effect。

## Write Set

- `FrontierState_t1.frontier_nodes`
- `FrontierState_t1.open_frontier_node_ids`
- `FrontierState_t1.closed_frontier_node_ids`
- `FrontierState_t1.run_term_catalog`
- `FrontierState_t1.run_shortlist_candidate_ids`
- `FrontierState_t1.semantic_hashes_seen`
- `FrontierState_t1.operator_statistics`
- `FrontierState_t1.remaining_budget`

## 输入 payload

- [[FrontierState_t]]
- [[SearchExecutionPlan_t]]
- [[SearchScoringResult_t]]
- [[BranchEvaluation_t]]
- [[NodeRewardBreakdown_t]]

## 输出 payload

- [[FrontierState_t1]]

## 不确定性边界 / 说明

- 这是纯 runtime 状态推进步骤，不允许由 LLM 直接回写 frontier。

## 相关

- [[operator-map]]
- [[expansion-trace]]
- [[FrontierState_t]]
- [[SearchExecutionPlan_t]]
- [[SearchScoringResult_t]]
- [[BranchEvaluation_t]]
- [[NodeRewardBreakdown_t]]
- [[FrontierState_t1]]
