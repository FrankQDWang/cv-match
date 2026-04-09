# FrontierSeedSpecification

用于初始化 frontier 的单条种子规格。

```text
FrontierSeedSpecification = { operator_name, seed_terms, seed_rationale, knowledge_pack_id, expected_coverage, negative_terms, target_location }
```

## 稳定字段组

- operator 名：`operator_name`
- 初始种子词：`seed_terms`
- 种子理由：`seed_rationale`
- 来源 knowledge pack：`knowledge_pack_id`
- 预期覆盖：`expected_coverage`
- 负向词：`negative_terms`
- 目标地点：`target_location`

## Contained In

- `[[BootstrapOutput]].frontier_seed_specifications`

## Used By

- [[GenerateBootstrapOutput]]
- [[InitializeFrontierState]]

## Invariants

- `operator_name` 必须来自 [[OperatorCatalog]]。
- round-0 只允许 `must_have_alias / strict_core / domain_company`。
- generic fallback 下 `knowledge_pack_id` 必须为空。
- routed path 下 `knowledge_pack_id` 最多只保留一个。

## 相关

- [[BootstrapOutput]]
- [[OperatorCatalog]]
