# ExtractRequirements

把原始输入和需求抽取草稿固化为业务真相 `RequirementSheet`。

## 公式

```text
draft_role_title_t = clean_title(RequirementExtractionDraft.role_title_candidate)
draft_capabilities_t = deduplicate(drop_empty(RequirementExtractionDraft.capability_candidates))
draft_hard_constraints_t = coerce_constraint_map(RequirementExtractionDraft.hard_constraint_candidates)
draft_scoring_rationale_t = trim(RequirementExtractionDraft.scoring_rationale_candidate)

R = {
  role_title: coalesce(draft_role_title_t, title_from(SearchInputTruth.job_description)),
  must_have_capabilities: draft_capabilities_t,
  hard_constraints: draft_hard_constraints_t,
  scoring_rationale: draft_scoring_rationale_t
}
```

## Notation Legend

```text
R := RequirementSheet
```

## Read Set

- `SearchInputTruth.job_description`
- `RequirementExtractionDraft.role_title_candidate`
- `RequirementExtractionDraft.capability_candidates`
- `RequirementExtractionDraft.hard_constraint_candidates`
- `RequirementExtractionDraft.scoring_rationale_candidate`

## Derived / Intermediate

- `clean_title(...)` 负责裁掉空白、去掉明显冗词，并把岗位标题收敛成单个稳定字符串。
- `deduplicate(drop_empty(...))` 负责删空值、去重复、保留 capability 的阅读顺序。
- `coerce_constraint_map(...)` 负责把草稿里的地点、年限等约束投影为稳定键名与稳定值形态。
- `title_from(SearchInputTruth.job_description)` 只在草稿标题缺失时兜底回到原始输入，不引入第二份真相。

## Write Set

- `RequirementSheet.role_title`
- `RequirementSheet.must_have_capabilities`
- `RequirementSheet.hard_constraints`
- `RequirementSheet.scoring_rationale`

## 输入 payload

- [[SearchInputTruth]]
- [[RequirementExtractionDraft]]

## 输出 payload

- [[RequirementSheet]]

## 不确定性边界 / 说明

- LLM 只负责提出草稿；最终进入主链的 `RequirementSheet` 必须经过 deterministic normalization。

## 相关

- [[operator-map]]
- [[expansion-trace]]
- [[SearchInputTruth]]
- [[RequirementExtractionDraft]]
- [[RequirementSheet]]
