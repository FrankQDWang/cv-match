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

- `GroundingOutput` 只服务启动与少量 repair，不是通用知识仓。
- 它为 `InitializeFrontierState` 提供结构化 seed，而不是给控制器读长文本。
- `frontier_seed_specifications` 只携带 round-0 需要的地点投影，不承接整份 `RequirementSheet.hard_constraints`。

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
- [[GroundingDraft]]
- [[GenerateGroundingOutput]]
- [[FrontierState_t]]
