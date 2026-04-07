# EvaluateBranchOutcome

对当前扩展给出 dual-critic 判断，为 reward 与 stop 提供分支级信号。

## 公式

```text
parent_node_t =
  F_t.frontier_nodes[p_t.child_frontier_node_stub.parent_frontier_node_id]

branch_evaluation_packet_t = {
  must_have_capabilities: R.must_have_capabilities,
  parent_frontier_node_id: parent_node_t.frontier_node_id,
  previous_node_shortlist_candidate_ids: parent_node_t.node_shortlist_candidate_ids,
  query_terms: p_t.query_terms,
  semantic_hash: p_t.semantic_hash,
  search_page_statistics: x_t.search_page_statistics,
  node_shortlist_candidate_ids: y_t.node_shortlist_candidate_ids,
  top_three_statistics: y_t.top_three_statistics
}

draft_branch_evaluation_t =
  BranchOutcomeEvaluationLLM(branch_evaluation_packet_t)

a_t = {
  novelty_score: clamp01(draft_branch_evaluation_t.novelty_score),
  usefulness_score: clamp01(draft_branch_evaluation_t.usefulness_score),
  branch_exhausted:
    draft_branch_evaluation_t.branch_exhausted
    or (|y_t.node_shortlist_candidate_ids| = 0),
  repair_operator_hint:
    whitelist_or_null(draft_branch_evaluation_t.repair_operator_hint, operator_catalog),
  evaluation_notes: normalize_text(draft_branch_evaluation_t.evaluation_notes)
}
```

## Notation Legend

```text
R := RequirementSheet
F_t := FrontierState_t
p_t := SearchExecutionPlan_t
x_t := SearchExecutionResult_t
y_t := SearchScoringResult_t
a_t := BranchEvaluation_t
```

## Read Set

- `RequirementSheet.must_have_capabilities`
- `FrontierState_t.frontier_nodes`
- `SearchExecutionPlan_t.query_terms`
- `SearchExecutionPlan_t.semantic_hash`
- `SearchExecutionPlan_t.child_frontier_node_stub`
- `SearchExecutionResult_t.search_page_statistics`
- `SearchScoringResult_t.node_shortlist_candidate_ids`
- `SearchScoringResult_t.top_three_statistics`

## Derived / Intermediate

- `branch_evaluation_packet_t` 只读取本轮 branch 的局部事实，不把整份历史事件日志塞给 critic。
- `previous_node_shortlist_candidate_ids` 提供 parent baseline，供 critic 判断当前扩展是否真的带来了新覆盖。
- `branch_exhausted` 除了允许草稿建议，还会在当前轮一个 fit 候选都没有时被 deterministic 拉高。
- `repair_operator_hint` 只能回到 operator catalog 或 `null`，不能输出自由文本 operator。

## Write Set

- `BranchEvaluation_t.novelty_score`
- `BranchEvaluation_t.usefulness_score`
- `BranchEvaluation_t.branch_exhausted`
- `BranchEvaluation_t.repair_operator_hint`
- `BranchEvaluation_t.evaluation_notes`

## 输入 payload

- [[RequirementSheet]]
- [[FrontierState_t]]
- [[SearchExecutionPlan_t]]
- [[SearchExecutionResult_t]]
- [[SearchScoringResult_t]]

## 输出 payload

- [[BranchEvaluation_t]]

## 不确定性边界 / 说明

- 它判断 branch 价值，但不直接修改 frontier，也不直接决定 stop。

## 相关

- [[operator-map]]
- [[expansion-trace]]
- [[RequirementSheet]]
- [[FrontierState_t]]
- [[SearchExecutionPlan_t]]
- [[SearchExecutionResult_t]]
- [[SearchScoringResult_t]]
- [[BranchEvaluation_t]]
