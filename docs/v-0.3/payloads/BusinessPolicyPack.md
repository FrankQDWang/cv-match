# BusinessPolicyPack

run 级业务偏好包，用于表达领域显式 override、排序偏好、风险偏好和解释口径。

```text
BusinessPolicyPack = { domain_pack_ids, fusion_weight_preferences, fit_gate_overrides, stability_policy, explanation_preferences }
```

## 稳定字段组

- domain pack 显式 override：`domain_pack_ids`
- 融合权重偏好：`fusion_weight_preferences`
- fit gate 覆盖：`fit_gate_overrides`
- 稳定性策略：`stability_policy`
- 解释偏好：`explanation_preferences`

## Direct Producer / Direct Consumers

- Direct producer：runtime config / business configuration
- Direct consumers：[[RetrieveGroundingKnowledge]]、[[FreezeScoringPolicy]]

## Invariants

- `BusinessPolicyPack` 表达的是偏好，不是需求真相。
- `domain_pack_ids` 一旦显式填写，就必须直接驱动 routing，不再自动推断领域。
- `domain_pack_ids` 最多只允许 2 个已知领域包。
- `fit_gate_overrides` 只能收紧 truth gate，不能放宽 `RequirementSheet.hard_constraints`。
- 如果 `stability_policy.mode = soft_penalty`，则稳定性默认不得进入 retrieval filter。

## 最小示例

```yaml
domain_pack_ids:
  - "llm_agent_rag_engineering"
  - "search_ranking_retrieval_engineering"
fusion_weight_preferences:
  rerank: 0.55
  must_have: 0.25
  preferred: 0.10
  risk_penalty: 0.10
fit_gate_overrides:
  min_years: 6
stability_policy:
  mode: "soft_penalty"
  penalty_weight: 1.0
  confidence_floor: 0.6
  allow_hard_gate: false
explanation_preferences:
  top_n_for_explanation: 5
  emphasize_business_delivery: true
```

## 相关

- [[RetrieveGroundingKnowledge]]
- [[FreezeScoringPolicy]]
- [[ScoringPolicy]]
