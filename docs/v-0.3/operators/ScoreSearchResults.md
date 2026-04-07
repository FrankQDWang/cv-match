# ScoreSearchResults

在冻结评分口径下对搜索结果做结构化评分。

## 公式

```text
scoring_packets_t = [
  {
    candidate: candidate_t,
    fit_gate_constraints: P.fit_gate_constraints,
    scoring_weights: P.scoring_weights,
    ranking_notes: P.ranking_notes
  }
  for candidate_t in x_t.deduplicated_candidates
]

draft_score_cards_t = SearchScoringLLM(scoring_packets_t)

normalized_score_cards_t =
  normalize_score_cards(draft_score_cards_t, P.fit_gate_constraints)

ranked_score_cards_t =
  sort_desc(normalized_score_cards_t, key = base_score)

y_t = {
  scored_candidates: ranked_score_cards_t,
  node_shortlist_candidate_ids:
    top_k_fit_candidate_ids(ranked_score_cards_t),
  top_three_statistics: {
    average_base_score_top_three:
      average_base_score(top_three(ranked_score_cards_t))
  }
}
```

## Notation Legend

```text
P := ScoringPolicy
x_t := SearchExecutionResult_t
y_t := SearchScoringResult_t
```

## Read Set

- `SearchExecutionResult_t.deduplicated_candidates`
- `ScoringPolicy.fit_gate_constraints`
- `ScoringPolicy.scoring_weights`
- `ScoringPolicy.ranking_notes`

## Derived / Intermediate

- `scoring_packets_t` 把每个候选与冻结后的评分口径绑定，保证 scoring 不再读取 run-local 漂移信息。
- `draft_score_cards_t` 是 LLM 给出的原始评分草稿。
- `normalize_score_cards(...)` 负责校正缺失字段、clamp 数值范围、执行 fit gate，并补齐稳定排序键。
- `top_k_fit_candidate_ids(...)` 只从通过 fit gate 的候选里取 node-local shortlist。

## Write Set

- `SearchScoringResult_t.scored_candidates`
- `SearchScoringResult_t.node_shortlist_candidate_ids`
- `SearchScoringResult_t.top_three_statistics`

## 输入 payload

- [[SearchExecutionResult_t]]
- [[ScoringPolicy]]

## 输出 payload

- [[SearchScoringResult_t]]

## 不确定性边界 / 说明

- 评分草稿可以由 LLM 生成，但最终数值字段与 shortlist 选择必须经过 deterministic normalization。

## 相关

- [[operator-map]]
- [[expansion-trace]]
- [[SearchExecutionResult_t]]
- [[ScoringPolicy]]
- [[SearchScoringResult_t]]
