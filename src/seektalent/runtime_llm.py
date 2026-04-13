from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic_ai import Agent, ModelRetry
from pydantic_ai.exceptions import UnexpectedModelBehavior

from seektalent.llm_config import build_llm_binding
from seektalent.models import (
    BranchEvaluationDraft_t,
    FrontierState_t,
    FrontierState_t1,
    LLMCallAudit,
    RequirementSheet,
    RuntimeBudgetState,
    SearchRoundArtifact,
    SearchExecutionPlan_t,
    SearchExecutionResult_t,
    SearchRunSummaryDraft_t,
    SearchScoringResult_t,
)
from seektalent.prompt_surfaces import (
    OUTPUT_RETRIES,
    RETRIES,
    STRICT_MODEL_SETTINGS,
    build_branch_evaluation_prompt_surface,
    build_llm_call_audit,
    build_search_run_finalization_prompt_surface,
)
from seektalent.prompts import load_prompt

BRANCH_OUTCOME_EVALUATION_PROMPT = load_prompt("branch_outcome_evaluation.md")
SEARCH_RUN_FINALIZATION_PROMPT = load_prompt("search_run_finalization.md")


def _test_model_outputs(
    output_type: type[BranchEvaluationDraft_t] | type[SearchRunSummaryDraft_t],
    *,
    model: Any | None,
) -> list[BranchEvaluationDraft_t | SearchRunSummaryDraft_t] | None:
    if getattr(model, "model_name", None) != "test":
        return None
    payload = getattr(model, "custom_output_args", None)
    if isinstance(payload, dict):
        return [output_type.model_validate(payload)]
    if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        return [output_type.model_validate(item) for item in payload]
    raise ValueError("test_model_requires_custom_output_args")


async def request_branch_evaluation_draft(
    requirement_sheet: RequirementSheet,
    frontier_state: FrontierState_t,
    plan: SearchExecutionPlan_t,
    execution_result: SearchExecutionResult_t,
    scoring_result: SearchScoringResult_t,
    runtime_budget_state: RuntimeBudgetState,
    *,
    model: Any | None = None,
    env_file: str | Path | None = ".env",
) -> tuple[BranchEvaluationDraft_t, LLMCallAudit]:
    parent_node = frontier_state.frontier_nodes.get(
        plan.child_frontier_node_stub.parent_frontier_node_id
    )
    if parent_node is None:
        raise ValueError(
            f"unknown_parent_frontier_node_id: {plan.child_frontier_node_stub.parent_frontier_node_id}"
        )
    prompt_surface = build_branch_evaluation_prompt_surface(
        requirement_sheet,
        parent_node,
        plan,
        execution_result,
        scoring_result,
        runtime_budget_state,
        instructions_text=BRANCH_OUTCOME_EVALUATION_PROMPT,
    )
    binding = build_llm_binding(
        BranchEvaluationDraft_t,
        callpoint="branch_outcome_evaluation",
        model=model,
        env_file=env_file,
    )
    test_outputs = _test_model_outputs(BranchEvaluationDraft_t, model=model)
    if test_outputs is not None:
        validator_retry_count = 0
        for index, draft in enumerate(test_outputs):
            try:
                return _validate_branch_evaluation_draft(
                    draft,
                    scoring_result=scoring_result,
                ), build_llm_call_audit(
                    model=model,
                    prompt_surface=prompt_surface,
                    validator_retry_count=validator_retry_count,
                    output_mode=binding.audit_output_mode,
                    model_name=binding.audit_model_name,
                )
            except ModelRetry:
                validator_retry_count += 1
                if validator_retry_count > 1 or index == len(test_outputs) - 1:
                    raise
        raise ValueError("test_model_requires_custom_output_args")
    validator_retry_count = 0
    last_validator_error: str | None = None
    active_agent = Agent(
        binding.model,
        output_type=binding.output_type,
        retries=RETRIES,
        output_retries=OUTPUT_RETRIES,
        builtin_tools=(),
        toolsets=(),
        system_prompt=(),
        model_settings=STRICT_MODEL_SETTINGS,
    )

    @active_agent.output_validator
    def _output_validator(draft: BranchEvaluationDraft_t) -> BranchEvaluationDraft_t:
        nonlocal validator_retry_count
        nonlocal last_validator_error
        try:
            return _validate_branch_evaluation_draft(
                draft,
                scoring_result=scoring_result,
            )
        except ModelRetry as exc:
            validator_retry_count += 1
            last_validator_error = str(exc)
            raise

    try:
        result = await active_agent.run(
            prompt_surface.input_text,
            message_history=None,
            instructions=BRANCH_OUTCOME_EVALUATION_PROMPT,
            builtin_tools=(),
            toolsets=(),
            infer_name=False,
        )
    except UnexpectedModelBehavior as exc:
        message = last_validator_error or str(exc)
        raise RuntimeError(f"branch_evaluation_output_invalid: {message}") from exc
    return BranchEvaluationDraft_t.model_validate(result.output), build_llm_call_audit(
        model=model,
        prompt_surface=prompt_surface,
        validator_retry_count=validator_retry_count,
        output_mode=binding.audit_output_mode,
        model_name=binding.audit_model_name,
    )


