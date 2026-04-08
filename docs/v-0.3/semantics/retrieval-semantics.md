# retrieval-semantics

`RetrieveGroundingKnowledge` 使用的 deterministic helper 语义 owner。

## `infer_domain_packs`

对当前已编译领域包做 deterministic routing，只允许输出 0、1 或 2 个领域包。

```text
pack_score =
  4 * title_alias_hit_any
  + 3 * must_have_link_hits
  + 1 * preferred_link_hits
  - 3 * exclusion_conflicts
```

- `title_alias_hit_any = 1`：`R.role_title` 命中任一领域卡的 `title / aliases / canonical_terms`
- `must_have_link_hits`：命中该领域 `must_have_links` 或强 query term 的 distinct must-have 数
- `preferred_link_hits`：命中该领域 `preferred_links` 的 distinct preferred 数
- `exclusion_conflicts`：`R.exclusion_signals` 命中该领域高置信度卡的 `positive_signals / query_terms` 的 distinct 数

路由判定：

- top1 `>= 5` 且与 top2 margin `>= 2`：输出单领域 `inferred_domain`
- top1/top2 都 `>= 5` 且 margin `< 2`，并且两者各自至少补到一个不同 must-have：输出双领域 `inferred_domain`
- 其余情况：输出空集合，交给 `generic_fallback`

## `cards_in`

- 输入：`GroundingKnowledgeBaseSnapshot` 与领域包 id 列表
- 输出：这些领域包下的全部编译知识卡
- `generic_fallback` 时返回空集合

## `match_cards`

对领域卡做 deterministic 排序：

```text
card_score =
  4 * title_or_alias_overlap
  + 2 * must_have_overlap
  + 1 * preferred_overlap
  + 1 * query_term_overlap
  - 2 * negative_signal_conflict
```

- 同分按 `confidence(high > medium > low)`、`freshness_date(desc)`、`card_id(asc)` 稳定排序

## `knowledge_retrieval_budget`

- 使用 [[KnowledgeRetrievalBudget]]
- `retrieved_cards` 最终数量不得超过 `max_cards`

## routing fields in `KnowledgeRetrievalResult`

- `explicit_domain`：`routing_confidence = 1.0`
- 单领域 `inferred_domain`：`routing_confidence = 0.8`
- 双领域 `inferred_domain`：`routing_confidence = 0.7`
- `generic_fallback`：`routing_confidence = 0.3`

## 相关

- [[RetrieveGroundingKnowledge]]
- [[KnowledgeRetrievalResult]]
- [[KnowledgeRetrievalBudget]]
