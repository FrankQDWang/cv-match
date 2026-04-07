# GenerateGroundingOutput

把 grounding 草稿归一化为 round-0 可消费的结构化启动结果。

## 公式

```text
draft_grounding_cards_t =
  normalize_grounding_cards(GroundingDraft.grounding_evidence_cards)

draft_seed_specifications_t =
  normalize_seed_specifications(GroundingDraft.frontier_seed_specifications)

GroundingOutput = {
  grounding_evidence_cards:
    filter_supported_cards(draft_grounding_cards_t, R.must_have_capabilities),
  frontier_seed_specifications:
    project_seed_target_location(draft_seed_specifications_t, R.hard_constraints.locations)
}
```

## Notation Legend

```text
R := RequirementSheet
```

## Read Set

- `RequirementSheet.must_have_capabilities`
- `RequirementSheet.hard_constraints.locations`
- `GroundingDraft.grounding_evidence_cards`
- `GroundingDraft.frontier_seed_specifications`

## Derived / Intermediate

- `normalize_grounding_cards(...)` 负责删空、去重，并把证据卡压成稳定字段集合。
- `normalize_seed_specifications(...)` 负责把 operator 名、seed term 和附属元数据收敛为统一结构。
- `filter_supported_cards(...)` 只保留与岗位 must-have 有关的 grounding 证据，不把草稿里的任意旁支知识带进主链。
- `project_seed_target_location(...)` 只把岗位地点约束投影到 `target_location`，不把整份 `hard_constraints` 塞进 seed spec。

## Write Set

- `GroundingOutput.grounding_evidence_cards`
- `GroundingOutput.frontier_seed_specifications`

## 输入 payload

- [[RequirementSheet]]
- [[GroundingDraft]]

## 输出 payload

- [[GroundingOutput]]

## 不确定性边界 / 说明

- 这是启动层，不承担 run 中的通用知识检索或长期记忆。

## 相关

- [[operator-map]]
- [[expansion-trace]]
- [[RequirementSheet]]
- [[GroundingDraft]]
- [[GroundingOutput]]
