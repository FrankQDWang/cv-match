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

## 最小示例

```yaml
grounding_evidence_cards:
  - label: "ranking engineer"
    rationale: "JD 明示 retrieval 或 ranking 经验"
    evidence_type: "title_alias"
frontier_seed_specifications:
  - operator_name: "must_have_alias"
    seed_terms: ["ranking engineer", "retrieval engineer"]
    target_location: "Shanghai"
```

## 相关

- [[operator-map]]
- [[GroundingEvidenceCard]]
- [[FrontierSeedSpecification]]
- [[GenerateGroundingOutput]]
- [[GroundingOutput]]
