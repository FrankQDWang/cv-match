# GenerateSearchControllerDecision

在 active node 语境中生成 operator-centered 决策。

## 公式

```text
controller_prompt_t = {
  active_frontier_node_summary: SearchControllerContext_t.active_frontier_node_summary,
  frontier_head_summary: SearchControllerContext_t.frontier_head_summary,
  unmet_requirement_weights: SearchControllerContext_t.unmet_requirement_weights,
  operator_statistics_summary: SearchControllerContext_t.operator_statistics_summary,
  term_budget_range: SearchControllerContext_t.term_budget_range,
  fit_gate_constraints: SearchControllerContext_t.fit_gate_constraints
}

draft_decision_t = SearchControllerDecisionLLM(controller_prompt_t)

normalized_action_t =
  "stop" if draft_decision_t.action = "stop"
  else "search_cts"

requested_operator_name_t = draft_decision_t.selected_operator_name
requested_additional_terms_t =
  deduplicate(drop_empty(draft_decision_t.operator_args.additional_terms))

normalized_operator_name_t =
  whitelist(
    requested_operator_name_t,
    operator_catalog,
    fallback = SearchControllerContext_t.active_frontier_node_summary.selected_operator_name
  )

normalized_operator_args_t =
  {
    ...drop_empty_fields(draft_decision_t.operator_args),
    additional_terms:
      first(
        SearchControllerContext_t.term_budget_range[1],
        requested_additional_terms_t
      )
  }

d_t = {
  action: normalized_action_t,
  target_frontier_node_id: SearchControllerContext_t.active_frontier_node_summary.frontier_node_id,
  selected_operator_name: normalized_operator_name_t,
  operator_args: normalized_operator_args_t,
  expected_gain_hypothesis: normalize_text(draft_decision_t.expected_gain_hypothesis)
}
```

## Notation Legend

```text
d_t := SearchControllerDecision_t
```

## Read Set

- `SearchControllerContext_t.active_frontier_node_summary`
- `SearchControllerContext_t.frontier_head_summary`
- `SearchControllerContext_t.unmet_requirement_weights`
- `SearchControllerContext_t.operator_statistics_summary`
- `SearchControllerContext_t.term_budget_range`
- `SearchControllerContext_t.fit_gate_constraints`

## Derived / Intermediate

- `controller_prompt_t` 是控制器真正看到的 prompt payload；它不再读取整份 frontier。
- `draft_decision_t` 是 LLM 草稿，还不是最终写入对象。
- `requested_operator_name_t` 与 `requested_additional_terms_t` 是从 LLM 草稿里拆出来的原始 operator patch。
- `whitelist(...)` 负责把 `selected_operator_name` 压回 operator catalog；如果草稿越界，则退回当前 active node 的 operator 作为合法值。
- `drop_empty_fields(...)` 负责去掉空参数；`first(max_terms, requested_additional_terms_t)` 负责把新增 term 数量裁回预算上限。
- `target_frontier_node_id` 不接受 LLM 自由改写，固定绑定当前 active node。

## Write Set

- `SearchControllerDecision_t.action`
- `SearchControllerDecision_t.target_frontier_node_id`
- `SearchControllerDecision_t.selected_operator_name`
- `SearchControllerDecision_t.operator_args`
- `SearchControllerDecision_t.expected_gain_hypothesis`

## 输入 payload

- [[SearchControllerContext_t]]

## 输出 payload

- [[SearchControllerDecision_t]]

## 不确定性边界 / 说明

- 这一步输出的是局部 patch 决策，不是自由 query 文本，更不是直接可执行 CTS 请求。

## 相关

- [[operator-map]]
- [[expansion-trace]]
- [[SearchControllerContext_t]]
- [[SearchControllerDecision_t]]
