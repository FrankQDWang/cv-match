# SeekTalent v0.3 单次 Expansion 字段级 Trace

> 本页是 worked example，只串联一条 `single expansion` 中“哪个 payload 变成了哪个 payload”。
> payload 的对象定义见 `payloads/`，operator 契约见 `operators/`。
> 本页是白盒状态账本，不重复 payload shape，只展示单轮状态如何推进。

## 0. Notation Legend

```text
R := RequirementSheet
P := ScoringPolicy
F_t := FrontierState_t
F_{t+1} := FrontierState_t1
n_t := active frontier node
d_t := SearchControllerDecision_t
p_t := SearchExecutionPlan_t
x_t := SearchExecutionResult_t
y_t := SearchScoringResult_t
a_t := BranchEvaluation_t
b_t := NodeRewardBreakdown_t
```

## 1. 初始快照

### 1.1 [[RequirementSheet]] 摘要

```text
R.role_title = "Senior Python / LLM Engineer"
R.must_have_capabilities = [
  "Python backend",
  "LLM application",
  "retrieval or ranking experience"
]
R.hard_constraints = {
  locations: ["Shanghai"],
  min_years: 5
}
```

### 1.2 [[ScoringPolicy]] 摘要

```text
P.fit_gate_constraints = {
  locations: ["Shanghai"],
  min_years: 5
}
P.ranking_notes = "must-have 优先于背景加分"
```

### 1.3 [[FrontierState_t]] 摘要

```text
F_t.open_frontier_node_ids = ["seed_alias", "seed_domain"]
F_t.closed_frontier_node_ids = ["seed_core"]
F_t.run_term_catalog = {"python backend", "llm application", "retrieval", "ranking", "rag"}
F_t.run_shortlist_candidate_ids = ["c17", "c32", "c91"]
F_t.semantic_hashes_seen = {"hash_core_01", "hash_alias_02"}
F_t.remaining_budget = 3
```

### 1.4 当前 `n_t` 摘要

```text
n_t = {
  frontier_node_id: "seed_alias",
  selected_operator_name: "must_have_alias",
  node_query_term_pool: ["python backend", "llm application", "rag"],
  parent_shortlist_candidate_ids: ["c17", "c32", "c91"],
  node_shortlist_candidate_ids: ["c32", "c44"],
  previous_branch_evaluation: {
    novelty_score: 0.48,
    usefulness_score: 0.62,
    branch_exhausted: false
  },
  reward_breakdown: {
    reward_score: 3.80
  },
  status: "open"
}
```

## 2. [[SelectActiveFrontierNode]] -> [[SearchControllerContext_t]]

```text
open_nodes_t = [
  F_t.frontier_nodes["seed_alias"],
  F_t.frontier_nodes["seed_domain"]
]

priority_score_t("seed_alias") = 4.12
priority_score_t("seed_domain") = 3.71
n_t = argmax priority_score_t = F_t.frontier_nodes["seed_alias"]

SearchControllerContext_t = {
  active_frontier_node_summary: {
    frontier_node_id: "seed_alias",
    selected_operator_name: "must_have_alias",
    node_query_term_pool: ["python backend", "llm application", "rag"],
    node_shortlist_candidate_ids: ["c32", "c44"]
  },
  frontier_head_summary: {
    open_node_count: 2,
    remaining_budget: 3,
    highest_priority_score: 4.12
  },
  unmet_requirement_weights: {
    retrieval_or_ranking_experience: 0.8
  },
  operator_statistics_summary: {
    must_have_alias: {average_reward: 3.8, times_selected: 1},
    domain_company: {average_reward: 2.9, times_selected: 1}
  },
  term_budget_range: [3, 8],
  fit_gate_constraints: {
    locations: ["Shanghai"],
    min_years: 5
  }
}
```

## 3. [[GenerateSearchControllerDecision]] -> [[SearchControllerDecision_t]]

