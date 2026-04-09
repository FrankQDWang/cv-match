# GenerateBootstrapOutput

把 `BootstrapKeywordDraft` 收口成 round-0 可执行 seeds。

## Signature

```text
GenerateBootstrapOutput : (RequirementSheet, BootstrapRoutingResult, DomainKnowledgePack | null, BootstrapKeywordDraft) -> BootstrapOutput
```

## 当前规则

- `strict_core`：`role_title + core_keywords`
- `must_have_alias`：`must_have_capabilities + must_have_keywords`
- `domain_company`：仅当 routed path 且 `expansion_keywords` 非空时生成
- `negative_terms`：`RequirementSheet.exclusion_signals + pack.exclude_keywords + draft.negative_keywords`

## 关键边界

- routed path 最多 3 条 seeds。
- generic fallback 固定只有 2 条 seeds。
- provenance 只保留 `knowledge_pack_id`，不再保留 `source_card_ids`。

## 相关

- [[BootstrapKeywordDraft]]
- [[BootstrapOutput]]

