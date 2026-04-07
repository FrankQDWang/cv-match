# RequirementExtractionDraft

`RequirementExtractionLLM` 生成的需求抽取草稿。

```text
RequirementExtractionDraft = { role_title_candidate, capability_candidates, hard_constraint_candidates, scoring_rationale_candidate }
```

## 稳定字段组

- 岗位标题草稿：`role_title_candidate`
- 能力候选列表：`capability_candidates`
- 硬约束候选列表：`hard_constraint_candidates`
- 评分说明草稿：`scoring_rationale_candidate`

## Direct Producer / Direct Consumers

- Direct producer：RequirementExtractionLLM
- Direct consumers：[[ExtractRequirements]]

## Invariants

- `RequirementExtractionDraft` 只是 LLM 草稿，不是最终业务真相。
- 必须经过 `ExtractRequirements` 的 deterministic normalization 才能进入主链。

## 最小示例

```yaml
role_title_candidate: "Senior Python / LLM Engineer"
capability_candidates:
  - "Python backend"
  - "LLM application"
  - "retrieval or ranking experience"
hard_constraint_candidates:
  locations: ["Shanghai"]
  min_years: 5
scoring_rationale_candidate: "must-have 先过，再看 ranking 背景"
```

## 相关

- [[operator-map]]
- [[SearchInputTruth]]
- [[ExtractRequirements]]
- [[RequirementSheet]]