```text
controller_prompt_t = {
  active_frontier_node_summary: SearchControllerContext_t.active_frontier_node_summary,
  frontier_head_summary: SearchControllerContext_t.frontier_head_summary,
  unmet_requirement_weights: SearchControllerContext_t.unmet_requirement_weights,
  operator_statistics_summary: SearchControllerContext_t.operator_statistics_summary,
  term_budget_range: SearchControllerContext_t.term_budget_range,
  fit_gate_constraints: SearchControllerContext_t.fit_gate_constraints
}

draft_decision_t = {
  action: "search_cts",
  selected_operator_name: "domain_company",
  operator_args: {
    company_archetypes: ["AI startup", "consumer internet"],
    additional_terms: ["ranking engineer"]
  },
  expected_gain_hypothesis: "补足 retrieval 或 ranking 相关信号"
}

normalized_action_t = "search_cts"
normalized_operator_name_t = "domain_company"
normalized_operator_args_t = draft_decision_t.operator_args

d_t = {
  action: normalized_action_t,
  target_frontier_node_id: "seed_alias",
  selected_operator_name: normalized_operator_name_t,
  operator_args: normalized_operator_args_t,
  expected_gain_hypothesis: "补足 retrieval 或 ranking 相关信号"
}
```

## 4. [[MaterializeSearchExecutionPlan]] -> [[SearchExecutionPlan_t]]

```text
parent_node_t = F_t.frontier_nodes[d_t.target_frontier_node_id]
base_query_terms_t = parent_node_t.node_query_term_pool
additional_terms_t = ["ranking engineer"]
query_terms_t = ["python backend", "llm application", "rag", "ranking engineer"]
projected_filters_t = R.hard_constraints
runtime_only_constraints_t = {
  must_have_keywords: ["retrieval", "ranking", "rag"]
}
target_new_t = 10
semantic_hash_t = "hash_domain_03"

p_t = {
  query_terms: query_terms_t,
  projected_filters: projected_filters_t,
  runtime_only_constraints: runtime_only_constraints_t,
  target_new_candidate_count: target_new_t,
  semantic_hash: semantic_hash_t,
  child_frontier_node_stub: {
    frontier_node_id: "child_domain_03",
    parent_frontier_node_id: "seed_alias",
    selected_operator_name: "domain_company"
  }
}
```

## 5. [[ExecuteSearchPlan]] -> [[SearchExecutionResult_t]]

```text
cts_request_t = {
  query_terms: p_t.query_terms,
  projected_filters: p_t.projected_filters,
  target_new_candidate_count: p_t.target_new_candidate_count
}

raw_candidates_t = ["c07", "c19", "c51", "c77", "c77"]
filtered_candidates_t = ["c07", "c19", "c51", "c77", "c77"]
deduplicated_candidates_t = ["c07", "c19", "c51", "c77"]

x_t = {
  raw_candidates: raw_candidates_t,
  deduplicated_candidates: deduplicated_candidates_t,
  search_page_statistics: {
    pages_fetched: 2,
    duplicate_rate: 0.25,
    latency_ms: 1800
  },
  search_observation: {
    unique_candidate_ids: ["c07", "c19", "c51", "c77"],
    shortage_after_last_page: false
  }
}
```

## 6. [[ScoreSearchResults]] -> [[SearchScoringResult_t]]

```text
scoring_packets_t = [
  {candidate_id: "c07", fit_gate_constraints: P.fit_gate_constraints},
  {candidate_id: "c19", fit_gate_constraints: P.fit_gate_constraints},
  {candidate_id: "c51", fit_gate_constraints: P.fit_gate_constraints},
  {candidate_id: "c77", fit_gate_constraints: P.fit_gate_constraints}
]

draft_score_cards_t = [
  {candidate_id: "c07", fit: 1, overall: 86, must_have: 92, risk: 8, base_score: 2.796},
  {candidate_id: "c19", fit: 1, overall: 84, must_have: 88, risk: 10, base_score: 2.610},
  {candidate_id: "c51", fit: 1, overall: 79, must_have: 82, risk: 14, base_score: 2.124},
  {candidate_id: "c77", fit: 0, overall: 65, must_have: 68, risk: 24, base_score: 1.126}
]

y_t.scored_candidates = draft_score_cards_t
y_t.node_shortlist_candidate_ids = ["c07", "c19", "c51"]
y_t.top_three_statistics = {
  average_base_score_top_three: 2.51
}
```

## 7. [[EvaluateBranchOutcome]] -> [[BranchEvaluation_t]]

