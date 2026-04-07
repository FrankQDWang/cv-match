# FrontierState_t

当前一次扩展开始前的 frontier 运行态。

```text
FrontierState_t = { frontier_nodes, open_frontier_node_ids, closed_frontier_node_ids, run_term_catalog, run_shortlist_candidate_ids, semantic_hashes_seen, operator_statistics, remaining_budget }
```

## 稳定字段组

- 节点表：`frontier_nodes`
- 待扩展节点 id：`open_frontier_node_ids`
- 已关闭节点 id：`closed_frontier_node_ids`
- run 级词表：`run_term_catalog`
- run 级 shortlist：`run_shortlist_candidate_ids`
- 语义哈希去重表：`semantic_hashes_seen`
- operator 统计：`operator_statistics`
- 剩余预算：`remaining_budget`

## Direct Producer / Direct Consumers

- Direct producer：[[InitializeFrontierState]]、previous round [[FrontierState_t1]] after runtime round shift
- Direct consumers：[[SelectActiveFrontierNode]]、[[CarryForwardFrontierState]]、[[MaterializeSearchExecutionPlan]]、[[EvaluateBranchOutcome]]、[[ComputeNodeRewardBreakdown]]、[[UpdateFrontierState]]

## Invariants

- `run_shortlist_candidate_ids` 与节点局部 shortlist 不同义。
- `semantic_hashes_seen` 只增不减。
- 只有 runtime 路径能消费 `remaining_budget`。
- `FrontierState_t(next round) := FrontierState_t1(previous round)` after runtime round shift。

## 最小示例

```yaml
open_frontier_node_ids: ["seed_alias", "seed_domain"]
closed_frontier_node_ids: ["seed_core"]
run_term_catalog: ["python backend", "llm application", "rag"]
run_shortlist_candidate_ids: ["c17", "c32", "c91"]
semantic_hashes_seen: ["hash_core_01", "hash_alias_02"]
remaining_budget: 3
```

## 相关

- [[operator-map]]
- [[InitializeFrontierState]]
- [[CarryForwardFrontierState]]
- [[SelectActiveFrontierNode]]
- [[FrontierState_t1]]
