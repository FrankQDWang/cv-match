# InitializeFrontierState

用 grounding 结果和 runtime budget 初始化第一版 frontier。

## Signature

```text
InitializeFrontierState : (GroundingOutput, RuntimeSearchBudget, OperatorCatalog) -> FrontierState_t
```

## Notation Legend

```text
O := GroundingOutput
F_t := FrontierState_t
```

## Input Projection

```text
seed_specs_t = O.frontier_seed_specifications
initial_round_budget_t = RuntimeSearchBudget.initial_round_budget
operator_catalog_t = OperatorCatalog
```

## Primitive Predicates / Matching Rules

```text
seed_id_t(seed_spec_t) =
  "seed_"
  + seed_spec_t.operator_name
  + "_"
  + stable_hash(seed_spec_t.seed_terms, seed_spec_t.target_location)[0 : 8]
```

## Transformation

```text
seed_frontier_nodes_t =
  [
    {
      frontier_node_id: seed_id_t(seed_spec_t),
      parent_frontier_node_id: null,
      donor_frontier_node_id: null,
      selected_operator_name: seed_spec_t.operator_name,
      node_query_term_pool: stable_deduplicate(seed_spec_t.seed_terms),
      source_card_ids: seed_spec_t.source_card_ids,
      seed_rationale: seed_spec_t.seed_rationale,
      negative_terms: seed_spec_t.negative_terms,
      parent_shortlist_candidate_ids: [],
      node_shortlist_candidate_ids: [],
      node_shortlist_score_snapshot: {},
      previous_branch_evaluation: null,
      reward_breakdown: null,
      status: "open"
    }
    for seed_spec_t in seed_specs_t
  ]
```

### Field-Level Output Assembly

```text
F_t.frontier_nodes =
  {
    node_t.frontier_node_id: node_t
    for node_t in seed_frontier_nodes_t
  }
F_t.open_frontier_node_ids = [node.frontier_node_id for node in seed_frontier_nodes_t]
F_t.closed_frontier_node_ids = []
F_t.run_term_catalog =
  set(term_t for node_t in seed_frontier_nodes_t for term_t in node_t.node_query_term_pool)
F_t.run_shortlist_candidate_ids = []
F_t.semantic_hashes_seen = {}
F_t.operator_statistics =
  {
    operator_name: {average_reward: 0.0, times_selected: 0}
    for operator_name in operator_catalog_t
  }
F_t.remaining_budget = initial_round_budget_t
```

## Defaults / Thresholds Used Here

```text
RuntimeSearchBudget.initial_round_budget defaults to 5
```

## Read Set

- `GroundingOutput.frontier_seed_specifications`
- `RuntimeSearchBudget.initial_round_budget`
- `OperatorCatalog`

## Write Set

- `FrontierState_t.frontier_nodes`
- `FrontierState_t.open_frontier_node_ids`
- `FrontierState_t.closed_frontier_node_ids`
- `FrontierState_t.run_term_catalog`
- `FrontierState_t.run_shortlist_candidate_ids`
- `FrontierState_t.semantic_hashes_seen`
- `FrontierState_t.operator_statistics`
- `FrontierState_t.remaining_budget`

## 输入 payload

- [[GroundingOutput]]

## 输出 payload

- [[FrontierState_t]]

## 不确定性边界 / 说明

- frontier 初始化必须是 runtime-owned，不允许控制器或 grounding 草稿直接写 frontier 状态。
- seed 节点的 `reward_breakdown` 固定为 `null`，因此在第一轮之前不能作为 donor。

## 相关

- [[operator-spec-style]]
- [[GroundingOutput]]
- [[FrontierState_t]]
- [[FrontierNode_t]]
- [[OperatorCatalog]]
- [[RuntimeSearchBudget]]
