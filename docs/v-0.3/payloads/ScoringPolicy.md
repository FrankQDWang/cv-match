# ScoringPolicy

冻结后的评分口径，供搜索结果评分稳定复用。

```text
ScoringPolicy = { fit_gate_constraints, scoring_weights, ranking_notes }
```

## 稳定字段组

- 过门槛约束：`fit_gate_constraints`
- 评分权重：`scoring_weights`
- 排序说明：`ranking_notes`

## Direct Producer / Direct Consumers

- Direct producer：[[FreezeScoringPolicy]]
- Direct consumers：[[SelectActiveFrontierNode]]、[[ScoreSearchResults]]

## Invariants

- `ScoringPolicy` 在单次 run 内冻结，不允许中途漂移。
- `fit_gate_constraints` 只表达稳定门槛，不承担搜索控制。

## 最小示例

```yaml
fit_gate_constraints:
  locations: ["Shanghai"]
  min_years: 5
scoring_weights:
  must_have: 0.5
  overall: 0.3
  risk: 0.2
ranking_notes: "must-have 优先于背景加分"
```

## 相关

- [[operator-map]]
- [[RequirementSheet]]
- [[FreezeScoringPolicy]]
- [[ScoreSearchResults]]
