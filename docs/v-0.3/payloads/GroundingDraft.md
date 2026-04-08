# GroundingDraft

`GroundingGenerationLLM` 输出的 grounding 草稿。

```text
GroundingDraft = {
  grounding_evidence_cards: list[GroundingEvidenceCard],
  frontier_seed_specifications: list[FrontierSeedSpecification]
}
```

## 稳定字段组

- grounding 证据卡：`grounding_evidence_cards`
- frontier 种子规格：`frontier_seed_specifications`

## Direct Producer / Direct Consumers

- Direct producer：GroundingGenerationLLM
- Direct consumers：[[GenerateGroundingOutput]]

## Invariants

- 它描述的是首轮语义启动建议，不是运行期活体状态。
- 种子规格必须经过 wrapper 归一化后才能进入 frontier 初始化。
- 非 generic 模式下，证据卡与种子规格都必须可回溯到 `KnowledgeRetrievalResult.retrieved_cards`。
- `generic_fallback` 下 LLM 草稿不得发明领域知识卡，也不得写出 `domain_company` 或 `crossover_compose` seed。

## 最小示例

```yaml
grounding_evidence_cards:
  - source_card_id: "role_alias.llm_agent_rag_engineering.backend_agent_engineer"
    label: "agent engineer"
    rationale: "role title 与 must-have 同时命中。"
    evidence_type: "title_alias"
    confidence: "high"
frontier_seed_specifications:
  - operator_name: "must_have_alias"
    seed_terms: ["agent engineer", "rag", "python"]
    seed_rationale: "先覆盖角色锚点与核心技术栈。"
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

- [[GroundingEvidenceCard]]
- [[FrontierSeedSpecification]]
- [[KnowledgeRetrievalResult]]
- [[GenerateGroundingOutput]]
