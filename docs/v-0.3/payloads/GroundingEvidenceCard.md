# GroundingEvidenceCard

当前岗位在 round-0 grounding 中实际采用的证据卡。

```text
GroundingEvidenceCard = { source_card_id, label, rationale, evidence_type, confidence }
```

## 稳定字段组

- 来源知识卡 id：`source_card_id`
- 标签：`label`
- 证据理由：`rationale`
- 证据类型：`evidence_type`
- 置信度：`confidence`

## Contained In

- `[[GroundingDraft]].grounding_evidence_cards`
- `[[GroundingOutput]].grounding_evidence_cards`

## Used By

- [[GenerateGroundingOutput]]
- [[InitializeFrontierState]]

## Invariants

- `source_card_id` 在非 generic 模式下必须能回溯到 `GroundingKnowledgeCard`；`generic_fallback` 下必须使用 `generic.requirement.*` 虚拟 id。
- `label` 必须是可直接进入 seed 推导或 grounding 展示的稳定短语。
- `evidence_type` 只能使用 [[GroundingCatalog]] 中允许的有限集合。

## 最小示例

```yaml
source_card_id: "role_alias.llm_agent_rag_engineering.backend_agent_engineer"
label: "agent engineer"
rationale: "knowledge card 与 JD 的 must-have 和 role title 同时命中。"
evidence_type: "title_alias"
confidence: "high"
```

## 相关

- [[GroundingKnowledgeCard]]
- [[GroundingCatalog]]
- [[GroundingDraft]]
- [[GroundingOutput]]
