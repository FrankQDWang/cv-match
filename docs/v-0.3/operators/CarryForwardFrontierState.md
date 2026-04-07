# CarryForwardFrontierState

在 direct-stop 路径中把当前 frontier 原样投影为 stop guard 可消费的 `FrontierState_t1`。

## 公式

```text
F_{t+1} = {
  frontier_nodes: F_t.frontier_nodes,
  open_frontier_node_ids: F_t.open_frontier_node_ids,
  closed_frontier_node_ids: F_t.closed_frontier_node_ids,
  run_term_catalog: F_t.run_term_catalog,
  run_shortlist_candidate_ids: F_t.run_shortlist_candidate_ids,
  semantic_hashes_seen: F_t.semantic_hashes_seen,
  operator_statistics: F_t.operator_statistics,
  remaining_budget: F_t.remaining_budget
}
```

## Notation Legend

```text
F_t := FrontierState_t
F_{t+1} := FrontierState_t1
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

## Derived / Intermediate

- 这是 identity carry-forward，不新增 child node，不改写 shortlist，不消耗额外 frontier 更新逻辑。
- 它只服务 direct-stop 路径，让 `EvaluateStopCondition` 与 `FinalizeSearchRun` 继续读取统一的 `FrontierState_t1`。

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

## 输出 payload

- [[FrontierState_t1]]

## 不确定性边界 / 说明

- 这是 runtime-only transformation，不是新的主链搜索步骤。

## 相关

- [[operator-map]]
- [[workflow-explained]]
- [[EvaluateStopCondition]]
- [[FrontierState_t]]
- [[FrontierState_t1]]
