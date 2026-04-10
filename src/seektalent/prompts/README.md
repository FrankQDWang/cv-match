# Prompt Files

- `bootstrap_requirement_extraction.md`
  owner: `bootstrap_llm.py`
  input: `PromptSurfaceSnapshot(surface_id=requirement_extraction).input_text`
  output: `RequirementExtractionDraft`

- `bootstrap_keyword_generation.md`
  owner: `bootstrap_llm.py`
  input: `PromptSurfaceSnapshot(surface_id=bootstrap_keyword_generation).input_text`
  output: `BootstrapKeywordDraft`

- `search_controller_decision.md`
  owner: `controller_llm.py`
  input: `PromptSurfaceSnapshot(surface_id=search_controller_decision).input_text`
  output: `SearchControllerDecisionDraft_t`

- `branch_outcome_evaluation.md`
  owner: `runtime_llm.py`
  input: `PromptSurfaceSnapshot(surface_id=branch_outcome_evaluation).input_text`
  output: `BranchEvaluationDraft_t`

- `search_run_finalization.md`
  owner: `runtime_llm.py`
  input: `PromptSurfaceSnapshot(surface_id=search_run_finalization).input_text`
  output: `SearchRunSummaryDraft_t`
