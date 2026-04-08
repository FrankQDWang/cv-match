# Agent Trace: case-crossover-illegal-reject

## Trace Meta

```yaml
case_id: "case-crossover-illegal-reject"
audience: "agent"
paired_business_trace: "[[trace-business-case-crossover-illegal-reject]]"
start_payloads: ["RequirementSheet", "FrontierState_t", "ScoringPolicy"]
terminal_artifact: "materialization_reject"
terminal_status: "reject_before_search"
node_id_rendering: "human-readable case-local example ids; runtime id owner remains operator specs"
```

## Scenario Inputs

```yaml
RequirementSheet:
  role_title: "Senior Python / LLM Engineer"
FrontierState_t:
  open_frontier_node_ids:
    - "child_agent_core_01"
    - "child_search_domain_01"
    - "seed_platform"
  remaining_budget: 4
ScoringPolicy:
  fit_gate_constraints:
    locations: ["Shanghai"]
    min_years: 5
```

## Operator Steps

### 1. SelectActiveFrontierNode

```yaml
operator_name: "SelectActiveFrontierNode"
operator_inputs:
  open_frontier_node_ids:
    - "child_agent_core_01"
    - "child_search_domain_01"
    - "seed_platform"
tools_or_services: ["runtime deterministic priority scoring", "runtime donor packing"]
operator_outputs:
  SearchControllerContext_t:
    active_frontier_node_summary:
      frontier_node_id: "child_agent_core_01"
      selected_operator_name: "must_have_alias"
    donor_candidate_node_summaries:
      - frontier_node_id: "child_search_domain_01"
        shared_anchor_terms: ["rag"]
        expected_incremental_coverage: ["retrieval or ranking experience"]
        reward_score: 3.9
    allowed_operator_names:
      - "must_have_alias"
      - "strict_core"
      - "domain_company"
      - "crossover_compose"
key_assertions:
  - "A legal donor candidate exists, so the reject must come from materialization guard rather than donor packing."
failure_or_reject_reason: null
```

### 2. GenerateSearchControllerDecision

```yaml
operator_name: "GenerateSearchControllerDecision"
operator_inputs:
  active_frontier_node_id: "child_agent_core_01"
  donor_candidate_ids: ["child_search_domain_01"]
tools_or_services: ["SearchControllerDecisionLLM", "runtime deterministic normalization"]
llm_audit:
  output_mode: "provider_native_strict_structured_output"
  retries: 0
  output_retries: 1
  validator_retry_count: 0
operator_outputs:
  SearchControllerDecision_t:
    action: "search_cts"
    target_frontier_node_id: "child_agent_core_01"
    selected_operator_name: "crossover_compose"
    operator_args:
      donor_frontier_node_id: "child_search_domain_01"
      shared_anchor_terms: []
      donor_terms_used: ["retrieval engineer", "ranking"]
    expected_gain_hypothesis: "Borrow retrieval coverage even without restating the shared anchor."
key_assertions:
  - "The decision can still request crossover, but guard enforcement happens downstream."
failure_or_reject_reason: null
```

### 3. MaterializeSearchExecutionPlan

```yaml
operator_name: "MaterializeSearchExecutionPlan"
operator_inputs:
  parent_frontier_node_id: "child_agent_core_01"
  donor_frontier_node_id: "child_search_domain_01"
  shared_anchor_terms: []
  donor_terms_used: ["retrieval engineer", "ranking"]
tools_or_services: ["runtime deterministic logic"]
operator_outputs:
  SearchExecutionPlan_t: null
key_assertions:
  - "Materialization fail-fast rejects crossover without any shared anchor."
failure_or_reject_reason: "crossover_requires_shared_anchor"
```

## Invariant Checks

- `SearchControllerDecision_t.selected_operator_name = "crossover_compose"`
- `SearchExecutionPlan_t = null`
- `failure_or_reject_reason = "crossover_requires_shared_anchor"`
- no child frontier node is created

## Terminal Outcome

```yaml
terminal_artifact: "materialization_reject"
reject_reason: "crossover_requires_shared_anchor"
continue_to_next_operator: "SelectActiveFrontierNode"
```

## Judge Packet

```yaml
expected_route: "crossover_reject"
expected_allowed_operators: ["must_have_alias", "strict_core", "domain_company", "crossover_compose"]
expected_tool_calls:
  - "SearchControllerDecisionLLM"
  - "runtime deterministic logic"
expected_terminal_state:
  search_execution_plan_created: false
  child_frontier_node_created: false
must_hold:
  - "The donor id remains whitelisted."
  - "Reject happens because shared_anchor_terms is empty."
must_not_hold:
  - "CTS.search is called"
  - "RerankService is called"
  - "SearchExecutionPlan_t is non-null"
```
