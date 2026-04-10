# RuntimeTermBudgetPolicy

根据 `search_phase` 裁定每轮 query term 数量范围。

```text
RuntimeTermBudgetPolicy = {
  explore_budget_range,
  balance_budget_range,
  harvest_budget_range
}
```

## 默认值

```yaml
explore_budget_range: [2, 6]
balance_budget_range: [2, 5]
harvest_budget_range: [2, 4]
```

## Derived Rule

- `search_phase = explore`：使用 `explore_budget_range`
- `search_phase = balance`：使用 `balance_budget_range`
- `search_phase = harvest`：使用 `harvest_budget_range`

## Invariants

- `clamp_term_budget(...)` 必须保序去重后再裁切。
- 如果可用 term 数量少于当前区间下界，不得凭空补词；直接保留实际数量。
- `MaterializeSearchExecutionPlan` 不得重新从 `remaining_budget` 推导 term budget；只允许消费已冻结的 `term_budget_range`。

## 相关

- [[SelectActiveFrontierNode]]
- [[MaterializeSearchExecutionPlan]]
