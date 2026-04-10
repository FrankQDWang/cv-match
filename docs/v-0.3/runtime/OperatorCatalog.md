# OperatorCatalog

```text
OperatorCatalog = {
  must_have_alias,
  strict_core,
  domain_expansion,
  crossover_compose
}
```

## 语义

- `must_have_alias`：围绕 must-have 或放松后的底层锚点扩展
- `strict_core`：围绕核心精准 seed 或通用扩展 seed 收缩/扩展
- `domain_expansion`：围绕单 pack 或多 pack 的领域上下文扩展
- `crossover_compose`：从 active node 与 donor node 的共享锚点做交叉

## Invariants

- `domain_expansion` 只有在 `knowledge_pack_ids` 非空时才合法
- `crossover_compose` 永不作为 round-0 seed operator

## 相关

- [[FrontierSeedSpecification]]
- [[GenerateSearchControllerDecision]]