async def request_search_run_summary_draft(
    requirement_sheet: RequirementSheet,
    frontier_state: FrontierState_t1,
    rounds: list[SearchRoundArtifact],
    stop_reason: str,
    *,
    model: Any | None = None,
    env_file: str | Path | None = ".env",
) -> tuple[SearchRunSummaryDraft_t, LLMCallAudit]:
    prompt_surface = build_search_run_finalization_prompt_surface(
        requirement_sheet,
        frontier_state,
        rounds,
        stop_reason,
        instructions_text=SEARCH_RUN_FINALIZATION_PROMPT,
    )
    binding = build_llm_binding(
        SearchRunSummaryDraft_t,
        callpoint="search_run_finalization",
        model=model,
        env_file=env_file,
    )
    test_outputs = _test_model_outputs(SearchRunSummaryDraft_t, model=model)
    if test_outputs is not None:
        validator_retry_count = 0
        for index, draft in enumerate(test_outputs):
            try:
                return _validate_search_run_summary_draft(draft), build_llm_call_audit(
                    model=model,
                    prompt_surface=prompt_surface,
                    validator_retry_count=validator_retry_count,
                    output_mode=binding.audit_output_mode,
                    model_name=binding.audit_model_name,
                )
            except ModelRetry:
                validator_retry_count += 1
                if validator_retry_count > 1 or index == len(test_outputs) - 1:
                    raise
        raise ValueError("test_model_requires_custom_output_args")
    validator_retry_count = 0
    last_validator_error: str | None = None
    active_agent = Agent(
        binding.model,
        output_type=binding.output_type,
        retries=RETRIES,
        output_retries=OUTPUT_RETRIES,
        builtin_tools=(),
        toolsets=(),
        system_prompt=(),
        model_settings=STRICT_MODEL_SETTINGS,
    )

    @active_agent.output_validator
    def _output_validator(draft: SearchRunSummaryDraft_t) -> SearchRunSummaryDraft_t:
        nonlocal validator_retry_count
        nonlocal last_validator_error
        try:
            return _validate_search_run_summary_draft(draft)
        except ModelRetry as exc:
            validator_retry_count += 1
            last_validator_error = str(exc)
            raise

    try:
        result = await active_agent.run(
            prompt_surface.input_text,
            message_history=None,
            instructions=SEARCH_RUN_FINALIZATION_PROMPT,
            builtin_tools=(),
            toolsets=(),
            infer_name=False,
        )
    except UnexpectedModelBehavior as exc:
        message = last_validator_error or str(exc)
        raise RuntimeError(f"search_run_finalization_output_invalid: {message}") from exc
    return SearchRunSummaryDraft_t.model_validate(result.output), build_llm_call_audit(
        model=model,
        prompt_surface=prompt_surface,
        validator_retry_count=validator_retry_count,
        output_mode=binding.audit_output_mode,
        model_name=binding.audit_model_name,
    )


def _validate_branch_evaluation_draft(
    draft: BranchEvaluationDraft_t,
    *,
    scoring_result: SearchScoringResult_t,
) -> BranchEvaluationDraft_t:
    if not scoring_result.node_shortlist_candidate_ids and not draft.branch_exhausted:
        raise ModelRetry(
            "branch_evaluation requires branch_exhausted=true when node_shortlist_candidate_ids is empty"
        )
    return draft.model_copy(
        update={"evaluation_notes": _normalized_text(draft.evaluation_notes)}
    )


def _validate_search_run_summary_draft(
    draft: SearchRunSummaryDraft_t,
) -> SearchRunSummaryDraft_t:
    summary = _normalized_text(draft.run_summary)
    if not summary:
        raise ModelRetry("search_run_finalization requires non-empty run_summary")
    if summary.lower() in {"n/a", "na", "none", "null", "todo", "tbd", "待补充", "待发单方补充"}:
        raise ModelRetry("search_run_finalization requires a concrete run_summary")
    return draft.model_copy(update={"run_summary": summary})


def _normalized_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split()).strip()


__all__ = [
    "BRANCH_OUTCOME_EVALUATION_PROMPT",
    "SEARCH_RUN_FINALIZATION_PROMPT",
    "request_branch_evaluation_draft",
    "request_search_run_summary_draft",
]
