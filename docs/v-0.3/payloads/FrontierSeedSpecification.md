# FrontierSeedSpecification

用于初始化 frontier 的单条种子规格。

```text
FrontierSeedSpecification = { operator_name, seed_terms, seed_rationale, source_card_ids, expected_coverage, negative_terms, target_location }
```

## 稳定字段组

- operator 名：`operator_name`
- 初始种子词：`seed_terms`
- 种子理由：`seed_rationale`
- 来源知识卡：`source_card_ids`
- 预期覆盖：`expected_coverage`
- 负向词：`negative_terms`
- 目标地点：`target_location`

## Contained In

- `[[GroundingDraft]].frontier_seed_specifications`
- `[[GroundingOutput]].frontier_seed_specifications`

## Used By

- [[GenerateGroundingOutput]]
- [[InitializeFrontierState]]

## Invariants

- `operator_name` 必须来自 [[OperatorCatalog]]。
- round-0 seed 的 `operator_name` 只允许 `must_have_alias / strict_core / domain_company`，不得使用 `crossover_compose`。
- `seed_terms` 必须是可直接进入 round-0 frontier 的稳定查询短语集合。
- 每条 seed 只允许 2-4 个 query terms。
- `source_card_ids` 在非 generic 模式下必须可回溯到 `GroundingKnowledgeCard`；`generic_fallback` 下允许为空数组。
- `domain_company` 与 `crossover_compose` 不得出现在 `generic_fallback` 产出的 seed 中。

## 最小示例

```yaml
operator_name: "must_have_alias"
seed_terms:
  - "agent engineer"
  - "rag"
  - "python"
seed_rationale: "先覆盖角色锚点与核心技术栈。"
source_card_ids:
  - "role_alias.llm_agent_rag_engineering.backend_agent_engineer"
expected_coverage:
  - "Python backend"
  - "LLM application"
negative_terms:
  - "data analyst"
target_location: "Shanghai"
```

## 相关

- [[GroundingDraft]]
- [[GroundingOutput]]
- [[GroundingKnowledgeCard]]
- [[OperatorCatalog]]
- [[InitializeFrontierState]]
