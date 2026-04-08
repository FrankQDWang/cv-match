# FrontierNode_t

`frontier_nodes` 中单个节点的 canonical schema owner。

```text
FrontierNode_t = {
  frontier_node_id,
  parent_frontier_node_id,
  donor_frontier_node_id,
  selected_operator_name,
  node_query_term_pool,
  source_card_ids,
  seed_rationale,
  negative_terms,
  parent_shortlist_candidate_ids,
  node_shortlist_candidate_ids,
  node_shortlist_score_snapshot,
  previous_branch_evaluation,
  reward_breakdown,
  status
}
```

## 稳定字段组

- 节点 id：`frontier_node_id`
- parent lineage：`parent_frontier_node_id`
- donor lineage：`donor_frontier_node_id`
- operator：`selected_operator_name`
- 节点 query term 池：`node_query_term_pool`
- 来源知识卡：`source_card_ids`
- seed 理由快照：`seed_rationale`
- 负向词：`negative_terms`
- parent shortlist：`parent_shortlist_candidate_ids`
- 节点 shortlist：`node_shortlist_candidate_ids`
- 节点 shortlist 分数快照：`node_shortlist_score_snapshot`
- 上一轮分支判断：`previous_branch_evaluation`
- reward：`reward_breakdown`
- 节点状态：`status`

## Direct Producer / Direct Consumers

- Direct producers：[[InitializeFrontierState]]、[[UpdateFrontierState]]
- Direct consumers：[[SelectActiveFrontierNode]]、[[MaterializeSearchExecutionPlan]]、[[EvaluateBranchOutcome]]、[[ComputeNodeRewardBreakdown]]、[[UpdateFrontierState]]

## Invariants

- seed node 的 `parent_frontier_node_id` 与 `donor_frontier_node_id` 必须为 `null`。
- seed node 的 `previous_branch_evaluation` 与 `reward_breakdown` 必须为 `null`；在获得第一份 deterministic reward 之前不得作为 donor。
- child node 的 `parent_frontier_node_id` 必须非空；只有 `crossover_compose` 才允许 `donor_frontier_node_id` 非空。
- `node_shortlist_score_snapshot` 只缓存当前节点 shortlist 候选的 `fusion_score`，用于 run-global shortlist 合并与审计。
- `reward_breakdown` 只表达 branch value，不得被解释为 candidate ranking。

## 最小示例

```yaml
frontier_node_id: "child_crossover_03"
parent_frontier_node_id: "seed_agent_core"
donor_frontier_node_id: "child_search_domain_01"
selected_operator_name: "crossover_compose"
node_query_term_pool: ["agent engineer", "rag", "python", "retrieval engineer", "ranking"]
source_card_ids:
  - "role_alias.llm_agent_rag_engineering.backend_agent_engineer"
  - "role_alias.search_ranking_retrieval_engineering.retrieval_engineer"
seed_rationale: null
negative_terms: ["data analyst", "pure algorithm research"]
parent_shortlist_candidate_ids: ["c32", "c44"]
node_shortlist_candidate_ids: ["c07", "c19", "c51"]
node_shortlist_score_snapshot:
  c07: 0.804
  c19: 0.763
  c51: 0.637
previous_branch_evaluation: [[BranchEvaluation_t]]
reward_breakdown: [[NodeRewardBreakdown_t]]
status: "open"
```

## 相关

- [[FrontierState_t]]
- [[FrontierState_t1]]
- [[InitializeFrontierState]]
- [[UpdateFrontierState]]
