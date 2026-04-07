# SearchControllerDecision_t

控制器规范化后的分支级决策对象。

```text
SearchControllerDecision_t = { action, target_frontier_node_id, selected_operator_name, operator_args, expected_gain_hypothesis }
```

## 稳定字段组

- 动作：`action`
- 目标节点 id：`target_frontier_node_id`
- operator 名称：`selected_operator_name`
- operator 参数：`operator_args`
- 预期增益假设：`expected_gain_hypothesis`

## Direct Producer / Direct Consumers

- Direct producer：[[GenerateSearchControllerDecision]]
- Direct consumers：[[MaterializeSearchExecutionPlan]]、[[EvaluateStopCondition]]

## Invariants

- `target_frontier_node_id` 必须绑定当前 active node。
- `selected_operator_name` 必须来自 operator catalog。
- `action` 只能来自 runtime 允许的有限集合。

## 最小示例

```yaml
action: "search_cts"
target_frontier_node_id: "seed_alias"
selected_operator_name: "domain_company"
operator_args:
  company_archetypes: ["AI startup", "consumer internet"]
  additional_terms: ["ranking engineer"]
expected_gain_hypothesis: "补足 retrieval/ranking 相关信号"
```

## 相关

- [[operator-map]]
- [[SearchControllerContext_t]]
- [[GenerateSearchControllerDecision]]
- [[SearchExecutionPlan_t]]
