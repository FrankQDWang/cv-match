# RequirementSheet

结构化后的岗位需求真相，是后续所有 canonical 读取的业务基线。

```text
RequirementSheet = { role_title, must_have_capabilities, hard_constraints, scoring_rationale }
```

## 稳定字段组

- 岗位标题：`role_title`
- 必须能力：`must_have_capabilities`
- 硬约束：`hard_constraints`
- 评分说明：`scoring_rationale`

## Direct Producer / Direct Consumers

- Direct producer：[[ExtractRequirements]]
- Direct consumers：[[FreezeScoringPolicy]]、[[GenerateGroundingOutput]]、[[SelectActiveFrontierNode]]、[[MaterializeSearchExecutionPlan]]、[[EvaluateBranchOutcome]]、[[FinalizeSearchRun]]

## Invariants

- `RequirementSheet` 是运行期唯一允许传播的结构化需求真相。
- 后续模块可以补充解释，但不能改写这里的需求边界。

## 最小示例

```yaml
role_title: "Senior Python / LLM Engineer"
must_have_capabilities:
  - "Python backend"
  - "LLM application"
  - "retrieval or ranking experience"
hard_constraints:
  locations: ["Shanghai"]
  min_years: 5
scoring_rationale: "先过 must-have，再看 ranking 补强"
```

## 相关

- [[operator-map]]
- [[ExtractRequirements]]
- [[ScoringPolicy]]
- [[GroundingOutput]]
