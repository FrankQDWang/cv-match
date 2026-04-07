# FrontierSeedSpecification

用于初始化 frontier 的单条种子规格。

```text
FrontierSeedSpecification = { operator_name, seed_terms, target_location }
```

## 稳定字段组

- operator 名：`operator_name`
- 初始种子词：`seed_terms`
- 目标地点：`target_location`

## Contained In

- `[[GroundingDraft]].frontier_seed_specifications`
- `[[GroundingOutput]].frontier_seed_specifications`

## Used By

- [[GenerateGroundingOutput]]
- [[InitializeFrontierState]]

## Invariants

- `operator_name` 必须来自 operator catalog。
- `seed_terms` 必须是可直接进入 round-0 frontier 的稳定查询短语集合。
- `target_location` 只承载岗位地点约束的局部投影，不承接整份 `hard_constraints`。

## 最小示例

```yaml
operator_name: "must_have_alias"
seed_terms:
  - "ranking engineer"
  - "retrieval engineer"
target_location: "Shanghai"
```

## 相关

- [[GroundingDraft]]
- [[GroundingOutput]]
- [[InitializeFrontierState]]
