# FrontierState_t1

一次扩展完成后的 frontier 新状态。

```text
FrontierState_t1 = { frontier_nodes, open_frontier_node_ids, closed_frontier_node_ids, run_term_catalog, run_shortlist_candidate_ids, semantic_hashes_seen, operator_statistics, remaining_budget }
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

- Direct producer：[[UpdateFrontierState]]、[[CarryForwardFrontierState]]
- Direct consumers：[[EvaluateStopCondition]]、[[FinalizeSearchRun]]、runtime round shift

## Invariants

- `FrontierState_t1` 的对象形状与 `FrontierState_t` 相同，但字段值不同。
- 当前轮里它服务于 stop / finalize；进入下一轮前会经 runtime round shift 重绑定为 `FrontierState_t`。

## 最小示例

```yaml
open_frontier_node_ids: ["seed_domain", "child_domain_03"]
closed_frontier_node_ids: ["seed_core", "seed_alias"]
run_shortlist_candidate_ids: ["c07", "c17", "c19"]
semantic_hashes_seen: ["hash_core_01", "hash_alias_02", "hash_domain_03"]
remaining_budget: 2
```

## 相关

- [[operator-map]]
- [[UpdateFrontierState]]
- [[CarryForwardFrontierState]]
- [[EvaluateStopCondition]]
- [[SearchRunResult]]
