# KnowledgeRetrievalResult

针对当前岗位从知识库快照中检索出的局部结果。

```text
KnowledgeRetrievalResult = {
  knowledge_base_snapshot_id,
  routing_mode,
  selected_domain_pack_ids,
  routing_confidence,
  fallback_reason,
  retrieved_cards: list[GroundingKnowledgeCard],
  negative_signal_terms
}
```

## 稳定字段组

- 知识库快照 id：`knowledge_base_snapshot_id`
- 路由模式：`routing_mode`
- 最终选中的领域包：`selected_domain_pack_ids`
- 路由置信度：`routing_confidence`
- fallback 原因：`fallback_reason`
- 命中的 knowledge cards：`retrieved_cards`
- 负向 / confusion 词：`negative_signal_terms`

## Direct Producer / Direct Consumers

- Direct producer：[[RetrieveGroundingKnowledge]]
- Direct consumers：[[GenerateGroundingOutput]]

## Invariants

- `retrieved_cards` 必须来自单一 `knowledge_base_snapshot_id`。
- `retrieved_cards` 的元素类型必须是完整 `GroundingKnowledgeCard` 对象，而不是 id 字符串。
- `routing_mode / selected_domain_pack_ids / routing_confidence / fallback_reason` 由本对象直接持有，不再拆出独立 routing metadata payload。
- `routing_mode` 只能是 `explicit_domain`、`inferred_domain`、`generic_fallback`。
- `selected_domain_pack_ids` 最多 2 个；`generic_fallback` 下必须为空数组。
- `negative_signal_terms` 在非 generic 模式下只能来自被检索到的高/中置信度卡片；`generic_fallback` 下回退为 `RequirementSheet.exclusion_signals`。

## 最小示例

```yaml
knowledge_base_snapshot_id: "kb-2026-04-07-v1"
routing_mode: "inferred_domain"
selected_domain_pack_ids:
  - "llm_agent_rag_engineering"
  - "search_ranking_retrieval_engineering"
routing_confidence: 0.7
fallback_reason: null
retrieved_cards:
  - card_id: "role_alias.llm_agent_rag_engineering.backend_agent_engineer"
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
negative_signal_terms:
  - "data analyst"
  - "pure algorithm research"
```

## 相关

- [[RetrieveGroundingKnowledge]]
- [[GroundingKnowledgeBaseSnapshot]]
- [[GroundingKnowledgeCard]]
