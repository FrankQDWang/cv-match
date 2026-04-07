# SearchScoringResult_t

在冻结评分口径下产生的节点局部评分结果。

```text
SearchScoringResult_t = { scored_candidates, node_shortlist_candidate_ids, top_three_statistics }
```

## 稳定字段组

- 候选评分明细：`scored_candidates`
- 节点 shortlist id：`node_shortlist_candidate_ids`
- top three 统计：`top_three_statistics`

## Direct Producer / Direct Consumers

- Direct producer：[[ScoreSearchResults]]
- Direct consumers：[[EvaluateBranchOutcome]]、[[ComputeNodeRewardBreakdown]]、[[UpdateFrontierState]]

## Invariants

- `node_shortlist_candidate_ids` 是 node-local，不等于 run-global shortlist。
- `top_three_statistics` 只描述当前节点局部结果。

## 最小示例

```yaml
scored_candidates:
  - candidate_id: "c07"
    fit: 1
    overall: 86
    must_have: 92
    risk: 8
    base_score: 2.796
node_shortlist_candidate_ids: ["c07", "c19", "c51"]
top_three_statistics:
  average_base_score_top_three: 2.51
```

## 相关

- [[operator-map]]
- [[SearchExecutionResult_t]]
- [[ScoreSearchResults]]
- [[BranchEvaluation_t]]
