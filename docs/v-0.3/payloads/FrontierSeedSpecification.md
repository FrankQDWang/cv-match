# FrontierSeedSpecification

用于初始化 frontier 的单条 round-0 seed。

```text
FrontierSeedSpecification = {
  operator_name,
  seed_terms,
  seed_rationale,
  knowledge_pack_ids,
  expected_coverage,
  negative_terms,
  target_location
}
```

## Invariants

- round-0 只允许 `must_have_alias / strict_core / domain_expansion`
- generic fallback 下 `knowledge_pack_ids = []`
- routed path 下 `knowledge_pack_ids` 继承 pack provenance，可为 1 或 2 个

## 相关

- [[BootstrapOutput]]
- [[OperatorCatalog]]
