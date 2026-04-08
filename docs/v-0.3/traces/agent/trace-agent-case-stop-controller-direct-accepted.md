# Agent Trace: case-stop-controller-direct-accepted

## Trace Meta

```yaml
case_id: "case-stop-controller-direct-accepted"
audience: "agent"
paired_business_trace: "[[trace-business-case-stop-controller-direct-accepted]]"
start_payloads: ["RequirementSheet", "FrontierState_t", "RuntimeRoundState"]
terminal_artifact: "SearchRunResult"
terminal_status: "stopped_and_finalized"
node_id_rendering: "human-readable case-local example ids; runtime id owner remains operator specs"
```

## Scenario Inputs

```yaml
RequirementSheet:
  role_title: "Senior Python / LLM Engineer"
  must_have_capabilities:
    - "Python backend"
    - "LLM application"
    - "retrieval or ranking experience"
FrontierState_t:
  open_frontier_node_ids:
    - "child_search_domain_01"
    - "seed_platform"
  run_shortlist_candidate_ids: ["c07", "c17", "c19", "c51", "c32", "c91"]
  remaining_budget: 3
RuntimeRoundState:
  runtime_round_index: 2
```

## Operator Steps

### 1. SelectActiveFrontierNode

```yaml
operator_name: "SelectActiveFrontierNode"
operator_inputs:
  open_frontier_node_ids:
    - "child_search_domain_01"
    - "seed_platform"
tools_or_services: ["runtime deterministic priority scoring", "runtime donor packing"]
operator_outputs:
  SearchControllerContext_t:
    active_frontier_node_summary:
      frontier_node_id: "child_search_domain_01"
      selected_operator_name: "strict_core"
    donor_candidate_node_summaries: []
    allowed_operator_names:
      - "must_have_alias"
      - "strict_core"
      - "domain_company"
      - "crossover_compose"
key_assertions:
  - "The controller still receives a normal context before it asks to stop."
failure_or_reject_reason: null
```

### 2. GenerateSearchControllerDecision

```yaml
operator_name: "GenerateSearchControllerDecision"
operator_inputs:
  active_frontier_node_id: "child_search_domain_01"
  remaining_budget: 3
tools_or_services: ["SearchControllerDecisionLLM", "runtime deterministic normalization"]
llm_audit:
  output_mode: "provider_native_strict_structured_output"
  retries: 0
  output_retries: 1
  validator_retry_count: 0
operator_outputs:
  SearchControllerDecision_t:
    action: "stop"
    target_frontier_node_id: "child_search_domain_01"
    selected_operator_name: "strict_core"
    operator_args: {}
    expected_gain_hypothesis: "Current shortlist is already strong enough for final review."
key_assertions:
  - "The controller may suggest stop, but runtime guard still owns final stop."
failure_or_reject_reason: null
```

### 3. CarryForwardFrontierState

```yaml
operator_name: "CarryForwardFrontierState"
operator_inputs:
  open_frontier_node_ids:
    - "child_search_domain_01"
    - "seed_platform"
  remaining_budget: 3
tools_or_services: ["runtime deterministic logic"]
operator_outputs:
  FrontierState_t1:
    open_frontier_node_ids:
      - "child_search_domain_01"
      - "seed_platform"
    run_shortlist_candidate_ids: ["c07", "c17", "c19", "c51", "c32", "c91"]
    remaining_budget: 3
key_assertions:
  - "Direct-stop path does not create a child node or consume search budget."
failure_or_reject_reason: null
```

### 4. EvaluateStopCondition

```yaml
operator_name: "EvaluateStopCondition"
operator_inputs:
  action: "stop"
  runtime_round_index: 2
  BranchEvaluation_t: null
  NodeRewardBreakdown_t: null
tools_or_services: ["runtime stop guard"]
operator_outputs:
  stop_reason: "controller_stop"
  continue_flag: false
key_assertions:
  - "Direct-stop is accepted because min_round_index is satisfied."
failure_or_reject_reason: null
```

### 5. FinalizeSearchRun

```yaml
operator_name: "FinalizeSearchRun"
operator_inputs:
  ranked_shortlist_candidate_ids: ["c07", "c17", "c19", "c51", "c32", "c91"]
  stop_reason: "controller_stop"
tools_or_services: ["SearchRunFinalizationLLM", "runtime deterministic logic"]
llm_audit:
  output_mode: "provider_native_strict_structured_output"
  retries: 0
  output_retries: 1
  validator_retry_count: 0
operator_outputs:
  SearchRunResult:
    final_shortlist_candidate_ids: ["c07", "c17", "c19", "c51", "c32", "c91"]
    stop_reason: "controller_stop"
    run_summary: "Current shortlist already covers the key Python, LLM, and retrieval signals needed for final review."
key_assertions:
  - "Finalization may summarize the run but cannot rewrite stop_reason or shortlist order."
failure_or_reject_reason: null
```

## Invariant Checks

- `BranchEvaluation_t = null`
- `NodeRewardBreakdown_t = null`
- `stop_reason = "controller_stop"`
- no `SearchExecutionPlan_t` is created

## Terminal Outcome

```yaml
terminal_artifact: "SearchRunResult"
stop_reason: "controller_stop"
final_shortlist_candidate_ids: ["c07", "c17", "c19", "c51", "c32", "c91"]
```

## Judge Packet

```yaml
expected_route: "controller_direct_stop"
expected_allowed_operators: ["must_have_alias", "strict_core", "domain_company", "crossover_compose"]
expected_tool_calls:
  - "SearchControllerDecisionLLM"
  - "runtime stop guard"
  - "SearchRunFinalizationLLM"
expected_terminal_state:
  stop_reason: "controller_stop"
  continue_flag: false
must_hold:
  - "Direct-stop path passes null branch artifacts into EvaluateStopCondition."
  - "runtime_round_index satisfies min_round_index."
  - "FinalizeSearchRun is invoked after stop is accepted."
must_not_hold:
  - "CTS.search is called"
  - "RerankService is called"
  - "stop_reason = exhausted_low_gain"
```
