# SearchExecutionPlan_t

`MaterializeSearchExecutionPlan` 物化出的可执行检索计划。

```text
SearchExecutionPlan_t = { query_terms, projected_filters, runtime_only_constraints, target_new_candidate_count, semantic_hash, child_frontier_node_stub }
```

## 稳定字段组

- 检索词：`query_terms`
- 可下推过滤：`projected_filters`
- 仅 runtime 使用的约束：`runtime_only_constraints`
- 目标新增候选数：`target_new_candidate_count`
- 语义哈希：`semantic_hash`
- child frontier node 草稿：`child_frontier_node_stub`

## Direct Producer / Direct Consumers

- Direct producer：[[MaterializeSearchExecutionPlan]]
- Direct consumers：[[ExecuteSearchPlan]]、[[EvaluateBranchOutcome]]、[[ComputeNodeRewardBreakdown]]、[[UpdateFrontierState]]

## Invariants

- `semantic_hash` 一旦生成不可改。
- `target_new_candidate_count` 在这里冻结，后续搜索不再读取游离外部变量。
- `runtime_only_constraints` 不要求 CTS 原生支持。

## 最小示例

```yaml
query_terms: ["python backend", "llm application", "rag", "ranking engineer"]
projected_filters:
  locations: ["Shanghai"]
  min_years: 5
runtime_only_constraints:
  must_have_keywords: ["retrieval", "ranking", "rag"]
target_new_candidate_count: 10
semantic_hash: "hash_domain_03"
child_frontier_node_stub:
  frontier_node_id: "child_domain_03"
  parent_frontier_node_id: "seed_alias"
  selected_operator_name: "domain_company"
```

## 相关

- [[operator-map]]
- [[SearchControllerDecision_t]]
- [[MaterializeSearchExecutionPlan]]
- [[SearchExecutionResult_t]]
