# GroundingKnowledgeBaseSnapshot

运行时知识库的只读快照。

```text
GroundingKnowledgeBaseSnapshot = { snapshot_id, domain_pack_ids, compiled_report_ids, card_ids, compiled_at }
```

## 稳定字段组

- 快照 id：`snapshot_id`
- 启用的 domain packs：`domain_pack_ids`
- 编入快照的 reviewed synthesis report id：`compiled_report_ids`
- 卡片 id 集：`card_ids`
- 编译时间：`compiled_at`

## Direct Producer / Direct Consumers

- Direct producer：knowledge base compiler / release pipeline
- Direct consumers：[[RetrieveGroundingKnowledge]]、audit

## Invariants

- 运行时只读取一个稳定 snapshot。
- `snapshot_id` 必须足以让任意 `source_card_ids` 回溯到对应卡片集合。
- snapshot 不承载原始 Markdown 正文，只承载编译产物索引。

## 最小示例

```yaml
snapshot_id: "kb-2026-04-07-v1"
domain_pack_ids:
  - "llm_agent_rag_engineering"
  - "search_ranking_retrieval_engineering"
compiled_report_ids:
  - "report.role_family.llm_agent_rag_engineering.codex_synthesis_2026_04_07"
  - "report.role_family.search_ranking_retrieval_engineering.codex_synthesis_2026_04_07"
card_ids:
  - "role_alias.llm_agent_rag_engineering.backend_agent_engineer"
  - "neg_confusion.search_ranking_retrieval_engineering.search_analyst"
compiled_at: "2026-04-07T10:30:00+08:00"
```

## 相关

- [[knowledge-base]]
- [[RetrieveGroundingKnowledge]]
- [[GroundingKnowledgeCard]]
