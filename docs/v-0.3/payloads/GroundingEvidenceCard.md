# GroundingEvidenceCard

round-0 grounding 使用的单条结构化证据卡。

```text
GroundingEvidenceCard = { label, rationale, evidence_type }
```

## 稳定字段组

- 标签：`label`
- 证据理由：`rationale`
- 证据类型：`evidence_type`

## Contained In

- `[[GroundingDraft]].grounding_evidence_cards`
- `[[GroundingOutput]].grounding_evidence_cards`

## Used By

- [[GenerateGroundingOutput]]
- [[InitializeFrontierState]]

## Invariants

- `label` 必须是可直接进入 seed 推导或 grounding 展示的稳定短语。
- `evidence_type` 只能使用 grounding catalog 中允许的有限集合。

## 最小示例

```yaml
label: "ranking engineer"
rationale: "JD 明示 retrieval 或 ranking 经验"
evidence_type: "title_alias"
```

## 相关

- [[GroundingDraft]]
- [[GroundingOutput]]
- [[GenerateGroundingOutput]]
