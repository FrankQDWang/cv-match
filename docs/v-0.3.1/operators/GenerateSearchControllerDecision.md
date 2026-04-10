# GenerateSearchControllerDecision

在 active node 语境中生成 operator-centered 决策。

## Signature

```text
GenerateSearchControllerDecision : SearchControllerContext_t -> SearchControllerDecision_t
```

## Prompt Surface

控制器不再读取 raw JSON payload。

`SearchControllerContext_t` 会先被投影成固定顺序的 prompt surface：

1. `Task Contract`
2. `Role Summary`
3. `Active Frontier Node`
4. `Donor Candidates`
5. `Allowed Operators`
6. `Operator Statistics`
7. `Fit Gates And Unmet Requirements`
8. `Runtime Budget State`
9. `Budget Warning`，仅当 `runtime_budget_state.near_budget_end = true`
10. `Decision Request`

这个 prompt surface 会完整落入 `controller_audit.prompt_surface`。

## Deterministic Normalization

控制器 LLM 先产出 `SearchControllerDecisionDraft_t`，然后 runtime 再做 deterministic 收口：

- `action` 只允许 `search_cts / stop`
- `selected_operator_name` 只能来自 `allowed_operator_names`
- 非 `crossover_compose` 的 `additional_terms` 会按 `term_budget_range` 裁剪
- `crossover_compose` 的 donor 只能来自合法 donor candidate 列表
- `target_frontier_node_id` 固定绑定 active node，不接受 LLM 改写

## Read Set

- `SearchControllerContext_t.role_title`
- `SearchControllerContext_t.role_summary`
- `SearchControllerContext_t.active_frontier_node_summary`
- `SearchControllerContext_t.donor_candidate_node_summaries`
- `SearchControllerContext_t.frontier_head_summary`
- `SearchControllerContext_t.unmet_requirement_weights`
- `SearchControllerContext_t.operator_statistics_summary`
- `SearchControllerContext_t.allowed_operator_names`
- `SearchControllerContext_t.term_budget_range`
- `SearchControllerContext_t.fit_gate_constraints`
- `SearchControllerContext_t.runtime_budget_state`

## Write Set

- `SearchControllerDecision_t.action`
- `SearchControllerDecision_t.target_frontier_node_id`
- `SearchControllerDecision_t.selected_operator_name`
- `SearchControllerDecision_t.operator_args`
- `SearchControllerDecision_t.expected_gain_hypothesis`

## 不确定性边界

- 唯一黑盒是 `SearchControllerDecisionLLM`；它只能返回 `SearchControllerDecisionDraft_t`
- provider-native strict structured output 固定为 `retries=0`、`output_retries=1`
- 仅允许单次业务型 validator retry，且只用于“能物化合法 query terms / crossover args”
- prompt 审计唯一 owner 是 `controller_audit.prompt_surface`

## 相关

- [[SearchControllerContext_t]]
- [[SearchControllerDecisionDraft_t]]
- [[SearchControllerDecision_t]]
- [[PromptSurfaceSnapshot]]
