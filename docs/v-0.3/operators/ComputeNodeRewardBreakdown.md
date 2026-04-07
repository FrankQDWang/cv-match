# ComputeNodeRewardBreakdown

把扩展结果压缩为 deterministic reward breakdown。

## 公式

```text
parent_node_t =
  F_t.frontier_nodes[p_t.child_frontier_node_stub.parent_frontier_node_id]

old_shortlist_candidate_ids_t = set(parent_node_t.node_shortlist_candidate_ids)
new_shortlist_candidate_ids_t = set(y_t.node_shortlist_candidate_ids)
net_new_candidate_ids_t = new_shortlist_candidate_ids_t - set(F_t.run_shortlist_candidate_ids)

incumbent_top_three_average_t =
  parent_baseline_top_three_average(parent_node_t)

candidate_top_three_average_t =
  y_t.top_three_statistics.average_base_score_top_three

delta_top_three_t =
  candidate_top_three_average_t - incumbent_top_three_average_t

must_have_gain_t =
  must_have_coverage_gain(y_t.scored_candidates, parent_node_t.node_shortlist_candidate_ids)

new_fit_yield_t =
  |net_new_candidate_ids_t|

diversity_t =
  shortlist_diversity_gain(y_t.node_shortlist_candidate_ids, F_t.run_shortlist_candidate_ids)

hard_constraint_violation_t =
  hard_constraint_violation_rate(y_t.scored_candidates, p_t.projected_filters)

duplicate_penalty_t = x_t.search_page_statistics.duplicate_rate
cost_penalty_t =
  search_cost_penalty(x_t.search_page_statistics.pages_fetched, x_t.search_page_statistics.latency_ms)

reward_score_t =
  weighted_sum(
    + delta_top_three_t,
    + must_have_gain_t,
    + new_fit_yield_t,
    + a_t.novelty_score,
    + a_t.usefulness_score,
    + diversity_t,
    - hard_constraint_violation_t,
    - duplicate_penalty_t,
    - cost_penalty_t
  )

b_t = {
  delta_top_three: delta_top_three_t,
  must_have_gain: must_have_gain_t,
  new_fit_yield: new_fit_yield_t,
  novelty: a_t.novelty_score,
  usefulness: a_t.usefulness_score,
  diversity: diversity_t,
  hard_constraint_violation: hard_constraint_violation_t,
  duplicate_penalty: duplicate_penalty_t,
  cost_penalty: cost_penalty_t,
  reward_score: reward_score_t
}
```

## Notation Legend

```text
F_t := FrontierState_t
p_t := SearchExecutionPlan_t
x_t := SearchExecutionResult_t
y_t := SearchScoringResult_t
a_t := BranchEvaluation_t
b_t := NodeRewardBreakdown_t
```

## Read Set

- `FrontierState_t.frontier_nodes`
- `FrontierState_t.run_shortlist_candidate_ids`
- `SearchExecutionPlan_t.projected_filters`
- `SearchExecutionPlan_t.child_frontier_node_stub`
- `SearchExecutionResult_t.search_page_statistics`
- `SearchScoringResult_t.scored_candidates`
- `SearchScoringResult_t.node_shortlist_candidate_ids`
- `SearchScoringResult_t.top_three_statistics`
- `BranchEvaluation_t.novelty_score`
- `BranchEvaluation_t.usefulness_score`

## Derived / Intermediate

- `old_shortlist_candidate_ids_t`、`new_shortlist_candidate_ids_t` 和 `net_new_candidate_ids_t` 先把 parent baseline、本轮 node shortlist、run-global 去重结果拆开。
- `parent_baseline_top_three_average(parent_node_t)` 表示当前 active node 在本次扩展前的 cached baseline，不重新发明第二套评分上下文。
- `must_have_coverage_gain(...)` 比较的是本轮评分结果与 parent node 旧 shortlist 的 must-have 覆盖变化。
- `new_fit_yield_t` 只计算真正新进入 run-global shortlist 的候选。
- `weighted_sum(...)` 是固定 reward 合成公式，不允许下游再自由修改各分项意义。

## Write Set

- `NodeRewardBreakdown_t.delta_top_three`
- `NodeRewardBreakdown_t.must_have_gain`
- `NodeRewardBreakdown_t.new_fit_yield`
- `NodeRewardBreakdown_t.novelty`
- `NodeRewardBreakdown_t.usefulness`
- `NodeRewardBreakdown_t.diversity`
- `NodeRewardBreakdown_t.hard_constraint_violation`
- `NodeRewardBreakdown_t.duplicate_penalty`
- `NodeRewardBreakdown_t.cost_penalty`
- `NodeRewardBreakdown_t.reward_score`

## 输入 payload

- [[FrontierState_t]]
- [[SearchExecutionPlan_t]]
- [[SearchExecutionResult_t]]
- [[SearchScoringResult_t]]
- [[BranchEvaluation_t]]

## 输出 payload

- [[NodeRewardBreakdown_t]]

## 不确定性边界 / 说明

- 这里消费 LLM 评判信号，但 reward 计算自身保持 deterministic。

## 相关

- [[operator-map]]
- [[expansion-trace]]
- [[FrontierState_t]]
- [[SearchExecutionPlan_t]]
- [[SearchExecutionResult_t]]
- [[SearchScoringResult_t]]
- [[BranchEvaluation_t]]
- [[NodeRewardBreakdown_t]]
