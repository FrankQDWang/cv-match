# Agent Trace: case-bootstrap-explicit-domain

## Trace Meta

```yaml
case_id: "case-bootstrap-explicit-domain"
audience: "agent"
paired_business_trace: "[[trace-business-case-bootstrap-explicit-domain]]"
start_payloads: ["SearchInputTruth", "BusinessPolicyPack", "GroundingKnowledgeBaseSnapshot"]
terminal_artifact: "SearchControllerContext_t"
terminal_status: "continue_to_controller"
node_id_rendering: "human-readable case-local example ids; runtime id owner remains operator specs"
```

## Scenario Inputs

```yaml
SearchInputTruth:
  job_description_focus: "Senior Agent Backend Engineer"
  hiring_notes_focus: "明确要求 Agent/RAG 场景与 workflow orchestration"
BusinessPolicyPack:
  domain_pack_ids: ["llm_agent_rag_engineering"]
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
    hard_constraints:
      locations: ["Shanghai"]
key_assertions:
  - "RequirementSheet becomes canonical truth."
failure_or_reject_reason: null
```

### 2. RetrieveGroundingKnowledge

```yaml
operator_name: "RetrieveGroundingKnowledge"
operator_inputs:
  BusinessPolicyPack.domain_pack_ids: ["llm_agent_rag_engineering"]
  RequirementSheet.role_title: "Senior Agent Backend Engineer"
tools_or_services: ["local grounding knowledge base snapshot", "runtime deterministic routing", "runtime deterministic card matching"]
operator_outputs:
  KnowledgeRetrievalResult:
    routing_mode: "explicit_domain"
    selected_domain_pack_ids: ["llm_agent_rag_engineering"]
    routing_confidence: 1.0
    retrieved_cards:
      - "role_alias.llm_agent_rag_engineering.backend_agent_engineer"
      - "stack.llm_agent_rag_engineering.workflow_orchestration"
    negative_signal_terms: ["pure algorithm research"]
key_assertions:
  - "Explicit domain bypasses inferred routing."
failure_or_reject_reason: null
```

### 3. FreezeScoringPolicy

```yaml
operator_name: "FreezeScoringPolicy"
operator_inputs:
  RequirementSheet.hard_constraints:
    locations: ["Shanghai"]
  BusinessPolicyPack.fit_gate_overrides: {}
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
  - "Run-level scoring policy is frozen before bootstrap search."
failure_or_reject_reason: null
```

### 4. GenerateGroundingOutput

```yaml
operator_name: "GenerateGroundingOutput"
operator_inputs:
  routing_mode: "explicit_domain"
  retrieved_cards:
    - "role_alias.llm_agent_rag_engineering.backend_agent_engineer"
    - "stack.llm_agent_rag_engineering.workflow_orchestration"
tools_or_services: ["GroundingGenerationLLM draft", "runtime deterministic normalization"]
llm_audit:
  output_mode: "provider_native_strict_structured_output"
  retries: 0
  output_retries: 1
  validator_retry_count: 0
operator_outputs:
  GroundingOutput:
    grounding_evidence_cards:
      - "role_alias.llm_agent_rag_engineering.backend_agent_engineer"
      - "stack.llm_agent_rag_engineering.workflow_orchestration"
    frontier_seed_specifications:
      - {operator_name: "must_have_alias", seed_terms: ["agent engineer", "python", "rag"]}
      - {operator_name: "strict_core", seed_terms: ["workflow orchestration", "agent platform"]}
      - {operator_name: "domain_company", seed_terms: ["llm platform", "ai application"]}
key_assertions:
  - "domain_company seed is legal because provenance is domain-grounded."
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
    remaining_budget: 5
    operator_statistics:
      crossover_compose: {average_reward: 0.0, times_selected: 0}
key_assertions:
  - "All bootstrap seeds are open nodes with reward_breakdown = null."
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
      selected_operator_name: "must_have_alias"
    donor_candidate_node_summaries: []
    allowed_operator_names:
      - "must_have_alias"
      - "strict_core"
      - "domain_company"
      - "crossover_compose"
key_assertions:
  - "Round-0 has no donor candidates because seed nodes have reward_breakdown = null."
failure_or_reject_reason: null
```

## Invariant Checks

- `routing_mode = explicit_domain`
- `selected_domain_pack_ids = ["llm_agent_rag_engineering"]`
- `domain_company` appears in `frontier_seed_specifications`
- `donor_candidate_node_summaries = []`

## Terminal Outcome

```yaml
terminal_artifact: "SearchControllerContext_t"
active_frontier_node_id: "seed_must_have_alias_01"
continue_to_next_operator: "GenerateSearchControllerDecision"
```

## Judge Packet

```yaml
expected_route: "explicit_domain"
expected_allowed_operators: ["must_have_alias", "strict_core", "domain_company", "crossover_compose"]
expected_tool_calls:
  - "RequirementExtractionLLM"
  - "local grounding knowledge base snapshot"
  - "GroundingGenerationLLM draft"
expected_terminal_state:
  active_frontier_node_id: "seed_must_have_alias_01"
  donor_candidate_count: 0
must_hold:
  - "Explicit domain bypasses inferred routing."
  - "domain_company is allowed in bootstrap."
must_not_hold:
  - "routing_mode = generic_fallback"
  - "non-empty donor candidate list on round 0"
```
