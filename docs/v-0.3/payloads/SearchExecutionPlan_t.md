# SearchExecutionPlan_t

`MaterializeSearchExecutionPlan` 物化出的可执行检索计划。

```text
SearchExecutionPlan_t = {
  query_terms,
  projected_filters,
  runtime_only_constraints,
  target_new_candidate_count,
  semantic_hash,
  knowledge_pack_id,
  child_frontier_node_stub,
  derived_position,
  derived_work_content
}
```

## 稳定字段组

- 检索词：`query_terms`
- 可下推过滤：`projected_filters`
- 仅 runtime 使用的约束：`runtime_only_constraints`
- 目标新增候选数：`target_new_candidate_count`
- 语义哈希：`semantic_hash`
- bootstrap provenance：`knowledge_pack_id`
- child frontier node 草稿：`child_frontier_node_stub`
- derived 职位信号：`derived_position`
- derived 工作内容信号：`derived_work_content`

## Invariants

- `semantic_hash` 一旦生成不可改。
- `target_new_candidate_count` 在这里冻结。
- `knowledge_pack_id` 只保留 bootstrap 来源，不参与后续 runtime 分叉。
- `child_frontier_node_stub.donor_frontier_node_id` 仅在 `crossover_compose` 下非空。

## 相关

- [[MaterializeSearchExecutionPlan]]
- [[RuntimeOnlyConstraints]]
