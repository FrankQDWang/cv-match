# GroundingOutput

归一化后的 round-0 grounding 结果。

```text
GroundingOutput = {
  grounding_evidence_cards: list[GroundingEvidenceCard],
  frontier_seed_specifications: list[FrontierSeedSpecification]
}
```

## 稳定字段组

- grounding 证据卡：`grounding_evidence_cards`
- frontier 种子规格：`frontier_seed_specifications`

## Direct Producer / Direct Consumers

- Direct producer：[[GenerateGroundingOutput]]
- Direct consumers：[[InitializeFrontierState]]

## Invariants

- `GroundingOutput` 只服务 bootstrap 关键词初始化，不是通用知识仓。
- 它为 `InitializeFrontierState` 提供结构化 seed，而不是给控制器读长文本。
- `frontier_seed_specifications` 必须固定在 3-5 条，每条 2-4 个 query terms。
- `generic_fallback` 下不得产出 `domain_company` 或 `crossover_compose` seed。

## 最小示例

```yaml
grounding_evidence_cards:
  - source_card_id: "role_alias.llm_agent_rag_engineering.backend_agent_engineer"
    label: "agent engineer"
    rationale: "知识卡与 JD 核心锚点一致。"
    evidence_type: "title_alias"
    confidence: "high"
frontier_seed_specifications:
  - operator_name: "must_have_alias"
    seed_terms: ["agent engineer", "rag", "python"]
    seed_rationale: "先打角色锚点。"
    source_card_ids:
      - "role_alias.llm_agent_rag_engineering.backend_agent_engineer"
    expected_coverage:
      - "Python backend"
      - "LLM application"
    negative_terms:
      - "data analyst"
    target_location: "Shanghai"
```

## 相关

- [[KnowledgeRetrievalResult]]
- [[GroundingKnowledgeCard]]
- [[GroundingEvidenceCard]]
- [[FrontierSeedSpecification]]
- [[GenerateGroundingOutput]]
