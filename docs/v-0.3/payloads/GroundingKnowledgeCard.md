# GroundingKnowledgeCard

编译后进入运行时知识库的单条结构化知识卡。

```text
GroundingKnowledgeCard = { card_id, domain_id, report_type, card_type, title, summary, canonical_terms, aliases, positive_signals, negative_signals, query_terms, must_have_links, preferred_links, confidence, source_report_ids, source_model_votes, freshness_date }
```

## 稳定字段组

- 卡片 id：`card_id`
- domain：`domain_id`
- 来源报告类型：`report_type`
- 卡片类型：`card_type`
- 标题与摘要：`title`、`summary`
- canonical 术语：`canonical_terms`
- 别名：`aliases`
- 正向信号：`positive_signals`
- 负向信号：`negative_signals`
- 推荐 query terms：`query_terms`
- must-have 链接：`must_have_links`
- preferred 链接：`preferred_links`
- 置信度：`confidence`
- 来源报告：`source_report_ids`
- 模型投票数：`source_model_votes`
- 新鲜度日期：`freshness_date`

## Direct Producer / Direct Consumers

- Direct producer：knowledge base compiler
- Direct consumers：[[RetrieveGroundingKnowledge]]

## Invariants

- `source_report_ids` 必须能追溯到 reviewed synthesis report 的 `report_id`。
- `confidence = low` 的 claim 不得直接进入 must-have gate。
- `query_terms` 必须是短语级、可直接进入 seed branch 的稳定词。

## 最小示例

```yaml
card_id: "role_alias.llm_agent_rag_engineering.backend_agent_engineer"
domain_id: "llm_agent_rag_engineering"
report_type: "role_family"
card_type: "role_alias"
title: "LLM/Agent 后端工程师"
summary: "面向 Agent/RAG/LLM 应用的后端与平台研发角色。"
canonical_terms: ["agent engineer", "rag engineer"]
aliases: ["llm application engineer", "ai backend engineer"]
positive_signals: ["tool calling", "workflow orchestration", "retrieval pipeline"]
negative_signals: ["pure prompt运营", "纯算法论文研究"]
query_terms: ["agent engineer", "rag", "python"]
must_have_links: ["cap.tool_orchestration", "cap.retrieval_pipeline"]
preferred_links: ["bg.to_b_delivery"]
confidence: "high"
source_report_ids: ["report.role_family.llm_agent_rag_engineering.codex_synthesis_2026_04_07"]
source_model_votes: 2
freshness_date: "2026-04-07"
```

## 相关

- [[knowledge-base]]
- [[RetrieveGroundingKnowledge]]
- [[KnowledgeRetrievalResult]]
