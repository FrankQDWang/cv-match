# InitializeFrontierState

用 grounding 结果和 runtime budget 初始化第一版 frontier。

## 公式

```text
seed_frontier_nodes_t = [
  {
    frontier_node_id: derive_seed_id(seed_specification_t),
    selected_operator_name: seed_specification_t.operator_name,
    node_query_term_pool: deduplicate(seed_specification_t.seed_terms),
    parent_shortlist_candidate_ids: [],
    node_shortlist_candidate_ids: [],
    previous_branch_evaluation: null,
    reward_breakdown: null,
    status: "open"
  }
  for seed_specification_t in GroundingOutput.frontier_seed_specifications
]

F_t = {
  frontier_nodes: index_by(seed_frontier_nodes_t, key = frontier_node_id),
  open_frontier_node_ids: [node.frontier_node_id for node in seed_frontier_nodes_t],
  closed_frontier_node_ids: [],
  run_term_catalog: union_of(node.node_query_term_pool for node in seed_frontier_nodes_t),
  run_shortlist_candidate_ids: [],
  semantic_hashes_seen: {},
  operator_statistics: zeroed_operator_statistics(seed_frontier_nodes_t),
  remaining_budget: initial_round_budget
}
```

## Notation Legend

```text
F_t := FrontierState_t
```

## Read Set

- `GroundingOutput.frontier_seed_specifications`
- `initial_round_budget`

## Derived / Intermediate

- `derive_seed_id(...)` 把每条 seed 规格映射为稳定 `frontier_node_id`，避免 runtime 启动后再临时命名。
- `deduplicate(seed_terms)` 负责把 seed term 压成 node-local 的初始 query pool。
- `zeroed_operator_statistics(...)` 为 operator catalog 建立初始统计桶，保证后续 reward 更新有落点。
- `initial_round_budget` 是 runtime 配置，不由 grounding 草稿决定。
- `RequirementSheet` 与 `ScoringPolicy` 的影响已经在 `GroundingOutput` 的上游固化，这一步不再直接重复读取它们。

## Write Set

- `FrontierState_t.frontier_nodes`
- `FrontierState_t.open_frontier_node_ids`
- `FrontierState_t.closed_frontier_node_ids`
- `FrontierState_t.run_term_catalog`
- `FrontierState_t.run_shortlist_candidate_ids`
- `FrontierState_t.semantic_hashes_seen`
- `FrontierState_t.operator_statistics`
- `FrontierState_t.remaining_budget`

## 输入 payload

- [[GroundingOutput]]

## 输出 payload

- [[FrontierState_t]]

## 不确定性边界 / 说明

- frontier 初始化必须是 runtime-owned，而不是控制器 prompt-owned。

## 相关

- [[operator-map]]
- [[expansion-trace]]
- [[GroundingOutput]]
- [[FrontierState_t]]
