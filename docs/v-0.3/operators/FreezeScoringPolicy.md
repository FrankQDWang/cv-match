# FreezeScoringPolicy

从 `RequirementSheet` 冻结出本次 run 的评分口径。

## 公式

```text
fit_gate_constraints_t = copy(R.hard_constraints)
must_have_weight_t = dominant_weight_from(R.must_have_capabilities, R.scoring_rationale)
overall_weight_t = secondary_weight_from(R.scoring_rationale)
risk_weight_t = 1.0 - must_have_weight_t - overall_weight_t

P = {
  fit_gate_constraints: fit_gate_constraints_t,
  scoring_weights: {
    must_have: must_have_weight_t,
    overall: overall_weight_t,
    risk: risk_weight_t
  },
  ranking_notes: R.scoring_rationale
}
```

## Notation Legend

```text
R := RequirementSheet
P := ScoringPolicy
```

## Read Set

- `RequirementSheet.must_have_capabilities`
- `RequirementSheet.hard_constraints`
- `RequirementSheet.scoring_rationale`

## Derived / Intermediate

- `fit_gate_constraints_t` 是 `R.hard_constraints` 的 run 内冻结拷贝，后续不允许再漂移。
- `dominant_weight_from(...)` 与 `secondary_weight_from(...)` 只负责把需求真相压缩成稳定权重，不读取轮次结果。
- `risk_weight_t` 是剩余权重，不再单独由下游自由改写。

## Write Set

- `ScoringPolicy.fit_gate_constraints`
- `ScoringPolicy.scoring_weights`
- `ScoringPolicy.ranking_notes`

## 输入 payload

- [[RequirementSheet]]

## 输出 payload

- [[ScoringPolicy]]

## 不确定性边界 / 说明

- 评分口径一旦冻结，就不允许随着 branch 扩展或 query 调整而改变。

## 相关

- [[operator-map]]
- [[expansion-trace]]
- [[RequirementSheet]]
- [[ScoringPolicy]]
