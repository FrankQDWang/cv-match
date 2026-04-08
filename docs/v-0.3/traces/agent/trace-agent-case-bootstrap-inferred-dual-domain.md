# Agent Trace: case-bootstrap-inferred-dual-domain

## Trace Meta

```yaml
case_id: "case-bootstrap-inferred-dual-domain"
audience: "agent"
paired_business_trace: "[[trace-business-case-bootstrap-inferred-dual-domain]]"
start_payloads: ["SearchInputTruth", "BusinessPolicyPack", "GroundingKnowledgeBaseSnapshot"]
terminal_artifact: "SearchControllerContext_t"
terminal_status: "continue_to_controller"
node_id_rendering: "human-readable case-local example ids; runtime id owner remains operator specs"
```

## Scenario Inputs

```yaml
SearchInputTruth:
  job_description_focus: "Senior Python / LLM Engineer"
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
    role_signal: "Senior Python / LLM Engineer"
tools_or_services: ["RequirementExtractionLLM", "runtime deterministic normalization"]
llm_audit:
  output_mode: "provider_native_strict_structured_output"
  retries: 0
  output_retries: 1
  validator_retry_count: 0
operator_outputs:
  RequirementSheet:
    role_title: "Senior Python / LLM Engineer"
    must_have_capabilities: ["Python backend", "LLM application", "retrieval or ranking experience"]
    preferred_capabilities: ["workflow orchestration", "to-b delivery"]
key_assertions:
  - "Requirement truth spans two distinct capability clusters."
failure_or_reject_reason: null
```

### 2. RetrieveGroundingKnowledge

```yaml
operator_name: "RetrieveGroundingKnowledge"
operator_inputs:
  explicit_domain_pack_ids: []
  must_have_capabilities:
    - "Python backend"
    - "LLM application"
    - "retrieval or ranking experience"
tools_or_services: ["local grounding knowledge base snapshot", "runtime deterministic routing", "runtime deterministic card matching"]
operator_outputs:
  KnowledgeRetrievalResult:
    routing_mode: "inferred_domain"
    selected_domain_pack_ids:
      - "llm_agent_rag_engineering"
      - "search_ranking_retrieval_engineering"
    routing_confidence: 0.7
    retrieved_cards:
      - "role_alias.llm_agent_rag_engineering.backend_agent_engineer"
      - "role_alias.search_ranking_retrieval_engineering.retrieval_engineer"
key_assertions:
  - "Both inferred packs clear threshold and cover different must-haves."
failure_or_reject_reason: null
```

### 3. FreezeScoringPolicy

```yaml
operator_name: "FreezeScoringPolicy"
operator_inputs:
  retrieved_domain_packs:
    - "llm_agent_rag_engineering"
    - "search_ranking_retrieval_engineering"
tools_or_services: ["runtime deterministic logic"]
operator_outputs:
  ScoringPolicy:
    rerank_query_text: "Senior Python / LLM Engineer; must-have: Python backend, LLM application, retrieval or ranking experience"
key_assertions:
  - "Dual-domain retrieval does not create a second scoring policy."
failure_or_reject_reason: null
```

### 4. GenerateGroundingOutput

```yaml
operator_name: "GenerateGroundingOutput"
operator_inputs:
  selected_domain_pack_ids:
    - "llm_agent_rag_engineering"
    - "search_ranking_retrieval_engineering"
tools_or_services: ["GroundingGenerationLLM draft", "runtime deterministic normalization"]
llm_audit:
  output_mode: "provider_native_strict_structured_output"
  retries: 0
  output_retries: 1
  validator_retry_count: 0
operator_outputs:
  GroundingOutput:
    frontier_seed_specifications:
      - {operator_name: "must_have_alias", seed_terms: ["agent engineer", "rag", "python"]}
      - {operator_name: "must_have_alias", seed_terms: ["retrieval engineer", "ranking", "rag"]}
      - {operator_name: "domain_company", seed_terms: ["llm platform", "workflow orchestration"]}
key_assertions:
  - "Bootstrap seeds preserve both domain anchors without using crossover."
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
      - "seed_agent_core"
      - "seed_search_domain"
      - "seed_platform"
key_assertions:
  - "Dual-domain bootstrap still starts from plain seed nodes."
failure_or_reject_reason: null
```

### 6. SelectActiveFrontierNode

```yaml
operator_name: "SelectActiveFrontierNode"
operator_inputs:
  open_frontier_node_ids:
    - "seed_agent_core"
    - "seed_search_domain"
    - "seed_platform"
tools_or_services: ["runtime deterministic priority scoring", "runtime donor packing"]
operator_outputs:
  SearchControllerContext_t:
    active_frontier_node_summary:
      frontier_node_id: "seed_agent_core"
    donor_candidate_node_summaries: []
    allowed_operator_names:
      - "must_have_alias"
      - "strict_core"
      - "domain_company"
      - "crossover_compose"
key_assertions:
  - "Round-0 dual-domain still has no donor because no seed has reward."
failure_or_reject_reason: null
```

## Invariant Checks

- `routing_mode = inferred_domain`
- `|selected_domain_pack_ids| = 2`
- `selected_domain_pack_ids` cover different must-have clusters
- `donor_candidate_node_summaries = []`

## Terminal Outcome

```yaml
terminal_artifact: "SearchControllerContext_t"
active_frontier_node_id: "seed_agent_core"
continue_to_next_operator: "GenerateSearchControllerDecision"
```

## Judge Packet

```yaml
expected_route: "inferred_domain_dual"
expected_allowed_operators: ["must_have_alias", "strict_core", "domain_company", "crossover_compose"]
expected_tool_calls:
  - "RequirementExtractionLLM"
  - "local grounding knowledge base snapshot"
  - "GroundingGenerationLLM draft"
expected_terminal_state:
  selected_domain_pack_ids:
    - "llm_agent_rag_engineering"
    - "search_ranking_retrieval_engineering"
  donor_candidate_count: 0
must_hold:
  - "Two domain packs are selected."
  - "The two packs complement different must-haves."
must_not_hold:
  - "routing_mode = explicit_domain"
  - "routing_mode = generic_fallback"
```
