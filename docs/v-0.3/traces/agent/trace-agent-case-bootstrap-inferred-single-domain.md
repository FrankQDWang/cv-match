# Agent Trace: case-bootstrap-inferred-single-domain

## Trace Meta

```yaml
case_id: "case-bootstrap-inferred-single-domain"
audience: "agent"
paired_business_trace: "[[trace-business-case-bootstrap-inferred-single-domain]]"
start_payloads: ["SearchInputTruth", "BusinessPolicyPack", "GroundingKnowledgeBaseSnapshot"]
terminal_artifact: "SearchControllerContext_t"
terminal_status: "continue_to_controller"
node_id_rendering: "human-readable case-local example ids; runtime id owner remains operator specs"
```

## Scenario Inputs

```yaml
SearchInputTruth:
  job_description_focus: "Senior Agent Backend Engineer"
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
    role_signal: "Senior Agent Backend Engineer"
tools_or_services: ["RequirementExtractionLLM", "runtime deterministic normalization"]
llm_audit:
  output_mode: "provider_native_strict_structured_output"
  retries: 0
  output_retries: 1
  validator_retry_count: 0
operator_outputs:
  RequirementSheet:
    role_title: "Senior Agent Backend Engineer"
    must_have_capabilities: ["Python backend", "LLM application", "workflow orchestration"]
    preferred_capabilities: ["to-b delivery"]
key_assertions:
  - "Requirement truth is extracted before domain inference."
failure_or_reject_reason: null
```

### 2. RetrieveGroundingKnowledge

```yaml
operator_name: "RetrieveGroundingKnowledge"
operator_inputs:
  explicit_domain_pack_ids: []
  role_title: "Senior Agent Backend Engineer"
tools_or_services: ["local grounding knowledge base snapshot", "runtime deterministic routing", "runtime deterministic card matching"]
operator_outputs:
  KnowledgeRetrievalResult:
    routing_mode: "inferred_domain"
    selected_domain_pack_ids: ["llm_agent_rag_engineering"]
    routing_confidence: 0.8
    retrieved_cards:
      - "role_alias.llm_agent_rag_engineering.backend_agent_engineer"
      - "stack.llm_agent_rag_engineering.workflow_orchestration"
key_assertions:
  - "Single-pack inference wins because top1 clears threshold and margin."
failure_or_reject_reason: null
```

### 3. FreezeScoringPolicy

```yaml
operator_name: "FreezeScoringPolicy"
operator_inputs:
  routing_mode: "inferred_domain"
tools_or_services: ["runtime deterministic logic"]
operator_outputs:
  ScoringPolicy:
    fit_gate_constraints:
      locations: ["Shanghai"]
    fusion_weights:
      rerank: 0.55
      must_have: 0.25
      preferred: 0.1
      risk_penalty: 0.1
key_assertions:
  - "ScoringPolicy is independent from whether routing was explicit or inferred."
failure_or_reject_reason: null
```

### 4. GenerateGroundingOutput

```yaml
operator_name: "GenerateGroundingOutput"
operator_inputs:
  selected_domain_pack_ids: ["llm_agent_rag_engineering"]
tools_or_services: ["GroundingGenerationLLM draft", "runtime deterministic normalization"]
llm_audit:
  output_mode: "provider_native_strict_structured_output"
  retries: 0
  output_retries: 1
  validator_retry_count: 0
operator_outputs:
  GroundingOutput:
    frontier_seed_specifications:
      - {operator_name: "must_have_alias", seed_terms: ["agent engineer", "python", "rag"]}
      - {operator_name: "strict_core", seed_terms: ["workflow orchestration", "agent platform"]}
      - {operator_name: "domain_company", seed_terms: ["llm platform", "ai application"]}
key_assertions:
  - "Single inferred domain still allows domain_company seed."
failure_or_reject_reason: null
```

### 5. InitializeFrontierState

```yaml
operator_name: "InitializeFrontierState"
operator_inputs:
  frontier_seed_specifications_count: 3
tools_or_services: ["runtime deterministic logic"]
operator_outputs:
  FrontierState_t:
    open_frontier_node_ids:
      - "seed_must_have_alias_01"
      - "seed_strict_core_02"
      - "seed_domain_company_03"
key_assertions:
  - "Bootstrap frontier is initialized without donor lineage."
failure_or_reject_reason: null
```

### 6. SelectActiveFrontierNode

```yaml
operator_name: "SelectActiveFrontierNode"
operator_inputs:
  open_frontier_node_ids:
    - "seed_must_have_alias_01"
    - "seed_strict_core_02"
    - "seed_domain_company_03"
tools_or_services: ["runtime deterministic priority scoring", "runtime donor packing"]
operator_outputs:
  SearchControllerContext_t:
    active_frontier_node_summary:
      frontier_node_id: "seed_must_have_alias_01"
    donor_candidate_node_summaries: []
    allowed_operator_names:
      - "must_have_alias"
      - "strict_core"
      - "domain_company"
      - "crossover_compose"
key_assertions:
  - "Single inferred domain does not change round-0 donor emptiness."
failure_or_reject_reason: null
```

## Invariant Checks

- `routing_mode = inferred_domain`
- `|selected_domain_pack_ids| = 1`
- `domain_company` remains allowed
- `donor_candidate_node_summaries = []`

## Terminal Outcome

```yaml
terminal_artifact: "SearchControllerContext_t"
active_frontier_node_id: "seed_must_have_alias_01"
continue_to_next_operator: "GenerateSearchControllerDecision"
```

## Judge Packet

```yaml
expected_route: "inferred_domain_single"
expected_allowed_operators: ["must_have_alias", "strict_core", "domain_company", "crossover_compose"]
expected_tool_calls:
  - "RequirementExtractionLLM"
  - "local grounding knowledge base snapshot"
  - "GroundingGenerationLLM draft"
expected_terminal_state:
  selected_domain_pack_ids: ["llm_agent_rag_engineering"]
  donor_candidate_count: 0
must_hold:
  - "Exactly one inferred domain pack is selected."
  - "Bootstrap still yields 3 seeds."
must_not_hold:
  - "selected_domain_pack_ids has length 2"
  - "routing_mode = generic_fallback"
```
