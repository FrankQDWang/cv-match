# GroundingCatalog

grounding 层允许出现的有限 evidence type 集合。

```text
GroundingCatalog = {
  title_alias,
  query_term,
  must_have_link,
  preferred_link,
  generic_requirement
}
```

## 字段说明

- `title_alias`：来自知识卡标题、别名或 canonical term 的直接命中。
- `query_term`：来自知识卡推荐 query terms 的稳定短语。
- `must_have_link`：来自知识卡 `must_have_links` 的结构化证据。
- `preferred_link`：来自知识卡 `preferred_links` 的结构化证据。
- `generic_requirement`：generic fallback 下直接来自 `RequirementSheet` 的通用启动证据。

## Invariants

- `generic_requirement` 只允许出现在 `generic_fallback`。
- 非 generic 模式下不得把自由生成文本标成 `title_alias` 或 `must_have_link`。

## 相关

- [[GroundingEvidenceCard]]
- [[GenerateGroundingOutput]]
