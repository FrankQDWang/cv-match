# Agent Trace: case-bootstrap-generic-fallback

## Trace Meta

```yaml
case_id: "case-bootstrap-generic-fallback"
audience: "agent"
paired_business_trace: "[[trace-business-case-bootstrap-generic-fallback]]"
start_payloads: ["SearchInputTruth", "BusinessPolicyPack", "GroundingKnowledgeBaseSnapshot"]
terminal_artifact: "SearchControllerContext_t"
terminal_status: "continue_to_controller"
node_id_rendering: "human-readable case-local example ids; runtime id owner remains operator specs"
```

## Scenario Inputs

```yaml
SearchInputTruth:
  job_description_focus: "Enterprise SaaS Data Governance Lead"
BusinessPolicyPack:
  domain_pack_ids: []
GroundingKnowledgeBaseSnapshot:
  available_domain_packs:
    - "llm_agent_rag_engineering"
    - "search_ranking_retrieval_engineering"
    - "finance_risk_control_ai"
```

## Operator Steps

### 1. ExtractRequirements

```yaml
operator_name: "ExtractRequirements"
operator_inputs:
  SearchInputTruth:
    role_signal: "Enterprise SaaS Data Governance Lead"
tools_or_services: ["RequirementExtractionLLM", "runtime deterministic normalization"]
llm_audit:
  output_mode: "provider_native_strict_structured_output"
  retries: 0
  output_retries: 1
  validator_retry_count: 0
operator_outputs:
  RequirementSheet:
    role_title: "Enterprise SaaS Data Governance Lead"
    must_have_capabilities:
      - "data governance"
      - "stakeholder management"
      - "enterprise delivery"
      - "cross-functional program leadership"
      - "policy design"
key_assertions:
  - "Requirement truth is extracted even when no domain pack matches."
failure_or_reject_reason: null
```

### 2. RetrieveGroundingKnowledge

```yaml
operator_name: "RetrieveGroundingKnowledge"
operator_inputs:
  explicit_domain_pack_ids: []
  role_title: "Enterprise SaaS Data Governance Lead"
tools_or_services: ["local grounding knowledge base snapshot", "runtime deterministic routing"]
operator_outputs:
  KnowledgeRetrievalResult:
    routing_mode: "generic_fallback"
    selected_domain_pack_ids: []
    routing_confidence: 0.3
    retrieved_cards: []
    negative_signal_terms:
      - "pure algorithm research"
      - "junior analyst"
key_assertions:
  - "No domain pack crosses threshold; generic fallback is forced."
failure_or_reject_reason: null
```

### 3. FreezeScoringPolicy

```yaml
operator_name: "FreezeScoringPolicy"
operator_inputs:
  routing_mode: "generic_fallback"
tools_or_services: ["runtime deterministic logic"]
operator_outputs:
  ScoringPolicy:
    fit_gate_constraints: {}
    fusion_weights:
      rerank: 0.55
      must_have: 0.25
      preferred: 0.1
      risk_penalty: 0.1
key_assertions:
  - "Scoring policy still freezes before search even with no retrieved cards."
failure_or_reject_reason: null
```

### 4. GenerateGroundingOutput

```yaml
operator_name: "GenerateGroundingOutput"
operator_inputs:
  routing_mode: "generic_fallback"
  retrieved_cards: []
tools_or_services: ["GroundingGenerationLLM draft", "runtime deterministic normalization"]
llm_audit:
  output_mode: "provider_native_strict_structured_output"
  retries: 0
  output_retries: 1
  validator_retry_count: 0
operator_outputs:
  GroundingOutput:
    grounding_evidence_cards:
      - "generic.requirement.role_title"
      - "generic.requirement.must_have.0"
      - "generic.requirement.must_have.1"
    frontier_seed_specifications:
      - {operator_name: "must_have_alias", seed_rationale: "role_title_anchor"}
      - {operator_name: "must_have_alias", seed_rationale: "must_have_core"}
      - {operator_name: "strict_core", seed_rationale: "coverage_repair"}
      - {operator_name: "strict_core", seed_rationale: "must_have_repair"}
      - {operator_name: "strict_core", seed_rationale: "must_have_repair"}
key_assertions:
  - "Generic evidence uses virtual ids."
  - "Repair seeds are emitted because uncovered must-haves remain."
failure_or_reject_reason: null
```

### 5. InitializeFrontierState

```yaml
operator_name: "InitializeFrontierState"
operator_inputs:
  frontier_seed_specifications_count: 5
tools_or_services: ["runtime deterministic logic"]
operator_outputs:
  FrontierState_t:
    open_frontier_node_ids:
      - "seed_role_title_anchor"
      - "seed_must_have_core"
      - "seed_coverage_repair"
      - "seed_must_have_repair_01"
      - "seed_must_have_repair_02"
key_assertions:
  - "Generic fallback still initializes a multi-seed frontier."
failure_or_reject_reason: null
```

### 6. SelectActiveFrontierNode

```yaml
operator_name: "SelectActiveFrontierNode"
operator_inputs:
  open_frontier_node_ids:
    - "seed_role_title_anchor"
    - "seed_must_have_core"
    - "seed_coverage_repair"
    - "seed_must_have_repair_01"
    - "seed_must_have_repair_02"
tools_or_services: ["runtime deterministic priority scoring", "runtime donor packing"]
operator_outputs:
  SearchControllerContext_t:
    active_frontier_node_summary:
      frontier_node_id: "seed_must_have_core"
    donor_candidate_node_summaries: []
    allowed_operator_names:
      - "must_have_alias"
      - "strict_core"
      - "crossover_compose"
key_assertions:
  - "domain_company is absent from allowed operators."
failure_or_reject_reason: null
```

## Invariant Checks

- `routing_mode = generic_fallback`
- `selected_domain_pack_ids = []`
- `grounding_evidence_cards[*].source_card_id` uses `generic.requirement.*`
- `domain_company` is absent from bootstrap seeds and allowed operators

## Terminal Outcome

```yaml
terminal_artifact: "SearchControllerContext_t"
active_frontier_node_id: "seed_must_have_core"
continue_to_next_operator: "GenerateSearchControllerDecision"
```

## Judge Packet

```yaml
expected_route: "generic_fallback"
expected_allowed_operators: ["must_have_alias", "strict_core", "crossover_compose"]
expected_tool_calls:
  - "RequirementExtractionLLM"
  - "local grounding knowledge base snapshot"
  - "GroundingGenerationLLM draft"
expected_terminal_state:
  selected_domain_pack_ids: []
  donor_candidate_count: 0
must_hold:
  - "retrieved_cards is empty."
  - "Generic evidence uses virtual ids."
  - "Repair seeds appear when uncovered must-haves remain."
must_not_hold:
  - "domain_company appears anywhere in bootstrap output"
  - "selected_domain_pack_ids is non-empty"
```
