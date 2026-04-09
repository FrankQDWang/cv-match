# BootstrapKeywordDraft

`BootstrapKeywordGenerationLLM` 生成的 round-0 关键词草稿。

```text
BootstrapKeywordDraft = { core_keywords, must_have_keywords, expansion_keywords, negative_keywords }
```

## 稳定字段组

- 核心词：`core_keywords`
- must-have 补充词：`must_have_keywords`
- 领域扩展词：`expansion_keywords`
- 负向词：`negative_keywords`

## Direct Producer / Direct Consumers

- Direct producer：BootstrapKeywordGenerationLLM
- Direct consumers：[[GenerateBootstrapOutput]]

## Invariants

- 它只是 LLM 草稿，不是最终 seed。
- `expansion_keywords` 只在 routed path 下允许进入 `domain_company` seed。
- generic fallback 下不允许靠它伪造领域 provenance。

## 相关

- [[BootstrapRoutingResult]]
- [[GenerateBootstrapOutput]]

