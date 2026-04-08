# KnowledgeRetrievalBudget

控制 routing 与知识卡召回上限的 runtime 预算。

```text
KnowledgeRetrievalBudget = { max_cards, max_inferred_domain_packs }
```

## 默认值

```yaml
max_cards: 8
max_inferred_domain_packs: 2
```

## Invariants

- `max_cards` 约束 `RetrieveGroundingKnowledge` 最终返回的 `retrieved_cards` 数量上限。
- `max_inferred_domain_packs` 只允许 routing 选出 1 或 2 个领域包，不能扩成全量多领域召回。

## 相关

- [[RetrieveGroundingKnowledge]]
- [[KnowledgeRetrievalResult]]