```text
parent_node_t = F_t.frontier_nodes[p_t.child_frontier_node_stub.parent_frontier_node_id]

branch_evaluation_packet_t = {
  must_have_capabilities: R.must_have_capabilities,
  parent_frontier_node_id: parent_node_t.frontier_node_id,
  previous_node_shortlist_candidate_ids: parent_node_t.node_shortlist_candidate_ids,
  query_terms: p_t.query_terms,
  semantic_hash: p_t.semantic_hash,
  search_page_statistics: x_t.search_page_statistics,
  node_shortlist_candidate_ids: y_t.node_shortlist_candidate_ids,
  top_three_statistics: y_t.top_three_statistics
}

draft_branch_evaluation_t = {
  novelty_score: 0.66,
  usefulness_score: 0.74,
  branch_exhausted: false,
  repair_operator_hint: "strict_core",
  evaluation_notes: "ranking 背景补强有效"
}

a_t = {
  novelty_score: draft_branch_evaluation_t.novelty_score,
  usefulness_score: draft_branch_evaluation_t.usefulness_score,
  branch_exhausted: draft_branch_evaluation_t.branch_exhausted,
  repair_operator_hint: draft_branch_evaluation_t.repair_operator_hint,
  evaluation_notes: draft_branch_evaluation_t.evaluation_notes
}
```

## 8. [[ComputeNodeRewardBreakdown]] -> [[NodeRewardBreakdown_t]]

```text
incumbent_top_three_average_t = 2.17
candidate_top_three_average_t = y_t.top_three_statistics.average_base_score_top_three
delta_top_three_t = candidate_top_three_average_t - incumbent_top_three_average_t
must_have_gain_t = 0.67
new_fit_yield_t = 1.00
diversity_t = 0.44
hard_constraint_violation_t = 0.00
duplicate_penalty_t = x_t.search_page_statistics.duplicate_rate
cost_penalty_t = 0.42
reward_score_t = 4.56

b_t = {
  delta_top_three: delta_top_three_t,
  must_have_gain: must_have_gain_t,
  new_fit_yield: new_fit_yield_t,
  novelty: 0.66,
  usefulness: 0.74,
  diversity: diversity_t,
  hard_constraint_violation: hard_constraint_violation_t,
  duplicate_penalty: duplicate_penalty_t,
  cost_penalty: cost_penalty_t,
  reward_score: reward_score_t
}
```

## 9. [[UpdateFrontierState]] -> [[FrontierState_t1]]

```text
T(F_{t+1}) = T(F_t) ∪ set(p_t.query_terms)
H(F_{t+1}) = H(F_t) ∪ {p_t.semantic_hash}
Top(F_{t+1}) = TopK(Eligible(Top(F_t) ∪ node shortlist from y_t))

parent_node_t = F_t.frontier_nodes["seed_alias"]

child_frontier_node_t = {
  frontier_node_id: "child_domain_03",
  parent_frontier_node_id: "seed_alias",
  selected_operator_name: "domain_company",
  node_query_term_pool: ["python backend", "llm application", "rag", "ranking engineer"],
  parent_shortlist_candidate_ids: ["c32", "c44"],
  node_shortlist_candidate_ids: ["c07", "c19", "c51"],
  previous_branch_evaluation: a_t,
  reward_breakdown: b_t,
  status: "open"
}

frontier_nodes_t1 = replace parent "seed_alias" with status="closed", then upsert child_frontier_node_t

F_{t+1}.open_frontier_node_ids = ["seed_domain", "child_domain_03"]
F_{t+1}.closed_frontier_node_ids = ["seed_core", "seed_alias"]
F_{t+1}.run_term_catalog = F_t.run_term_catalog union {"ranking engineer"}
F_{t+1}.run_shortlist_candidate_ids = merge old shortlist with ["c07", "c19", "c51"]
F_{t+1}.semantic_hashes_seen = F_t.semantic_hashes_seen union {"hash_domain_03"}
F_{t+1}.remaining_budget = 2
```

## 10. [[EvaluateStopCondition]]

```text
budget_exhausted_t = (F_{t+1}.remaining_budget <= 0)
no_open_node_t = (size(F_{t+1}.open_frontier_node_ids) = 0)
controller_stop_requested_t = (d_t.action = "stop")
controller_stop_accepted_t = (
  controller_stop_requested_t
  and runtime_round_index >= min_round_index
)
low_gain_branch_t = (
  a_t.branch_exhausted
  and a_t.novelty_score < 0.30
  and a_t.usefulness_score < 0.30
  and b_t.reward_score < 1.00
)

stop_reason =
  "budget_exhausted" if budget_exhausted_t
  else "no_open_node" if no_open_node_t
  else "exhausted_low_gain" if low_gain_branch_t
  else "controller_stop" if controller_stop_accepted_t
  else null

continue_flag = (stop_reason = null)

Inputs:
- F_{t+1}.remaining_budget
- F_{t+1}.open_frontier_node_ids
- d_t.action
- a_t.branch_exhausted
- a_t.novelty_score
- a_t.usefulness_score
- b_t.reward_score
```
