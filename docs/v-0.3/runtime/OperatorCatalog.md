# OperatorCatalog

运行时允许出现的 operator 有限集合。

```text
OperatorCatalog = {
  must_have_alias,
  strict_core,
  domain_company,
  crossover_compose
}
```

## 字段说明

- `must_have_alias`：围绕角色锚点或 must-have 别名做首轮/修复扩展，允许在 generic fallback 中使用。
- `strict_core`：对当前 query pool 做收缩，剔除弱相关 terms，只保留核心锚点，允许在 generic fallback 中使用。
- `domain_company`：围绕领域公司、业务场景或行业标签扩展，只允许在 `explicit_domain` 或 `inferred_domain` 中使用。
- `crossover_compose`：从 active node 与 donor node 的共享锚点出发做定向交叉，永不作为 round-0 seed operator，generic fallback 下只要 donor 合法仍可使用。

## Invariants

- `operator_name`、`selected_operator_name`、`repair_operator_hint` 只能来自本目录定义的有限集合。
- `domain_company` 在 `generic_fallback` 中必须被禁用。
- `crossover_compose` 必须带合法 donor lineage，且必须经过 shared-anchor guard。

## 最小示例

```yaml
must_have_alias:
  generic_fallback_allowed: true
  requires_donor: false
strict_core:
  generic_fallback_allowed: true
  requires_donor: false
domain_company:
  generic_fallback_allowed: false
  requires_donor: false
crossover_compose:
  generic_fallback_allowed: true
  requires_donor: true
```

## 相关

- [[SearchControllerDecision_t]]
- [[FrontierSeedSpecification]]
- [[GenerateSearchControllerDecision]]
- [[EvaluateBranchOutcome]]
