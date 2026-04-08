# Agent Trace: case-stop-controller-direct-rejected

## Trace Meta

```yaml
case_id: "case-stop-controller-direct-rejected"
audience: "agent"
paired_business_trace: "[[trace-business-case-stop-controller-direct-rejected]]"
start_payloads: ["RequirementSheet", "FrontierState_t", "RuntimeRoundState"]
terminal_artifact: "stop_reason / continue_flag"
terminal_status: "continue_after_rejected_stop"
node_id_rendering: "human-readable case-local example ids; runtime id owner remains operator specs"
```

## Scenario Inputs

```yaml
RequirementSheet:
  role_title: "Senior Python / LLM Engineer"
FrontierState_t:
  open_frontier_node_ids:
    - "child_search_domain_01"
    - "seed_platform"
  run_shortlist_candidate_ids: ["c07", "c17", "c19", "c51"]
  remaining_budget: 4
RuntimeRoundState:
  runtime_round_index: 1
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
  - "The controller can ask to stop even before the minimum round index is met."
failure_or_reject_reason: null
```

### 2. GenerateSearchControllerDecision

```yaml
operator_name: "GenerateSearchControllerDecision"
operator_inputs:
  active_frontier_node_id: "child_search_domain_01"
  runtime_round_index: 1
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
    expected_gain_hypothesis: "The shortlist looks promising enough to stop early."
key_assertions:
  - "Controller stop is only a suggestion."
failure_or_reject_reason: null
```

### 3. CarryForwardFrontierState

```yaml
operator_name: "CarryForwardFrontierState"
operator_inputs:
  open_frontier_node_ids:
    - "child_search_domain_01"
    - "seed_platform"
  remaining_budget: 4
tools_or_services: ["runtime deterministic logic"]
operator_outputs:
  FrontierState_t1:
    open_frontier_node_ids:
      - "child_search_domain_01"
      - "seed_platform"
    run_shortlist_candidate_ids: ["c07", "c17", "c19", "c51"]
    remaining_budget: 4
key_assertions:
  - "Identity carry-forward keeps the frontier unchanged before guard evaluation."
failure_or_reject_reason: null
```

### 4. EvaluateStopCondition

```yaml
operator_name: "EvaluateStopCondition"
operator_inputs:
  action: "stop"
  runtime_round_index: 1
  BranchEvaluation_t: null
  NodeRewardBreakdown_t: null
tools_or_services: ["runtime stop guard"]
operator_outputs:
  stop_reason: null
  continue_flag: true
key_assertions:
  - "Direct-stop is rejected because min_round_index is not yet satisfied."
failure_or_reject_reason: null
```

## Invariant Checks

- `BranchEvaluation_t = null`
- `NodeRewardBreakdown_t = null`
- `stop_reason = null`
- no `SearchExecutionPlan_t` is created

## Terminal Outcome

```yaml
terminal_artifact: "stop_reason / continue_flag"
stop_reason: null
continue_flag: true
next_required_operator: "SelectActiveFrontierNode"
```

## Judge Packet

```yaml
expected_route: "controller_direct_stop_rejected"
expected_allowed_operators: ["must_have_alias", "strict_core", "domain_company", "crossover_compose"]
expected_tool_calls:
  - "SearchControllerDecisionLLM"
  - "runtime stop guard"
expected_terminal_state:
  stop_reason: null
  continue_flag: true
must_hold:
  - "EvaluateStopCondition receives null branch artifacts."
  - "runtime_round_index is below min_round_index."
  - "The run continues after the rejected stop request."
must_not_hold:
  - "FinalizeSearchRun is called"
  - "CTS.search is called"
  - "stop_reason = controller_stop"
```
