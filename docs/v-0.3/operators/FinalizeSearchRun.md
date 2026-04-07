# FinalizeSearchRun

读取 run 级 shortlist，生成最终运行结果摘要。

## 公式

```text
supporting_frontier_nodes_t =
  frontier_nodes_that_support(F_{t+1}.frontier_nodes, F_{t+1}.run_shortlist_candidate_ids)

candidate_rank_key_t(candidate_id) =
  max(
    node_t.reward_breakdown.reward_score
    for node_t in supporting_frontier_nodes_t
    if candidate_id in node_t.node_shortlist_candidate_ids
  )

ranked_shortlist_t =
  stable_sort_desc(F_{t+1}.run_shortlist_candidate_ids, key = candidate_rank_key_t)

finalization_context_t = {
  role_title: R.role_title,
  must_have_capabilities: R.must_have_capabilities,
  hard_constraints: R.hard_constraints,
  ranked_candidates: ranked_shortlist_t,
  stop_reason: stop_reason
}

draft_run_summary_t = SearchRunFinalizationLLM(finalization_context_t)

SearchRunResult = {
  final_shortlist_candidate_ids: ranked_shortlist_t,
  run_summary: normalize_text(draft_run_summary_t.run_summary),
  stop_reason: stop_reason
}
```

## Notation Legend

```text
R := RequirementSheet
F_{t+1} := FrontierState_t1
```

## Read Set

- `RequirementSheet.role_title`
- `RequirementSheet.must_have_capabilities`
- `RequirementSheet.hard_constraints`
- `FrontierState_t1.frontier_nodes`
- `FrontierState_t1.run_shortlist_candidate_ids`
- `stop_reason`

## Derived / Intermediate

- `supporting_frontier_nodes_t` 负责把 run-global shortlist 回挂到真正产出这些候选的 frontier 节点。
- `candidate_rank_key_t(candidate_id)` 取所有支持该候选的 frontier 节点里最高的 reward 分数，作为最终排序键。
- `stable_sort_desc(...)` 只在 `F_{t+1}.run_shortlist_candidate_ids` 给定的事实集合内排序，不创建新候选。
- `finalization_context_t` 是 finalizer 真正可见的缩口上下文，不把整份 frontier 原样喂给 LLM。
- `normalize_text(...)` 只清洗总结文本，不允许它改写 shortlist id 或 stop reason。

## Write Set

- `SearchRunResult.final_shortlist_candidate_ids`
- `SearchRunResult.run_summary`
- `SearchRunResult.stop_reason`

## 输入 payload

- [[RequirementSheet]]
- [[FrontierState_t1]]
- `stop_reason`

## 输出 payload

- [[SearchRunResult]]

## 不确定性边界 / 说明

- LLM 可以写总结，但不能改写 run-global shortlist 事实。

## 相关

- [[operator-map]]
- [[expansion-trace]]
- [[RequirementSheet]]
- [[FrontierState_t1]]
- [[SearchRunResult]]
